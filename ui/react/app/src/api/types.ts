export type EMGSample = {
  id: number;
  timestamp: string; // ISO
  channel: number;
  raw: number | null;
  rect: number | null;
  envelope: number | null;
  rms: number | null;
};

export type Health = { status: 'ok' | string };

export type LogLevel = 'info' | 'warn' | 'error';
export type LogItem = { id: string; ts: string; level: LogLevel; message: string; context?: Record<string, unknown> };
