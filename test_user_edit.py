import requests
import json

base_url = "http://localhost:8001"
# We need to find a user to edit. Let's assume ID 1 exists (usually superadmin)
user_id = 1

print(f"Testing PUT update for User ID {user_id}...")

payload = {
    "first_name": "Antigravity",
    "last_name": "Tester",
    "email": "tester@example.com"
}

headers = {
    "X-User-Email": "superadmin@example.com",
    "X-User-Name": "Super Admin",
    "Content-Type": "application/json"
}

try:
    # First, let's GET the current data
    resp_get = requests.get(f"{base_url}/api/org-users/{user_id}/", headers=headers)
    print("Current Data:", resp_get.json())

    # Now, Update
    resp = requests.put(f"{base_url}/api/org-users/{user_id}/", json=payload, headers=headers)
    print("Update Response Status:", resp.status_code)
    print("Update Response Body:", resp.json())

    if resp.status_code == 200:
        print("SUCCESS: User profile updated.")
    else:
        print("FAILED: Update rejected.")

except Exception as e:
    print(f"Error during testing: {e}")
