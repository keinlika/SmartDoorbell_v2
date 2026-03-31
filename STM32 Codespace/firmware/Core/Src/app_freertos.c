#include "cmsis_os.h"
#include "app_config.h"
#include <string.h>

extern UART_HandleTypeDef huart2; // adjust if different

static void vTaskDoorbell(void *arg);
static void vTaskPIR(void *arg);
static void vTaskHeartbeat(void *arg);

static void send_event(const char *evt){
  HAL_UART_Transmit(&huart2,(uint8_t*)evt,strlen(evt),100);
  const char nl='\n'; HAL_UART_Transmit(&huart2,(uint8_t*)&nl,1,50);
}

void MX_FREERTOS_Init(void) {
  xTaskCreate(vTaskDoorbell, "door", 256, NULL, osPriorityAboveNormal, NULL);
  xTaskCreate(vTaskPIR,       "pir",  256, NULL, osPriorityNormal,     NULL);
  xTaskCreate(vTaskHeartbeat, "hb",   128, NULL, osPriorityLow,        NULL);
}

static void vTaskDoorbell(void *arg){
  uint32_t t_last=0;
  GPIO_InitTypeDef g={0};
  g.Pin=PIN_BTN_PIN; g.Mode=GPIO_MODE_INPUT; g.Pull=GPIO_PULLUP;
  HAL_GPIO_Init(PIN_BTN_GPIO,&g);
  for(;;){
    if(HAL_GPIO_ReadPin(PIN_BTN_GPIO,PIN_BTN_PIN)==GPIO_PIN_RESET){
      uint32_t now=xTaskGetTickCount();
      if((now-t_last) > pdMS_TO_TICKS(DEBOUNCE_MS)){
        send_event("doorbell_pressed");
        t_last=now;
      }
      vTaskDelay(pdMS_TO_TICKS(30));
    } else vTaskDelay(pdMS_TO_TICKS(10));
  }
}

static void vTaskPIR(void *arg){
  uint8_t latched=0; uint32_t last=0;
  GPIO_InitTypeDef g={0};
  g.Pin=PIN_PIR_PIN; g.Mode=GPIO_MODE_INPUT; g.Pull=GPIO_NOPULL;
  HAL_GPIO_Init(PIN_PIR_GPIO,&g);
  for(;;){
    GPIO_PinState s=HAL_GPIO_ReadPin(PIN_PIR_GPIO,PIN_PIR_PIN);
    if(s==GPIO_PIN_SET && (!latched || (xTaskGetTickCount()-last)>pdMS_TO_TICKS(PIR_COOLDOWN_MS))){
      send_event("motion_detected");
      latched=1; last=xTaskGetTickCount();
    }
    if((xTaskGetTickCount()-last)>pdMS_TO_TICKS(PIR_COOLDOWN_MS)) latched=0;
    vTaskDelay(pdMS_TO_TICKS(50));
  }
}

static void vTaskHeartbeat(void *arg){
  GPIO_InitTypeDef g={0};
  g.Pin=PIN_LED_PIN; g.Mode=GPIO_MODE_OUTPUT_PP; g.Pull=GPIO_NOPULL; g.Speed=GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(PIN_LED_GPIO,&g);
  for(;;){
    HAL_GPIO_TogglePin(PIN_LED_GPIO,PIN_LED_PIN);
    vTaskDelay(pdMS_TO_TICKS(500));
  }
}
