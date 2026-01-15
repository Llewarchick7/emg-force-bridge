import { useEffect, useRef } from 'react';

type Pt = { x: number; y: number };

export default function Chart({ data, color = '#2563eb', height = 180 }:{ data: Pt[]; color?: string; height?: number; }) {
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
    for (const p of data) { if (p.y < minY) minY = p.y; if (p.y > maxY) maxY = p.y; }
    if (minY === maxY) { minY -= 1; maxY += 1; }

    const xToPx = (x:number) => ((x - minX)/(maxX - minX || 1)) * (width - 20) + 10;
    const yToPx = (y:number) => (1 - (y - minY)/(maxY - minY)) * (h - 20) + 10;

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
  }, [data, height]);

  return <div className="panel"><canvas ref={canvasRef} style={{ width: '100%', height }} /></div>;
}
