#ifndef APP_H
#define APP_H

#include "stm32f7xx_hal.h"
#include "main.h"
#include "cmsis_os.h"
#include "usart.h"
#include "gpio.h"
#include "FreeRTOS.h"
#include "task.h"

#include "../../Lib/adxl345/src/driver_adxl345.h"

#include "adxl_sampling_task.h"



void app_init();



#endif