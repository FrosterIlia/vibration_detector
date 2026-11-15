#ifndef PI_COMM_TASK_H
#define PI_COMM_TASK_H

#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "main.h"
#include "cmsis_os.h"
#include "usart.h"

#include <stdbool.h>
#include <stdint.h>

extern TaskHandle_t pi_comm_task_handler;

void pi_comm_task(void *argument); // UART transmission with PI

#endif
