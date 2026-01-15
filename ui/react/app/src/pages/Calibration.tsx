import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useDeviceStore } from '@state/deviceStore';
import { api } from '@api/client';

function rms(values: number[]) {
  if (values.length === 0) return 0;
  const meanSq = values.reduce((s,v) => s + v*v, 0) / values.length;
  return Math.sqrt(meanSq);
}

const PERSIST_KEY = 'efb_calibration_v1';

export default function Calibration() {
  const { selectedChannel } = useDeviceStore();
  const [capturing, setCapturing] = useState(false);
  const [seconds, setSeconds] = useState(10);
  const [baseline, setBaseline] = useState<number | null>(() => {
    try { const raw = localStorage.getItem(PERSIST_KEY); if (!raw) return null; const obj = JSON.parse(raw); return obj?.[`ch_${selectedChannel}`] ?? null; } catch { return null; }
  });
  const [preview, setPreview] = useState<number | null>(null);
  const timerRef = useRef<number | null>(null);

  const capture = useCallback(async () => {
    const end = new Date();
    const start = new Date(end.getTime() - seconds * 1000);
    const hist = await api.emgHistory(start.toISOString(), end.toISOString(), selectedChannel).catch(() => [] as any[]);
    const vals = hist.map((s:any) => s.rms ?? s.envelope ?? s.rect ?? s.raw ?? 0);
    const b = rms(vals);
    setPreview(b);
  }, [selectedChannel, seconds]);

  useEffect(() => {
    if (!capturing) return; 
    capture();
    timerRef.current = window.setInterval(capture, 1000);
    return () => { if (timerRef.current) window.clearInterval(timerRef.current); };
  }, [capturing, capture]);

  const save = useCallback(() => {
    if (preview == null) return;
    setBaseline(preview);
    let obj: Record<string, number> = {};
    try { const raw = localStorage.getItem(PERSIST_KEY); obj = raw ? JSON.parse(raw) : {}; } catch {}
    obj[`ch_${selectedChannel}`] = preview;
    localStorage.setItem(PERSIST_KEY, JSON.stringify(obj));
  }, [preview, selectedChannel]);

  const threshold = useMemo(() => baseline != null ? baseline * 1.5 : null, [baseline]);

  return (
    <div className="vstack" style={{ gap: 16 }}>
      <div className="panel vstack">
        <div style={{ fontWeight: 600 }}>Baseline Calibration</div>
        <div style={{ color: '#475569', fontSize: 14 }}>Capture relaxed muscle activity as baseline RMS.</div>
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <div className="hstack" style={{ gap: 12 }}>
            <label>Duration</label>
            <select value={seconds} onChange={(e) => setSeconds(Number(e.target.value))}>
              <option value={5}>5s</option>
              <option value={10}>10s</option>
              <option value={20}>20s</option>
            </select>
          </div>
          <div className="hstack" style={{ gap: 8 }}>
            {!capturing && <button className="btn" onClick={() => setCapturing(true)}>Start</button>}
            {capturing && <button className="btn secondary" onClick={() => setCapturing(false)}>Stop</button>}
            <button className="btn" onClick={save} disabled={preview == null}>Save</button>
          </div>
        </div>
        <div className="grid cols-3" style={{ marginTop: 12 }}>
          <div>
            <div style={{ fontSize: 12, color: '#475569' }}>Preview RMS</div>
            <div style={{ fontWeight: 600 }}>{preview?.toFixed(4) ?? '—'}</div>
          </div>
          <div>
            <div style={{ fontSize: 12, color: '#475569' }}>Baseline RMS</div>
            <div style={{ fontWeight: 600 }}>{baseline?.toFixed(4) ?? '—'}</div>
          </div>
          <div>
            <div style={{ fontSize: 12, color: '#475569' }}>Suggested Threshold</div>
            <div style={{ fontWeight: 600 }}>{threshold?.toFixed(4) ?? '—'}</div>
          </div>
        </div>
      </div>
      <div className="panel" style={{ fontSize: 12, color: '#475569' }}>
        Note: Values are stored locally. Backend calibration endpoints can be wired later.
      </div>
    </div>
  );
}
