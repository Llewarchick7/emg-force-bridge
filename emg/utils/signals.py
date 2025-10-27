"""Small signal utilities used across the pipeline."""
from __future__ import annotations
import numpy as np


def dc_offset(x: np.ndarray) -> float:
    """Compute mean (DC) of a signal."""
    return float(np.mean(x))


def detrend_mean(x: np.ndarray) -> np.ndarray:
    """Subtract mean from a signal."""
    return x - np.mean(x)
