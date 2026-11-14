#ifndef ADXL_SAMPLING_TASK_H
#define ADXL_SAMPLING_TASK_H

#include "FreeRTOS.h"
#include "task.h"
#include "main.h"
#include "cmsis_os.h"
#include "usart.h"

#define ACCEL_WATERMARK_LEVEL 16


extern TaskHandle_t adxl_sampling_task_handler;

void adxl_sampling_task(void *argument);

#endif