"""Minimal streaming pipeline abstractions for real-time EMG."""
from __future__ import annotations
from typing import Protocol, Any, Iterable

class Stage(Protocol):
    """A pipeline stage with optional reset and a transform method."""
    def reset(self) -> None: ...
    def transform(self, x): ...

class Pipeline:
    """Simple sequential pipeline for streaming data."""
    def __init__(self, stages: Iterable[Stage]):
        self.stages = list(stages)

    def reset(self):
        for s in self.stages:
            if hasattr(s, "reset"):
                s.reset()

    def transform(self, x):
        y = x
        for s in self.stages:
            y = s.transform(y)
        return y
