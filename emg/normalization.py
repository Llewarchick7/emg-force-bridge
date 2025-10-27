"""Normalization utilities for EMG envelopes.

Supports baseline subtraction/z-scoring and percent of MVC normalization.
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass

@dataclass
class Normalizer:
    """Stateful normalizer for EMG features/envelopes.

    Attributes:
        mvc_value: Reference maximum voluntary contraction (MVC) value.
        baseline_mean: Baseline mean for subtraction or z-scoring.
        baseline_std: Baseline std for z-scoring.
    """
    mvc_value: float | None = None
    baseline_mean: float | None = None
    baseline_std: float | None = None

    def fit_baseline(self, x: np.ndarray):
        """Estimate baseline mean and std from a baseline segment."""
        self.baseline_mean = float(np.mean(x))
        self.baseline_std = float(np.std(x) + 1e-12)
        return self

    def fit_mvc(self, mvc_window: np.ndarray):
        """Record MVC value from a calibration window (max of window)."""
        self.mvc_value = float(np.max(mvc_window))
        return self

    def subtract_baseline(self, x: np.ndarray) -> np.ndarray:
        """Subtract baseline mean if available; otherwise return x unchanged."""
        if self.baseline_mean is None:
            return x
        return x - self.baseline_mean

    def zscore(self, x: np.ndarray) -> np.ndarray:
        """Z-score using baseline stats if available; otherwise return x."""
        if self.baseline_mean is None or self.baseline_std is None:
            return x
        return (x - self.baseline_mean) / self.baseline_std

    def to_percent_mvc(self, x: np.ndarray) -> np.ndarray:
        """Convert to percent of MVC if mvc_value is set and positive."""
        if not self.mvc_value or self.mvc_value <= 0:
            return x
        return (x / self.mvc_value) * 100.0
