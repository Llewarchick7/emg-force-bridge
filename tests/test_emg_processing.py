import math
import numpy as np

from backend.services import emg_processing as ep


def test_fill_missing_fields_computes_when_missing_fields():
    # Use a fresh channel id to avoid state leakage
    ch = 101
    raws = [0.0, 0.1, -0.1, 0.2, -0.2, 0.3, -0.3]
    out = [ep.fill_missing_fields(channel=ch, raw=r, rect=None, envelope=None, rms=None) for r in raws]
    # All outputs should be finite and non-negative
    for rect, env, rms in out:
        assert math.isfinite(rect) and math.isfinite(env) and math.isfinite(rms)
        assert rect >= 0.0 and env >= 0.0 and rms >= 0.0
    # Last envelope and rms should be > 0 after warm-up
    assert out[-1][1] > 0.0
    assert out[-1][2] > 0.0


def test_bandpass_alignment_high_freq_has_higher_metrics():
    # Two channels: low freq (10 Hz) and high freq (100 Hz)
    fs = ep.FS_HZ
    t = np.arange(int(fs)) / fs  # 1 second
    x_low = np.sin(2 * np.pi * 10.0 * t)
    x_high = np.sin(2 * np.pi * 100.0 * t)

    ch_low, ch_high = 202, 203
    # Reset state to be sure
    ep._processor.reset(ch_low)
    ep._processor.reset(ch_high)

    env_low = rms_low = None
    env_high = rms_high = None
    for r in x_low:
        _, env_low, rms_low = ep.fill_missing_fields(channel=ch_low, raw=float(r), rect=None, envelope=None, rms=None)
    for r in x_high:
        _, env_high, rms_high = ep.fill_missing_fields(channel=ch_high, raw=float(r), rect=None, envelope=None, rms=None)

    # Band-pass (20–450 Hz) should attenuate 10 Hz; 100 Hz should pass
    assert env_high > env_low
    assert rms_high > rms_low


def test_provided_fields_passthrough():
    ch = 304
    rect_in, env_in, rms_in = 0.3, 0.4, 0.2
    rect, env, rms = ep.fill_missing_fields(channel=ch, raw=0.5, rect=rect_in, envelope=env_in, rms=rms_in)
    assert rect == rect_in and env == env_in and rms == rms_in
