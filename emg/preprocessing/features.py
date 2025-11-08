from __future__ import annotations
import numpy as np
from .envelope import sliding_rms, sliding_rms_seconds

__all__ = [
    "estimate_fs",
    "compute_metrics",
]

def estimate_fs(t: np.ndarray, default: float = 1000.0) -> float:
    """Estimate sampling rate from a time array in seconds using median dt.
    Returns default when not computable.
    """
    if t is None or len(t) < 2:
        return float(default)
    t = np.asarray(t, dtype=float)
    dt = np.diff(t)
    dt = dt[(dt > 0) & np.isfinite(dt)]
    if dt.size == 0:
        return float(default)
    return float(1.0 / np.median(dt))

def _psd_metrics(sig: np.ndarray, fs: float) -> tuple[float, float]:
    """Return (MNF, MDF) using simple FFT-based PSD metrics."""
    if fs <= 0 or sig.size < 2:
        return 0.0, 0.0
    x = np.asarray(sig, dtype=float)
    x = x - np.mean(x)
    yf = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(x.size, d=1.0/float(fs))
    psd = np.abs(yf) ** 2
    psd_sum = float(np.sum(psd))
    if psd_sum <= 0:
        return 0.0, 0.0
    mnf = float(np.sum(freqs * psd) / psd_sum)
    cumsum = np.cumsum(psd)
    half = cumsum[-1] / 2.0
    idx = int(np.searchsorted(cumsum, half))
    mdf = float(freqs[idx]) if idx < freqs.size else 0.0
    return mnf, mdf

def compute_metrics(t: np.ndarray, sig: np.ndarray, fs: float, rms_window_s: float = 0.10) -> dict:
    """Compute basic EMG metrics for a time segment.
    Returns dict with keys: peak_env, iemg, time_to_peak_s, median_freq_hz, env
    """
    t = np.asarray(t, dtype=float)
    x = np.asarray(sig, dtype=float)
    if x.size < 3:
        return {}
    # Envelope using RMS of centered signal
    xc = x - np.mean(x)
    env = sliding_rms_seconds(xc, fs, rms_window_s)
    dt = 1.0 / float(fs) if fs > 0 else 0.0
    iemg = float(np.sum(env) * dt)
    peak = float(np.max(env))
    t_to_peak = float(t[np.argmax(env)] - t[0]) if t.size > 0 else 0.0
    # Median frequency via PSD
    _, mdf = _psd_metrics(x, fs)
    return {
        "peak_env": peak,
        "iemg": iemg,
        "time_to_peak_s": t_to_peak,
        "median_freq_hz": mdf,
        "env": env,
    }
