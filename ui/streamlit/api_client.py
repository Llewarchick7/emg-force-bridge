"""Simple client for backend EMG API (FastAPI).

Functions:
- fetch_latest(base_url, api_key, channel)
- fetch_history(base_url, api_key, start_iso, end_iso, channel)
"""
from __future__ import annotations
from typing import Optional, Dict, Any, List, Tuple
import requests
from datetime import datetime, timezone


def _headers(api_key: Optional[str]) -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if api_key:
        h["x-api-key"] = api_key
    return h


def fetch_latest(base_url: str, api_key: Optional[str], channel: int) -> Optional[Dict[str, Any]]:
    try:
        url = f"{base_url.rstrip('/')}/emg/latest"
        resp = requests.get(url, params={"channel": channel}, headers=_headers(api_key), timeout=5)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


def fetch_latest_status(base_url: str, api_key: Optional[str], channel: int) -> Tuple[Optional[Dict[str, Any]], int]:
    """Return (json, status_code) for latest endpoint to aid UI diagnostics."""
    try:
        url = f"{base_url.rstrip('/')}/emg/latest"
        resp = requests.get(url, params={"channel": channel}, headers=_headers(api_key), timeout=5)
        if resp.status_code == 200:
            return resp.json(), 200
        return None, resp.status_code
    except Exception:
        return None, -1


def fetch_history(base_url: str, api_key: Optional[str], start_iso: str, end_iso: str, channel: Optional[int] = None) -> List[Dict[str, Any]]:
    try:
        url = f"{base_url.rstrip('/')}/emg/history"
        params = {"start": start_iso, "end": end_iso}
        if channel is not None:
            params["channel"] = int(channel)
        resp = requests.get(url, params=params, headers=_headers(api_key), timeout=10)
        if resp.status_code == 200:
            return resp.json() or []
        return []
    except Exception:
        return []


def post_sample(base_url: str, api_key: Optional[str], channel: int, raw: float, timestamp: Optional[datetime] = None) -> Tuple[Optional[Dict[str, Any]], int]:
    """Post a single EMG sample to backend /emg ingest endpoint.

    Returns (json, status_code). Missing fields (rect/envelope/rms) will be filled by backend.
    """
    try:
        url = f"{base_url.rstrip('/')}/emg"
        ts = timestamp or datetime.now(timezone.utc)
        payload = {
            "timestamp": ts.isoformat(),
            "channel": int(channel),
            "raw": float(raw),
            # optional computed fields omitted to let backend fill them
        }
        resp = requests.post(url, json=payload, headers=_headers(api_key), timeout=5)
        if resp.status_code in (200, 201):
            return resp.json(), resp.status_code
        return None, resp.status_code
    except Exception:
        return None, -1
