import hashlib
import json
import os
import shutil
from pathlib import Path
from git import Repo

BASE_DIR = Path(__file__).resolve().parents[2]
REPOS_DIR = BASE_DIR / "repos"
CACHE_DIR = BASE_DIR / "cache"
REPOS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

IGNORE_DIRS = {".git", "node_modules", "dist", "build", "__pycache__", ".next", ".venv", "venv"}


def repo_id_from_url(repo_url: str) -> str:
    return hashlib.sha1(repo_url.encode("utf-8")).hexdigest()[:12]


def get_commit_hash(repo_path: Path) -> str:
    """获取当前 HEAD 的 commit hash。"""
    try:
        repo = Repo(repo_path)
        return repo.head.commit.hexsha[:12]
    except Exception:
        return "unknown"


def get_cache_path(repo_id: str, commit_hash: str) -> Path:
    return CACHE_DIR / f"{repo_id}_{commit_hash}.json"


def load_cache(repo_id: str, commit_hash: str) -> dict | None:
    """加载缓存，返回 None 表示缓存不存在。"""
    path = get_cache_path(repo_id, commit_hash)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def save_cache(repo_id: str, commit_hash: str, data: dict):
    """保存分析结果到缓存。"""
    path = get_cache_path(repo_id, commit_hash)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def clone_or_update(repo_url: str) -> tuple[str, Path]:
    repo_id = repo_id_from_url(repo_url)
    repo_path = REPOS_DIR / repo_id

    if repo_path.exists():
        try:
            repo = Repo(repo_path)
            repo.remotes.origin.pull()
        except Exception:
            shutil.rmtree(repo_path)
            Repo.clone_from(repo_url, repo_path)
    else:
        Repo.clone_from(repo_url, repo_path)

    return repo_id, repo_path


def get_repo_path(repo_id: str) -> Path:
    repo_path = REPOS_DIR / repo_id
    if not repo_path.exists():
        raise FileNotFoundError("Repo not found. Please analyze it first.")
    return repo_path


def build_file_tree(repo_path: Path) -> list[dict]:
    def walk(path: Path) -> list[dict]:
        nodes = []
        for child in sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            if child.name in IGNORE_DIRS:
                continue
            rel = str(child.relative_to(repo_path))
            if child.is_dir():
                nodes.append({"name": child.name, "path": rel, "type": "dir", "children": walk(child)})
            else:
                nodes.append({"name": child.name, "path": rel, "type": "file"})
        return nodes

    return walk(repo_path)


def read_file(repo_path: Path, file_path: str) -> str:
    target = (repo_path / file_path).resolve()
    if not str(target).startswith(str(repo_path.resolve())):
        raise ValueError("Invalid file path")
    return target.read_text(encoding="utf-8", errors="ignore")


def cleanup_old_repos(max_age_days: int = 7):
    """清理超过指定天数的仓库目录。"""
    import time
    now = time.time()
    cutoff = now - max_age_days * 86400

    for item in REPOS_DIR.iterdir():
        if item.is_dir() and item.stat().st_mtime < cutoff:
            shutil.rmtree(item, ignore_errors=True)

    # 同时清理过期缓存
    for item in CACHE_DIR.iterdir():
        if item.is_file() and item.stat().st_mtime < cutoff:
            item.unlink(missing_ok=True)
