# UART Protocol v1.0

**Frame**
```
0xAA | Ver | MsgID | Len(2) | Seq | Payload[Len] | CRC16(2)
```
- Ver: 0x01
- CRC16: CCITT-FALSE over Ver..Payload.

**Msg IDs**
- 0x01 HELLO
- 0x02 ACK
- 0x10 SENSOR_EVENT
- 0x11 HEARTBEAT
- 0x12 CAMERA_EVENT
- 0x20 ACTUATE
- 0x30 CONFIG_SET
- 0x31 CONFIG_GET
- 0x40 CAMERA_TRIGGER
- 0x41 CAMERA_STATUS
- 0x42 CLIP_META

**CAMERA_EVENT payload**
```
uint8  state    // 1 start, 0 end
uint32 ts_ms
uint8  src      // 0 Pi GPIO, 1 MCU-A GPIO, 2 webhook
```
