import { useState } from 'react';
import Chart from '@components/Chart';
import { api } from '@api/client';
import { useDeviceStore } from '@state/deviceStore';
import { logError, logInfo } from '@state/logStore';
import type { PSDResponse, SyntheticEmgResponse } from '@api/types';

export default function PSD() {
  const { selectedChannel } = useDeviceStore();
  const [duration, setDuration] = useState(10);
  const [fs, setFs] = useState(1000);
  const [amp, setAmp] = useState(1.0);
  const [noise, setNoise] = useState(0.2);
  const [f1, setF1] = useState(80);
  const [f2, setF2] = useState(140);
  const [method, setMethod] = useState<'fft'|'welch'>('welch');
  const [scale, setScale] = useState<'linear'|'log'>('log');
  const [nperseg, setNperseg] = useState(1024);
  const [noverlap, setNoverlap] = useState(512);
  const [windowFn, setWindowFn] = useState<'hann'|'hamming'|'blackman'|'boxcar'>('hann');
  const [nfft, setNfft] = useState<number | ''>('');
  const [detrend, setDetrend] = useState<'constant'|'linear'|'none'>('constant');
  const [welchScaling, setWelchScaling] = useState<'density'|'spectrum'>('density');
  const [average, setAverage] = useState<'mean'|'median'>('mean');
  const [fmin, setFmin] = useState<number | ''>('');
  const [fmax, setFmax] = useState<number | ''>('');
  const [mnf, setMnf] = useState<number | null>(null);
  const [mdf, setMdf] = useState<number | null>(null);
  const [series, setSeries] = useState<{x:number;y:number}[]>([]);
  const [busy, setBusy] = useState(false);

  const runDemo = async () => {
    try {
      setBusy(true);
      const res: SyntheticEmgResponse = await api.demoSyntheticEmg({ duration_s: duration, fs, channel: selectedChannel, amplitude: amp, noise_std: noise, f1_hz: f1, f2_hz: f2 });
      logInfo('Synthetic EMG inserted', { inserted: res.inserted, channel: res.channel });
      const start = new Date(res.start).toISOString();
      const end = new Date(res.end).toISOString();
      const out: PSDResponse = await api.analyticsPsd(selectedChannel, start, end, {
        method,
        window: windowFn,
        nperseg,
        noverlap,
        nfft: nfft === '' ? undefined : Number(nfft),
        detrend,
        scaling: welchScaling,
        average,
        fmin: fmin === '' ? undefined : Number(fmin),
        fmax: fmax === '' ? undefined : Number(fmax),
      });
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
        <div className="hstack" style={{ gap: 12, flexWrap:'wrap' }}>
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
          <label>PSD</label>
          <select value={method} onChange={(e)=>setMethod(e.target.value as any)}>
            <option value="fft">FFT</option>
            <option value="welch">Welch</option>
          </select>
          {method === 'welch' && (
            <>
              <label>window</label>
              <select value={windowFn} onChange={(e)=>setWindowFn(e.target.value as any)}>
                <option value="hann">hann</option>
                <option value="hamming">hamming</option>
                <option value="blackman">blackman</option>
                <option value="boxcar">boxcar</option>
              </select>
              <label>nperseg</label>
              <input className="input" type="number" value={nperseg} onChange={(e)=>setNperseg(Number(e.target.value))} style={{ width: 80 }} />
              <label>noverlap</label>
              <input className="input" type="number" value={noverlap} onChange={(e)=>setNoverlap(Number(e.target.value))} style={{ width: 80 }} />
              <label>nfft</label>
              <input className="input" type="number" value={nfft} onChange={(e)=>setNfft((e.target.value === '' ? '' : Number(e.target.value)) as any)} style={{ width: 80 }} placeholder="auto" />
              <label>detrend</label>
              <select value={detrend} onChange={(e)=>setDetrend(e.target.value as any)}>
                <option value="constant">constant</option>
                <option value="linear">linear</option>
                <option value="none">none</option>
              </select>
              <label>scaling</label>
              <select value={welchScaling} onChange={(e)=>setWelchScaling(e.target.value as any)}>
                <option value="density">density</option>
                <option value="spectrum">spectrum</option>
              </select>
              <label>average</label>
              <select value={average} onChange={(e)=>setAverage(e.target.value as any)}>
                <option value="mean">mean</option>
                <option value="median">median</option>
              </select>
              <label>fmin</label>
              <input className="input" type="number" value={fmin} onChange={(e)=>setFmin((e.target.value === '' ? '' : Number(e.target.value)) as any)} style={{ width: 80 }} placeholder="min Hz" />
              <label>fmax</label>
              <input className="input" type="number" value={fmax} onChange={(e)=>setFmax((e.target.value === '' ? '' : Number(e.target.value)) as any)} style={{ width: 80 }} placeholder="max Hz" />
            </>
          )}
          <label>Scale</label>
          <select value={scale} onChange={(e)=>setScale(e.target.value as any)}>
            <option value="linear">Linear</option>
            <option value="log">Log</option>
          </select>
        </div>
        <button className="btn" onClick={runDemo} disabled={busy}>{busy ? 'Running...' : 'Generate + Compute PSD'}</button>
      </div>
      <div className="grid cols-3">
        <div className="panel"><div style={{ fontSize:12, color:'#475569' }}>MNF</div><div style={{ fontWeight:600 }}>{mnf?.toFixed(1) ?? '—'} Hz</div></div>
        <div className="panel"><div style={{ fontSize:12, color:'#475569' }}>MDF</div><div style={{ fontWeight:600 }}>{mdf?.toFixed(1) ?? '—'} Hz</div></div>
        <div className="panel"><div style={{ fontSize:12, color:'#475569' }}>Points</div><div style={{ fontWeight:600 }}>{series.length}</div></div>
      </div>
      <Chart 
        data={series} 
        height={320} 
        xLabel="Frequency (Hz)" 
        yLabel={scale === 'log' ? 'PSD (log10)' : 'PSD (a.u.)'} 
        yLog={scale === 'log'} 
        vlines={[
          ...(mnf != null ? [{ x: mnf, color: '#10b981' }] : []),
          ...(mdf != null ? [{ x: mdf, color: '#ef4444' }] : []),
        ]}
      />
    </div>
  );
}
