import ast
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
    class_names = re.findall(r"class\s+([A-Za-z_$][\w$]*)", source)
    function_names = re.findall(r"function\s+([A-Za-z_$][\w$]*)\s*\(", source)
    arrow_names = re.findall(r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>", source)
    imports = re.findall(r"import\s+(?:.+?\s+from\s+)?['\"]([^'\"]+)['\"]", source)

    return {
        "classes": [{"name": name, "line": 0} for name in class_names],
        "functions": [{"name": name, "line": 0} for name in function_names + arrow_names],
        "imports": imports,
    }


MAX_NODES = 30
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
    MAX_EDGES_PER_NODE = 3
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
