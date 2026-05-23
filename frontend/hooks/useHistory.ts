'use client';

import { useState, useEffect } from 'react';

export type HistoryItem = {
  repoUrl: string;
  repoId: string;
  timestamp: number;
};

const STORAGE_KEY = 'repo-insight-history';
const MAX_HISTORY = 20;

export function useHistory() {
  const [history, setHistory] = useState<HistoryItem[]>([]);

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        setHistory(JSON.parse(saved));
      } catch {}
    }
  }, []);

  function addHistory(item: HistoryItem) {
    setHistory((prev) => {
      // 去重：移除相同 repoUrl 的旧记录
      const filtered = prev.filter((h) => h.repoUrl !== item.repoUrl);
      const next = [item, ...filtered].slice(0, MAX_HISTORY);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }

  function clearHistory() {
    setHistory([]);
    localStorage.removeItem(STORAGE_KEY);
  }

  return { history, addHistory, clearHistory };
}
