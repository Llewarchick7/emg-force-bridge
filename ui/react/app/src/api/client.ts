export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY || '';

async function request<T>(path: string, method: HttpMethod = 'GET', body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(API_KEY ? { 'x-api-key': API_KEY } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    const err: any = new Error(`API ${method} ${path} failed ${res.status}: ${text}`);
    err.status = res.status;
    err.body = text;
    throw err;
  }
  return res.json();
}

export const api = {
  health: () => request<{ status: string }>(`/health`),
  emgLatest: (channel: number) => request(`/emg/latest?channel=${channel}`),
  emgHistory: (startISO: string, endISO: string, channel?: number) =>
    request(`/emg/history?start=${encodeURIComponent(startISO)}&end=${encodeURIComponent(endISO)}${typeof channel === 'number' ? `&channel=${channel}` : ''}`),
  analyticsActivation: (channel: number, startISO: string, endISO: string, threshold = 0.1) =>
    request(`/analytics/activation?channel=${channel}&start=${encodeURIComponent(startISO)}&end=${encodeURIComponent(endISO)}&threshold=${threshold}`),
  analyticsRms: (channel: number, startISO: string, endISO: string) =>
    request(`/analytics/rms?channel=${channel}&start=${encodeURIComponent(startISO)}&end=${encodeURIComponent(endISO)}`),
};
