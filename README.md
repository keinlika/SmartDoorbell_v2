# SmartDoorbell v2

SmartDoorbell v2 is an IoT smart security doorbell system built using a Raspberry Pi.

The system captures video and audio events when motion is detected and streams or uploads them to a backend service.

## Architecture

SmartDoorbell_v2 contains two main components:

### device_firmware
Runs on the Raspberry Pi and handles:
- motion detection
- camera capture
- audio recording
- sending events to the backend

### cloud_backend
Handles:
- device registration
- event processing
- user authentication (planned)
- dashboard interface

## Technologies

- Python
- Raspberry Pi
- FastAPI
- WebSockets
- OpenCV / FFmpeg

## Project Structure

SmartDoorbell_v2
│
├── cloud_backend
│ └── FastAPI server and dashboard
│
├── device_firmware
│ └── Raspberry Pi camera + sensor logic
│
└── README.md


## Status

Prototype development.

Future improvements:
- secure login system
- event notifications
- mobile integration
- improved video pipeline

## Author

Kein Lika

