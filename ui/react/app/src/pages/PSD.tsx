import { useState } from 'react';
import Chart from '@components/Chart';
import { api } from '@api/client';
import { useDeviceStore } from '@state/deviceStore';
import { logError, logInfo } from '@state/logStore';

export default function PSD() {
  const { selectedChannel } = useDeviceStore();
  const [duration, setDuration] = useState(10);
  const [fs, setFs] = useState(1000);
  const [amp, setAmp] = useState(1.0);
  const [noise, setNoise] = useState(0.2);
  const [f1, setF1] = useState(80);
  const [f2, setF2] = useState(140);
  const [mnf, setMnf] = useState<number | null>(null);
  const [mdf, setMdf] = useState<number | null>(null);
  const [series, setSeries] = useState<{x:number;y:number}[]>([]);
  const [busy, setBusy] = useState(false);

  const runDemo = async () => {
    try {
      setBusy(true);
      const res = await api.demoSyntheticEmg({ duration_s: duration, fs, channel: selectedChannel, amplitude: amp, noise_std: noise, f1_hz: f1, f2_hz: f2 });
      logInfo('Synthetic EMG inserted', res);
      const start = new Date(res.start).toISOString();
      const end = new Date(res.end).toISOString();
      const out = await api.analyticsPsd(selectedChannel, start, end);
      setMnf(out.mnf); setMdf(out.mdf);
      const pts = (out.freqs as number[]).map((fx:number, i:number) => ({ x: fx, y: (out.psd as number[])[i] }));
      setSeries(pts);
    } catch (e) {
      logError('PSD demo failed', { error: String(e) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="vstack" style={{ gap: 16 }}>
      <div className="panel hstack" style={{ justifyContent:'space-between', alignItems:'center' }}>
        <div className="hstack" style={{ gap: 12, flexWrap:'wrap' as any }}>
          <label>Duration</label>
          <select value={duration} onChange={(e)=>setDuration(Number(e.target.value))}>
            <option value={5}>5s</option>
            <option value={10}>10s</option>
            <option value={20}>20s</option>
          </select>
          <label>Fs</label>
          <select value={fs} onChange={(e)=>setFs(Number(e.target.value))}>
            <option value={500}>500</option>
            <option value={1000}>1000</option>
            <option value={2000}>2000</option>
          </select>
          <label>Amp</label>
          <input className="input" type="number" step="0.1" value={amp} onChange={(e)=>setAmp(Number(e.target.value))} style={{ width: 80 }} />
          <label>Noise</label>
          <input className="input" type="number" step="0.1" value={noise} onChange={(e)=>setNoise(Number(e.target.value))} style={{ width: 80 }} />
          <label>f1</label>
          <input className="input" type="number" value={f1} onChange={(e)=>setF1(Number(e.target.value))} style={{ width: 80 }} />
          <label>f2</label>
          <input className="input" type="number" value={f2} onChange={(e)=>setF2(Number(e.target.value))} style={{ width: 80 }} />
        </div>
        <button className="btn" onClick={runDemo} disabled={busy}>{busy ? 'Running...' : 'Generate + Compute PSD'}</button>
      </div>
      <div className="grid cols-3">
        <div className="panel"><div style={{ fontSize:12, color:'#475569' }}>MNF</div><div style={{ fontWeight:600 }}>{mnf?.toFixed(1) ?? '—'} Hz</div></div>
        <div className="panel"><div style={{ fontSize:12, color:'#475569' }}>MDF</div><div style={{ fontWeight:600 }}>{mdf?.toFixed(1) ?? '—'} Hz</div></div>
        <div className="panel"><div style={{ fontSize:12, color:'#475569' }}>Points</div><div style={{ fontWeight:600 }}>{series.length}</div></div>
      </div>
      <Chart data={series} height={320} />
    </div>
  );
}
