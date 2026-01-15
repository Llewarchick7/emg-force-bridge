# EMG Force Bridge UI

Minimal, clinical-facing web UI for device status, data visualization, calibration, and logs.

## Features

- Dashboard: backend health, latest sample, quick metrics
- Visualization: time window plot for selected channel
- Calibration: baseline RMS capture and local threshold suggestion
- Logs: error/events with export for audit

## Quick Start

1) Install dependencies

```bash
cd ui/react/app
npm install
```

2) Configure environment (optional)

```bash
cp .env.example .env
# edit VITE_API_BASE and VITE_API_KEY as needed
```

3) Run the dev server

```bash
npm run dev
```

The app will start on http://localhost:5173.

Backend API defaults to http://localhost:8000.

## Notes

- Realtime streaming can be upgraded to WebSocket when backend route is ready.
- Calibration values are stored in localStorage for now; backend endpoint can be added later.
- Logs persist locally and can be exported as JSON for clinical compliance workflows.
