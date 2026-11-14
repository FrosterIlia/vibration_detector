#include "adxl_sampling_task.h"
#include "driver_adxl345.h"
#include "driver_adxl345_interface.h"
#include "main.h"
#include "portmacro.h"
#include "projdefs.h"
#include "stm32f767xx.h"
#include "stm32f7xx_hal_gpio.h"
#include <stdio.h>

TaskHandle_t adxl_sampling_task_handler;

void adxl_sampling_task(void *argument)
{
  adxl345_handle_t adxl_handle;
  int16_t raw[32][3];
  float g[32][3];
  uint16_t len = 16;
  char msg[64];

  DRIVER_ADXL345_LINK_INIT(&adxl_handle, adxl345_handle_t);
  DRIVER_ADXL345_LINK_IIC_INIT(&adxl_handle, adxl345_interface_iic_init);
  DRIVER_ADXL345_LINK_IIC_DEINIT(&adxl_handle, adxl345_interface_iic_deinit);
  DRIVER_ADXL345_LINK_IIC_READ(&adxl_handle, adxl345_interface_iic_read);
  DRIVER_ADXL345_LINK_IIC_WRITE(&adxl_handle, adxl345_interface_iic_write);
  DRIVER_ADXL345_LINK_SPI_INIT(&adxl_handle, adxl345_interface_spi_init);
  DRIVER_ADXL345_LINK_SPI_DEINIT(&adxl_handle, adxl345_interface_spi_deinit);
  DRIVER_ADXL345_LINK_SPI_READ(&adxl_handle, adxl345_interface_spi_read);
  DRIVER_ADXL345_LINK_SPI_WRITE(&adxl_handle, adxl345_interface_spi_write);
  DRIVER_ADXL345_LINK_DELAY_MS(&adxl_handle, adxl345_interface_delay_ms);
  DRIVER_ADXL345_LINK_DEBUG_PRINT(&adxl_handle, adxl345_interface_debug_print);
  DRIVER_ADXL345_LINK_RECEIVE_CALLBACK(&adxl_handle,
                                       adxl345_interface_receive_callback);

  adxl345_set_interface(&adxl_handle, ADXL345_INTERFACE_SPI);
  if (adxl345_init(&adxl_handle) != 0)
  {
    vTaskDelete(NULL);
  }
  adxl345_set_spi_wire(&adxl_handle, ADXL345_SPI_WIRE_4);
  adxl345_set_rate(&adxl_handle, ADXL345_RATE_3200);
  adxl345_set_range(&adxl_handle, ADXL345_RANGE_4G);
  adxl345_set_full_resolution(&adxl_handle, ADXL345_BOOL_TRUE);
  adxl345_set_justify(&adxl_handle, ADXL345_JUSTIFY_RIGHT);
  adxl345_set_measure(&adxl_handle,
                      ADXL345_BOOL_FALSE); // standby while configuring
  adxl345_set_mode(&adxl_handle,
                   ADXL345_MODE_BYPASS); // flushes FIFO -> INT1 drops
  adxl345_set_mode(&adxl_handle, ADXL345_MODE_STREAM);
  adxl345_set_watermark(&adxl_handle, ACCEL_WATERMARK_LEVEL);
  adxl345_set_interrupt_map(&adxl_handle, ADXL345_INTERRUPT_WATERMARK,
                            ADXL345_INTERRUPT_PIN1);
  adxl345_set_interrupt_active_level(&adxl_handle,
                                     ADXL345_INTERRUPT_ACTIVE_LEVEL_HIGH);
  adxl345_set_interrupt(&adxl_handle, ADXL345_INTERRUPT_WATERMARK,
                        ADXL345_BOOL_TRUE);
  adxl345_set_measure(&adxl_handle, ADXL345_BOOL_TRUE);

  for (;;)
  {
    HAL_GPIO_TogglePin(GPIOB, LD1_Pin);
    ulTaskNotifyTake(pdTRUE, portMAX_DELAY);

    len = 32;
    if (adxl345_read(&adxl_handle, raw, g, &len) == 0)
    {
      int n = snprintf(msg, sizeof(msg), "%u samples, x=%d y=%d z=%d mg\r\n",
                       len, (int)(g[0][0] * 1000), (int)(g[0][1] * 1000),
                       (int)(g[0][2] * 1000));
      HAL_UART_Transmit(&huart3, (const uint8_t *)msg, n, 100);
    }
  }
}

void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
  if (GPIO_Pin == ACCEL_INT1_PIN_Pin)
  {
    BaseType_t woken = pdFALSE;
    vTaskNotifyGiveFromISR(adxl_sampling_task_handler, &woken);
    portYIELD_FROM_ISR(woken);
  }
}