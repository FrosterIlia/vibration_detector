#include "processing_task.h"
#include "arm_math_types.h"
#include "dsp/statistics_functions.h"
#include "main.h"
#include "portmacro.h"
#include "projdefs.h"
#include "stm32f7xx_hal_gpio.h"
#include <string.h>

TaskHandle_t processing_task_handler;

sample_block_t pool[N_BLOCKS];

static arm_rfft_fast_instance_f32 fft;
static float32_t hann[N_FFT];
static float32_t hann_power; // sum of hann[i]^2, needed for scaling
static float32_t fft_input[AXIS_NUMBER]
                          [N_FFT]; // FFT input (gets destroyed by the FFT)
static float32_t fft_output[AXIS_NUMBER][N_FFT]; // FFT output
static float32_t psd_sums[AXIS_NUMBER][N_BINS];  // running totals, one per axis
static uint32_t n_segments;

void processing_task(void *argument)
{
	processing_init();

	uint8_t current_block_index, prev_block_index;

	// We need to have a previous block initialized before we can start
	// processing
	if (xQueueReceive(full_sample_queue, &prev_block_index, portMAX_DELAY) !=
	    pdTRUE)
	{
		UART_PRINT("ERR: full queue receive failed\r\n");
	}

	for (;;)
	{
		if (xQueueReceive(full_sample_queue, &current_block_index,
		                  portMAX_DELAY) != pdTRUE)
		{
			UART_PRINT("ERR: full queue receive failed\r\n");
		}
		process_block(current_block_index, prev_block_index);
		xQueueSend(empty_sample_queue, &prev_block_index, 0);
		prev_block_index = current_block_index;
	}
}

void process_block(uint8_t current_block_index, uint8_t prev_block_index)
{
	UART_PRINT("processing");

	for (uint16_t i = 0; i < BLOCK_SAMPLES; i++)
	{
		fft_input[0][i] = pool[prev_block_index].x[i];
		fft_input[0][i + BLOCK_SAMPLES] = pool[current_block_index].x[i];

		fft_input[1][i] = pool[prev_block_index].y[i];
		fft_input[1][i + BLOCK_SAMPLES] = pool[current_block_index].y[i];

		fft_input[2][i] = pool[prev_block_index].z[i];
		fft_input[2][i + BLOCK_SAMPLES] = pool[current_block_index].z[i];
	}

	// Normalize the values. Removes gravity and other shit
	float32_t mean[AXIS_NUMBER];
	arm_mean_f32(fft_input[0], N_FFT, &mean[0]);
	arm_mean_f32(fft_input[1], N_FFT, &mean[1]);
	arm_mean_f32(fft_input[2], N_FFT, &mean[2]);

	arm_offset_f32(fft_input[0], -mean[0], fft_input[0], N_FFT);
	arm_offset_f32(fft_input[1], -mean[1], fft_input[1], N_FFT);
	arm_offset_f32(fft_input[2], -mean[2], fft_input[2], N_FFT);

	arm_mult_f32(fft_input[0], hann, fft_input[0], N_FFT);
	arm_mult_f32(fft_input[1], hann, fft_input[1], N_FFT);
	arm_mult_f32(fft_input[2], hann, fft_input[2], N_FFT);

	arm_rfft_fast_f32(&fft, fft_input[0], fft_output[0], 0);
	arm_rfft_fast_f32(&fft, fft_input[1], fft_output[1], 0);
	arm_rfft_fast_f32(&fft, fft_input[2], fft_output[2], 0);

	for (uint8_t axis = 0; axis < AXIS_NUMBER; axis++)
	{
		// The RFFT packs the real-only DC and Nyquist bins into the first pair
		psd_sums[axis][0] += fft_output[axis][0] * fft_output[axis][0]; // 0 Hz
		psd_sums[axis][N_FFT / 2] +=
		    fft_output[axis][1] * fft_output[axis][1]; // 1600 Hz
		for (uint32_t k = 1; k < N_FFT / 2; k++)
		{
			float32_t re = fft_output[axis][2 * k];
			float32_t im = fft_output[axis][2 * k + 1];
			psd_sums[axis][k] += re * re + im * im;
		}
	}
	++n_segments;
}

void processing_init(void)
{
	if (arm_rfft_fast_init_f32(&fft, N_FFT) != ARM_MATH_SUCCESS)
	{
		UART_PRINT("FFT Engine failed to initialize");
	}

	hann_power = 0.0f;
	for (uint32_t i = 0; i < N_FFT; i++)
	{
		hann[i] = 0.5f * (1.0f - cosf(2.0f * PI * i / N_FFT));
		hann_power += hann[i] * hann[i];
	}
}

bool psd_finalize(float32_t out[3][N_BINS], float32_t sampling_freq)
{
	if (n_segments == 0)
		return false;
	float32_t scale = 1.0f / (sampling_freq * hann_power * n_segments);
	for (int axis = 0; axis < AXIS_NUMBER; axis++)
	{
		for (uint32_t k = 0; k < N_BINS; k++)
		{
			float32_t v = psd_sums[axis][k] * scale;
			if (k != 0 && k != N_FFT / 2)
				v *= 2.0f; // one-sided
			out[axis][k] = v;
		}
	}
	return true;
}