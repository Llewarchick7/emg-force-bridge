# EMG Force Bridge - Systems Architecture

## Overview

The EMG Force Bridge system is designed for rapid prototyping of a low-cost EMG feedback device for physical therapists. The architecture implements a complete data pipeline from hardware sensor acquisition through BLE wireless transmission to cloud storage and real-time visualization.

## System Components

### 1. Hardware Layer (ESP32-S3 Firmware)
**Location:** `/firmware/`

The firmware runs on an ESP32-S3 microcontroller and manages:
- **EMG Sensor Interface:** ADS1115 16-bit ADC sampling at ~860 SPS
- **Signal Processing:** Real-time filtering, rectification, and envelope extraction
- **BLE GATT Server:** NimBLE stack for wireless transmission
- **Data Packetization:** Efficient 12-byte packets for reliable BLE transmission

**Key Files:**
- `firmware/src/main.c` - Application entry point
- `firmware/src/services/ble_emg.c` - BLE GATT peripheral implementation
- `firmware/src/services/emg_processor.c` - Real-time DSP processing
- `firmware/src/tasks/` - FreeRTOS task implementations

### 2. BLE Gateway (Python Client)
**Location:** `/backend/serial/ble_gateway.py`

The BLE gateway acts as a bridge between the ESP32 BLE peripheral and the backend API:
- **Device Discovery:** Scans for and connects to the ESP32 device
- **BLE Client:** Uses Bleak library for cross-platform BLE communication
- **Notification Handling:** Receives 12-byte BLE notification packets at ~20 Hz
- **Batching & Forwarding:** Accumulates samples and POSTs to backend API
- **Protocol Translation:** Converts binary BLE packets to JSON REST API format

**BLE Packet Format (12 bytes):**
```
Offset | Size | Type    | Field       | Description
-------|------|---------|-------------|----------------------------------
0      | 4    | uint32  | ts_ms       | Device timestamp (milliseconds)
4      | 2    | uint16  | env_mv      | Envelope value (millivolts)
6      | 2    | uint16  | rms_mv      | RMS value (millivolts)
8      | 1    | uint8   | active      | Activation flag (0 or 1)
9      | 1    | uint8   | quality     | Signal quality indicator
10     | 2    | uint16  | seq         | Sequence number (for drop detection)
```

### 3. Backend API (FastAPI)
**Location:** `/backend/`

RESTful API service providing data ingestion, storage, and query endpoints:

**Core Components:**
- `main.py` - FastAPI application initialization and middleware
- `routers/emg.py` - EMG data endpoints
- `routers/imu.py` - IMU data endpoints (for future expansion)
- `routers/analytics.py` - Data analysis and aggregation endpoints
- `db/models.py` - SQLAlchemy ORM models
- `db/session.py` - Database session management
- `core/config.py` - Configuration and settings

**Key Endpoints:**

**POST /emg/**
- Ingests single or batch EMG samples
- Requires API key authentication (X-API-Key header)
- Accepts JSON payload with EMG sample data
- Returns saved records with database IDs

**GET /emg/latest**
- Retrieves most recent sample for a given channel
- Query params: `channel` (int)

**GET /emg/history**
- Retrieves historical data within time range
- Query params: `start` (ISO datetime), `end` (ISO datetime), `channel` (int, optional)

**GET /health**
- Health check endpoint
- Returns {"status": "ok"}

### 4. Database Layer (SQLAlchemy + SQLite)
**Location:** `/backend/db/`

Persistent storage for all sensor data:

**EMGSample Table:**
```sql
CREATE TABLE emg_samples (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME INDEXED,
    channel INTEGER INDEXED,
    raw FLOAT,
    rect FLOAT,
    envelope FLOAT,
    rms FLOAT
);
```

**IMUSample Table:**
```sql
CREATE TABLE imu_samples (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME INDEXED,
    x FLOAT, y FLOAT, z FLOAT,
    ax FLOAT, ay FLOAT, az FLOAT,
    gx FLOAT, gy FLOAT, gz FLOAT
);
```

### 5. Frontend Layer
**Location:** `/ui/`

Two UI implementations for different use cases:

**Streamlit Dashboard** (`/ui/streamlit/`)
- Rapid prototyping interface
- Real-time data visualization
- Interactive signal processing controls
- Historical data comparison

**React Application** (`/ui/react/`)
- Production-ready web interface (Next.js)
- Modern component-based architecture
- REST API integration for real-time updates
- Responsive design for clinic environments

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        HARDWARE LAYER (ESP32-S3)                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌─────────────┐    ┌──────────────┐         │
│  │  ADS1115 ADC │───>│ EMG Acq     │───>│ Processing   │         │
│  │  (860 SPS)   │    │ Task        │    │ Task         │         │
│  └──────────────┘    └─────────────┘    └──────────────┘         │
│                                                 │                   │
│                                                 v                   │
│                         ┌────────────────────────────────┐         │
│                         │  Packetizer                    │         │
│                         │  (12-byte fixed packets)       │         │
│                         └────────────────────────────────┘         │
│                                                 │                   │
│                                                 v                   │
│                         ┌────────────────────────────────┐         │
│                         │  BLE GATT Server (NimBLE)      │         │
│                         │  Service UUID: 0000abcd-...    │         │
│                         │  Char UUID: 0000abce-...       │         │
│                         │  Notifications @ 20 Hz         │         │
│                         └────────────────────────────────┘         │
│                                                                     │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 │ BLE Notifications
                                 │ (12 bytes/packet)
                                 │
                                 v
┌─────────────────────────────────────────────────────────────────────┐
│                      GATEWAY LAYER (Python/Bleak)                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  BLE Gateway (ble_gateway.py)                                │ │
│  │                                                               │ │
│  │  1. Device Discovery & Connection                            │ │
│  │  2. Subscribe to BLE Notifications                           │ │
│  │  3. Unpack 12-byte binary packets                            │ │
│  │  4. Convert to JSON format                                   │ │
│  │  5. Batch samples (50 samples or 250ms)                      │ │
│  │  6. POST to backend API                                      │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 │ HTTP POST
                                 │ (JSON batches)
                                 │
                                 v
┌─────────────────────────────────────────────────────────────────────┐
│                     BACKEND LAYER (FastAPI)                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  API Server (main.py)                                      │   │
│  │                                                             │   │
│  │  ┌──────────────┐                                          │   │
│  │  │ CORS         │  Enable cross-origin for UI access       │   │
│  │  │ Middleware   │                                          │   │
│  │  └──────────────┘                                          │   │
│  │                                                             │   │
│  │  ┌──────────────┐                                          │   │
│  │  │ API Key Auth │  X-API-Key header validation            │   │
│  │  │ (routers/    │  Default: "dev-key"                     │   │
│  │  │  auth.py)    │                                          │   │
│  │  └──────────────┘                                          │   │
│  │                                                             │   │
│  │  ┌───────────────────────────────────────────────────┐    │   │
│  │  │  Routers                                          │    │   │
│  │  │                                                   │    │   │
│  │  │  /emg/ (POST)     - Ingest EMG samples           │    │   │
│  │  │  /emg/latest      - Get latest sample            │    │   │
│  │  │  /emg/history     - Query historical data        │    │   │
│  │  │  /imu/            - IMU data endpoints            │    │   │
│  │  │  /analytics/      - Analytics & aggregations     │    │   │
│  │  │  /health          - Health check                 │    │   │
│  │  └───────────────────────────────────────────────────┘    │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                 │                                   │
│                                 v                                   │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  SQLAlchemy ORM (db/models.py)                             │   │
│  │  - EMGSample model                                         │   │
│  │  - IMUSample model                                         │   │
│  │  - Patient model                                           │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                 │                                   │
└─────────────────────────────────┼───────────────────────────────────┘
                                  │
                                  │ SQL Queries
                                  │
                                  v
┌─────────────────────────────────────────────────────────────────────┐
│                     DATABASE LAYER (SQLite)                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  File: backend/data/app.db                                          │
│                                                                     │
│  Tables:                                                            │
│  - emg_samples (id, timestamp, channel, raw, rect, envelope, rms)  │
│  - imu_samples (id, timestamp, x, y, z, ax, ay, az, gx, gy, gz)    │
│  - patients (id, name, created_at)                                 │
│                                                                     │
│  Indexes: timestamp, channel for efficient queries                 │
│                                                                     │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  │ HTTP GET
                                  │ (REST API)
                                  │
                                  v
┌─────────────────────────────────────────────────────────────────────┐
│                      FRONTEND LAYER                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────┐      ┌─────────────────────┐             │
│  │  Streamlit UI       │      │  React/Next.js UI   │             │
│  │                     │      │                     │             │
│  │  - Live dashboard   │      │  - Production web   │             │
│  │  - Real-time plots  │      │  - Modern UI/UX     │             │
│  │  - Signal controls  │      │  - Mobile support   │             │
│  │  - Rapid prototyp.  │      │  - Clinic ready     │             │
│  └─────────────────────┘      └─────────────────────┘             │
│           │                             │                           │
│           └─────────────┬───────────────┘                           │
│                         │                                           │
│                         │ REST API Calls                            │
│                         │ - GET /emg/latest                         │
│                         │ - GET /emg/history                        │
│                         │ - GET /analytics/*                        │
│                         │                                           │
└─────────────────────────┴───────────────────────────────────────────┘
```

## Detailed Component Communication

### 1. BLE Device → Gateway Communication

**Protocol:** Bluetooth Low Energy (BLE) 5.0
**Transport:** GATT Notifications
**Rate:** 20 Hz (50ms interval)
**MTU:** 128 bytes (preferred), 23 bytes (minimum)

**Connection Sequence:**
1. ESP32 advertises as "emg-force-bridge"
2. Gateway scans and discovers device
3. Gateway initiates connection
4. Gateway subscribes to notification characteristic
5. ESP32 sends notifications at configured rate
6. Gateway acknowledges (implicit in BLE protocol)

**Data Format:**
- Binary struct, little-endian encoding
- Fixed 12-byte packets for reliable transmission
- Sequence numbers for drop detection

### 2. Gateway → Backend Communication

**Protocol:** HTTP/1.1
**Transport:** REST API over TCP
**Format:** JSON
**Authentication:** API Key (X-API-Key header)

**Request Format (POST /emg/):**
```json
[
  {
    "timestamp": "2026-01-13T19:17:32",
    "channel": 0,
    "raw": 0.0,
    "rect": 0.852,
    "envelope": 0.852,
    "rms": 0.897
  },
  ...
]
```

**Response Format:**
```json
[
  {
    "id": 1234,
    "timestamp": "2026-01-13T19:17:32",
    "channel": 0,
    "raw": 0.0,
    "rect": 0.852,
    "envelope": 0.852,
    "rms": 0.897
  },
  ...
]
```

**Batching Strategy:**
- Accumulate up to 50 samples
- OR flush after 250ms timeout
- Prevents overwhelming the backend with individual requests
- Provides good latency/throughput balance

### 3. Backend → Database Communication

**ORM:** SQLAlchemy
**Database:** SQLite (development), PostgreSQL (production ready)
**Connection Pool:** Managed by SQLAlchemy

**Query Patterns:**

**Insert (Batch):**
```python
for item in items:
    row = EMGSample(
        timestamp=item.timestamp,
        channel=item.channel,
        raw=item.raw,
        rect=item.rect,
        envelope=item.envelope,
        rms=item.rms
    )
    db.add(row)
db.commit()
```

**Query Latest:**
```python
db.query(EMGSample)
  .filter(EMGSample.channel == channel)
  .order_by(EMGSample.timestamp.desc())
  .first()
```

**Query Range:**
```python
db.query(EMGSample)
  .filter(EMGSample.timestamp >= start_dt, 
          EMGSample.timestamp <= end_dt,
          EMGSample.channel == channel)
  .order_by(EMGSample.timestamp.asc())
  .all()
```

### 4. Frontend → Backend Communication

**Protocol:** HTTP/1.1 REST API
**Polling:** Frontend polls at regular intervals (e.g., 1-5 Hz)
**Future Enhancement:** WebSocket for real-time push updates

**Typical UI Workflow:**
1. User opens dashboard
2. Frontend requests latest data: `GET /emg/latest?channel=0`
3. Display real-time value
4. User selects time range for history
5. Frontend requests historical data: `GET /emg/history?start=...&end=...`
6. Plot time series chart
7. Repeat polling for live updates

## Security Architecture

### Authentication & Authorization

**Current Implementation (Development):**
- API Key authentication via `X-API-Key` header
- Default key: "dev-key" (configurable via environment)
- Applied to all data ingestion endpoints

**Production Recommendations:**
1. **API Key Rotation:** Implement key rotation mechanism
2. **TLS/HTTPS:** Enable HTTPS for all API communication
3. **Rate Limiting:** Add per-client rate limits to prevent abuse
4. **BLE Security:** Enable LE Secure Connections with bonding
5. **Device Whitelisting:** Only allow paired BLE devices to connect

### Data Privacy

1. **De-identification:** All patient data stored without PII
2. **Consent Forms:** Required before data collection (see `docs/consent_form.md`)
3. **Local Storage:** SQLite database stored locally by default
4. **Access Control:** API key prevents unauthorized access

## Signal Processing Pipeline

The ESP32 performs real-time DSP before BLE transmission:

**Processing Steps:**
1. **Acquisition:** ADS1115 samples at ~860 SPS (configurable)
2. **Band-pass Filter:** 20-450 Hz (removes DC offset and high-freq noise)
3. **Notch Filter:** 60 Hz (removes AC power line interference)
4. **Rectification:** Full-wave rectification (absolute value)
5. **Envelope Extraction:** 
   - Option A: RMS with sliding window
   - Option B: Low-pass filter at 5 Hz
6. **Activation Detection:** Threshold-based muscle activation
7. **Quality Estimation:** SNR calculation for signal quality

**Key Parameters:**
- Sampling Rate: 860 Hz
- Band-pass: 20-450 Hz (typical EMG bandwidth)
- Notch: 60 Hz (US power frequency, 50 Hz for EU)
- RMS Window: Configurable (typically 50-200ms)
- Envelope Cutoff: 5 Hz

See `docs/dsp.md` for mathematical details.

## Performance Characteristics

### Latency Budget

| Stage                    | Latency      | Notes                              |
|--------------------------|--------------|-------------------------------------|
| ADC Sampling             | 1.2 ms       | Per sample at 860 Hz               |
| On-device Processing     | ~5 ms        | FreeRTOS task scheduling           |
| BLE Notification         | 50 ms        | Configured interval                |
| Gateway Batching         | 0-250 ms     | Batching window                    |
| HTTP POST                | 10-50 ms     | Local network                      |
| Database Insert          | 5-20 ms      | Batch insert                       |
| **Total (worst-case)**   | **~340 ms**  | Sensor to database                 |
| Frontend Poll            | 200-1000 ms  | Configurable UI refresh            |

### Throughput

- **BLE Bandwidth:** 20 packets/sec × 12 bytes = 240 bytes/sec
- **Backend Ingest:** ~200 samples/sec (batched)
- **Database Growth:** ~17 MB/day (continuous recording)
- **UI Update Rate:** 1-5 Hz (configurable)

### Reliability

- **Sequence Numbers:** Detect packet loss
- **Connection Resilience:** Gateway auto-reconnects on disconnect
- **Batch Retries:** Failed POST requests can be retried
- **Data Integrity:** SQLite ACID guarantees

## Deployment Architecture

### Development Setup

```
┌────────────────┐     BLE      ┌─────────────────┐
│   ESP32-S3     │◄────────────►│  Laptop/PC      │
│   (Hardware)   │              │                 │
└────────────────┘              │  - BLE Gateway  │
                                │  - Backend API  │
                                │  - SQLite DB    │
                                │  - UI (local)   │
                                └─────────────────┘
```

### Clinical Deployment

```
┌────────────────┐     BLE      ┌──────────────────┐
│   ESP32-S3     │◄────────────►│  Gateway Device  │
│   (on Patient) │              │  (Raspberry Pi)  │
└────────────────┘              └─────────┬────────┘
                                          │
                                          │ WiFi/LAN
                                          │
                                          v
                                ┌──────────────────┐
                                │  Clinic Server   │
                                │                  │
                                │  - Backend API   │
                                │  - PostgreSQL    │
                                │  - Web UI        │
                                └──────────────────┘
                                          │
                                          │ HTTPS
                                          │
                                          v
                                ┌──────────────────┐
                                │  PT Workstation  │
                                │  (Web Browser)   │
                                └──────────────────┘
```

## Configuration

### ESP32 Firmware Configuration

**File:** `firmware/sdkconfig`
- BLE device name
- Service/Characteristic UUIDs
- Notification interval
- MTU preferences

### Gateway Configuration

**File:** `backend/serial/ble_gateway.py` (constants)
- `DEVICE_NAME`: BLE device name to connect to
- `SERVICE_UUID`: BLE service UUID
- `CHAR_UUID`: BLE characteristic UUID
- `BACKEND_URL`: Backend API endpoint
- `API_KEY`: Authentication key
- `BATCH_SIZE`: Number of samples per POST
- `POST_INTERVAL_SEC`: Max time between POSTs

### Backend Configuration

**File:** `backend/core/config.py` or `.env`
- `api_key`: API authentication key
- `sqlite_path`: Database file location
- CORS origins (for frontend access)

### Frontend Configuration

- Backend API URL
- Polling interval
- Chart refresh rate
- Display preferences

## Future Enhancements

### Short-term
1. **WebSocket Support:** Real-time push updates to UI
2. **Multi-channel Support:** Multiple EMG sensors simultaneously
3. **Cloud Deployment:** AWS/Azure hosting for backend
4. **Mobile App:** Native iOS/Android BLE clients

### Medium-term
1. **Edge ML:** On-device inference on ESP32
2. **Advanced Analytics:** Fatigue detection, gesture recognition
3. **Multi-patient:** Support concurrent patient sessions
4. **Data Export:** CSV/MATLAB export functionality

### Long-term
1. **HIPAA Compliance:** Full healthcare data protection
2. **Clinical Integration:** HL7/FHIR interfaces
3. **Wireless EMG Array:** Multiple electrode channels
4. **Real-time Biofeedback:** Audio/visual feedback loops

## Troubleshooting

### BLE Connection Issues
- **Problem:** Gateway can't find device
- **Solution:** Ensure ESP32 is powered and advertising, check device name
- **Check:** Use BLE scanner app to verify device is visible

### Backend Connection Issues
- **Problem:** Gateway can't POST to backend
- **Solution:** Verify backend is running on correct port, check API key
- **Check:** `curl http://localhost:8000/health` should return `{"status": "ok"}`

### Data Not Appearing in UI
- **Problem:** Frontend shows no data
- **Solution:** Check backend logs, verify data in database, check CORS settings
- **Check:** `GET /emg/latest` should return recent sample

## References

- **BLE Specification:** Bluetooth 5.0 Core Specification
- **FastAPI Documentation:** https://fastapi.tiangolo.com
- **SQLAlchemy ORM:** https://docs.sqlalchemy.org
- **Bleak (BLE Library):** https://github.com/hbldh/bleak
- **ESP-IDF:** https://docs.espressif.com/projects/esp-idf/

## Related Documentation

- `docs/dsp.md` - Signal processing algorithms and mathematics
- `docs/protocol.md` - Testing protocols for clinical use
- `docs/data_schema.md` - Data format specifications
- `docs/consent_form.md` - Patient consent requirements
- `firmware/README.md` - Firmware build instructions
- `backend/README.md` - Backend setup and deployment
