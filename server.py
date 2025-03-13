from dotenv import load_dotenv
import os
import requests
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel  # For type validation

app = FastAPI()

# Define a model for the expected request body
class ValidationRequest(BaseModel):
    key: int
    hw_id: str

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

@app.post("/validate")  # Changed to POST to accept a body
def validate_key(request: ValidationRequest):  # Use the model for the request body
    key = request.key
    hw_id = request.hw_id
    print(f"🔍 Checking Key: {key}, Hardware ID: {hw_id}")

    payload = {
        "requests": [
            {
                "type": "execute",
                "stmt": {
                    "sql": "SELECT * FROM anti_idle_app WHERE id = ?",
                    "args": [{"type": "integer", "value": str(key)}]
                }
            },
            {
                "type": "execute",
                "stmt": {
                    "sql": "UPDATE anti_idle_app SET hw_id = ? WHERE id = ?",
                    "args": [
                        {"type": "text", "value": hw_id},  # Use the client-provided hw_id
                        {"type": "integer", "value": str(key)}
                    ]
                }
            }
        ]
    }

    try:
        print(f"📤 Sending to {DB_URL}: {json.dumps(payload, indent=2)}")
        print(f"📤 Headers: {headers}")
        response = requests.post(DB_URL, headers=headers, json=payload)
        print(f"📥 Response: {response.text}")
        response.raise_for_status()

        try:
            data = response.json()
        except ValueError:
            print(f"❌ Invalid JSON response: {response.text}")
            raise HTTPException(status_code=500, detail="Invalid database response")

        results = data.get("results", [])
        if not results:
            print("🚫 No results found.")
            raise HTTPException(status_code=404, detail="Key not found")

        first_result = results[0].get("response", {}).get("result", {})
        cols = first_result.get("cols", [])
        rows_data = first_result.get("rows", [])

        if not rows_data:
            print("🚫 No matching row found.")
            raise HTTPException(status_code=404, detail="Key not found")

        col_heads = [col["name"] for col in cols]
        first_row = rows_data[0]
        row_values = [col["value"] for col in first_row]

        row_dict = dict(zip(col_heads, row_values))
        serial_key = row_dict.get("s_key", "UNKNOWN")

        if serial_key != "UNKNOWN":
            os.makedirs("client", exist_ok=True)
            with open('client/serial_key.txt', 'w', encoding="utf-8") as file:
                file.write(str(serial_key))

        print("✅ s_key:", serial_key)
        return {"s_key": serial_key}

    except requests.exceptions.RequestException as e:
        print(f"❌ Database request failed: {e}")
        raise HTTPException(status_code=500, detail="Database request failed")