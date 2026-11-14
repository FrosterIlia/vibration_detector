#ifndef PROCESSING_TASK_H
#define PROCESSING_TASK_H

#include "FreeRTOS.h"
#include "task.h"
#include "main.h"
#include "cmsis_os.h"
#include "usart.h"

#include "adxl_sampling_task.h"
#include "driver_adxl345.h"
#include "driver_adxl345_interface.h"
#include "main.h"
#include "portmacro.h"
#include "projdefs.h"
#include "stm32f767xx.h"
#include "stm32f7xx_hal_gpio.h"
#include <stdio.h>

extern TaskHandle_t processing_task_handler;

void processing_task(void *argument);

#endif