# Data CSV schema

Each recording CSV should have the following columns:
- timestamp_s: float (seconds from start)
- value: int or float (raw ADC or scaled voltage)
- label: optional, short text label for supervised data rows

Example filename:
data/{subject_id}_{session_id}_{muscle}_{YYYYMMDD_HHMMSS}.csv

Store metadata in a JSON sidecar:
data/{subject_id}_{session_id}_{meta}.json
Fields:
- subject_id, session_id, muscle, sampling_rate_hz, electrode_positions, notes