import os
from supabase import create_client
from dotenv import load_dotenv

# 1. Load secrets from .env
load_dotenv()

# 2. Connect to Cloud
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

def get_serial():
    """Gets the unique hardware ID of the Raspberry Pi"""
    cpuserial = "0000000000000000"
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line.startswith('Serial'):
                    cpuserial = line.split(':')[1].strip()
    except:
        cpuserial = "TEST_DEVICE_001"
    return cpuserial

# 3. Register this device
serial_id = get_serial()
print(f"Attempting to register Device ID: {serial_id}")

data = {
    "device_id": serial_id,
    "name": "Front Door Main",
    "status": "online"
}

try:
    # Insert into the 'devices' table
    response = supabase.table("devices").insert(data).execute()
    print("SUCCESS! Device registered in cloud.")
except Exception as e:
    print(f"Error: {e}")
