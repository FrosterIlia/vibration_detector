#include "processing_task.h"
#include "main.h"
#include "projdefs.h"
#include "stm32f7xx_hal_gpio.h"

TaskHandle_t processing_task_handler;

void processing_task(void *argument)
{
  for (;;)
  {
    HAL_GPIO_TogglePin(GPIOB, LD1_Pin);
	vTaskDelay(pdMS_TO_TICKS(100));
  }
}