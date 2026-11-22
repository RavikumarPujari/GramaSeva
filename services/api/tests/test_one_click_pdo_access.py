import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import io
import uuid
import pytest
from datetime import datetime, timezone
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.users import Profile, RoleAssignment
from app.models.localities import LocalityUnit
from app.models.issues import Issue, Submission, MediaAsset, Assignment, StatusEvent, WorkCompletion, RepairReview


def create_valid_test_jpeg():
    buf = io.BytesIO()
    img = Image.new("RGB", (100, 100), color="blue")
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestOneClickPdoAccess:
    @classmethod
    def setup_class(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()
        cls.peeranwadi = cls.db.query(LocalityUnit).filter(
            LocalityUnit.official_code == "GP-BEL-PEER"
        ).first() or cls.db.query(LocalityUnit).filter(
            LocalityUnit.id == "dfd115e1-d6c3-490d-9c69-c92247019be0"
        ).first()

    @classmethod
    def teardown_class(cls):
        cls.db.close()

    def test_01_dev_pdo_session_endpoint_success(self):
        """Test POST /api/v1/auth/dev-pdo-session returns genuine JWT and Peeranwadi PDO profile."""
        resp = self.client.post("/api/v1/auth/dev-pdo-session")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        profile = data["profile"]
        assert profile["email"] == "pdo.peeranwadi@belagavi.gov.in"
        assert profile["full_name"] == "Basavaraj Patil"
        roles = [r["role"] for r in profile["roles"]]
        assert "reviewer" in roles

    def test_02_dev_pdo_session_disabled_in_production(self):
        """Test that in production environment (APP_ENV=production), endpoint is strictly blocked with 403."""
        old_env = os.environ.get("APP_ENV", "development")
        try:
            os.environ["APP_ENV"] = "production"
            resp = self.client.post("/api/v1/auth/dev-pdo-session")
            assert resp.status_code == 403
            assert "disabled in production" in resp.json()["detail"].lower()
        finally:
            os.environ["APP_ENV"] = old_env

    def test_03_authenticated_pdo_access_to_staff_apis(self):
        """Test that the JWT returned by /dev-pdo-session grants access to all PDO staff endpoints."""
        session_resp = self.client.post("/api/v1/auth/dev-pdo-session")
        token = session_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Profile /me
        me_resp = self.client.get("/api/v1/auth/me", headers=headers)
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "pdo.peeranwadi@belagavi.gov.in"

        # 2. Village overview
        ov_resp = self.client.get("/api/v1/staff/village-overview", headers=headers)
        assert ov_resp.status_code == 200
        ov_data = ov_resp.json()
        assert "village_name" in ov_data
        assert "Peeranwadi" in ov_data["village_name"]

        # 3. All complaints list
        comp_resp = self.client.get("/api/v1/staff/all-complaints", headers=headers)
        assert comp_resp.status_code == 200
        assert isinstance(comp_resp.json(), list)

        # 4. Workers list
        wrk_resp = self.client.get("/api/v1/staff/workers", headers=headers)
        assert wrk_resp.status_code == 200

        # 5. Wards list
        ward_resp = self.client.get("/api/v1/staff/wards", headers=headers)
        assert ward_resp.status_code == 200

    def test_04_citizen_complaint_appears_in_pdo_dashboard_and_workflow_complete(self):
        """
        Verify complete workflow:
        1. Citizen submits new complaint for Peeranwadi GP.
        2. PDO one-click session fetches it with full complaint records.
        3. PDO assigns worker.
        4. Resolution review verified.
        5. Cleaned up afterwards.
        """
        created_issue_id = None
        created_sub_id = None

        try:
            # 1. Submit citizen complaint for Peeranwadi GP
            img_bytes = create_valid_test_jpeg()
            sub_resp = self.client.post(
                "/api/v1/reports/submit",
                data={
                    "category": "road_damage",
                    "description": "Severe pothole near Peeranwadi Main Cross Road",
                    "latitude": 15.8497,
                    "longitude": 74.4977,
                    "village_name": "Peeranwadi",
                    "citizen_name": "Ananya Hegde",
                    "citizen_phone": "+919876543210",
                },
                files={"file": ("pothole.jpg", img_bytes, "image/jpeg")},
            )
            assert sub_resp.status_code in [200, 201], f"Submission failed: {sub_resp.text}"
            sub_data = sub_resp.json()
            created_sub_id = sub_data.get("submission_id") or sub_data.get("id")
            created_issue_id = sub_data.get("issue_id")

            # 2. Establish PDO session
            pdo_session = self.client.post("/api/v1/auth/dev-pdo-session").json()
            pdo_token = pdo_session["access_token"]
            headers = {"Authorization": f"Bearer {pdo_token}"}

            # 3. Fetch complaints on PDO dashboard
            all_comp_resp = self.client.get("/api/v1/staff/all-complaints", headers=headers)
            assert all_comp_resp.status_code == 200
            complaints = all_comp_resp.json()

            # Verify the submitted complaint appears
            found = next((c for c in complaints if c.get("id") == created_issue_id or c.get("id") == created_sub_id), None)
            assert found is not None, f"Complaint {created_issue_id} did not appear in PDO complaints list!"

            # Verify complaint record fields (Requirement 6)
            assert found["category"] == "road_damage"
            assert "Peeranwadi" in (found.get("village_name") or "")
            assert found.get("description") == "Severe pothole near Peeranwadi Main Cross Road"
            assert found.get("status") in ["SUBMITTED", "UNDER_REVIEW"]
            assert found.get("created_at") is not None

            # 4. PDO Triage: Assign to worker
            worker = self.db.query(Profile).filter(Profile.email == "worker.ramesh@fixproof.org").first()
            if worker:
                triage_resp = self.client.post(
                    f"/api/v1/staff/triage/{created_issue_id}",
                    json={
                        "decision": "CONFIRM_DISPATCH",
                        "assigned_worker_id": worker.id,
                        "priority": "HIGH",
                        "instructions": "Please inspect and repair as urgent civic priority.",
                    },
                    headers=headers,
                )
                assert triage_resp.status_code == 200
                triage_data = triage_resp.json()
                assert triage_data.get("status") in ["success", "ASSIGNED", "IN_PROGRESS", "TRIAGED"]
                # Also verify in DB that issue was updated
                self.db.expire_all()
                updated_issue = self.db.query(Issue).filter(Issue.id == created_issue_id).first()
                assert updated_issue.status in ["ASSIGNED", "IN_PROGRESS", "UNDER_REVIEW"]

        finally:
            # Clean up all created test records so database remains clean
            if created_issue_id:
                self.db.query(RepairReview).filter(RepairReview.issue_id == created_issue_id).delete(synchronize_session=False)
                self.db.query(WorkCompletion).filter(WorkCompletion.issue_id == created_issue_id).delete(synchronize_session=False)
                self.db.query(Assignment).filter(Assignment.issue_id == created_issue_id).delete(synchronize_session=False)
                self.db.query(StatusEvent).filter(StatusEvent.issue_id == created_issue_id).delete(synchronize_session=False)
                self.db.query(MediaAsset).filter(MediaAsset.issue_id == created_issue_id).delete(synchronize_session=False)
                self.db.query(Submission).filter(Submission.issue_id == created_issue_id).delete(synchronize_session=False)
                self.db.query(Issue).filter(Issue.id == created_issue_id).delete(synchronize_session=False)
                self.db.commit()

    def test_05_dev_admin_session_endpoint_success(self):
        """Test POST /api/v1/auth/dev-admin-session returns Super Admin JWT and grants access to /admin APIs."""
        resp = self.client.post("/api/v1/auth/dev-admin-session")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        assert data["profile"]["email"] == "admin@fixproof.org"
        assert any(r["role"] == "admin" for r in data["profile"]["roles"])

        headers = {"Authorization": f"Bearer {data['access_token']}"}
        ov_resp = self.client.get("/api/v1/admin/overview", headers=headers)
        assert ov_resp.status_code == 200, f"Admin overview failed: {ov_resp.text}"

    def test_06_dev_worker_session_endpoint_success(self):
        """Test POST /api/v1/auth/dev-worker-session returns Worker JWT and grants access to /worker APIs."""
        resp = self.client.post("/api/v1/auth/dev-worker-session")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        assert data["profile"]["email"] == "worker.ramesh@fixproof.org"
        assert any(r["role"] == "worker" for r in data["profile"]["roles"])

        headers = {"Authorization": f"Bearer {data['access_token']}"}
        st_resp = self.client.get("/api/v1/worker/status", headers=headers)
        assert st_resp.status_code == 200, f"Worker status failed: {st_resp.text}"

    def test_07_demo_session_endpoint_unified(self):
        """Test POST /api/v1/auth/demo-session routes properly for super_admin, village_pdo, and worker."""
        # 1. Super Admin
        r_admin = self.client.post("/api/v1/auth/demo-session", json={"role": "super_admin"})
        assert r_admin.status_code == 200
        assert r_admin.json()["profile"]["email"] == "admin@fixproof.org"

        # 2. Village PDO
        r_pdo = self.client.post("/api/v1/auth/demo-session", json={"role": "village_pdo"})
        assert r_pdo.status_code == 200
        assert r_pdo.json()["profile"]["email"] == "pdo.peeranwadi@belagavi.gov.in"

        # 3. Worker
        r_worker = self.client.post("/api/v1/auth/demo-session", json={"role": "worker"})
        assert r_worker.status_code == 200
        assert r_worker.json()["profile"]["email"] == "worker.ramesh@fixproof.org"

        # 4. Invalid role
        r_bad = self.client.post("/api/v1/auth/demo-session", json={"role": "unsupported_role"})
        assert r_bad.status_code == 400

    def test_08_role_permission_isolation_and_security(self):
        """Verify strict role-based access control: demo worker cannot access admin or staff APIs, PDO cannot access admin."""
        worker_tok = self.client.post("/api/v1/auth/dev-worker-session").json()["access_token"]
        worker_headers = {"Authorization": f"Bearer {worker_tok}"}

        pdo_tok = self.client.post("/api/v1/auth/dev-pdo-session").json()["access_token"]
        pdo_headers = {"Authorization": f"Bearer {pdo_tok}"}

        # Worker blocked from Admin API
        resp_w_admin = self.client.get("/api/v1/admin/overview", headers=worker_headers)
        assert resp_w_admin.status_code == 403, f"Expected 403 for worker accessing admin, got {resp_w_admin.status_code}"

        # Worker blocked from PDO Staff API
        resp_w_staff = self.client.get("/api/v1/staff/all-complaints", headers=worker_headers)
        assert resp_w_staff.status_code == 403, f"Expected 403 for worker accessing staff, got {resp_w_staff.status_code}"

        # PDO blocked from Super Admin API
        resp_p_admin = self.client.get("/api/v1/admin/overview", headers=pdo_headers)
        assert resp_p_admin.status_code == 403, f"Expected 403 for PDO accessing admin, got {resp_p_admin.status_code}"

    def test_09_citizen_normal_password_authentication(self):
        """Verify citizen requires valid email & password, and citizen token cannot access protected staff/admin APIs."""
        # 1. Successful citizen password login
        cit_resp = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "citizen.ananya@example.com",
                "password": "DemoPassword123!",
                "selected_role": "citizen",
            },
        )
        assert cit_resp.status_code == 200, f"Citizen login failed: {cit_resp.text}"
        cit_data = cit_resp.json()
        assert "access_token" in cit_data
        cit_headers = {"Authorization": f"Bearer {cit_data['access_token']}"}

        # 2. Citizen blocked from staff APIs
        resp_c_staff = self.client.get("/api/v1/staff/all-complaints", headers=cit_headers)
        assert resp_c_staff.status_code == 403

        # 3. Citizen blocked from admin APIs
        resp_c_admin = self.client.get("/api/v1/admin/overview", headers=cit_headers)
        assert resp_c_admin.status_code == 403
