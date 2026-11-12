#ifndef ADXL_SAMPLING_TASK_H
#define ADXL_SAMPLING_TASK_H

#include "FreeRTOS.h"
#include "task.h"
#include "main.h"
#include "cmsis_os.h"
#include "usart.h"

void adxl_sampling_task(void *argument);

#endif