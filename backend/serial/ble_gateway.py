import asyncio
import struct
import time
from typing import Optional, Deque, List
from collections import deque

import requests
from bleak import BleakClient, BleakScanner

API_KEY = "dev-key"  # override via ENV if desired
BACKEND_URL = "http://127.0.0.1:8000"  # change if running elsewhere
# UUIDs must match your ESP32 GATT service
SERVICE_UUID = "0000abcd-0000-1000-8000-00805f9b34fb"
CHAR_UUID = "0000abce-0000-1000-8000-00805f9b34fb"  # notify characteristic
DEVICE_NAME = "emg-force-bridge"  # or MAC address if preferred

# Packet: 12 bytes little-endian: ts_ms (u32), env_mv (u16), rms_mv (u16), active (u8), quality (u8), seq (u16)
PACK_FMT = "<IHHBBH"
PACK_SZ = 12

BATCH_SIZE = 50
POST_INTERVAL_SEC = 0.25
CHANNEL_DEFAULT = 0

class IngestBuffer:
    def __init__(self):
        self.buf: Deque[dict] = deque()
        self.last_post = time.time()

    def add(self, sample: dict):
        self.buf.append(sample)

    def should_post(self) -> bool:
        return len(self.buf) >= BATCH_SIZE or (time.time() - self.last_post) >= POST_INTERVAL_SEC

    def drain(self) -> List[dict]:
        items = list(self.buf)
        self.buf.clear()
        self.last_post = time.time()
        return items


ingest = IngestBuffer()


def build_emg_json(ts_ms: int, env_mv: int, rms_mv: int, active: int, quality: int, seq: int) -> dict:
    # If ts_ms is device uptime, use server time for DB; include ts_ms as seq_meta
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    return {
        "timestamp": now_iso,
        "channel": CHANNEL_DEFAULT,
        "raw": 0.0,
        "rect": float(env_mv) / 1000.0 if env_mv >= 0 else 0.0,
        "envelope": float(env_mv) / 1000.0,
        "rms": float(rms_mv) / 1000.0,
        # Optionally, include metadata in a separate endpoint if needed
    }


async def find_device(name: Optional[str] = None) -> Optional[str]:
    devices = await BleakScanner.discover()
    for d in devices:
        if name and d.name and d.name.lower() == name.lower():
            return d.address
    return None


async def run_gateway():
    addr = await find_device(DEVICE_NAME)
    if not addr:
        print("Device not found; ensure it is advertising and in range.")
        return
    print(f"Connecting to {addr}...")

    async with BleakClient(addr) as client:
        ok = await client.is_connected()
        if not ok:
            print("Failed to connect.")
            return
        print("Connected.")

        def handle_notify(_, data: bytearray):
            if len(data) != PACK_SZ:
                return
            ts_ms, env_mv, rms_mv, active, quality, seq = struct.unpack(PACK_FMT, data)
            sample = build_emg_json(ts_ms, env_mv, rms_mv, active, quality, seq)
            ingest.add(sample)

        await client.start_notify(CHAR_UUID, handle_notify)
        print("Subscribed to notifications.")

        try:
            while True:
                await asyncio.sleep(0.05)
                if ingest.should_post():
                    items = ingest.drain()
                    try:
                        r = requests.post(
                            f"{BACKEND_URL}/emg",
                            json=items,
                            headers={"X-API-Key": API_KEY},
                            timeout=5,
                        )
                        if r.status_code >= 300:
                            print("POST failed:", r.status_code, r.text)
                        else:
                            print(f"Posted {len(items)} EMG samples")
                    except Exception as e:
                        print("POST error:", e)
        finally:
            await client.stop_notify(CHAR_UUID)
            print("Unsubscribed.")


if __name__ == "__main__":
    asyncio.run(run_gateway())
