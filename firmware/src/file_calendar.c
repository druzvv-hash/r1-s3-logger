#include "file_calendar.h"
#include "session_file.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
static portMUX_TYPE lock=portMUX_INITIALIZER_UNLOCKED;
static TaskHandle_t owner;
static uint32_t calendar;
void gll_file_calendar_begin(uint64_t us){portENTER_CRITICAL(&lock);owner=xTaskGetCurrentTaskHandle();calendar=gll_fattime(us);portEXIT_CRITICAL(&lock);}
void gll_file_calendar_end(void){portENTER_CRITICAL(&lock);if(owner==xTaskGetCurrentTaskHandle())owner=NULL;portEXIT_CRITICAL(&lock);}
extern uint32_t __real_get_fattime(void);
uint32_t __wrap_get_fattime(void){portENTER_CRITICAL(&lock);uint32_t t=owner==xTaskGetCurrentTaskHandle()?calendar:0;portEXIT_CRITICAL(&lock);return t?t:__real_get_fattime();}
