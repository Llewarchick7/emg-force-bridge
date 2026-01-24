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

export type PSDResponse = {
  freqs: number[];
  psd: number[];
  mnf: number;
  mdf: number;
};

export type SyntheticEmgResponse = {
  inserted: number;
  channel: number;
  start: string; // ISO datetime
  end: string;   // ISO datetime
};

// Clinical hierarchy types
export type PatientProfile = {
  id?: number;
  name: string;
  injury_side?: string | null; // 'left' | 'right'
  created_at?: string;
};

export type SessionRead = {
  id: number;
  patient_id: number;
  started_at: string;
  ended_at?: string | null;
  notes?: string | null;
};

export type SessionCreate = {
  patient_id: number;
  started_at?: string;
  notes?: string | null;
};

export type TrialRead = {
  id: number;
  session_id: number;
  name: string;
  channel: number;
  limb?: string | null; // 'affected' | 'healthy'
  movement_type?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  baseline_rms_uv?: number | null;
  mvc_rms_uv?: number | null;
};

export type TrialCreate = {
  session_id: number;
  name: string;
  channel: number;
  limb?: string | null;
  movement_type?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  baseline_rms_uv?: number | null;
  mvc_rms_uv?: number | null;
};

export type NormalizedActivationResponse = {
  percent_mvc: number;
  rms_uv: number;
  mvc_rms_uv: number;
  baseline_rms_uv?: number | null;
  start: string;
  end: string;
};
