from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import mimetypes
import asyncio
import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# 1. Load Keys
load_dotenv()
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

DEVICE_ID = "00000000165a568e"
BUCKET_NAME = "doorbell_images"
CLIP_RETENTION_DAYS = 90

# CORS at top level
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


def infer_event_type(filename: str) -> str:
    lower_name = filename.lower()
    if lower_name.startswith("sensor_"):
        return "motion"
    if lower_name.startswith("manual_"):
        return "manual"
    if lower_name.startswith("ring_"):
        return "ring"
    return "motion"


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


@app.get("/")
def read_root():
    return FileResponse("static/index.html")


@app.get("/login.html")
def login_page():
    return FileResponse("static/login.html")


@app.get("/static/login.html")
def login_page_static():
    return FileResponse("static/login.html")


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not supabase:
        return JSONResponse(content={"error": "Database not connected"}, status_code=500)

    if not file.filename:
        return JSONResponse(content={"error": "Missing filename"}, status_code=400)

    safe_filename = os.path.basename(file.filename)
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

        event_payload = {
            "device_id": DEVICE_ID,
            "video_url": public_url,
            "event_type": infer_event_type(safe_filename)
        }

        insert_response = supabase.table("events").insert(event_payload).execute()
        print(f"   [DB] Event inserted: {event_payload}")

        return {
            "status": "success",
            "url": public_url,
            "event": event_payload,
            "db_response": insert_response.data
        }

    except Exception as e:
        print(f"   [Upload Error] {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            disconnected = []
            for client in connected_clients:
                if client != websocket:
                    try:
                        await client.send_text(data)
                    except Exception:
                        disconnected.append(client)
            for client in disconnected:
                if client in connected_clients:
                    connected_clients.remove(client)

    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
