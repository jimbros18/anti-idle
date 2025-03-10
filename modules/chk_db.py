from dotenv import load_dotenv
import os
import requests

load_dotenv()
token = os.getenv("TURSO_TOKEN_KEY")
url = os.getenv("TURSO_DB_URL")
# url = "https://api.turso.tech/v1/organizations/jimbros/databases/db1/execute"
query = 'SELECT * FROM client'

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
    }
payload = {
    "query": "SELECT * FROM client"
}

if not token or not url:
    raise ValueError("TURSO_TOKEN_KEY or TURSO_DB_URL not found in .env file")

def connect2db():
    try:
        # Make the API request
        response = requests.post(f"{url}/v1/query", json=payload, headers=headers)

        # Print raw response for debugging
        print("Status Code:", response.status_code)
        print("Response Text:", response.text)

        # Check if the request was successful
        if response.status_code == 200:
            try:
                tables = response.json()
                print("Data:", tables)
                return tables
            except requests.exceptions.RequestsJSONDecodeError as e:
                print(f"JSON Decode Error: {e}")
                print("Response might not be valid JSON.")
                return None
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

if __name__ == "__main__":
    connect2db()
