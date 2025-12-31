from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from db.session import get_db
from routers.auth import api_key_auth
from services.analytics import activation_percent, threshold_crossings, rms_over_window

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
