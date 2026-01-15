from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session
from typing import List, Union

from ..db.session import get_db
from ..db.models import IMUSample
from ..models.schemas import IMUSampleCreate, IMUSampleRead
from .auth import api_key_auth


router = APIRouter(dependencies=[Depends(api_key_auth)])


@router.post("/", response_model=List[IMUSampleRead])
def ingest_imu(
    payload: Union[IMUSampleCreate, List[IMUSampleCreate]] = Body(...),
    db: Session = Depends(get_db),
):
    items: List[IMUSampleCreate] = payload if isinstance(payload, list) else [payload]
    if not items:
        raise HTTPException(status_code=400, detail="Empty payload")
    saved: List[IMUSample] = []
    for it in items:
        row = IMUSample(
            timestamp=it.timestamp,
            x=it.x,
            y=it.y,
            z=it.z,
            ax=it.ax,
            ay=it.ay,
            az=it.az,
            gx=it.gx,
            gy=it.gy,
            gz=it.gz,
        )
        db.add(row)
        saved.append(row)
    db.commit()
    for r in saved:
        db.refresh(r)
    return saved
