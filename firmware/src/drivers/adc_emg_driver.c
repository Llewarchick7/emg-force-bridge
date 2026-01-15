/*
adc_emg_driver.c
copyright (c) 2025 Logan Lewarchick
Licensed under the MIT License (see LICENSE file)
------------------------------------------
Purpose:  Implements an ESP32 (master) I2C driver for the ADS1115(slave) 16-bit ADC
          to configure conversion behavior and read EMG signals from MyoWare sensors.

Hardware: ADS1115 is a 16-bit I2C ADC(Analog-to-Digital Converter) with a PGA (Programmable Gain Amplifier)

Wiring:   Connect ADS1115 to ESP32 I2C pins (SCL, SDA), power (VDD, GND).

references:
- ADS1115 datasheet: https://www.ti.com/lit/ds/symlink/ads1115.pdf
- ESP32-S3 + ESP-IDF documentation: https://docs.espressif.com/projects/esp-idf/en/v5.5.1/esp32s3/get-started/index.html 
*/

// Headers from ESP-IDF...
#include "driver/i2c.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "driver/gpio.h"

// Standard C library headers...
#include <stdint.h>
#include <stdbool.h>

// Internal headers
#include "i2c_scan.h"

// Forward declarations for internal helpers
esp_err_t ads1115_read_config(uint16_t *out_cfg);

static const char *TAG = "ADS1115";
// Diagnostic option: enable ESP32 internal I2C pull-ups
// Default 0 now that external pull-ups are installed.
#ifndef ADS_I2C_PULLUPS_INTERNAL_TEST
#define ADS_I2C_PULLUPS_INTERNAL_TEST 0
#endif

// Helper to (re)initialize I2C with given pins, clock and internal pull-up option
static esp_err_t i2c_reinit(i2c_port_t port, int sda_gpio, int scl_gpio, int clk_hz, bool use_internal_pullups) {
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = sda_gpio,
        .sda_pullup_en = use_internal_pullups ? GPIO_PULLUP_ENABLE : GPIO_PULLUP_DISABLE,
        .scl_io_num = scl_gpio,
        .scl_pullup_en = use_internal_pullups ? GPIO_PULLUP_ENABLE : GPIO_PULLUP_DISABLE,
        .master.clk_speed = clk_hz,
        .clk_flags = 0,
    };
    esp_err_t err = i2c_param_config(port, &conf);
    if (err != ESP_OK) return err;
    err = i2c_driver_install(port, conf.mode, 0, 0, 0);
    return err;
}
// Check bus idle levels to infer presence of external pull-ups and wiring health
static void i2c_bus_idle_check(int sda_gpio, int scl_gpio) {
    gpio_config_t conf_in = {
        .pin_bit_mask = (1ULL << sda_gpio) | (1ULL << scl_gpio),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&conf_in);
    // Small settle delay
    vTaskDelay(pdMS_TO_TICKS(5));
    int sda_lvl = gpio_get_level(sda_gpio);
    int scl_lvl = gpio_get_level(scl_gpio);
    ESP_LOGI(TAG, "Bus idle levels: SDA=%d SCL=%d (expect 1/1 with pull-ups)", sda_lvl, scl_lvl);
}

// Perform a minimal I2C controller sanity check: issue START + address write and
// observe the result to differentiate controller activity (NACK) from bus timeout.
static void i2c_sanity_check(i2c_port_t port) {
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    // Use an address unlikely to exist; any non-present address should NACK
    const uint8_t addr = 0x00; // reserved; typical devices won't ACK this
    i2c_master_start(cmd);
    (void)i2c_master_write_byte(cmd, (addr << 1) | I2C_MASTER_WRITE, true);
    i2c_master_stop(cmd);
    esp_err_t err = i2c_master_cmd_begin(port, cmd, pdMS_TO_TICKS(50));
    i2c_cmd_link_delete(cmd);

    if (err == ESP_OK) {
        ESP_LOGI(TAG, "I2C sanity: unexpected ACK at 0x%02X (controller active)", addr);
    } else if (err == ESP_FAIL) {
        ESP_LOGI(TAG, "I2C sanity: saw NACK as expected (controller active)");
    } else if (err == ESP_ERR_TIMEOUT) {
        ESP_LOGE(TAG, "I2C sanity: bus timeout (SCL/SDA stuck?)");
    } else {
        ESP_LOGW(TAG, "I2C sanity: cmd error %d", err);
    }
}

// I2C bus configuration and ADC address
#define ADS1115_I2C_PORT I2C_NUM_0 // I2C port number on ESP32-S3
#define ADS1115_SCL_GPIO  5  // Physical GPIO pin for SCL line on ESP32-S3
#define ADS1115_SDA_GPIO  4  // Physical GPIO pin for SDA line on ESP32-S3
#define ADS1115_ADDR      0x48  // ADS1115 slave address, ADDR pin tied to GND by default
// I2C clock (lowered for stability during bring-up)
#define ADS1115_I2C_CLK_HZ 100000 // 100 kHz standard mode

// ADS1115 register addresses
#define ADS1115_REG_CONVERSION 0x00
#define ADS1115_REG_CONFIG     0x01


// ---------------- Config Register Bit Definitions ------------------------------------------------
#define ADS1115_OS_SINGLE        (0b1   << 15)
#define ADS1115_MUX_AIN0_AIN1    (0b000 << 12)
#define ADS1115_MUX_AIN0_AIN3    (0b001 << 12)
#define ADS1115_MUX_AIN1_AIN3    (0b010 << 12)
#define ADS1115_MUX_AIN2_AIN3    (0b011 << 12)
#define ADS1115_MUX_AIN0_GND     (0b100 << 12)
#define ADS1115_MUX_AIN1_GND     (0b101 << 12)
#define ADS1115_MUX_AIN2_GND     (0b110 << 12)
#define ADS1115_MUX_AIN3_GND     (0b111 << 12)

#define ADS1115_PGA_6V144        (0b000 << 9)
#define ADS1115_PGA_4V096        (0b001 << 9)
#define ADS1115_PGA_2V048        (0b010 << 9)
#define ADS1115_PGA_1V024        (0b011 << 9)
#define ADS1115_PGA_0V512        (0b100 << 9)
#define ADS1115_PGA_0V256        (0b101 << 9) // also 110/111
// Mask for clearing/setting PGA field [11:9]
#define ADS1115_PGA_MASK         (0b111 << 9)

#define ADS1115_MODE_CONTINUOUS  (0b0   << 8)
#define ADS1115_MODE_SINGLESHOT  (0b1   << 8)

#define ADS1115_DR_8             (0b000 << 5)
#define ADS1115_DR_16            (0b001 << 5)
#define ADS1115_DR_32            (0b010 << 5)
#define ADS1115_DR_64            (0b011 << 5)
#define ADS1115_DR_128           (0b100 << 5)
#define ADS1115_DR_250           (0b101 << 5)
#define ADS1115_DR_475           (0b110 << 5)
#define ADS1115_DR_860           (0b111 << 5)

#define ADS1115_COMP_DISABLE     (0b11)
// -------------------------------------------------------------------------------------------------

static float s_gain = 1.0f; // software scaling until hardware PGA available
static float s_lsb_volts = 4.096f / 32768.0f; // default for ±4.096 V PGA

static inline float pga_lsb_from_field(uint16_t pga_field) {
    // Returns the volts-per-count LSB value based on the PGA field setting
    switch (pga_field) {
        case ADS1115_PGA_6V144: return 6.144f / 32768.0f;
        case ADS1115_PGA_4V096: return 4.096f / 32768.0f;
        case ADS1115_PGA_2V048: return 2.048f / 32768.0f;
        case ADS1115_PGA_1V024: return 1.024f / 32768.0f;
        case ADS1115_PGA_0V512: return 0.512f / 32768.0f;
        case ADS1115_PGA_0V256: return 0.256f / 32768.0f;
        default:                return 4.096f / 32768.0f; // sane fallback
    }
}

static inline bool pga_field_valid(uint16_t pga_field) {
    /*
    Description:
        Validates if the provided PGA field corresponds to a valid ADS1115 PGA setting.
    Parameters:
        pga_field: The PGA field value to validate.
    Returns:
        true if the field is valid, false otherwise.
    */
    return pga_field == ADS1115_PGA_6V144 ||
           pga_field == ADS1115_PGA_4V096 ||
           pga_field == ADS1115_PGA_2V048 ||
           pga_field == ADS1115_PGA_1V024 ||
           pga_field == ADS1115_PGA_0V512 ||
           pga_field == ADS1115_PGA_0V256;
}

esp_err_t ads1115_set_pga(uint16_t pga_field) {
    /*
    Description:
        Sets the Programmable Gain Amplifier (PGA) setting on the ADS1115 ADC.
    Parameters:
        pga_field: One of the ADS1115_PGA_* constants defining the desired gain.
    Returns:
        ESP_OK on success, or an ESP error code on failure.
    */
    if (!pga_field_valid(pga_field)) {
        ESP_LOGE(TAG, "Invalid PGA field: 0x%04X", pga_field);
        return ESP_ERR_INVALID_ARG;
    }
    uint16_t cfg = 0;
    esp_err_t err = ads1115_read_config(&cfg);
    if (err != ESP_OK) return err;
    cfg &= ~ADS1115_PGA_MASK;
    cfg |= pga_field;
    uint8_t buf[3] = { ADS1115_REG_CONFIG, (uint8_t)(cfg >> 8), (uint8_t)(cfg & 0xFF) };
    err = i2c_master_write_to_device(ADS1115_I2C_PORT, ADS1115_ADDR, buf, sizeof(buf), pdMS_TO_TICKS(100));
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "ADS1115 set PGA write failed: %d", err);
        return err;
    }
    s_lsb_volts = pga_lsb_from_field(pga_field);
    ESP_LOGI(TAG, "ADS1115 PGA updated, LSB=%.9f V/count", (double)s_lsb_volts);
    return ESP_OK;
}

esp_err_t ads1115_read_config(uint16_t *out_cfg) {
    /*
    Description: 
        Reads the current configuration register from the ADS1115.
    Parameters:
        out_cfg: Pointer to a uint16_t variable where the configuration register value will be stored.
    Returns:
        ESP_OK on success, or an ESP error code on failure.
        out_cfg will contain the 16-bit configuration register value if the read is successful.
    */
    if (!out_cfg) return ESP_ERR_INVALID_ARG;
    uint8_t reg = ADS1115_REG_CONFIG; // set the register pointer to CONFIG register
    uint8_t data[2] = {0, 0}; // buffer to hold the read data
    // Read 16-bit CONFIG register...
    esp_err_t err = i2c_master_write_read_device(ADS1115_I2C_PORT, ADS1115_ADDR, &reg, 1, data, 2, pdMS_TO_TICKS(50)); // stores read data into 'data' array
    if (err != ESP_OK) return err; // read failed
    *out_cfg = (uint16_t)((data[0] << 8) | data[1]); // combine MSB( Most Significant Byte) and LSB (Least Significant Byte) into one 16-bit word
    return ESP_OK; // read successful
}

// Quick probe to verify the ADS1115 responds at the configured I2C address
esp_err_t ads1115_probe(void) {
    uint8_t reg = ADS1115_REG_CONFIG;
    uint8_t data[2] = {0, 0};
    esp_err_t err = i2c_master_write_read_device(ADS1115_I2C_PORT, ADS1115_ADDR, &reg, 1, data, 2, pdMS_TO_TICKS(50));
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "ADS1115 not responding at 0x%02X (I2C err=%d). Check VDD, GND, SDA, SCL, pull-ups, and ADDR wiring.", ADS1115_ADDR, err);
        return err;
    }
    ESP_LOGI(TAG, "ADS1115 detected at 0x%02X", ADS1115_ADDR);
    return ESP_OK;
}

// Diagnostic: probe all possible ADDR variants and log ACK/no-ACK
static void ads1115_probe_addr_variants(void) {
    const uint8_t addrs[4] = { 0x48, 0x49, 0x4A, 0x4B };
    const char *labels[4] = {
        "ADDR=GND (0x48)",
        "ADDR=VDD (0x49)",
        "ADDR=SDA  (0x4A)",
        "ADDR=SCL  (0x4B)"
    };
    uint8_t reg = ADS1115_REG_CONFIG;
    uint8_t data[2] = {0, 0};
    ESP_LOGI(TAG, "Probing ADDR variants: GND/VDD/SDA/SCL -> 0x48/0x49/0x4A/0x4B");
    for (int i = 0; i < 4; ++i) {
        esp_err_t err = i2c_master_write_read_device(ADS1115_I2C_PORT, addrs[i], &reg, 1, data, 2, pdMS_TO_TICKS(50));
        if (err == ESP_OK) {
            ESP_LOGI(TAG, "  ACK at %s", labels[i]);
        } else {
            ESP_LOGW(TAG, "  No ACK at %s (err=%d)", labels[i], err);
        }
    }
}

esp_err_t ads1115_init(void) {
    /*
    Description:
        Initializes the ADS1115 ADC over I2C with default configuration:
        - AIN0 vs GND
        - ±4.096 V range
        - Continuous conversion mode
        - 860 samples per second
        - Comparator disabled
    Returns:
        ESP_OK on success, or an ESP error code on failure.
    */

    // Initializes an I2C configuration struct for ESP-IDF-based driver...
    // To set up I2C communication with the ADS1115 ADC
    esp_err_t err = i2c_reinit(ADS1115_I2C_PORT, ADS1115_SDA_GPIO, ADS1115_SCL_GPIO, ADS1115_I2C_CLK_HZ, ADS_I2C_PULLUPS_INTERNAL_TEST);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "i2c init failed: %d", err);
        return err;
    }

    ESP_LOGI(TAG, "I2C pull-ups: %s", ADS_I2C_PULLUPS_INTERNAL_TEST ? "internal (ESP32 GPIO)" : "external (board) expected");
    // Quick sanity to verify master is issuing START/STOP and bus responds
    i2c_sanity_check(ADS1115_I2C_PORT);

    // Verify the ADS1115 is present before writing configuration
    // First, check bus idle levels (should be high if pull-ups are present)
    i2c_bus_idle_check(ADS1115_SDA_GPIO, ADS1115_SCL_GPIO);
    // Provide targeted diagnostics if one line is stuck
    int sda_lvl = gpio_get_level(ADS1115_SDA_GPIO);
    int scl_lvl = gpio_get_level(ADS1115_SCL_GPIO);
    if (sda_lvl == 0 && scl_lvl == 1) {
        ESP_LOGW(TAG, "SDA stuck LOW while SCL HIGH: likely missing pull-up on SDA, short to GND, bad jumper, or miswired SDA pin.");
        ESP_LOGW(TAG, "  Actions: reseat/replace SDA jumper, verify ADS1115 SDA pin to GPIO%d, check ADDR/ALERT not connected to SDA, ensure pull-ups present (internal or external).", ADS1115_SDA_GPIO);
    }
    // Quick probe first, so we see ACK/no-ACK promptly
    err = ads1115_probe();
    if (err != ESP_OK) {
        // Log specific ADDR-variant results to help with wiring/address diagnosis
        ads1115_probe_addr_variants();
        ESP_LOGI(TAG, "Running full I2C bus scan (SDA=%d, SCL=%d, %d Hz, internal pull-ups %s)",
             ADS1115_SDA_GPIO, ADS1115_SCL_GPIO, ADS1115_I2C_CLK_HZ,
             ADS_I2C_PULLUPS_INTERNAL_TEST ? "ENABLED" : "DISABLED");
        i2c_scan_bus(ADS1115_SDA_GPIO, ADS1115_SCL_GPIO);
        ESP_LOGW(TAG, "Initial probe failed; attempting SDA/SCL swap fallback...");
        // Tear down and reconfigure with swapped pins to detect reversed wiring
        i2c_driver_delete(ADS1115_I2C_PORT);
        esp_err_t e2 = i2c_reinit(ADS1115_I2C_PORT, ADS1115_SCL_GPIO, ADS1115_SDA_GPIO, ADS1115_I2C_CLK_HZ, ADS_I2C_PULLUPS_INTERNAL_TEST);
        if (e2 != ESP_OK) {
            ESP_LOGE(TAG, "i2c init (swapped) failed: %d", e2);
            return e2;
        }
        ESP_LOGI(TAG, "Re-scanning I2C bus with swapped pins (SDA=%d, SCL=%d, internal pull-ups %s)",
                 ADS1115_SCL_GPIO, ADS1115_SDA_GPIO,
                 ADS_I2C_PULLUPS_INTERNAL_TEST ? "ENABLED" : "DISABLED");
        i2c_scan_bus(ADS1115_SCL_GPIO, ADS1115_SDA_GPIO);
        e2 = ads1115_probe();
        if (e2 != ESP_OK) {
            ESP_LOGW(TAG, "No response after pin swap; trying slower clock and internal pull-ups for diagnostics...");
            // Try original pins with 10 kHz and internal pull-ups
            i2c_driver_delete(ADS1115_I2C_PORT);
            const int slow_clk = 10000;
            e2 = i2c_reinit(ADS1115_I2C_PORT, ADS1115_SDA_GPIO, ADS1115_SCL_GPIO, slow_clk, true);
            if (e2 != ESP_OK) {
                ESP_LOGE(TAG, "i2c init (slow/internal) failed: %d", e2);
                return err;
            }
            ESP_LOGI(TAG, "Re-probing at 10 kHz with internal pull-ups enabled");
            ads1115_probe_addr_variants();
            i2c_scan_bus(ADS1115_SDA_GPIO, ADS1115_SCL_GPIO);
            e2 = ads1115_probe();
            if (e2 != ESP_OK) {
                ESP_LOGE(TAG, "ADS1115 still not responding; check VDD=3.3V, GND common, correct SDA/SCL pads, and ADDR wiring");
                return err; // return original error
            }
        }
        ESP_LOGW(TAG, "ADS1115 responded with swapped pins; wiring likely reversed. Continuing with swapped configuration.");
        // Continue with swapped configuration in effect
    }

    /*
    Build the Config Value for ADS1115 Config register:
        - AIN0 vs GND
        - ±4.096 V
        - continuous
        - 860 SPS
        - comparator disabled
    Note: Switch to ADS1115_PGA_2V048 if signal fits ±2.048 V for finer resolution
    */ 
    uint16_t cfg =
        ADS1115_MUX_AIN0_GND |
        ADS1115_PGA_4V096    |
        ADS1115_MODE_CONTINUOUS |
        ADS1115_DR_860       |
        ADS1115_COMP_DISABLE;

    // Write configuration to ADS1115...
    uint8_t buf[3] = { ADS1115_REG_CONFIG, (uint8_t)(cfg >> 8), (uint8_t)(cfg & 0xFF) }; // buffer to hold register address and config data
    // Sends the register address followed by the two data bytes to set the ADS1115 config register...
    err = i2c_master_write_to_device(ADS1115_I2C_PORT, ADS1115_ADDR, buf, sizeof(buf), pdMS_TO_TICKS(100)); 
    // Check for errors...
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "ADS1115 write config failed: %d", err);
        return err;
    }
    // Read back configuration to verify
    uint16_t readback = 0;
    if (ads1115_read_config(&readback) == ESP_OK) {
        ESP_LOGI(TAG, "ADS1115 cfg written=0x%04X readback=0x%04X", cfg, readback);
    }
    // initialize LSB based on the configured PGA
    s_lsb_volts = pga_lsb_from_field(ADS1115_PGA_4V096);
    ESP_LOGI(TAG, "ADS1115 configured for continuous 860 SPS on AIN0");
    return ESP_OK;
}

esp_err_t ads1115_read_sample(int16_t *out_raw) {
    /*
    Description:
        Reads a single conversion sample from the ADS1115 conversion register.
    Parameters:
        out_raw: Pointer to an int16_t variable where the raw ADC sample will be stored.
    Returns:
        ESP_OK on success, or an ESP error code on failure.
        out_raw will contain the 16-bit signed ADC sample if the read is successful.
    */
    if (!out_raw) return ESP_ERR_INVALID_ARG;
    uint8_t reg = ADS1115_REG_CONVERSION;
    uint8_t data[2] = {0, 0}; // buffer to hold the read data
    // Read 16-bit conversion result...
    esp_err_t err = i2c_master_write_read_device(ADS1115_I2C_PORT, ADS1115_ADDR, &reg, 1, data, 2, pdMS_TO_TICKS(50)); // stores read data into 'data' array
    if (err != ESP_OK) return err;
    *out_raw = (int16_t)((data[0] << 8) | data[1]);
    return ESP_OK;
}

void ads1115_set_gain(float gain) {
    /*
    Description:
        Sets a software gain factor to scale the voltage readings.
    Parameters:
        gain: The gain factor to apply to the voltage readings. Must be > 0.0 and <= 100.0.
    Returns:
        None. Logs an error if the gain value is invalid.
    */
    if (gain > 0.0f && gain <= 100.0f) {
        s_gain = gain;
    } else {
        ESP_LOGE(TAG, "Invalid gain value: %f (must be > 0.0 and <= 100.0)", gain);
    }
}

float ads1115_scale_to_volts(int16_t raw) {
    /*
    Description:
        Converts a raw ADC sample to a voltage value in volts, applying the configured software gain.
    Parameters:
        raw: The raw 16-bit ADC sample to convert.
    Returns:
        The voltage corresponding to the raw ADC sample, scaled by the software gain.
    */
    return (raw * s_lsb_volts) * s_gain;
}