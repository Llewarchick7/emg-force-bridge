"""
Database models.

Models define the structure of the database tables using SQLAlchemy ORM.

"""



from sqlalchemy import Column, Integer, Float, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from db.session import Base


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
