import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import threading
from collections import deque
from datetime import datetime
import json
from pathlib import Path

# EMG imports
from emg.config import EMGConfig
from emg.acquisition.serial_source import SerialConfig, read_serial_csv
from emg.preprocessing.filters import apply_bandpass, apply_notch, StreamingSOS, design_bandpass_sos
from emg.preprocessing.rectify import full_wave_rectify
from emg.preprocessing.envelope import sliding_rms
from emg.features.time import rms, mav, wl, zero_crossings
from emg.features.freq import welch_psd, mean_frequency, median_frequency
from emg.artifacts.detectors import detect_motion_lowfreq, detect_clipping, detect_spikes
from emg.normalization import Normalizer
from emg.io.logger import CSVLogger

# Configure Streamlit
st.set_page_config(
    page_title="EMG Force Bridge - Real-Time Monitor",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'recording' not in st.session_state:
    st.session_state.recording = False
if 'data_buffer' not in st.session_state:
    st.session_state.data_buffer = deque(maxlen=5000)  # 5 seconds at 1kHz
if 'normalizer' not in st.session_state:
    st.session_state.normalizer = Normalizer()
if 'serial_thread' not in st.session_state:
    st.session_state.serial_thread = None
if 'stop_acquisition' not in st.session_state:
    st.session_state.stop_acquisition = False

def data_acquisition_thread(port, baud, fs):
    """Background thread for continuous data acquisition"""
    try:
        scfg = SerialConfig(port=port, baud=baud)
        
        # Setup streaming filters
        bandpass_sos = design_bandpass_sos(fs, 20.0, 450.0)
        bp_filter = StreamingSOS(bandpass_sos)
        
        for t, val in read_serial_csv(scfg):
            if st.session_state.stop_acquisition:
                break
                
            # Store raw data
            timestamp = time.time()
            
            # Apply streaming filters (single sample)
            val_array = np.array([val])
            filtered = bp_filter.process(val_array)[0]
            rectified = abs(filtered)
            
            # Add to buffer
            st.session_state.data_buffer.append({
                'timestamp': timestamp,
                'time_rel': t,
                'raw': val,
                'filtered': filtered,
                'rectified': rectified
            })
            
    except Exception as e:
        st.error(f"Data acquisition error: {e}")

def compute_features(data_window):
    """Compute real-time features from data window"""
    if len(data_window) < 10:
        return {}
    
    raw_vals = np.array([d['raw'] for d in data_window])
    filtered_vals = np.array([d['filtered'] for d in data_window])
    rect_vals = np.array([d['rectified'] for d in data_window])
    
    # Time domain features
    features = {
        'rms': rms(filtered_vals),
        'mav': mav(filtered_vals), 
        'wl': wl(filtered_vals),
        'zc': zero_crossings(filtered_vals, threshold=0.01),
    }
    
    # Envelope
    if len(rect_vals) >= 50:  # Need enough samples for envelope
        envelope = sliding_rms(rect_vals, min(50, len(rect_vals)))
        features['envelope'] = float(envelope[-1])
    else:
        features['envelope'] = 0.0
    
    # Frequency features (if enough data)
    if len(filtered_vals) >= 256:
        try:
            freqs, psd = welch_psd(filtered_vals, fs=1000.0, nperseg=min(256, len(filtered_vals)))
            features['mean_freq'] = mean_frequency(freqs, psd)
            features['median_freq'] = median_frequency(freqs, psd)
        except:
            features['mean_freq'] = 0.0
            features['median_freq'] = 0.0
    
    # Artifacts
    features['motion_artifact'] = detect_motion_lowfreq(raw_vals, fs=1000.0)
    features['clipping'] = detect_clipping(raw_vals)
    features['spikes'] = detect_spikes(raw_vals)
    
    return features

def main():
    st.title("⚡ EMG Force Bridge - Real-Time Monitor")
    st.markdown("Professional EMG signal acquisition, processing, and analysis")
    
    # Sidebar controls
    st.sidebar.header("🎛️ Control Panel")
    
    # Connection settings
    st.sidebar.subheader("Connection")
    port = st.sidebar.text_input("COM Port", value="COM5")
    baud = st.sidebar.selectbox("Baud Rate", [9600, 115200, 230400], index=1)
    
    # Signal processing settings  
    st.sidebar.subheader("Signal Processing")
    fs = st.sidebar.slider("Sample Rate (Hz)", 500, 2000, 1000)
    filter_enabled = st.sidebar.checkbox("Band-pass Filter (20-450 Hz)", value=True)
    notch_enabled = st.sidebar.checkbox("Notch Filter (60 Hz)", value=True)
    
    # Display settings
    st.sidebar.subheader("Display")
    time_window = st.sidebar.slider("Time Window (s)", 1.0, 10.0, 3.0, 0.5)
    update_rate = st.sidebar.slider("Update Rate (Hz)", 1, 20, 10)
    
    # Acquisition controls
    st.sidebar.subheader("Acquisition")
    
    if st.sidebar.button("▶️ Start Acquisition"):
        if st.session_state.serial_thread is None or not st.session_state.serial_thread.is_alive():
            st.session_state.stop_acquisition = False
            st.session_state.serial_thread = threading.Thread(
                target=data_acquisition_thread, 
                args=(port, baud, fs)
            )
            st.session_state.serial_thread.daemon = True
            st.session_state.serial_thread.start()
            st.sidebar.success("Acquisition started!")
    
    if st.sidebar.button("⏹️ Stop Acquisition"):
        st.session_state.stop_acquisition = True
        st.sidebar.info("Stopping acquisition...")
    
    # Recording controls
    st.sidebar.subheader("Recording")
    session_name = st.sidebar.text_input("Session Name", value=f"emg_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    if st.sidebar.button("🔴 Start Recording"):
        st.session_state.recording = True
        st.sidebar.success(f"Recording: {session_name}")
    
    if st.sidebar.button("⏹️ Stop Recording"):
        st.session_state.recording = False
        st.sidebar.info("Recording stopped")
    
    # Main display area
    if len(st.session_state.data_buffer) == 0:
        st.info("👆 Click 'Start Acquisition' in the sidebar to begin monitoring")
        st.stop()
    
    # Get recent data
    data_list = list(st.session_state.data_buffer)
    current_time = time.time()
    
    # Filter to time window
    cutoff_time = current_time - time_window
    recent_data = [d for d in data_list if d['timestamp'] >= cutoff_time]
    
    if len(recent_data) < 2:
        st.warning("Waiting for data...")
        st.stop()
    
    # Convert to arrays for plotting
    timestamps = np.array([d['time_rel'] for d in recent_data])
    raw_signal = np.array([d['raw'] for d in recent_data])
    filtered_signal = np.array([d['filtered'] for d in recent_data])
    rectified_signal = np.array([d['rectified'] for d in recent_data])
    
    # Compute envelope
    if len(rectified_signal) >= 50:
        envelope = sliding_rms(rectified_signal, min(50, len(rectified_signal)))
    else:
        envelope = rectified_signal
    
    # Create main plots
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Real-Time Signal")
        
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=['Raw EMG', 'Filtered EMG', 'Envelope'],
            vertical_spacing=0.1
        )
        
        # Raw signal
        fig.add_trace(
            go.Scatter(x=timestamps, y=raw_signal, name="Raw", line=dict(color='lightblue')),
            row=1, col=1
        )
        
        # Filtered signal  
        fig.add_trace(
            go.Scatter(x=timestamps, y=filtered_signal, name="Filtered", line=dict(color='blue')),
            row=2, col=1
        )
        
        # Envelope
        fig.add_trace(
            go.Scatter(x=timestamps, y=envelope, name="Envelope", line=dict(color='red', width=3)),
            row=3, col=1
        )
        
        fig.update_layout(height=500, showlegend=False)
        fig.update_xaxes(title_text="Time (s)", row=3, col=1)
        fig.update_yaxes(title_text="ADC", row=1, col=1)
        fig.update_yaxes(title_text="Filtered", row=2, col=1) 
        fig.update_yaxes(title_text="Envelope", row=3, col=1)
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📊 Live Features & Analysis")
        
        # Compute features from recent window
        window_data = recent_data[-200:] if len(recent_data) >= 200 else recent_data
        features = compute_features(window_data)
        
        # Feature display
        if features:
            col2a, col2b = st.columns(2)
            
            with col2a:
                st.metric("RMS", f"{features.get('rms', 0):.3f}")
                st.metric("MAV", f"{features.get('mav', 0):.3f}")  
                st.metric("Envelope", f"{features.get('envelope', 0):.3f}")
                
            with col2b:
                st.metric("Waveform Length", f"{features.get('wl', 0):.1f}")
                st.metric("Zero Crossings", f"{features.get('zc', 0)}")
                st.metric("Mean Freq (Hz)", f"{features.get('mean_freq', 0):.1f}")
        
        # Signal quality indicators
        st.subheader("🔍 Signal Quality")
        
        if features:
            quality_cols = st.columns(3)
            
            with quality_cols[0]:
                if features.get('motion_artifact', False):
                    st.error("🔴 Motion Artifact")
                else:
                    st.success("🟢 No Motion")
                    
            with quality_cols[1]:
                if features.get('clipping', False):
                    st.error("🔴 Clipping")
                else:
                    st.success("🟢 No Clipping")
                    
            with quality_cols[2]:
                if features.get('spikes', False):
                    st.error("🔴 Spikes")
                else:
                    st.success("🟢 Clean Signal")
    
    # Status bar
    st.markdown("---")
    status_cols = st.columns(4)
    
    with status_cols[0]:
        st.metric("Buffer Size", len(st.session_state.data_buffer))
        
    with status_cols[1]:
        if st.session_state.serial_thread and st.session_state.serial_thread.is_alive():
            st.success("🟢 Acquiring")
        else:
            st.error("🔴 Stopped")
            
    with status_cols[2]:
        if st.session_state.recording:
            st.success("🔴 Recording")
        else:
            st.info("⏸️ Not Recording")
            
    with status_cols[3]:
        st.metric("Data Rate", f"{len(recent_data)/time_window:.0f} Hz")
    
    # Auto-refresh
    time.sleep(1.0 / update_rate)
    st.rerun()

if __name__ == "__main__":
    main()