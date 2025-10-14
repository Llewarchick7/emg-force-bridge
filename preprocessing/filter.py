import numpy as np
from scipy.signal import butter, filtfilt, iirnotch

def butter_bandpass(lowcut, highcut, fs, order=4):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a

def apply_bandpass(data, lowcut=20.0, highcut=450.0, fs=1000.0, order=4):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = filtfilt(b, a, data)
    return y

def apply_notch(data, notch_freq=60.0, fs=1000.0, Q=30.0):
    # notch_freq in Hz, Q ~ 30 is a reasonable starting point
    w0 = notch_freq / (fs/2)
    b, a = iirnotch(w0, Q)
    y = filtfilt(b, a, data)
    return y

def sliding_rms(signal, window_size):
    signal = np.asarray(signal, dtype=float)
    if window_size <= 1:
        return np.abs(signal)
    half = window_size // 2
    padded = np.pad(signal, (half, half), 'constant', constant_values=(0,0))
    out = np.zeros(len(signal))
    for i in range(len(signal)):
        window = padded[i:i+window_size]
        out[i] = np.sqrt(np.mean(window**2))
    return out