'use client';

import { useState } from 'react';

const API_BASE = 'http://localhost:8000';

export type AnalyzeResult = {
  repo_id: string;
  tree: any[];
  files: any[];
  mermaid: string;
  learning_path: string[];
  dependency_graph: string;
};

export function useAnalyze() {
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState('');
  const [result, setResult] = useState<AnalyzeResult | null>(null);

  async function analyze(repoUrl: string) {
    setLoading(true);
    setProgress('提交任务...');
    setResult(null);

    try {
      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: repoUrl }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '提交失败');

      const { task_id } = data;
      const result = await pollTask(task_id);
      setResult(result);
      return result;
    } catch (err: any) {
      alert(err.message);
      return null;
    } finally {
      setLoading(false);
      setProgress('');
    }
  }

  async function pollTask(taskId: string): Promise<AnalyzeResult> {
    const maxWait = 300;
    const interval = 1500;
    let elapsed = 0;

    while (elapsed < maxWait * 1000) {
      const res = await fetch(`${API_BASE}/api/analyze/${taskId}`);
      const data = await res.json();

      if (data.status === 'done' && data.result) return data.result;
      if (data.status === 'error') throw new Error(data.error || '分析失败');

      setProgress(data.progress || '处理中...');
      await new Promise((r) => setTimeout(r, interval));
      elapsed += interval;
    }

    throw new Error('分析超时，请稍后重试');
  }

  return { loading, progress, result, analyze };
}
