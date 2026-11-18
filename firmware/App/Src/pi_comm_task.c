#include "pi_comm_task.h"

#include "cmsis_os.h"
#include "portmacro.h"
#include "processing_task.h" // N_BINS, AXIS_NUMBER, float32_t
#include "app.h"             // log_printf
#include "projdefs.h"
#include "stm32f7xx_hal_def.h"
#include "stm32f7xx_hal_uart.h"
#include "usart.h"

#include <string.h>

#define Q_REC (xQueueReceive(rxQueue, &rec_byte, pdMS_TO_TICKS(2000)) == pdTRUE)
#define Q_REC_MAX xQueueReceive(rxQueue, &rec_byte, portMAX_DELAY)
#define SEND_ACK Uart_Send(&ACK, 1)
#define SEND_NACK Uart_Send(&NACK, 1)

// COMM COMMANDS
const uint8_t START = 'S';
const uint8_t STOP = 'P';
const uint8_t REQ_LEN = 'L';
const uint8_t REQ_PSD = 'D';
const uint8_t CLEAR = 'C';
const uint8_t ACK = 'A';
const uint8_t NACK = 'N';

TaskHandle_t pi_comm_task_handler;

static volatile sys_state state = IDLE; // only access with a getter in other files

static QueueHandle_t rxQueue; // bytes received from the Pi (filled by the ISR)
static uint8_t rx_byte;       // HAL writes each received byte here


//NOTE - ADD MUTEXES (NO MUTEXES ON UART YET)
void pi_comm_task(void *argument)
{
	Uart_Init();

	uint8_t rec_byte;
	for (;;)
	{
		// receive UART from PI
		Q_REC_MAX;

		switch (state)
		{
		case IDLE:
			if (rec_byte == START) 
			{
				xEventGroupSetBits(sys_events, EVT_RUN);
				state = MEASURING;
				SEND_ACK;
			}
			else SEND_NACK;
			
			break;
		case MEASURING:
			//Block Until PI says to stop
			// receive UART from PI

			if (rec_byte == STOP)
			{
				SEND_ACK;
				xEventGroupSetBits(sys_events, EVT_STOP);	//clear event group
				
				//wait for data to to transfer set to max for now, but
				xEventGroupWaitBits(sys_events, EVT_DATA, pdTRUE, pdTRUE, portMAX_DELAY); 
				state = REPORTING;
			}	
			else SEND_NACK;
						
			break;
		case REPORTING:
			size_t psd_size = get_size_psd();
			if (rec_byte == REQ_LEN)
			{
				Uart_Send(&psd_size, (uint32_t)sizeof(psd_size));	//send length
			}	
			else if (rec_byte == REQ_PSD)
			{
				Uart_Send(&psd_out, psd_size);	//send PSD
			}
			else if (rec_byte == CLEAR)
			{
				SEND_ACK;
				xEventGroupClearBits(sys_events, EVT_STOP);	 //clear stop flag
				xEventGroupSetBits(sys_events, EVT_CLEAR);
	
				state = IDLE;
			}
			else SEND_NACK;
			
		break;
		}
	}
}


void Uart_Init(void)
{
	rxQueue = xQueueCreate(256, sizeof(uint8_t));
	//configASSERT(rxQueue); // NULL = FreeRTOS heap is full (raise configTOTAL_HEAP_SIZE)
	// Receive one byte by interrupt into rx_byte. HAL_UART_RxCpltCallback
	// queues it and re-arms for the next one.
	HAL_UART_Receive_IT(&huart6, &rx_byte, 1);
}

// ISR from USART 6 -- adds to rxQueue
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
	if (huart == &huart6)
	{
		BaseType_t woken = pdFALSE;
		xQueueSendFromISR(rxQueue, &rx_byte,
		                  &woken); // if the queue is full, the byte is dropped
		HAL_UART_Receive_IT(&huart6, &rx_byte, 1); // re-arm for the next byte	"how many bytes should i collect before calls RxCplt"
		portYIELD_FROM_ISR(woken);
	}
}

// tells task that transmit is done
void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart)
{
	if (huart == &huart6)
	{
		BaseType_t woken = pdFALSE;
		vTaskNotifyGiveFromISR(pi_comm_task_handler, &woken);
		portYIELD_FROM_ISR(woken);
	}
}

//what to do on error
void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
	if (huart == &huart6)
	{
		HAL_UART_Receive_IT(&huart6, &rx_byte, 1);	//Re-arm
	}
}

// Starts Transmit interrupt, blocks until transmit is do
HAL_StatusTypeDef Uart_Send(const void *data, uint16_t len)
{
	//timeout calculations (with buffer)
	uint32_t tx_MS = ((uint32_t)len * 10 * 1000) / huart6.Init.BaudRate; //theoretical tx time in MS
	TickType_t timeout = tx_MS * 2 + 10; // +10 accounts for transfers < 1 ms

	ulTaskNotifyTake(pdTRUE,0); // clears stale "transmit done" signals

	HAL_StatusTypeDef status = HAL_UART_Transmit_IT(&huart6, (const uint8_t *)data, len);
	if (status == HAL_OK)
	{
		if (ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(timeout)) == 0) // if fails
		{
			HAL_UART_AbortTransmit_IT(&huart6);
			status = HAL_TIMEOUT; 
		}
	}
	return status;
}

sys_state get_sys_state(void)
{
	return state;
}

