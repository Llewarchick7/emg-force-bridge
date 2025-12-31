/*
task_acq.c 
EMG acquisition task using ADS1115 ADC over I2C
*/




#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_log.h"
#include "esp_timer.h"
#include <stdint.h>

// ADS1115 driver API declarations
esp_err_t ads1115_init(void);
esp_err_t ads1115_read_sample(int16_t *out_raw);
void      ads1115_set_gain(float gain);
float     ads1115_scale_to_volts(int16_t raw);

// 
static const char *TAG = "task_acq";

typedef struct {
	int64_t ts_us; // timestamp in microseconds
	int16_t raw; // raw ADC sample
	float   volts; // scaled voltage
} emg_sample_t;

// Declare Queue to hold EMG samples (emg_sample_t data)
static QueueHandle_t s_emg_queue; 

QueueHandle_t emg_get_queue(void) { return s_emg_queue; }

static void emg_acq_task(void *arg) {
	/*
	Description:
		EMG acquisition task using ADS1115 ADC over I2C
	Parameters:
		arg: Task argument (unused)
	Returns:
		None
	*/
	(void)arg;
	ads1115_set_gain(1.0f);
	if (ads1115_init() != ESP_OK) {
		ESP_LOGE(TAG, "ADS1115 init failed");
		vTaskDelete(NULL);
		return;
	}
	// ADS1115 in continuous mode ~860 SPS; loop reads as fast as possible
	while (1) { 
		int16_t raw;
		if (ads1115_read_sample(&raw) == ESP_OK) {
			emg_sample_t s;
			s.ts_us = esp_timer_get_time(); // assign timestamp
			s.raw = raw; // assign raw ADC value
			s.volts = ads1115_scale_to_volts(raw); // assign scaled voltage
			if (s_emg_queue) {
				(void)xQueueSend(s_emg_queue, &s, 0);
			}
		}
		// Small delay to yield; ADS1115 updates at ~1.16ms intervals (860 SPS)
		vTaskDelay(pdMS_TO_TICKS(1));
	}
}

void emg_acq_start(void) {
	/*
	Description:
		Start the EMG acquisition task and create the queue for EMG samples
	
	*/
	if (!s_emg_queue) {
		s_emg_queue = xQueueCreate(256, sizeof(emg_sample_t));
	}
	xTaskCreate(emg_acq_task, "emg_acq", 4096, NULL, 5, NULL);
}
