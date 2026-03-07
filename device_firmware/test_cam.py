import cv2
import time

def test_camera(index):
    print(f"\n--- Testing Camera Index {index} ---")
    
    # Force V4L2 backend (standard for Linux USB cams)
    cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
    
    if not cap.isOpened():
        print(f"Index {index}: Could not open.")
        return False

    # --- THE MAGIC SETTINGS ---
    # Force 640x480 resolution (Standard, easy for Pi)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Force MJPEG format (Fixes 'No Image' on many USB cams)
    # The 'fourcc' code for MJPG is 1196444237
    cap.set(cv2.CAP_PROP_FOURCC, 1196444237)
    
    # Allow camera to warm up (Auto-exposure needs time)
    print("Warming up camera for 2 seconds...")
    time.sleep(2)
    
    # Try to read a frame
    ret, frame = cap.read()
    
    if ret:
        filename = f"success_cam_{index}.jpg"
        cv2.imwrite(filename, frame)
        print(f"SUCCESS! Image saved to {filename}")
        cap.release()
        return True
    else:
        print("Opened successfully, but still NO IMAGE.")
        cap.release()
        return False

# Test Index 0 (The most likely candidate)
if not test_camera(0):
    # If 0 fails, try 1 (Sometimes USB cams spawn as video0 and video1)
    test_camera(1)
