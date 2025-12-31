from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from core.config import settings
from db.session import Base, engine
from routers.emg import router as emg_router
from routers.imu import router as imu_router
from routers.analytics import router as analytics_router

app = FastAPI(title="EMG Force Bridge Backend", version="0.1.0")

# CORS (allow local tools / dashboards)
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# Ensure DB exists
Base.metadata.create_all(bind=engine)

# Routers
app.include_router(emg_router, prefix="/emg", tags=["emg"])
app.include_router(imu_router, prefix="/imu", tags=["imu"])
app.include_router(analytics_router, prefix="/analytics", tags=["analytics"])

@app.get("/health")
def health():
	return {"status": "ok"}
