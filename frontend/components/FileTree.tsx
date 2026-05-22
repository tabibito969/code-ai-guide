'use client';

type TreeNode = {
  name: string;
  path: string;
  type: 'dir' | 'file';
  children?: TreeNode[];
};

export default function FileTree({ nodes, onSelect }: { nodes: TreeNode[]; onSelect: (path: string) => void }) {
  return <div className="tree-container">{nodes.map((node) => <Node key={node.path} node={node} onSelect={onSelect} />)}</div>;
}

function Node({ node, onSelect }: { node: TreeNode; onSelect: (path: string) => void }) {
  if (node.type === 'dir') {
    return (
      <div className="tree-node">
        <div className="tree-dir">📁 {node.name}</div>
        <div style={{ paddingLeft: 14 }}>
          {node.children?.map((child) => <Node key={child.path} node={child} onSelect={onSelect} />)}
        </div>
      </div>
    );
  }

  return (
    <div className="tree-node">
      <button className="tree-file" onClick={() => onSelect(node.path)}>📄 {node.name}</button>
    </div>
  );
}
