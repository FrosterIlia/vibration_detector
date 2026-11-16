#include "app.h"
#include "FreeRTOS.h"
#include "adxl_sampling_task.h"
#include "pi_comm_task.h"
#include "processing_task.h"
#include "stm32f7xx_hal_uart.h"
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

QueueHandle_t empty_sample_queue;
QueueHandle_t full_sample_queue;
SemaphoreHandle_t log_mutex;

void app_init(void)
{
	// Created first so it exists before any task can log
	log_mutex = xSemaphoreCreateMutex();

	// These queues store indexes of the blocks inside the pool
	empty_sample_queue = xQueueCreate(N_BLOCKS, sizeof(uint8_t));
	full_sample_queue = xQueueCreate(N_BLOCKS, sizeof(uint8_t));

	for (uint8_t i = 0; i < N_BLOCKS; i++)
	{
		xQueueSend(empty_sample_queue, &i, 0);
	}

	xTaskCreate(adxl_sampling_task, "SamplingTask", 1024, NULL,
	            tskIDLE_PRIORITY + 5, &adxl_sampling_task_handler);
	xTaskCreate(processing_task, "ProcessingTask", 1024, NULL,
	            tskIDLE_PRIORITY + 2, &processing_task_handler);
	xTaskCreate(pi_comm_task, "PiCommTask", 1024, NULL, tskIDLE_PRIORITY + 1,
	            &pi_comm_task_handler);
}

int __io_putchar(int ch)
{
	HAL_UART_Transmit(&huart3, (uint8_t *)&ch, 1, HAL_MAX_DELAY);
	return ch;
}

void log_printf(const char *fmt, ...)
{
	// Skip locking if the mutex hasn't been created yet (e.g. very early boot)
	bool locked = false;
	if (log_mutex != NULL)
	{
		xSemaphoreTake(log_mutex, portMAX_DELAY);
		locked = true;
	}

	va_list args;
	va_start(args, fmt);

	printf("[%lu] ", (unsigned long)xTaskGetTickCount());
	vprintf(fmt, args);
	printf("\r\n");

	va_end(args);

	if (locked)
	{
		xSemaphoreGive(log_mutex);
	}
}
