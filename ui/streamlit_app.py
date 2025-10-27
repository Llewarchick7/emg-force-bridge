import streamlit as st
import joblib
import pandas as pd
import numpy as np
from emg.preprocessing.filters import apply_bandpass, apply_notch
from emg.preprocessing.envelope import sliding_rms

st.title("EMG Force Bridge — Live Demo")

st.sidebar.header("Quick actions")
uploaded = st.sidebar.file_uploader("Upload a CSV (timestamp_s,value,optional label)", type=['csv'])
model_file = st.sidebar.text_input("Model path", value="models/baseline_svm.joblib")
if st.sidebar.button("Load model"):
    try:
        model = joblib.load(model_file)
        st.sidebar.success("Model loaded")
    except Exception as e:
        st.sidebar.error(f"Failed to load model: {e}")
        model = None

st.header("Signal viewer")
if uploaded:
    df = pd.read_csv(uploaded)
    if 'value' in df.columns:
        st.line_chart(df['value'])
    else:
        st.error("CSV must contain 'value' column")

st.write("This app will be extended to live-stream serial data and show model predictions in real time.")
st.write("Calibration and per-user baseline features will be added in next iterations.")