import { useEffect, useMemo, useState } from 'react';
import Chart from '@components/Chart';
import { useDeviceStore } from '@state/deviceStore';
import { api } from '@api/client';

export default function Visualization() {
  const { selectedChannel, setChannel, channels } = useDeviceStore();
  const [duration, setDuration] = useState(60); // seconds
  const [series, setSeries] = useState<{ x: number; y: number }[]>([]);

  useEffect(() => {
    let active = true;
    const fetchRange = async () => {
      const end = new Date();
      const start = new Date(end.getTime() - duration * 1000);
      const hist = await api.emgHistory(start.toISOString(), end.toISOString(), selectedChannel).catch(() => [] as any[]);
      if (!active) return;
      const points = hist.map((s:any) => ({ x: new Date(s.timestamp).getTime(), y: s.envelope ?? s.rms ?? s.rect ?? s.raw ?? 0 }));
      setSeries(points);
    };
    fetchRange();
    const t = setInterval(fetchRange, 4000);
    return () => { active = false; clearInterval(t); };
  }, [selectedChannel, duration]);

  const data = useMemo(() => series, [series]);

  return (
    <div className="vstack" style={{ gap: 16 }}>
      <div className="panel hstack" style={{ justifyContent: 'space-between' }}>
        <div className="hstack" style={{ gap: 12 }}>
          <label>Channel</label>
          <select value={selectedChannel} onChange={(e) => setChannel(Number(e.target.value))}>
            {channels.map(c => <option key={c} value={c}>CH {c}</option>)}
          </select>
        </div>
        <div className="hstack" style={{ gap: 12 }}>
          <label>Window</label>
          <select value={duration} onChange={(e) => setDuration(Number(e.target.value))}>
            <option value={15}>15s</option>
            <option value={30}>30s</option>
            <option value={60}>60s</option>
            <option value={120}>120s</option>
          </select>
        </div>
      </div>
      <Chart data={data} height={360} />
    </div>
  );
}
