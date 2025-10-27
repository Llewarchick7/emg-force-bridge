"""Filtering utilities for EMG preprocessing.

This module provides both offline (zero-phase) filters using filtfilt and
stateful streaming filters using second-order sections (SOS) for causal
real-time processing.
"""
from __future__ import annotations
import numpy as np
from scipy import signal

# Offline, zero-phase utilities

def apply_bandpass(data: np.ndarray, lowcut: float = 20.0, highcut: float = 450.0, fs: float = 1000.0, order: int = 4) -> np.ndarray:
    """Zero-phase Butterworth band-pass filter.

    Args:
        data: 1D array of EMG samples.
        lowcut: Lower cutoff (Hz).
        highcut: Upper cutoff (Hz).
        fs: Sampling Frequency (Hz).
        order: Filter order.
    Returns:
        Filtered signal, same length as input.
    """
    nyq = 0.5 * fs
    low = max(lowcut / nyq, 1e-6)
    high = min(highcut / nyq, 0.999999)
    b, a = signal.butter(order, [low, high], btype='band')
    return signal.filtfilt(b, a, data)


def apply_notch(data: np.ndarray, notch_freq: float = 60.0, fs: float = 1000.0, q: float = 30.0) -> np.ndarray:
    """Zero-phase IIR notch filter for power-line interference.

    Args:
        data: 1D array of EMG samples.
        notch_freq: Notch frequency (e.g., 50 or 60 Hz).
        fs: Sampling rate (Hz).
        q: Quality factor (higher is narrower).
    Returns:
        Filtered signal, same length as input.
    """
    w0 = notch_freq / (fs / 2)
    b, a = signal.iirnotch(w0, q)
    return signal.filtfilt(b, a, data)


def apply_highpass(data: np.ndarray, cutoff: float, fs: float, order: int = 2) -> np.ndarray:
    """Zero-phase Butterworth high-pass filter."""
    nyq = 0.5 * fs
    wn = max(cutoff / nyq, 1e-6)
    b, a = signal.butter(order, wn, btype='high')
    return signal.filtfilt(b, a, data)


def apply_lowpass(data: np.ndarray, cutoff: float, fs: float, order: int = 4) -> np.ndarray:
    """Zero-phase Butterworth low-pass filter."""
    nyq = 0.5 * fs
    wn = min(cutoff / nyq, 0.999999)
    b, a = signal.butter(order, wn, btype='low')
    return signal.filtfilt(b, a, data)

# Stateful streaming (causal)
class StreamingSOS:
    """Causal streaming filter based on second-order sections.

    Useful for real-time pipelines where filtfilt isn't applicable.

    Methods:
        reset(): Reinitialize state to steady-state for zero input.
        process(x): Filter a new block of samples, returning the output.
    """
    def __init__(self, sos: np.ndarray):
        self.sos = sos
        self.zi = signal.sosfilt_zi(sos)

    def reset(self):
        self.zi = signal.sosfilt_zi(self.sos)

    def process(self, x: np.ndarray) -> np.ndarray:
        y, self.zi = signal.sosfilt(self.sos, x, zi=self.zi)
        return y


def design_bandpass_sos(fs: float, low: float, high: float, order: int = 4) -> np.ndarray:
    """Design a Butterworth band-pass filter and return SOS coefficients.

    Args:
        fs: Sampling rate (Hz).
        low: Lower cutoff (Hz).
        high: Upper cutoff (Hz).
        order: Filter order.
    Returns:
        sos array suitable for StreamingSOS.
    """
    nyq = 0.5 * fs
    low_n = max(low / nyq, 1e-6)
    high_n = min(high / nyq, 0.999999)
    return signal.butter(order, [low_n, high_n], btype='bandpass', output='sos')
