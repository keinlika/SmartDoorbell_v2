import os
import secrets
from supabase import create_client
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BACKEND_DIR, ".env")

# 1. Load secrets from .env
load_dotenv(dotenv_path=ENV_PATH)

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


def get_device_id():
    return os.environ.get("DOORBELL_DEVICE_ID", get_serial())


def read_device_record(device_id: str):
    response = supabase.table("devices").select("*").eq("device_id", device_id).limit(1).execute()
    records = response.data or []
    return records[0] if records else None


def resolve_device_token(existing_record: dict | None) -> tuple[str, str]:
    if existing_record:
        token_value = existing_record.get("device_token")
        if isinstance(token_value, str) and token_value.strip():
            return token_value.strip(), "devices.device_token"

    env_token = os.environ.get("DOORBELL_DEVICE_TOKEN", "").strip()
    if env_token:
        return env_token, "env"

    return secrets.token_urlsafe(24), "generated"

# 3. Register this device
serial_id = get_device_id()
print(f"Attempting to register Device ID: {serial_id}")

data = {
    "device_id": serial_id,
    "name": os.environ.get("DOORBELL_DEVICE_NAME", "Front Door Main"),
    "status": "online"
}

try:
    existing_record = read_device_record(serial_id)
    device_token, token_source = resolve_device_token(existing_record)
    data["device_token"] = device_token

    if existing_record:
        try:
            supabase.table("devices").update(data).eq("device_id", serial_id).execute()
        except Exception as token_error:
            fallback_data = {k: v for k, v in data.items() if k != "device_token"}
            supabase.table("devices").update(fallback_data).eq("device_id", serial_id).execute()
            print(f"SUCCESS! Device registration updated without token column support: {token_error}")
        else:
            print(f"SUCCESS! Device registration updated in cloud using token from {token_source}.")
    else:
        try:
            supabase.table("devices").insert(data).execute()
        except Exception as token_error:
            fallback_data = {k: v for k, v in data.items() if k != "device_token"}
            supabase.table("devices").insert(fallback_data).execute()
            print(f"SUCCESS! Device registered without token column support: {token_error}")
        else:
            print(f"SUCCESS! Device registered in cloud using token from {token_source}.")
    print(f"DEVICE_TOKEN={device_token}")
except Exception as e:
    print(f"Error: {e}")
