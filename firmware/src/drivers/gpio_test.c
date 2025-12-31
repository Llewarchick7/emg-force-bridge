/*
gpio_test.c - GPIO pin test utility without multimeter
Tests GPIO functionality by reading back set values and checking input/output
*/

#include "driver/gpio.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "GPIO_TEST";

#define TEST_SDA_PIN 8
#define TEST_SCL_PIN 9

void gpio_test_run(void) {
    ESP_LOGI(TAG, "=== GPIO Software Test (no multimeter needed) ===");
    ESP_LOGI(TAG, "Testing SDA=%d, SCL=%d", TEST_SDA_PIN, TEST_SCL_PIN);
    
    // Test 1: Output mode - set and read back
    ESP_LOGI(TAG, "Test 1: Output mode test...");
    gpio_config_t out_conf = {
        .pin_bit_mask = (1ULL << TEST_SDA_PIN) | (1ULL << TEST_SCL_PIN),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&out_conf);
    
    bool output_ok = true;
    
    // Set HIGH and read back
    gpio_set_level(TEST_SDA_PIN, 1);
    gpio_set_level(TEST_SCL_PIN, 1);
    vTaskDelay(pdMS_TO_TICKS(10));
    int sda_high = gpio_get_level(TEST_SDA_PIN);
    int scl_high = gpio_get_level(TEST_SCL_PIN);
    
    if (sda_high != 1 || scl_high != 1) {
        ESP_LOGE(TAG, "  FAIL: Set HIGH but read SDA=%d, SCL=%d (expected 1,1)", sda_high, scl_high);
        output_ok = false;
    } else {
        ESP_LOGI(TAG, "  PASS: HIGH readback correct");
    }
    
    // Set LOW and read back
    gpio_set_level(TEST_SDA_PIN, 0);
    gpio_set_level(TEST_SCL_PIN, 0);
    vTaskDelay(pdMS_TO_TICKS(10));
    int sda_low = gpio_get_level(TEST_SDA_PIN);
    int scl_low = gpio_get_level(TEST_SCL_PIN);
    
    if (sda_low != 0 || scl_low != 0) {
        ESP_LOGE(TAG, "  FAIL: Set LOW but read SDA=%d, SCL=%d (expected 0,0)", sda_low, scl_low);
        output_ok = false;
    } else {
        ESP_LOGI(TAG, "  PASS: LOW readback correct");
    }
    
    // Test 2: Input mode with pull-up
    ESP_LOGI(TAG, "Test 2: Input mode with pull-up...");
    gpio_config_t in_conf = {
        .pin_bit_mask = (1ULL << TEST_SDA_PIN) | (1ULL << TEST_SCL_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&in_conf);
    vTaskDelay(pdMS_TO_TICKS(10));
    
    int sda_pullup = gpio_get_level(TEST_SDA_PIN);
    int scl_pullup = gpio_get_level(TEST_SCL_PIN);
    
    if (sda_pullup != 1 || scl_pullup != 1) {
        ESP_LOGW(TAG, "  WARN: Pull-up test: SDA=%d, SCL=%d (expected 1,1 when floating)", sda_pullup, scl_pullup);
        ESP_LOGW(TAG, "  This may be normal if pins have external pull-downs or are shorted");
    } else {
        ESP_LOGI(TAG, "  PASS: Pull-ups working (pins read HIGH when floating)");
    }
    
    // Summary
    ESP_LOGI(TAG, "=== GPIO Test Summary ===");
    if (output_ok) {
        ESP_LOGI(TAG, "GPIO pins appear functional");
        ESP_LOGI(TAG, "If I2C still fails, check:");
        ESP_LOGI(TAG, "  1. ADS1115 power (VDD should be 3.3V)");
        ESP_LOGI(TAG, "  2. Physical wiring connections (loose wires?)");
        ESP_LOGI(TAG, "  3. ADS1115 chip may be damaged");
        ESP_LOGI(TAG, "  4. Wrong board pinout (GPIO17/18 may not be where you think)");
    } else {
        ESP_LOGE(TAG, "GPIO pins NOT working correctly!");
        ESP_LOGE(TAG, "Possible causes:");
        ESP_LOGE(TAG, "  1. GPIO17/18 used by USB-Serial or JTAG on your board");
        ESP_LOGE(TAG, "  2. These are strapping pins - check ESP32-S3 datasheet");
        ESP_LOGE(TAG, "  3. Try different GPIOs (e.g., GPIO8/GPIO9 or GPIO10/GPIO11)");
    }
}
