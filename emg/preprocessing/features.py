"""Feature and metric extraction for EMG segments.

Metrics Implemented
-------------------
1. Sampling Rate Estimate "estimate_fs" using median inter‑sample interval.
2. Time‑domain metrics via "compute_metrics":
    - Peak envelope :math:`\max e[n]`
    - Integrated EMG (iEMG): :math:`\text{iEMG} = \sum_n e[n] \Delta t` approximates area under the envelope.
    - Time‑to‑Peak: first timestamp of envelope maximum minus segment start.
    - Median Frequency (MDF): frequency below which 50% of total spectral power lies.
    - Envelope sequence used for overlays.

Frequency Metrics (MNF/MDF)
---------------------------
For a zero‑mean windowed signal :math:`x[n]`, compute the one‑sided FFT
"rfft" giving bins :math:`X[k]`, frequencies :math:`f_k`, and power spectral
density (unnormalized) :math:`P[k] = |X[k]|^2`.

Mean Frequency (MNF):
.. math:: \text{MNF} = \frac{\sum_k f_k P[k]}{\sum_k P[k]}

Median Frequency (MDF): smallest :math:`f_m` such that
.. math:: \sum_{k : f_k \le f_m} P[k] \ge \tfrac{1}{2} \sum_k P[k]

Rationale
---------
MDF is often used to approximate muscle fatigue trends (downward shift over
time). Peak envelope and iEMG relate to intensity of activation. Time‑to‑peak
can characterize contraction dynamics.

Resilience
----------
Functions degrade gracefully: empty or degenerate inputs return defaults.
"""
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
    """
    Compute mean (MNF) and median frequency (MDF) of the EMG signal using FFT-based PSD.
    
    Args: 
        sig: EMG signal array.
        fs: Sampling frequency in Hz.
    
    Returns:
        tuple[float, float]: (MNF, MDF) using simple FFT-based PSD metrics.
    """
    if fs <= 0 or sig.size < 2:
        return 0.0, 0.0
    n = np.asarray(sig, dtype=float) # Convert signal to float array of n samples
    n = n - np.mean(n) # Zero-mean the signal
    yf = np.fft.rfft(n) # Compute the one-sided FFT of the zero-mean signal
    freqs = np.fft.rfftfreq(n.size, d=1.0/float(fs)) # Frequency bins corresponding to FFT
    psd = np.abs(yf) ** 2 # Power spectral density (unnormalized)
    psd_sum = float(np.sum(psd)) # Total power in the PSD
    if psd_sum <= 0:
        return 0.0, 0.0
    mnf = float(np.sum(freqs * psd) / psd_sum) # Mean frequency
    cumsum = np.cumsum(psd) # Cumulative sum of the PSD
    half = cumsum[-1] / 2.0 # Half of the cumulative sum
    idx = int(np.searchsorted(cumsum, half)) # Index of the median frequency
    mdf = float(freqs[idx]) if idx < freqs.size else 0.0 # Median frequency
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
    env = sliding_rms_seconds(xc, fs, rms_window_s) # Compute RMS envelope over sliding window
    dt = 1.0 / float(fs) if fs > 0 else 0.0
    iemg = float(np.sum(env) * dt) # Integrated EMG (area under the envelope)
    peak = float(np.max(env)) # Peak envelope value
    t_to_peak = float(t[np.argmax(env)] - t[0]) if t.size > 0 else 0.0 # Time to peak
    # Median frequency via PSD
    _, mdf = _psd_metrics(x, fs) # Compute median frequency via PSD
    return {
        "peak_env": peak,
        "iemg": iemg,
        "time_to_peak_s": t_to_peak,
        "median_freq_hz": mdf,
        "env": env,
    }
