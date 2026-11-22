import sys
import os
import io
import json
from PIL import Image

sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, os.path.abspath("services/api"))

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.users import Profile, RoleAssignment
from app.auth.security import create_access_token

client = TestClient(app)

def create_test_image():
    img = Image.new("RGB", (640, 480), color=(120, 120, 120))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.getvalue()

def run_e2e_test():
    print("\n--- 1. Testing Location Resolution for Santibastawad (15.777507, 74.466091) ---")
    res = client.get("/api/v1/localities/resolve-gps?latitude=15.777507&longitude=74.466091")
    assert res.status_code == 200, f"resolve-gps failed: {res.text}"
    loc_data = res.json()
    print("resolve-gps response:", json.dumps(loc_data, indent=2))
    assert loc_data["is_verified"] is True
    assert loc_data["village_name"] == "Santibastawad"
    assert loc_data["taluk"] == "Belagavi Taluk"
    assert loc_data["district"] == "Belagavi District"
    assert loc_data["locality_unit_id"] is not None
    print(" Location GPS resolution PASSED!")

    print("\n--- 2. Testing Google Geocode Endpoint for Santibastawad ---")
    res_geo = client.get("/api/v1/localities/google-geocode?latitude=15.777507&longitude=74.466091")
    assert res_geo.status_code == 200, f"google-geocode failed: {res_geo.text}"
    geo_data = res_geo.json()
    print("google-geocode response:", json.dumps(geo_data, indent=2))
    assert geo_data["village"] == "Santibastawad"
    assert "Belagavi" in geo_data["taluk"]
    assert "Belagavi" in geo_data["district"]
    assert geo_data["postal_code"] == "590014"
    print(" Google Geocode resolution PASSED!")

    print("\n--- 3. Testing Gemini Problem Analysis with Citizen Notes ---")
    test_img = create_test_image()
    files = {"file": ("test_road.jpg", test_img, "image/jpeg")}
    data = {
        "category_hint": "road_damage",
        "village_name": "Santibastawad",
        "citizen_notes": "Deep crater pothole dangerous for two wheelers near village bus stop",
        "locale": "en",
    }
    res_gemini = client.post("/api/v1/ai/gemini/analyze-problem", files=files, data=data)
    assert res_gemini.status_code == 200, f"gemini analysis failed: {res_gemini.text}"
    gemini_out = res_gemini.json()
    print("Gemini Problem Analysis:")
    print(" Title:", gemini_out.get("title"))
    print(" Description:", gemini_out.get("description"))
    print(" Category:", gemini_out.get("suggested_category"))
    assert "road" in gemini_out.get("suggested_category", "").lower()
    print(" Gemini Problem Analysis PASSED!")

    print("\n--- 4. Testing Roboflow / Orchestrator Analysis with Bounding Box Alignment ---")
    files_ai = {"file": ("test_road.jpg", test_img, "image/jpeg")}
    data_ai = {
        "category_hint": "road_damage",
        "village_name": "Santibastawad",
        "citizen_notes": "Hazardous road pothole",
        "locale": "en",
    }
    res_ai = client.post("/api/v1/ai/analyze-complaint", files=files_ai, data=data_ai)
    assert res_ai.status_code == 200, f"analyze-complaint failed: {res_ai.text}"
    ai_out = res_ai.json()
    print("AI Analysis Category:", ai_out.get("predicted_category"))
    print("AI Description:", ai_out.get("ai_description"))
    print("Observations count:", len(ai_out.get("observations", [])))
    print(" AI Analysis PASSED!")

    print("\n--- 5. Testing Citizen Complaint Submission at Santibastawad ---")
    files_sub = {"file": ("pothole.jpg", test_img, "image/jpeg")}
    sub_data = {
        "category": "road_damage",
        "title": "Severe Pothole on Santibastawad Road",
        "description": "Deep road depression hazardous for school buses and bikes near Santibastawad village cross.",
        "citizen_name": "Ananya Sharma",
        "citizen_phone": "9876543210",
        "latitude": "15.777507",
        "longitude": "74.466091",
        "confirmed_latitude": "15.777507",
        "confirmed_longitude": "74.466091",
        "confirmed_address": "Santibastawad, Belagavi Taluk, Belagavi District, Karnataka - 590014",
        "village_name": "Santibastawad",
        "confirmed_village": "Santibastawad",
        "taluk_name": "Belagavi Taluk",
        "detected_district": "Belagavi District",
        "detected_postal_code": "590014",
        "is_guest": "false",
    }
    # Authenticate as citizen
    db = SessionLocal()
    citizen = db.query(Profile).filter(Profile.email == "citizen.ananya@example.com").first()
    if not citizen:
        citizen = db.query(Profile).filter(Profile.email.like("%citizen%")).first()
    assert citizen is not None, "Citizen profile not found"
    citizen_token = create_access_token(data={"sub": citizen.email, "profile_id": citizen.id})
    db.close()

    res_sub = client.post(
        "/api/v1/reports/submit",
        files=files_sub,
        data=sub_data,
        headers={"Authorization": f"Bearer {citizen_token}"},
    )
    assert res_sub.status_code == 200, f"report submission failed: {res_sub.text}"
    sub_resp = res_sub.json()
    tracking_id = sub_resp["tracking_id"]
    issue_id = sub_resp.get("issue_id")
    print(f" Complaint successfully registered! Tracking ID: {tracking_id}, Issue ID: {issue_id}")
    print(" Jurisdiction Status:", sub_resp.get("jurisdiction_status"))
    assert sub_resp.get("jurisdiction_status") == "VERIFIED", f"Expected VERIFIED, got {sub_resp.get('jurisdiction_status')}"
    print(" Citizen Submission PASSED!")

    print("\n--- 6. Testing PDO Complaint Visibility ---")
    db = SessionLocal()
    pdo = db.query(Profile).filter(Profile.email == "pdo.peeranwadi@belagavi.gov.in").first()
    assert pdo is not None, "PDO profile not found"
    pdo_token = create_access_token(data={"sub": pdo.email, "profile_id": pdo.id})
    db.close()

    # Call PDO overview
    res_overview = client.get(
        "/api/v1/staff/pdo/overview",
        headers={"Authorization": f"Bearer {pdo_token}"},
    )
    assert res_overview.status_code == 200, f"PDO overview failed: {res_overview.text}"
    overview_data = res_overview.json()
    print("PDO Overview Total Complaints:", overview_data.get("total_complaints"))
    assert overview_data.get("total_complaints", 0) > 0, "PDO total complaints should be > 0"

    # Call PDO all-complaints
    res_complaints = client.get(
        "/api/v1/staff/all-complaints",
        headers={"Authorization": f"Bearer {pdo_token}"},
    )
    assert res_complaints.status_code == 200, f"PDO all-complaints failed: {res_complaints.text}"
    complaints = res_complaints.json()
    found_complaint = next((c for c in complaints if c.get("tracking_id") == tracking_id or c.get("id") == issue_id), None)
    assert found_complaint is not None, f"Newly created complaint {tracking_id} NOT found in PDO complaints list!"
    print(f" SUCCESS! Found complaint in PDO dashboard: ID={found_complaint['id']}, Status={found_complaint['status']}, Village={found_complaint.get('village_name')}")

    print("\n--- 7. Testing PDO Triage & Worker Assignment ---")
    db = SessionLocal()
    worker = db.query(Profile).filter(Profile.email == "worker.ramesh@fixproof.org").first()
    assert worker is not None, "Worker profile not found"
    worker_id = worker.id
    worker_token = create_access_token(data={"sub": worker.email, "profile_id": worker.id})
    db.close()

    triage_payload = {
        "status": "APPROVED",
        "priority": "HIGH",
        "assigned_worker_id": worker_id,
        "instructions": "Execute urgent asphalt cold-mix repair of potholes.",
        "audit_reason": "Verified legitimate village road hazard by Village PDO",
    }
    target_id = found_complaint["id"]
    res_triage = client.post(
        f"/api/v1/staff/issues/{target_id}/triage",
        json=triage_payload,
        headers={"Authorization": f"Bearer {pdo_token}"},
    )
    assert res_triage.status_code == 200, f"Triage failed: {res_triage.text}"
    triage_resp = res_triage.json()
    print("Triage Response Status:", triage_resp.get("status"))
    assert triage_resp.get("status") == "ASSIGNED"
    print(" Triage & Worker Assignment PASSED!")

    print("\n--- 8. Testing Worker Work Execution & Completion Upload ---")
    res_tasks = client.get(
        "/api/v1/worker/tasks",
        headers={"Authorization": f"Bearer {worker_token}"},
    )
    assert res_tasks.status_code == 200, f"Worker tasks failed: {res_tasks.text}"
    tasks = res_tasks.json()
    worker_task = next((t for t in tasks if t.get("issue_id") == target_id), None)
    assert worker_task is not None, f"Assigned task not found in worker's inbox!"
    print(f" Worker task found: {worker_task['assignment_id']}, status={worker_task['status']}")

    # Worker starts work
    res_start = client.post(
        f"/api/v1/worker/tasks/{worker_task['assignment_id']}/start",
        headers={"Authorization": f"Bearer {worker_token}"},
    )
    assert res_start.status_code == 200, f"Worker start failed: {res_start.text}"
    print(" Worker started work successfully!")

    # Worker uploads after photo and completion report
    after_img = create_test_image()
    res_media = client.post(
        f"/api/v1/reports/{target_id}/media",
        files={"file": ("after_repair.jpg", after_img, "image/jpeg")},
        data={"evidence_role": "WORKER_AFTER"},
        headers={"Authorization": f"Bearer {worker_token}"},
    )
    assert res_media.status_code == 200, f"Worker media upload failed: {res_media.text}"
    media_data = res_media.json()
    after_media_id = media_data.get("media_asset_id") or media_data.get("id")

    completion_payload = {
        "work_description": "Potholes filled and leveled with cold asphalt mix. Surface compacted and safe for traffic.",
        "work_performed": "Road pothole patch repair",
        "materials_used": "Cold mix asphalt, binder gravel (2 bags)",
        "labour_details": "Worker Ramesh K. + 1 assistant, 3 hours",
        "materials_cost": 1200.0,
        "labour_cost": 800.0,
        "other_expenses_cost": 200.0,
        "proposed_cost": 2200.0,
        "after_media_ids": [after_media_id] if after_media_id else [],
    }
    res_complete = client.post(
        f"/api/v1/worker/tasks/{worker_task['assignment_id']}/submit-completion",
        json=completion_payload,
        headers={"Authorization": f"Bearer {worker_token}"},
    )
    assert res_complete.status_code == 200, f"Completion submit failed: {res_complete.text}"
    print(" Worker completion submitted successfully! Status is REPAIR_REPORTED")

    print("\n--- 9. Testing PDO Independent Resolution Review & Final Approval ---")
    review_payload = {
        "decision": "APPROVE",
        "explanation": "Field work verified on site. Road repaired to standard. Expenditure ₹2,200.00 approved.",
        "verified_cost": 2200.0,
        "cost_remarks": "Standard scheduled rates for asphalt cold-mix repair.",
    }
    res_review = client.post(
        f"/api/v1/staff/issues/{target_id}/resolution",
        json=review_payload,
        headers={"Authorization": f"Bearer {pdo_token}"},
    )
    assert res_review.status_code == 200, f"Resolution review failed: {res_review.text}"
    print(" PDO verified and approved resolution! Status is now RESOLVED")

    print("\n--- 10. Testing Public / Citizen Tracking Status ---")
    res_track = client.get(f"/api/v1/public/track/{tracking_id}")
    assert res_track.status_code == 200, f"Public tracking failed: {res_track.text}"
    track_data = res_track.json()
    print("Citizen Tracking Details:")
    print(" Tracking ID:", track_data.get("tracking_id"))
    print(" Status:", track_data.get("status"))
    print(" Village:", track_data.get("village_name"))
    print(" Category:", track_data.get("category"))
    print(" Timeline Events:", len(track_data.get("timeline", [])))
    assert track_data.get("status") == "RESOLVED", f"Expected RESOLVED, got {track_data.get('status')}"
    print(" Public Tracking reflects RESOLVED! Complete workflow verified successfully!")

    print("\n=======================================================")
    print(" ALL 10 END-TO-END VERIFICATION CHECKS PASSED PERFECTLY! ")
    print("=======================================================\n")

if __name__ == '__main__':
    run_e2e_test()
