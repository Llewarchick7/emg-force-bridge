"""Windowing helpers for feature extraction."""
from __future__ import annotations
import numpy as np
from typing import Iterator, Tuple


def sliding_windows(x: np.ndarray, window: int, step: int) -> Iterator[Tuple[int, np.ndarray]]:
    """Yield overlapping windows of a 1D array.

    Args:
        x: Input array.
        window: Window length in samples.
        step: Hop size in samples.
    Yields:
        (start_idx, window_array) for each window.
    """
    n = len(x)
    if window <= 0 or step <= 0:
        return
    for start in range(0, n - window + 1, step):
        yield start, x[start:start+window]
