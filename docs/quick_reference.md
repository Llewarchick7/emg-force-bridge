# EMG Force Bridge - Quick Reference Guide

## System Overview

The EMG Force Bridge is a complete end-to-end system for wireless EMG signal acquisition, processing, and visualization. Data flows from a wearable sensor through BLE wireless to a gateway, then to a backend API for storage, and finally to frontend dashboards for real-time monitoring.

## Architecture at a Glance

```
[Sensor] --BLE--> [Gateway] --HTTP--> [Backend API] --SQL--> [Database]
                                              ^
                                              |
                                           HTTP/REST
                                              |
                                          [Frontend]
```

## Key Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Hardware** | ESP32-S3 + ADS1115 | EMG signal acquisition & BLE transmission |
| **Gateway** | Python + Bleak | BLE-to-HTTP bridge |
| **Backend** | FastAPI + SQLAlchemy | REST API & data persistence |
| **Database** | SQLite (dev) / PostgreSQL (prod) | Time-series data storage |
| **Frontend** | React / Streamlit | Real-time monitoring dashboard |

## Data Flow Summary

### 1. Acquisition (ESP32)
- **Sampling Rate:** 860 Hz
- **Resolution:** 16-bit ADC
- **Processing:** Band-pass → Notch → Rectify → Envelope → RMS
- **Output Rate:** 20 Hz (50ms intervals)

### 2. Transmission (BLE)
- **Protocol:** BLE GATT Notifications
- **Packet Size:** 12 bytes (fixed)
- **Format:** Binary (little-endian)
- **Fields:** timestamp, envelope, RMS, active, quality, sequence

### 3. Gateway (Python)
- **Role:** BLE client → HTTP client
- **Batching:** 50 samples or 250ms
- **Format Conversion:** Binary → JSON
- **Authentication:** API Key

### 4. Backend (FastAPI)
- **Endpoints:** POST /emg/, GET /emg/latest, GET /emg/history
- **Authentication:** X-API-Key header
- **Storage:** Batch insert to database
- **Response:** JSON with database IDs

### 5. Frontend (React/Streamlit)
- **Method:** HTTP polling (1-5 Hz)
- **Queries:** Latest value & historical range
- **Visualization:** Time-series charts, real-time gauges
- **Future:** WebSocket for push updates

## Key Protocols

### BLE Packet Format (12 bytes)
```
Byte | Field      | Type    | Units        | Range
-----|------------|---------|--------------|------------------
0-3  | ts_ms      | uint32  | milliseconds | 0 to ~49 days
4-5  | env_mv     | uint16  | millivolts   | 0 to 65535
6-7  | rms_mv     | uint16  | millivolts   | 0 to 65535
8    | active     | uint8   | boolean      | 0 or 1
9    | quality    | uint8   | percent      | 0 to 100
10-11| seq        | uint16  | count        | 0 to 65535 (wraps)
```

### REST API - EMG Sample JSON
```json
{
  "timestamp": "2026-01-13T19:17:32",
  "channel": 0,
  "raw": 0.0,
  "rect": 0.852,
  "envelope": 0.852,
  "rms": 0.897
}
```

## Configuration Quick Reference

### ESP32 Firmware
```c
// In ble_emg.c
#define BLE_STREAM_INTERVAL_MS 50  // 20 Hz notification rate

// Service/Characteristic UUIDs
SERVICE_UUID  = "0000abcd-0000-1000-8000-00805f9b34fb"
CHAR_UUID     = "0000abce-0000-1000-8000-00805f9b34fb"
```

### Gateway (ble_gateway.py)
```python
DEVICE_NAME = "emg-force-bridge"
BACKEND_URL = "http://127.0.0.1:8000"
API_KEY = "dev-key"
BATCH_SIZE = 50
POST_INTERVAL_SEC = 0.25
```

### Backend (config.py or .env)
```python
api_key = "dev-key"
sqlite_path = "backend/data/app.db"
```

## Common Operations

### Start the System

1. **Flash ESP32 Firmware:**
```bash
cd firmware
idf.py -p COM3 flash monitor
```

2. **Start Backend API:**
```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

3. **Start BLE Gateway:**
```bash
cd backend/serial
python ble_gateway.py
```

4. **Start Frontend (Streamlit):**
```bash
cd ui/streamlit
streamlit run dashboard.py
```

### Check System Health

**Test Backend:**
```bash
curl http://localhost:8000/health
# Expected: {"status": "ok"}
```

**Test API Authentication:**
```bash
curl -H "X-API-Key: dev-key" http://localhost:8000/emg/latest?channel=0
```

**Check Database:**
```bash
sqlite3 backend/data/app.db "SELECT COUNT(*) FROM emg_samples;"
```

## Performance Metrics

### Latency Budget
- **Sensor to Database:** ~340ms (worst case)
  - ADC: 1.2ms
  - Processing: ~5ms
  - BLE: 50ms
  - Gateway batch: 0-250ms
  - HTTP POST: 10-50ms
  - DB insert: 5-20ms
- **Database to Frontend:** 200-1000ms (polling interval)

### Throughput
- **BLE:** 20 packets/sec × 12 bytes = 240 bytes/sec
- **Backend:** ~200 samples/sec (batched)
- **Database Growth:** ~17 MB/day continuous recording

### Reliability
- **Packet Loss Detection:** Sequence numbers
- **Auto-Reconnect:** Gateway handles disconnects
- **Retry Logic:** Failed POSTs can retry
- **ACID Guarantees:** SQLite transactions

## Troubleshooting

### Problem: BLE device not found
**Check:**
- ESP32 powered on and running
- Device name matches in gateway config
- BLE adapter working on host machine
- Use BLE scanner app to verify advertising

**Fix:**
```python
# In ble_gateway.py, try using MAC address instead of name
addr = "AA:BB:CC:DD:EE:FF"  # ESP32 MAC address
```

### Problem: Gateway can't connect to backend
**Check:**
- Backend running on port 8000
- API key matches in gateway and backend
- Firewall not blocking connections

**Test:**
```bash
curl http://localhost:8000/health
```

### Problem: No data in frontend
**Check:**
- Backend receiving data (check logs)
- Database has records
- CORS configured for frontend domain
- API key provided if required

**Test:**
```bash
curl -H "X-API-Key: dev-key" http://localhost:8000/emg/latest?channel=0
```

### Problem: High packet loss
**Check:**
- BLE interference (WiFi, other devices)
- Distance between ESP32 and gateway
- MTU negotiation (should be >23 bytes)
- Notification interval (try increasing to 100ms)

**Monitor:**
- Watch sequence numbers for gaps
- Check gateway logs for reconnection events

## Signal Processing Parameters

### Filters (On ESP32)
- **Band-pass:** 20-450 Hz (typical EMG bandwidth)
- **Notch:** 60 Hz (US) or 50 Hz (EU) for power line
- **Envelope:** 5 Hz low-pass or RMS window
- **RMS Window:** 50-200ms typical

### Quality Thresholds
- **Activation Threshold:** Typically 0.1-0.5V (configurable)
- **SNR Good:** >20 dB
- **SNR Fair:** 10-20 dB
- **SNR Poor:** <10 dB

## Security Checklist

### Development
- ✓ API key authentication
- ✓ Local network only
- ✓ De-identified data

### Production (TODO)
- ☐ HTTPS/TLS for API
- ☐ Strong API keys or OAuth2
- ☐ BLE encryption enabled
- ☐ Database encryption
- ☐ Rate limiting
- ☐ Device whitelisting
- ☐ Audit logging

## API Endpoint Reference

### Health Check
```
GET /health
Response: {"status": "ok"}
```

### Ingest EMG Data
```
POST /emg/
Headers: X-API-Key: dev-key
Body: Single object or array of EMGSampleCreate
Response: Array of EMGSampleRead with IDs
```

### Get Latest Sample
```
GET /emg/latest?channel=0
Headers: X-API-Key: dev-key
Response: Single EMGSampleRead
```

### Get Historical Data
```
GET /emg/history?start=2026-01-13T10:00:00&end=2026-01-13T11:00:00&channel=0
Headers: X-API-Key: dev-key
Response: Array of EMGSampleRead
```

## Database Schema Reference

### emg_samples Table
```sql
CREATE TABLE emg_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    channel INTEGER NOT NULL,
    raw FLOAT NOT NULL,
    rect FLOAT NOT NULL,
    envelope FLOAT NOT NULL,
    rms FLOAT NOT NULL,
    INDEX idx_timestamp (timestamp),
    INDEX idx_channel (channel)
);
```

### imu_samples Table
```sql
CREATE TABLE imu_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    x FLOAT, y FLOAT, z FLOAT,
    ax FLOAT, ay FLOAT, az FLOAT,
    gx FLOAT, gy FLOAT, gz FLOAT,
    INDEX idx_timestamp (timestamp)
);
```

## File Structure Reference

```
emg-force-bridge/
├── firmware/              # ESP32-S3 firmware (ESP-IDF)
│   ├── src/
│   │   ├── main.c        # Entry point
│   │   ├── services/
│   │   │   ├── ble_emg.c        # BLE GATT server
│   │   │   ├── emg_processor.c  # DSP processing
│   │   │   └── packetizer.c     # Data packetization
│   │   ├── drivers/      # Hardware drivers (ADS1115)
│   │   └── tasks/        # FreeRTOS tasks
│   └── sdkconfig         # ESP-IDF configuration
│
├── backend/              # FastAPI backend
│   ├── main.py          # FastAPI app
│   ├── routers/
│   │   ├── emg.py       # EMG endpoints
│   │   ├── imu.py       # IMU endpoints
│   │   └── analytics.py # Analytics endpoints
│   ├── db/
│   │   ├── models.py    # SQLAlchemy models
│   │   └── session.py   # Database session
│   ├── serial/
│   │   └── ble_gateway.py  # BLE-to-HTTP bridge
│   └── core/
│       └── config.py    # Configuration
│
├── ui/                  # Frontend interfaces
│   ├── streamlit/       # Streamlit dashboard
│   └── react/           # React/Next.js app
│
├── emg/                 # Shared EMG processing library
│   └── preprocessing/   # Filters, envelopes, features
│
├── ml/                  # Machine learning experiments
│
├── docs/                # Documentation
│   ├── systems_architecture.md   # THIS DOCUMENT
│   ├── sequence_diagrams.md      # Workflow sequences
│   ├── dsp.md                    # Signal processing math
│   └── protocol.md               # Testing protocols
│
└── tests/               # Unit tests
```

## Development Workflow

### 1. Make Firmware Changes
```bash
cd firmware
# Edit src/ files
idf.py build
idf.py flash
idf.py monitor  # View logs
```

### 2. Make Backend Changes
```bash
cd backend
# Edit routers/ or db/ files
# Backend auto-reloads with --reload flag
# Test endpoint
curl -H "X-API-Key: dev-key" http://localhost:8000/emg/latest?channel=0
```

### 3. Make Frontend Changes
```bash
cd ui/streamlit
# Edit dashboard files
# Streamlit auto-reloads on file change
```

### 4. Test End-to-End
1. Ensure ESP32 is running and advertising
2. Start backend API
3. Start gateway (watch for connection)
4. Open frontend and verify data flowing
5. Check database for new records

## Next Steps & Enhancements

### Short-term
- [ ] WebSocket support for real-time frontend updates
- [ ] Multi-channel support (4 EMG channels)
- [ ] Cloud deployment (AWS/Azure)
- [ ] Mobile app (React Native)

### Medium-term
- [ ] On-device ML inference
- [ ] Advanced analytics (fatigue detection)
- [ ] Data export (CSV/MATLAB)
- [ ] Multi-patient sessions

### Long-term
- [ ] HIPAA compliance
- [ ] Clinical integration (HL7/FHIR)
- [ ] Wireless EMG array
- [ ] Real-time biofeedback loops

## Additional Resources

- **Main Documentation:** [systems_architecture.md](./systems_architecture.md)
- **Sequence Diagrams:** [sequence_diagrams.md](./sequence_diagrams.md)
- **Signal Processing:** [dsp.md](./dsp.md)
- **Testing Protocol:** [protocol.md](./protocol.md)
- **ESP-IDF Docs:** https://docs.espressif.com/projects/esp-idf/
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **Bleak (BLE):** https://github.com/hbldh/bleak

## Support

For issues or questions:
1. Check this quick reference guide
2. Review detailed architecture docs
3. Check ESP32 serial logs (`idf.py monitor`)
4. Check backend API logs (console output)
5. Check gateway logs (console output)
6. Verify each component independently before testing end-to-end

## Version History

- **v0.1.0** - Initial system architecture
  - ESP32-S3 firmware with BLE
  - Python BLE gateway
  - FastAPI backend
  - SQLite database
  - Streamlit UI prototype
