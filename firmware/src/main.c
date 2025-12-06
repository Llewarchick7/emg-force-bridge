#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"

// acquisition start
void emg_acq_start(void);

static const char *TAG = "main";

void app_main(void) {
    ESP_LOGI(TAG, "EMG Force Bridge firmware booting...");
    // Start EMG acquisition task (ADS1115 ~860 SPS)
    emg_acq_start();
    while (true) {
        vTaskDelay(pdMS_TO_TICKS(1000));
        ESP_LOGI(TAG, "heartbeat");
    }
}
