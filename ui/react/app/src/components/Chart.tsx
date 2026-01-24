import { useEffect, useRef } from 'react';

type Pt = { x: number; y: number };

type VLine = { x: number; color?: string };
export default function Chart({ data, color = '#2563eb', height = 180, xLabel, yLabel, vlines = [], yLog = false }:{ data: Pt[]; color?: string; height?: number; xLabel?: string; yLabel?: string; vlines?: VLine[]; yLog?: boolean; }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth * dpr;
    const h = height * dpr;
    canvas.width = width;
    canvas.height = h;
    ctx.clearRect(0,0,width,h);

    if (data.length === 0) return;

    const minX = data[0].x;
    const maxX = data[data.length-1].x;
    let minY = Infinity, maxY = -Infinity;
    const eps = 1e-12;
    const yVal = (y:number) => yLog ? Math.log10(Math.max(eps, y)) : y;
    for (const p of data) { const yy = yVal(p.y); if (yy < minY) minY = yy; if (yy > maxY) maxY = yy; }
    if (minY === maxY) { minY -= 1; maxY += 1; }

    const xToPx = (x:number) => ((x - minX)/(maxX - minX || 1)) * (width - 20) + 10;
    const yToPx = (y:number) => (1 - ((yVal(y) - minY)/(maxY - minY || 1))) * (h - 20) + 10;

    ctx.strokeStyle = '#e2e8f0';
    ctx.lineWidth = 1;
    // grid horizontal
    for (let i=0;i<=4;i++) {
      const y = 10 + i * (h-20)/4;
      ctx.beginPath(); ctx.moveTo(10, y); ctx.lineTo(width-10, y); ctx.stroke();
    }

    ctx.strokeStyle = color;
    ctx.lineWidth = 2 * dpr;
    ctx.beginPath();
    for (let i=0;i<data.length;i++) {
      const p = data[i];
      const x = xToPx(p.x); const y = yToPx(p.y);
      if (i === 0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
    }
    ctx.stroke();

    // Draw vertical reference lines
    if (vlines && vlines.length) {
      for (const v of vlines) {
        const x = xToPx(v.x);
        ctx.strokeStyle = v.color || '#0f172a';
        ctx.lineWidth = 1 * dpr;
        ctx.beginPath(); ctx.moveTo(x, 10); ctx.lineTo(x, h-10); ctx.stroke();
      }
    }
  }, [data, height]);

  return (
    <div className="panel">
      {(yLabel || xLabel) && (
        <div className="hstack" style={{ justifyContent:'space-between', marginBottom: 6 }}>
          <div style={{ fontSize: 12, color: '#475569' }}>{yLabel || ''}</div>
          <div style={{ fontSize: 12, color: '#475569' }}>{xLabel || ''}</div>
        </div>
      )}
      <canvas ref={canvasRef} style={{ width: '100%', height }} />
    </div>
  );
}
