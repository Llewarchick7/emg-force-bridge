import { create } from 'zustand';
import { api } from '@api/client';
import type { EMGSample } from '@api/types';
import { logError, logInfo } from './logStore';

export interface DeviceState {
  backendOnline: boolean;
  lastHealthTs?: string;
  lastSample?: EMGSample;
  selectedChannel: number;
  channels: number[];
  setChannel: (ch: number) => void;
  checkHealth: () => Promise<void>;
  pollLatest: (intervalMs?: number) => () => void;
}

export const useDeviceStore = create<DeviceState>((set, get) => ({
  backendOnline: false,
  selectedChannel: 0,
  channels: [0,1,2,3],
  setChannel: (ch) => set({ selectedChannel: ch }),
  checkHealth: async () => {
    try {
      const res = await api.health();
      set({ backendOnline: res.status === 'ok', lastHealthTs: new Date().toISOString() });
    } catch (e) {
      set({ backendOnline: false });
      logError('Health check failed', { error: String(e) });
    }
  },
  pollLatest: (intervalMs = 500) => {
    let active = true;
    const tick = async () => {
      const ch = get().selectedChannel;
      try {
        const sample = await api.emgLatest(ch);
        if (!active) return;
        set({ lastSample: sample, backendOnline: true });
      } catch (e) {
        set({ backendOnline: false });
      }
      if (active) setTimeout(tick, intervalMs);
    };
    tick();
    logInfo('Started latest-sample polling');
    return () => { active = false; logInfo('Stopped latest-sample polling'); };
  },
}));
