// UART transport for CSV frames (ESP32-IDF)
#include "driver/uart.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include <stdarg.h>
#include <stdio.h>

static const char *TAG = "uart_tx";

#define UART_NUM       UART_NUM_0
#define UART_TX_PIN    43  // adjust for your board
#define UART_RX_PIN    44
#define UART_BAUDRATE  115200

void uart_tx_init(void) {
	uart_config_t cfg = {
		.baud_rate = UART_BAUDRATE,
		.data_bits = UART_DATA_8_BITS,
		.parity    = UART_PARITY_DISABLE,
		.stop_bits = UART_STOP_BITS_1,
		.flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
		.source_clk = UART_SCLK_DEFAULT,
	};
	ESP_ERROR_CHECK(uart_driver_install(UART_NUM, 1024, 0, 0, NULL, 0));
	ESP_ERROR_CHECK(uart_param_config(UART_NUM, &cfg));
	ESP_ERROR_CHECK(uart_set_pin(UART_NUM, UART_TX_PIN, UART_RX_PIN, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
	ESP_LOGI(TAG, "UART initialized @ %d baud", UART_BAUDRATE);
}

static void _uart_write_str(const char *s) {
	if (!s) return;
	(void)uart_write_bytes(UART_NUM, s, (int)strlen(s));
}

void uart_tx_printf(const char *fmt, ...) {
	static char buf[256];
	va_list ap;
	va_start(ap, fmt);
	int n = vsnprintf(buf, sizeof(buf), fmt, ap);
	va_end(ap);
	if (n > 0) {
		_uart_write_str(buf);
	}
}
