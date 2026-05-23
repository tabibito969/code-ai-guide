# Repo Insight MVP

一个完全可运行的代码仓库智能理解系统 MVP。

功能：

- 输入 GitHub 仓库 URL
- 自动 clone 到本地
- 扫描目录结构
- 分析 Python / JavaScript / TypeScript 文件中的类、函数、import
- 生成 Mermaid 架构图
- 生成学习路径
- 支持接入 DeepSeek API 做代码解释
- 提供 Next.js 前端界面

## 环境要求

- **Python** 3.11 ~ 3.13（3.14 因 pydantic-core 兼容性问题暂不支持）
- **Node.js** 18+
- **Git**

## 一、启动后端

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（首次需要）
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY（可选，不填则返回本地静态解释）

# 启动
uvicorn app.main:app --reload --port 8000
```

后端地址：http://localhost:8000

## 二、启动前端

```bash
cd frontend
npm install
npm run dev
```

前端地址：http://localhost:3000

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
repo-insight-mvp/
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
      globals.css
    components/
      FileTree.tsx
      MermaidView.tsx
```
