# Deployment and Operations

## 1. Current Deployment Model

The current system is best described as an internal or local-network deployment model with cloud-backed storage and authentication.

In practice:

- the backend runs as a FastAPI application
- the Raspberry Pi firmware runs as a long-lived Python process
- Supabase provides cloud services
- the dashboard is served by the backend
- the live preview stream is served directly from the device on port `8001`

This is appropriate for development, demo use, and controlled deployment.

## 2. Backend Startup

From the repository’s current structure, the backend should be started from the `cloud_backend` directory with:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

This matters because the FastAPI entrypoint is [`cloud_backend/app/main.py`](/home/phreaks4security/SmartDoorbell_v2/cloud_backend/app/main.py), not `cloud_backend/main.py`.

## 3. Device Startup

The device firmware is started from the `device_firmware` directory with:

```bash
python3 doorbell_connect.py
```

There is also a thin wrapper entrypoint:

```bash
python3 doorbell_connect_production.py
```

That wrapper simply imports and runs the same main firmware logic.

## 4. Environment Variables

## 4.1 Backend Environment

The backend expects values such as:

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_BUCKET_NAME`
- `DEFAULT_DEVICE_ID`
- `ALLOWED_ORIGINS`
- `DEVICE_AUTH_MODE`
- `DEVICE_TOKEN_MAP`
- `CLIP_RETENTION_DAYS`

These are typically loaded from `cloud_backend/.env`.

## 4.2 Device Firmware Environment

The firmware loads environment variables from:

- `device_firmware/.env`
- repository root `.env`
- `~/.env`

Important settings include:

- `DOORBELL_WS_URI`
- `DOORBELL_UPLOAD_URL`
- `DOORBELL_DEVICE_ID`
- `DOORBELL_DEVICE_TOKEN`
- `DOORBELL_VIDEO_DURATION`
- `DOORBELL_CAMERA_PATH`
- `DOORBELL_AUDIO_DEVICE`
- `DOORBELL_STREAM_HOST`
- `DOORBELL_STREAM_PORT`
- preview quality settings
- recording quality settings

This configuration model is a strong operational choice because it allows device tuning without code edits.

## 5. Runtime Dependencies

### Backend dependencies

- Python runtime
- FastAPI
- Uvicorn
- Supabase Python client
- dotenv support

### Device dependencies

- Python runtime
- OpenCV
- FFmpeg installed on the Raspberry Pi
- Flask
- `requests`
- `websockets`
- `RPi.GPIO`
- access to camera, audio, and GPIO devices

### Cloud dependency

- active Supabase project with correct tables and storage bucket

## 6. Operational Flow

The normal operating sequence is:

1. backend starts and serves the dashboard
2. user signs in through Supabase-backed auth
3. device starts and connects to the backend WebSocket
4. device streams MJPEG locally on port `8001`
5. manual or motion capture creates recordings
6. recordings upload to backend and then to Supabase Storage
7. dashboard displays updated history and summary

## 7. Reliability Features Already Present

The current implementation includes several operationally useful behaviors:

- repeated camera initialization attempts
- repeated backend WebSocket reconnection attempts
- upload retry spooling for failed clip uploads
- retention cleanup task for old clips
- configurable recording and preview quality settings
- canonical login routing to avoid auth-page inconsistency

These are significant because they show the project considers runtime behavior, not just feature checkboxes.

## 8. Domain and HTTPS Readiness

The current repo does not include a complete public-domain deployment stack.

Specifically, it does not include:

- reverse-proxy configuration
- HTTPS certificate management
- production process supervision configuration
- container orchestration
- public network hardening

That does not mean the project is incomplete. It means the current deployment target is controlled/demo use rather than unrestricted internet production.

## 9. What Full Public Deployment Would Need

To deploy this as a full public product, the next stage would require:

1. reverse proxy such as Nginx or Caddy
2. HTTPS and certificate management
3. process manager such as systemd, Supervisor, or containers
4. hardened firewall and port exposure rules
5. private media delivery or signed URL access
6. stricter device-auth enforcement
7. production logging and monitoring
8. backup and recovery plans
9. infrastructure for scaling WebSocket connections if needed

## 10. Practical Demo-Day Operations

For a successful demonstration, the most important operational checks are:

- backend is running on port `8000`
- Raspberry Pi firmware is running
- the Pi can reach the backend WebSocket and upload endpoint
- Supabase credentials are valid
- the dashboard can reach the device MJPEG stream on port `8001`
- at least one paired device exists for the account being used

## 11. Operational Conclusion

The project’s current operational model is realistic for an internal smart-home deployment and a senior-project live demo. It already reflects practical concerns such as reconnect loops, local retry storage, and configurable environment-driven tuning, even though it is not yet packaged as a public SaaS deployment.
