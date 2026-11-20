import unittest
import uuid
import sys
import os

# Ensure local test environment
os.environ["DATABASE_URL"] = "sqlite:///./fixproof_dev.db"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.core.database import SessionLocal, Base, engine
from app.models.users import Profile, RoleAssignment, WardMember, Announcement, CitizenWardRegistration, CitizenDocument
from app.models.localities import LocalityUnit, Organization
from app.models.issues import Issue, Submission, StatusEvent
from app.admin.router import (
    get_superadmin_overview,
    get_taluk_analytics,
    list_villages,
    list_pdos,
    get_user_management_roster,
    create_announcement,
    get_announcements,
    create_pdo_account,
    CreateAnnouncementRequest,
    CreatePDORequest,
)
from app.staff.router import (
    get_village_pdo_overview,
    get_pdo_village_map,
    get_village_wards,
    add_ward_member,
    CreateWardMemberRequest,
)
from app.worker.router import (
    get_worker_approval_status,
    get_worker_map_tasks,
)
from app.citizen.router import (
    get_citizen_profile,
    update_citizen_profile,
    get_citizen_wards,
    register_citizen_ward,
    delete_citizen_ward,
    get_citizen_documents,
    add_citizen_document,
    UpdateCitizenProfileRequest,
    RegisterWardRequest,
    AddDocumentRequest,
)
from app.auth.router import login, LoginRequest
from app.auth.security import hash_password
from database.seeds.demo_seed import seed_database
from fastapi import HTTPException

class TestSuperadminPdoWorker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        seed_database(reset_old_pilot=False)
        cls.db = SessionLocal()

        cls.admin = cls.db.query(Profile).filter(Profile.email == "admin@fixproof.org").first()

        # Ensure demo citizen for tests
        cls.citizen = cls.db.query(Profile).filter(Profile.email == "citizen.ananya@example.com").first()
        if not cls.citizen:
            cls.citizen = Profile(
                email="citizen.ananya@example.com",
                password_hash=hash_password("DemoPassword123!"),
                full_name="Ananya Sharma",
                preferred_locale="en",
                taluk="Belagavi Taluk",
                district="Belagavi District",
                state="Karnataka",
            )
            cls.db.add(cls.citizen)
            cls.db.flush()
            cls.db.add(RoleAssignment(profile_id=cls.citizen.id, role="citizen", is_active=True))
            cls.db.commit()

        # Ensure demo worker for tests
        cls.worker = cls.db.query(Profile).filter(Profile.email == "worker.ramesh@fixproof.org").first()
        if not cls.worker:
            cls.worker = Profile(
                email="worker.ramesh@fixproof.org",
                password_hash=hash_password("DemoPassword123!"),
                full_name="Ramesh K.",
                preferred_locale="kn",
            )
            cls.db.add(cls.worker)
            cls.db.flush()
            cls.db.add(RoleAssignment(profile_id=cls.worker.id, role="worker", is_active=True, approval_status="APPROVED"))
            cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_role_based_login(self):
        """Tests that login validates matching roles properly."""
        # Valid admin login
        req = LoginRequest(email="admin@fixproof.org", password="DemoPassword123!", selected_role="admin")
        res = login(req=req, db=self.db)
        self.assertIn("access_token", res)
        self.assertTrue(any(r.role == "admin" for r in res["profile"]["roles"]))

        # Invalid role selection (citizen selecting admin role)
        req_wrong = LoginRequest(email="citizen.ananya@example.com", password="DemoPassword123!", selected_role="admin")
        with self.assertRaises(HTTPException) as ctx:
            login(req=req_wrong, db=self.db)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_02_belagavi_9_villages_and_analytics(self):
        """Tests Belagavi Taluk 9 villages initial configuration and analytics."""
        ov = get_superadmin_overview(current_admin=self.admin, db=self.db)
        self.assertEqual(ov.total_villages, 9)
        self.assertGreaterEqual(ov.total_complaints, 0)

        analytics = get_taluk_analytics(current_admin=self.admin, db=self.db)
        self.assertEqual(analytics["taluk_name"], "Belagavi Taluk")
        self.assertIn("category_distribution", analytics)
        self.assertIn("village_comparison", analytics)
        self.assertEqual(len(analytics["village_comparison"]), 9)
        self.assertIn("pdo_coverage", analytics)

        villages = list_villages(unit_type=None, current_admin=self.admin, db=self.db)
        self.assertEqual(len(villages), 9)

        village_names = [v.name_en for v in villages]
        self.assertIn("Peeranwadi", village_names)
        self.assertIn("Yellur", village_names)
        self.assertIn("Mandoli", village_names)

        users = get_user_management_roster(role=None, search=None, limit=50, current_admin=self.admin, db=self.db)
        self.assertGreater(len(users), 0)

    def test_03_create_pdo_account_with_random_name(self):
        """Tests Super Admin appointing a primary PDO to a village with a realistic name."""
        peeranwadi = self.db.query(LocalityUnit).filter(LocalityUnit.name_en == "Peeranwadi").first()
        self.assertIsNotNone(peeranwadi)

        pdo_email = f"pdo.peeranwadi.{uuid.uuid4().hex[:4]}@belagavi.gov.in"
        pdo_req = CreatePDORequest(
            email=pdo_email,
            password="DemoPassword123!",
            full_name="Kiran Patil",
            phone_number="+91 98450 12345",
            village_id=peeranwadi.id,
            is_primary=True,
        )
        created_pdo = create_pdo_account(req=pdo_req, current_admin=self.admin, db=self.db)
        self.assertEqual(created_pdo.email, pdo_email)
        self.assertEqual(created_pdo.village_id, peeranwadi.id)

        # Verify PDO appears in list
        pdos = list_pdos(current_admin=self.admin, db=self.db)
        self.assertGreater(len(pdos), 0)

        # Verify village PDO overview scoped to Peeranwadi
        pdo_profile = self.db.query(Profile).filter(Profile.id == created_pdo.id).first()
        pdo_ov = get_village_pdo_overview(current_reviewer=pdo_profile, db=self.db)
        self.assertEqual(pdo_ov.village_name, "Peeranwadi")

    def test_04_superadmin_announcements(self):
        """Tests broadcast announcement creation and delivery logging."""
        req = CreateAnnouncementRequest(
            title="Belagavi Taluk Drainage Audit",
            content="All PDOs to audit monsoon water pipe drainage lines across Belagavi Taluk.",
            target_type="ALL_PDOS",
        )
        res = create_announcement(req=req, current_admin=self.admin, db=self.db)
        self.assertIn("id", res)
        self.assertGreaterEqual(res["delivered_count"], 0)

        announcements = get_announcements(current_admin=self.admin, db=self.db)
        self.assertGreater(len(announcements), 0)

    def test_05_worker_status_and_tasks(self):
        """Tests Worker profile check and scoped map tasks."""
        status = get_worker_approval_status(current_worker=self.worker, db=self.db)
        self.assertIn(status.approval_status, ["APPROVED", "PENDING"])

        tasks = get_worker_map_tasks(current_worker=self.worker, db=self.db)
        self.assertIsInstance(tasks, list)

    def test_06_citizen_profile_wards_documents(self):
        """Tests Citizen profile editing, multi-ward registry, and document vault."""
        # Profile
        prof = get_citizen_profile(current_user=self.citizen, db=self.db)
        self.assertEqual(prof["email"], self.citizen.email)

        update_req = UpdateCitizenProfileRequest(
            full_name="Ananya Sharma",
            address="House #42, Main Road, Peeranwadi",
            phone_number="+91 98800 55443",
            taluk="Belagavi Taluk",
            district="Belagavi District",
        )
        updated = update_citizen_profile(req=update_req, current_user=self.citizen, db=self.db)
        self.assertEqual(updated["full_name"], "Ananya Sharma")
        self.assertEqual(updated["taluk"], "Belagavi Taluk")

        # Multi-ward registration under a Belagavi village
        peeranwadi = self.db.query(LocalityUnit).filter(LocalityUnit.name_en == "Peeranwadi").first()
        if peeranwadi:
            w_req = RegisterWardRequest(
                ward_unit_id=peeranwadi.id,
                residence_type="PROPERTY_OWNER",
                is_primary=False,
            )
            w_res = register_citizen_ward(req=w_req, current_user=self.citizen, db=self.db)
            self.assertIn("registration_id", w_res)

            citizen_wards = get_citizen_wards(current_user=self.citizen, db=self.db)
            self.assertGreater(len(citizen_wards), 0)

            # Clean up
            delete_citizen_ward(registration_id=w_res["registration_id"], current_user=self.citizen, db=self.db)

        # Document Vault
        doc_req = AddDocumentRequest(
            title="Ration Card 2026",
            document_type="RATION_CARD",
            file_url="/documents/ration_card_2026.pdf",
            file_size_bytes=1048576,
        )
        doc_res = add_citizen_document(req=doc_req, current_user=self.citizen, db=self.db)
        self.assertIn("id", doc_res)

        docs = get_citizen_documents(current_user=self.citizen, db=self.db)
        self.assertGreater(len(docs), 0)

if __name__ == "__main__":
    unittest.main()
