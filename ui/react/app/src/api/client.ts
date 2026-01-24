export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
// For demo convenience, default to backend's default dev key when not provided
const API_KEY = import.meta.env.VITE_API_KEY || 'dev-key';

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

import type { PSDResponse, SyntheticEmgResponse, SessionRead, SessionCreate, TrialRead, TrialCreate, NormalizedActivationResponse } from '@api/types';

export const api = {
  health: () => request<{ status: string }>(`/health`),
  emgLatest: (channel: number) => request(`/emg/latest?channel=${channel}`),
  emgHistory: (startISO: string, endISO: string, channel?: number) =>
    request(`/emg/history?start=${encodeURIComponent(startISO)}&end=${encodeURIComponent(endISO)}${typeof channel === 'number' ? `&channel=${channel}` : ''}`),
  analyticsActivation: (channel: number, startISO: string, endISO: string, threshold = 0.1) =>
    request(`/analytics/activation?channel=${channel}&start=${encodeURIComponent(startISO)}&end=${encodeURIComponent(endISO)}&threshold=${threshold}`),
  analyticsRms: (channel: number, startISO: string, endISO: string) =>
    request(`/analytics/rms?channel=${channel}&start=${encodeURIComponent(startISO)}&end=${encodeURIComponent(endISO)}`),
  analyticsPsd: (
    channel: number,
    startISO: string,
    endISO: string,
    opts?: {
      method?: 'fft'|'welch';
      window?: string;
      nperseg?: number;
      noverlap?: number;
      nfft?: number;
      detrend?: 'constant'|'linear'|'none';
      return_onesided?: boolean;
      scaling?: 'density'|'spectrum';
      average?: 'mean'|'median';
      fmin?: number;
      fmax?: number;
    }
  ): Promise<PSDResponse> => {
    const q = new URLSearchParams({
      channel: String(channel),
      start: startISO,
      end: endISO,
      ...(opts?.method ? { method: opts.method } : {}),
      ...(opts?.window ? { window: opts.window } : {}),
      ...(opts?.nperseg ? { nperseg: String(opts.nperseg) } : {}),
      ...(opts?.noverlap ? { noverlap: String(opts.noverlap) } : {}),
      ...(opts?.nfft ? { nfft: String(opts.nfft) } : {}),
      ...(opts?.detrend ? { detrend: opts.detrend } : {}),
      ...(opts?.return_onesided != null ? { return_onesided: String(opts.return_onesided) } : {}),
      ...(opts?.scaling ? { scaling: opts.scaling } : {}),
      ...(opts?.average ? { average: opts.average } : {}),
      ...(opts?.fmin != null ? { fmin: String(opts.fmin) } : {}),
      ...(opts?.fmax != null ? { fmax: String(opts.fmax) } : {}),
    }).toString();
    return request<PSDResponse>(`/analytics/psd?${q}`);
  },
  demoSyntheticEmg: (body: {
    duration_s?: number; fs?: number; channel?: number; amplitude?: number; noise_std?: number; f1_hz?: number; f2_hz?: number;
  }): Promise<SyntheticEmgResponse> => request<SyntheticEmgResponse>(`/demo/synthetic/emg`, 'POST', body),
  // Clinical session/trial endpoints
  createSession: (payload: SessionCreate): Promise<SessionRead> => request<SessionRead>(`/sessions`, 'POST', payload),
  createTrial: (sessionId: number, payload: TrialCreate): Promise<TrialRead> => request<TrialRead>(`/sessions/${sessionId}/trials`, 'POST', payload),
  setTrialMVC: (trialId: number, mvc_rms_uv: number): Promise<TrialRead> => request<TrialRead>(`/sessions/trials/${trialId}/mvc`, 'POST', { mvc_rms_uv }),
  setTrialBaseline: (trialId: number, baseline_rms_uv: number): Promise<TrialRead> => request<TrialRead>(`/sessions/trials/${trialId}/baseline`, 'POST', { baseline_rms_uv }),
  getTrialNormalized: (trialId: number, startISO: string, endISO: string): Promise<NormalizedActivationResponse> =>
    request<NormalizedActivationResponse>(`/sessions/trials/${trialId}/normalized?start=${encodeURIComponent(startISO)}&end=${encodeURIComponent(endISO)}`),
};
