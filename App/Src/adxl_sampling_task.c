#include "adxl_sampling_task.h"

void adxl_sampling_task(void *argument)
{

  for(;;)
  {
    HAL_UART_Transmit(&huart3, (const uint8_t *)"hello\n", 6, 100);
    HAL_GPIO_TogglePin(GPIOB, LD1_Pin);
    osDelay(1000);
  }
}