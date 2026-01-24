"""Frequency-domain feature utilities for EMG.

Functions compute power spectra (Welch/FFT) and summary frequencies commonly
used for EMG fatigue and spectral analysis. Centralized here so both backend
APIs and offline tools share consistent implementations.
"""
from __future__ import annotations
import numpy as np
from scipy import signal
from typing import Tuple


def welch_psd(
    x: np.ndarray,
    fs: float = 1.0,
    window: str | tuple | np.ndarray = "hann",
    nperseg: int | None = None,
    noverlap: int | None = None,
    nfft: int | None = None,
    detrend: str | None = "constant",
    return_onesided: bool = True,
    scaling: str = "density",
    axis: int = -1,
    average: str = "mean",
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute Welch power spectral density with full parameter control.

    Args:
        x: 1D EMG signal samples.
        fs: Sampling rate in Hz.
        window: Window function (name), tuple config, or array.
        nperseg: Segment length. If None, SciPy default (256) is used.
        noverlap: Overlap between segments. If None, SciPy default is used.
        nfft: Length of FFT used; increases frequency resolution if > nperseg.
        detrend: Detrend mode ('constant', 'linear') or None.
        return_onesided: If True (default) return one-sided spectrum for real data.
        scaling: 'density' (power/Hz) or 'spectrum' (power).
        axis: Axis along which the periodogram is computed.
        average: 'mean' (default) or 'median' segment averaging.
    Returns:
        (f, Pxx) where f are frequency bins (Hz) and Pxx is PSD.
    """
    x = np.asarray(x, dtype=float)
    if x.ndim != 1:
        x = np.ravel(x)
    # Clip nperseg to signal length when provided; else let SciPy choose default
    nperseg_eff = None if nperseg is None else max(1, min(int(nperseg), int(x.size)))
    f, Pxx = signal.welch(
        x,
        fs=fs,
        window=window,
        nperseg=nperseg_eff,
        noverlap=noverlap,
        nfft=nfft,
        detrend=detrend,
        return_onesided=return_onesided,
        scaling=scaling,
        axis=axis,
        average=average,
    )
    return f, Pxx


def fft_psd(x: np.ndarray, fs: float) -> Tuple[np.ndarray, np.ndarray]:
    """Compute simple one-sided FFT-based PSD (|X|^2) for reference/compat.

    Args:
        x: 1D EMG signal samples.
        fs: Sampling rate in Hz.
    Returns:
        (f, Pxx) where f are frequency bins (Hz) and Pxx is unnormalized power.
    """
    x = np.asarray(x, dtype=float)
    if fs <= 0 or x.size < 2:
        return np.array([]), np.array([])
    x = x - np.mean(x)
    yf = np.fft.rfft(x)
    f = np.fft.rfftfreq(x.size, d=1.0/float(fs))
    Pxx = np.abs(yf) ** 2
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


def bandlimit_psd(
    f: np.ndarray,
    Pxx: np.ndarray,
    fmin: float | None = None,
    fmax: float | None = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Return PSD limited to [fmin, fmax] frequency band.

    If limits are None or invalid, returns inputs unchanged.
    """
    f = np.asarray(f, dtype=float)
    Pxx = np.asarray(Pxx, dtype=float)
    if f.size == 0 or Pxx.size == 0:
        return f, Pxx
    lo = -np.inf if fmin is None else float(fmin)
    hi = np.inf if fmax is None else float(fmax)
    if not np.isfinite(lo):
        lo = -np.inf
    if not np.isfinite(hi):
        hi = np.inf
    mask = (f >= lo) & (f <= hi)
    if not np.any(mask):
        return f[:0], Pxx[:0]
    return f[mask], Pxx[mask]
