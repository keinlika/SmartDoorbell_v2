# System Architecture

## 1. Architecture Summary

The project is a three-layer smart doorbell architecture:

1. **Device layer** on a Raspberry Pi
2. **Cloud/backend layer** using FastAPI and Supabase
3. **Web application layer** served as static frontend pages by the backend

At a high level:

- the Raspberry Pi captures live video and local hardware events
- the backend coordinates uploads, metadata, account ownership, and real-time signaling
- Supabase stores users, device relationships, event records, and uploaded media
- the dashboard lets a signed-in user pair devices, monitor status, trigger recording, and review history

## 2. Main Components

### 2.1 Raspberry Pi Device Firmware

The device firmware is implemented in [`device_firmware/doorbell_connect.py`](/home/phreaks4security/SmartDoorbell_v2/device_firmware/doorbell_connect.py).

Its responsibilities are:

- initialize and manage the CSI (Camera Serial Interface)/video camera at `/dev/video0`
- initialize and read the GPIO motion sensor
- capture microphone input from ALSA `plughw:1,0`
- serve an MJPEG live preview stream over Flask on port `8001`
- connect to the backend WebSocket channel
- react to motion events and manual-record commands
- temporarily release camera access, record a clip with FFmpeg, then restore preview
- upload clips to the backend
- spool failed uploads locally and retry later

### 2.2 Backend

The backend is implemented in [`cloud_backend/app/main.py`](/home/phreaks4security/SmartDoorbell_v2/cloud_backend/app/main.py) using FastAPI.

Its responsibilities are:

- serve the dashboard and login pages
- validate browser sessions using Supabase Auth tokens
- accept clip uploads from the device
- write event metadata to Supabase
- provide device, event, and summary APIs to the dashboard
- support a device pairing flow
- relay real-time WebSocket messages between device and browser
- enforce account scoping for devices and clips
- run retention cleanup for old clips

### 2.3 Supabase

Supabase is used as the cloud data platform. In the current implementation it provides:

- user authentication
- relational data storage
- object storage for uploaded MP4 clips

The backend and frontend both rely on Supabase:

- the backend uses the Python client for token validation, data access, and storage operations
- the frontend uses the Supabase JavaScript client for login, signup, session handling, and some direct membership/profile operations

### 2.4 Frontend Dashboard

The dashboard is served from [`cloud_backend/app/static/index.html`](/home/phreaks4security/SmartDoorbell_v2/cloud_backend/app/static/index.html).

Its responsibilities are:

- session-aware dashboard rendering
- theme persistence
- device selection and management views
- pairing and viewer invitation UI
- live stream display
- manual recording trigger
- event history and featured viewer
- storage and retention summary display
- logout and session-failure recovery

### 2.5 Authentication UI

The login and account-creation flow is served from [`cloud_backend/app/static/login.html`](/home/phreaks4security/SmartDoorbell_v2/cloud_backend/app/static/login.html).

It provides:

- sign in
- create account
- confirm password on sign-up
- inline validation
- success and error feedback
- light/dark theme persistence matching the dashboard

## 3. Hardware Architecture

The hardware platform is a Raspberry Pi 3B+ connected to:

- a camera device exposed as `/dev/video0`
- a microphone exposed through ALSA as `plughw:1,0`
- a GPIO motion sensor

This choice creates a constrained-compute environment. The architecture therefore prioritizes recording reliability over continuous multi-purpose video processing.

## 4. Camera Ownership Model

### 4.1 Current Hot-Swap Design

The current design uses a **hot-swap camera ownership model**:

- OpenCV owns the camera during live preview
- the firmware serves MJPEG frames over Flask for the dashboard
- when recording is triggered, preview pauses and releases the camera
- FFmpeg then takes exclusive control of the camera and microphone for the recording session
- after recording completes, the firmware reinitializes OpenCV and restores preview

### 4.2 Why This Architecture Was Chosen

This design fits the project priorities on Raspberry Pi 3B+:

1. recording reliability
2. better saved clip quality
3. acceptable preview quality
4. reasonable CPU usage
5. lower implementation risk

The system avoids more complex always-on dual pipelines that would increase steady-state CPU load and make camera access less predictable on limited hardware.

## 5. Data Flow

## 5.1 Login and Dashboard Access

1. User opens `/login.html`.
2. Frontend authenticates with Supabase Auth.
3. Frontend stores session in browser storage through the Supabase JS client.
4. On dashboard load, the browser includes the access token in API requests to the backend.
5. The backend validates the bearer token by calling `supabase.auth.get_user(token)`.
6. The backend resolves which devices and events the user is allowed to access.

## 5.2 Device Pairing Flow

1. A device exists in the `devices` table with a pairing code.
2. The signed-in user submits the pairing code from the dashboard.
3. The backend finds the device row and confirms that it is not already claimed by another owner.
4. The backend updates the device to assign `owner_id`, `user_id`, and `is_claimed=true`.
5. The backend also inserts an owner membership row into `device_members` if needed.
6. The dashboard reloads the user’s accessible device set.

## 5.3 Live Preview Flow

1. The Raspberry Pi firmware serves MJPEG at `http://<device-host>:8001/stream`.
2. The dashboard displays that stream in an `<img>` tag.
3. The browser treats the stream as an MJPEG image source and refreshes frames continuously.

This is lightweight and simple, but it ties live preview to a device-accessible stream endpoint rather than cloud-relayed video.

## 5.4 Manual Recording Flow

1. A signed-in user clicks **Record Clip** in the dashboard.
2. The frontend sends a WebSocket message with `{"action":"manual_record","device_id":...}`.
3. The backend relays that command to the matching device WebSocket connection.
4. The firmware receives the command, acquires a recording lock, and starts the record flow.
5. The preview camera is released.
6. FFmpeg records a clip with video and audio.
7. The clip is uploaded to the backend.
8. The backend stores the file in Supabase Storage and inserts an `events` row.
9. The dashboard refreshes event history and viewer state.

## 5.5 Motion Recording Flow

1. The motion sensor changes GPIO state.
2. The firmware’s sensor listener detects motion.
3. If no recording is already running, the firmware starts a recording task.
4. The same hot-swap recording pipeline runs as in manual capture.
5. The uploaded clip is categorized as a motion event and appears in event history.

## 5.6 Upload and Event Persistence Flow

1. The firmware posts a multipart file to `/upload`.
2. The backend validates device identity according to its device-auth mode.
3. The backend uploads the bytes to Supabase Storage.
4. The backend receives a public URL for the file.
5. The backend writes an `events` row with:
   - device ID
   - user ID
   - event type
   - video URL
   - file size
6. The frontend later fetches those events through `/api/events`.

## 6. Control Flow

### 6.1 Browser to Backend

The browser controls the system by:

- calling REST APIs for pairing, history, summaries, and deletion
- maintaining a WebSocket connection for device events and manual recording commands

### 6.2 Backend to Device

The backend sends commands or relays messages over the `/ws` WebSocket endpoint. The most important control message is the manual-record request.

### 6.3 Device to Backend

The device reports:

- authentication information for the WebSocket session
- recording start or completion events
- uploaded clip files
- status-style events relayed over WebSocket

## 7. Real-Time Communication Flow

Real-time communication uses one shared WebSocket route: `/ws`.

### Browser behavior

- connects to `/ws`
- sends manual recording messages
- listens for events to update logs and history

### Device behavior

- connects to `/ws`
- authenticates with `device_auth`
- receives `manual_record` commands
- may send recording-related event payloads

### Backend behavior

- maintains connected client list
- tracks which WebSocket connections correspond to devices
- relays browser commands to the correct device
- forwards device-originated messages to other connected clients

## 8. Ownership and Access Model

The project uses an account-scoped device model rather than a global shared-device list.

### Main entities

- **users**: Supabase-authenticated accounts
- **devices**: hardware doorbell units
- **device_members**: access relationships between users and devices
- **events**: uploaded clip metadata

### Access levels

- owner
- viewer

### Why this matters

This prevents one user from seeing another user’s clips simply because they know the dashboard URL. Device ownership and membership scoping are central to making the system behave like a real product rather than a demo feed.

## 9. Recording, Uploading, and Viewing Pipeline

The end-to-end media pipeline is:

1. Preview via MJPEG in Flask
2. Recording via FFmpeg
3. File upload to FastAPI
4. Storage in Supabase bucket
5. Event record creation in Supabase database
6. Event retrieval by authenticated dashboard
7. Playback through the featured viewer or capture list

## 10. Architectural Tradeoffs

### Strengths

- practical for Raspberry Pi 3B+
- clear separation of responsibilities
- account-scoped cloud-backed design
- manageable complexity for a senior project
- real-time control without requiring a full signaling platform

### Constraints

- live preview is not cloud-relayed and is not a full multi-device streaming architecture
- public storage URLs require stronger hardening for public deployment
- the WebSocket relay is simple and not horizontally scaled
- browser-side direct Supabase writes for some device-member operations are convenient but less controlled than a pure backend-owned API model

## 11. Architectural Conclusion

The system is best understood as an edge-to-cloud smart-home product architecture optimized for reliable event capture on constrained hardware. Its most important design choice is the hot-swap ownership model for the camera, which prioritizes stable recording on Raspberry Pi 3B+ while still preserving an acceptable live dashboard preview.
