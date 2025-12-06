#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"

static const char *TAG = "main";

void app_main(void) {
    ESP_LOGI(TAG, "EMG Force Bridge firmware booting...");
    // TODO: init drivers, create tasks
    while (true) {
        vTaskDelay(pdMS_TO_TICKS(1000));
        ESP_LOGI(TAG, "heartbeat");
    }
}
