import { create } from 'zustand';
import type { LogItem, LogLevel } from '@api/types';

function uid() { return Math.random().toString(36).slice(2); }

const STORAGE_KEY = 'efb_logs_v1';

function loadPersisted(): LogItem[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    if (!Array.isArray(arr)) return [];
    return arr as LogItem[];
  } catch { return []; }
}

function persist(logs: LogItem[]) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(logs.slice(-1000))); } catch {}
}

export interface LogState {
  logs: LogItem[];
  add: (level: LogLevel, message: string, context?: Record<string, unknown>) => void;
  clear: () => void;
}

export const useLogStore = create<LogState>((set, get) => ({
  logs: loadPersisted(),
  add: (level, message, context) => set(() => {
    const item: LogItem = { id: uid(), ts: new Date().toISOString(), level, message, context };
    const next = [...get().logs, item];
    persist(next);
    return { logs: next };
  }),
  clear: () => set(() => { persist([]); return { logs: [] }; }),
}));

export function logInfo(message: string, context?: Record<string, unknown>) { useLogStore.getState().add('info', message, context); }
export function logWarn(message: string, context?: Record<string, unknown>) { useLogStore.getState().add('warn', message, context); }
export function logError(message: string, context?: Record<string, unknown>) { useLogStore.getState().add('error', message, context); }
