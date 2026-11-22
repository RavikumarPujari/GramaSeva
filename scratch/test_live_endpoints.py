import urllib.request
import json

base_url = "http://127.0.0.1:8000/api/v1"

def test_endpoint(name, url, method="GET", data=None):
    try:
        req = urllib.request.Request(url, method=method)
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "TestRunner")
        payload = json.dumps(data).encode("utf-8") if data else None
        with urllib.request.urlopen(req, data=payload, timeout=10) as response:
            code = response.status
            body = json.loads(response.read().decode("utf-8"))
            print(f"[SUCCESS] {name} (Status {code})")
            return body
    except Exception as e:
        print(f"[FAIL] {name}: {e}")
        return None

print("=== TESTING LIVE BACKEND ENDPOINTS ===")

# 1. Models Status
models = test_endpoint("GET /ai/models/status", f"{base_url}/ai/models/status")
if models:
    print(f"  Total Models Registered: {len(models)}")
    for m in models:
        print(f"   - [{m['key']}] {m['name']} ({m['model_id']}) -> Status: {m['status']}")

# 2. Landmarks Register
landmarks = test_endpoint("GET /localities/landmarks", f"{base_url}/localities/landmarks")
if landmarks:
    print(f"  Total Landmarks: {len(landmarks)}")
    print(f"   - First Landmark: {landmarks[0]['name']} (Lat: {landmarks[0]['lat']}, Lon: {landmarks[0]['lon']})")

# 3. Boundaries Register
boundaries = test_endpoint("GET /localities/boundaries", f"{base_url}/localities/boundaries")
if boundaries:
    print(f"  Total Boundaries: {len(boundaries)}")
    print(f"   - First Boundary: {boundaries[0]['name_en']} ({boundaries[0]['gram_panchayat']})")

# 4. Resolve GPS
resolve = test_endpoint("GET /localities/resolve-gps", f"{base_url}/localities/resolve-gps?latitude=15.8152&longitude=74.4610")
if resolve:
    print(f"  GPS Resolution: {resolve.get('village_name')} (Verified: {resolve.get('is_verified')})")

# 5. Dual Source Verification
dual_source = test_endpoint(
    "POST /localities/verify-dual-source",
    f"{base_url}/localities/verify-dual-source",
    method="POST",
    data={
        "latitude": 15.8152,
        "longitude": 74.4610,
        "gps_accuracy": 12.0,
        "acquisition_method": "GPS_VERIFIED",
        "selected_village": "Peeranwadi"
    }
)
if dual_source:
    print(f"  Dual Source Status: {dual_source.get('overall_status')} (Jurisdiction: {dual_source.get('jurisdiction_status')})")
    print(f"  Summary: {dual_source.get('summary_message')}")

print("=== ALL LIVE TESTS COMPLETE ===")
