# EMG-Force-Bridge

Goal
- Rapid prototyping of a low-cost EMG feedback device for physical therapists.
- Hardware target (v1): Arduino Uno + MyoWare 2.0 + disposable electrodes.
- Software target: streaming acquisition → preprocessing → live inference → simple feedback UI.
- Constraints: 1 hour/day development, heavy use of AI agents for boilerplate and tests.

Repo layout
- acquisition/      # Arduino sketches & serial reader
- emg/                 # reusable processing package (filters, envelopes, features, utils)
- models/           # training scripts & model artifacts
- ui/               # Streamlit demo and utilities
- data/             # recordings (CSV) & metadata (do not commit sensitive data)
- notebooks/        # exploratory notebooks
- docs/             # protocol, consent, outreach
- tests/            # unit tests
- .github/workflows # CI (pytest)
- NOTES.md          # daily 1-hour log

Quickstart
1. Install Python 3.10+, create a venv, pip install -r requirements.txt
2. Upload acquisition/arduino/emg_stream.ino to your Arduino Uno.
3. Connect MyoWare output to A0, ground and reference electrode on subject.
4. Run acquisition/serial_reader.py to view live data and save CSV.
5. Use the `emg.preprocessing` package for cleaning (e.g., `from emg.preprocessing.filters import apply_bandpass, apply_notch`); train a baseline model with models/train.py.
6. Run ui/unified_dashboard.py for the consolidated live & compare interface.

Safety & ethics
- Use a ground/reference electrode; do not place electrodes across the chest or near the heart in ways that could cause current loops.
- For all human tests, use docs/consent_form.md and record only de-identified data.

Daily workflow (1 hour/day)
- 5 min: Review NOTES.md
- 40 min: Focused task (one GitHub issue / one file)
- 10 min: Run a test or collect a short recording, commit & push
- 5 min: Log results & next microtasks in NOTES.md

Processing modules
- Filters: `emg/preprocessing/filters.py` (apply_bandpass, apply_notch, high/low-pass, streaming SOS)
- Envelopes: `emg/preprocessing/envelope.py` (sliding_rms, lowpass_envelope)
- Features: `emg/preprocessing/features.py` (estimate_fs, compute_metrics)
- The Streamlit UI imports these modules; avoid duplicating processing logic in UI code.

Signal Processing Overview
--------------------------
The EMG pipeline performs (optionally) band‑pass (20–450 Hz) and 60 Hz notch
filtering, full‑wave rectification, and envelope extraction (RMS window or
5 Hz low‑pass of rectified signal). Frequency metrics (Mean and Median
Frequency) are computed from an FFT‑based PSD. See `docs/dsp.md` for detailed
mathematical derivations and rationale behind each processing step.