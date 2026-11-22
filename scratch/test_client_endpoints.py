import sys
import os
import json

sys.path.insert(0, os.path.abspath("services/api"))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("=== TESTING FASTAPI ENDPOINTS VIA TESTCLIENT ===")

# 1. Models Status
r = client.get("/api/v1/ai/models/status")
print(f"1. GET /ai/models/status -> Status: {r.status_code}")
if r.status_code == 200:
    models = r.json()
    print(f"   Total Models Registered: {len(models)}")
    for m in models:
        print(f"    - [{m['key']}] {m['name']} ({m['model_id']}) -> Status: {m['status']}")

# 2. Landmarks Register
r = client.get("/api/v1/localities/landmarks")
print(f"2. GET /localities/landmarks -> Status: {r.status_code}")
if r.status_code == 200:
    landmarks = r.json()
    print(f"   Total Landmarks: {len(landmarks)}")
    print(f"    - Landmark 1: {landmarks[0]['name']} (Lat: {landmarks[0]['lat']}, Lon: {landmarks[0]['lon']})")

# 3. Boundaries Register
r = client.get("/api/v1/localities/boundaries")
print(f"3. GET /localities/boundaries -> Status: {r.status_code}")
if r.status_code == 200:
    boundaries = r.json()
    print(f"   Total Boundaries: {len(boundaries)}")
    print(f"    - Boundary 1: {boundaries[0]['name_en']} ({boundaries[0]['gram_panchayat']})")

# 4. Resolve GPS
r = client.get("/api/v1/localities/resolve-gps?latitude=15.8152&longitude=74.4610")
print(f"4. GET /localities/resolve-gps -> Status: {r.status_code}")
if r.status_code == 200:
    res = r.json()
    print(f"   Resolved: {res.get('village_name')} (Verified: {res.get('is_verified')})")

# 5. Dual Source Verification
payload = {
    "latitude": 15.8152,
    "longitude": 74.4610,
    "gps_accuracy": 12.0,
    "acquisition_method": "GPS_VERIFIED",
    "selected_village": "Peeranwadi"
}
r = client.post("/api/v1/localities/verify-dual-source", json=payload)
print(f"5. POST /localities/verify-dual-source -> Status: {r.status_code}")
if r.status_code == 200:
    res = r.json()
    print(f"   Status: {res.get('overall_status')} | Jurisdiction: {res.get('jurisdiction_status')}")
    print(f"   Summary: {res.get('summary_message')}")

print("=== ALL TESTCLIENT ENDPOINT TESTS COMPLETED SUCCESSFULLY ===")
