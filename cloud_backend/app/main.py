from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse  # <-- Added FileResponse
import json
import os
import mimetypes
from dotenv import load_dotenv
from supabase import create_client, Client

# 1. Load Keys
load_dotenv()
url = os.environ.get("SUPABASE_URL")
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

# 2. Serve the Dashboard HTML
@app.get("/")
def read_root():
    # Looks for index.html in the exact same folder as main.py
    return FileResponse("index.html")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not supabase:
        return JSONResponse(content={"error": "Database not connected"}, status_code=500)

    print(f"   [Upload] Receiving: {file.filename}")
    
    try:
        # 1. Read file
        file_bytes = await file.read()
        
        # 2. Detect proper file type (Video vs Image)
        content_type, _ = mimetypes.guess_type(file.filename)
        if not content_type:
            content_type = "application/octet-stream"
            
        # 3. Upload with original filename (so we verify history)
        # We use 'upsert=true' to overwrite if the name is identical
        try:
            supabase.storage.from_("doorbell_images").upload(
                path=file.filename, 
                file=file_bytes, 
                file_options={"content-type": content_type, "upsert": "true"}
            )
        except Exception as upload_err:
            print(f"   [Supabase] Note: {upload_err}")

        # 4. Get the Link
        public_url = supabase.storage.from_("doorbell_images").get_public_url(file.filename)
        print(f"   [Cloud] Saved to: {public_url}")

        return {"status": "success", "url": public_url}

    except Exception as e:
        print(f"   [Upload Error] {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Broadcast alerts to all connected dashboards
            for client in connected_clients:
                if client != websocket:
                    await client.send_text(data)
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
