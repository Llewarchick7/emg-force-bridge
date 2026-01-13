# EMG Force Bridge - Sequence Diagrams

This document provides detailed sequence diagrams for key system workflows.

## 1. Device Boot and BLE Connection Sequence

```
┌────────┐     ┌─────────┐     ┌──────────┐     ┌─────────┐
│ ESP32  │     │   BLE   │     │ Gateway  │     │ Backend │
│Hardware│     │  Stack  │     │ (Python) │     │   API   │
└───┬────┘     └────┬────┘     └────┬─────┘     └────┬────┘
    │               │               │                │
    │ Power On      │               │                │
    ├──────────────>│               │                │
    │               │               │                │
    │ nvs_flash_init│               │                │
    ├──────────────>│               │                │
    │               │               │                │
    │ emg_acq_start │               │                │
    ├───────────────┤               │                │
    │               │               │                │
    │ ble_emg_start │               │                │
    ├──────────────>│               │                │
    │               │               │                │
    │               │ Start         │                │
    │               │ Advertising   │                │
    │               ├──────────────>│                │
    │               │               │                │
    │               │            Scan for            │
    │               │          "emg-force-bridge"    │
    │               │<──────────────┤                │
    │               │               │                │
    │               │  Device Found │                │
    │               ├──────────────>│                │
    │               │               │                │
    │               │ Connection    │                │
    │               │   Request     │                │
    │               │<──────────────┤                │
    │               │               │                │
    │               │   Connected   │                │
    │               ├──────────────>│                │
    │               │               │                │
    │               │ MTU Exchange  │                │
    │               │   (128 bytes) │                │
    │               │<─────────────>│                │
    │               │               │                │
    │               │ Subscribe to  │                │
    │               │ Notifications │                │
    │               │<──────────────┤                │
    │               │               │                │
    │               │ Subscription  │                │
    │               │  Confirmed    │                │
    │               ├──────────────>│                │
    │               │               │                │
    │               │               │ Test Backend   │
    │               │               │  Connectivity  │
    │               │               ├───────────────>│
    │               │               │                │
    │               │               │ {"status":"ok"}│
    │               │               │<───────────────┤
    │               │               │                │
    │          [READY TO STREAM]    │                │
    │               │               │                │
```

## 2. Real-time Data Streaming Sequence

```
┌────────┐  ┌──────────┐  ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌──────────┐
│ADS1115 │  │   EMG    │  │   BLE   │  │ Gateway │  │ Backend  │  │ Database │
│  ADC   │  │Processor │  │  GATT   │  │ (Bleak) │  │   API    │  │ (SQLite) │
└───┬────┘  └────┬─────┘  └────┬────┘  └────┬────┘  └────┬─────┘  └────┬─────┘
    │            │             │            │            │             │
    │ Sample @   │             │            │            │             │
    │  860 Hz    │             │            │            │             │
    ├───────────>│             │            │            │             │
    │            │             │            │            │             │
    │            │ Process:    │            │            │             │
    │            │ - Bandpass  │            │            │             │
    │            │ - Notch     │            │            │             │
    │            │ - Rectify   │            │            │             │
    │            │ - Envelope  │            │            │             │
    │            │ - RMS       │            │            │             │
    │            ├──────────   │            │            │             │
    │            │             │            │            │             │
    │            │ Packetize   │            │            │             │
    │            │ (12 bytes)  │            │            │             │
    │            ├────────────>│            │            │             │
    │            │             │            │            │             │
    │            │             │ Notify     │            │             │
    │            │             │ @ 20 Hz    │            │             │
    │            │             ├───────────>│            │             │
    │            │             │            │            │             │
    │            │             │            │ Unpack     │             │
    │            │             │            │ Binary     │             │
    │            │             │            ├────────    │             │
    │            │             │            │            │             │
    │            │             │            │ Convert    │             │
    │            │             │            │ to JSON    │             │
    │            │             │            ├────────    │             │
    │            │             │            │            │             │
    │            │             │            │ Buffer     │             │
    │            │             │            │ (50 items  │             │
    │            │             │            │ or 250ms)  │             │
    │            │             │            ├────────    │             │
    │            │             │            │            │             │
    │            │             │            │ POST /emg/ │             │
    │            │             │            │ (batch)    │             │
    │            │             │            ├───────────>│             │
    │            │             │            │            │             │
    │            │             │            │            │ Validate   │
    │            │             │            │            │ API Key    │
    │            │             │            │            ├──────────  │
    │            │             │            │            │             │
    │            │             │            │            │ Batch      │
    │            │             │            │            │ INSERT     │
    │            │             │            │            ├────────────>│
    │            │             │            │            │             │
    │            │             │            │            │   COMMIT    │
    │            │             │            │            │<────────────┤
    │            │             │            │            │             │
    │            │             │            │  200 OK    │             │
    │            │             │            │  (records) │             │
    │            │             │            │<───────────┤             │
    │            │             │            │            │             │
    │            │             │            │ Log Success│             │
    │            │             │            ├────────    │             │
    │            │             │            │            │             │
    │         [CYCLE REPEATS @ 20 Hz]       │            │             │
    │            │             │            │            │             │
```

## 3. Frontend Real-time Update Sequence

```
┌─────────┐     ┌─────────┐     ┌──────────┐
│ React   │     │ Backend │     │ Database │
│   UI    │     │   API   │     │ (SQLite) │
└────┬────┘     └────┬────┘     └────┬─────┘
     │               │               │
     │ User Opens    │               │
     │  Dashboard    │               │
     ├───────────    │               │
     │               │               │
     │ GET /emg/     │               │
     │   latest      │               │
     │  ?channel=0   │               │
     ├──────────────>│               │
     │               │               │
     │               │ SELECT * FROM │
     │               │ emg_samples   │
     │               │ WHERE chan=0  │
     │               │ ORDER BY ts   │
     │               │ DESC LIMIT 1  │
     │               ├──────────────>│
     │               │               │
     │               │  Latest Row   │
     │               │<──────────────┤
     │               │               │
     │  200 OK       │               │
     │  {sample}     │               │
     │<──────────────┤               │
     │               │               │
     │ Display Value │               │
     ├───────────    │               │
     │               │               │
     │ [WAIT 1 SEC]  │               │
     ├───────────    │               │
     │               │               │
     │ GET /emg/     │               │
     │   latest      │               │
     │  ?channel=0   │               │
     ├──────────────>│               │
     │               │               │
     │               │ SELECT ...    │
     │               ├──────────────>│
     │               │               │
     │               │  New Latest   │
     │               │<──────────────┤
     │               │               │
     │  200 OK       │               │
     │  {sample}     │               │
     │<──────────────┤               │
     │               │               │
     │ Update Chart  │               │
     ├───────────    │               │
     │               │               │
     │     [POLLING LOOP CONTINUES]  │
     │               │               │
```

## 4. Historical Data Query Sequence

```
┌─────────┐     ┌─────────┐     ┌──────────┐
│   UI    │     │ Backend │     │ Database │
│(Streamlit│    │   API   │     │ (SQLite) │
└────┬────┘     └────┬────┘     └────┬─────┘
     │               │               │
     │ User Selects  │               │
     │  Time Range   │               │
     ├───────────    │               │
     │               │               │
     │ GET /emg/     │               │
     │   history?    │               │
     │ start=2026-   │               │
     │   01-13T10:00 │               │
     │ &end=2026-    │               │
     │   01-13T11:00 │               │
     │ &channel=0    │               │
     ├──────────────>│               │
     │               │               │
     │               │ Parse ISO     │
     │               │  Datetime     │
     │               ├──────────     │
     │               │               │
     │               │ SELECT * FROM │
     │               │ emg_samples   │
     │               │ WHERE ts      │
     │               │  BETWEEN      │
     │               │  ? AND ?      │
     │               │ AND chan=0    │
     │               │ ORDER BY ts   │
     │               ├──────────────>│
     │               │               │
     │               │ Matching Rows │
     │               │ (could be     │
     │               │  thousands)   │
     │               │<──────────────┤
     │               │               │
     │  200 OK       │               │
     │  [{sample1},  │               │
     │   {sample2},  │               │
     │   ...]        │               │
     │<──────────────┤               │
     │               │               │
     │ Render Time   │               │
     │  Series Chart │               │
     ├───────────    │               │
     │               │               │
```

## 5. Error Handling Sequence - BLE Disconnect

```
┌────────┐  ┌──────────┐  ┌─────────┐  ┌─────────┐
│ ESP32  │  │   BLE    │  │ Gateway │  │ Backend │
└───┬────┘  └────┬─────┘  └────┬────┘  └────┬────┘
    │            │             │            │
    │ [STREAMING NORMALLY]     │            │
    │            │             │            │
    │  Signal    │             │            │
    │   Lost     │             │            │
    │     X──────X             │            │
    │            │             │            │
    │            │             │ Timeout    │
    │            │             │ Detected   │
    │            │             ├────────    │
    │            │             │            │
    │            │             │ Log Error  │
    │            │             ├────────    │
    │            │             │            │
    │            │             │ Disconnect │
    │            │             ├───────────>│
    │            │             │            │
    │            │             │ Sleep 2s   │
    │            │             ├────────    │
    │            │             │            │
    │            │             │ Rescan for │
    │            │             │  Device    │
    │            │<────────────┤            │
    │            │             │            │
    │   [ESP32 STILL ADVERTISING]           │
    │            │             │            │
    │            │ Device Found│            │
    │            ├────────────>│            │
    │            │             │            │
    │            │ Reconnect   │            │
    │            │<────────────┤            │
    │            │             │            │
    │            │ Subscribe   │            │
    │            │<────────────┤            │
    │            │             │            │
    │    [RESUME STREAMING]    │            │
    │            │             │            │
```

## 6. Error Handling Sequence - Backend API Failure

```
┌──────────┐     ┌─────────┐     ┌──────────┐
│ Gateway  │     │ Backend │     │ Database │
└────┬─────┘     └────┬────┘     └────┬─────┘
     │                │               │
     │ POST /emg/     │               │
     │  (batch)       │               │
     ├───────────────>│               │
     │                │               │
     │                │ Validate      │
     │                │  API Key      │
     │                ├───────────    │
     │                │               │
     │                │ INSERT ...    │
     │                ├──────────────>│
     │                │               │
     │                │   ERROR:      │
     │                │   Disk Full   │
     │                │<──────────────X
     │                │               │
     │  500 Internal  │               │
     │  Server Error  │               │
     │<───────────────┤               │
     │                │               │
     │ Log Error      │               │
     ├───────────     │               │
     │                │               │
     │ Keep Samples   │               │
     │  in Buffer     │               │
     ├───────────     │               │
     │                │               │
     │ [WAIT 5s]      │               │
     ├───────────     │               │
     │                │               │
     │ Retry POST     │               │
     │  /emg/         │               │
     ├───────────────>│               │
     │                │               │
     │         [If continues failing, │
     │          gateway buffers and   │
     │          alerts operator]      │
     │                │               │
```

## 7. Sequence Number Gap Detection

```
┌──────────┐     ┌─────────┐
│ Gateway  │     │  ESP32  │
└────┬─────┘     └────┬────┘
     │                │
     │ Notification   │
     │  (seq=100)     │
     │<───────────────┤
     │                │
     │ Process OK     │
     ├───────────     │
     │                │
     │ Notification   │
     │  (seq=101)     │
     │<───────────────┤
     │                │
     │ Process OK     │
     ├───────────     │
     │                │
     │ [PACKET 102 LOST IN BLE]
     │                │
     │ Notification   │
     │  (seq=103)     │
     │<───────────────┤
     │                │
     │ Detect Gap:    │
     │  Expected 102  │
     │  Got 103       │
     ├───────────     │
     │                │
     │ Log Warning:   │
     │  "1 packet(s)  │
     │   lost"        │
     ├───────────     │
     │                │
     │ Update Seq     │
     │  Tracker       │
     ├───────────     │
     │                │
     │ Continue       │
     │  Processing    │
     ├───────────     │
     │                │
```

## 8. Multi-Channel Processing (Future)

```
┌────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐
│ADS1115 │  │   EMG    │  │   BLE   │  │ Gateway  │
│ (4-ch) │  │Processor │  │  GATT   │  │          │
└───┬────┘  └────┬─────┘  └────┬────┘  └────┬─────┘
    │            │             │            │
    │ Ch0 Sample │             │            │
    ├───────────>│             │            │
    │            │             │            │
    │ Ch1 Sample │             │            │
    ├───────────>│             │            │
    │            │             │            │
    │ Ch2 Sample │             │            │
    ├───────────>│             │            │
    │            │             │            │
    │ Ch3 Sample │             │            │
    ├───────────>│             │            │
    │            │             │            │
    │            │ Process All │            │
    │            │  Channels   │            │
    │            ├──────────   │            │
    │            │             │            │
    │            │ Pack Multi- │            │
    │            │  Channel    │            │
    │            │  Packet     │            │
    │            │  (48 bytes) │            │
    │            ├────────────>│            │
    │            │             │            │
    │            │             │ Notify     │
    │            │             ├───────────>│
    │            │             │            │
    │            │             │            │ Process
    │            │             │            │  Each Ch
    │            │             │            ├─────────
    │            │             │            │
    │            │             │            │ POST 4x
    │            │             │            │ (or batch)
    │            │             │            ├─────────
    │            │             │            │
```

## Notes

### Timing Considerations

1. **BLE Notification Interval (50ms):** 
   - Balances latency and BLE reliability
   - Can be adjusted based on application needs
   - Lower values increase packet loss risk

2. **Gateway Batching (250ms):**
   - Reduces HTTP request overhead
   - Provides reasonable latency for monitoring
   - Batch size is adaptive (count or time)

3. **Frontend Polling (1000ms):**
   - Suitable for dashboard visualization
   - Can be reduced for more responsive UI
   - Consider WebSocket for <100ms latency needs

### Error Recovery Strategies

1. **BLE Connection Loss:**
   - Gateway maintains connection state
   - Automatic reconnection with exponential backoff
   - Device continues advertising when disconnected

2. **Backend API Failure:**
   - Gateway buffers samples locally
   - Retries with exponential backoff
   - Logs errors for operator review

3. **Database Errors:**
   - Transaction rollback on failure
   - API returns 500 error to gateway
   - Gateway retries or alerts operator

### Performance Optimizations

1. **Batch Processing:**
   - BLE: Single notification per interval
   - Gateway: Batch POST (50 samples)
   - Database: Batch INSERT with commit

2. **Indexed Queries:**
   - Timestamp index for range queries
   - Channel index for filtering
   - Composite index for common patterns

3. **Connection Pooling:**
   - SQLAlchemy manages DB connections
   - BLE connection reused during session
   - HTTP connections can use keep-alive

### Security Considerations

1. **BLE Pairing:**
   - Future: Implement LE Secure Connections
   - Device whitelisting recommended
   - Consider RPA (Resolvable Private Address)

2. **API Authentication:**
   - Current: Simple API key
   - Production: OAuth2 or JWT recommended
   - Rate limiting per client

3. **Data Encryption:**
   - BLE: Can enable encryption
   - HTTP: Should use HTTPS in production
   - Database: File-level encryption available

