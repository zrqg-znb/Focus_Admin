import requests
import json
from datetime import date, timedelta
import random

# API Base URL
BASE_URL = "http://127.0.0.1:8000/api"

# Login Credentials (Assuming default admin/admin or create a new user if needed)
# Please update if you have specific credentials
USERNAME = "admin" 
PASSWORD = "password" if False else "123456"


# Indicator Data
INDICATOR_CODE = "TEST_01_ZRQ"
INDICATOR_DATA = {
    "code": "TEST_01_ZRQ",
    "name": "test01",
    "project": "A66",
    "module": "RAM",
    "chip_type": "NN84",
    "value_type": "avg", # Assuming avg based on description
    "baseline_value": 100.2,
    "baseline_unit": "byte",
    "fluctuation_range": 5,
    "fluctuation_direction": "down",
    # owner_id needs to be fetched or assumed current user
}

def login():
    url = f"{BASE_URL}/core/login"
    payload = {
        "username": USERNAME,
        "password": PASSWORD
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        print(f"Login successful. Token: {data['accessToken'][:10]}...")
        return data['accessToken'], data['id']
    except Exception as e:
        print(f"Login failed: {e}")
        if 'response' in locals():
            print(f"Response: {response.text}")
        return None, None

def ensure_indicator_exists(token, owner_id):
    # Search by filtering project, module, chip_type
    query_params = f"project={INDICATOR_DATA['project']}&module={INDICATOR_DATA['module']}&chip_type={INDICATOR_DATA['chip_type']}"
    url = f"{BASE_URL}/performance/indicators?{query_params}"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data['items']:
            for item in data['items']:
                if item['name'] == INDICATOR_DATA['name']:
                    print(f"Indicator {INDICATOR_DATA['name']} already exists. ID: {item['id']}")
                    return item['id']
    
    # Create if not exists
    print(f"Creating indicator {INDICATOR_CODE}...")
    create_url = f"{BASE_URL}/performance/indicators"
    payload = INDICATOR_DATA.copy()
    payload['owner_id'] = owner_id # Set current user as owner
    
    response = requests.post(create_url, json=payload, headers=headers)
    if response.status_code == 200:
        print("Indicator created successfully.")
        return response.json()['id']
    else:
        print(f"Failed to create indicator: {response.text}")
        return None

def upload_data(token):
    url = f"{BASE_URL}/performance/data/upload"
    headers = {"Authorization": f"Bearer {token}"}
    
    # Generate some dummy data for the last 7 days
    today = date.today()
    
    # We will upload data for 3 different days
    for i in range(3):
        data_date = today - timedelta(days=i)
        
        # Generate a value around the baseline (100.2)
        # Random value between 90 and 110
        value = round(random.uniform(90, 110), 2)
        
        payload = {
            "project": INDICATOR_DATA["project"],
            "module": INDICATOR_DATA["module"],
            "chip_type": INDICATOR_DATA["chip_type"],
            "date": data_date.isoformat(),
            "data": [
                {
                    "code": INDICATOR_CODE,
                    "name": INDICATOR_DATA["name"],
                    "value": value
                }
            ]
        }
        
        print(f"Uploading data for {data_date}: Value={value}")
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            print(f"Upload success: {response.json()}")
        else:
            print(f"Upload failed: {response.text}")

if __name__ == "__main__":
    token, user_id = login()
    if token:
        # 1. Ensure indicator exists
        indicator_id = ensure_indicator_exists(token, user_id)
        
        if indicator_id:
            # 2. Upload data
            upload_data(token)
