#!/usr/bin/env python3
"""
doorbell_connect.py (Hot-Swap Architecture)

Architecture:
- Directly reads from physical camera /dev/video0.
- Serves an optimized MJPEG stream (640x360 @ 15fps) via Flask on port 8001.
- On motion/manual trigger: Pauses stream, releases camera, lets FFmpeg record
  high-quality video, then re-acquires the camera.
"""

import asyncio
import websockets
import RPi.GPIO as GPIO
import json
import datetime
import os
import requests
import subprocess
import cv2
import threading
import time
import shutil
import shlex
from flask import Flask, Response


def get_env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def get_env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def get_env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_env_files():
    env_candidates = (
        os.path.join(FIRMWARE_DIR, ".env"),
        os.path.join(os.path.dirname(FIRMWARE_DIR), ".env"),
        os.path.expanduser("~/.env"),
    )

    for env_path in env_candidates:
        if not os.path.isfile(env_path):
            continue

        try:
            with open(env_path, "r", encoding="utf-8") as env_file:
                for raw_line in env_file:
                    line = raw_line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue

                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip("'").strip('"')

                    if key.startswith("export "):
                        key = key[7:].strip()

                    if key and key not in os.environ:
                        os.environ[key] = value
        except Exception as exc:
            print(f"   [Config] Failed to load {env_path}: {exc}")


def get_serial() -> str:
    cpuserial = "0000000000000000"
    try:
        with open("/proc/cpuinfo", "r") as cpuinfo:
            for line in cpuinfo:
                if line.startswith("Serial"):
                    cpuserial = line.split(":", 1)[1].strip()
                    break
    except Exception:
        cpuserial = "TEST_DEVICE_001"
    return cpuserial


# ----------------------------
# CONFIGURATION
# ----------------------------
FIRMWARE_DIR = os.path.dirname(os.path.abspath(__file__))
load_env_files()
WS_URI = os.environ.get("DOORBELL_WS_URI", "ws://192.168.1.232:8000/ws")
UPLOAD_URL = os.environ.get("DOORBELL_UPLOAD_URL", "http://192.168.1.232:8000/upload")
SENSOR_PIN = get_env_int("DOORBELL_SENSOR_PIN", 4)
VIDEO_DURATION = get_env_int("DOORBELL_VIDEO_DURATION", 5)

PHYSICAL_CAM_INDEX = get_env_int("DOORBELL_CAMERA_INDEX", 0)
PHYSICAL_CAM_PATH = os.environ.get("DOORBELL_CAMERA_PATH", "/dev/video0")
AUDIO_DEV = os.environ.get("DOORBELL_AUDIO_DEVICE", "plughw:1,0")
UPLOAD_TIMEOUT = get_env_int("DOORBELL_UPLOAD_TIMEOUT", 30)
UPLOAD_RETRY_INTERVAL = get_env_int("DOORBELL_UPLOAD_RETRY_INTERVAL", 15)
STREAM_HOST = os.environ.get("DOORBELL_STREAM_HOST", "0.0.0.0")
STREAM_PORT = get_env_int("DOORBELL_STREAM_PORT", 8001)
SPOOL_DIR = os.environ.get("DOORBELL_SPOOL_DIR", os.path.join(FIRMWARE_DIR, "spool"))
DEVICE_ID = os.environ.get("DOORBELL_DEVICE_ID", get_serial())
DEVICE_TOKEN = os.environ.get("DOORBELL_DEVICE_TOKEN", "").strip()
DEVICE_NAME = os.environ.get("DOORBELL_DEVICE_NAME", "Front Door Main")
PREVIEW_CAPTURE_WIDTH = get_env_int("DOORBELL_PREVIEW_CAPTURE_WIDTH", 640)
PREVIEW_CAPTURE_HEIGHT = get_env_int("DOORBELL_PREVIEW_CAPTURE_HEIGHT", 480)
PREVIEW_OUTPUT_WIDTH = get_env_int("DOORBELL_PREVIEW_OUTPUT_WIDTH", 640)
PREVIEW_OUTPUT_HEIGHT = get_env_int("DOORBELL_PREVIEW_OUTPUT_HEIGHT", 360)
PREVIEW_FPS = get_env_int("DOORBELL_PREVIEW_FPS", 12)
PREVIEW_JPEG_QUALITY = get_env_int("DOORBELL_PREVIEW_JPEG_QUALITY", 60)
PREVIEW_FRAME_SKIP = max(0, get_env_int("DOORBELL_PREVIEW_FRAME_SKIP", 0))
PREVIEW_BUFFER_SIZE = max(1, get_env_int("DOORBELL_PREVIEW_BUFFER_SIZE", 1))
PREVIEW_CAMERA_FOURCC = os.environ.get("DOORBELL_PREVIEW_CAMERA_FOURCC", "MJPG")
PREVIEW_USE_MJPEG = get_env_bool("DOORBELL_PREVIEW_USE_MJPEG", True)
CAMERA_INIT_RETRIES = max(1, get_env_int("DOORBELL_CAMERA_INIT_RETRIES", 5))
CAMERA_INIT_DELAY = max(0.1, get_env_float("DOORBELL_CAMERA_INIT_DELAY", 1.5))
RECORD_WIDTH = get_env_int("DOORBELL_RECORD_WIDTH", 1280)
RECORD_HEIGHT = get_env_int("DOORBELL_RECORD_HEIGHT", 720)
RECORD_FPS = get_env_int("DOORBELL_RECORD_FPS", 24)
RECORD_INPUT_FORMAT = os.environ.get("DOORBELL_RECORD_INPUT_FORMAT", "mjpeg")
RECORD_CRF = get_env_int("DOORBELL_RECORD_CRF", 21)
RECORD_PRESET = os.environ.get("DOORBELL_RECORD_PRESET", "superfast")
RECORD_VIDEO_CODEC = os.environ.get("DOORBELL_RECORD_VIDEO_CODEC", "libx264")
RECORD_AUDIO_BITRATE = os.environ.get("DOORBELL_RECORD_AUDIO_BITRATE", "96k")
RECORD_AUDIO_CHANNELS = max(1, get_env_int("DOORBELL_RECORD_AUDIO_CHANNELS", 1))
RECORD_THREAD_QUEUE_SIZE = max(64, get_env_int("DOORBELL_RECORD_THREAD_QUEUE_SIZE", 256))
RECORD_RELEASE_DELAY = max(0.2, get_env_float("DOORBELL_RECORD_RELEASE_DELAY", 0.75))
RECORD_EXTRA_ARGS = shlex.split(os.environ.get("DOORBELL_RECORD_EXTRA_ARGS", ""))

# Global lock and state for Hot-Swapping
cap_lock = threading.Lock()
is_recording = threading.Event()
cap = None

# ----------------------------
# GPIO SETUP
# ----------------------------
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(SENSOR_PIN, GPIO.IN)

# ----------------------------
# LIVE STREAM SETUP (Flask & OpenCV)
# ----------------------------
app = Flask(__name__)


def ensure_spool_dir():
    os.makedirs(SPOOL_DIR, exist_ok=True)


def parse_clip_metadata(filepath: str) -> tuple[str, str]:
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    if "_" not in base_name:
        return "sensor", base_name
    trigger_type, timestamp = base_name.split("_", 1)
    return trigger_type, timestamp


def build_capture_candidates():
    candidates = []
    if PHYSICAL_CAM_PATH:
        candidates.append(PHYSICAL_CAM_PATH)
    candidates.append(PHYSICAL_CAM_INDEX)
    return candidates


def configure_preview_capture(video_capture):
    video_capture.set(cv2.CAP_PROP_BUFFERSIZE, PREVIEW_BUFFER_SIZE)
    video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, PREVIEW_CAPTURE_WIDTH)
    video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, PREVIEW_CAPTURE_HEIGHT)
    video_capture.set(cv2.CAP_PROP_FPS, PREVIEW_FPS)
    if PREVIEW_USE_MJPEG and len(PREVIEW_CAMERA_FOURCC) >= 4:
        fourcc = cv2.VideoWriter_fourcc(*PREVIEW_CAMERA_FOURCC[:4])
        video_capture.set(cv2.CAP_PROP_FOURCC, fourcc)


def open_camera_capture():
    for source in build_capture_candidates():
        try:
            new_cap = cv2.VideoCapture(source, cv2.CAP_V4L2)
        except TypeError:
            new_cap = cv2.VideoCapture(source)

        configure_preview_capture(new_cap)
        if not new_cap.isOpened():
            new_cap.release()
            continue

        return new_cap, source

    return None, None


def init_camera(retries: int = CAMERA_INIT_RETRIES, delay: float = CAMERA_INIT_DELAY):
    global cap
    for attempt in range(1, retries + 1):
        new_cap, source = open_camera_capture()
        if new_cap is not None:
            ok, test_frame = new_cap.read()
            if ok and test_frame is not None:
                cap = new_cap
                print(f"   [Camera] Ready from {source} (attempt {attempt}/{retries})")
                return
            new_cap.release()
        print(f"   [Camera] Not ready yet, retrying in {delay}s... ({attempt}/{retries})")
        time.sleep(delay)
    print("   [Camera] WARNING: Could not open camera at startup. Stream will retry.")

init_camera()
ensure_spool_dir()

def generate_frames():
    global cap
    frame_counter = 0

    while True:
        if is_recording.is_set():
            time.sleep(0.5)
            continue

        success = False
        frame = None
        with cap_lock:
            if cap is not None and cap.isOpened():
                success = cap.grab()
                if success:
                    success, frame = cap.retrieve()
            else:
                init_camera(retries=1, delay=0)

        if not success or frame is None:
            time.sleep(2.0)
            continue

        frame_counter += 1
        if PREVIEW_FRAME_SKIP and frame_counter % (PREVIEW_FRAME_SKIP + 1) != 0:
            continue

        if frame.shape[1] != PREVIEW_OUTPUT_WIDTH or frame.shape[0] != PREVIEW_OUTPUT_HEIGHT:
            frame = cv2.resize(frame, (PREVIEW_OUTPUT_WIDTH, PREVIEW_OUTPUT_HEIGHT))
        ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, PREVIEW_JPEG_QUALITY])

        if not ok:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
        )

@app.route("/stream")
def stream():
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

def start_flask():
    app.run(host=STREAM_HOST, port=STREAM_PORT, debug=False, use_reloader=False, threaded=True)

threading.Thread(target=start_flask, daemon=True).start()

# ----------------------------
# VIDEO MANAGER
# ----------------------------
class VideoManager:
    def __init__(self):
        print(
            "   [System] Camera Configured: "
            f"preview {PREVIEW_CAPTURE_WIDTH}x{PREVIEW_CAPTURE_HEIGHT}@{PREVIEW_FPS} "
            f"-> {PREVIEW_OUTPUT_WIDTH}x{PREVIEW_OUTPUT_HEIGHT}, "
            f"record {RECORD_WIDTH}x{RECORD_HEIGHT}@{RECORD_FPS} {RECORD_VIDEO_CODEC} CRF {RECORD_CRF}"
        )

    def build_record_command(self, filename: str) -> list[str]:
        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-y",
            "-thread_queue_size",
            str(RECORD_THREAD_QUEUE_SIZE),
            "-f",
            "v4l2",
            "-input_format",
            RECORD_INPUT_FORMAT,
            "-video_size",
            f"{RECORD_WIDTH}x{RECORD_HEIGHT}",
            "-framerate",
            str(RECORD_FPS),
            "-i",
            PHYSICAL_CAM_PATH,
            "-thread_queue_size",
            str(RECORD_THREAD_QUEUE_SIZE),
            "-f",
            "alsa",
            "-ac",
            str(RECORD_AUDIO_CHANNELS),
            "-i",
            AUDIO_DEV,
            "-c:v",
            RECORD_VIDEO_CODEC,
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            RECORD_AUDIO_BITRATE,
        ]
        if RECORD_VIDEO_CODEC in {"libx264", "libx264rgb", "libx265"}:
            command.extend(["-preset", RECORD_PRESET, "-crf", str(RECORD_CRF)])
        command.extend(RECORD_EXTRA_ARGS)
        command.extend(["-t", str(VIDEO_DURATION), filename])
        return command

    def record_clip(self, filename: str) -> bool:
        global cap
        print(f"   [Camera] Starting recording to {filename}...")

        is_recording.set()
        with cap_lock:
            if cap is not None:
                cap.release()
                cap = None
        time.sleep(RECORD_RELEASE_DELAY)

        try:
            command = self.build_record_command(filename)
            subprocess.run(command, check=False)
            success = os.path.exists(filename) and os.path.getsize(filename) > 1000

            if success:
                print(f"   [Camera] CLIP SAVED: {filename}")
            else:
                print("   [Camera Error] Recording failed (File empty).")
            return success

        except Exception as e:
            print(f"   [Camera Crash] {e}")
            return False

        finally:
            with cap_lock:
                init_camera()
            is_recording.clear()

    def upload_to_cloud(self, filename: str) -> str | None:
        print("   [Cloud] Uploading video...")
        try:
            headers = {"X-Device-ID": DEVICE_ID}
            if DEVICE_TOKEN:
                headers["X-Device-Token"] = DEVICE_TOKEN
            with open(filename, "rb") as f:
                files = {"file": (os.path.basename(filename), f, "video/mp4")}
                response = requests.post(UPLOAD_URL, files=files, headers=headers, timeout=UPLOAD_TIMEOUT)

            if response.status_code in (200, 201):
                return response.json().get("url")
            print(f"   [Cloud Error] {response.status_code}: {response.text}")
            return None
        except Exception as e:
            print(f"   [Cloud Error] Upload failed: {e}")
            return None

cam = VideoManager()
recording_lock = asyncio.Lock()
upload_lock = asyncio.Lock()
inflight_uploads = set()


def queue_clip_for_retry(filepath: str) -> str:
    ensure_spool_dir()
    queued_path = os.path.join(SPOOL_DIR, os.path.basename(filepath))
    if os.path.abspath(filepath) != os.path.abspath(queued_path):
        shutil.move(filepath, queued_path)
    print(f"   [Cloud] Clip queued for retry: {queued_path}")
    return queued_path


async def send_clip_event(websocket, trigger_type: str, timestamp: str, video_url: str | None, queued: bool = False):
    payload = {
        "event": "motion" if trigger_type == "sensor" else "manual_record_complete",
        "status": "queued" if queued else ("detected" if trigger_type == "sensor" else "completed"),
        "video_url": video_url,
        "timestamp": timestamp,
        "queued": queued,
    }

    try:
        await websocket.send(json.dumps(payload))
        print(f"   -> Alert sent! URL: {video_url}")
    except Exception:
        pass


async def upload_clip(filepath: str) -> str | None:
    if filepath in inflight_uploads:
        return None

    async with upload_lock:
        if filepath in inflight_uploads:
            return None

        inflight_uploads.add(filepath)
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, cam.upload_to_cloud, filepath)
        finally:
            inflight_uploads.discard(filepath)


async def retry_pending_uploads(websocket):
    while True:
        try:
            ensure_spool_dir()
            pending_files = sorted(
                os.path.join(SPOOL_DIR, name)
                for name in os.listdir(SPOOL_DIR)
                if name.lower().endswith(".mp4")
            )

            for filepath in pending_files:
                if filepath in inflight_uploads or not os.path.exists(filepath):
                    continue

                trigger_type, timestamp = parse_clip_metadata(filepath)
                video_url = await upload_clip(filepath)
                if not video_url:
                    continue

                try:
                    os.remove(filepath)
                except Exception as e:
                    print(f"   [Cloud Error] Uploaded clip could not be deleted: {e}")

                await send_clip_event(websocket, trigger_type, timestamp, video_url)

        except websockets.exceptions.ConnectionClosed:
            break
        except Exception as e:
            print(f"   [Cloud Retry Error] {e}")

        await asyncio.sleep(UPLOAD_RETRY_INTERVAL)

async def execute_recording(websocket, trigger_type: str):
    async with recording_lock:
        loop = asyncio.get_running_loop()
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"\n!!! {trigger_type.upper()} RECORDING at {timestamp} !!!")
        filename = f"{trigger_type}_{timestamp}.mp4"

        try:
            await websocket.send(json.dumps({
                "event": "recording_started",
                "type": trigger_type,
                "timestamp": timestamp
            }))
        except Exception:
            pass

        video_url = None
        queued = False
        success = await loop.run_in_executor(None, cam.record_clip, filename)
        if success:
            video_url = await upload_clip(filename)
            if video_url:
                try:
                    os.remove(filename)
                except Exception as e:
                    print(f"   [Cloud Error] Uploaded clip could not be deleted: {e}")
            else:
                queue_clip_for_retry(filename)
                queued = True
        elif os.path.exists(filename):
            try:
                os.remove(filename)
            except Exception as e:
                print(f"   [Camera Error] Failed to remove incomplete clip: {e}")

        await send_clip_event(websocket, trigger_type, timestamp, video_url, queued=queued)

async def listen_to_sensor(websocket):
    print(f"   [Sensor] Active on GPIO {SENSOR_PIN}. Waiting for movement...")
    is_motion_active = False
    while True:
        if GPIO.input(SENSOR_PIN):
            if not is_motion_active:
                asyncio.create_task(execute_recording(websocket, "sensor"))
                is_motion_active = True
        else:
            if is_motion_active:
                is_motion_active = False
        await asyncio.sleep(0.1)

async def listen_to_cloud(websocket):
    while True:
        try:
            msg = await websocket.recv()
        except websockets.exceptions.ConnectionClosed:
            break
        try:
            data = json.loads(msg)
        except json.JSONDecodeError:
            continue

        if data.get("action") == "manual_record":
            asyncio.create_task(execute_recording(websocket, "manual"))


async def authenticate_with_cloud(websocket):
    payload = {
        "action": "device_auth",
        "device_id": DEVICE_ID,
        "device_name": DEVICE_NAME,
    }
    if DEVICE_TOKEN:
        payload["device_token"] = DEVICE_TOKEN
    await websocket.send(json.dumps(payload))

async def main():
    print(f"Connecting to Cloud at {WS_URI}...")
    while True:
        try:
            async with websockets.connect(WS_URI) as websocket:
                print("SUCCESS! Connected.")
                await authenticate_with_cloud(websocket)
                await asyncio.gather(
                    listen_to_sensor(websocket),
                    listen_to_cloud(websocket),
                    retry_pending_uploads(websocket),
                )
        except Exception as e:
            print(f"Connection Error: {e}. Retrying in 5s...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup()
        with cap_lock:
            try:
                if cap is not None:
                    cap.release()
            except Exception:
                pass
