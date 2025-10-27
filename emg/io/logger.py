"""CSV logging utilities for saving features or envelopes."""
from __future__ import annotations
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

@dataclass
class CSVLogger:
    """Lightweight CSV logger that writes dict rows with fixed headers."""
    path: Path
    fieldnames: list[str]
    append: bool = False

    def __post_init__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        mode = 'a' if self.append else 'w'
        self._fh = open(self.path, mode, newline='')
        self._writer = csv.DictWriter(self._fh, fieldnames=self.fieldnames)
        if not self.append:
            self._writer.writeheader()

    def write(self, row: Mapping[str, object]):
        """Write a single row and flush immediately."""
        self._writer.writerow(row)
        self._fh.flush()

    def close(self):
        """Close the underlying file handle."""
        self._fh.close()
