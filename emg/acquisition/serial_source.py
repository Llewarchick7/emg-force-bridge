"""Acquisition utilities for reading EMG samples from a serial stream.

This module provides a simple CSV reader compatible with the Arduino sketch
that prints either "timestamp_us,adc" or just "adc" on each line.
"""
from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Iterator, Tuple

import serial

@dataclass
class SerialConfig:
    """Serial connection configuration.

    Attributes:
        port: Serial port name (e.g., "COM3" on Windows or "/dev/ttyACM0" on Linux).
        baud: Baud rate. Must match the firmware (default 115200).
    """
    port: str
    baud: int = 115200


def read_serial_csv(cfg: SerialConfig) -> Iterator[Tuple[float, float]]:
    """Read CSV lines from a serial device and yield (t_seconds, value).

    The input may be either "timestamp_us,adc" or just "adc". When the
    timestamp is missing, the function emits a monotonic host-side timestamp
    starting from the first received sample.

    Args:
        cfg: Serial configuration.
    Yields:
        (t_seconds, value) tuples.
    """
    with serial.Serial(cfg.port, cfg.baud, timeout=1) as ser:
        t0 = time.monotonic()
        while True:
            line = ser.readline().decode(errors="ignore").strip()
            if not line:
                continue
            parts = line.split(',')
            try:
                if len(parts) == 2:
                    ts_us = float(parts[0])
                    val = float(parts[1])
                    yield ts_us / 1e6, val
                else:
                    val = float(parts[0])
                    yield (time.monotonic() - t0), val
            except ValueError:
                # Skip malformed lines rather than raising.
                continue


