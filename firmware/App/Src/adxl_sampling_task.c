#include "app.h"
#include "adxl_sampling_task.h"
#include "portmacro.h"
#include "processing_task.h"
#include "projdefs.h"

TaskHandle_t adxl_sampling_task_handler;

int16_t capture_buf[CAPTURE_MAX][3];
uint32_t capture_count;

void adxl_sampling_task(void *argument)
{
	adxl345_handle_t adxl_handle;
	int16_t raw[32][3];
	float g[32][3];
	uint16_t len = 16;

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
	DRIVER_ADXL345_LINK_DEBUG_PRINT(&adxl_handle,
	                                adxl345_interface_debug_print);
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

	uint8_t current_block_index;
	uint16_t sample_index = 0;
	if (xQueueReceive(empty_sample_queue, &current_block_index, 0) != pdPASS)
	{
		log_printf("ERR: no empty block at start");
	}


	bool was_running = false;
	bool was_capturing = false;

	for (;;)
	{
		ulTaskNotifyTake(pdTRUE, portMAX_DELAY);

		EventBits_t bits = xEventGroupGetBits(sys_events);
		bool running = (bits & EVT_RUN) != 0; //was the event group triggered
		bool capturing = (bits & EVT_CAPTURE) != 0;

		if (running && !was_running)
		{
			sample_index = 0;
		}
		was_running = running;

		if (!capturing && was_capturing)
		{
			xEventGroupSetBits(sys_events, EVT_CAPTURE_DONE);
		}
		was_capturing = capturing;

		len = 32;
		if (adxl345_read(&adxl_handle, raw, g, &len) == 0)
		{
			if (capturing)
			{
				for (uint8_t i = 0; i < len && capture_count < CAPTURE_MAX; i++)
				{
					capture_buf[capture_count][0] = (int16_t)(g[i][0] * 1000);
					capture_buf[capture_count][1] = (int16_t)(g[i][1] * 1000);
					capture_buf[capture_count][2] = (int16_t)(g[i][2] * 1000);
					capture_count++;
				}
			}

			if (!running)	//ignore buffer code if Event group isnt set
				continue;
			for (uint8_t i = 0; i < len; i++)
			{
				pool[current_block_index].x[sample_index] = (int)(g[i][0] * 1000);
				pool[current_block_index].y[sample_index] = (int)(g[i][1] * 1000);
				pool[current_block_index].z[sample_index] = (int)(g[i][2] * 1000);
				++sample_index;

				if (sample_index == BLOCK_SAMPLES)
				{
					if (xQueueSend(full_sample_queue, &current_block_index, 0) !=
					    pdTRUE)
					{
						log_printf("ERR: full queue send failed");
					}
					if (xQueueReceive(empty_sample_queue, &current_block_index,
					                  0) != pdPASS)
					{
						log_printf("ERR: no empty block available");
					}
					sample_index = 0;
				}
			}
		}
		else
		{
			log_printf("Reading accelerometer failed");
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
