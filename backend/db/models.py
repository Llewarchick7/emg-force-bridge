"""
Database models.

Models define the structure of the database tables using SQLAlchemy ORM.

"""



from sqlalchemy import Column, Integer, Float, DateTime, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from backend.db.session import Base


class EMGSample(Base):
    """
    Database model for EMG sample data
    """
    __tablename__ = "emg_samples"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    channel: Mapped[int] = mapped_column(Integer, index=True)
    raw: Mapped[float] = mapped_column(Float)
    rect: Mapped[float] = mapped_column(Float)
    envelope: Mapped[float] = mapped_column(Float)
    rms: Mapped[float] = mapped_column(Float)


class IMUSample(Base):
    __tablename__ = "imu_samples"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    z: Mapped[float] = mapped_column(Float)
    ax: Mapped[float] = mapped_column(Float, default=0.0)
    ay: Mapped[float] = mapped_column(Float, default=0.0)
    az: Mapped[float] = mapped_column(Float, default=0.0)
    gx: Mapped[float] = mapped_column(Float, default=0.0)
    gy: Mapped[float] = mapped_column(Float, default=0.0)
    gz: Mapped[float] = mapped_column(Float, default=0.0)


class Patient(Base):
    __tablename__ = "patients"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    injury_side: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sessions: Mapped[list["Session"]] = relationship(back_populates="patient")


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(512), nullable=True)
    patient: Mapped[Patient] = relationship(back_populates="sessions")
    trials: Mapped[list["Trial"]] = relationship(back_populates="session")


class Trial(Base):
    __tablename__ = "trials"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    channel: Mapped[int] = mapped_column(Integer)
    limb: Mapped[str | None] = mapped_column(String(16), nullable=True)
    movement_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    baseline_rms_uv: Mapped[float | None] = mapped_column(Float, nullable=True)
    mvc_rms_uv: Mapped[float | None] = mapped_column(Float, nullable=True)
    session: Mapped[Session] = relationship(back_populates="trials")
