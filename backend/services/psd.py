from __future__ import annotations
import numpy as np
from typing import Tuple


def psd_metrics(sig: np.ndarray, fs: float) -> Tuple[np.ndarray, np.ndarray, float, float]:
    """Compute simple FFT-based PSD and return (freqs, psd, mnf, mdf).
    Uses rfft on zero-mean signal, unnormalized power |X|^2.
    """
    if fs <= 0 or sig.size < 2:
        return np.array([]), np.array([]), 0.0, 0.0
    x = np.asarray(sig, dtype=float)
    x = x - np.mean(x)
    yf = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(x.size, d=1.0/float(fs))
    psd = np.abs(yf) ** 2
    total = float(np.sum(psd))
    if total <= 0:
        return freqs, psd, 0.0, 0.0
    mnf = float(np.sum(freqs * psd) / total)
    cumsum = np.cumsum(psd)
    mdf_idx = int(np.searchsorted(cumsum, cumsum[-1] / 2.0))
    mdf = float(freqs[mdf_idx]) if mdf_idx < freqs.size else 0.0
    return freqs, psd, mnf, mdf


def moving_rms(x: np.ndarray, win: int) -> np.ndarray:
    if win <= 1:
        return np.abs(x)
    x2 = np.square(x)
    kernel = np.ones(win) / win
    y = np.sqrt(np.convolve(x2, kernel, mode='same'))
    return y
