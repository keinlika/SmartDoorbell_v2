# Hardware and Software Stack

## 1. Hardware Stack

### Raspberry Pi 3B+

The main edge-computing platform is a Raspberry Pi 3B+.

#### Why it was chosen

- inexpensive and widely available
- supports Python, OpenCV, FFmpeg, GPIO, and Linux networking
- practical for academic prototyping and live demos
- sufficient for moderate multimedia workloads if designed carefully

#### Tradeoffs

- limited CPU and RAM compared to newer Pi models
- cannot be treated like a high-end video-processing server
- requires careful tuning to balance preview responsiveness and recording quality

### Camera

The camera is accessed through `/dev/video0`.

#### Why it was chosen

- standard Linux video-device interface
- works with both OpenCV and FFmpeg through V4L2

#### Tradeoffs

- shared camera ownership is not always reliable
- camera hot-swap and initialization behavior must be handled carefully

### Microphone

The microphone is accessed through ALSA as `plughw:1,0`.

#### Why it was chosen

- standard Linux audio interface
- FFmpeg can capture from ALSA directly

#### Tradeoffs

- audio device naming may vary between systems
- requires environment-based configurability

### Motion Sensor

The motion sensor is connected through GPIO.

#### Why it was chosen

- low-cost event trigger
- simple way to demonstrate physical-world interaction
- allows event-driven recording without requiring AI-based vision detection

#### Tradeoffs

- can produce false positives depending on placement
- requires debounce-aware system design and recording lock protection

## 2. Software Stack

### Python

Python is used for both backend and device firmware.

#### Why it was chosen

- fast development speed
- strong support for FastAPI, OpenCV, FFmpeg orchestration, GPIO, and HTTP/WebSocket integrations
- practical for a senior project with multiple moving parts

#### Tradeoffs

- not the most efficient choice for all real-time media processing
- some runtime errors surface only under device conditions

### FastAPI

The backend framework is FastAPI.

#### Why it was chosen

- modern Python web framework
- easy route definition
- native support for async endpoints and WebSockets
- simple static file serving for a small product

#### Tradeoffs

- not a complete production deployment solution by itself
- needs surrounding infrastructure such as reverse proxy, HTTPS, and process management for public deployment

### Supabase

Supabase is used for:

- authentication
- database storage
- object storage

#### Why it was chosen

- consolidates several platform concerns into one service
- reduces custom backend code
- supports relational data and auth together
- practical for student-scale full-stack development

#### Tradeoffs

- current implementation depends on public file URLs for clips
- some frontend operations write directly through the JS client rather than only through backend-owned APIs
- stronger row-level security and hardened storage access would be needed for full production deployment

### OpenCV

OpenCV is used on the Raspberry Pi for live preview camera access and frame handling.

#### Why it was chosen

- easy access to V4L2 camera devices
- straightforward frame resizing and JPEG encoding
- appropriate for MJPEG preview generation

#### Tradeoffs

- not ideal for simultaneous high-quality preview and recording on constrained hardware
- contributes to the need for camera hot-swap logic

### FFmpeg

FFmpeg is used for actual clip recording.

#### Why it was chosen

- robust audio/video capture pipeline
- configurable codecs, frame rates, resolutions, and compression settings
- better suited than OpenCV alone for saved clip generation

#### Tradeoffs

- command-line orchestration is more complex
- CPU load must be tuned carefully on Raspberry Pi 3B+

### Flask

Flask is used on the device to serve the local MJPEG stream.

#### Why it was chosen

- lightweight and easy to embed into the firmware runtime
- sufficient for one simple stream endpoint

#### Tradeoffs

- adds another local server process within the device runtime model
- MJPEG streaming is simple but not as efficient as modern streaming protocols

### WebSockets

WebSockets provide real-time command and event relay between browser and device.

#### Why it was chosen

- fits manual recording triggers well
- keeps dashboard and device loosely coupled
- simpler than building a custom polling system for every action

#### Tradeoffs

- current relay model is simple and not horizontally scaled
- connection state management becomes more important as the number of devices grows

### Tailwind CSS and Plain JavaScript

The frontend is implemented as static HTML pages styled with Tailwind and controlled with vanilla JavaScript.

#### Why it was chosen

- fast to iterate
- easy to deploy
- avoids frontend build-chain complexity
- appropriate for a focused dashboard product

#### Tradeoffs

- large pages can become harder to maintain than a component-based application
- state management is manual rather than framework-driven

## 3. Supporting Libraries and Services

The current implementation also relies on:

- `python-dotenv` for environment configuration
- `requests` for device upload HTTP calls
- `websockets` for device real-time communication
- `RPi.GPIO` for sensor handling
- Supabase JS client in the browser

## 4. Stack Rationale

The overall stack is a pragmatic full-stack combination optimized for a senior project:

- simple enough to implement and explain
- modern enough to be credible
- powerful enough to demonstrate account-scoped cloud-connected hardware

The stack is not the absolute highest-performance combination possible, but it is appropriate for the educational and product goals of the project.
