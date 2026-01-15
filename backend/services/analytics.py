from sqlalchemy.orm import Session
from datetime import datetime
from math import sqrt

from ..db.models import EMGSample


def _query_window(db: Session, channel: int, start: datetime, end: datetime):
    return (
        db.query(EMGSample)
        .filter(EMGSample.channel == channel, EMGSample.timestamp >= start, EMGSample.timestamp <= end)
        .order_by(EMGSample.timestamp.asc())
        .all()
    )


def activation_percent(db: Session, channel: int, start: datetime, end: datetime, threshold: float) -> tuple[float, int]:
    samples = _query_window(db, channel, start, end)
    if not samples:
        return 0.0, 0
    active = sum(1 for s in samples if s.envelope >= threshold)
    return (active / len(samples)) * 100.0, len(samples)


def threshold_crossings(db: Session, channel: int, start: datetime, end: datetime, threshold: float) -> int:
    samples = _query_window(db, channel, start, end)
    crossings = 0
    prev_above = None
    for s in samples:
        above = s.envelope >= threshold
        if prev_above is not None and above != prev_above:
            crossings += 1
        prev_above = above
    return crossings


def rms_over_window(db: Session, channel: int, start: datetime, end: datetime) -> float:
    samples = _query_window(db, channel, start, end)
    if not samples:
        return 0.0
    # Use rectified or raw; here use raw to compute RMS, fall back to provided rms if available
    if all(s.rms is not None for s in samples):
        # Average of provided RMS values (simple proxy)
        return sum(s.rms for s in samples) / len(samples)
    acc = sum((s.raw ** 2) for s in samples)
    return sqrt(acc / len(samples))
