# Code AI Guide

一个完全可运行的代码仓库智能理解系统。

功能：

- 输入 GitHub 仓库 URL
- 自动 clone 到本地
- 扫描目录结构
- 分析 Python / JavaScript / TypeScript 文件中的类、函数、import
- 生成 Mermaid 架构图
- 生成学习路径
- 支持接入 DeepSeek API 做代码解释
- 提供 Next.js 前端界面

## 一、启动后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows 用 .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

后端地址：

```text
http://localhost:8000
```

## 二、启动前端

```bash
cd frontend
npm install
npm run dev
```

前端地址：

```text
http://localhost:3000
```

## 三、DeepSeek 配置

编辑：

```text
backend/.env
```

填入：

```text
DEEPSEEK_API_KEY=你的 key
```

如果不填，系统会返回本地静态解释，不影响运行。

## 四、主要接口

### 分析仓库

```http
POST /api/analyze
```

请求：

```json
{
  "repo_url": "https://github.com/fastapi/fastapi"
}
```

### 解释文件

```http
POST /api/explain
```

请求：

```json
{
  "repo_id": "生成的 repo_id",
  "file_path": "app/main.py"
}
```

## 五、项目结构

```text
code-ai-guide/
  backend/
    app/
      main.py
      models.py
      services/
        repo_service.py
        analyzer.py
        llm_service.py
  frontend/
    app/
      page.tsx
      layout.tsx
      globals.css
    components/
      FileTree.tsx
      MermaidView.tsx
```
