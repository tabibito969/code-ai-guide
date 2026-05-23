from pydantic import BaseModel, HttpUrl
from typing import Any


class AnalyzeRequest(BaseModel):
    repo_url: HttpUrl


class ExplainRequest(BaseModel):
    repo_id: str
    file_path: str


class AnalyzeResponse(BaseModel):
    repo_id: str
    tree: list[dict[str, Any]]
    files: list[dict[str, Any]]
    mermaid: str
    learning_path: list[str]
    dependency_graph: str = ""