import urllib.request
import json
import uuid
import io
from PIL import Image

BASE_URL = "http://127.0.0.1:8000/api/v1"

def print_result(phase, status, details):
    badge = "✓ PASS" if status else "✗ FAIL"
    print(f"[{badge}] {phase}: {details}")

print("=== GRAMASEVA COMPLETE 10-PHASE VERIFICATION ===")

# 1. Health check
try:
    with urllib.request.urlopen(f"{BASE_URL}/health", timeout=5) as r:
        data = json.loads(r.read().decode())
        print_result("Phase 1 - Server Health", r.status == 200, f"Status: {data.get('status')}, Version: {data.get('version')}")
except Exception as e:
    print_result("Phase 1 - Server Health", False, str(e))

# 2. Reverse geocoding & boundary check
try:
    # Peeranwadi coords
    lat, lon = 15.8152, 74.4610
    with urllib.request.urlopen(f"{BASE_URL}/localities/google-geocode?latitude={lat}&longitude={lon}", timeout=5) as r:
        data = json.loads(r.read().decode())
        v = data.get("village")
        t = data.get("taluk")
        print_result("Phase 3 - Village Detection", "Peeranwadi" in str(v), f"Village: {v}, Taluk: {t}")
except Exception as e:
    print_result("Phase 3 - Village Detection", False, str(e))

# 3. Gemini Multilingual AI Analysis (Kannada)
boundary = '----WebKitFormBoundary' + uuid.uuid4().hex
lines = []
def add_field(name, val):
    lines.append(f'--{boundary}')
    lines.append(f'Content-Disposition: form-data; name="{name}"')
    lines.append('')
    lines.append(str(val))

def add_file(name, filename, data, mime='image/jpeg'):
    lines.append(f'--{boundary}')
    lines.append(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"')
    lines.append(f'Content-Type: {mime}')
    lines.append('')
    lines.append(data.decode('latin1'))

add_field('category_hint', 'road_damage')
add_field('village_name', 'Peeranwadi')
add_field('locale', 'kn')
img = Image.new('RGB', (120, 120), color=(90, 90, 90))
buf = io.BytesIO()
img.save(buf, format='JPEG')
add_file('file', 'road_sample.jpg', buf.getvalue())
lines.append(f'--{boundary}--')
lines.append('')
body = '\r\n'.join(lines).encode('latin1')

req = urllib.request.Request(
    f"{BASE_URL}/ai/gemini/analyze-problem",
    data=body,
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}', 'Accept': 'application/json'},
    method='POST'
)

try:
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read().decode())
        has_kn = any(ord(c) >= 0x0C80 and ord(c) <= 0x0CFF for c in data.get('title', '') + data.get('description', ''))
        print_result("Phase 4 - Kannada AI Analysis", r.status == 200 and has_kn, f"Title: {data.get('title')[:40]}...")
except Exception as e:
    print_result("Phase 4 - Kannada AI Analysis", False, str(e))

# 4. Duplicate Check
try:
    dup_payload = json.dumps({
        "category": "road_damage",
        "latitude": 15.8152,
        "longitude": 74.4610,
        "threshold_meters": 1000,
        "similarity_threshold": 0.5
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/reports/check-duplicates",
        data=dup_payload,
        headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        dups = json.loads(r.read().decode())
        print_result("Phase 5 - Duplicate Checking", r.status == 200, f"Found {len(dups)} candidate duplicates")
except Exception as e:
    print_result("Phase 5 - Duplicate Checking", False, str(e))

# 5. Full End-to-End Guest Complaint Submission
boundary2 = '----WebKitFormBoundary' + uuid.uuid4().hex
lines2 = []
def add_field2(name, val):
    lines2.append(f'--{boundary2}')
    lines2.append(f'Content-Disposition: form-data; name="{name}"')
    lines2.append('')
    lines2.append(str(val))

def add_file2(name, filename, data, mime='image/jpeg'):
    lines2.append(f'--{boundary2}')
    lines2.append(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"')
    lines2.append(f'Content-Type: {mime}')
    lines2.append('')
    lines2.append(data.decode('latin1'))

add_field2('category', 'road_damage')
add_field2('title', 'Peeranwadi Road Pothole')
add_field2('description', 'Severe pothole reported by guest citizen.')
add_field2('citizen_name', 'Basavaraj Patil')
add_field2('citizen_phone', '+919876543219')
add_field2('is_guest', 'true')
add_field2('latitude', '15.815200')
add_field2('longitude', '74.461000')
add_field2('confirmed_latitude', '15.815200')
add_field2('confirmed_longitude', '74.461000')
add_field2('detected_village', 'Peeranwadi')
add_field2('detected_taluk', 'Belagavi Taluk')
add_field2('detected_district', 'Belagavi District')
add_field2('location_confirmation_status', 'CITIZEN_CONFIRMED')
add_field2('confirmation_method', 'CITIZEN_CONFIRMED')
add_field2('selected_language', 'kn')

img2 = Image.new('RGB', (150, 150), color=(100, 60, 40))
buf2 = io.BytesIO()
img2.save(buf2, format='JPEG')
add_file2('file', 'evidence.jpg', buf2.getvalue())

lines2.append(f'--{boundary2}--')
lines2.append('')
body2 = '\r\n'.join(lines2).encode('latin1')

req2 = urllib.request.Request(
    f"{BASE_URL}/reports/submit",
    data=body2,
    headers={'Content-Type': f'multipart/form-data; boundary={boundary2}', 'Accept': 'application/json'},
    method='POST'
)

try:
    with urllib.request.urlopen(req2, timeout=10) as r:
        res = json.loads(r.read().decode())
        t_id = res.get('tracking_id')
        st = res.get('status')
        print_result("Phase 7 - Complaint Submission", r.status == 201 and bool(t_id), f"Tracking ID: {t_id}, Status: {st}")
except Exception as e:
    print_result("Phase 7 - Complaint Submission", False, str(e))

print("=== VERIFICATION COMPLETE ===")
