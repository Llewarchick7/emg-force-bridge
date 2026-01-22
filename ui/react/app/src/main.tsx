import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import App from './App';
import Dashboard from './pages/Dashboard';
import Visualization from './pages/Visualization';
import Calibration from './pages/Calibration';
import Logs from './pages/Logs';
import PSD from './pages/PSD';
import './styles.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />}> 
          <Route index element={<Dashboard />} />
          <Route path="visualization" element={<Visualization />} />
          <Route path="calibration" element={<Calibration />} />
          <Route path="psd" element={<PSD />} />
          <Route path="logs" element={<Logs />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
