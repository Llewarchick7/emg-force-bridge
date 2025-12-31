from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class EMGSampleCreate(BaseModel):
	# EMG sample creation schema
	timestamp: datetime
	channel: int = Field(ge=0)
	raw: float
	rect: float
	envelope: float
	rms: float


class EMGSampleRead(EMGSampleCreate):
	id: int

	class Config:
		from_attributes = True


class IMUSampleCreate(BaseModel):
	timestamp: datetime
	x: float
	y: float
	z: float
	ax: float = 0.0
	ay: float = 0.0
	az: float = 0.0
	gx: float = 0.0
	gy: float = 0.0
	gz: float = 0.0


class IMUSampleRead(IMUSampleCreate):
	id: int

	class Config:
		from_attributes = True


class AnalyticsRequest(BaseModel):
	channel: int
	start: datetime
	end: datetime
	threshold: float = Field(default=0.1)


class ActivationResponse(BaseModel):
	activation_percent: float
	sample_count: int


class ThresholdCrossingsResponse(BaseModel):
	crossings: int


class RMSResponse(BaseModel):
	rms: float
