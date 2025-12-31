/*
i2c_scan.c - I2C bus scanner utility
Scans all 7-bit I2C addresses (0x03-0x77) and reports which devices respond
*/

#include "driver/i2c.h"
#include "esp_log.h"

static const char *TAG = "I2C_SCAN";
#define SCAN_TIMEOUT_MS 200

#define I2C_PORT I2C_NUM_0

void i2c_scan_bus(int sda_gpio, int scl_gpio) {
    ESP_LOGI(TAG, "Scanning I2C bus on SDA=%d, SCL=%d...", sda_gpio, scl_gpio);
    
    int found = 0;
    for (uint8_t addr = 0x03; addr < 0x78; addr++) {
        i2c_cmd_handle_t cmd = i2c_cmd_link_create();
        i2c_master_start(cmd);
        i2c_master_write_byte(cmd, (addr << 1) | I2C_MASTER_WRITE, true);
        i2c_master_stop(cmd);
        
        esp_err_t err = i2c_master_cmd_begin(I2C_PORT, cmd, pdMS_TO_TICKS(SCAN_TIMEOUT_MS));
        i2c_cmd_link_delete(cmd);
        
        if (err == ESP_OK) {
            ESP_LOGI(TAG, "  Found device at 0x%02X", addr);
            found++;
        }
    }
    
    if (found == 0) {
        ESP_LOGW(TAG, "No I2C devices found! Check wiring:");
        ESP_LOGW(TAG, "  - SDA on GPIO%d", sda_gpio);
        ESP_LOGW(TAG, "  - SCL on GPIO%d", scl_gpio);
        ESP_LOGW(TAG, "  - VDD connected to 3.3V");
        ESP_LOGW(TAG, "  - GND connected");
        ESP_LOGW(TAG, "  - Pull-ups present (internal or external)");
    } else {
        ESP_LOGI(TAG, "Scan complete, found %d device(s)", found);
    }
}
