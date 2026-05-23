import uuid
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from app.models import AnalyzeRequest, AnalyzeResponse, ExplainRequest
from app.services.repo_service import (
    clone_or_update, build_file_tree, get_repo_path, read_file,
    get_commit_hash, load_cache, save_cache, cleanup_old_repos,
)
from app.services.analyzer import analyze_repo, generate_mermaid, generate_learning_path, generate_dependency_graph
from app.services.llm_service import explain_code

app = FastAPI(title="Repo Insight MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 异步任务状态存储
task_store: dict[str, dict] = {}


@app.on_event("startup")
async def startup_cleanup():
    """启动时清理过期仓库和缓存。"""
    cleanup_old_repos(max_age_days=7)


@app.get("/")
def health():
    return {"status": "ok", "name": "Repo Insight MVP"}


@app.post("/api/analyze")
def analyze_start(req: AnalyzeRequest, bg: BackgroundTasks):
    """提交分析任务，立即返回 task_id，后台执行。"""
    task_id = str(uuid.uuid4())[:8]
    task_store[task_id] = {"status": "pending", "progress": "排队中...", "result": None, "error": None}
    bg.add_task(run_analysis, task_id, str(req.repo_url))
    return {"task_id": task_id}


def run_analysis(task_id: str, repo_url: str):
    """后台执行：clone → 分析 → 生成结果（带缓存）。"""
    try:
        task_store[task_id]["status"] = "running"

        task_store[task_id]["progress"] = "克隆仓库中..."
        repo_id, repo_path = clone_or_update(repo_url)
        commit_hash = get_commit_hash(repo_path)

        # 检查缓存
        cached = load_cache(repo_id, commit_hash)
        if cached:
            task_store[task_id] = {
                "status": "done",
                "progress": "完成（命中缓存）",
                "result": cached,
                "error": None,
            }
            logger.info(f"任务 {task_id} 命中缓存")
            return

        task_store[task_id]["progress"] = "扫描文件树..."
        tree = build_file_tree(repo_path)

        task_store[task_id]["progress"] = "分析代码结构..."
        files = analyze_repo(repo_path)

        task_store[task_id]["progress"] = "生成架构图..."
        mermaid = generate_mermaid(files)

        task_store[task_id]["progress"] = "生成学习路径..."
        learning_path = generate_learning_path(files)

        task_store[task_id]["progress"] = "生成依赖关系图..."
        dep_graph = generate_dependency_graph(repo_path)

        result = {
            "repo_id": repo_id,
            "tree": tree,
            "files": files,
            "mermaid": mermaid,
            "learning_path": learning_path,
            "dependency_graph": dep_graph,
        }

        # 保存缓存
        save_cache(repo_id, commit_hash, result)

        task_store[task_id] = {
            "status": "done",
            "progress": "完成",
            "result": result,
            "error": None,
        }
        logger.info(f"任务 {task_id} 完成，分析了 {len(files)} 个文件")

    except Exception as e:
        task_store[task_id] = {
            "status": "error",
            "progress": "失败",
            "result": None,
            "error": str(e),
        }
        logger.error(f"任务 {task_id} 失败: {e}")


@app.get("/api/analyze/{task_id}")
def get_task_status(task_id: str):
    """轮询任务状态和进度。"""
    task = task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@app.post("/api/explain")
async def explain(req: ExplainRequest):
    try:
        repo_path = get_repo_path(req.repo_id)
        code = read_file(repo_path, req.file_path)
        explanation = await explain_code(req.file_path, code)
        return {"file_path": req.file_path, "explanation": explanation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
