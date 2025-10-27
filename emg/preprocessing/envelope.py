"""Envelope extraction utilities for EMG.

Two common approaches are provided:
- sliding_rms: RMS over a moving window (simple and robust)
- lowpass_envelope: Low-pass filter of rectified EMG
"""
from __future__ import annotations
import numpy as np
from scipy import signal


def sliding_rms(x: np.ndarray, window_size: int) -> np.ndarray:
    """Compute RMS envelope using a centered moving window.

    Args:
        x: 1D array of rectified EMG samples (or raw; RMS is always positive).
        window_size: Window length in samples. If <= 1, abs(x) is returned.
    Returns:
        Array of same length as x containing RMS estimates.
    """
    x = np.asarray(x, dtype=float)
    if window_size <= 1:
        return np.abs(x)
    kernel = np.ones(int(window_size), dtype=float) / float(window_size)
    # same-length convolution of squared signal
    return np.sqrt(np.convolve(x * x, kernel, mode='same'))


def lowpass_envelope(rectified: np.ndarray, fs: float, cutoff_hz: float = 5.0, order: int = 2) -> np.ndarray:
    """Low-pass filter a rectified signal to obtain an envelope.

    Args:
        rectified: Full-wave rectified EMG signal.
        fs: Sampling rate (Hz).
        cutoff_hz: Envelope low-pass cutoff (Hz).
        order: Butterworth order.
    Returns:
        Smoothed envelope, same length as input.
    """
    nyq = 0.5 * fs
    wn = min(cutoff_hz / nyq, 0.999999)
    b, a = signal.butter(order, wn, btype='low')
    return signal.filtfilt(b, a, rectified)
