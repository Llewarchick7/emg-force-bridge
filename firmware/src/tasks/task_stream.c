#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include <stdint.h>

// From acquisition
typedef struct {
	int64_t ts_us;
	int16_t raw;
	float   volts;
} emg_sample_t;

QueueHandle_t emg_get_queue(void);

// UART transport
void uart_tx_init(void);
void uart_tx_printf(const char *fmt, ...);

static void emg_stream_task(void *arg) {
	(void)arg;
	uart_tx_init();
	uart_tx_printf("time_us,adc,volts\r\n");
	emg_sample_t s;
	QueueHandle_t q = emg_get_queue();
	while (1) {
		if (q && xQueueReceive(q, &s, portMAX_DELAY) == pdTRUE) {
			uart_tx_printf("%lld,%d,%.6f\r\n", (long long)s.ts_us, (int)s.raw, (double)s.volts);
		}
	}
}

void emg_stream_start(void) {
	xTaskCreate(emg_stream_task, "emg_stream", 4096, NULL, 5, NULL);
}
