"""Preprocessing subpackage for EMG signals.
Exports common helpers for filters, envelopes, and feature computation.
"""
from .filters import apply_bandpass, apply_notch
from .envelope import sliding_rms
