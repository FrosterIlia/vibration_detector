#ifndef APP_H
#define APP_H

#include "stm32f7xx_hal.h"
#include "main.h"
#include "cmsis_os.h"
#include "usart.h"
#include "gpio.h"
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "semphr.h"

#include "../../Lib/adxl345/src/driver_adxl345.h"

#include "adxl_sampling_task.h"



void app_init();

extern SemaphoreHandle_t log_mutex;

// Thread-safe printf to UART3, prefixed with the tick count and ending in
// "\r\n". Must not be called from an ISR.
void log_printf(const char *fmt, ...) __attribute__((format(printf, 1, 2)));


#endif