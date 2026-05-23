'use client';

import { useState } from 'react';

const API_BASE = 'http://localhost:8000';

export function useExplain() {
  const [selectedFile, setSelectedFile] = useState('');
  const [explanation, setExplanation] = useState('');
  const [loading, setLoading] = useState(false);

  async function explain(repoId: string, filePath: string) {
    setSelectedFile(filePath);
    setExplanation('解释生成中...');
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/explain`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_id: repoId, file_path: filePath }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Explain failed');
      setExplanation(data.explanation);
    } catch (err: any) {
      setExplanation(err.message);
    } finally {
      setLoading(false);
    }
  }

  function clear() {
    setSelectedFile('');
    setExplanation('');
  }

  return { selectedFile, explanation, loading, explain, clear };
}
