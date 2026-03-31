# Wiring

| Signal            | From            | To                | Notes             |
|-------------------|-----------------|-------------------|-------------------|
| Camera PIR OUT    | Camera          | Pi GPIO17         | primary trigger   |
| UART-B TX/RX      | MCU-A PA9/PA10  | Pi UART (/dev/ttyAMA0) | 115200 8N1  |
| UART-A TX/RX      | MCU-A PA2/PA3   | MCU-B PB11/PB10   | 115200 8N1       |
| LED               | MCU-B PB3       | LED               | active-high       |
| Relay/Buzzer      | MCU-B PB8/PB9   | Actuator driver   |                   |
