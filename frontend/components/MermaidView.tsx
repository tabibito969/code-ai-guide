'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import mermaid from 'mermaid';

function parseSvgSize(svg: string): { w: number; h: number } {
  const match = svg.match(/viewBox="([^"]+)"/);
  if (match) {
    const parts = match[1].split(/\s+/).map(Number);
    return { w: parts[2] || 800, h: parts[3] || 600 };
  }
  const w = Number(svg.match(/width="(\d+)"/)?.[1]) || 800;
  const h = Number(svg.match(/height="(\d+)"/)?.[1]) || 600;
  return { w, h };
}

export default function MermaidView({ chart }: { chart: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [zoomed, setZoomed] = useState(false);
  const [svgContent, setSvgContent] = useState('');
  const [svgSize, setSvgSize] = useState({ w: 800, h: 600 });

  useEffect(() => {
    mermaid.initialize({
      startOnLoad: false,
      theme: 'default',
      securityLevel: 'loose',
      fontFamily: 'Arial, Helvetica, sans-serif',
    });

    async function render() {
      if (!ref.current || !chart) return;
      ref.current.innerHTML = '';

      const id = `mermaid-${Math.random().toString(36).slice(2)}`;
      try {
        const { svg } = await mermaid.render(id, chart);
        ref.current.innerHTML = svg;
        setSvgContent(svg);
        setSvgSize(parseSvgSize(svg));
      } catch (e) {
        console.error('Mermaid render error:', e);
        ref.current.innerHTML = `<pre class="mermaid-error">${chart}</pre>`;
      }
    }

    render();
  }, [chart]);

  const close = useCallback(() => setZoomed(false), []);

  function downloadSvg() {
    if (!svgContent) return;
    const blob = new Blob([svgContent], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'architecture.svg';
    a.click();
    URL.revokeObjectURL(url);
  }

  function downloadPng() {
    if (!svgContent) return;
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    const svgBlob = new Blob([svgContent], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(svgBlob);

    img.onload = () => {
      canvas.width = svgSize.w * 2;
      canvas.height = svgSize.h * 2;
      ctx.fillStyle = 'white';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      const pngUrl = canvas.toDataURL('image/png');
      const a = document.createElement('a');
      a.href = pngUrl;
      a.download = 'architecture.png';
      a.click();
      URL.revokeObjectURL(url);
    };
    img.src = url;
  }

  useEffect(() => {
    if (!zoomed) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') close(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [zoomed, close]);

  const PAD = 64;
  const maxW = window.innerWidth * 0.92;
  const maxH = window.innerHeight * 0.88;
  const scale = Math.min(1, maxW / (svgSize.w + PAD), maxH / (svgSize.h + PAD));
  const modalW = Math.min(svgSize.w * scale + PAD, maxW);
  const modalH = Math.min(svgSize.h * scale + PAD, maxH);

  return (
    <>
      {svgContent && (
        <div className="mermaid-export">
          <button className="export-btn" onClick={downloadSvg}>下载 SVG</button>
          <button className="export-btn" onClick={downloadPng}>下载 PNG</button>
        </div>
      )}
      <div
        ref={ref}
        className="mermaid-container"
        onClick={() => svgContent && setZoomed(true)}
        style={{ cursor: svgContent ? 'zoom-in' : 'default' }}
      />      {zoomed && (
        <div className="mermaid-overlay" onClick={close}>
          <div
            className="mermaid-zoomed"
            style={{ width: modalW, height: modalH }}
            onClick={(e) => e.stopPropagation()}
          >
            <button className="mermaid-close" onClick={close}>✕</button>
            <div dangerouslySetInnerHTML={{ __html: svgContent }} />
          </div>
        </div>
      )}
    </>
  );
}
