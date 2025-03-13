import requests
import wmi

def connect(key):
    API_URL = "http://127.0.0.1:8000/validate"
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

def get_hardware_ids():
    try:
        c = wmi.WMI()
        hardware_info = {}
        
        for board in c.Win32_BaseBoard():
            hardware_info['Motherboard_ID'] = board.SerialNumber.strip() if board.SerialNumber else "Not Available"
        for cpu in c.Win32_Processor():
            hardware_info['CPU_ID'] = cpu.ProcessorId.strip() if cpu.ProcessorId else "Not Available"
        ram_ids = [ram.SerialNumber.strip() if ram.SerialNumber else "Not Available" for ram in c.Win32_PhysicalMemory()]
        hardware_info['RAM_IDs'] = ram_ids if ram_ids else ['Not Available']
        disk_ids = [disk.SerialNumber.strip() if disk.SerialNumber else "Not Available" for disk in c.Win32_DiskDrive()]
        hardware_info['Disk_IDs'] = disk_ids if disk_ids else ['Not Available']
        for bios in c.Win32_BIOS():
            hardware_info['BIOS_ID'] = bios.SerialNumber.strip() if bios.SerialNumber else "Not Available"
        net_ids = [net.MACAddress.strip() for net in c.Win32_NetworkAdapter() if net.MACAddress]
        hardware_info['Network_IDs'] = net_ids if net_ids else ['Not Available']
        gpu_ids = [gpu.PNPDeviceID.strip() if gpu.PNPDeviceID else "Not Available" for gpu in c.Win32_VideoController()]
        hardware_info['GPU_IDs'] = gpu_ids if gpu_ids else ['Not Available']
        
        if not hardware_info:
            return None
        
        joined_hw_id = "|".join(
            str(value) if not isinstance(value, list) else ";".join(map(str, value))
            for value in hardware_info.values()
        )
        print("Generated hw_id:", joined_hw_id)
        return joined_hw_id

    except Exception as e:
        print(f"Error retrieving hardware IDs: {e}")
        return None

if __name__ == "__main__":
    result = connect(123)
    print(f"Result: {result}")