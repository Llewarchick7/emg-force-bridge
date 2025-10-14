# Data Collection Protocol (short)

Purpose
- Collect labeled EMG recordings for basic contraction vs rest classification and calibration.

Setup
- Hardware: Arduino Uno, MyoWare 2.0, disposable Ag/AgCl electrodes, USB or battery power.
- Place reference electrode on a bony prominence (e.g., elbow crest), MyoWare electrodes on muscle belly (e.g., biceps), ground on nearby location.

Recording procedure (per session)
1. Participant signs docs/consent_form.md.
2. Clean skin with alcohol pad and allow to dry.
3. Attach electrodes per diagram (see README sketches).
4. Calibration: 5 seconds rest, 5 seconds maximal voluntary contraction (MVC).
5. Task: 10 repetitions of 3-second contraction with 5-second rest between reps.
6. Save each recording as CSV with metadata.

Metadata fields (save alongside CSV)
- subject_id (de-identified)
- session_id
- date_time_utc
- muscle
- electrode_positions (short note)
- sampling_rate_hz
- notes

Quality checks
- Check for expected amplitude during MVC.
- If signal is flat or noisy, re-prepare skin and reposition electrodes.

Data storage
- Store de-identified CSV files in data/ and maintain a local backup.