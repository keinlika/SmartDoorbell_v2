
#pragma once
#include "stm32f4xx_hal.h"

#define PIN_PIR_GPIO      GPIOA
#define PIN_PIR_PIN       GPIO_PIN_1
#define PIN_BTN_GPIO      GPIOA
#define PIN_BTN_PIN       GPIO_PIN_2
#define PIN_LED_GPIO      GPIOB
#define PIN_LED_PIN       GPIO_PIN_3

#define DEBOUNCE_MS 40
#define PIR_COOLDOWN_MS 2000
