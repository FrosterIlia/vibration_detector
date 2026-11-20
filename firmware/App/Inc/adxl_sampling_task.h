#ifndef ADXL_SAMPLING_TASK_H
#define ADXL_SAMPLING_TASK_H

#include "FreeRTOS.h"
#include "task.h"
#include "main.h"
#include "cmsis_os.h"
#include "usart.h"

#include "adxl_sampling_task.h"
#include "pi_comm_task.h"
#include "driver_adxl345.h"
#include "driver_adxl345_interface.h"
#include "main.h"
#include "portmacro.h"
#include "projdefs.h"
#include "stm32f767xx.h"
#include "stm32f7xx_hal_gpio.h"
#include <stdio.h>

#define ACCEL_WATERMARK_LEVEL 16
#define SAMPLING_RATE 3200
#define CAPTURE_MAX (SAMPLING_RATE * 10)

extern TaskHandle_t adxl_sampling_task_handler;

extern int16_t capture_buf[CAPTURE_MAX][3];
extern uint32_t capture_count;

void adxl_sampling_task(void *argument);

#endif