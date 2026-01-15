import { useEffect } from 'react';
import { useDeviceStore } from '@state/deviceStore';

export default function ErrorBanner() {
  const backendOnline = useDeviceStore(s => s.backendOnline);
  const checkHealth = useDeviceStore(s => s.checkHealth);

  useEffect(() => {
    checkHealth();
    const t = setInterval(checkHealth, 5000);
    return () => clearInterval(t);
  }, [checkHealth]);

  if (backendOnline) return null;
  return (
    <div className="panel" style={{ borderColor: '#fecaca', background: '#fee2e2', marginBottom: 16 }}>
      <strong style={{ color: '#991b1b' }}>Backend Offline:</strong> Unable to reach the API. Check server status and network.
    </div>
  );
}
