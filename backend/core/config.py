from pydantic import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    api_key: str = "dev-key"
    sqlite_path: str = str(Path(__file__).resolve().parents[1] / "data" / "app.db")

    class Config:
        env_file = ".env"


settings = Settings()
