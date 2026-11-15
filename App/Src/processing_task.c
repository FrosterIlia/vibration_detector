#include "processing_task.h"
#include "main.h"
#include "portmacro.h"
#include "projdefs.h"
#include "stm32f7xx_hal_gpio.h"

TaskHandle_t processing_task_handler;

sample_block_t pool[N_BLOCKS];

arm_rfft_fast_instance_f32 fft;

void processing_task(void *argument)
{

	if (arm_rfft_fast_init_f32(&fft, 4096) != ARM_MATH_SUCCESS)
	{
		UART_PRINT("FFT Engine failed to initialize");
	}

	for (;;)
	{
		uint8_t current_block_index;
		if (xQueueReceive(full_sample_queue, &current_block_index,
		                  portMAX_DELAY) != pdTRUE)
		{
			UART_PRINT("ERR: full queue receive failed\r\n");
		}
		process_block(current_block_index);
		xQueueSend(empty_sample_queue, &current_block_index, 0);
	}
}

void process_block(uint8_t block_index)
{
	UART_PRINT("processing");
	HAL_GPIO_TogglePin(GPIOB, LD1_Pin);
}