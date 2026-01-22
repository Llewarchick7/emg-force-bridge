from __future__ import annotations
from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import numpy as np

from db.session import get_db
from db.models import EMGSample
from routers.auth import api_key_auth
from models.schemas import SyntheticEMGRequest
from services.psd import moving_rms

router = APIRouter(dependencies=[Depends(api_key_auth)])


@router.post("/synthetic/emg")
def generate_synthetic_emg(payload: SyntheticEMGRequest = Body(...), db: Session = Depends(get_db)):
    fs = float(payload.fs)
    dur = float(payload.duration_s)
    n = int(max(1, round(fs * dur)))
    t0 = datetime.utcnow()

    # Time vector in seconds
    t = np.arange(n, dtype=float) / fs
    # Simple band-limited synthetic EMG: sum of sinusoids + Gaussian noise
    x = (
        payload.amplitude * (np.sin(2*np.pi*payload.f1_hz*t) + 0.6*np.sin(2*np.pi*payload.f2_hz*t))
        + np.random.normal(0.0, payload.noise_std, size=n)
    )
    rect = np.abs(x)
    env = moving_rms(x, max(1, int(0.05 * fs)))  # 50 ms RMS window
    rms_series = moving_rms(x, max(1, int(0.2 * fs)))  # 200 ms RMS estimate

    rows = []
    for i in range(n):
        ts = t0 + timedelta(seconds=float(i)/fs)
        rows.append(EMGSample(
            timestamp=ts,
            channel=int(payload.channel),
            raw=float(x[i]),
            rect=float(rect[i]),
            envelope=float(env[i]),
            rms=float(rms_series[i]),
        ))
    db.bulk_save_objects(rows)
    db.commit()
    return {"inserted": len(rows), "channel": int(payload.channel), "start": t0, "end": t0 + timedelta(seconds=dur)}
