"""Rectification utilities for EMG signals.

Full‑wave rectification maps the raw bipolar EMG signal :math:`x[n]` to its
absolute value :math:`|x[n]|`, preserving amplitude while discarding phase.
This is a preprocessing step prior to envelope extraction and iEMG features.
"""
import numpy as np

def full_wave_rectify(x: np.ndarray) -> np.ndarray:
    """Full-wave rectification.

    Args:
        x: 1D signal array.
    Returns:
        Absolute value of the input signal.
    """
    return np.abs(np.asarray(x, dtype=float))
