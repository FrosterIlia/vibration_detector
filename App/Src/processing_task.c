#include "processing_task.h"
#include "main.h"
#include "portmacro.h"
#include "projdefs.h"
#include "stm32f7xx_hal_gpio.h"

TaskHandle_t processing_task_handler;

sample_block_t pool[N_BLOCKS];

void processing_task(void *argument)
{
	for (;;)
	{
		uint8_t current_block_index;
		if (xQueueReceive(full_sample_queue, &current_block_index, portMAX_DELAY) != pdTRUE)
		{
			UART_PRINT("ERR: full queue receive failed\r\n");
		}
		process_block(current_block_index);
		xQueueSend(empty_sample_queue, &current_block_index, 0);
	}
}

void process_block(uint8_t block_index)
{
	HAL_GPIO_TogglePin(GPIOB, LD1_Pin);
}