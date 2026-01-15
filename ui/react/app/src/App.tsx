import { NavLink, Outlet } from 'react-router-dom';
import ErrorBanner from '@components/ErrorBanner';

export default function App() {
  return (
    <div className="app-root">
      <aside className="sidebar">
        <h1>EMG Force Bridge</h1>
        <nav>
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/visualization">Visualization</NavLink>
          <NavLink to="/calibration">Calibration</NavLink>
          <NavLink to="/logs">Logs</NavLink>
        </nav>
      </aside>
      <main className="content">
        <ErrorBanner />
        <Outlet />
      </main>
    </div>
  );
}
