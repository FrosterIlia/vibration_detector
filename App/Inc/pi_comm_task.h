#ifndef PI_COMM_TASK_H
#define PI_COMM_TASK_H

#include <stdbool.h>
#include <stdint.h>

#include "FreeRTOS.h"        // must come before any other FreeRTOS header
#include "task.h"
#include "queue.h"

#include "main.h"            // pulls in stm32f7xx_hal.h (HAL_StatusTypeDef etc.)
#include "usart.h"           // huart6, UART_HandleTypeDef

#include <stdbool.h>
#include <stdint.h>

typedef enum {
	IDLE,	// start recording with accelerometer
	MEASURING,	// stop recording with accelerometer
	REPORTING,
} sys_state;

extern TaskHandle_t pi_comm_task_handler;

void pi_comm_task(void *argument); // UART transmission with PI

void Uart_Init (void);

// Sends len bytes over USART6 in the background (interrupt driven).
// data must stay valid until the transfer finishes, e.g. a string literal.
HAL_StatusTypeDef Uart_Send(const void *data, uint16_t len);

sys_state get_sys_state(void);

#endif
