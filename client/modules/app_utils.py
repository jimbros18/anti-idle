import requests
import wmi
from datetime import datetime
import ctypes
import os
import ast
import json

TRIAL_FILE = "client/cache.txt"


def get_hardware_ids():
    try:
        c = wmi.WMI()
        hardware_ids = []
        
        # Motherboard
        for board in c.Win32_BaseBoard():
            hardware_ids.append(board.SerialNumber.strip() if board.SerialNumber else "Not Available")
        
        # CPU
        for cpu in c.Win32_Processor():
            hardware_ids.append(cpu.ProcessorId.strip() if cpu.ProcessorId else "Not Available")
        
        # RAM
        ram_ids = [ram.SerialNumber.strip() if ram.SerialNumber else "Not Available" for ram in c.Win32_PhysicalMemory()]
        hardware_ids.extend(ram_ids if ram_ids else ["Not Available"])
        
        # Disk
        disk_ids = [disk.SerialNumber.strip() if disk.SerialNumber else "Not Available" for disk in c.Win32_DiskDrive()]
        hardware_ids.extend(disk_ids if disk_ids else ["Not Available"])
        
        # BIOS
        for bios in c.Win32_BIOS():
            hardware_ids.append(bios.SerialNumber.strip() if bios.SerialNumber else "Not Available")
        
        # Network
        net_ids = [net.MACAddress.strip() for net in c.Win32_NetworkAdapter() if net.MACAddress]
        hardware_ids.extend(net_ids if net_ids else ["Not Available"])
        
        # GPU
        gpu_ids = [gpu.PNPDeviceID.strip() if gpu.PNPDeviceID else "Not Available" for gpu in c.Win32_VideoController()]
        hardware_ids.extend(gpu_ids if gpu_ids else ["Not Available"])
        
        if not hardware_ids:
            return None
        
        # Join all IDs with '|'
        joined_hw_id = "|".join(hardware_ids)
        # print("Generated hw_id:", joined_hw_id)
        return joined_hw_id

    except Exception as e:
        print(f"Error retrieving hardware IDs: {e}")
        return None

    except Exception as e:
        print(f"Error retrieving hardware IDs: {e}")
        return None

def read_cache(data=None):
    try:
        if not os.path.isfile(TRIAL_FILE) and data is None:
            os.makedirs(os.path.dirname(TRIAL_FILE), exist_ok=True)
            with open(TRIAL_FILE, "w", encoding="utf-8") as f:
                f.write("")  # Create an empty cache file if not present
            print("CACHE NOT FOUND..... CACHE CREATED.")
            return None
        
        if data is not None:  # has data
            print("WRITING DATA TO CACHE")
            with open(TRIAL_FILE, "w", encoding="utf-8") as f:
                # Serialize the data to JSON before writing to the file
                json.dump(data, f)  # Write as JSON

        print("READING CACHE")
        with open(TRIAL_FILE, "r", encoding="utf-8") as f:
            txt_content = f.read()

        print(f"CACHE CONTENT: {txt_content}")
        
        if txt_content:
            # Deserialize the JSON content back to Python objects
            return json.loads(txt_content)
        else:
            return None
    
    except PermissionError as e:
        print(f"Permission denied at {TRIAL_FILE}. Operation: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

hw_id = get_hardware_ids()
cache = read_cache()
date = datetime.now().isoformat()

def check_cache():
    if cache is not None:
        data = update_lastcon()
        print('UPDATING SERVER')
        new_cache = read_cache(data)
        return count_days(new_cache)
    else:
        return register_device()
        
def set_hidden_windows(file_path):
    """Set the hidden attribute on Windows."""
    try:
        ctypes.windll.kernel32.SetFileAttributesW(file_path, 2)  # 2 = FILE_ATTRIBUTE_HIDDEN
        print(f"Set {file_path} as hidden", flush=True)
    except Exception as e:
        print(f"Error hiding file: {e}", flush=True)

def register_device():
    API_URL = "http://127.0.0.1:8000/reg_dev"
    date_now = datetime.now().isoformat()

    if not hw_id:
        print("❌ Failed to generate hardware ID")
        return None

    payload = {"hw_id": hw_id, 'date':date_now}

    try:
        response = requests.post(API_URL, json=payload, timeout=5)
        response.raise_for_status()  # Raises an error for HTTP issues

        try:
            data = response.json()
            if data:
               content =  read_cache(data)
               return count_days(content)
        
        except ValueError:
            print("❌ Invalid JSON response from server!")
            return None
        
    except requests.exceptions.Timeout:
        print("❌ register timed out")
        return None
    
    except requests.exceptions.RequestException as e:
        print(f"❌register Server Error: {e}")
        return None

def update_lastcon():
    # hw_id: str = get_hardware_ids()
    user_date = datetime.now().isoformat()
    if hw_id is None:
        print("❌ Failed to get hardware IDs")
        return None
    
    API_URL = "http://127.0.0.1:8000/lastcon"
    payload = {"hw_id": hw_id, "date": user_date}
    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        return data
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Server Error: {e}")
        return None
    
def validate_key(key):
    API_URL = "http://127.0.0.1:8000/validate"
    # hw_id = get_hardware_ids()
    date = datetime.now().isoformat()
    
    if hw_id is None:
        print("❌ Failed to generate hardware ID")
        return None

    # Payload with key and hw_id
    payload = {
        "key": key,
        "hw_id": hw_id,
        "date": date
    }
    
    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        
        if "s_key" in data:
            print(f"Serial Key valid: {data['s_key']}")
            print(f"Hardware IDs: {hw_id}")
            info = {"key": data['s_key'], "id": hw_id}
            return info
        
        print("❌ Key not found in response!")
        return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Server Error: {e}")
        return None

def count_days(cache):
    if cache is not None:
        # data_dict = cache['data']
        reg_at = cache['data']['registered_at']
        dt_obj = datetime.fromisoformat(reg_at)
        now = datetime.now()
        time_diff = now - dt_obj
        print(time_diff.days)
        return time_diff.days
    else:
        print('CACHE IS NONE')
        return None

def check_license(key):
    API_URL = "http://127.0.0.1:8000/license"
    hw_id = get_hardware_ids()
    if hw_id is None:
        print("❌ Failed to generate hardware ID")
        return None

    # Payload with key and hw_id
    payload = {
        "key": key,
        "hw_id": hw_id
    }
    
    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        print(data)
        
        # if "license_key" in data:
        #     print(f"LIC_KEY: {data['license_key']}")
        #     return data
        
        # print("❌ Key not found in response!")
        # return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Server Error: {e}")
        return None
