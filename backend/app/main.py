from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models import AnalyzeRequest, AnalyzeResponse, ExplainRequest
from app.services.repo_service import clone_or_update, build_file_tree, get_repo_path, read_file
from app.services.analyzer import analyze_repo, generate_mermaid, generate_learning_path
from app.services.llm_service import explain_code

#FastAPI的实例化对象app
app = FastAPI(title="Code AI Guide")

#注册 CORS（跨域资源共享）中间件，让浏览器通过各种端口请求
app.add_middleware(
    CORSMiddleware, #FastAPI内置的CORS中间件
    allow_origins=["http://localhost:3000"],
    allow_credentials=True, #允许携带凭证信息
    allow_methods=["*"], #允许所有HTTP方法
    allow_headers=["*"], #允许自定义请求头
)

#装饰器 .get HTTP 的 GET 方法 / 根目录
@app.get("/")
def health():
    return {"status": "ok", "name": "Code AI Guide"}
#对后端进行健康检查
#HTTP 的 POST 方法
@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    try:
        repo_id, repo_path = clone_or_update(str(req.repo_url))
        tree = build_file_tree(repo_path)
        files = analyze_repo(repo_path)
        mermaid = generate_mermaid(files)
        learning_path = generate_learning_path(files)
        return AnalyzeResponse(
            repo_id=repo_id,
            tree=tree,
            files=files,
            mermaid=mermaid,
            learning_path=learning_path,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#async 关键字 定义异步函数
@app.post("/api/explain")
async def explain(req: ExplainRequest):
    try:
        repo_path = get_repo_path(req.repo_id)
        code = read_file(repo_path, req.file_path)
        explanation = await explain_code(req.file_path, code)
        return {"file_path": req.file_path, "explanation": explanation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
