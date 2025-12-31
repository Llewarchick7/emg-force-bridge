// On-device EMG processing task
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_log.h"
#include <math.h>

// Source queue from acquisition
typedef struct {
	int64_t ts_us;
	int16_t raw;
	float   volts;
} emg_sample_t;
QueueHandle_t emg_get_queue(void);

// Processed packet sent downstream (to stream task)
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

static QueueHandle_t s_proc_queue;
QueueHandle_t emg_get_proc_queue(void) { return s_proc_queue; }

static const char *TAG = "task_proc";

// Simple one-pole low-pass filter helper
typedef struct { float y; float alpha; } lp1_t;
static inline void lp1_init(lp1_t *f, float alpha) { f->y = 0.0f; f->alpha = alpha; }
static inline float lp1_step(lp1_t *f, float x) {
	f->y += f->alpha * (x - f->y);
	return f->y;
}

// Compute alpha from cutoff and sample rate: alpha = 1 - exp(-2*pi*fc/fs)
static inline float lp1_alpha(float fc, float fs) {
	const float PI = 3.14159265358979323846f;
	float a = 1.0f - expf(-2.0f * PI * fc / fs);
	// Clamp to [0,1] with clear guarding to satisfy -Werror=misleading-indentation
	if (a < 0.0f) {
		a = 0.0f;
	}
	if (a > 1.0f) {
		a = 1.0f;
	}
	return a;
}

// BiQuad filter (Direct Form I) for band-pass (e.g., 20-450 Hz)
typedef struct { float b0,b1,b2,a1,a2; float x1,x2,y1,y2; } biquad_t;
static inline void bq_init(biquad_t *q, float b0,float b1,float b2,float a1,float a2){
	q->b0=b0; q->b1=b1; q->b2=b2; q->a1=a1; q->a2=a2; q->x1=0; q->x2=0; q->y1=0; q->y2=0;
}
static inline float bq_step(biquad_t *q, float x){
	float y = q->b0*x + q->b1*q->x1 + q->b2*q->x2 - q->a1*q->y1 - q->a2*q->y2;
	q->x2 = q->x1; q->x1 = x; q->y2 = q->y1; q->y1 = y; return y;
}

// Precomputed Butterworth band-pass (Fs=860Hz, ~20-450Hz), two cascaded biquads.
// Coefficients generated offline; normalized a0=1.
static void bp_coeffs_860_20_450(biquad_t *s1, biquad_t *s2){
	// Section 1
	bq_init(s1, 0.243134f, 0.0f, -0.243134f, -0.226877f, 0.513732f);
	// Section 2
	bq_init(s2, 0.513732f, 0.0f, -0.513732f, -0.289264f, 0.672538f);
}

// Sliding RMS via windowed sum of squares
typedef struct { float *buf; int cap; int idx; int count; float sumsq; } rms_win_t;
static inline void rms_init(rms_win_t *w, float *storage, int n){ w->buf=storage; w->cap=n; w->idx=0; w->count=0; w->sumsq=0.0f; }
static inline float rms_step(rms_win_t *w, float x){
	float x2 = x*x;
	if (w->count < w->cap){ w->buf[w->idx++] = x2; w->sumsq += x2; w->count++; if (w->idx==w->cap) w->idx=0; }
	else { float old = w->buf[w->idx]; w->buf[w->idx] = x2; w->sumsq += x2 - old; w->idx++; if (w->idx==w->cap) w->idx=0; }
	return sqrtf(w->sumsq / (float)w->count);
}

static void emg_proc_task(void *arg) {
	(void)arg;
	// Assumed ADS1115 data rate
	const float fs = 860.0f;
	const float fc_env = 5.0f; // 5 Hz envelope LPF
	lp1_t env; lp1_init(&env, lp1_alpha(fc_env, fs));

	// Band-pass filter setup
	biquad_t bp1, bp2; bp_coeffs_860_20_450(&bp1, &bp2);

	// RMS window ~100 ms → n ≈ 86 samples
	enum { RMS_N = 86 };
	static float rms_storage[RMS_N];
	rms_win_t rms; rms_init(&rms, rms_storage, RMS_N);

	// Thresholds with hysteresis (envelope units, volts). Tune per patient.
	float thresh_on  = 0.050f; // 50 mV
	float thresh_off = 0.030f; // 30 mV
	int active = 0;

	// Simple SNR estimate: env / (baseline LP of rect)
	lp1_t baseline; lp1_init(&baseline, lp1_alpha(1.0f, fs));

	QueueHandle_t src = emg_get_queue();
	if (!src) {
		ESP_LOGE(TAG, "acq queue not ready");
		vTaskDelete(NULL);
		return;
	}

	emg_sample_t s;
	while (1) {
		if (xQueueReceive(src, &s, portMAX_DELAY) == pdTRUE) {
			emg_packet_t p;
			p.ts_us = s.ts_us;
			p.raw   = s.raw;
			p.volts = s.volts;
			// Band-pass
			float bp = bq_step(&bp1, s.volts);
			bp = bq_step(&bp2, bp);
			p.bp = bp;
			// Rectify and envelope
			p.rect  = bp >= 0.0f ? bp : -bp;
			p.env   = lp1_step(&env, p.rect);
			// RMS of band-passed signal
			p.rms   = rms_step(&rms, bp);
			// Hysteresis activation
			if (!active && p.env >= thresh_on) active = 1;
			else if (active && p.env <= thresh_off) active = 0;
			p.active = active;
			// Simple SNR proxy
			float base = lp1_step(&baseline, p.rect);
			p.snr = (base > 1e-6f) ? (p.env / base) : 0.0f;
			if (s_proc_queue) {
				(void)xQueueSend(s_proc_queue, &p, 0);
			}
		}
	}
}

void emg_proc_start(void) {
	if (!s_proc_queue) {
		s_proc_queue = xQueueCreate(256, sizeof(emg_packet_t));
	}
	xTaskCreate(emg_proc_task, "emg_proc", 4096, NULL, 5, NULL);
}
