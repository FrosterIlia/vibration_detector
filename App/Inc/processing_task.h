#ifndef PROCESSING_TASK_H
#define PROCESSING_TASK_H

#include "FreeRTOS.h"
#include "task.h"
#include "main.h"
#include "cmsis_os.h"
#include "usart.h"
#include "queue.h"

#include "adxl_sampling_task.h"
#include "driver_adxl345.h"
#include "driver_adxl345_interface.h"
#include "main.h"
#include "portmacro.h"
#include "projdefs.h"
#include "stm32f767xx.h"
#include "stm32f7xx_hal_gpio.h"
#include <stdio.h>

#include "arm_math.h"

#define N_BLOCKS 4
#define BLOCK_SAMPLES 2048

extern TaskHandle_t processing_task_handler;

extern arm_rfft_fast_instance_f32 fft;

typedef struct {
    int16_t  x[BLOCK_SAMPLES], y[BLOCK_SAMPLES], z[BLOCK_SAMPLES];
} sample_block_t;                      // ~12 KB

extern sample_block_t pool[N_BLOCKS];

extern QueueHandle_t empty_sample_queue;
extern QueueHandle_t full_sample_queue; 

void processing_task(void *argument);

void process_block(uint8_t block_index);

#endif