#include "adxl_sampling_task.h"
#include "driver_adxl345_interface.h"
#include <stdio.h>

void adxl_sampling_task(void *argument)
{
  adxl345_handle_t adxl;
  int16_t raw[32][3];
  float g[32][3];
  uint16_t len;
  char msg[64];

  /* connect the driver to our interface functions */
  DRIVER_ADXL345_LINK_INIT(&adxl, adxl345_handle_t);
  DRIVER_ADXL345_LINK_IIC_INIT(&adxl, adxl345_interface_iic_init);
  DRIVER_ADXL345_LINK_IIC_DEINIT(&adxl, adxl345_interface_iic_deinit);
  DRIVER_ADXL345_LINK_IIC_READ(&adxl, adxl345_interface_iic_read);
  DRIVER_ADXL345_LINK_IIC_WRITE(&adxl, adxl345_interface_iic_write);
  DRIVER_ADXL345_LINK_SPI_INIT(&adxl, adxl345_interface_spi_init);
  DRIVER_ADXL345_LINK_SPI_DEINIT(&adxl, adxl345_interface_spi_deinit);
  DRIVER_ADXL345_LINK_SPI_READ(&adxl, adxl345_interface_spi_read);
  DRIVER_ADXL345_LINK_SPI_WRITE(&adxl, adxl345_interface_spi_write);
  DRIVER_ADXL345_LINK_DELAY_MS(&adxl, adxl345_interface_delay_ms);
  DRIVER_ADXL345_LINK_DEBUG_PRINT(&adxl, adxl345_interface_debug_print);
  DRIVER_ADXL345_LINK_RECEIVE_CALLBACK(&adxl, adxl345_interface_receive_callback);

  /* configure the sensor (in standby), then start measuring */
  adxl345_set_interface(&adxl, ADXL345_INTERFACE_SPI);
  if (adxl345_init(&adxl) != 0)
  {
    vTaskDelete(NULL);
  }
  adxl345_set_spi_wire(&adxl, ADXL345_SPI_WIRE_4);
  adxl345_set_rate(&adxl, ADXL345_RATE_3200);
  adxl345_set_range(&adxl, ADXL345_RANGE_4G);
  adxl345_set_full_resolution(&adxl, ADXL345_BOOL_TRUE);
  adxl345_set_justify(&adxl, ADXL345_JUSTIFY_RIGHT);
  adxl345_set_mode(&adxl, ADXL345_MODE_STREAM);
  adxl345_set_watermark(&adxl, 16);
  adxl345_set_interrupt_map(&adxl, ADXL345_INTERRUPT_WATERMARK, ADXL345_INTERRUPT_PIN1);
  adxl345_set_interrupt_active_level(&adxl, ADXL345_INTERRUPT_ACTIVE_LEVEL_HIGH);
  adxl345_set_interrupt(&adxl, ADXL345_INTERRUPT_WATERMARK, ADXL345_BOOL_TRUE);
  adxl345_set_measure(&adxl, ADXL345_BOOL_TRUE);

  for(;;)
  {
    len = 32;
    if (adxl345_read(&adxl, raw, g, &len) == 0)
    {
      int n = snprintf(msg, sizeof(msg), "%u samples, x=%d y=%d z=%d mg\r\n", len,
                       (int)(g[0][0] * 1000), (int)(g[0][1] * 1000), (int)(g[0][2] * 1000));
      HAL_UART_Transmit(&huart3, (const uint8_t *)msg, n, 100);
    }
    HAL_GPIO_TogglePin(GPIOB, LD1_Pin);
    vTaskDelay(pdMS_TO_TICKS(100));
  }
}
