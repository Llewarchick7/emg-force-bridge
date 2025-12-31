from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session
from typing import List, Union

from db.session import get_db
from db.models import EMGSample
from models.schemas import EMGSampleCreate, EMGSampleRead
from routers.auth import api_key_auth


router = APIRouter(dependencies=[Depends(api_key_auth)])


@router.post("/", response_model=List[EMGSampleRead])
def ingest_emg(
    payload: Union[EMGSampleCreate, List[EMGSampleCreate]] = Body(...),
    db: Session = Depends(get_db),
):
    items: List[EMGSampleCreate] = payload if isinstance(payload, list) else [payload]
    if not items:
        raise HTTPException(status_code=400, detail="Empty payload")
    saved: List[EMGSample] = []
    for it in items:
        row = EMGSample(
            timestamp=it.timestamp,
            channel=it.channel,
            raw=it.raw,
            rect=it.rect,
            envelope=it.envelope,
            rms=it.rms,
        )
        db.add(row)
        saved.append(row)
    db.commit()
    for r in saved:
        db.refresh(r)
    return saved


@router.get("/latest", response_model=EMGSampleRead)
def get_latest(channel: int, db: Session = Depends(get_db)):
    row = (
        db.query(EMGSample)
        .filter(EMGSample.channel == channel)
        .order_by(EMGSample.timestamp.desc())
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="No samples for channel")
    return row


@router.get("/history", response_model=List[EMGSampleRead])
def get_history(start: str, end: str, channel: int | None = None, db: Session = Depends(get_db)):
    from datetime import datetime

    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    q = db.query(EMGSample).filter(EMGSample.timestamp >= start_dt, EMGSample.timestamp <= end_dt)
    if channel is not None:
        q = q.filter(EMGSample.channel == channel)
    q = q.order_by(EMGSample.timestamp.asc())
    return q.all()
