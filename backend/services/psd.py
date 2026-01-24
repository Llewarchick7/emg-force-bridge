from __future__ import annotations
"""Deprecated: spectral helpers are provided by emg.features.freq.

This module remains for backward-compatibility and re-exports minimal FFT PSD.
"""
import numpy as np
from typing import Tuple

from emg.features.freq import fft_psd, mean_frequency, median_frequency


def psd_metrics(sig: np.ndarray, fs: float) -> Tuple[np.ndarray, np.ndarray, float, float]:
    f, Pxx = fft_psd(sig, fs)
    mnf = mean_frequency(f, Pxx) if f.size else 0.0
    mdf = median_frequency(f, Pxx) if f.size else 0.0
    return f, Pxx, mnf, mdf
