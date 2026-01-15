from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    api_key: str | None = "dev-key"
    sqlite_path: str = str(Path(__file__).resolve().parents[1] / "data" / "app.db")
    # pydantic v2 settings config
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


settings = Settings()
