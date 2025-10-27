#!/usr/bin/env python
"""Offline processing demo: load CSV with a column 'value', apply filters and envelope, write features CSV."""
import argparse
import pandas as pd
import numpy as np
from pathlib import Path

from emg.config import EMGConfig
from emg.preprocessing.filters import apply_bandpass, apply_notch
from emg.preprocessing.rectify import full_wave_rectify
from emg.preprocessing.envelope import sliding_rms
from emg.windowing import sliding_windows
from emg.features.time import rms, mav, wl, zero_crossings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_csv", type=Path)
    ap.add_argument("output_csv", type=Path)
    ap.add_argument("--fs", type=int, default=1000)
    args = ap.parse_args()

    cfg = EMGConfig(sample_rate_hz=args.fs)
    df = pd.read_csv(args.input_csv)
    x = df["value"].to_numpy(float)

    x = apply_bandpass(x, cfg.bandpass_low_hz, cfg.bandpass_high_hz, cfg.sample_rate_hz)
    if cfg.notch_hz:
        x = apply_notch(x, cfg.notch_hz, cfg.sample_rate_hz, cfg.notch_q)
    xr = full_wave_rectify(x)
    env = sliding_rms(xr, int(cfg.rms_window_ms * cfg.sample_rate_hz / 1000))

    win = int(cfg.feature_window_ms * cfg.sample_rate_hz / 1000)
    step = int(cfg.feature_step_ms * cfg.sample_rate_hz / 1000)

    rows = []
    for start, w in sliding_windows(env, win, step):
        rows.append({
            "start": start,
            "rms": rms(w),
            "mav": mav(w),
            "wl": wl(w),
            "zc": zero_crossings(w, threshold=cfg.zc_threshold),
        })
    out = pd.DataFrame(rows)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output_csv, index=False)


if __name__ == "__main__":
    main()
