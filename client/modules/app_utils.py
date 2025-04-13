import requests
import wmi
from datetime import datetime
import ctypes
import os
import ast

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

hw_id = get_hardware_ids()

def check_cache():
    print('SEARCHING CACHE ON START')
    cache = read_cache()
    if cache:
        data = update_lastcon()
        print('UPDATING SERVER')
        read_cache(data)
        return cache
    else:
        register_device()

def set_hidden_windows(file_path):
    """Set the hidden attribute on Windows."""
    try:
        ctypes.windll.kernel32.SetFileAttributesW(file_path, 2)  # 2 = FILE_ATTRIBUTE_HIDDEN
        print(f"Set {file_path} as hidden", flush=True)
    except Exception as e:
        print(f"Error hiding file: {e}", flush=True)

def read_cache(data=None):
    try:
        if not os.path.isfile(TRIAL_FILE) and data is None:
            os.makedirs(os.path.dirname(TRIAL_FILE), exist_ok=True)
            with open(TRIAL_FILE, "w", encoding="utf-8") as f:
                f.write("")
            print("CACHE NOT FOUND..... CACHE CREATED.")
            return None
        
        if data is not None: #has data
            print("WRITING DATA TO CACHE")
            with open(TRIAL_FILE, "w", encoding="utf-8") as f:
                f.write(f"{data}")

        print("READING CACHE")
        with open(TRIAL_FILE, "r", encoding="utf-8") as f:
            txt_content = f.read()

        print(f"CACHE CONTENT: {txt_content}")
        return txt_content if txt_content else None
    
    except PermissionError as e:
        print(f"Irur: Permission denied at {TRIAL_FILE}. Operation: {e}")
        return None
    except Exception as e:
        print(f"Irur: Unexpected error: {e}")
        return None

def register_device():
    API_URL = "http://127.0.0.1:8000/reg_dev"
    # hw_id = get_hardware_ids()
    date_reg = datetime.now().isoformat()
    last_server_con = datetime.now().isoformat()

    if not hw_id:
        print("❌ Failed to generate hardware ID")
        return None

    payload = {"hw_id": hw_id, 'reg':date_reg, 'server_con': last_server_con}

    try:
        response = requests.post(API_URL, json=payload, timeout=5)
        response.raise_for_status()  # Raises an error for HTTP issues

        try:
            data = response.json()
            if data:
                read_cache(data)
            return data
        
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
    hw_id: str = get_hardware_ids()
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

def check_trial():
    with open(TRIAL_FILE, "r") as file:
        content = file.read()
    data = ast.literal_eval(content)
    reg_at = data['registered_at']
    reg_date = reg_at['value']
    # reg_date ='2025-03-31T21:48:32.999104'
    dt_obj = datetime.fromisoformat(reg_date)
    now = datetime.now()
    time_diff = now - dt_obj
    if time_diff.days >= 14:
        print(f'{time_diff} days passed, trial has expired.')
    else:
        print(f'{time_diff} TRIAL ACTIVE')
