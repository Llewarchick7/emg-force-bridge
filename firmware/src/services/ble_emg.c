/*
ble_emg.c

Overview
--------
- Provides a minimal BLE GATT peripheral (NimBLE host) that streams processed EMG telemetry
    as compact, fixed-size notifications designed for clinic-grade reliability.
- Uses integer-scaled payloads and rate limiting to avoid BLE fragmentation/drops and to
    maintain deterministic throughput across Android/iOS.

Key Design Choices
------------------
- NimBLE host: lean BLE-only stack with strong interoperability and smaller footprint.
- Compact payload (12 bytes): only real-time essentials (timestamp, envelope, RMS, activation,
    signal quality, sequence number). Full data remains available on UART/log and can be sent on-demand.
- Rate limiting: decouples processing rate from BLE notify rate (default 50 ms ≈ 20 Hz).
- MTU preference + handling: requests higher MTU (128) and logs negotiated size.
- Sequence numbers: aids detection of drops/reordering and supports analytics.

Security & Ops (next steps)
---------------------------
- Enable LE Secure Connections with bonding, whitelist paired clients, enable RPA privacy.
- Enforce connection parameters suitable for stable telemetry (e.g., 15 ms interval).

Integration Notes
-----------------
- The stream consumes packets from `emg_get_proc_queue()` (produced by the processing task)
    and publishes the compact frames via `ble_gatts_notify_custom()`.
*/


// Minimal BLE GATT server (NimBLE) to stream EMG packets via notifications
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_timer.h"
#include <math.h>
#include <string.h>

#include "esp_bt.h"
#include "esp_nimble_hci.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "host/ble_att.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"

// Packet type from processing
typedef struct {
    int64_t ts_us;
    int16_t raw;
    float   volts;
    float   bp;
    float   rect;
    float   env;
    float   rms;
    int     active;
    float   snr;
} emg_packet_t;

QueueHandle_t emg_get_proc_queue(void);

static const char *TAG = "ble_emg"; // module tag for logging

// Simple 128-bit UUIDs
// EMG Service: 7a264b2b-9831-4f6d-9392-102d0000EEEE
// EMG Characteristic: 7a264b2b-9831-4f6d-9392-102d0001EEEE

static uint16_t s_conn_handle = 0;     // active connection handle
static uint16_t s_val_handle = 0;      // characteristic value handle used for notifications
static bool     s_notify_enabled = false; // client subscription state to notifications
static uint16_t s_seq = 0;             // sequence number for streamed packets

// Rate limiting for notifications (ms). Clinics: 20–50 Hz recommended.
#ifndef BLE_STREAM_INTERVAL_MS
#define BLE_STREAM_INTERVAL_MS 50
#endif

// NimBLE GATT definitions
// Characteristic access callback (optional reads)
static int emg_chr_access_cb(uint16_t conn_handle, uint16_t attr_handle, struct ble_gatt_access_ctxt *ctxt, void *arg) {
    (void)conn_handle; (void)arg;
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        // Optionally serve last value; for stream, we send via notifications only
        return 0;
    }
    return 0;
}

static const ble_uuid128_t EMG_SVC_UUID128 = {
    .u = { .type = BLE_UUID_TYPE_128 },
    .value = {0x7a,0x26,0x4b,0x2b,0x98,0x31,0x4f,0x6d,0x93,0x92,0x10,0x2d,0x00,0x00,0xEE,0xEE}
};
static const ble_uuid128_t EMG_CHAR_UUID128= {
    .u = { .type = BLE_UUID_TYPE_128 },
    .value = {0x7a,0x26,0x4b,0x2b,0x98,0x31,0x4f,0x6d,0x93,0x92,0x10,0x2d,0x00,0x01,0xEE,0xEE}
};

static struct ble_gatt_chr_def emg_chrs[] = {
    {
        .uuid = &EMG_CHAR_UUID128.u,
        .flags = BLE_GATT_CHR_F_NOTIFY | BLE_GATT_CHR_F_READ,
        .access_cb = emg_chr_access_cb,
        .val_handle = &s_val_handle,
    },
    {0},
};

static struct ble_gatt_svc_def emg_svcs[] = {
    {
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = &EMG_SVC_UUID128.u,
        .characteristics = emg_chrs,
    },
    {0},
};

// GAP event handler: connection lifecycle, subscription, and MTU updates
static int gap_event(struct ble_gap_event *event, void *arg) {
    (void)arg;
    switch (event->type) {
        case BLE_GAP_EVENT_CONNECT:
            if (event->connect.status == 0) {
                s_conn_handle = event->connect.conn_handle;
                ESP_LOGI(TAG, "BLE connected, conn=%u", s_conn_handle);
            } else {
                ESP_LOGW(TAG, "BLE connect failed; restarting adv");
                struct ble_gap_adv_params p = { .disc_mode = BLE_GAP_DISC_MODE_GEN, .conn_mode = BLE_GAP_CONN_MODE_UND };
                ble_gap_adv_start(BLE_OWN_ADDR_PUBLIC, NULL, BLE_HS_FOREVER, &p, gap_event, NULL);
            }
            break;
        case BLE_GAP_EVENT_MTU:
            ESP_LOGI(TAG, "MTU updated: conn=%u mtu=%u", event->mtu.conn_handle, event->mtu.value);
            break;
        case BLE_GAP_EVENT_DISCONNECT:
            ESP_LOGI(TAG, "BLE disconnected; restarting adv");
            s_conn_handle = 0; s_notify_enabled = false;
            {
                struct ble_gap_adv_params p = { .disc_mode = BLE_GAP_DISC_MODE_GEN, .conn_mode = BLE_GAP_CONN_MODE_UND };
                ble_gap_adv_start(BLE_OWN_ADDR_PUBLIC, NULL, BLE_HS_FOREVER, &p, gap_event, NULL);
            }
            break;
        case BLE_GAP_EVENT_SUBSCRIBE:
            if (event->subscribe.attr_handle == s_val_handle) {
                s_notify_enabled = event->subscribe.cur_notify;
                ESP_LOGI(TAG, "Notify %s", s_notify_enabled ? "ENABLED" : "DISABLED");
            }
            break;
        default:
            break;
    }
    return 0;
}

// No separate GATTS callback in NimBLE; subscription handled in gap_event

// Notification publisher task
// Consumes processed EMG packets and emits compact frames at a controlled rate
static void ble_notify_task(void *arg) {
    (void)arg;
    QueueHandle_t q = emg_get_proc_queue();
    emg_packet_t p;
    int64_t last_send_us = 0;
    const int64_t interval_us = (int64_t)BLE_STREAM_INTERVAL_MS * 1000;
    while (1) {
        if (q && xQueueReceive(q, &p, portMAX_DELAY) == pdTRUE) {
            int64_t now = esp_timer_get_time();
            if (!s_notify_enabled || !s_conn_handle || !s_val_handle) {
                // Not connected or notifications disabled; just drop/advance
                continue;
            }
            if (now - last_send_us < interval_us) {
                // Rate limit: skip until interval elapses
                continue;
            }

            // Build compact 12-byte packet (little-endian):
            // Layout:
            //   - ts_ms   (uint32_t): downsampled timestamp in ms
            //   - env_mv  (int16_t) : envelope scaled to millivolts
            //   - rms_mv  (int16_t) : RMS scaled to millivolts
            //   - active  (uint8_t) : activation flag (0/1)
            //   - quality (uint8_t) : signal quality percentage 0..100
            //   - seq     (uint16_t): sequence number for drop/reorder detection
            uint8_t pkt[12];
            uint32_t ts_ms = (uint32_t)(p.ts_us / 1000);
            // Scale to millivolts and clamp
            float env_mv_f = p.env * 1000.0f;
            float rms_mv_f = p.rms * 1000.0f;
            int env_mv = (int)lrintf(env_mv_f);
            int rms_mv = (int)lrintf(rms_mv_f);
            if (env_mv > 32767) env_mv = 32767; else if (env_mv < -32768) env_mv = -32768;
            if (rms_mv > 32767) rms_mv = 32767; else if (rms_mv < -32768) rms_mv = -32768;
            uint8_t active = (uint8_t)(p.active ? 1 : 0);
            // Map SNR (~0..4+) to 0..100%
            float qf = p.snr * 25.0f; if (qf > 100.0f) qf = 100.0f; if (qf < 0.0f) qf = 0.0f;
            uint8_t quality = (uint8_t)lrintf(qf);
            uint16_t seq = s_seq++;

            int off = 0;
            memcpy(&pkt[off], &ts_ms, sizeof(ts_ms)); off += sizeof(ts_ms);
            int16_t env_s = (int16_t)env_mv; memcpy(&pkt[off], &env_s, sizeof(env_s)); off += sizeof(env_s);
            int16_t rms_s = (int16_t)rms_mv; memcpy(&pkt[off], &rms_s, sizeof(rms_s)); off += sizeof(rms_s);
            memcpy(&pkt[off], &active, sizeof(active)); off += sizeof(active);
            memcpy(&pkt[off], &quality, sizeof(quality)); off += sizeof(quality);
            memcpy(&pkt[off], &seq, sizeof(seq)); off += sizeof(seq);

            // Stream the 12-byte packet via a GATT notification
            struct os_mbuf *om = ble_hs_mbuf_from_flat(pkt, off);
            if (om) {
                (void)ble_gatts_notify_custom(s_conn_handle, s_val_handle, om);
                last_send_us = now;
            }
        }
    }
}

static void ble_host_task(void *param) {
    (void)param;
    nimble_port_run();
    nimble_port_freertos_deinit();
}

// Callback when NimBLE host/stack is synced and ready
static void on_ble_sync(void) {
    ESP_LOGI(TAG, "NimBLE host synced, configuring services...");
    
    // Now safe to configure GAP/GATT services
    ble_svc_gap_init();
    ble_svc_gatt_init();
    ble_svc_gap_device_name_set("EMG-BRIDGE");

    // Prefer higher MTU; final MTU is negotiated and reported via GAP events
    ble_att_set_preferred_mtu(128);

    // Register our custom EMG service and characteristic
    ble_gatts_count_cfg(emg_svcs);
    ble_gatts_add_svcs(emg_svcs);

    // Start advertising with flags and complete local name
    struct ble_hs_adv_fields f = {0};
    const char *name = "EMG-BRIDGE";
    f.flags = BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP;
    f.name = (uint8_t*)name;
    f.name_len = (uint8_t)strlen(name);
    f.name_is_complete = 1;
    int rc = ble_gap_adv_set_fields(&f);
    if (rc != 0) {
        ESP_LOGW(TAG, "adv set fields failed: rc=%d", rc);
    }

    struct ble_gap_adv_params p = {0};
    p.conn_mode = BLE_GAP_CONN_MODE_UND;
    p.disc_mode = BLE_GAP_DISC_MODE_GEN;
    rc = ble_gap_adv_start(BLE_OWN_ADDR_PUBLIC, NULL, BLE_HS_FOREVER, &p, gap_event, NULL);
    if (rc != 0) {
        ESP_LOGW(TAG, "adv start failed: rc=%d", rc);
    }

    ESP_LOGI(TAG, "BLE advertising as EMG-BRIDGE");
}

// Callback on host reset (e.g., after stack failure or restart)
static void on_ble_reset(int reason) {
    ESP_LOGW(TAG, "NimBLE host reset, reason=%d", reason);
}

void ble_emg_start(void) {
    ESP_LOGI(TAG, "BLE init starting...");
    
    // Initialize BLE controller and HCI for NimBLE (robust, non-fatal on failure)
    esp_bt_controller_config_t bt_cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    (void)esp_bt_controller_mem_release(ESP_BT_MODE_CLASSIC_BT);
    
    esp_err_t err = esp_bt_controller_init(&bt_cfg);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "BT controller init failed: %d (possible sdkconfig mismatch or BLE5 conflict)", err);
        ESP_LOGW(TAG, "BLE disabled; continuing without wireless. Hint: disable BLE 5 features in menuconfig if needed.");
        return; // do not continue; avoid host start and subsequent panic
    }
    
    err = esp_bt_controller_enable(ESP_BT_MODE_BLE);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "BT controller enable failed: %d", err);
        ESP_LOGW(TAG, "BLE disabled; continuing without wireless.");
        return;
    }
    
    // Give controller time to stabilize before starting HCI
    vTaskDelay(pdMS_TO_TICKS(100));
    
    err = esp_nimble_hci_init();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "NimBLE HCI init failed: %d", err);
        ESP_LOGW(TAG, "BLE disabled; continuing without wireless.");
        return;
    }
    
    // Only proceed to host init if controller and HCI succeeded
    ESP_LOGI(TAG, "BLE controller OK, starting NimBLE host...");
    
    // Initialize NimBLE port (must succeed before starting host task)
    nimble_port_init();
    
    // Verify nimble port initialized successfully
    if (!ble_hs_is_enabled()) {
        ESP_LOGE(TAG, "NimBLE host not enabled after init; BLE disabled.");
        return;
    }

    // Register sync/reset callbacks BEFORE starting host task
    ble_hs_cfg.sync_cb = on_ble_sync;
    ble_hs_cfg.reset_cb = on_ble_reset;

    // Start NimBLE host task on FreeRTOS
    // Services will be configured in on_ble_sync() when stack is ready
    nimble_port_freertos_init(ble_host_task);

    // Start BLE notify task
    xTaskCreate(ble_notify_task, "ble_notify", 4096, NULL, 5, NULL);
    ESP_LOGI(TAG, "NimBLE host task started, waiting for sync...");
}
