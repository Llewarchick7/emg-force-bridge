#!/usr/bin/env python
"""Realtime serial processing demo: read serial CSV, filter, envelope, print features."""
import argparse
import numpy as np
from collections import deque

from emg.config import EMGConfig
from emg.acquisition.serial_source import SerialConfig, read_serial_csv
from emg.preprocessing.filters import apply_bandpass, apply_notch
from emg.preprocessing.rectify import full_wave_rectify
from emg.preprocessing.envelope import sliding_rms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True)
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--fs", type=int, default=1000)
    args = ap.parse_args()

    cfg = EMGConfig(sample_rate_hz=args.fs)
    scfg = SerialConfig(port=args.port, baud=args.baud)

    # Simple rolling buffer to approximate windowing in realtime
    win = int(cfg.rms_window_ms * cfg.sample_rate_hz / 1000)
    buf = deque(maxlen=win)

    for t, val in read_serial_csv(scfg):
        buf.append(val)
        if len(buf) < win:
            continue
        x = np.array(buf, dtype=float)
        x = apply_bandpass(x, cfg.bandpass_low_hz, cfg.bandpass_high_hz, cfg.sample_rate_hz)
        if cfg.notch_hz:
            x = apply_notch(x, cfg.notch_hz, cfg.sample_rate_hz, cfg.notch_q)
        env = sliding_rms(full_wave_rectify(x), win)
        print(f"t={t:.3f}s env={float(env[-1]):.4f}")


if __name__ == "__main__":
    main()
