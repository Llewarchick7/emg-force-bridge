"""Filtering utilities for EMG preprocessing.

This module provides both offline (zero-phase) filters using filtfilt and
stateful streaming filters using second-order sections (SOS) for causal
real-time processing.
"""
from __future__ import annotations
import numpy as np
from scipy import signal

# Offline, zero-phase utilities

def apply_bandpass(
    data: np.ndarray,
    lowcut: float | None = 20.0,
    highcut: float | None = 450.0,
    fs: float = 1000.0,
    order: int = 4,
) -> np.ndarray:
    """Zero-phase Butterworth band-pass filter with guardrails.

    - If lowcut is None: behaves as low-pass
    - If highcut is None: behaves as high-pass
    - If invalid parameters (e.g., lowcut >= highcut), returns input unchanged

    Returns filtered signal with same length as input.
    """
    x = np.asarray(data, dtype=float)
    if x.size < 10 or fs <= 0:
        return x
    nyq = 0.5 * float(fs)
    # Normalize and clamp
    lo = None if lowcut is None else max(float(lowcut), 0.0)
    hi = None if highcut is None else max(float(highcut), 0.0)

    # Routes for single-sided filters
    if lo is None and hi is not None:
        wn = min(hi / nyq, 0.999999)
        if not (0 < wn < 1):
            return x
        b, a = signal.butter(order, wn, btype='low')
        return signal.filtfilt(b, a, x)
    if hi is None and lo is not None:
        wn = max(lo / nyq, 1e-6)
        if not (0 < wn < 1):
            return x
        b, a = signal.butter(order, wn, btype='high')
        return signal.filtfilt(b, a, x)

    # Both provided: band-pass
    if lo is None or hi is None:
        return x
    if lo >= hi:
        # invalid band, passthrough
        return x
    low_n = max(lo / nyq, 1e-6)
    high_n = min(hi / nyq, 0.999999)
    if not (0 < low_n < high_n < 1):
        return x
    try:
        b, a = signal.butter(order, [low_n, high_n], btype='band')
        return signal.filtfilt(b, a, x)
    except Exception:
        return x


def apply_notch(
    data: np.ndarray,
    notch_freq: float = 60.0,
    fs: float = 1000.0,
    q: float = 30.0,
) -> np.ndarray:
    """Zero-phase IIR notch filter for power-line interference (guarded).

    Returns passthrough when parameters are invalid or input is too short,
    to keep real-time pipelines resilient.
    """
    x = np.asarray(data, dtype=float)
    try:
        if x.size < 10 or fs <= 0 or notch_freq <= 0:
            return x
        # Normalize and clamp to (0,1)
        w0 = float(notch_freq) / (float(fs) / 2.0)
        w0 = min(0.999, max(1e-6, w0))
        if not (0 < w0 < 1):
            return x
        b, a = signal.iirnotch(w0, q)
        # filtfilt can still fail on very short vectors; guard via try/except
        return signal.filtfilt(b, a, x)
    except Exception:
        return x


def apply_highpass(data: np.ndarray, cutoff: float, fs: float, order: int = 2) -> np.ndarray:
    """Zero-phase Butterworth high-pass filter."""
    x = np.asarray(data, dtype=float)
    if x.size < 10 or fs <= 0 or cutoff is None:
        return x
    nyq = 0.5 * float(fs)
    wn = max(float(cutoff) / nyq, 1e-6)
    if not (0 < wn < 1):
        return x
    b, a = signal.butter(order, wn, btype='high')
    return signal.filtfilt(b, a, x)


def apply_lowpass(data: np.ndarray, cutoff: float, fs: float, order: int = 4) -> np.ndarray:
    """Zero-phase Butterworth low-pass filter."""
    x = np.asarray(data, dtype=float)
    if x.size < 10 or fs <= 0 or cutoff is None:
        return x
    nyq = 0.5 * float(fs)
    wn = min(float(cutoff) / nyq, 0.999999)
    if not (0 < wn < 1):
        return x
    b, a = signal.butter(order, wn, btype='low')
    return signal.filtfilt(b, a, x)

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
