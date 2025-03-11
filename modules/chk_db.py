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
                        "sql": "SELECT * FROM anti_idle_app WHERE s_key = ?",
                        "args": [{"type": "text", "value": f'{serialkey}'}]
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

        print("Row Data:", row_dict)
        return row_dict  # Return a single row as a dictionary

    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        return None  # Return None if request fails


# DROP TABLE IF EXISTS anti_idle_app;

# CREATE TABLE anti_idle_app (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     name TEXT,
#     address TEXT,
#     email TEXT,
#     contact_number INTEGER,
#     sub_type TEXT,
#     s_key TEXT,
#     hw_id TEXT,
#     mc_ad TEXT,
#     act_date DATE,
#     xp_date DATE
# );

# INSERT INTO anti_idle_app (s_key, hw_id, mc_ad, act_date, xp_date, sub_type, name, address, email, contact_number) VALUES
# ('A1B2C3D4E5F6G7H', 'HW1234567890', '00:1A:2B:3C:4D:5E', '2025-03-11', '2025-04-11', 'Monthly', 'John Doe', '123 Main St, Manila', 'john.doe@example.com', '+639171234567'),
# ('Z9Y8X7W6V5U4T3S', 'HW0987654321', '00:1B:2C:3D:4E:5F', '2025-02-10', '2026-02-10', 'Yearly', 'Jane Smith', '456 Side St, Cebu', 'jane.smith@example.com', '+639189876543'),
# ('M1N2B3V4C5X6Z7Y', 'HW1122334455', '00:1C:2D:3E:4F:5G', '2025-01-15', '2025-02-15', 'Monthly', 'Alice Brown', '789 Corner St, Davao', 'alice.brown@example.com', '+639123456789');
