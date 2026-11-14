#include "app.h"
#include "adxl_sampling_task.h"
#include "processing_task.h"

QueueHandle_t empty_sample_queue;
QueueHandle_t full_sample_queue;

void app_init(void)
{
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
}
