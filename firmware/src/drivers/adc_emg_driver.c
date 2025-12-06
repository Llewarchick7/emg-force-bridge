// ADS1115 16-bit I2C ADC driver for sEMG sampling (ESP32-IDF)
#include "driver/i2c.h"
#include "esp_log.h"
#include "esp_timer.h"
#include <stdint.h>

static const char *TAG = "ADS1115";

#define ADS1115_I2C_PORT I2C_NUM_0
#define ADS1115_SCL_GPIO  18
#define ADS1115_SDA_GPIO  17
#define ADS1115_ADDR      0x48  // default address when ADDR tied to GND

// ADS1115 registers
#define ADS1115_REG_CONVERSION 0x00
#define ADS1115_REG_CONFIG     0x01

// Config bits (see datasheet)
#define ADS1115_OS_SINGLE      0x8000
#define ADS1115_MUX_AIN0_GND   0x4000  // AIN0 vs GND
#define ADS1115_PGA_4_096V     0x0200  // +/-4.096V range (adjust per AFE)
#define ADS1115_MODE_CONTINUOUS 0x0000 // continuous mode
#define ADS1115_MODE_SINGLE    0x0100  // single-shot mode
#define ADS1115_DR_860SPS      0x00E0  // 860 samples per second
#define ADS1115_COMP_DISABLE   0x0003

static float s_gain = 1.0f; // software scaling until hardware PGA available

esp_err_t ads1115_init(void) {
	i2c_config_t conf = {
		.mode = I2C_MODE_MASTER,
		.sda_io_num = ADS1115_SDA_GPIO,
		.sda_pullup_en = GPIO_PULLUP_ENABLE,
		.scl_io_num = ADS1115_SCL_GPIO,
		.scl_pullup_en = GPIO_PULLUP_ENABLE,
		.master.clk_speed = 400000,
		.clk_flags = 0,
	};
	ESP_ERROR_CHECK(i2c_param_config(ADS1115_I2C_PORT, &conf));
	ESP_ERROR_CHECK(i2c_driver_install(ADS1115_I2C_PORT, conf.mode, 0, 0, 0));

	// Configure ADS1115: continuous mode, AIN0 vs GND, 860 SPS
	uint16_t cfg = ADS1115_MUX_AIN0_GND | ADS1115_PGA_4_096V | ADS1115_MODE_CONTINUOUS | ADS1115_DR_860SPS | ADS1115_COMP_DISABLE;
	uint8_t buf[3];
	buf[0] = ADS1115_REG_CONFIG;
	buf[1] = (uint8_t)((cfg >> 8) & 0xFF);
	buf[2] = (uint8_t)(cfg & 0xFF);
	esp_err_t err = i2c_master_write_to_device(ADS1115_I2C_PORT, ADS1115_ADDR, buf, sizeof(buf), pdMS_TO_TICKS(100));
	if (err != ESP_OK) {
		ESP_LOGE(TAG, "ADS1115 write config failed: %d", err);
		return err;
	}
	ESP_LOGI(TAG, "ADS1115 configured for continuous 860 SPS on AIN0");
	return ESP_OK;
}

esp_err_t ads1115_read_sample(int16_t *out_raw) {
	if (!out_raw) return ESP_ERR_INVALID_ARG;
	uint8_t reg = ADS1115_REG_CONVERSION;
	uint8_t data[2] = {0};
	esp_err_t err = i2c_master_write_read_device(ADS1115_I2C_PORT, ADS1115_ADDR, &reg, 1, data, 2, pdMS_TO_TICKS(50));
	if (err != ESP_OK) {
		return err;
	}
	int16_t raw = (int16_t)((data[0] << 8) | data[1]);
	*out_raw = raw;
	return ESP_OK;
}

void ads1115_set_gain(float gain) { s_gain = gain; }

float ads1115_scale_to_volts(int16_t raw) {
	// With PGA +/-4.096V, LSB size is 125uV; adjust per actual AFE scaling.
	const float lsb = 4.096f / 32768.0f; // volts per count
	return (raw * lsb) * s_gain;
}
