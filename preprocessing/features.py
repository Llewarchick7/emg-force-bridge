import numpy as np
import pandas as pd
from scipy import stats

def extract_time_features(signal, fs, window_center_idx, window_size):
    # window_center_idx: center index of current window
    half = window_size // 2
    start = max(0, window_center_idx - half)
    end = min(len(signal), window_center_idx + half)
    w = signal[start:end]
    features = {}
    features['mean'] = np.mean(w)
    features['std'] = np.std(w)
    features['rms'] = np.sqrt(np.mean(w**2))
    features['mad'] = np.mean(np.abs(w - np.mean(w)))
    features['max'] = np.max(w)
    features['min'] = np.min(w)
    features['zcr'] = ((w[:-1]*w[1:])<0).sum() if len(w) > 1 else 0
    return features

def sliding_feature_matrix(signal, fs=1000, window_ms=200, step_ms=50):
    window_size = int(window_ms * fs / 1000)
    step = int(step_ms * fs / 1000)
    rows = []
    for center in range(0, len(signal), step):
        feats = extract_time_features(signal, fs, center, window_size)
        rows.append(feats)
    return pd.DataFrame(rows)