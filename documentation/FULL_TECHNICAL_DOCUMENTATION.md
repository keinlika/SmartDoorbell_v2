# Full Technical Documentation

## 1. Repository Walkthrough

The current repository is centered around three active implementation areas:

- [`cloud_backend/app/main.py`](/home/phreaks4security/SmartDoorbell_v2/cloud_backend/app/main.py)
- [`cloud_backend/app/static/index.html`](/home/phreaks4security/SmartDoorbell_v2/cloud_backend/app/static/index.html)
- [`cloud_backend/app/static/login.html`](/home/phreaks4security/SmartDoorbell_v2/cloud_backend/app/static/login.html)
- [`device_firmware/doorbell_connect.py`](/home/phreaks4security/SmartDoorbell_v2/device_firmware/doorbell_connect.py)

There are also support scripts:

- [`cloud_backend/register_device.py`](/home/phreaks4security/SmartDoorbell_v2/cloud_backend/register_device.py)
- [`cloud_backend/test_login.py`](/home/phreaks4security/SmartDoorbell_v2/cloud_backend/test_login.py)
- [`device_firmware/doorbell_connect_production.py`](/home/phreaks4security/SmartDoorbell_v2/device_firmware/doorbell_connect_production.py)

The documentation below explains the system as a complete implementation rather than just a list of files.

## 2. Backend Implementation

## 2.1 Backend Startup and Configuration

The backend uses FastAPI and loads configuration from `.env` values with `python-dotenv`.

Important backend settings include:

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_BUCKET_NAME`
- `DEFAULT_DEVICE_ID`
- `ALLOWED_ORIGINS`
- `DEVICE_AUTH_MODE`
- `DEVICE_TOKEN_MAP`

The backend also sets:

- a clip retention policy through `CLIP_RETENTION_DAYS`
- a Supabase storage bucket name
- CORS settings for local development and dashboard access

## 2.2 Authentication Helpers

The backend does not implement its own password system. Instead, it uses Supabase Auth for account creation and sign-in, then validates browser bearer tokens server-side.

The key helper is effectively:

- extract bearer token from `Authorization`
- call `supabase.auth.get_user(token)`
- treat the returned user as the authenticated principal

This ensures backend APIs remain account-aware even though the login UI runs in the browser.

## 2.3 Device Access Resolution

The backend resolves which devices a user can access by reading:

- owned devices from the `devices` table
- viewer/shared relationships from `device_members`

This is important because the system is not built around one global test device. The same account may access multiple devices, and a device may be shared with another user.

## 2.4 Device Authentication Modes

The firmware is treated differently from browser users. Device requests can be evaluated in three modes:

- `off`
- `shadow`
- `enforce`

The default is `shadow`, which allows legacy behavior while logging failures and missing data. This is useful during development but weaker than strict enforcement.

The device can identify itself with headers such as:

- `X-Device-ID`
- `X-Device-Token`

Those values are checked against:

- a `devices.device_token` column if available
- or a fallback `DEVICE_TOKEN_MAP` environment mapping

## 2.5 API Routes

### `GET /`

Serves the dashboard page.

### `GET /login.html`

Serves the polished login page. This is the canonical login route.

### `GET /login`

Redirects to `/login.html`.

### `GET /static/login.html`

Redirects to `/login.html` so logout and old links do not land on a legacy path.

### `GET /healthz`

Lightweight health-check endpoint.

### `POST /upload`

Accepts a file upload from the device. The route:

1. validates device context
2. uploads the file to Supabase Storage
3. creates an `events` table row
4. returns upload metadata

This is the core ingestion route for recordings.

### `POST /api/pair-device`

Pairs a hardware device to the authenticated user through a pairing code. It sets the device owner and ensures an owner membership row exists.

### `GET /api/device-access`

Returns the devices the user can access and the user’s role on each one.

### `GET /api/events`

Returns event history, optionally scoped to a specific device.

### `GET /api/dashboard-summary`

Returns summary metrics such as:

- number of accessible devices
- online devices
- clip count
- clips today
- last event time
- storage usage
- retention policy days

### `DELETE /api/events/{event_id}`

Deletes an event and its associated storage object. This is currently owner-only.

### `GET /api/status`

Returns a global device status style response. It exists, but it is not the main user-scoped dashboard source.

## 2.6 WebSocket Behavior

The backend uses one WebSocket endpoint at `/ws`.

### Device session behavior

The device sends a message with action `device_auth`. The backend tracks that WebSocket as belonging to a specific device ID.

### Browser session behavior

The browser keeps a socket open to receive updates and send commands.

### Manual recording behavior

When the browser sends `manual_record`, the backend forwards that message only to the matching device connection when a device ID is present.

### General message relay

If a device sends JSON messages, the backend forwards them to other clients and injects the known device ID into the payload when needed.

This simple relay approach is adequate for a senior project and keeps the real-time model understandable.

## 2.7 Clip Retention Cleanup

The backend includes a cleanup coroutine that removes event records older than the configured retention window and attempts to delete associated files from Supabase Storage.

This is important because it shows operational thinking beyond just “store everything forever.”

## 3. Frontend Implementation

## 3.1 Dashboard Page

The dashboard is a single static HTML page enhanced with Tailwind classes and inline JavaScript. It is not a React application. This matters because it demonstrates a simpler deployment model and lower frontend complexity.

The dashboard handles:

- session verification
- theme management
- device loading
- summary loading
- history loading
- WebSocket connection
- pairing
- viewer invitation
- deletion
- logout

## 3.2 Session Handling in the Browser

The frontend uses the Supabase JavaScript client with browser session storage. When the page loads, it checks for a current session. If none exists, it redirects to `/login.html`.

Authenticated API calls send the bearer token in the `Authorization` header.

## 3.3 Theme Logic

Both the dashboard and login page use the same `localStorage.theme` model. This means:

- theme choice persists across pages
- dark or light mode remains consistent after login or logout
- the experience feels like one product rather than two disconnected pages

## 3.4 Device Selector and Access Rendering

The dashboard requests `/api/device-access`, then renders:

- a device selector
- device cards
- access role indicators

The active device determines which history and summary data are loaded.

## 3.5 Pairing Workflow

The pairing form posts to `/api/pair-device` with the user’s bearer token. On success, the page reloads device state and updates the UI.

## 3.6 Live Preview

The dashboard live preview is intentionally simple. It points an image element to the device’s MJPEG stream at port `8001`. This is a pragmatic tradeoff:

- simple to implement
- low frontend complexity
- no cloud streaming service required

The limitation is that this is not yet a full remote multi-device media relay architecture.

## 3.7 Recent Captures and Featured Viewer

The dashboard presents:

- a featured viewer for the selected clip
- a queue/list of recent captures
- deletion controls
- empty states for no activity

This creates a more product-grade review experience than simply dumping raw links.

## 3.8 Authentication Page

The login page provides both sign-in and account creation in one polished auth shell.

### Sign-in flow

- validates email and password
- calls `signInWithPassword`
- redirects to the dashboard on success

### Sign-up flow

- validates email, password, and confirm password
- calls `signUp`
- upserts a profile when appropriate
- if email confirmation is required, shows a success message and returns the user to sign-in mode

## 4. Firmware Implementation

## 4.1 Device Runtime Model

The firmware is a long-running Python process that combines:

- camera management
- Flask streaming
- GPIO monitoring
- FFmpeg recording
- HTTP upload
- WebSocket control
- local retry logic

This is a practical edge-runtime design for a Raspberry Pi.

## 4.2 Environment Loading

The firmware loads `.env` values from:

- `device_firmware/.env`
- repository root `.env`
- `~/.env`

This makes deployment flexible on the device.

## 4.3 Camera Initialization

The firmware uses OpenCV to initialize the camera and tries to configure preview settings such as:

- capture width and height
- frame rate
- MJPEG fourcc when available
- buffer size

It attempts multiple initialization retries because camera readiness can be inconsistent on embedded hardware.

## 4.4 MJPEG Preview Serving

Flask serves `/stream` by repeatedly:

1. reading a frame from OpenCV
2. resizing it to preview output dimensions
3. encoding it as JPEG
4. yielding it as a multipart MJPEG response

This is intentionally separate from recording because it favors a responsive dashboard preview without permanently running a more expensive recording stack.

## 4.5 Recording Flow

Recording is managed by a `VideoManager` class and an `asyncio.Lock` so that overlapping recordings are prevented.

The sequence is:

1. set recording state
2. release OpenCV camera
3. wait briefly to let the device node settle
4. start FFmpeg with camera and microphone inputs
5. wait for FFmpeg to finish
6. validate the output file
7. reinitialize OpenCV

This is the core of the hot-swap architecture.

## 4.6 Recording Quality Configuration

The current implementation exposes recording settings through environment variables. Defaults are tuned toward Raspberry Pi 3B+ stability:

- `1280x720`
- `24 fps`
- `libx264`
- `superfast`
- `CRF 21`
- mono AAC audio at `96k`

Preview quality is intentionally lower than recording quality.

## 4.7 Motion Sensor Handling

GPIO is configured in BCM mode and monitored continuously. When motion is detected, the firmware starts a motion-triggered recording task, subject to the recording lock so that duplicate simultaneous captures do not overlap.

## 4.8 WebSocket Control Loop

The firmware reconnects to the backend WebSocket in a loop. On connection it sends a device-auth payload. It then listens for messages such as `manual_record`.

This design makes the device resilient to temporary backend restarts or network interruptions.

## 4.9 Upload and Retry Behavior

After a clip is recorded, the firmware attempts upload immediately. If upload fails:

- the file is moved or retained in a local spool directory
- a retry task periodically attempts to send pending MP4 files again

This is a major step beyond a fragile single-attempt prototype.

## 5. Support Scripts

## 5.1 `register_device.py`

This script helps register or update the device record in Supabase. It:

- derives or reads the device ID
- optionally generates a token
- writes device metadata
- prints the effective token

This is useful for setup and pairing preparation.

## 5.2 `test_login.py`

This is a rough manual test script, not a formal automated test suite. It currently appears outdated because it targets a route that is not part of the current backend implementation.

That is worth acknowledging in a senior-project defense because it shows honest awareness of the project’s testing maturity.

## 6. Current Architecture Decisions

The most important architecture decisions visible in the code are:

### Use FastAPI plus Supabase instead of a custom auth/database stack

This reduces backend complexity while still providing a serious account model.

### Use static HTML and JavaScript instead of a heavier frontend framework

This simplifies deployment and keeps the UI easy to reason about for a senior project.

### Use hot-swap camera ownership instead of a single always-on multi-role media pipeline

This prioritizes reliability on Raspberry Pi 3B+.

### Use local retry spooling on the device

This acknowledges real network failure modes.

### Use account-scoped device access

This makes the system behave more like a real product and less like a classroom demo.

## 7. Complete System Explanation

As a complete system, Sentio works like this:

- a user creates an account or signs in
- the user pairs a hardware doorbell to their account
- the dashboard loads that user’s accessible devices
- the Raspberry Pi streams a lightweight preview and stays connected by WebSocket
- motion or manual record requests trigger a higher-quality FFmpeg recording
- the clip uploads to the backend and is written to storage and database tables
- the dashboard fetches and displays those clips in a polished review interface
- owners can manage devices, view history, and delete stored events

This is a full-stack smart-home workflow built from the repository’s actual implementation.
