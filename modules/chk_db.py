from dotenv import load_dotenv
import os
import requests
import json

load_dotenv()
token = os.getenv("TURSO_TOKEN_KEY")
url = os.getenv("TURSO_DB_URL")
# query = 'SELECT * FROM client'

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
    }

payload = {
    "requests": [
        {
            "type": "execute",
            "stmt": {
                "sql": "SELECT * FROM client"
            }
        }
    ]
}

def connect2db():
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        data = response.json()

        col_heads = [col["name"] for col in data["results"][0]["response"]["result"]["cols"]]
        rows = data["results"][0]["response"]["result"]["rows"]

        print("Headers:",col_heads)

        for index, row in enumerate(rows):
            values = [col["value"] for col in row]
            print(f"Row {index + 1}: ", values)

    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
