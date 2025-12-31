// Stream processed packets out over UART as CSV
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include <stdint.h>

// From processing
typedef struct {
	int64_t ts_us;
	int16_t raw;
	float   volts;
	float   bp;     // band-pass filtered volts
	float   rect;   // |bp|
	float   env;    // low-pass envelope of rect
	float   rms;    // sliding RMS (energy metric)
	int     active; // thresholded activation (with hysteresis)
	float   snr;    // simple signal quality estimate
} emg_packet_t;

QueueHandle_t emg_get_proc_queue(void);

// UART transport
void uart_tx_init(void);
void uart_tx_printf(const char *fmt, ...);

static void emg_stream_task(void *arg) {
	(void)arg;
	uart_tx_init();
	uart_tx_printf("time_us,adc,volts,bp,rect,env,rms,active,snr\r\n");
	emg_packet_t p;
	QueueHandle_t q = emg_get_proc_queue();
	while (1) {
		if (q && xQueueReceive(q, &p, portMAX_DELAY) == pdTRUE) {
			uart_tx_printf("%lld,%d,%.6f,%.6f,%.6f,%.6f,%d,%.3f\r\n",
				(long long)p.ts_us, (int)p.raw, (double)p.volts,
				(double)p.bp, (double)p.rect, (double)p.env,
				(double)p.rms, (int)p.active, (double)p.snr);
		}
	}
}

void emg_stream_start(void) {
	xTaskCreate(emg_stream_task, "emg_stream", 4096, NULL, 5, NULL);
}
