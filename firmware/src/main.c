#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "nvs_flash.h"

// acquisition start
void emg_acq_start(void);
void emg_proc_start(void);
void emg_stream_start(void);
void ble_emg_start(void);
void gpio_test_run(void);

static const char *TAG = "main";

void app_main(void) {
    ESP_LOGI(TAG, "EMG Force Bridge firmware booting...");
    ESP_LOGI("POWER", "ESP32 3V3 pin should be live now");
    
    // Optional: Run GPIO test to verify pins are working.
    // Disabled by default to avoid driving I2C lines when hardware is connected.
    // Define RUN_GPIO_TEST at build time to enable.
    #ifdef RUN_GPIO_TEST
    ESP_LOGI(TAG, "Running GPIO test on SDA/SCL pins...");
    gpio_test_run();
    #endif
    
    // Initialize NVS (required by BLE stack for storing bonds/keys)
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ESP_ERROR_CHECK(nvs_flash_init());
    } else {
        ESP_ERROR_CHECK(ret);
    }
    // Start EMG acquisition and streaming (ADS1115 ~860 SPS)
    emg_acq_start();
    emg_proc_start();
    emg_stream_start();
    ble_emg_start();
    while (true) {
        vTaskDelay(pdMS_TO_TICKS(1000));
        ESP_LOGI(TAG, "heartbeat");
    }
}
