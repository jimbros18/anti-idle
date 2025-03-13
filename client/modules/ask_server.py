import requests

def connect(key):
    API_URL = f"http://127.0.0.1:8000/validate/{key}"
    
    try:
        response = requests.get(API_URL)
        response.raise_for_status()  # 🚀 Raise error for 4xx/5xx responses

        data = response.json()
        
        # ✅ Check if 's_key' exists in response
        if "s_key" in data:
            print(f"✅ Key is valid! Serial Key: {data['s_key']}")
            return data["s_key"]  # Return the actual serial key
        
        print("❌ Key not found in response!")
        return None  # Return None for missing keys

    except requests.exceptions.RequestException as e:
        print(f"❌ Server Error: {e}")
        return None  # Return None on request failure
