"""Configuration dataclasses for the EMG pipeline.

This module centralizes tunable parameters (sampling, filter bands, windowing,
thresholds) so experiments and real-time scripts share a consistent setup.
"""
from dataclasses import dataclass

@dataclass
class EMGConfig:
    """Top-level configuration for EMG preprocessing and feature extraction.

    Attributes:
        sample_rate_hz: Sampling rate (Hz). 1000 Hz is a common default.
        bandpass_low_hz: Lower cutoff for software band-pass (Hz).
        bandpass_high_hz: Upper cutoff for software band-pass (Hz).
        notch_hz: Power-line notch frequency (50 or 60). None to disable.
        notch_q: Quality factor for notch filter (higher = narrower).
        envelope_method: "rms" or "lowpass" for envelope extraction.
        envelope_lp_cut_hz: Low-pass cutoff for envelope when using "lowpass".
        rms_window_ms: RMS window length (ms) when using "rms" envelope.
        feature_window_ms: Feature window length (ms).
        feature_step_ms: Step between consecutive windows (ms).
        zc_threshold: Threshold for zero crossings.
        ssc_threshold: Threshold for slope sign changes.
        willison_threshold: Threshold for Willison amplitude.
        mvc_value: Optional MVC reference for normalization (units of envelope).
        baseline_mean: Optional baseline mean for normalization.
        baseline_std: Optional baseline std for normalization.
    """

    # Sampling
    sample_rate_hz: int = 1000

    # Filtering (software)
    bandpass_low_hz: float = 20.0
    bandpass_high_hz: float = 450.0
    notch_hz: float | None = 60.0
    notch_q: float = 30.0

    # Envelope
    envelope_method: str = "rms"  # or "lowpass"
    envelope_lp_cut_hz: float = 5.0
    rms_window_ms: int = 100

    # Windowing
    feature_window_ms: int = 200
    feature_step_ms: int = 100

    # Thresholds
    zc_threshold: float = 0.01
    ssc_threshold: float = 0.01
    willison_threshold: float = 0.02

    # Normalization
    mvc_value: float | None = None
    baseline_mean: float | None = None
    baseline_std: float | None = None
