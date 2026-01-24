from fastapi import Header, HTTPException, Depends
from backend.core.config import settings


def api_key_auth(x_api_key: str | None = Header(default=None)):
    if settings.api_key and x_api_key == settings.api_key:
        return True
    raise HTTPException(status_code=401, detail="Unauthorized: invalid API key")
