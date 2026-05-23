import ast
import json
import re
from pathlib import Path
from typing import Any
SUPPORTED_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx"}
IGNORE_PARTS = {".git", "node_modules", "dist", "build", "__pycache__", ".next", ".venv", "venv"}


def should_scan(path: Path) -> bool:
    return path.suffix in SUPPORTED_SUFFIXES and not any(part in IGNORE_PARTS for part in path.parts)


def analyze_repo(repo_path: Path) -> list[dict[str, Any]]:
    results = []
    for file in repo_path.rglob("*"):
        if file.is_file() and should_scan(file):
            rel = str(file.relative_to(repo_path))
            text = file.read_text(encoding="utf-8", errors="ignore")
            if file.suffix == ".py":
                info = analyze_python(text)
            else:
                info = analyze_js_ts(text)
            info["path"] = rel
            info["language"] = language_from_suffix(file.suffix)
            results.append(info)
    return results


def language_from_suffix(suffix: str) -> str:
    return {
        ".py": "Python",
        ".js": "JavaScript",
        ".jsx": "React JSX",
        ".ts": "TypeScript",
        ".tsx": "React TSX",
    }.get(suffix, "Unknown")


def analyze_python(source: str) -> dict[str, Any]:
    data: dict[str, Any] = {"classes": [], "functions": [], "imports": []}
    lines = source.splitlines()
    data["total_lines"] = len(lines)
    data["blank_lines"] = sum(1 for l in lines if not l.strip())
    data["comment_lines"] = sum(1 for l in lines if l.strip().startswith("#"))

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return data

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            data["classes"].append({"name": node.name, "line": node.lineno})
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            data["functions"].append({"name": node.name, "line": node.lineno})
        elif isinstance(node, ast.Import):
            for n in node.names:
                data["imports"].append(n.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            data["imports"].append(module)
    return data

def analyze_js_ts(source: str) -> dict[str, Any]:
    """用正则分析 JS/TS 文件，支持更多语法模式。"""
    classes: list[dict] = []
    functions: list[dict] = []
    imports: list[str] = []

    lines = source.splitlines()
    total_lines = len(lines)
    blank_lines = sum(1 for l in lines if not l.strip())
    comment_lines = sum(1 for l in lines if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("*"))

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # 类声明（含 extends）
        m = re.match(r"(?:export\s+)?(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)", stripped)
        if m:
            classes.append({"name": m.group(1), "line": i})
            continue

        # 函数声明
        m = re.match(r"(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*[\(<]", stripped)
        if m:
            functions.append({"name": m.group(1), "line": i})
            continue

        # 箭头函数: const/let/var name = ... => / function
        m = re.match(r"(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?", stripped)
        if m and ("=>" in stripped or "function" in stripped):
            functions.append({"name": m.group(1), "line": i})
            continue

        # 方法定义: name(...) { 或 async name(...) {
        m = re.match(r"(?:async\s+)?([A-Za-z_$][\w$]*)\s*[\(<].*\)?\s*\{", stripped)
        if m and m.group(1) not in ("if", "for", "while", "switch", "catch", "return"):
            functions.append({"name": m.group(1), "line": i})
            continue

        # import ... from '...'
        m = re.findall(r"import\s+(?:type\s+)?(?:.+?\s+from\s+)?['\"]([^'\"]+)['\"]", stripped)
        if m:
            imports.extend(m)
            continue

        # require('...')
        m = re.findall(r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", stripped)
        if m:
            imports.extend(m)

    return {
        "classes": classes,
        "functions": functions,
        "imports": imports,
        "total_lines": total_lines,
        "blank_lines": blank_lines,
        "comment_lines": comment_lines,
    }

MAX_NODES = 50  # 提升节点上限，覆盖大型仓库
TEST_PREFIXES = ("test_", "tests/", "docs_src/", "docs/", "scripts/", "benchmarks/")


def _is_core_file(path: str) -> bool:
    p = path.replace("\\", "/").lower()
    return not any(p.startswith(prefix) for prefix in TEST_PREFIXES)


def _top_module(path: str) -> str:
    parts = path.replace("\\", "/").split("/")
    return parts[0] if len(parts) > 1 else "."


def _short_name(path: str) -> str:
    """Show last 2 path segments for readability."""
    p = path.replace("\\", "/")
    parts = p.split("/")
    if len(parts) <= 2:
        return p
    return "/".join(parts[-2:])


def generate_mermaid(files: list[dict[str, Any]]) -> str:
    if not files:
        return 'graph TD\n  A["No analyzable files found"]'

    # 1) Keep only core source files (no tests, docs, scripts)
    core = [f for f in files if _is_core_file(f["path"])]

    # 2) Score by connectivity: how many other core files import this one
    path_set = {f["path"] for f in core}
    import_count: dict[str, int] = {f["path"]: 0 for f in core}
    edges_set: set[tuple[str, str]] = set()

    for f in core:
        for imp in f.get("imports", []):
            target = find_import_target(imp, files)
            if target and target != f["path"] and target in path_set:
                import_count[target] = import_count.get(target, 0) + 1
                edges_set.add((f["path"], target))

    # 3) Sort by connectivity, pick top N
    ranked = sorted(core, key=lambda f: import_count.get(f["path"], 0), reverse=True)[:MAX_NODES]
    selected = {f["path"] for f in ranked}

    # 4) Build node id map
    node_id: dict[str, str] = {}
    for idx, f in enumerate(ranked):
        node_id[f["path"]] = f"N{idx}"

    # 5) Group by top-level module for subgraphs
    groups: dict[str, list[dict]] = {}
    for f in ranked:
        mod = _top_module(f["path"])
        groups.setdefault(mod, []).append(f)

    lines = ["graph TD"]
    used_ids: set[str] = set()

    for mod, members in groups.items():
        if len(members) == 1:
            f = members[0]
            safe = _short_name(f["path"]).replace('"', "'")
            nid = node_id[f["path"]]
            lines.append(f'  {nid}["{safe}"]')
            used_ids.add(nid)
        else:
            lines.append(f"  subgraph {mod}")
            for f in members:
                safe = _short_name(f["path"]).replace('"', "'")
                nid = node_id[f["path"]]
                lines.append(f'    {nid}["{safe}"]')
                used_ids.add(nid)
            lines.append("  end")

    # 6) Add edges (only between selected nodes), limit per node
    edge_count: dict[str, int] = {}
    MAX_EDGES_PER_NODE = 5  # 每个节点最多 5 条边
    for src, tgt in sorted(edges_set):
        if src in selected and tgt in selected:
            if edge_count.get(src, 0) >= MAX_EDGES_PER_NODE:
                continue
            lines.append(f"  {node_id[src]} --> {node_id[tgt]}")
            edge_count[src] = edge_count.get(src, 0) + 1

    return "\n".join(lines)


def find_import_target(import_name: str, files: list[dict[str, Any]]) -> str | None:
    normalized = import_name.replace(".", "/")
    for file in files:
        path = file["path"].replace("\\", "/")
        if path.endswith(normalized + ".py") or path.endswith(normalized + ".js") or path.endswith(normalized + ".ts"):
            return file["path"]
    return None


def generate_learning_path(files: list[dict[str, Any]]) -> list[str]:
    priority_keywords = ["main", "app", "index", "server", "router", "controller", "service", "model", "schema"]

    def score(file: dict[str, Any]) -> int:
        path = file["path"].lower()
        points = 0
        for i, kw in enumerate(priority_keywords):
            if kw in path:
                points += 100 - i * 8
        points += len(file.get("functions", [])) * 2
        points += len(file.get("classes", [])) * 3
        return points

    ranked = sorted(files, key=score, reverse=True)
    return [f["path"] for f in ranked[:10]]


def generate_dependency_graph(repo_path: Path) -> str:
    """生成项目依赖关系图（Mermaid 格式）。"""
    deps: dict[str, list[str]] = {}

    # 解析 package.json
    pkg_json = repo_path / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            prod = list(data.get("dependencies", {}).keys())
            dev = list(data.get("devDependencies", {}).keys())
            if prod:
                deps["npm: dependencies"] = prod[:20]  # 限制数量
            if dev:
                deps["npm: devDependencies"] = dev[:15]
        except Exception:
            pass

    # 解析 requirements.txt
    req_txt = repo_path / "requirements.txt"
    if req_txt.exists():
        try:
            lines = req_txt.read_text(encoding="utf-8").splitlines()
            pkgs = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("-"):
                    # 提取包名（去掉版本号）
                    name = re.split(r"[>=<!~\[]", line)[0].strip()
                    if name:
                        pkgs.append(name)
            if pkgs:
                deps["pip: requirements"] = pkgs[:20]
        except Exception:
            pass

    # 解析 pyproject.toml
    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists() and "pip: requirements" not in deps:
        try:
            content = pyproject.read_text(encoding="utf-8")
            # 简单提取 dependencies
            m = re.search(r"dependencies\s*=\s*\[(.*?)\]", content, re.DOTALL)
            if m:
                pkgs = re.findall(r'"([^"]+)"', m.group(1))
                if pkgs:
                    deps["pip: pyproject"] = [re.split(r"[>=<!~\[]", p)[0].strip() for p in pkgs[:20]]
        except Exception:
            pass

    if not deps:
        return 'graph TD\n  A["未找到依赖文件（package.json / requirements.txt / pyproject.toml）"]'

    # 生成 Mermaid
    lines = ["graph LR"]
    lines.append('  ROOT["📦 项目"]')

    node_id = 0
    for category, packages in deps.items():
        cat_id = f"C{node_id}"
        node_id += 1
        lines.append(f'  {cat_id}["{category}"]')
        lines.append(f'  ROOT --> {cat_id}')

        for pkg in packages[:12]:  # 每类最多显示 12 个
            safe = pkg.replace('"', "'")
            pkg_id = f"N{node_id}"
            node_id += 1
            lines.append(f'  {pkg_id}["{safe}"]')
            lines.append(f'  {cat_id} --> {pkg_id}')

    return "\n".join(lines)