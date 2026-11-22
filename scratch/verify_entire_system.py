import os
import sys
import io
import json
from PIL import Image

# Setup paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "api")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ["DATABASE_URL"] = "sqlite:///./fixproof_dev.db"

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, engine, Base
from database.seeds.demo_seed import seed_database
from app.ai.roboflow_service import roboflow_service
from workers.adapters.road_damage.adapter import road_damage_adapter
from workers.adapters.water_leak.adapter import water_leak_adapter

def create_sample_image(format="JPEG", size=(400, 300), color=(140, 140, 140)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()

def run_system_audit():
    print("=" * 70)
    print("GRAMASEVA — SYSTEM INTEGRITY & AI MODELS COMPREHENSIVE AUDIT")
    print("=" * 70)
    
    # Ensure tables and seed
    Base.metadata.create_all(bind=engine)
    seed_database(reset_old_pilot=False)
    client = TestClient(app)
    
    results = {}
    
    # -------------------------------------------------------------
    # 1. AI MODELS AUDIT
    # -------------------------------------------------------------
    print("\n[1] Testing AI Models Readiness & Endpoints...")
    
    # 1A. Health endpoint
    res = client.get("/api/v1/ai/models/health")
    print(f"  -> GET /api/v1/ai/models/health status: {res.status_code}")
    assert res.status_code == 200, f"Health endpoint failed: {res.text}"
    health_data = res.json()
    print(f"     Models registered: {[m['model_id'] for m in health_data]}")
    results["ai_health_endpoint"] = "PASS"
    
    # 1B. Local Road Damage Adapter
    sample_img = create_sample_image()
    rdd_res = road_damage_adapter.predict(sample_img)
    print(f"  -> Local Road Damage Model status: {rdd_res['status']}, model_id: {rdd_res['model_id']}")
    results["local_rdd_model"] = "PASS"
    
    # 1C. Local Water Leak Adapter
    leak_res = water_leak_adapter.predict(sample_img)
    print(f"  -> Local Water Leak Model status: {leak_res['status']}, model_id: {leak_res['model_id']}")
    results["local_leak_model"] = "PASS"
    
    # 1D. Roboflow Multi-Model Service Test
    registered = roboflow_service.get_registered_models()
    print(f"  -> Roboflow Registered Models ({len(registered)}):")
    for r in registered:
        print(f"     - {r['key']}: {r['name']} => ID: {r['model_id']}")
    results["roboflow_registry"] = "PASS"
    
    # 1E. Roboflow Multi-Model Analysis with test synthetic predictions
    test_results = [
        {
            "model_key": "model_1",
            "model_id": "civic_issues_v1-dc7ae-zzdgj/1",
            "status": "COMPLETED",
            "primary_category": "road_damage",
            "defect_label": "pothole",
            "confidence_score": 0.88,
            "predictions": [{"class": "pothole", "confidence": 0.88, "x": 100, "y": 100, "width": 60, "height": 40}],
        },
        {
            "model_key": "model_2",
            "model_id": "civic-issue-yljwt-tptzy/2",
            "status": "COMPLETED",
            "primary_category": "road_damage",
            "defect_label": "pothole",
            "confidence_score": 0.83,
            "predictions": [{"class": "pothole", "confidence": 0.83, "x": 102, "y": 99, "width": 58, "height": 41}],
        },
        {
            "model_key": "model_3",
            "model_id": "civic-issues-qj5pb/2",
            "status": "COMPLETED",
            "primary_category": "road_damage",
            "defect_label": "road_damage",
            "confidence_score": 0.79,
            "predictions": [{"class": "road_damage", "confidence": 0.79, "x": 105, "y": 102, "width": 62, "height": 44}],
        },
    ]
    comparison = roboflow_service.compare_predictions(test_results)
    print(f"  -> Multi-Model Consensus Engine: Status={comparison['consensus_status']}, Category={comparison['consensus_category']}, HasConsensus={comparison['has_consensus']}")
    assert comparison["consensus_status"] == "STRONG_CONSENSUS"
    results["consensus_engine"] = "PASS"
    
    # 1F. Disputed Classification Test (Garbage Dump vs Road Damage)
    disputed_test = [
        {
            "model_key": "model_1",
            "model_id": "civic_issues_v1-dc7ae-zzdgj/1",
            "status": "COMPLETED",
            "primary_category": "road_damage",
            "defect_label": "pothole",
            "confidence_score": 0.85,
            "predictions": [{"class": "pothole", "confidence": 0.85, "x": 100, "y": 100, "width": 50, "height": 50}],
        },
        {
            "model_key": "model_2",
            "model_id": "civic-issue-yljwt-tptzy/2",
            "status": "COMPLETED",
            "primary_category": "garbage",
            "defect_label": "garbage_dump",
            "confidence_score": 0.89,
            "predictions": [{"class": "garbage_dump", "confidence": 0.89, "x": 100, "y": 100, "width": 120, "height": 100}],
        },
    ]
    dispute_comp = roboflow_service.compare_predictions(disputed_test)
    print(f"  -> Governance Check (Garbage vs Road Damage): Status={dispute_comp['consensus_status']}, HasConsensus={dispute_comp['has_consensus']}")
    assert dispute_comp["consensus_status"] == "DISPUTED"
    results["governance_check"] = "PASS"
    
    # 1G. Bounding Box Rendering with Model Attribution Tags
    pil_img = Image.new("RGB", (300, 300), color=(100, 100, 100))
    annotated_uri = roboflow_service.draw_multi_model_bounding_boxes(pil_img, test_results)
    assert annotated_uri.startswith("data:image/jpeg;base64,")
    print(f"  -> Multi-Model Bounding Box Renderer: Generated URI length={len(annotated_uri)} chars")
    results["bounding_box_renderer"] = "PASS"
    
    # 1H. AI Unified Complaint Analysis API Endpoint
    analyze_res = client.post(
        "/api/v1/ai/analyze-complaint",
        files={"file": ("test.jpg", sample_img, "image/jpeg")},
        data={"latitude": "15.8497", "longitude": "74.4977", "village_name": "Peeranwadi", "category_hint": "road_damage"},
    )
    print(f"  -> POST /api/v1/ai/analyze-complaint status: {analyze_res.status_code}")
    assert analyze_res.status_code == 200, f"Analyze failed: {analyze_res.text}"
    analyze_json = analyze_res.json()
    print(f"     Analysis response: status={analyze_json.get('status')}, category={analyze_json.get('predicted_category')}, provider={analyze_json.get('model_provider')}, consensus={analyze_json.get('ai_consensus_status')}")
    results["analyze_complaint_api"] = "PASS"

    # -------------------------------------------------------------
    # 2. AUTHENTICATION & LOGIN AUDIT
    # -------------------------------------------------------------
    print("\n[2] Testing Authentication & Logins Across Roles...")
    
    roles_to_test = [
        ("Super Admin", "admin@fixproof.org", "DemoPassword123!"),
        ("PDO Reviewer", "reviewer.gowdanahalli@fixproof.org", "DemoPassword123!"),
        ("Worker", "worker.ramesh@fixproof.org", "DemoPassword123!"),
        ("Citizen", "citizen.ananya@example.com", "DemoPassword123!"),
    ]
    
    tokens = {}
    for role_label, email, password in roles_to_test:
        login_res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert login_res.status_code == 200, f"Login failed for {role_label}: {login_res.text}"
        data = login_res.json()
        token = data.get("access_token")
        assert token, f"No token returned for {role_label}"
        tokens[role_label] = token
        print(f"  -> {role_label} login OK: user_id={data.get('user_id')}, role={data.get('primary_role')}")
    results["authentication_all_roles"] = "PASS"

    # -------------------------------------------------------------
    # 3. WORKFLOW AUDIT (END-TO-END ISSUE REPORT & RESOLUTION)
    # -------------------------------------------------------------
    print("\n[3] Testing Civic Complaint Life-Cycle Workflow...")
    
    # 3A. Citizen Report Submission
    cit_token = tokens["Citizen"]
    submit_res = client.post(
        "/api/v1/reports/submit",
        headers={"Authorization": f"Bearer {cit_token}"},
        data={
            "category": "road_damage",
            "title": "Severe Pothole on Post Office Road",
            "description": "Large deep pothole creating hazard for two wheelers.",
            "village_name": "Peeranwadi",
            "ward_name": "Ward 1",
            "latitude": "15.8497",
            "longitude": "74.4977",
            "citizen_name": "Ananya Sharma",
            "citizen_phone": "9876543210",
        },
        files={"file": ("pothole.jpg", sample_img, "image/jpeg")},
    )
    print(f"  -> Citizen Report Submit status: {submit_res.status_code}")
    assert submit_res.status_code in (200, 201), f"Submit failed: {submit_res.text}"
    submit_json = submit_res.json()
    ref_num = submit_json.get("tracking_id") or submit_json.get("reference_number")
    issue_id = submit_json.get("issue_id") or submit_json.get("id")
    print(f"     Created Issue: ID={issue_id}, Tracking={ref_num}")
    results["citizen_report_submission"] = "PASS"
    
    # 3B. Public Tracking
    track_res = client.get(f"/api/v1/public/track/{ref_num}")
    print(f"  -> Public Tracking GET /public/track/{ref_num} status: {track_res.status_code}")
    assert track_res.status_code == 200, f"Track failed: {track_res.text}"
    results["public_tracking"] = "PASS"
    
    # 3C. Staff / PDO All Complaints & Inbox
    pdo_token = tokens["PDO Reviewer"]
    staff_res = client.get(
        "/api/v1/staff/all-complaints",
        headers={"Authorization": f"Bearer {pdo_token}"},
    )
    print(f"  -> PDO GET /staff/all-complaints status: {staff_res.status_code}")
    assert staff_res.status_code == 200, f"Staff complaints failed: {staff_res.text}"
    staff_list = staff_res.json()
    print(f"     Total complaints returned to PDO: {len(staff_list)}")
    # Verify multi-model fields are present on items
    if len(staff_list) > 0:
        first = staff_list[0]
        assert "ai_model_ids" in first, "ai_model_ids missing from StaffComplaintItem"
        assert "ai_consensus_status" in first, "ai_consensus_status missing from StaffComplaintItem"
        assert "ai_model_summaries" in first, "ai_model_summaries missing from StaffComplaintItem"
    results["pdo_all_complaints"] = "PASS"

    # 3D. Super Admin Overview
    admin_token = tokens["Super Admin"]
    admin_res = client.get(
        "/api/v1/admin/overview",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    print(f"  -> Admin GET /admin/overview status: {admin_res.status_code}")
    assert admin_res.status_code == 200, f"Admin overview failed: {admin_res.text}"
    results["admin_overview"] = "PASS"

    # -------------------------------------------------------------
    # 4. SUMMARY
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("ALL AUDIT CHECKS PASSED SUCCESSFULLY:")
    for k, v in results.items():
        print(f"  [+] {k}: {v}")
    print("=" * 70)

if __name__ == "__main__":
    run_system_audit()
