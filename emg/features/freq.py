"""Frequency-domain feature utilities for EMG.

Functions compute power spectra (Welch) and summary frequencies commonly used
for EMG fatigue and spectral analysis.
"""
from __future__ import annotations
import numpy as np
from scipy import signal
from typing import Tuple


def welch_psd(x: np.ndarray, fs: float, nperseg: int = 256) -> Tuple[np.ndarray, np.ndarray]:
    """Compute Welch power spectral density.

    Args:
        x: 1D EMG signal samples.
        fs: Sampling rate in Hz.
        nperseg: Window length for each segment.
    Returns:
        (f, Pxx) where f are frequency bins (Hz) and Pxx is PSD (power/Hz).
    """
    x = np.asarray(x, dtype=float)
    f, Pxx = signal.welch(x, fs=fs, nperseg=min(nperseg, len(x)))
    return f, Pxx


def mean_frequency(f: np.ndarray, Pxx: np.ndarray) -> float:
    """Mean frequency of the spectrum (power-weighted average).

    Args:
        f: Frequency bins (Hz).
        Pxx: PSD values aligned with f.
    Returns:
        Mean frequency in Hz.
    """
    f = np.asarray(f, dtype=float)
    Pxx = np.asarray(Pxx, dtype=float)
    num = np.sum(f * Pxx)
    den = np.sum(Pxx) + 1e-12
    return float(num / den)


def median_frequency(f: np.ndarray, Pxx: np.ndarray) -> float:
    """Median frequency of the spectrum (frequency splitting total power in half).

    Args:
        f: Frequency bins (Hz).
        Pxx: PSD values aligned with f.
    Returns:
        Median frequency in Hz.
    """
    f = np.asarray(f, dtype=float)
    Pxx = np.asarray(Pxx, dtype=float)
    cumsum = np.cumsum(Pxx)
    half = cumsum[-1] / 2.0
    idx = int(np.searchsorted(cumsum, half))
    idx = min(idx, len(f) - 1)
    return float(f[idx])
