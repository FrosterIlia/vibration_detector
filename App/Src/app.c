#include "app.h"
#include "adxl_sampling_task.h"

void app_init(void)
{
    TaskHandle_t adxl_sampling_task_handler;
    xTaskCreate(adxl_sampling_task, "SamplingTask", 1024, NULL, tskIDLE_PRIORITY + 1, &adxl_sampling_task_handler);
}
