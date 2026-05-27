'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import FileTree from '../components/FileTree';
import MermaidView from '../components/MermaidView';
import './globals.css';

type LearningPathItem = {
  file_path: string;
  stage: string;
  stage_order: number;
  priority: number;
  description: string;
};

type AnalyzeResult = {
  repo_id: string;
  tree: any[];
  files: any[];
  mermaid: string;
  learning_path: LearningPathItem[];
};

const API_BASE = 'http://localhost:8000';

export default function HomePage() {
  const [repoUrl, setRepoUrl] = useState('https://github.com/tiangolo/fastapi');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [selectedFile, setSelectedFile] = useState('');
  const [explanation, setExplanation] = useState('');

  async function analyze() {
    setLoading(true);
    setExplanation('');
    setSelectedFile('');
    try {
      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: repoUrl }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Analyze failed');
      setResult(data);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function explain(path: string) {
    if (!result) return;
    setSelectedFile(path);
    setExplanation('解释生成中...');
    try {
      const res = await fetch(`${API_BASE}/api/explain`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_id: result.repo_id, file_path: path }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Explain failed');
      setExplanation(data.explanation);
    } catch (err: any) {
      setExplanation(err.message);
    }
  }

  function groupByStage(items: LearningPathItem[]) {
    const groups: { stage: string; items: LearningPathItem[] }[] = [];
    const seen = new Set<string>();
    for (const item of items) {
      if (!seen.has(item.stage)) {
        seen.add(item.stage);
        groups.push({ stage: item.stage, items: [] });
      }
      groups[groups.length - 1].items.push(item);
    }
    return groups;
  }

  function shortName(filePath: string): string {
    const parts = filePath.replace(/\\/g, '/').split('/');
    return parts.length <= 2 ? filePath : parts.slice(-2).join('/');
  }

  return (
    <main className="container">
      <section className="header">
        <h1>Code AI Guide</h1>
        <p>输入 GitHub 仓库 URL，生成文件树、架构图、学习路径和 AI 代码解释。</p>
      </section>

      <section className="card form">
        <input value={repoUrl} onChange={(e) => setRepoUrl(e.target.value)} placeholder="GitHub repository URL" />
        <button className="primary-btn" onClick={analyze} disabled={loading}>{loading ? '分析中' : '开始分析'}</button>
      </section>

      {result && (
        <section className="grid">
          <div className="card">
            <h2>文件树</h2>
            <FileTree nodes={result.tree} onSelect={explain} />
          </div>

          <div className="card">
            <h2>架构图</h2>
            <MermaidView chart={result.mermaid} />
            <h2>学习路径</h2>
            <div className="learning-path">
              {groupByStage(result.learning_path).map((group) => (
                <div key={group.stage} className="path-stage">
                  <h3 className="path-stage-title">
                    <span className="stage-dot" />
                    {group.stage}
                  </h3>
                  <ol className="path-list">
                    {group.items.map((item) => (
                      <li key={item.file_path} className="path-item">
                        <button
                          className="tree-file path-file-btn"
                          onClick={() => explain(item.file_path)}
                        >
                          {shortName(item.file_path)}
                        </button>
                        <span className="path-desc">{item.description}</span>
                        <span className="path-priority" title="优先级分数">
                          {item.priority}
                        </span>
                      </li>
                    ))}
                  </ol>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <h2>代码解释</h2>
            {selectedFile && <p><span className="badge">{selectedFile}</span></p>}
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
