from __future__ import annotations
"""Backend EMG processing helpers delegating to emg preprocessing modules.

Goal: Avoid reimplementing algorithms; reuse emg.preprocessing rectification,
envelope, and RMS functions with short per-channel buffers and return the
latest values for ingestion.
"""
from collections import deque
from typing import Dict, Optional, Tuple
import numpy as np

from emg.preprocessing.rectify import full_wave_rectify
from emg.preprocessing.envelope import lowpass_envelope, sliding_rms_seconds
from emg.preprocessing.filters import apply_bandpass

# Explicit processing constants (aligned with firmware)
FS_HZ = 860.0
BANDPASS_LOW_HZ = 20.0
BANDPASS_HIGH_HZ = 450.0
ENVELOPE_CUTOFF_HZ = 5.0
RMS_WINDOW_S = 0.10
BUFFER_SECONDS = 1.0


class _ChannelBuf:
    def __init__(self, maxlen: int):
        self.x = deque(maxlen=maxlen)

    def append(self, v: float):
        self.x.append(float(v))

    def array(self) -> np.ndarray:
        return np.asarray(self.x, dtype=float)


class EMGProcessor:
    def __init__(self, fs: float = FS_HZ, rms_window_s: float = RMS_WINDOW_S, buf_seconds: float = BUFFER_SECONDS):
        self.fs = float(fs)
        self.rms_window_s = float(rms_window_s)
        self.maxlen = max(8, int(self.fs * float(buf_seconds)))
        self._bufs: Dict[int, _ChannelBuf] = {}

    def reset(self, channel: Optional[int] = None) -> None:
        if channel is None:
            self._bufs.clear()
        else:
            self._bufs.pop(channel, None)

    def _buf(self, channel: int) -> _ChannelBuf:
        b = self._bufs.get(channel)
        if b is None:
            b = _ChannelBuf(maxlen=self.maxlen)
            self._bufs[channel] = b
        return b

    def process_sample(self, channel: int, raw: float,
                       rect: Optional[float] = None,
                       envelope: Optional[float] = None,
                       rms: Optional[float] = None) -> Tuple[float, float, float]:
        """Fill missing fields by buffering and using emg.preprocessing functions.

        Returns (rect, envelope, rms)
        """
        b = self._buf(channel)
        b.append(raw if raw == raw else 0.0)  # NaN guard
        x = b.array()

        # Band-pass to align with firmware (20–450 Hz @ 860 Hz)
        try:
            y_bp = apply_bandpass(x, lowcut=BANDPASS_LOW_HZ, highcut=BANDPASS_HIGH_HZ, fs=self.fs, order=4)
        except Exception:
            y_bp = x

        # Rectified value for current sample (|band-passed sample|)
        if rect is None:
            r = float(abs(y_bp[-1])) if y_bp.size else float(abs(raw))
        else:
            r = rect

        # Envelope: low-pass of rectified band-passed buffer; take last element
        if envelope is None:
            try:
                env_buf = lowpass_envelope(full_wave_rectify(y_bp), fs=self.fs, cutoff_hz=ENVELOPE_CUTOFF_HZ, order=2)
                env = float(env_buf[-1])
            except Exception:
                env = r
        else:
            env = envelope

        # RMS: sliding RMS over band-passed signal; take last element
        if rms is None:
            try:
                rms_buf = sliding_rms_seconds(y_bp, fs=self.fs, window_seconds=self.rms_window_s)
                rms_out = float(rms_buf[-1])
            except Exception:
                rms_out = r
        else:
            rms_out = rms

        return r, env, rms_out


# Module-level singleton used by routers/services
_processor = EMGProcessor()


def fill_missing_fields(channel: int, raw: float,
                        rect: Optional[float], envelope: Optional[float], rms: Optional[float]) -> Tuple[float, float, float]:
    """Convenience wrapper returning completed (rect, envelope, rms)."""
    return _processor.process_sample(channel=channel, raw=raw, rect=rect, envelope=envelope, rms=rms)
