from dotenv import load_dotenv
import os
import requests
import json

load_dotenv()
token = os.getenv("TBL_TOKEN_KEY")
url = os.getenv("DB_URL")


headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
    }


def connect2db(serialkey):
    print(serialkey) # ex: 1
    try:
        payload = {
            "requests": [
                {
                    "type": "execute",
                    "stmt": {
                        "sql": "SELECT * FROM anti_idle_app WHERE id = ?",
                        "args": [{"type": "integer", "value": f'{serialkey}'}]
                    }
                }
            ]
        }

        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        data = response.json()

        # Validate response structure
        results = data.get("results", [])
        if not results:
            print("No results found in API response.")
            return None  # Return None if no results

        first_result = results[0].get("response", {}).get("result", {})
        cols = first_result.get("cols", [])
        rows_data = first_result.get("rows", [])

        if not rows_data:
            print("No matching row found.")
            return None  # Return None if no matching row

        # Extract headers
        col_heads = [col["name"] for col in cols]

        # Extract the first (and only) row
        first_row = rows_data[0]
        row_values = [col["value"] for col in first_row]

        # Return as a dictionary
        row_dict = dict(zip(col_heads, row_values))

        with open('serial_key.txt', 'w', encoding="utf-8") as file:
            file.write(row_dict["s_key"])

        print("s_key:", row_dict['s_key'])
        return row_dict['s_key']  # Return a single row as a dictionary

    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        return None  # Return None if request fails


def find_txt():
    file_path = 'serial_key.txt'
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            return content