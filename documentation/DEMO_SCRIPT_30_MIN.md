# 30-Minute Demo Script

## Demo Goal

The goal of the demo is to show that Sentio is a complete smart doorbell system, not just a camera feed or a backend API. The professor should leave with a clear understanding of:

- what the product does
- how the hardware, backend, cloud, and UI work together
- why the architecture choices were made
- what tradeoffs were accepted

## Demo Structure Overview

### Minutes 0-3: Project framing

**What to say**

“Sentio is a smart doorbell system built as a full-stack senior project. It uses a Raspberry Pi device for sensing and media capture, a FastAPI backend for coordination, Supabase for authentication and storage, and a browser dashboard for monitoring and review. My goal was not only to detect motion or record video, but to build a product-like system with user accounts, device ownership, and real workflows.”

**What to show**

- repository structure
- high-level architecture slide or diagram

### Minutes 3-7: System architecture explanation

**What to say**

“The system has three main layers. The Raspberry Pi handles the camera, microphone, and motion sensor. The backend handles uploads, account-scoped APIs, and real-time messaging. Supabase provides auth, database, and storage. The browser dashboard sits on top of that and gives the user access to pairing, live preview, recording, and history.”

**What to show**

- architecture diagram
- key files:
  - `device_firmware/doorbell_connect.py`
  - `cloud_backend/app/main.py`
  - `cloud_backend/app/static/index.html`
  - `cloud_backend/app/static/login.html`

### Minutes 7-10: Authentication and product entry

**What to say**

“Users authenticate with Supabase Auth. I kept one canonical login route and designed the auth UI to match the dashboard so it feels like one product. Sign-up includes confirm-password validation, and account state determines which devices and clips are visible.”

**What to show**

- login page
- theme toggle
- create-account mode
- password mismatch validation
- successful sign-in

### Minutes 10-14: Dashboard walkthrough

**What to say**

“Once logged in, the user lands on the dashboard. This page shows device access, live preview, storage usage, retention policy, recent captures, and management actions. The design goal was to make it feel like a product workspace rather than a raw engineering tool.”

**What to show**

- header and device selector
- storage summary
- pairing area
- recent captures
- featured viewer

### Minutes 14-18: Device pairing and ownership

**What to say**

“Pairing is important because this is an account-scoped system. A user claims a device by pairing code, and the backend assigns ownership in the database. This matters for privacy and access control, since event history is filtered by device ownership and membership.”

**What to show**

- pairing form
- result of pairing
- device appearing in selector

### Minutes 18-23: Live preview and recording

**What to say**

“On the Raspberry Pi, I used a hot-swap architecture. The live dashboard preview is MJPEG served locally from OpenCV. When recording is triggered, the firmware releases the preview camera and gives FFmpeg exclusive access for a higher-quality saved clip. I chose that because on a Raspberry Pi 3B+, recording reliability mattered more than running a more complex always-on pipeline.”

**What to show**

- live preview on dashboard
- backend console if useful
- firmware console if useful
- click manual record
- show new clip appear in the dashboard

### Minutes 23-25: Motion trigger

**What to say**

“Manual recording is not the only path. The GPIO motion sensor can trigger the same recording flow automatically. That demonstrates the physical hardware integration side of the project.”

**What to show**

- trigger the sensor
- show resulting event in history

### Minutes 25-27: Clip review and deletion

**What to say**

“Recorded clips are uploaded, stored, and shown in the dashboard. The user can select a recent capture, play it in the featured viewer, and delete it if needed. Owners have stronger management permissions than viewers.”

**What to show**

- featured viewer
- recent captures queue
- delete one clip
- show updated history/storage

### Minutes 27-29: Tradeoffs and limitations

**What to say**

“I made several deliberate tradeoffs. I used static frontend pages instead of a larger frontend framework to keep the stack focused. I used Supabase to avoid rebuilding authentication and storage. I kept the hot-swap camera model because it is the most reliable for this hardware. The main limitations are the simple MJPEG preview path, public clip URLs in the current implementation, and limited automated testing.”

**What to show**

- a short limitations slide
- maybe one code snippet or settings section showing configurable quality tuning

### Minutes 29-30: Conclusion

**What to say**

“Sentio demonstrates a full smart-doorbell workflow: account creation, login, device pairing, live monitoring, manual and motion-triggered recording, cloud upload, event review, and storage-aware management. The project is beyond a prototype because it implements the full path from edge device to user-facing product, while still being honest about the next steps needed for a more production-grade deployment.”

## Backup Plans if the Live Demo Partially Fails

### If the Raspberry Pi stream does not load

Say:

“Live preview in this system is device-hosted MJPEG, so if the local stream is unavailable, the rest of the cloud pipeline is still demonstrable.”

Then show:

- pre-recorded clips already in event history
- featured viewer
- storage summary
- architecture explanation

### If Supabase auth has an issue

Use a pre-authenticated browser session if possible and explain:

“Authentication is handled by Supabase, so if there is a temporary external issue, I can still show the post-login dashboard state and walk through the code-level auth model.”

### If motion sensor trigger misbehaves

Use manual recording as the primary demonstration and explain that motion-triggered recording uses the same recording pipeline with a different trigger source.

### If upload fails during demo

Show the firmware retry/spool explanation:

“Upload failure does not destroy the clip. The system preserves it locally and retries later, which is one of the reliability features I built in.”

## What to Emphasize to Maximize Evaluation

Focus on these points:

1. this is a complete integrated system, not a disconnected demo
2. the architecture reflects deliberate engineering tradeoffs
3. the project uses real authentication and ownership concepts
4. the Raspberry Pi constraints were handled realistically
5. the UI was designed to feel like a product, not just a lab interface
6. the project is honest about limitations and future hardening steps

## Final Presentation Advice

Keep the presentation anchored in three themes:

- **integration**
- **design rationale**
- **practical engineering tradeoffs**

If the professor asks a difficult question, relate your answer back to one of those themes and explain why you made the choice you made given hardware, time, and system goals.
