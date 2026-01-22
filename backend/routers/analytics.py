from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime

from ..db.session import get_db
from .auth import api_key_auth
from ..services.analytics import activation_percent, threshold_crossings, rms_over_window
from services.psd import psd_metrics
from db.models import EMGSample
from models.schemas import PSDResponse

router = APIRouter(dependencies=[Depends(api_key_auth)])


@router.get("/activation")
def get_activation(channel: int, start: str, end: str, threshold: float = 0.1, db: Session = Depends(get_db)):
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid datetime format; use ISO 8601")
    pct, count = activation_percent(db, channel, start_dt, end_dt, threshold)
    return {"activation_percent": pct, "sample_count": count}


@router.get("/threshold-crossings")
def get_threshold_crossings(channel: int, start: str, end: str, threshold: float = 0.1, db: Session = Depends(get_db)):
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid datetime format; use ISO 8601")
    crossings = threshold_crossings(db, channel, start_dt, end_dt, threshold)
    return {"crossings": crossings}


@router.get("/rms")
def get_rms(channel: int, start: str, end: str, db: Session = Depends(get_db)):
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid datetime format; use ISO 8601")
    rms = rms_over_window(db, channel, start_dt, end_dt)
    return {"rms": rms}


@router.get("/psd", response_model=PSDResponse)
def get_psd(
    channel: int = Query(..., ge=0),
    start: str = Query(...),
    end: str = Query(...),
    db: Session = Depends(get_db),
):
    """Compute simple FFT-based PSD for samples in [start, end] for a channel."""
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid datetime format; use ISO 8601")
    rows = (
        db.query(EMGSample)
        .filter(EMGSample.channel == channel, EMGSample.timestamp >= start_dt, EMGSample.timestamp <= end_dt)
        .order_by(EMGSample.timestamp.asc())
        .all()
    )
    if not rows:
        return {"freqs": [], "psd": [], "mnf": 0.0, "mdf": 0.0}
    # Estimate sampling rate from timestamps
    ts = [r.timestamp for r in rows]
    if len(ts) >= 2:
        dts = [(ts[i+1]-ts[i]).total_seconds() for i in range(len(ts)-1)]
        dts = [d for d in dts if d > 0]
        fs = 1.0 / (sum(dts)/len(dts)) if dts else 1000.0
    else:
        fs = 1000.0
    import numpy as np
    x = np.array([r.raw for r in rows], dtype=float)
    freqs, psd, mnf, mdf = psd_metrics(x, fs)
    return {
        "freqs": [float(f) for f in freqs.tolist()],
        "psd": [float(p) for p in psd.tolist()],
        "mnf": float(mnf),
        "mdf": float(mdf),
    }
