#include "app.h"
#include "adxl_sampling_task.h"
#include "processing_task.h"

void app_init(void)
{
    xTaskCreate(adxl_sampling_task, "SamplingTask", 1024, NULL, tskIDLE_PRIORITY + 5, &adxl_sampling_task_handler);
	xTaskCreate(processing_task, "ProcessingTask", 1024, NULL, tskIDLE_PRIORITY + 2, &processing_task_handler);
}
