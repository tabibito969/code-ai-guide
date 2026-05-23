'use client';

import { useState, useMemo } from 'react';

type TreeNode = {
  name: string;
  path: string;
  type: 'dir' | 'file';
  children?: TreeNode[];
};

export default function FileTree({ nodes, onSelect }: { nodes: TreeNode[]; onSelect: (path: string) => void }) {
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    if (!search.trim()) return nodes;
    const q = search.toLowerCase();
    return filterTree(nodes, q);
  }, [nodes, search]);

  return (
    <div>
      <input
        className="file-search"
        placeholder="搜索文件..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      <div className="tree-container">
        {filtered.length === 0 ? (
          <p className="tree-empty">没有匹配的文件</p>
        ) : (
          filtered.map((node) => <Node key={node.path} node={node} onSelect={onSelect} highlight={search} />)
        )}
      </div>
    </div>
  );
}

function filterTree(nodes: TreeNode[], query: string): TreeNode[] {
  return nodes
    .map((node) => {
      if (node.type === 'file') {
        return node.name.toLowerCase().includes(query) || node.path.toLowerCase().includes(query) ? node : null;
      }
      // 目录：递归过滤子节点
      const children = node.children ? filterTree(node.children, query) : [];
      if (children.length > 0 || node.name.toLowerCase().includes(query)) {
        return { ...node, children };
      }
      return null;
    })
    .filter(Boolean) as TreeNode[];
}

function highlightText(text: string, query: string) {
  if (!query) return text;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark>{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  );
}

function Node({ node, onSelect, highlight = '' }: { node: TreeNode; onSelect: (path: string) => void; highlight?: string }) {
  if (node.type === 'dir') {
    return (
      <div className="tree-node">
        <div className="tree-dir">📁 {highlightText(node.name, highlight)}</div>
        <div style={{ paddingLeft: 14 }}>
          {node.children?.map((child) => (
            <Node key={child.path} node={child} onSelect={onSelect} highlight={highlight} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="tree-node">
      <button className="tree-file" onClick={() => onSelect(node.path)}>
        📄 {highlightText(node.name, highlight)}
      </button>
    </div>
  );
}
