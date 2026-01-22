"""Unified Streamlit EMG dashboard.

Provides two views:
1. Live Monitor – acquisition, filtering (band‑pass, notch), rectification,
    envelope (RMS or low‑pass), metrics (RMS, iEMG, MNF, MDF, SNR, clipping),
    spectrogram, markers, recording & buffer export.
2. Compare Sessions – load two CSV recordings, window selection, feature
    extraction (peak envelope, iEMG, time‑to‑peak, MDF), symmetry index, overlay.

Processing Chain (Live)
-----------------------
Raw ADC codes -> scale to volts -> (optional) band‑pass -> (optional) notch ->
center -> rectification -> envelope -> metrics.

Key Equations
-------------
Rectification: :math:`r[n] = |x[n]|`
RMS Envelope: :math:`e_{RMS}[n] = \sqrt{\frac{1}{N} \sum_{k=n-N/2}^{n+N/2} r[k]^2}`
Integrated EMG: :math:`iEMG = \sum_n e[n] \Delta t`
Mean Frequency: :math:`MNF = \frac{\sum_k f_k P[k]}{\sum_k P[k]}`
Median Frequency: smallest :math:`f_m` with cumulative power >= 50%.

Resilience & UX Notes
---------------------
All processing guardrails return passthrough on invalid parameters to keep the
UI responsive under misconfiguration (e.g. HP >= LP). Auto‑refresh rate is
throttled to balance latency and CPU usage.
""" 
import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plots import plot_time_series, plot_psd, plot_spectrogram
from api_client import fetch_latest, fetch_latest_status, post_sample
import time
import threading
from collections import deque
import serial
import serial.tools.list_ports
import pandas as pd
from pathlib import Path
from datetime import datetime
import os
from emg.preprocessing.filters import apply_bandpass, apply_notch
from emg.preprocessing.envelope import sliding_rms, lowpass_envelope
from emg.preprocessing.features import estimate_fs, compute_metrics

# Optional: attach Streamlit context to background thread (avoids warnings)
try:
    from streamlit.runtime.scriptrunner import add_script_run_ctx as _add_run_ctx
except Exception:
    _add_run_ctx = None

st.set_page_config(page_title="EMG Unified Dashboard", page_icon="⚡", layout="wide")

# ------------------------------
# Shared helpers
# ------------------------------

def list_ports():
    ports = serial.tools.list_ports.comports()
    return [p.device for p in ports]

# ------------------------------------------------------------------------------------------
# Live Monitor Tab
# Namespaced session-state keys with 'live_' to avoid collisions
# ------------------------------------------------------------------------------------------

# Initialize session state variables
# Track live data buffer, serial thread, recording state, etc.
if 'live_data_buffer' not in st.session_state:
    st.session_state.live_data_buffer = deque(maxlen=10000) # ~10s window of data, assuming 1kHz fs
if 'live_serial_thread' not in st.session_state:
    st.session_state.live_serial_thread = None
if 'live_source' not in st.session_state:
    st.session_state.live_source = 'Serial'
if 'live_backend_thread' not in st.session_state:
    st.session_state.live_backend_thread = None
if 'live_backend_base' not in st.session_state:
    st.session_state.live_backend_base = 'http://localhost:8000'
if 'live_backend_api_key' not in st.session_state:
    st.session_state.live_backend_api_key = ''
if 'live_backend_channel' not in st.session_state:
    st.session_state.live_backend_channel = 0
if 'live_stop' not in st.session_state:
    st.session_state.live_stop = False
if 'live_ser' not in st.session_state:
    st.session_state.live_ser = None
if 'live_recording' not in st.session_state:
    st.session_state.live_recording = False
if 'live_record_file' not in st.session_state:
    st.session_state.live_record_file = None
if 'live_record_path' not in st.session_state:
    st.session_state.live_record_path = None
if 'live_last_error' not in st.session_state:
    st.session_state.live_last_error = ""
if 'live_vref' not in st.session_state:
     st.session_state.live_vref = 5.0  # Arduino Uno default reference (Vcc)
if 'live_adc_max' not in st.session_state:
     st.session_state.live_adc_max = 1023.0  # 10-bit ADC max code
if 'live_markers' not in st.session_state:
    st.session_state.live_markers = []  # list of dicts {time: float, label: str}
if 'live_gain' not in st.session_state:
    st.session_state.live_gain = 1.0
# removed battery UI/state (not functional with current Arduino stream)
if 'live_session_name' not in st.session_state:
    st.session_state.live_session_name = f"emg_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
if 'live_last_sample_wall' not in st.session_state:
    st.session_state.live_last_sample_wall = None

# ------------------------------------------------------------------------------------------
# Simple FFT Demo Tab (minimal, backend-only)
# Namespaced session-state keys with 'simple_' to avoid collisions
# ------------------------------------------------------------------------------------------

if 'simple_data_buffer' not in st.session_state:
    st.session_state.simple_data_buffer = deque(maxlen=10000)  # ~10–12s at 860 Hz
if 'simple_backend_thread' not in st.session_state:
    st.session_state.simple_backend_thread = None
if 'simple_backend_base' not in st.session_state:
    st.session_state.simple_backend_base = 'http://localhost:8000'
if 'simple_backend_api_key' not in st.session_state:
    st.session_state.simple_backend_api_key = 'dev-key'
if 'simple_backend_channel' not in st.session_state:
    st.session_state.simple_backend_channel = 0
if 'simple_stop' not in st.session_state:
    st.session_state.simple_stop = False
if 'simple_last_error' not in st.session_state:
    st.session_state.simple_last_error = ""
if 'simple_last_sample_wall' not in st.session_state:
    st.session_state.simple_last_sample_wall = None


def render_simple_fft_demo():
    st.subheader("🎯 Simple FFT-Focused Demo")
    st.caption("Fixed sampling rate: 860 Hz · Band-pass: 20–450 Hz · Envelope LPF/RMS: 5 Hz / 0.10 s")

    # Controls
    c1, c2, c3, c4, c5 = st.columns([1.8, 1.6, 1.0, 0.9, 0.9])
    with c1:
        st.text_input("Base URL", key="simple_backend_base")
    with c2:
        st.text_input("API Key", key="simple_backend_api_key")
    with c3:
        st.number_input("Channel", min_value=0, max_value=16, step=1, key="simple_backend_channel")
    with c4:
        time_window = st.slider("Window (s)", 1, 8, 3)
    with c5:
        started = st.session_state.simple_backend_thread and st.session_state.simple_backend_thread.is_alive()
        can_start = len(str(st.session_state.simple_backend_base).strip()) > 0
        if st.button("🟢 START", use_container_width=True, disabled=(started or not can_start)):
            st.session_state.simple_stop = False
            st.session_state.simple_data_buffer.clear()
            st.session_state.simple_last_error = ""

            def _simple_backend_poll():
                from datetime import datetime, timezone
                t0 = None
                base = st.session_state.simple_backend_base
                key = st.session_state.simple_backend_api_key
                ch = int(st.session_state.simple_backend_channel)
                while not st.session_state.simple_stop:
                    sample, status = fetch_latest_status(base, key, ch)
                    if status == 200 and sample and 'timestamp' in sample:
                        try:
                            ts = datetime.fromisoformat(sample['timestamp'].replace('Z','+00:00'))
                            if t0 is None:
                                t0 = ts
                            t_sec = (ts - t0).total_seconds()
                            st.session_state.simple_data_buffer.append({
                                'time': t_sec,
                                'raw': float(sample.get('raw', 0.0)),
                                'rect': float(sample.get('rect', 0.0)),
                                'envelope': float(sample.get('envelope', 0.0)),
                                'rms': float(sample.get('rms', 0.0))
                            })
                            st.session_state.simple_last_sample_wall = time.time()
                        except Exception:
                            pass
                    else:
                        if status == 404:
                            st.session_state.simple_last_error = "Backend: No samples yet (404)."
                        elif status == 401:
                            st.session_state.simple_last_error = "Backend: Unauthorized (401). Check API key."
                        elif status == -1:
                            st.session_state.simple_last_error = "Backend: Connection error. Verify server URL."
                        else:
                            st.session_state.simple_last_error = f"Backend: HTTP {status}."
                    time.sleep(0.12)

            th = threading.Thread(target=_simple_backend_poll, daemon=True)
            if _add_run_ctx:
                try:
                    _add_run_ctx(th)
                except Exception:
                    pass
            th.start()
            st.session_state.simple_backend_thread = th

    with c5:
        if st.button("🔴 STOP", use_container_width=True):
            st.session_state.simple_stop = True
    # Quick backend test: send a synthetic sample
    tcol1, tcol2 = st.columns([1.0, 3.0])
    with tcol1:
        if st.button("🧪 Test Backend (POST sample)", help="Posts a synthetic sample to prime /emg/latest."):
            base = st.session_state.simple_backend_base
            key = st.session_state.simple_backend_api_key
            ch = int(st.session_state.simple_backend_channel)
            # small synthetic sample (random noise around 0.05)
            raw = float(0.05 + np.random.normal(0, 0.005))
            _, status = post_sample(base, key, ch, raw)
            if status == 200:
                st.success("Sample posted. Latest should populate shortly.")
            elif status == 401:
                st.error("Unauthorized (401). Check API key.")
            elif status == -1:
                st.error("Connection error. Verify backend URL.")
            else:
                st.warning(f"POST returned HTTP {status}.")

    # Status
    fs_fixed = 860.0
    connected = st.session_state.simple_backend_thread and st.session_state.simple_backend_thread.is_alive()
    last_wall = st.session_state.simple_last_sample_wall
    flowing = bool(connected and last_wall and (time.time() - float(last_wall) < 1.0))
    s1, s2, s3 = st.columns(3)
    with s1:
        if flowing:
            st.success("🟢 CONNECTED: Data Flowing")
        elif connected:
            st.warning("🟡 CONNECTED: Waiting for data…")
        else:
            st.info(f"🌐 Polling backend {st.session_state.simple_backend_base}…")
    with s2:
        st.metric("Fs", f"{fs_fixed:.0f} Hz")
    with s3:
        st.metric("Buffer", len(st.session_state.simple_data_buffer))

    # Need some data before plotting
    if len(st.session_state.simple_data_buffer) < 20:
        if st.session_state.simple_last_error:
            st.warning(st.session_state.simple_last_error)
        time.sleep(0.15)
        st.rerun()
        return

    # Build window
    data_list = list(st.session_state.simple_data_buffer)
    max_samples = int(max(1, time_window * fs_fixed))
    recent = data_list[-max_samples:] if len(data_list) > max_samples else data_list
    times = np.array([d['time'] for d in recent], dtype=float)
    raw_vals = np.array([d.get('raw', 0.0) for d in recent], dtype=float)

    # Processing constants
    hp, lp = 20.0, 450.0
    rms_win_s = 0.10
    rect = np.abs(raw_vals - np.mean(raw_vals))
    sig_bp = apply_bandpass(raw_vals - np.mean(raw_vals), lowcut=hp, highcut=lp, fs=fs_fixed)
    env_lp = lowpass_envelope(rect, fs=fs_fixed, cutoff_hz=5.0)
    env_rms = sliding_rms(rect, window_size=max(1, int(fs_fixed * rms_win_s)))

    # Tabs grouped by insight
    tab1, tab2, tab3 = st.tabs(["Activation & Power", "Frequency & Fatigue", "Quality & Diagnostics"])

    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=times, y=sig_bp, name="Band-pass", line=dict(color="#1f77b4")))
        fig.add_trace(go.Scatter(x=times, y=rect, name="Rectified", line=dict(color="#ff7f0e")))
        fig.add_trace(go.Scatter(x=times, y=env_rms, name="RMS Env (0.10s)", line=dict(color="#2ca02c")))
        fig.add_trace(go.Scatter(x=times, y=env_lp, name="Low-pass Env (5 Hz)", line=dict(color="#9467bd")))
        fig.update_layout(height=360, xaxis_title="Time (s)", yaxis_title="Amplitude (a.u.)", legend_orientation="h")
        st.plotly_chart(fig, use_container_width=True)
        # Simple scalar metrics
        rms_val = float(np.sqrt(np.mean(sig_bp**2))) if len(sig_bp) > 0 else 0.0
        iemg_val = float(np.sum(rect) / fs_fixed)
        m1, m2 = st.columns(2)
        m1.metric("RMS (band-pass)", f"{rms_val:.3f}")
        m2.metric("iEMG (rect)", f"{iemg_val:.3f}")

    with tab2:
        # Welch/FFT PSD (use simple FFT for clarity)
        yf = np.fft.rfft(sig_bp)
        freqs = np.fft.rfftfreq(len(sig_bp), d=1.0/fs_fixed)
        psd = np.abs(yf)**2
        mnf = 0.0
        mdf = 0.0
        if len(psd) > 1:
            psd_sum = float(np.sum(psd))
            if psd_sum > 0:
                mnf = float(np.sum(freqs * psd) / psd_sum)
                cumsum = np.cumsum(psd)
                half = cumsum[-1] / 2.0
                idx = int(np.searchsorted(cumsum, half))
                mdf = float(freqs[idx]) if idx < len(freqs) else 0.0
        fig_psd = go.Figure()
        fig_psd.add_trace(go.Scatter(x=freqs, y=psd, name="PSD", line=dict(color="#1f77b4")))
        fig_psd.add_shape(type="line", x0=mnf, x1=mnf, y0=0, y1=float(np.max(psd)) if len(psd)>0 else 1,
                          line=dict(color="#d62728", dash="dash"))
        fig_psd.add_shape(type="line", x0=mdf, x1=mdf, y0=0, y1=float(np.max(psd)) if len(psd)>0 else 1,
                          line=dict(color="#2ca02c", dash="dot"))
        fig_psd.update_layout(height=360, xaxis_title="Frequency (Hz)", yaxis_title="Power", legend_orientation="h")
        st.plotly_chart(fig_psd, use_container_width=True)
        m1, m2 = st.columns(2)
        m1.metric("MNF", f"{mnf:.1f} Hz")
        m2.metric("MDF", f"{mdf:.1f} Hz")

    with tab3:
        # Simple quality proxy via SNR (rectified)
        snr_db = np.nan
        if len(rect) > 0:
            q = np.quantile(rect, 0.2)
            noise = rect[rect <= q]
            noise_rms = float(np.sqrt(np.mean(noise**2))) if len(noise) > 0 else 0.0
            sig_rms = float(np.sqrt(np.mean(rect**2))) if len(rect) > 0 else 0.0
            snr_db = float(20.0 * np.log10(sig_rms / noise_rms)) if noise_rms > 0 else np.nan
        qual = "Unknown"
        if np.isfinite(snr_db):
            qual = "Good" if snr_db > 20 else ("OK" if snr_db > 10 else "Poor")
        q1, q2, q3 = st.columns(3)
        q1.metric("SNR", f"{snr_db:.1f} dB" if np.isfinite(snr_db) else "N/A")
        q2.metric("Samples", len(recent))
        q3.metric("Status", qual)
        if st.session_state.simple_last_error:
            st.warning(st.session_state.simple_last_error)

    time.sleep(0.12)
    st.rerun()


# ------------------------------
# Signal processing helpers now provided by emg.preprocessing
# ------------------------------


def live_serial_reader_thread(port: str, baud: int = 115200):
    """Robust serial reader with auto-reconnect and microseconds->seconds conversion."""
    while not st.session_state.live_stop:
        try:
            ser = serial.Serial(port, baud, timeout=1)
            st.session_state.live_ser = ser
            time.sleep(2)  # wait for Arduino reset
            try:
                ser.reset_input_buffer()
            except Exception:
                pass
            start_us = None
            while not st.session_state.live_stop:
                line_bytes = ser.readline()
                if not line_bytes:
                    continue
                try:
                    line = line_bytes.decode('utf-8', errors='ignore').strip()
                except Exception:
                    continue
                if not line:
                    continue
                if 'timestamp' in line.lower() or ',' not in line:
                    continue
                parts = line.split(',')
                if len(parts) < 2:
                    continue
                try:
                    t_us = int(parts[0])
                    adc = int(parts[1])
                except ValueError:
                    continue
                if start_us is None:
                    start_us = t_us
                t_sec = (t_us - start_us) / 1_000_000.0
                st.session_state.live_data_buffer.append({
                    'time': t_sec,
                    'adc': adc,
                    'voltage': (adc / float(st.session_state.live_adc_max)) * 5.0
                })
                # Mark wall-clock time of last received sample for flow detection
                try:
                    st.session_state.live_last_sample_wall = time.time()
                except Exception:
                    pass
                # Write to disk if recording
                if st.session_state.live_recording and st.session_state.live_record_file:
                    try:
                            v = (adc / float(st.session_state.live_adc_max)) * 5.0
                            st.session_state.live_record_file.write(f"{t_sec:.6f},{adc},{v:.6f}\n")
                    except Exception:
                        pass
            try:
                ser.close()
            except Exception:
                pass
        except serial.SerialException as e:
            st.session_state.live_last_error = f"Serial error: {e}"
            time.sleep(1.0)
            continue
        except Exception as e:
            st.session_state.live_last_error = f"Reader error: {e}"
            time.sleep(0.2)
            continue
    try:
        if st.session_state.live_ser:
            st.session_state.live_ser.close()
    except Exception:
        pass


def render_live_tab():
    st.subheader("⚡ Live EMG Monitor")

    # Top controls: Port, Time Window, Start/Stop
    src_col, port_col, win_col, start_col, stop_col = st.columns([1.4, 2.0, 1.1, 0.9, 0.9])
    with src_col:
        st.session_state.live_source = st.selectbox("Source", ["Serial", "Backend API"], index=(0 if st.session_state.live_source=="Serial" else 1))
    with port_col:
        selected_port = None
        if st.session_state.live_source == "Serial":
            ports = list_ports()
            options = ports + ["Manual..."] if ports else ["Manual..."]
            choice = st.selectbox("Port", options, index=0)
            manual_port = None
            if choice == "Manual...":
                placeholder = "COM3" if os.name == 'nt' else "/dev/ttyUSB0"
                manual_port = st.text_input("Manual port", value=placeholder)
            selected_port = manual_port if manual_port else (choice if choice != "Manual..." else None)
        else:
            st.text_input("Base URL", key="live_backend_base")
            st.text_input("API Key", key="live_backend_api_key")
            st.number_input("Channel", min_value=0, max_value=16, value=st.session_state.live_backend_channel, key="live_backend_channel")
    with win_col:
        time_window = st.slider("Window (s)", 1, 10, 3)
    with start_col:
        can_start_serial = selected_port is not None and len(str(selected_port).strip()) > 0
        can_start_backend = (len(str(st.session_state.live_backend_base).strip()) > 0)
        can_start = can_start_serial if st.session_state.live_source == "Serial" else can_start_backend
        if st.button("🟢 START", use_container_width=True, disabled=not can_start):
            st.session_state.live_stop = False
            st.session_state.live_data_buffer.clear()
            st.session_state.live_last_error = ""
            if st.session_state.live_source == "Serial":
                if st.session_state.live_serial_thread is None or not st.session_state.live_serial_thread.is_alive():
                    st.session_state['live_target_port'] = selected_port
                    th = threading.Thread(target=live_serial_reader_thread, args=(selected_port,), daemon=True)
                    if _add_run_ctx:
                        try:
                            _add_run_ctx(th)
                        except Exception:
                            pass
                    th.start()
                    st.session_state.live_serial_thread = th
            else:
                # Backend polling thread
                def _backend_poll():
                    from datetime import datetime, timezone
                    t0 = None
                    last_ts = None
                    base = st.session_state.live_backend_base
                    key = st.session_state.live_backend_api_key
                    ch = int(st.session_state.live_backend_channel)
                    while not st.session_state.live_stop:
                        sample, status = fetch_latest_status(base, key, ch)
                        if status == 200 and sample and 'timestamp' in sample and 'raw' in sample:
                            try:
                                ts = datetime.fromisoformat(sample['timestamp'].replace('Z','+00:00'))
                                if t0 is None:
                                    t0 = ts
                                t_sec = (ts - t0).total_seconds()
                                st.session_state.live_data_buffer.append({
                                    'time': t_sec,
                                    'raw': float(sample.get('raw', 0.0)),
                                    'rect': float(sample.get('rect', 0.0)),
                                    'envelope': float(sample.get('envelope', 0.0)),
                                    'rms': float(sample.get('rms', 0.0))
                                })
                                st.session_state.live_last_sample_wall = time.time()
                            except Exception:
                                pass
                        else:
                            # Update status message for visibility
                            if status == 404:
                                st.session_state.live_last_error = "Backend: No samples yet (404). Awaiting ingestion."
                            elif status == 401:
                                st.session_state.live_last_error = "Backend: Unauthorized (401). Check API key."
                            elif status == -1:
                                st.session_state.live_last_error = "Backend: Connection error. Verify base URL and server."
                            else:
                                st.session_state.live_last_error = f"Backend: HTTP {status}."
                        time.sleep(0.1)
                th = threading.Thread(target=_backend_poll, daemon=True)
                if _add_run_ctx:
                    try:
                        _add_run_ctx(th)
                    except Exception:
                        pass
                th.start()
                st.session_state.live_backend_thread = th
    with stop_col:
        if st.button("🔴 STOP", use_container_width=True):
            st.session_state.live_stop = True
            if st.session_state.live_ser:
                try:
                    st.session_state.live_ser.close()
                except Exception:
                    pass

    # Amplitude units selection
    unit_col, _sp = st.columns([1.2, 3.0])
    with unit_col:
        amp_units = st.selectbox("Amplitude units", ["ADC code", "Voltage (V)", "Raw"], index=2 if st.session_state.live_source=="Backend API" else 0)
    with _sp:
        st.caption("Voltage = (adc/1023)*5.0 V | Increase RMS window or use Low-pass for smoother envelope.")

    # Filter settings row
    st.markdown("---")
    f1, f2, f3, f4, f5 = st.columns([1, 1, 1, 1, 1])
    with f1:
        apply_bp = st.checkbox("Band-pass", value=True)
    with f2:
        hp = st.number_input("HP (Hz)", min_value=0.0, max_value=500.0, value=20.0, step=1.0)
    with f3:
        lp = st.number_input("LP (Hz)", min_value=5.0, max_value=500.0, value=450.0, step=5.0)
    with f4:
        use_notch = st.checkbox("Notch 60Hz", value=True)
    with f5:
        rms_s = st.number_input("RMS window (s)", min_value=0.02, max_value=0.50, value=0.10, step=0.01, format="%.2f")
    env_method = st.radio("Envelope method", ["RMS", "Low-pass"], horizontal=True, index=0)

    # Basic guard to prevent invalid band selection from crashing
    if apply_bp and hp >= lp:
        st.warning("HP must be less than LP; skipping band-pass filter.")
        apply_bp = False

    # Recording, Download, Event markers
    st.markdown("---")
    rec_col, stop_rec_col, dl_col, mark_text_col, mark_btn_col = st.columns([1, 1, 2, 1.5, 0.8])
    st.text_input("Session", key="live_session_name")
    with rec_col:
        if st.button("🔴 Record", disabled=st.session_state.live_recording, use_container_width=True):
            try:
                Path("data").mkdir(exist_ok=True)
                # sanitize session name
                raw_name = (st.session_state.live_session_name or "").strip()
                if not raw_name:
                    raw_name = f"emg_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                invalid = '<>:"/\\|?*'
                safe_name = ''.join((c if c not in invalid else '_') for c in raw_name)
                safe_name = safe_name.rstrip('.')  # Windows does not allow trailing dot
                if not safe_name.lower().endswith('.csv'):
                    safe_name = f"{safe_name}.csv"
                path = Path("data") / safe_name
                f = open(path, 'w', buffering=1)
                f.write("time_s,adc,voltage_v\n")
                st.session_state.live_record_file = f
                st.session_state.live_record_path = str(path)
                st.session_state.live_recording = True
            except Exception:
                pass
    with stop_rec_col:
        if st.button("⏹️ Stop", disabled=not st.session_state.live_recording, use_container_width=True):
            try:
                if st.session_state.live_record_file:
                    st.session_state.live_record_file.close()
                st.session_state.live_record_file = None
                st.session_state.live_recording = False
            except Exception:
                pass
    with dl_col:
        if len(st.session_state.live_data_buffer) > 0:
            df_buf = pd.DataFrame(list(st.session_state.live_data_buffer))
            # derive buffer filename from session name
            raw_name = (st.session_state.live_session_name or "").strip()
            invalid = '<>:"/\\|?*'
            safe_base = ''.join((c if c not in invalid else '_') for c in raw_name) or 'emg'
            safe_base = safe_base.rstrip('.')
            st.download_button(
                label="⬇️ Download Current Buffer (CSV)",
                data=df_buf.to_csv(index=False),
                file_name=f"{safe_base}_buffer.csv",
                mime="text/csv"
            )
    with mark_text_col:
        mark_label = st.text_input("Event label", value="event")
    with mark_btn_col:
        if st.button("Add Marker"):
            # Use latest time as marker anchor
            if len(st.session_state.live_data_buffer) > 0:
                t_now = st.session_state.live_data_buffer[-1]['time']
                st.session_state.live_markers.append({'time': t_now, 'label': mark_label})

    # Data availability checks
    if len(st.session_state.live_data_buffer) < 20:
        st.info("Collecting data…")
        time.sleep(0.2)
        st.rerun()
        return

    # Build recent window arrays
    data_list = list(st.session_state.live_data_buffer)
    fs_est = 1000.0
    t_arr = np.array([d['time'] for d in data_list], dtype=float)
    if len(t_arr) > 1:
        dt = np.diff(t_arr)
        dt = dt[(dt > 0) & np.isfinite(dt)]
        if len(dt) > 0:
            fs_est = float(1.0 / np.median(dt))
    # Clamp unreasonable fs estimates (protect envelope math)
    fs_est = float(min(5000.0, max(50.0, fs_est)))
    max_samples = int(time_window * fs_est)
    recent = data_list[-max_samples:] if len(data_list) > max_samples else data_list
    times = np.array([d['time'] for d in recent], dtype=float)
    adc_vals = np.array([d['adc'] for d in recent if 'adc' in d], dtype=float)
    has_adc = len(adc_vals) == len(recent) and len(recent) > 0
    raw_vals = np.array([d['raw'] for d in recent if 'raw' in d], dtype=float)
    has_raw = len(raw_vals) == len(recent) and len(recent) > 0
    if amp_units == "ADC code" and has_adc:
        adc_max = float(st.session_state.live_adc_max)
        sig = adc_vals
    elif amp_units == "Voltage (V)" and has_adc:
        adc_max = float(st.session_state.live_adc_max)
        sig = (adc_vals / adc_max) * 5.0
    elif has_raw:
        sig = raw_vals
    else:
        # Fallback to voltage if possible else zeros
        sig = (adc_vals / float(st.session_state.live_adc_max)) * 5.0 if has_adc else np.zeros(len(recent))

    # Raw signal (centered for frequency metrics)
    sig_centered = sig - np.mean(sig)

    # Filtering
    sig_f = sig_centered.copy()
    if apply_bp:
        sig_f = apply_bandpass(sig_f, lowcut=hp, highcut=lp, fs=fs_est)
    if use_notch:
        sig_f = apply_notch(sig_f, notch_freq=60.0, fs=fs_est)

    # Rectification and envelope
    rect = np.abs(sig_f)
    win_n = int(max(1, fs_est * rms_s))
    if env_method == "Low-pass":
        env = lowpass_envelope(rect, fs=fs_est, cutoff_hz=5.0)
    else:
        # RMS on rectified signal (more distinct from rectified curve)
        env = sliding_rms(rect, window_size=win_n)
    # Optional extra smoothing
    smooth_col1, smooth_col2 = st.columns([1,1])
    with smooth_col1:
        extra_smooth = st.checkbox("Extra smooth (MA)", value=False, help="Apply moving average after envelope for clear demo visualization.")
    with smooth_col2:
        ma_ms = st.slider("MA window (ms)", 10, 500, 150, 10, disabled=not extra_smooth)
    if extra_smooth:
        ma_samples = max(1, int((ma_ms/1000.0)*fs_est))
        if len(env) >= ma_samples and ma_samples > 1:
            kernel = np.ones(ma_samples)/ma_samples
            env = np.convolve(env, kernel, mode='same')
    env_disp = env
    if win_n < 3:
        st.warning("RMS window is <3 samples; envelope will look identical to rectified. Increase the RMS window.")

    # Metrics: RMS, iEMG, MNF, MDF
    dt_win = 1.0 / fs_est if fs_est > 0 else 0.001
    rms_val = float(np.sqrt(np.mean(sig_f**2))) if len(sig_f) > 0 else 0.0
    iemg_val = float(np.sum(rect) * dt_win)
    # Frequency metrics from PSD
    yf = np.fft.rfft(sig_centered)
    freqs = np.fft.rfftfreq(len(sig_centered), d=1.0/fs_est) if fs_est > 0 else np.array([])
    psd = np.abs(yf) ** 2
    if len(psd) > 1:
        psd_sum = np.sum(psd)
        mnf = float(np.sum(freqs * psd) / psd_sum) if psd_sum > 0 else 0.0
        cumsum = np.cumsum(psd)
        half = cumsum[-1] / 2.0 if cumsum[-1] > 0 else 0.0
        idx = int(np.searchsorted(cumsum, half)) if half > 0 else 0
        mdf = float(freqs[idx]) if idx < len(freqs) else 0.0
    else:
        mnf = 0.0
        mdf = 0.0

    # SNR estimate (rectified-based noise floor)
    if len(rect) > 0:
        q = np.quantile(rect, 0.2)
        noise = rect[rect <= q]
        noise_rms = float(np.sqrt(np.mean(noise**2))) if len(noise) > 0 else 0.0
        sig_rms = float(np.sqrt(np.mean(rect**2)))
        snr_db = float(20.0 * np.log10(sig_rms / noise_rms)) if noise_rms > 0 else np.nan
    else:
        snr_db = np.nan

    # Clipping estimate on ADC range (only when adc present)
    if amp_units == "ADC code" and has_adc:
        th_hi = 0.99 * float(st.session_state.live_adc_max)
        th_lo = 0.01 * float(st.session_state.live_adc_max)
        clip_pct = 100.0 * np.mean((adc_vals >= th_hi) | (adc_vals <= th_lo)) if len(adc_vals) > 0 else 0.0
    else:
        clip_pct = 0.0

    # Channel quality from SNR and clipping
    quality = "Poor"
    if np.isnan(snr_db):
        quality = "Unknown"
    elif snr_db > 20 and clip_pct < 1.0:
        quality = "Good"
    elif snr_db > 10 and clip_pct < 5.0:
        quality = "OK"

    # Status and metrics
    s1, s2, s3 = st.columns(3)
    with s1:
        connected = False
        if st.session_state.live_source == "Serial":
            connected = st.session_state.live_serial_thread and st.session_state.live_serial_thread.is_alive()
        else:
            connected = st.session_state.live_backend_thread and st.session_state.live_backend_thread.is_alive()
        last_wall = st.session_state.live_last_sample_wall
        flowing = bool(connected and last_wall and (time.time() - float(last_wall) < 1.0))
        if flowing:
            st.success("🟢 CONNECTED: Data Flowing")
        elif connected:
            st.warning("🟡 CONNECTED: Waiting for data…")
        else:
            if st.session_state.live_source == "Serial":
                tgt = st.session_state.get('live_target_port')
                if tgt and not st.session_state.live_last_error:
                    st.info(f"🔌 Connecting to {tgt}…")
                else:
                    st.error("🔴 DISCONNECTED")
            else:
                base = st.session_state.live_backend_base
                st.info(f"🌐 Polling backend {base}…")
    with s2:
        st.metric("Buffer", len(st.session_state.live_data_buffer))
        st.caption(f"Fs≈{fs_est:.0f} Hz | RMS win≈{win_n} samples")
    with s3:
        st.metric("SNR (dB)", f"{snr_db:.1f}" if np.isfinite(snr_db) else "N/A")
    s5, s6, s7 = st.columns(3)
    with s5:
        st.metric("RMS", f"{rms_val:.2f}")
    with s6:
        st.metric("iEMG", f"{iemg_val:.3f}")
    with s7:
        st.metric("Quality", quality)

    # Plots: raw/rectified/envelope
    st.markdown("---")
    fig_ts = plot_time_series(times, sig, rect, env_disp, st.session_state.live_markers, amp_units, env_method)
    st.plotly_chart(fig_ts, use_container_width=True)

    # Optional spectrogram
    with st.expander("Frequency Content (Spectrogram)"):
        show_spec = st.checkbox("Show spectrogram", value=False)
        if show_spec:
            spec_fig = plot_spectrogram(sig_f, fs_est)
            if spec_fig is not None:
                st.plotly_chart(spec_fig, use_container_width=True)
            else:
                st.info("Not enough data for spectrogram yet.")

    # PSD and frequency metrics
    fig_psd = plot_psd(freqs, psd, mnf, mdf, fs_est)
    st.plotly_chart(fig_psd, use_container_width=True)

    # Error log (if any)
    if st.session_state.live_last_error:
        st.warning(st.session_state.live_last_error)

    # Auto-refresh
    time.sleep(0.1)
    st.rerun()







# -------------------------------------------------------------------------------------------
# Compare Tab
# -------------------------------------------------------------------------------------------

def _std_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to a standard schema: time_s, adc, voltage_v."""
    cols = {c.lower(): c for c in df.columns}
    out = df.copy()
    # Time
    if 'time_s' in out.columns:
        pass
    elif 'time' in cols:
        out.rename(columns={cols['time']: 'time_s'}, inplace=True)
    elif 'timestamp' in cols:
        out.rename(columns={cols['timestamp']: 'time_s'}, inplace=True)
    # ADC
    if 'adc' not in out.columns:
        if 'raw' in cols:
            out.rename(columns={cols['raw']: 'adc'}, inplace=True)
    # Voltage
    if 'voltage_v' not in out.columns:
        if 'voltage' in cols:
            out.rename(columns={cols['voltage']: 'voltage_v'}, inplace=True)
    return out




def _list_data_files() -> list:
    data_dir = Path('data')
    if not data_dir.exists():
        return []
    return sorted([str(p) for p in data_dir.glob('*.csv')])


def render_compare_tab():
    st.subheader("🔀 Compare Sessions (e.g., Left vs Right)")

    # Source selection: from disk or upload
    s1, s2 = st.columns(2)
    with s1:
        st.caption("Session A")
        files = _list_data_files()
        a_choice = st.selectbox("Pick from data/", files + ["Upload..."], key="cmp_a_pick")
        a_df = None
        if a_choice == "Upload...":
            a_up = st.file_uploader("Upload CSV A", type=["csv"], key="cmp_a_up")
            if a_up is not None:
                a_df = pd.read_csv(a_up)
        elif a_choice:
            try:
                a_df = pd.read_csv(a_choice)
            except Exception as e:
                st.error(f"Failed to load A: {e}")
        a_label = st.text_input("Label A", value="Left")

    with s2:
        st.caption("Session B")
        files_b = _list_data_files()
        b_choice = st.selectbox("Pick from data/", files_b + ["Upload..."], key="cmp_b_pick")
        b_df = None
        if b_choice == "Upload...":
            b_up = st.file_uploader("Upload CSV B", type=["csv"], key="cmp_b_up")
            if b_up is not None:
                b_df = pd.read_csv(b_up)
        elif b_choice:
            try:
                b_df = pd.read_csv(b_choice)
            except Exception as e:
                st.error(f"Failed to load B: {e}")
        b_label = st.text_input("Label B", value="Right")

    if a_df is None or b_df is None:
        st.info("Select or upload two sessions to compare.")
        return

    # Normalize columns
    a_df = _std_columns(a_df)
    b_df = _std_columns(b_df)
    # Choose signal column for analysis (prefer adc)
    sig_col = 'adc' if 'adc' in a_df.columns and 'adc' in b_df.columns else ('voltage_v' if 'voltage_v' in a_df.columns and 'voltage_v' in b_df.columns else None)
    if sig_col is None or 'time_s' not in a_df.columns or 'time_s' not in b_df.columns:
        st.error("CSV must contain time and signal columns (time_s + adc or voltage_v).")
        return

    # Estimate sampling frequency
    fs_a = estimate_fs(a_df['time_s'].to_numpy())
    fs_b = estimate_fs(b_df['time_s'].to_numpy())

    # Region selection (optional)
    st.markdown("---")
    st.caption("Optional analysis window (in seconds from start of each file)")
    # Safely determine slider ranges even if data is empty or NaN
    def _safe_tmax(df: pd.DataFrame) -> float:
        if 'time_s' not in df.columns:
            return 1.0
        ts = pd.to_numeric(df['time_s'], errors='coerce').dropna()
        if ts.empty:
            return 1.0
        m = float(ts.max())
        return m if np.isfinite(m) and m > 0 else 1.0

    tmax_a = _safe_tmax(a_df)
    tmax_b = _safe_tmax(b_df)
    r1, r2 = st.columns(2)
    with r1:
        win_a = st.slider("Window A", 0.0, tmax_a, (0.0, tmax_a), key="win_a")
    with r2:
        win_b = st.slider("Window B", 0.0, tmax_b, (0.0, tmax_b), key="win_b")

    a_mask = (a_df['time_s'] >= win_a[0]) & (a_df['time_s'] <= win_a[1])
    b_mask = (b_df['time_s'] >= win_b[0]) & (b_df['time_s'] <= win_b[1])
    a_t = a_df.loc[a_mask, 'time_s'].to_numpy()
    b_t = b_df.loc[b_mask, 'time_s'].to_numpy()
    a_sig = a_df.loc[a_mask, sig_col].to_numpy().astype(float)
    b_sig = b_df.loc[b_mask, sig_col].to_numpy().astype(float)

    # Compute metrics
    a_metrics = compute_metrics(a_t, a_sig, fs_a)
    b_metrics = compute_metrics(b_t, b_sig, fs_b)
    if not a_metrics or not b_metrics:
        st.warning("Not enough data to compute metrics.")
        return

    # Display metrics side-by-side
    st.markdown("## Results")
    mcols = st.columns(4)
    mcols[0].metric(f"Peak Env ({a_label})", f"{a_metrics['peak_env']:.3f}")
    mcols[1].metric(f"Peak Env ({b_label})", f"{b_metrics['peak_env']:.3f}")
    mcols[2].metric(f"IEMG ({a_label})", f"{a_metrics['iemg']:.3f}")
    mcols[3].metric(f"IEMG ({b_label})", f"{b_metrics['iemg']:.3f}")

    mcols2 = st.columns(4)
    mcols2[0].metric(f"Time-to-Peak ({a_label})", f"{a_metrics['time_to_peak_s']:.2f}s")
    mcols2[1].metric(f"Time-to-Peak ({b_label})", f"{b_metrics['time_to_peak_s']:.2f}s")
    mcols2[2].metric(f"Median Freq ({a_label})", f"{a_metrics['median_freq_hz']:.1f} Hz")
    mcols2[3].metric(f"Median Freq ({b_label})", f"{b_metrics['median_freq_hz']:.1f} Hz")

    # Symmetry index (choose metric)
    st.markdown("---")
    metric_key = st.selectbox("Symmetry metric", ["peak_env", "iemg"], format_func=lambda k: "Peak Env" if k=="peak_env" else "IEMG")
    a_val = a_metrics[metric_key]
    b_val = b_metrics[metric_key]
    denom = (a_val + b_val) / 2.0 if (a_val + b_val) != 0 else 1.0
    symmetry = 100.0 * (a_val - b_val) / denom
    st.metric("Symmetry Index", f"{symmetry:+.1f}%")

    # Overlay envelope plots
    st.markdown("## Envelope Overlay")
    # Build envelope time aligned to window start for each
    a_env = a_metrics['env']
    b_env = b_metrics['env']
    # Downsample for display if very long
    def _downsample(x, max_pts=400):
        if len(x) <= max_pts:
            return x
        idx = np.linspace(0, len(x)-1, max_pts).astype(int)
        return x[idx]
    a_env_ds = _downsample(a_env)
    b_env_ds = _downsample(b_env)
    a_t0 = np.linspace(0, len(a_env_ds)/fs_a, num=len(a_env_ds))
    b_t0 = np.linspace(0, len(b_env_ds)/fs_b, num=len(b_env_ds))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=a_t0, y=a_env_ds, name=a_label, line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=b_t0, y=b_env_ds, name=b_label, line=dict(color='red')))
    fig.update_layout(height=350, xaxis_title="Time (s)", yaxis_title="Envelope (a.u.)")
    st.plotly_chart(fig, use_container_width=True)

    # Export combined metrics
    out_df = pd.DataFrame([
        {'label': a_label, **{k: v for k, v in a_metrics.items() if k != 'env'}},
        {'label': b_label, **{k: v for k, v in b_metrics.items() if k != 'env'}},
        {'label': 'symmetry', f'sym_{metric_key}': symmetry}
    ])
    st.download_button(
        label="⬇️ Download metrics (CSV)",
        data=out_df.to_csv(index=False),
        file_name=f"compare_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )



def main():
    st.markdown("# EMG Unified Dashboard")
    view = st.radio("View", ["Simple FFT Demo", "Live Monitor", "Compare"], horizontal=True, key="main_view")
    if view == "Simple FFT Demo":
        render_simple_fft_demo()
    elif view == "Live Monitor":
        render_live_tab()
    else:
        render_compare_tab()



if __name__ == "__main__":
    main()
