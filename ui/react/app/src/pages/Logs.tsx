import { useLogStore } from '@state/logStore';

export default function Logs() {
  const { logs, clear } = useLogStore();

  const exportLogs = () => {
    const blob = new Blob([JSON.stringify(logs, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `logs-${new Date().toISOString()}.json`; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="vstack" style={{ gap: 16 }}>
      <div className="panel hstack" style={{ justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontWeight: 600 }}>System Logs</div>
          <div style={{ fontSize: 12, color: '#475569' }}>Error states and events for clinical audit.</div>
        </div>
        <div className="hstack" style={{ gap: 8 }}>
          <button className="btn secondary" onClick={exportLogs} disabled={logs.length === 0}>Export</button>
          <button className="btn" onClick={clear} disabled={logs.length === 0}>Clear</button>
        </div>
      </div>
      <div className="panel" style={{ overflow: 'auto' }}>
        <table className="table">
          <thead>
            <tr>
              <th style={{ width: 220 }}>Timestamp</th>
              <th style={{ width: 90 }}>Level</th>
              <th>Message</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {logs.slice().reverse().map(l => (
              <tr key={l.id}>
                <td>{new Date(l.ts).toLocaleString()}</td>
                <td>{l.level.toUpperCase()}</td>
                <td>{l.message}</td>
                <td style={{ fontFamily: 'monospace', fontSize: 12, whiteSpace: 'pre-wrap' }}>
                  {l.context ? JSON.stringify(l.context) : ''}
                </td>
              </tr>
            ))}
            {logs.length === 0 && (
              <tr><td colSpan={4} style={{ color: '#475569' }}>No logs yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
