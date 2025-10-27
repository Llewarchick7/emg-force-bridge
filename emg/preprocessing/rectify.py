"""Rectification utilities for EMG signals."""
import numpy as np

def full_wave_rectify(x: np.ndarray) -> np.ndarray:
    """Full-wave rectification.

    Args:
        x: 1D signal array.
    Returns:
        Absolute value of the input signal.
    """
    return np.abs(np.asarray(x, dtype=float))
