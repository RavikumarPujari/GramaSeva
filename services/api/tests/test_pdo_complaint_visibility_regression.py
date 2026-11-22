"""
Regression Test: Citizen Complaint Submission to Village PDO Visibility
Verifies:
1. Citizen submits a complaint with village_name='Peeranwadi'.
2. Peeranwadi PDO (Basavaraj Patil) sees the complaint in:
   - /api/v1/staff/all-complaints
   - /api/v1/staff/village-overview
   - /api/v1/staff/inbox
3. An unrelated PDO (or unassigned reviewer) CANNOT see the complaint.
4. Cleans up test records afterwards to maintain database cleanliness.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.core.database import SessionLocal
from app.models.users import Profile, RoleAssignment
from app.models.issues import Issue, Submission, MediaAsset, StatusEvent
from app.models.localities import LocalityUnit

client = TestClient(app)

def test_pdo_complaint_visibility_and_jurisdiction_scoping():
    db: Session = SessionLocal()
    created_issue_id = None
    created_sub_id = None
    dummy_reviewer_id = None

    try:
        # 1. Authenticate Citizen Ananya
        login_res = client.post(
            "/api/v1/auth/login",
            json={"email": "citizen.ananya@example.com", "password": "DemoPassword123!"},
        )
        assert login_res.status_code == 200, f"Citizen login failed: {login_res.text}"
        citizen_token = login_res.json()["access_token"]

        # 2. Submit complaint for Peeranwadi
        import io
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (128, 128), color=(40, 80, 160)).save(buf, format="JPEG")
        sample_img = buf.getvalue()
        files = {"file": ("pothole.jpg", sample_img, "image/jpeg")}
        data = {
            "category": "road_damage",
            "title": "Pothole on Main Belagavi-Khanapur Road in Peeranwadi",
            "description": "Deep pothole causing serious hazard to two-wheelers near Peeranwadi bus shelter.",
            "village_name": "Peeranwadi",
            "latitude": 15.8497,
            "longitude": 74.4977,
            "citizen_name": "Ananya Sharma",
            "citizen_phone": "+919876543210",
            "is_guest": False,
        }

        submit_res = client.post(
            "/api/v1/reports/submit",
            headers={"Authorization": f"Bearer {citizen_token}"},
            files=files,
            data=data,
        )
        assert submit_res.status_code == 201, f"Complaint submission failed: {submit_res.text}"
        sub_json = submit_res.json()
        tracking_id = sub_json["tracking_id"]
        created_issue_id = sub_json["issue_id"]
        created_sub_id = sub_json["id"]

        assert tracking_id is not None
        assert created_issue_id is not None

        # Verify Issue was assigned to Peeranwadi LocalityUnit
        peeranwadi_gp = db.query(LocalityUnit).filter(LocalityUnit.id == "dfd115e1-d6c3-490d-9c69-c92247019be0").first()
        issue_db = db.query(Issue).filter(Issue.id == created_issue_id).first()
        assert issue_db is not None
        assert issue_db.locality_unit_id == peeranwadi_gp.id
        assert issue_db.jurisdiction_status == "VERIFIED"

        # 3. Authenticate Peeranwadi PDO (Basavaraj Patil)
        pdo_login = client.post(
            "/api/v1/auth/login",
            json={"email": "pdo.peeranwadi@belagavi.gov.in", "password": "DemoPassword123!"},
        )
        assert pdo_login.status_code == 200, f"PDO login failed: {pdo_login.text}"
        pdo_token = pdo_login.json()["access_token"]

        # 4. Check Peeranwadi PDO's all-complaints
        all_comp_res = client.get(
            "/api/v1/staff/all-complaints",
            headers={"Authorization": f"Bearer {pdo_token}"},
        )
        assert all_comp_res.status_code == 200, f"all-complaints failed: {all_comp_res.text}"
        all_comp = all_comp_res.json()
        matching_comp = [c for c in all_comp if c["id"] == created_issue_id or c["reference_number"] == tracking_id]
        assert len(matching_comp) == 1, f"Newly submitted complaint {tracking_id} not visible in Peeranwadi PDO dashboard!"
        assert matching_comp[0]["village_name"] == "Peeranwadi"
        assert matching_comp[0]["category"] == "road_damage"

        # 5. Check Peeranwadi PDO's village-overview
        ov_res = client.get(
            "/api/v1/staff/village-overview",
            headers={"Authorization": f"Bearer {pdo_token}"},
        )
        assert ov_res.status_code == 200, f"village-overview failed: {ov_res.text}"
        ov_data = ov_res.json()
        assert ov_data["total_complaints"] >= 1
        assert ov_data["new_complaints"] >= 1
        assert ov_data["village_name"] == "Peeranwadi"

        # 6. Check Peeranwadi PDO's inbox
        inbox_res = client.get(
            "/api/v1/staff/inbox",
            headers={"Authorization": f"Bearer {pdo_token}"},
        )
        assert inbox_res.status_code == 200, f"inbox failed: {inbox_res.text}"
        inbox = inbox_res.json()
        matching_inbox = [c for c in inbox if c["issue_id"] == created_issue_id or c["tracking_id"] == tracking_id]
        assert len(matching_inbox) == 1, f"Complaint {tracking_id} not visible in Peeranwadi PDO inbox!"

        # 7. Create an ephemeral PDO assigned to Yellur Gram Panchayat (unrelated jurisdiction)
        yellur_gp = db.query(LocalityUnit).filter(LocalityUnit.name_en == "Yellur").first()
        assert yellur_gp is not None

        from app.auth.security import hash_password
        dummy_reviewer = Profile(
            email="pdo.yellur.test@belagavi.gov.in",
            password_hash=hash_password("DemoPassword123!"),
            full_name="Yellur Reviewer Test",
            taluk="Belagavi Taluk",
            is_active=True,
        )
        db.add(dummy_reviewer)
        db.flush()
        dummy_reviewer_id = dummy_reviewer.id

        dummy_role = RoleAssignment(
            profile_id=dummy_reviewer.id,
            role="reviewer",
            jurisdiction_unit_id=yellur_gp.id,  # Assigned to Yellur, NOT Peeranwadi
            is_active=True,
        )
        db.add(dummy_role)
        db.commit()

        # 8. Authenticate as Yellur PDO
        yellur_login = client.post(
            "/api/v1/auth/login",
            json={"email": "pdo.yellur.test@belagavi.gov.in", "password": "DemoPassword123!"},
        )
        assert yellur_login.status_code == 200
        yellur_token = yellur_login.json()["access_token"]

        # 9. Verify Yellur PDO CANNOT see Peeranwadi complaint
        yellur_comp_res = client.get(
            "/api/v1/staff/all-complaints",
            headers={"Authorization": f"Bearer {yellur_token}"},
        )
        assert yellur_comp_res.status_code == 200
        yellur_comps = yellur_comp_res.json()
        yellur_matching = [c for c in yellur_comps if c["id"] == created_issue_id or c["reference_number"] == tracking_id]
        assert len(yellur_matching) == 0, "Security violation: Peeranwadi complaint leaked into Yellur PDO dashboard!"

        yellur_inbox_res = client.get(
            "/api/v1/staff/inbox",
            headers={"Authorization": f"Bearer {yellur_token}"},
        )
        assert yellur_inbox_res.status_code == 200
        yellur_inbox = yellur_inbox_res.json()
        yellur_inbox_matching = [c for c in yellur_inbox if c["issue_id"] == created_issue_id or c["tracking_id"] == tracking_id]
        assert len(yellur_inbox_matching) == 0, "Security violation: Peeranwadi complaint leaked into Yellur PDO inbox!"

        yellur_ov_res = client.get(
            "/api/v1/staff/village-overview",
            headers={"Authorization": f"Bearer {yellur_token}"},
        )
        assert yellur_ov_res.status_code == 200
        assert yellur_ov_res.json()["total_complaints"] == 0

    finally:
        # Cleanup ephemeral test records to keep database clean
        if created_issue_id:
            db.query(StatusEvent).filter(StatusEvent.issue_id == created_issue_id).delete(synchronize_session=False)
            db.query(MediaAsset).filter(MediaAsset.issue_id == created_issue_id).delete(synchronize_session=False)
            db.query(Submission).filter(Submission.issue_id == created_issue_id).delete(synchronize_session=False)
            db.query(Issue).filter(Issue.id == created_issue_id).delete(synchronize_session=False)

        if dummy_reviewer_id:
            db.query(RoleAssignment).filter(RoleAssignment.profile_id == dummy_reviewer_id).delete(synchronize_session=False)
            db.query(Profile).filter(Profile.id == dummy_reviewer_id).delete(synchronize_session=False)

        db.commit()
        db.close()
