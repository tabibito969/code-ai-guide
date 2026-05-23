'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import FileTree from '../components/FileTree';
import MermaidView from '../components/MermaidView';
import ThemeToggle from '../components/ThemeToggle';
import { useAnalyze } from '../hooks/useAnalyze';
import { useExplain } from '../hooks/useExplain';
import { useHistory } from '../hooks/useHistory';
import './globals.css';

export default function HomePage() {
  const [repoUrl, setRepoUrl] = useState('https://github.com/tiangolo/fastapi');
  const { loading, progress, result, analyze } = useAnalyze();
  const { selectedFile, explanation, explain, clear } = useExplain();
  const { history, addHistory, clearHistory } = useHistory();

  async function handleAnalyze() {
    clear();
    const res = await analyze(repoUrl);
    if (res) {
      addHistory({ repoUrl, repoId: res.repo_id, timestamp: Date.now() });
    }
  }

  function selectFromHistory(url: string) {
    setRepoUrl(url);
  }

  function handleExplain(path: string) {
    if (!result) return;
    explain(result.repo_id, path);
  }

  return (
    <main className="container">
      <section className="header">
        <div className="header-text">
          <h1>Repo Insight MVP</h1>
          <p>输入 GitHub 仓库 URL，生成文件树、架构图、学习路径和 AI 代码解释。</p>
        </div>
        <ThemeToggle />
      </section>

      <section className="card form">
        <input value={repoUrl} onChange={(e) => setRepoUrl(e.target.value)} placeholder="GitHub repository URL" />
        <button className="primary-btn" onClick={handleAnalyze} disabled={loading}>
          {loading ? progress || '分析中...' : '开始分析'}
        </button>
      </section>

      {history.length > 0 && (
        <section className="card history-section">
          <div className="history-header">
            <h3>历史记录</h3>
            <button className="history-clear" onClick={clearHistory}>清空</button>
          </div>
          <div className="history-list">
            {history.map((item) => (
              <button
                key={item.repoUrl}
                className="history-item"
                onClick={() => selectFromHistory(item.repoUrl)}
              >
                <span className="history-url">{item.repoUrl.replace('https://github.com/', '')}</span>
                <span className="history-time">
                  {new Date(item.timestamp).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                </span>
              </button>
            ))}
          </div>
        </section>
      )}

      {result && (
        <section className="grid">
          <div className="card">
            <h2>文件树</h2>
            <FileTree nodes={result.tree} onSelect={handleExplain} />
          </div>

          <div className="card">
            <h2>架构图</h2>
            <MermaidView chart={result.mermaid} />
            {result.dependency_graph && (
              <>
                <h2>依赖关系</h2>
                <MermaidView chart={result.dependency_graph} />
              </>
            )}
            <h2>学习路径</h2>
            <ol>
              {result.learning_path.map((p) => (
                <li key={p}>
                  <button className="tree-file" onClick={() => handleExplain(p)}>
                    {p}
                  </button>
                </li>
              ))}
            </ol>
          </div>

          <div className="card">
            <h2>代码解释</h2>
            {selectedFile && (
              <>
                <p>
                  <span className="badge">{selectedFile}</span>
                </p>
                {(() => {
                  const fileInfo = result.files.find((f: any) => f.path === selectedFile);
                  if (!fileInfo) return null;
                  return (
                    <div className="file-metrics">
                      <span>📏 {fileInfo.total_lines ?? '?'} 行</span>
                      <span>📝 {fileInfo.functions?.length ?? 0} 函数</span>
                      <span>🏗️ {fileInfo.classes?.length ?? 0} 类</span>
                      <span>📦 {fileInfo.imports?.length ?? 0} 依赖</span>
                    </div>
                  );
                })()}
              </>
            )}
            <div className="markdown-content">
              {explanation ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{explanation}</ReactMarkdown>
              ) : (
                <p>点击左侧文件或学习路径开始解释。</p>
              )}
            </div>
          </div>
        </section>
      )}
    </main>
  );
}
