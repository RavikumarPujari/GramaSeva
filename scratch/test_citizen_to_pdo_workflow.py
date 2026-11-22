import sys
import os
import io
import json
import requests
from PIL import Image

sys.path.insert(0, os.path.abspath("services/api"))
from app.core.database import SessionLocal
from app.models.users import Profile, RoleAssignment
from app.models.localities import LocalityUnit
from app.models.issues import Issue, Submission, MediaAsset, StatusEvent, Assignment
from app.auth.security import create_access_token

BASE_URL = "http://127.0.0.1:8000/api/v1"

def create_test_image(color="blue", size=(200, 200)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def run_test():
    db = SessionLocal()
    print("==================================================")
    print("TESTING COMPLETE CITIZEN-TO-PDO WORKFLOW")
    print("==================================================")

    # 1. Setup PDO, Worker, Locality
    pdo = db.query(Profile).filter(Profile.email == "pdo.peeranwadi@belagavi.gov.in").first()
    if not pdo:
        raise Exception("PDO user pdo.peeranwadi@belagavi.gov.in not found!")
    
    worker = db.query(Profile).filter(Profile.email.ilike("%worker.ramesh%")).first()
    if not worker:
        raise Exception("Worker user not found!")

    # Ensure worker has approved worker role
    worker_ra = db.query(RoleAssignment).filter(
        RoleAssignment.profile_id == worker.id,
        RoleAssignment.role == "worker",
    ).first()
    if not worker_ra:
        worker_ra = RoleAssignment(
            profile_id=worker.id,
            role="worker",
            approval_status="APPROVED",
            is_active=True,
            jurisdiction_unit_id="dfd115e1-d6c3-490d-9c69-c92247019be0"
        )
        db.add(worker_ra)
    else:
        worker_ra.approval_status = "APPROVED"
        worker_ra.is_active = True
    db.commit()

    pdo_token = create_access_token({"sub": pdo.id, "email": pdo.email, "roles": ["reviewer"]})
    worker_token = create_access_token({"sub": worker.id, "email": worker.email, "roles": ["worker"]})
    pdo_headers = {"Authorization": f"Bearer {pdo_token}"}
    worker_headers = {"Authorization": f"Bearer {worker_token}"}
    db.close()

    # ==========================================
    # STEP 1: CITIZEN COMPLAINT SUBMISSION
    # ==========================================
    print("\n--- STEP 1: CITIZEN SUBMIT REPORT ---")
    img_bytes = create_test_image("red")
    files = {"file": ("pothole.jpg", img_bytes, "image/jpeg")}
    data = {
        "category": "road_damage",
        "title": "Severe pothole on Peeranwadi Main Road",
        "description": "Large pothole causing traffic slowdown near Peeranwadi High School.",
        "village_name": "Peeranwadi",
        "confirmed_village": "Peeranwadi",
        "taluk_name": "Belagavi Taluk",
        "confirmed_latitude": "15.8152",
        "confirmed_longitude": "74.4610",
        "citizen_name": "Ramesh Citizen",
        "citizen_phone": "+919876543210",
        "is_guest": "true",
        "location_method": "GPS_VERIFIED",
        "gps_accuracy": "5.5",
    }
    res = requests.post(f"{BASE_URL}/reports/submit", files=files, data=data)
    print("Submit status:", res.status_code)
    if res.status_code not in [200, 201]:
        print("Submit error:", res.text)
        sys.exit(1)

    sub_data = res.json()
    tracking_id = sub_data.get("tracking_id")
    issue_id = sub_data.get("id") or sub_data.get("issue_id")
    print(f"Created Tracking ID: {tracking_id}, Issue ID: {issue_id}")

    # ==========================================
    # STEP 2: FIX 2 VERIFICATION (IMAGE SERVING)
    # ==========================================
    print("\n--- STEP 2: CHECK PUBLIC IMAGE SERVING ---")
    track_res = requests.get(f"{BASE_URL}/public/track/{tracking_id}")
    assert track_res.status_code == 200, f"Tracking failed: {track_res.text}"
    track_info = track_res.json()
    print("Public track status:", track_info.get("status"))
    assert track_info.get("status") == "SUBMITTED"

    before_photos = track_info.get("before_photos", [])
    assert len(before_photos) > 0, "No before photos returned!"
    media_url = before_photos[0]["view_url"]
    print(f"Before photo view URL: {media_url}")

    # Test viewing media asset directly via public endpoint
    media_res = requests.get(f"http://127.0.0.1:8000{media_url}")
    print(f"Media view HTTP status: {media_res.status_code}")
    assert media_res.status_code == 200, f"Media asset returned {media_res.status_code} instead of 200! Body: {media_res.text}"
    assert len(media_res.content) > 100, "Media asset content is empty!"
    print(f"Successfully verified image serving! Size: {len(media_res.content)} bytes.")

    # ==========================================
    # STEP 3: FIX 1 & FIX 3 (PDO DASHBOARD & MAP)
    # ==========================================
    print("\n--- STEP 3: CHECK PDO DASHBOARD VISIBILITY & LIVE MAP ---")
    overview_res = requests.get(f"{BASE_URL}/staff/village-overview", headers=pdo_headers)
    assert overview_res.status_code == 200, f"Overview failed: {overview_res.text}"
    overview_data = overview_res.json()
    print("PDO Village Overview:", overview_data.get("village_name"))
    print("New complaints count:", overview_data.get("new_complaints"))
    assert overview_data.get("new_complaints", 0) >= 1, "New complaints count should be at least 1!"

    all_res = requests.get(f"{BASE_URL}/staff/all-complaints", headers=pdo_headers)
    assert all_res.status_code == 200
    all_complaints = all_res.json()
    found_in_pdo = any(c.get("reference_number") == tracking_id or c.get("id") == issue_id for c in all_complaints)
    print(f"Complaint found in PDO list: {found_in_pdo}")
    assert found_in_pdo, "Complaint did NOT appear in PDO all-complaints!"

    map_res = requests.get(f"{BASE_URL}/staff/village-map", headers=pdo_headers)
    assert map_res.status_code == 200
    map_data = map_res.json()
    found_in_map = any(p.get("reference_number") == tracking_id or p.get("id") == issue_id for p in map_data.get("points", []))
    print(f"Complaint found on PDO Live Map: {found_in_map}")
    assert found_in_map, "Complaint did NOT appear in PDO live map points!"

    # ==========================================
    # STEP 4: STAGE 2 - PDO ACCEPTS COMPLAINT
    # ==========================================
    print("\n--- STEP 4: PDO ACCEPTS COMPLAINT (UNDER_REVIEW) ---")
    accept_res = requests.post(f"{BASE_URL}/staff/issues/{issue_id}/confirm", headers=pdo_headers, json={"reason": "Verified and accepted by PDO"})
    assert accept_res.status_code == 200, f"Accept failed: {accept_res.text}"
    print("Accept response:", accept_res.json())

    # Verify track update
    track_res = requests.get(f"{BASE_URL}/public/track/{tracking_id}")
    track_info = track_res.json()
    print(f"Public track status after accept: {track_info.get('status')}")
    assert track_info.get("status") == "UNDER_REVIEW", f"Expected UNDER_REVIEW, got {track_info.get('status')}"
    timeline_statuses = [ev["status"] for ev in track_info.get("timeline", [])]
    print("Timeline after accept:", timeline_statuses)
    assert "UNDER_REVIEW" in timeline_statuses

    # ==========================================
    # STEP 5: STAGE 3 - PDO ASSIGNS WORKER
    # ==========================================
    print("\n--- STEP 5: PDO ASSIGNS WORKER (ASSIGNED) ---")
    assign_payload = {
        "decision": "CONFIRM_DISPATCH",
        "assigned_worker_id": worker.id,
        "priority": "HIGH",
        "instructions": "Fill road pothole using hot-mix asphalt bitumen.",
        "audit_reason": "High traffic road requires rapid dispatch",
    }
    assign_res = requests.post(f"{BASE_URL}/staff/triage/{issue_id}", headers=pdo_headers, json=assign_payload)
    assert assign_res.status_code == 200, f"Assign failed: {assign_res.text}"
    print("Assign response:", assign_res.json())

    # Verify track update
    track_res = requests.get(f"{BASE_URL}/public/track/{tracking_id}")
    track_info = track_res.json()
    print(f"Public track status after assign: {track_info.get('status')}")
    assert track_info.get("status") == "ASSIGNED"
    timeline_statuses = [ev["status"] for ev in track_info.get("timeline", [])]
    print("Timeline after assign:", timeline_statuses)
    assert "ASSIGNED" in timeline_statuses

    # ==========================================
    # STEP 6: STAGE 4 - WORKER STARTS WORK
    # ==========================================
    print("\n--- STEP 6: WORKER COMMENCES WORK (IN_PROGRESS) ---")
    # Get worker tasks
    tasks_res = requests.get(f"{BASE_URL}/worker/tasks", headers=worker_headers)
    assert tasks_res.status_code == 200
    worker_tasks = tasks_res.json()
    matched_task = next(
        (t for t in worker_tasks if t.get("reference_number") == tracking_id or t.get("issue_id") == issue_id),
        None,
    )
    assert matched_task is not None, f"Assigned task {tracking_id} not found in worker's task list!"
    assignment_id = matched_task["assignment_id"]
    real_issue_id = matched_task["issue_id"]
    print(f"Worker matched assignment ID: {assignment_id}, Issue ID: {real_issue_id}")

    # Worker accepts and starts
    start_res = requests.post(f"{BASE_URL}/worker/assignments/{assignment_id}/accept", headers=worker_headers)
    assert start_res.status_code == 200, f"Start failed: {start_res.text}"
    print("Worker start response:", start_res.json())

    track_res = requests.get(f"{BASE_URL}/public/track/{tracking_id}")
    track_info = track_res.json()
    print(f"Public track status after worker start: {track_info.get('status')}")
    assert track_info.get("status") == "IN_PROGRESS"

    # ==========================================
    # STEP 7: STAGE 5 - WORKER COMPLETES WORK
    # ==========================================
    print("\n--- STEP 7: WORKER COMPLETES WORK (AWAITING_VERIFICATION) ---")
    after_img_bytes = create_test_image("green")
    after_upload = requests.post(
        f"{BASE_URL}/worker/issues/{issue_id}/repair-evidence",
        headers=worker_headers,
        files={"file": ("repaired_road.jpg", after_img_bytes, "image/jpeg")}
    )
    assert after_upload.status_code == 200, f"Repair evidence upload failed: {after_upload.text}"
    after_media_id = after_upload.json().get("media_id")
    print(f"Uploaded repair after-photo ID: {after_media_id}")

    comp_payload = {
        "work_description": "Pothole filled with gravel foundation and 50mm bitumen surface compacting.",
        "work_performed": "Asphalt patch repair",
        "materials_used": "Cold mix asphalt, aggregate",
        "labour_details": "2 workers, 3 hours",
        "materials_cost": 2200.0,
        "labour_cost": 1000.0,
        "other_expenses_cost": 0.0,
        "proposed_cost": 3200.0,
        "after_media_ids": [after_media_id]
    }
    complete_res = requests.post(f"{BASE_URL}/worker/issues/{issue_id}/completion", headers=worker_headers, json=comp_payload)
    assert complete_res.status_code == 200, f"Work completion failed: {complete_res.text}"
    print("Work completion response:", complete_res.json())

    track_res = requests.get(f"{BASE_URL}/public/track/{tracking_id}")
    track_info = track_res.json()
    print(f"Public track status after completion: {track_info.get('status')}")
    assert track_info.get("status") in ["REPAIR_REPORTED", "AWAITING_VERIFICATION"]
    assert track_info.get("has_after_photo") is True, "has_after_photo should be True!"

    # ==========================================
    # STEP 8: STAGE 6 - PDO VERIFIES RESOLUTION
    # ==========================================
    print("\n--- STEP 8: PDO VERIFIES AND RESOLVES COMPLAINT (RESOLVED) ---")
    verify_payload = {
        "decision": "APPROVE",
        "explanation": "Inspected repaired asphalt. Defect fully eliminated and compliant with road standards.",
        "verified_cost": 3200.0,
        "cost_remarks": "Approved as per standard rural road schedule of rates."
    }
    verify_res = requests.post(f"{BASE_URL}/staff/issues/{issue_id}/resolution", headers=pdo_headers, json=verify_payload)
    assert verify_res.status_code == 200, f"Verify resolution failed: {verify_res.text}"
    print("Verify resolution response:", verify_res.json())

    # Final Citizen Tracking Verification
    print("\n--- FINAL CITIZEN TRACKING LIFECYCLE AUDIT ---")
    final_track = requests.get(f"{BASE_URL}/public/track/{tracking_id}").json()
    print(f"Final Status: {final_track.get('status')}")
    assert final_track.get("status") == "RESOLVED"
    print(f"Verified Cost: {final_track.get('verified_cost')}")
    assert final_track.get("verified_cost") == 3200.0

    timeline = final_track.get("timeline", [])
    print(f"Timeline events ({len(timeline)} events):")
    for ev in timeline:
        print(f"  - [{ev.get('status')}] Actor: {ev.get('actor_title')} | Time: {ev.get('timestamp')} | Reason: {ev.get('public_summary')}")

    assert len(timeline) >= 5, f"Expected at least 5 chronological timeline events, got {len(timeline)}"
    print("\n==================================================")
    print("SUCCESS: ALL 6 WORKFLOW STAGES AND FIXES PASSED!")
    print("==================================================")

if __name__ == "__main__":
    run_test()
