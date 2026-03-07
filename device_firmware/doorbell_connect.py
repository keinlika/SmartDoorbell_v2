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
from flask import Flask, Response

# ----------------------------
# CONFIGURATION
# ----------------------------
WS_URI = "ws://localhost:8000/ws"
UPLOAD_URL = "http://localhost:8000/upload"
SENSOR_PIN = 4
VIDEO_DURATION = 5  # seconds

# Direct physical camera
PHYSICAL_CAM_INDEX = 0
PHYSICAL_CAM_PATH = "/dev/video0"
AUDIO_DEV = "plughw:1,0"

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

def init_camera():
    global cap
    cap = cv2.VideoCapture(PHYSICAL_CAM_INDEX)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

init_camera()

def generate_frames():
    """Reads frames from OpenCV, optimizes them, and streams MJPEG."""
    global cap
    frame_counter = 0
    
    while True:
        # 1. HOT-SWAP PAUSE: If recording, sleep and yield nothing.
        if is_recording.is_set():
            time.sleep(0.5)
            continue

        with cap_lock:
            if cap is not None and cap.isOpened():
                success = cap.grab()
                if success:
                    success, frame = cap.retrieve()
            else:
                success = False

        if not success or frame is None:
            time.sleep(0.1)
            continue

        # 2. OPTIMIZATION: 15 FPS and 360p
        frame_counter += 1
        if frame_counter % 2 != 0:
            continue
            
        frame_resized = cv2.resize(frame, (640, 360))
        ok, buffer = cv2.imencode(".jpg", frame_resized, [cv2.IMWRITE_JPEG_QUALITY, 65])
        
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
    app.run(host="0.0.0.0", port=8001, debug=False, use_reloader=False, threaded=True)

threading.Thread(target=start_flask, daemon=True).start()

# ----------------------------
# VIDEO MANAGER
# ----------------------------
class VideoManager:
    def __init__(self):
        # Using explicit mjpeg input format for the physical camera to ensure high framerate
        self.cmd_template = (
            "ffmpeg -hide_banner -loglevel warning -y "
            f"-f v4l2 -input_format mjpeg -video_size 1280x720 -framerate 30 -i {PHYSICAL_CAM_PATH} "
            f"-f alsa -ac 1 -i {AUDIO_DEV} "
            "-c:v libx264 -preset ultrafast -c:a aac "
            "-t {} {}"
        )
        print("   [System] Camera Configured: Direct Physical Hot-Swap")

    def record_clip(self, filename: str) -> bool:
        global cap
        print(f"   [Camera] Recording {VIDEO_DURATION}s clip...")

        # --- HARDWARE HANDOFF (DROP) ---
        is_recording.set()
        with cap_lock:
            if cap is not None:
                cap.release()
        time.sleep(0.5) # Give Linux half a second to fully free /dev/video0

        # --- RECORDING ---
        try:
            full_command = self.cmd_template.format(VIDEO_DURATION, filename)
            subprocess.run(
                full_command, 
                shell=True, 
                check=False
            )
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
            # --- HARDWARE HANDOFF (RECLAIM) ---
            with cap_lock:
                init_camera()
            is_recording.clear()

    def upload_to_cloud(self, filename: str) -> str | None:
        print("   [Cloud] Uploading video...")
        try:
            with open(filename, "rb") as f:
                file_bytes = f.read()
            files = {"file": (os.path.basename(filename), file_bytes, "video/mp4")}
            response = requests.post(UPLOAD_URL, files=files, timeout=30)
            
            if response.status_code == 200:
                return response.json().get("url")
            print(f"   [Cloud Error] {response.status_code}: {response.text}")
            return None
        except Exception as e:
            print(f"   [Cloud Error] Upload failed: {e}")
            return None

cam = VideoManager()
recording_lock = asyncio.Lock()

async def execute_recording(websocket, trigger_type: str):
    async with recording_lock:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"\n!!! {trigger_type.upper()} RECORDING at {timestamp} !!!")
        filename = f"{trigger_type}_{timestamp}.mp4"

        try:
            await websocket.send(json.dumps({"event": "recording_started", "type": trigger_type, "timestamp": timestamp}))
        except Exception:
            pass

        video_url = None
        if cam.record_clip(filename):
            video_url = cam.upload_to_cloud(filename)

        try:
            os.remove(filename)
        except Exception:
            pass

        payload = {
            "event": "motion" if trigger_type == "sensor" else "manual_record_complete",
            "status": "detected" if trigger_type == "sensor" else "completed",
            "video_url": video_url,
            "timestamp": timestamp,
        }

        try:
            await websocket.send(json.dumps(payload))
            print(f"   -> Alert sent! URL: {video_url}")
        except Exception:
            pass

async def listen_to_sensor(websocket):
    print(f"   [Sensor] Active on GPIO {SENSOR_PIN}. Waiting for movement...")
    is_motion_active = False
    while True:
        if GPIO.input(SENSOR_PIN):
            if not is_motion_active:
                await execute_recording(websocket, "sensor")
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
            await execute_recording(websocket, "manual")

async def main():
    print(f"Connecting to Cloud at {WS_URI}...")
    while True:
        try:
            async with websockets.connect(WS_URI) as websocket:
                print("SUCCESS! Connected.")
                await asyncio.gather(
                    listen_to_sensor(websocket),
                    listen_to_cloud(websocket),
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
