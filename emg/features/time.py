"""Time-domain EMG feature functions.

Includes common features used in EMG decoding:
- RMS: Root Mean Square
- MAV: Mean Absolute Value
- WL: Waveform Length
- ZC: Zero Crossings (optional threshold)
- SSC: Slope Sign Changes (optional threshold)
- Willison Amplitude: Count of diffs exceeding a threshold
"""
from __future__ import annotations
import numpy as np


def rms(x: np.ndarray) -> float:
    """Root mean square of a window."""
    x = np.asarray(x, dtype=float)
    return float(np.sqrt(np.mean(x * x)))


def mav(x: np.ndarray) -> float:
    """Mean absolute value of a window."""
    x = np.asarray(x, dtype=float)
    return float(np.mean(np.abs(x)))


def wl(x: np.ndarray) -> float:
    """Waveform length (sum of absolute successive differences)."""
    x = np.asarray(x, dtype=float)
    return float(np.sum(np.abs(np.diff(x))))


def zero_crossings(x: np.ndarray, threshold: float = 0.0) -> int:
    """Count zero crossings with optional amplitude threshold.

    If threshold > 0, both samples around a crossing must exceed the
    threshold in magnitude to be counted.
    """
    x = np.asarray(x, dtype=float)
    s = np.sign(x)
    crossings = np.where(np.diff(s) != 0)[0]
    if threshold > 0:
        valid = (np.abs(x[:-1]) > threshold) & (np.abs(x[1:]) > threshold)
        return int(np.sum(valid[crossings]))
    return int(len(crossings))


def slope_sign_changes(x: np.ndarray, threshold: float = 0.0) -> int:
    """Count slope sign changes with optional curvature threshold."""
    x = np.asarray(x, dtype=float)
    dx = np.diff(x)
    ssc = (np.sign(dx[:-1]) != np.sign(dx[1:])) & (np.abs(np.diff(x, n=2)) > threshold)
    return int(np.sum(ssc))


def willison_amplitude(x: np.ndarray, threshold: float = 0.0) -> int:
    """Count of adjacent-sample differences exceeding a threshold."""
    x = np.asarray(x, dtype=float)
    return int(np.sum(np.abs(np.diff(x)) > threshold))
