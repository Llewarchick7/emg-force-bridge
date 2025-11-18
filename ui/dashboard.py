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
    port_col, win_col, start_col, stop_col = st.columns([2.2, 1.1, 0.9, 0.9])
    with port_col:
        ports = list_ports()
        options = ports + ["Manual..."] if ports else ["Manual..."]
        choice = st.selectbox("Port", options, index=0)
        manual_port = None
        if choice == "Manual...":
            placeholder = "COM3" if os.name == 'nt' else "/dev/ttyUSB0"
            manual_port = st.text_input("Manual port", value=placeholder)
        selected_port = manual_port if manual_port else (choice if choice != "Manual..." else None)
    with win_col:
        time_window = st.slider("Window (s)", 1, 10, 3)
    with start_col:
        can_start = selected_port is not None and len(str(selected_port).strip()) > 0
        if st.button("🟢 START", use_container_width=True, disabled=not can_start):
            if st.session_state.live_serial_thread is None or not st.session_state.live_serial_thread.is_alive():
                st.session_state.live_stop = False
                st.session_state.live_data_buffer.clear()
                # record target port for status display
                st.session_state['live_target_port'] = selected_port
                st.session_state.live_last_error = ""
                th = threading.Thread(target=live_serial_reader_thread, args=(selected_port,), daemon=True)
                if _add_run_ctx:
                    try:
                        _add_run_ctx(th)
                    except Exception:
                        pass
                th.start()
                st.session_state.live_serial_thread = th
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
        amp_units = st.selectbox("Amplitude units", ["ADC code", "Voltage (V)"])
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
    sig_adc = np.array([d['adc'] for d in recent], dtype=float)
    adc_max = float(st.session_state.live_adc_max)
    sig_voltage = (sig_adc / adc_max) * 5.0
    # Choose representation
    sig = sig_voltage if amp_units == "Voltage (V)" else sig_adc

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

    # Clipping estimate on ADC range
    th_hi = 0.99 * adc_max
    th_lo = 0.01 * adc_max
    clip_pct = 100.0 * np.mean((sig_adc >= th_hi) | (sig_adc <= th_lo)) if len(sig_adc) > 0 else 0.0

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
        connected = st.session_state.live_serial_thread and st.session_state.live_serial_thread.is_alive()
        last_wall = st.session_state.live_last_sample_wall
        flowing = bool(connected and last_wall and (time.time() - float(last_wall) < 1.0))
        if flowing:
            st.success("🟢 CONNECTED: Data Flowing")
        elif connected:
            st.warning("🟡 CONNECTED: Waiting for data…")
        else:
            tgt = st.session_state.get('live_target_port')
            if tgt and not st.session_state.live_last_error:
                st.info(f"🔌 Connecting to {tgt}…")
            else:
                st.error("🔴 DISCONNECTED")
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
    view = st.radio("View", ["Live Monitor", "Compare"], horizontal=True, key="main_view")
    if view == "Live Monitor":
        render_live_tab()
    else:
        render_compare_tab()



if __name__ == "__main__":
    main()
