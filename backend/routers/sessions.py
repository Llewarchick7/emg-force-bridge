from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from datetime import datetime

from backend.db.session import get_db
from backend.routers.auth import api_key_auth
from backend.db.models import Patient, Session as SessionModel, Trial as TrialModel, EMGSample
from backend.models.schemas import SessionCreate, SessionRead, TrialCreate, TrialRead, TrialMVCUpdate, TrialBaselineUpdate, NormalizedActivationResponse

router = APIRouter(prefix="/sessions", tags=["sessions"], dependencies=[Depends(api_key_auth)])


@router.post("/", response_model=SessionRead)
def create_session(payload: SessionCreate = Body(...), db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    sess = SessionModel(patient_id=payload.patient_id, started_at=payload.started_at or datetime.utcnow(), notes=payload.notes)
    db.add(sess)
    db.commit(); db.refresh(sess)
    return SessionRead(id=sess.id, patient_id=sess.patient_id, started_at=sess.started_at, ended_at=sess.ended_at, notes=sess.notes)


@router.post("/{session_id}/trials", response_model=TrialRead)
def create_trial(session_id: int, payload: TrialCreate = Body(...), db: Session = Depends(get_db)):
    sess = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    trial = TrialModel(
        session_id=session_id,
        name=payload.name,
        channel=payload.channel,
        limb=payload.limb,
        movement_type=payload.movement_type,
        started_at=payload.started_at or datetime.utcnow(),
        ended_at=payload.ended_at,
        baseline_rms_uv=payload.baseline_rms_uv,
        mvc_rms_uv=payload.mvc_rms_uv,
    )
    db.add(trial)
    db.commit(); db.refresh(trial)
    return TrialRead(
        id=trial.id, session_id=trial.session_id, name=trial.name, channel=trial.channel, limb=trial.limb,
        movement_type=trial.movement_type, started_at=trial.started_at, ended_at=trial.ended_at,
        baseline_rms_uv=trial.baseline_rms_uv, mvc_rms_uv=trial.mvc_rms_uv,
    )


@router.post("/trials/{trial_id}/baseline", response_model=TrialRead)
def set_trial_baseline(trial_id: int, payload: TrialBaselineUpdate = Body(...), db: Session = Depends(get_db)):
    trial = db.query(TrialModel).filter(TrialModel.id == trial_id).first()
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")
    trial.baseline_rms_uv = payload.baseline_rms_uv
    db.commit(); db.refresh(trial)
    return TrialRead(
        id=trial.id, session_id=trial.session_id, name=trial.name, channel=trial.channel, limb=trial.limb,
        movement_type=trial.movement_type, started_at=trial.started_at, ended_at=trial.ended_at,
        baseline_rms_uv=trial.baseline_rms_uv, mvc_rms_uv=trial.mvc_rms_uv,
    )


@router.post("/trials/{trial_id}/mvc", response_model=TrialRead)
def set_trial_mvc(trial_id: int, payload: TrialMVCUpdate = Body(...), db: Session = Depends(get_db)):
    trial = db.query(TrialModel).filter(TrialModel.id == trial_id).first()
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")
    trial.mvc_rms_uv = payload.mvc_rms_uv
    db.commit(); db.refresh(trial)
    return TrialRead(
        id=trial.id, session_id=trial.session_id, name=trial.name, channel=trial.channel, limb=trial.limb,
        movement_type=trial.movement_type, started_at=trial.started_at, ended_at=trial.ended_at,
        baseline_rms_uv=trial.baseline_rms_uv, mvc_rms_uv=trial.mvc_rms_uv,
    )


@router.get("/trials/{trial_id}/normalized", response_model=NormalizedActivationResponse)
def get_trial_normalized_activation(trial_id: int, start: str, end: str, db: Session = Depends(get_db)):
    trial = db.query(TrialModel).filter(TrialModel.id == trial_id).first()
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")
    if not trial.mvc_rms_uv:
        raise HTTPException(status_code=400, detail="MVC not set for trial")
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid datetime format; use ISO 8601")
    rows = (
        db.query(EMGSample)
        .filter(EMGSample.channel == trial.channel, EMGSample.timestamp >= start_dt, EMGSample.timestamp <= end_dt)
        .order_by(EMGSample.timestamp.asc())
        .all()
    )
    import numpy as np
    if not rows:
        return NormalizedActivationResponse(percent_mvc=0.0, rms_uv=0.0, mvc_rms_uv=trial.mvc_rms_uv or 0.0, baseline_rms_uv=trial.baseline_rms_uv, start=start_dt, end=end_dt)
    x = np.array([r.rms for r in rows if r.rms is not None], dtype=float)
    if x.size == 0:
        # fallback to envelope
        x = np.array([r.envelope for r in rows if r.envelope is not None], dtype=float)
    rms_uv = float(np.mean(x)) if x.size else 0.0
    mvc = float(trial.mvc_rms_uv or 1e-6)
    percent = 100.0 * (rms_uv / mvc)
    return NormalizedActivationResponse(percent_mvc=percent, rms_uv=rms_uv, mvc_rms_uv=mvc, baseline_rms_uv=trial.baseline_rms_uv, start=start_dt, end=end_dt)
