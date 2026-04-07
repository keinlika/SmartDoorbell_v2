from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, Header, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import mimetypes
import asyncio
import datetime
import time as _time
import hmac
import json

_SERVER_START = _time.time()
from dotenv import load_dotenv
from supabase import create_client, Client

APP_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(APP_DIR)
STATIC_DIR = os.path.join(APP_DIR, "static")
ENV_PATH = os.path.join(BACKEND_DIR, ".env")


def get_env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def parse_origin_list(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


def parse_device_token_map(raw_value: str | None) -> dict[str, str]:
    token_map = {}
    if not raw_value:
        return token_map
    for entry in raw_value.split(","):
        entry = entry.strip()
        if not entry or ":" not in entry:
            continue
        device_id, token = entry.split(":", 1)
        device_id = device_id.strip()
        token = token.strip()
        if device_id and token:
            token_map[device_id] = token
    return token_map


def cors_settings() -> tuple[list[str], bool]:
    if ALLOWED_ORIGINS == ["*"]:
        return ["*"], False
    if ALLOWED_ORIGINS:
        return ALLOWED_ORIGINS, True
    return ["*"], False


# 1. Load Keys
load_dotenv(dotenv_path=ENV_PATH)
_raw_url = os.environ.get("SUPABASE_URL", "")
url = _raw_url if _raw_url.endswith("/") else _raw_url + "/"
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("ERROR: API Keys missing! Check .env")
    supabase = None
else:
    try:
        supabase: Client = create_client(url, key)
        print("   [Cloud] Supabase Connected.")
    except Exception as e:
        print(f"   [Cloud] Connection Failed: {e}")
        supabase = None

app = FastAPI()
connected_clients = []
client_metadata = {}

DEVICE_ID = os.environ.get("DEFAULT_DEVICE_ID", "00000000165a568e")
BUCKET_NAME = os.environ.get("SUPABASE_BUCKET_NAME", "doorbell_images")
CLIP_RETENTION_DAYS = get_env_int("CLIP_RETENTION_DAYS", 90)
ALLOWED_ORIGINS = parse_origin_list(os.environ.get("ALLOWED_ORIGINS"))
CORS_ALLOW_ORIGINS, CORS_ALLOW_CREDENTIALS = cors_settings()
DEVICE_AUTH_MODE = os.environ.get("DEVICE_AUTH_MODE", "shadow").strip().lower() or "shadow"
DEVICE_TOKEN_MAP = parse_device_token_map(os.environ.get("DEVICE_TOKEN_MAP"))

# CORS at top level
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def infer_event_type(filename: str) -> str:
    lower_name = filename.lower()
    if lower_name.startswith("sensor_"):
        return "motion"
    if lower_name.startswith("manual_"):
        return "manual"
    if lower_name.startswith("ring_"):
        return "ring"
    return "motion"


def resolve_device_id(request_device_id: str | None = None) -> str:
    return request_device_id or DEVICE_ID


def get_device_record(device_id: str) -> dict | None:
    if not supabase or not device_id:
        return None
    try:
        response = (
            supabase.table("devices")
            .select("*")
            .eq("device_id", device_id)
            .limit(1)
            .execute()
        )
        records = response.data or []
        return records[0] if records else None
    except Exception as e:
        print(f"   [Auth] Device lookup failed for {device_id}: {e}")
        return None


def get_expected_device_token(device_id: str) -> tuple[str | None, str]:
    device_record = get_device_record(device_id)
    if device_record:
        token_value = device_record.get("device_token")
        if isinstance(token_value, str) and token_value.strip():
            return token_value.strip(), "devices.device_token"
    env_token = DEVICE_TOKEN_MAP.get(device_id)
    if env_token:
        return env_token, "env"
    return None, "none"


def resolve_event_user_id(device_record: dict | None) -> str | None:
    if not device_record:
        return None
    for field_name in ("owner_id", "user_id"):
        field_value = device_record.get(field_name)
        if isinstance(field_value, str) and field_value.strip():
            return field_value.strip()
    return None


def extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def get_authenticated_user_id(authorization: str | None) -> str:
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not connected")

    access_token = extract_bearer_token(authorization)
    if not access_token:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    try:
        user_response = supabase.auth.get_user(access_token)
        user = getattr(user_response, "user", None)
        user_id = getattr(user, "id", None)
    except Exception as e:
        print(f"   [Auth] Browser user lookup failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid session")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")

    return user_id


def get_accessible_devices_for_user(user_id: str) -> list[dict]:
    if not supabase or not user_id:
        return []

    owner_response = (
        supabase.table("devices")
        .select("device_id, owner_id, user_id, is_claimed, name, status, paired_at, updated_at")
        .eq("owner_id", user_id)
        .order("name", desc=False)
        .execute()
    )
    compatibility_response = (
        supabase.table("devices")
        .select("device_id, owner_id, user_id, is_claimed, name, status, paired_at, updated_at")
        .eq("user_id", user_id)
        .order("name", desc=False)
        .execute()
    )
    owned_devices = (owner_response.data or []) + (compatibility_response.data or [])
    owned_by_id = {
        device["device_id"]: {**device, "access_role": "owner"}
        for device in owned_devices
        if device.get("device_id")
    }

    membership_response = (
        supabase.table("device_members")
        .select("device_id, role")
        .eq("user_id", user_id)
        .execute()
    )
    memberships = membership_response.data or []
    member_only_ids = [
        membership.get("device_id")
        for membership in memberships
        if membership.get("device_id") and membership.get("device_id") not in owned_by_id
    ]

    shared_devices = []
    if member_only_ids:
        shared_lookup = {membership["device_id"]: membership.get("role", "viewer") for membership in memberships if membership.get("device_id")}
        for device_id in member_only_ids:
            shared_response = (
                supabase.table("devices")
                .select("device_id, owner_id, user_id, is_claimed, name, status, paired_at, updated_at")
                .eq("device_id", device_id)
                .limit(1)
                .execute()
            )
            shared_rows = shared_response.data or []
            if shared_rows:
                device = shared_rows[0]
                shared_devices.append({**device, "access_role": shared_lookup.get(device_id, "viewer")})

    return list(owned_by_id.values()) + shared_devices


def client_info(role: str = "viewer", device_id: str | None = None, authenticated: bool = False) -> dict:
    return {
        "role": role,
        "device_id": device_id,
        "authenticated": authenticated,
    }


def validate_device_credentials(request_device_id: str | None, request_device_token: str | None) -> tuple[bool, str | None, str | None]:
    if not request_device_id:
        return False, None, "missing device id"

    expected_token, token_source = get_expected_device_token(request_device_id)
    if not expected_token:
        return False, None, "unknown device"

    if not request_device_token:
        return False, None, "missing device token"

    if not hmac.compare_digest(request_device_token, expected_token):
        return False, None, "invalid device token"

    if token_source != "none":
        print(f"   [Auth] Device {request_device_id} authenticated via {token_source}")
    return True, request_device_id, None


def resolve_device_context(request_device_id: str | None, request_device_token: str | None) -> tuple[str | None, bool, str | None]:
    if DEVICE_AUTH_MODE == "off":
        return resolve_device_id(request_device_id), False, None

    is_valid, verified_device_id, auth_error = validate_device_credentials(request_device_id, request_device_token)
    if is_valid:
        return verified_device_id, True, None

    if DEVICE_AUTH_MODE == "enforce":
        return None, False, auth_error or "device authentication required"

    fallback_device_id = resolve_device_id(request_device_id)
    if auth_error:
        print(f"   [Auth Shadow] {fallback_device_id}: {auth_error}")
    return fallback_device_id, False, auth_error


def is_device_client(websocket: WebSocket) -> bool:
    metadata = client_metadata.get(websocket, {})
    if metadata.get("role") != "device":
        return False
    if DEVICE_AUTH_MODE == "enforce":
        return bool(metadata.get("authenticated"))
    return True


def register_device_client(websocket: WebSocket, payload: dict) -> dict:
    device_id, authenticated, auth_error = resolve_device_context(
        payload.get("device_id"),
        payload.get("device_token"),
    )

    if device_id is None:
        client_metadata[websocket] = client_info()
        return {
            "action": "device_auth_ack",
            "status": "rejected",
            "reason": auth_error or "device authentication failed",
        }

    client_metadata[websocket] = client_info(
        role="device",
        device_id=device_id,
        authenticated=authenticated,
    )
    return {
        "action": "device_auth_ack",
        "status": "authenticated" if authenticated else "legacy",
        "device_id": device_id,
        "mode": DEVICE_AUTH_MODE,
    }


def find_existing_event(device_id: str, public_url: str):
    response = (
        supabase.table("events")
        .select("*")
        .eq("device_id", device_id)
        .eq("video_url", public_url)
        .order("id", desc=True)
        .limit(1)
        .execute()
    )
    existing = response.data or []
    return existing[0] if existing else None


async def cleanup_old_clips():
    """
    Deletes events and their Supabase storage files older than CLIP_RETENTION_DAYS.
    Runs once on startup then every 24 hours.
    """
    while True:
        if supabase:
            try:
                cutoff = (
                    datetime.datetime.utcnow() -
                    datetime.timedelta(days=CLIP_RETENTION_DAYS)
                ).isoformat()

                response = (
                    supabase.table("events")
                    .select("id, video_url")
                    .lt("created_at", cutoff)
                    .execute()
                )

                old_events = response.data or []

                if old_events:
                    print(f"   [Cleanup] Found {len(old_events)} clip(s) older than {CLIP_RETENTION_DAYS} days.")

                    for event in old_events:
                        try:
                            # Delete from storage
                            filename = event["video_url"].rsplit("/", 1)[-1].split("?")[0]
                            supabase.storage.from_(BUCKET_NAME).remove([filename])

                            # Delete from database
                            supabase.table("events").delete().eq("id", event["id"]).execute()
                            print(f"   [Cleanup] Deleted event #{event['id']} ({filename})")

                        except Exception as e:
                            print(f"   [Cleanup] Failed to delete event #{event['id']}: {e}")
                else:
                    print(f"   [Cleanup] No clips older than {CLIP_RETENTION_DAYS} days found.")

            except Exception as e:
                print(f"   [Cleanup Error] {e}")

        # Wait 24 hours before next cleanup
        await asyncio.sleep(60 * 60 * 24)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cleanup_old_clips())
    print(f"   [Cleanup] Auto-cleanup scheduled — clips older than {CLIP_RETENTION_DAYS} days will be removed daily.")
    print(f"   [Server] Static assets: {STATIC_DIR}")
    print(f"   [Server] Allowed CORS origins: {CORS_ALLOW_ORIGINS}")
    print(f"   [Auth] Device auth mode: {DEVICE_AUTH_MODE}")


@app.get("/")
def read_root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/login.html")
def login_page():
    return FileResponse(os.path.join(STATIC_DIR, "login.html"))


@app.get("/static/login.html")
def login_page_static():
    return FileResponse(os.path.join(STATIC_DIR, "login.html"))


@app.get("/healthz")
async def health_check():
    return {
        "status": "ok",
        "supabase_connected": bool(supabase),
        "uptime_seconds": int(_time.time() - _SERVER_START),
    }


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    x_device_id: str | None = Header(default=None),
    x_device_token: str | None = Header(default=None),
):
    if not supabase:
        return JSONResponse(content={"error": "Database not connected"}, status_code=500)

    if not file.filename:
        return JSONResponse(content={"error": "Missing filename"}, status_code=400)

    safe_filename = os.path.basename(file.filename)
    device_id, is_authenticated, auth_error = resolve_device_context(x_device_id, x_device_token)
    if device_id is None:
        return JSONResponse(content={"error": auth_error or "Unauthorized device"}, status_code=401)
    device_record = get_device_record(device_id)
    event_user_id = resolve_event_user_id(device_record)

    if auth_error and DEVICE_AUTH_MODE == "shadow":
        print(f"   [Auth Shadow] Upload accepted for fallback device {device_id}")

    print(f"   [Upload] Receiving: {safe_filename}")

    try:
        file_bytes = await file.read()
        content_type, _ = mimetypes.guess_type(safe_filename)
        if not content_type:
            content_type = "application/octet-stream"

        supabase.storage.from_(BUCKET_NAME).upload(
            path=safe_filename,
            file=file_bytes,
            file_options={"content-type": content_type, "upsert": "true"}
        )

        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(safe_filename)
        print(f"   [Cloud] Saved to: {public_url}")

        existing_event = find_existing_event(device_id, public_url)
        if existing_event:
            print(f"   [DB] Reused existing event #{existing_event['id']} for {safe_filename}")
            return {
                "status": "success",
                "url": public_url,
                "event": existing_event,
                "db_response": [existing_event],
                "duplicate": True,
                "authenticated": is_authenticated,
            }

        event_payload = {
            "device_id": device_id,
            "user_id": event_user_id,
            "video_url": public_url,
            "event_type": infer_event_type(safe_filename),
            "file_size": len(file_bytes),
        }

        insert_response = supabase.table("events").insert(event_payload).execute()
        print(f"   [DB] Event inserted: {event_payload}")

        return {
            "status": "success",
            "url": public_url,
            "event": event_payload,
            "db_response": insert_response.data,
            "authenticated": is_authenticated,
        }

    except Exception as e:
        print(f"   [Upload Error] {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/api/pair-device")
async def pair_device(request: Request, authorization: str | None = Header(default=None)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not connected")

    user_id = get_authenticated_user_id(authorization)

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")

    pairing_code = str((payload or {}).get("pairing_code", "")).strip()
    if not pairing_code:
        raise HTTPException(status_code=400, detail="Missing pairing code")

    try:
        lookup_response = (
            supabase.table("devices")
            .select("device_id, owner_id, user_id, is_claimed, name, status, pairing_code")
            .eq("pairing_code", pairing_code)
            .limit(1)
            .execute()
        )
        device_rows = lookup_response.data or []
        device = device_rows[0] if device_rows else None
        if not device:
            raise HTTPException(status_code=404, detail="Pairing code not found")

        existing_owner_id = device.get("owner_id")
        if device.get("is_claimed") and existing_owner_id and existing_owner_id != user_id:
            raise HTTPException(status_code=409, detail="This device has already been claimed by another account")

        update_response = (
            supabase.table("devices")
            .update({
                "owner_id": user_id,
                "user_id": user_id,
                "is_claimed": True,
            })
            .eq("device_id", device["device_id"])
            .execute()
        )
        if hasattr(update_response, "data") and update_response.data == []:
            raise HTTPException(status_code=409, detail="This device was claimed by another account before pairing completed")

        claimed_lookup_response = (
            supabase.table("devices")
            .select("device_id, owner_id, user_id, is_claimed, name, status")
            .eq("device_id", device["device_id"])
            .limit(1)
            .execute()
        )
        claimed_rows = claimed_lookup_response.data or []
        if not claimed_rows:
            raise HTTPException(status_code=500, detail="Claim succeeded but device record could not be reloaded")

        claimed_device = claimed_rows[0]

        member_response = (
            supabase.table("device_members")
            .select("id")
            .eq("device_id", claimed_device["device_id"])
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        existing_members = member_response.data or []
        if not existing_members:
            supabase.table("device_members").insert({
                "device_id": claimed_device["device_id"],
                "user_id": user_id,
                "role": "owner",
            }).execute()

        return {"status": "success", "device": claimed_device}
    except HTTPException:
        raise
    except Exception as e:
        print(f"   [Pairing Error] {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/device-access")
async def get_device_access(authorization: str | None = Header(default=None)):
    user_id = get_authenticated_user_id(authorization)

    try:
        devices = get_accessible_devices_for_user(user_id)
        return {"devices": devices}
    except HTTPException:
        raise
    except Exception as e:
        print(f"   [Access Error] {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/events/{event_id}")
async def delete_event(event_id: int):
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not connected")

    try:
        response = supabase.table("events").select("video_url").eq("id", event_id).single().execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Event not found")

        video_url = response.data["video_url"]
        filename = video_url.rsplit("/", 1)[-1].split("?")[0]

        print(f"   [Delete] Removing file: {filename}")
        supabase.storage.from_(BUCKET_NAME).remove([filename])

        supabase.table("events").delete().eq("id", event_id).execute()
        print(f"   [Delete] Database row {event_id} removed.")

        return {"status": "success", "message": f"Deleted {filename} completely!"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"   [Delete Error] {repr(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def get_status():
    """Live status: uptime, clip counts, last event."""
    uptime_secs = int(_time.time() - _SERVER_START)
    hours, remainder = divmod(uptime_secs, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m" if hours else f"{minutes}m {seconds}s"

    clips_today = 0
    total_clips = 0
    last_event = None

    if supabase:
        try:
            today = datetime.datetime.utcnow().date().isoformat()
            today_res = supabase.table("events").select("id", count="exact").gte("created_at", today).execute()
            clips_today = today_res.count or 0

            total_res = supabase.table("events").select("id", count="exact").execute()
            total_clips = total_res.count or 0

            last_res = supabase.table("events").select("created_at").order("created_at", desc=True).limit(1).execute()
            if last_res.data:
                last_event = last_res.data[0]["created_at"]
        except Exception as e:
            print(f"   [Status Error] {e}")

    return {
        "uptime": uptime_str,
        "clips_today": clips_today,
        "total_clips": total_clips,
        "last_event": last_event,
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    client_metadata[websocket] = client_info()

    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                payload = None

            if isinstance(payload, dict) and payload.get("action") == "device_auth":
                auth_response = register_device_client(websocket, payload)
                await websocket.send_text(json.dumps(auth_response))
                if auth_response["status"] == "rejected":
                    await websocket.close(code=1008)
                    break
                continue

            disconnected = []
            targets = []
            if isinstance(payload, dict) and payload.get("action") == "manual_record":
                targets = [client for client in connected_clients if client != websocket and is_device_client(client)]
                if not targets and DEVICE_AUTH_MODE != "enforce":
                    targets = [client for client in connected_clients if client != websocket]
            else:
                targets = [client for client in connected_clients if client != websocket]

            for client in targets:
                if client != websocket:
                    try:
                        await client.send_text(data)
                    except Exception:
                        disconnected.append(client)
            for client in disconnected:
                if client in connected_clients:
                    connected_clients.remove(client)
                client_metadata.pop(client, None)

    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        client_metadata.pop(websocket, None)
