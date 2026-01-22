import { useEffect, useMemo, useRef, useState } from 'react';
import DeviceStatus from '@components/DeviceStatus';
import Chart from '@components/Chart';
import { useDeviceStore } from '@state/deviceStore';
import { api } from '@api/client';

type EmgSample = {
  timestamp: string | number | Date;
  envelope?: number;
  rms?: number;
  rect?: number;
  raw?: number;
};

export default function Dashboard() {
  const { selectedChannel, pollLatest } = useDeviceStore();
  const stopRef = useRef<() => void>();
  const [series, setSeries] = useState<{ x: number; y: number }[]>([]);

  useEffect(() => {
    stopRef.current = pollLatest(500);
    return () => stopRef.current?.();
  }, [pollLatest, selectedChannel]);

  useEffect(() => {
    let active = true;
    const fetchRecent = async () => {
      const end = new Date();
      const start = new Date(end.getTime() - 20_000);
      const histRaw = await api.emgHistory(start.toISOString(), end.toISOString(), selectedChannel).catch(() => [] as unknown);
      const hist: EmgSample[] = Array.isArray(histRaw) ? (histRaw as EmgSample[]) : [];
      if (!active) return;
      const points = hist.map((s: EmgSample) => ({ x: new Date(s.timestamp).getTime(), y: s.envelope ?? s.rms ?? s.rect ?? s.raw ?? 0 }));
      setSeries(points);
    };
    fetchRecent();
    const t = setInterval(fetchRecent, 3000);
    return () => { active = false; clearInterval(t); };
  }, [selectedChannel]);

  const chartData = useMemo(() => series, [series]);

  return (
    <div className="vstack" style={{ gap: 16 }}>
      <DeviceStatus />
      <div className="grid cols-3">
        <div className="panel">
          <div style={{ fontSize: 12, color: '#475569' }}>Recent Window</div>
          <div style={{ fontWeight: 600 }}>20s</div>
        </div>
        <div className="panel">
          <div style={{ fontSize: 12, color: '#475569' }}>Samples</div>
          <div style={{ fontWeight: 600 }}>{chartData.length}</div>
        </div>
        <div className="panel">
          <div style={{ fontSize: 12, color: '#475569' }}>Display Metric</div>
          <div style={{ fontWeight: 600 }}>envelope/rms</div>
        </div>
      </div>
      <Chart data={chartData} height={220} />
    </div>
  );
}
