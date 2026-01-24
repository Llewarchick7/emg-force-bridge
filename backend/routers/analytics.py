from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime

from backend.db.session import get_db
from backend.routers.auth import api_key_auth
from backend.services.analytics import activation_percent, threshold_crossings, rms_over_window
from emg.features.freq import welch_psd, fft_psd, mean_frequency, median_frequency, bandlimit_psd
from backend.db.models import EMGSample
from backend.models.schemas import PSDResponse

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
    method: str = Query("welch", pattern="^(fft|welch)$"),
    # Welch parameters (pass-through)
    window: str | None = Query("hann"),
    nperseg: int | None = Query(None, ge=4),
    noverlap: int | None = Query(None, ge=0),
    nfft: int | None = Query(None, ge=4),
    detrend: str | None = Query("constant"),
    return_onesided: bool = Query(True),
    scaling: str = Query("density", pattern="^(density|spectrum)$"),
    average: str = Query("mean", pattern="^(mean|median)$"),
    # Band limits (Hz)
    fmin: float | None = Query(None, ge=0.0),
    fmax: float | None = Query(None, ge=0.0),
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
    if method == "welch":
        detrend_param = None if (detrend or "").lower() == "none" else detrend
        freqs, psd = welch_psd(
            x,
            fs,
            window=window or "hann",
            nperseg=nperseg,
            noverlap=noverlap,
            nfft=nfft,
            detrend=detrend_param,
            return_onesided=return_onesided,
            scaling=scaling,
            average=average,
        )
    else:
        freqs, psd = fft_psd(x, fs)
    # Apply band limits before computing summary frequencies
    freqs_band, psd_band = bandlimit_psd(freqs, psd, fmin=fmin, fmax=fmax)
    mnf = mean_frequency(freqs_band, psd_band) if freqs_band.size else 0.0
    mdf = median_frequency(freqs_band, psd_band) if freqs_band.size else 0.0
    return {
        "freqs": [float(f) for f in freqs_band.tolist()],
        "psd": [float(p) for p in psd_band.tolist()],
        "mnf": float(mnf),
        "mdf": float(mdf),
    }
