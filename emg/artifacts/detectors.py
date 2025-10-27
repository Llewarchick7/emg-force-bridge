"""Artifact detection helpers for EMG signals.

Provides simple heuristics for common artifacts: motion (low-frequency
contamination), clipping (saturation), and spikes (outliers).
"""
from __future__ import annotations
import numpy as np
from scipy import signal


def detect_motion_lowfreq(x: np.ndarray, fs: float, cutoff_hz: float = 20.0, threshold: float = 3.0) -> bool:
    """Detect motion artifact via low-frequency energy exceeding a threshold.

    Compares the standard deviation of a low-pass filtered version against
    the overall standard deviation of the signal.
    """
    nyq = 0.5 * fs
    wn = min(cutoff_hz / nyq, 0.999999)
    b, a = signal.butter(2, wn, btype='low')
    low = signal.filtfilt(b, a, x)
    return float(np.std(low)) > threshold * (float(np.std(x)) + 1e-12)


def detect_clipping(x: np.ndarray, clip_value: float | None = None) -> bool:
    """Detect whether samples reach or exceed a clip value.

    If clip_value is None, uses the maximum absolute value in the window,
    which detects flat-topped saturation when repeated.
    """
    if clip_value is None:
        clip_value = float(np.max(np.abs(x)))
    return bool(np.any(np.abs(x) >= clip_value))


def detect_spikes(x: np.ndarray, z_thresh: float = 6.0) -> bool:
    """Detect outlier spikes by z-score thresholding."""
    z = (x - np.mean(x)) / (np.std(x) + 1e-12)
    return bool(np.any(np.abs(z) > z_thresh))
