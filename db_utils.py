from dotenv import load_dotenv
import os
import requests
import json
from fastapi import HTTPException
from pydantic import BaseModel

# Load environment variables
load_dotenv()
DB_URL = os.getenv("DB_URL")
TBL_TOKEN_KEY = os.getenv("TBL_TOKEN_KEY")

if not TBL_TOKEN_KEY or not DB_URL:
    raise RuntimeError("❌ Missing environment variables: TBL_TOKEN_KEY or DB_URL")

headers = {
    "Authorization": f"Bearer {TBL_TOKEN_KEY}",
    "Content-Type": "application/json"
}

# Define models
class ValidationRequest(BaseModel):
    key: str
    hw_id: str
    date: str

class DeviceRegisterRequest(BaseModel):
    hw_id: str
    reg: str  # Registration date
    server_con: str  # Last server connection

def validate_key(request: ValidationRequest):
    """Validate a key and update hardware ID in the database."""
    key = request.key
    hw_id = request.hw_id
    date = request.date

    payload = {
        "requests": [
            {
                "type": "execute",
                "stmt": {
                    "sql": "SELECT * FROM licenses WHERE license_key = ?",
                    "args": [{"type": "text", "value": key}]
                }
            },
            {
                "type": "execute",
                "stmt": {
                    "sql": "UPDATE licenses SET hardware_id = ?, date_used = ? WHERE license_key = ?",
                    "args": [
                        {"type": "text", "value": hw_id},
                        {"type": "text", "value": date},
                        {"type": "text", "value": key}
                    ]
                }
            }
        ]
    }

    try:
        response = requests.post(DB_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("results", [])
        
        # Check if we got results from the SELECT query (first request)
        if not results or len(results) < 1 or not results[0].get("response", {}).get("result", {}).get("rows", []):
            raise HTTPException(status_code=404, detail="Key not found")
            
        # Get the SELECT query result (first request)
        select_result = results[0]["response"]["result"]
        col_heads = [col["name"] for col in select_result["cols"]]
        first_row = select_result["rows"][0]
        
        # Handle different row formats
        if isinstance(first_row, list) and first_row and isinstance(first_row[0], dict) and "value" in first_row[0]:
            row_values = [col["value"] for col in first_row]
        else:
            row_values = first_row
            
        row_dict = dict(zip(col_heads, row_values))
        
        # Verify the license_key exists
        license_key = row_dict.get("license_key")
        if not license_key:
            raise HTTPException(status_code=404, detail="Key not found")
            
        # Write to file
        os.makedirs("client", exist_ok=True)
        with open('client/serial_key.txt', 'w', encoding="utf-8") as file:
            file.write(str(license_key))
            
        # Return the full row
        return row_dict

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Database request failed: {str(e)}")
    except ValueError:
        raise HTTPException(status_code=500, detail="Invalid database response")
    
async def check_device_exists(hw_id: str):
    """Check if a device with the given hardware_id exists in the database."""
    payload = {
        "requests": [
            {
                "type": "execute",
                "stmt": {
                    "sql": "SELECT hardware_id, registered_at, last_server_con FROM devices WHERE hardware_id = ?",
                    "args": [{"type": "text", "value": hw_id}]
                }
            }
        ]
    }

    try:
        response = requests.post(DB_URL, headers=headers, json=payload)
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])
        if not results:
            print("🚫 No response from DB on check.")
            raise HTTPException(status_code=500, detail="Database error")

        result = results[0].get("response", {}).get("result", {})
        rows = result.get("rows", [])
        
        if rows:
            device_data = rows[0]  # [hw_id, registered_at, last_server_con]
            return {
                "exists": True,
                "hardware_id": device_data[0],
                "registered_at": device_data[1],
                "last_server_con": device_data[2]
            }
        return {"exists": False}

    except requests.exceptions.RequestException as e:
        print(f"❌ Database request failed in check: {e}")
        raise HTTPException(status_code=500, detail="Database request failed")
    except ValueError:
        print(f"❌ Invalid JSON response in check: {response.text}")
        raise HTTPException(status_code=500, detail="Invalid database response")

async def register_device(request: DeviceRegisterRequest):
    hw_id = request.hw_id
    reg = request.reg
    server_con = request.server_con
    
    device_check = await check_device_exists(hw_id)
    
    if device_check["exists"]:
        return {
            "server message": "Device already registered",
            "hardware_id": device_check["hardware_id"],
            "registered_at": device_check["registered_at"],
            "last_server_con": device_check["last_server_con"]
        }

    payload = {
        "requests": [
            {
                "type": "execute",
                "stmt": {
                    "sql": """
                        INSERT OR IGNORE INTO devices (hardware_id, registered_at, last_server_con) 
                        VALUES (?, ?, ?)
                    """,
                    "args": [
                        {"type": "text", "value": hw_id},
                        {"type": "text", "value": reg},
                        {"type": "text", "value": server_con}
                    ]
                }
            }
        ]
    }

    try:
        print(f"📤 Sending to {DB_URL}: {json.dumps(payload, indent=2)}")
        response = requests.post(DB_URL, headers=headers, json=payload)
        response.raise_for_status()

        try:
            data = response.json()
            results = data.get("results", [])
            if not results:
                print("🚫 No response from DB.")
                raise HTTPException(status_code=500, detail="Database error")
            
            return {
                "server message": "Device registered successfully",
                # "hardware_id": hw_id,
                # "registered_at": reg,
                # "last_server_con": server_con
            }
        
        except ValueError:
            print(f"❌ Invalid JSON response: {response.text}")
            raise HTTPException(status_code=500, detail="Invalid database response")

    except requests.exceptions.RequestException as e:
        print(f"❌ Database request failed: {e}")
        raise HTTPException(status_code=500, detail="Database request failed")
    
class HW_ID_REQ(BaseModel):
    hw_id: str
    date: str

async def server_lastcon(request: HW_ID_REQ):
    hw_id = request.hw_id
    date = request.date
    payload = {
            "requests": [
                {
                    "type": "execute",
                    "stmt": {
                            "sql": "UPDATE devices SET last_server_con = ? WHERE hardware_id = ?",
                        "args": [
                                {"type": "text", "value": date},
                                {"type": "text", "value": hw_id}
                       ]
                    }
                },
                {
                    "type": "query",
                    "stmt": {
                        "sql": "SELECT * FROM devices WHERE hardware_id = ?",
                        "args": [{"type": "text", "value": hw_id}]
                    }
                }
            ]
        }
    try:
        response = requests.post(DB_URL, headers=headers, json=payload)
        response.raise_for_status()
        try:
            data = response.json()
            print(data)
            results = data.get("results", [])
            if not results:
                print("🚫 No response from DB.")
                raise HTTPException(status_code=500, detail="Database error")
            
            # device = results[1].get("results", [])[0]  # Assumes second query gives data
            # if len(results) < 2 or not results[1].get("results"):
            #     print("🚫 No data returned from SELECT query")
            #     raise HTTPException(status_code=500, detail="No data returned")
            
            return {
                "server message": "Last server connection updated!",
                "device": results
            }
                
        except ValueError:
            print(f"❌ Invalid JSON response: {response.text}")
            raise HTTPException(status_code=500, detail="Invalid database response")

    except requests.exceptions.RequestException as e:
        print(f"❌ Database request failed: {e}")
        raise HTTPException(status_code=500, detail="Database request failed")