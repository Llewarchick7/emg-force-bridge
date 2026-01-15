import { useMemo } from 'react';
import { useDeviceStore } from '@state/deviceStore';

function timeAgo(ts?: string) {
  if (!ts) return '—';
  const d = Date.now() - new Date(ts).getTime();
  if (d < 2000) return 'just now';
  const s = Math.floor(d / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  return `${h}h ago`;
}

export default function DeviceStatus() {
  const { backendOnline, lastHealthTs, lastSample, channels, selectedChannel, setChannel } = useDeviceStore();
  const latestMetric = useMemo(() => {
    if (!lastSample) return '—';
    const v = lastSample.envelope ?? lastSample.rms ?? lastSample.rect ?? lastSample.raw ?? 0;
    return v.toFixed(3);
  }, [lastSample]);

  return (
    <div className="panel">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <div className="hstack" style={{ gap: 12 }}>
          <span className={`badge ${backendOnline ? 'ok' : 'err'}`}>{backendOnline ? 'Online' : 'Offline'}</span>
          <div className="vstack">
            <div style={{ fontWeight: 600 }}>Backend</div>
            <div style={{ fontSize: 12, color: '#475569' }}>Health: {timeAgo(lastHealthTs)}</div>
          </div>
        </div>
        <div className="hstack" style={{ gap: 12 }}>
          <div className="vstack">
            <div style={{ fontWeight: 600 }}>Channel</div>
            <select value={selectedChannel} onChange={(e) => setChannel(Number(e.target.value))}>
              {channels.map(c => <option key={c} value={c}>CH {c}</option>)}
            </select>
          </div>
          <div className="vstack">
            <div style={{ fontWeight: 600 }}>Latest</div>
            <div style={{ fontSize: 14, color: '#475569' }}>{latestMetric}</div>
          </div>
          <div className="vstack">
            <div style={{ fontWeight: 600 }}>Sample</div>
            <div style={{ fontSize: 12, color: '#475569' }}>{timeAgo(lastSample?.timestamp)}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
