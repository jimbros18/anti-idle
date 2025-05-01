from dotenv import load_dotenv
import os
import requests
import json
from fastapi import HTTPException, Request
from pydantic import BaseModel
import ast
import re

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

# class Key_Id(BaseModel):
#     key : str
#     hw_id : str

def find_key_id(key: str, hw_id: str):
    # hw_id = request.hw_id
    # key = request.key
    print(f'find_id: {hw_id}')
    print(f'find_key: {key}')

    payload = {
            "requests": [
                {
                    "type": "execute",
                    "stmt": {
                        "sql": "SELECT * FROM licenses WHERE license_key = ? AND hardware_id = ?",
                        "args": [{"type": "text", "value":key},
                                {"type": "text", "value":hw_id}]
                    }
                }
            ]
        }
    try:
        response = requests.post(DB_URL, headers=headers, json=payload)
        response.raise_for_status()
        try:
            data = response.json()
            # print(data)
            results = data.get("results", [])

            if not results or results[0].get("type") != "ok":
                raise HTTPException(status_code=500, detail="Database error")

            select_result = results[0]["response"]["result"]

            cols = [col["name"] for col in select_result["cols"]]
            rows = select_result.get("rows", [])

            if not rows:
                print({'status': "trial", 'key': 'None'})
                return {'status': "trial", 'key': 'None'}
                    
            # extract the first row
            row = rows[0]
            info = {cols[i]: cell.get("value") for i, cell in enumerate(row)}
            if info['license_key'] == key and info['hardware_id'] == hw_id:
                print({'status': "licensed", 'key': info['license_key']})
                return {'status': "licensed", 'key': info['license_key']}
            
        except ValueError:
            print(f"❌ Invalid JSON response: {response.text}")
            raise HTTPException(status_code=500, detail="Invalid database response")

    except requests.exceptions.RequestException as e:
        print(f"❌ Database request failed: {e}")
        print(f"Response body: {response.text}")
        raise HTTPException(status_code=500, detail="Database request failed")

def check_license(key:str): # finds license_key if it exist
    print(f'chec license: {key}')
    payload = {
            "requests": [
                {
                    "type": "execute",
                    "stmt": {
                        "sql": "SELECT * FROM licenses WHERE license_key = ?",
                        "args": [{"type": "text", "value":key}]
                    }
                }
            ]
        }
    try:
        response = requests.post(DB_URL, headers=headers, json=payload)
        response.raise_for_status()
        try:
            data = response.json()
            results = data.get("results", [])

            if not results or results[0].get("type") != "ok":
                raise HTTPException(status_code=500, detail="Database error")

            select_result = results[0]["response"]["result"]

            cols = [col["name"] for col in select_result["cols"]]
            rows = select_result.get("rows", [])
            # print(f'rows: {rows}')

            if not rows:
                print({'key': "invalid"})
                return {'key': "invalid"}
                    
            # extract the first row
            row = rows[0]
            info = {cols[i]: cell.get("value") for i, cell in enumerate(row)}
            if info['license_key'] == key:
                print({'key': "valid"})
                return {'key': "valid"}
            
            # return {rows}

        except ValueError:
            print(f"❌ Invalid JSON response: {response.text}")
            raise HTTPException(status_code=500, detail="Invalid database response")

    except requests.exceptions.RequestException as e:
        print(f"❌ Database request failed: {e}")
        print(f"Response body: {response.text}")
        raise HTTPException(status_code=500, detail="Database request failed")
class ValidationRequest(BaseModel):
    key: str
    hw_id: str
    date: str

def validate_key(key: str, hw_id: str, date: str):
    print(f"validate_key: key={key}")
    payload = {
        "requests": [
            {"type": "execute", "stmt": {"sql": "SELECT * FROM licenses WHERE license_key = ?", "args": [{"type": "text", "value": key}]}},
            {"type": "execute", "stmt": {"sql": "SELECT * FROM licenses WHERE hardware_id = ?", "args": [{"type": "text", "value": hw_id}]}}
        ]
    }
    try:
        response = requests.post(DB_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        if not results or results[0].get("type") != "ok":
            print(f"validate_key: SELECT key failed: {results}")
            raise HTTPException(status_code=404, detail="Invalid key")
        
        # Check license key
        select_result = results[0]["response"]["result"]
        rows = select_result.get("rows", [])
        if not rows:
            print({'status': 'trial', 'key': 'None'})
            return {'status': 'trial', 'key': 'None'}
        cols = [col["name"] for col in select_result["cols"]]
        info = {cols[i]: cell.get("value") for i, cell in enumerate(rows[0])}
        print(f"validate_key: License={info}")
        
        # Check hardware_id conflict
        if len(results) > 1 and results[1].get("type") == "ok":
            hw_result = results[1]["response"]["result"]
            hw_rows = hw_result.get("rows", [])
            if hw_rows and hw_rows[0][cols.index("license_key")]["value"] != key:
                print(f"validate_key: hardware_id={hw_id} already used by another key")
                raise HTTPException(status_code=400, detail="Hardware ID already bound to another license")
        
        if info.get('hardware_id') and info['hardware_id'] != hw_id:
            print({'status': 'trial', 'key': 'None'})
            return {'status': 'trial', 'key': 'None'}
        
        if info.get('hardware_id') is None:
            print(f"validate_key: Updating hw_id={hw_id}, date={date}")
            update_payload = {
                "requests": [{"type": "execute", "stmt": {
                    "sql": "UPDATE licenses SET hardware_id = ?, is_active = 1, date_used = ? WHERE license_key = ?",
                    "args": [{"type": "text", "value": hw_id}, {"type": "text", "value": date}, {"type": "text", "value": key}]
                }}]
            }
            update_response = requests.post(DB_URL, headers=headers, json=update_payload, timeout=10)
            update_response.raise_for_status()
            update_data = update_response.json()
            print(f"validate_key: Update response={update_data}")
            if not update_data.get("results", []) or update_data["results"][0].get("type") != "ok":
                error = update_data.get("results", [{}])[0].get("error", "Unknown error")
                print(f"validate_key: Update failed: {error}")
                raise HTTPException(status_code=500, detail=f"Update failed: {error}")
        
        print({'status': 'licensed', 'key': key})
        return {'status': 'licensed', 'key': key}
    except requests.exceptions.RequestException as e:
        print(f"validate_key error: DB request failed: {e}")
        raise HTTPException(status_code=500, detail=f"DB request failed: {e}")
    except ValueError as e:
        print(f"validate_key error: Invalid response: {e}")
        raise HTTPException(status_code=500, detail=f"Invalid DB response: {e}")
    
async def check_device_exists(hw_id: str):
    """Check if a device with the given hardware_id exists in the database."""
    payload = {
        "requests": [
            {
                "type": "execute",
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
                "id": device_data[0]['value'],
                "hardware_id": device_data[1]['value'],
                "registered_at": device_data[2]['value'],
                "last_server_con": device_data[3]['value']
            }
        return {"exists": False}

    except requests.exceptions.RequestException as e:
        print(f"❌ Database request failed in check: {e}")
        raise HTTPException(status_code=500, detail="Database request failed")
    except ValueError:
        print(f"❌ Invalid JSON response in check: {response.text}")
        raise HTTPException(status_code=500, detail="Invalid database response")
class DeviceRegisterRequest(BaseModel):
    hw_id: str
    date: str  # Registration date
    # server_con: str  # Last server connection

async def register_device(request: DeviceRegisterRequest):
    hw_id = request.hw_id
    user_date = request.date
    # server_con = request.server_con
    
    dev_data= await check_device_exists(hw_id)
    
    if dev_data["exists"]:
        device_data = {
            "id": dev_data["id"],
            "hardware_id": dev_data["hardware_id"],
            "registered_at": dev_data["registered_at"],
            "last_server_con": dev_data["last_server_con"],
        }
        return {
            "server message": "Device already registered",
            "data": device_data
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
                    {"type": "text", "value": user_date},
                    {"type": "text", "value": user_date}
                ]
            }
        },
        {
            "type": "execute",
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
            results = data.get("results", [])
            if not results or len(results) < 2:
                print("🚫 No response from DB.")
                raise HTTPException(status_code=500, detail="Database error")

            # Extract device data from SELECT query (second request)
            select_result = results[1]["response"]["result"]
            cols = [col["name"] for col in select_result["cols"]]
            row = select_result["rows"][0]
            device_data = {
                cols[i]: value["value"] for i, value in enumerate(row)
            }

            return {
                "server message": "Device registered successfully",
                "data": device_data
            }
        
        except ValueError:
            print(f"❌ Invalid JSON response: {response.text}")
            raise HTTPException(status_code=500, detail="Invalid database response")

    except requests.exceptions.RequestException as e:
        print(f"❌ Database request failed: {e}")
        print(f"Response body: {response.text}")
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
                    "type": "execute",
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
            results = data.get("results", [])
            if not results:
                print("🚫 No response from DB.")
                raise HTTPException(status_code=500, detail="Database error")
            
            if len(results) < 2 or not results[1].get("response", {}).get("result", {}).get("rows"):
                print("🚫 No data returned from SELECT query")
                raise HTTPException(status_code=404, detail="Device not found")

            # Extract device data
            select_result = results[1]["response"]["result"]
            cols = [col["name"] for col in select_result["cols"]]  # Get column names
            row = select_result["rows"][0]  # Get first row
            device_data = {
                cols[i]: value["value"] for i, value in enumerate(row)
            }
            
            return {
                "server message": "Last server connection updated!",
                "data": device_data
            }
                
        except ValueError:
            print(f"❌ Invalid JSON response: {response.text}")
            raise HTTPException(status_code=500, detail="Invalid database response")

    except requests.exceptions.RequestException as e:
        print(f"❌ Database request failed: {e}")
        print(f"Response body: {response.text}")
        raise HTTPException(status_code=500, detail="Database request failed")


