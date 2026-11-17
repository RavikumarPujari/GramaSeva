import unittest
import sys
import os
import uuid

# Add services/api to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Add root to sys.path for database.seeds
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.core.database import SessionLocal, Base, engine
from app.models import (
    Profile,
    RoleAssignment,
    Organization,
    LocalityUnit,
    Department,
    Issue,
    Submission,
)
from app.auth.security import hash_password, verify_password, create_access_token, decode_access_token
from app.auth.dependencies import (
    verify_jurisdiction_scope,
    verify_separation_of_duty,
)
from app.auth.router import register, login, RegisterRequest, LoginRequest
from database.seeds.demo_seed import seed_database

class TestDatabaseAndPermissions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Run seed so test database is populated
        seed_database()
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_user_authentication_and_jwt(self):
        """Test password hashing, verification, token generation and decoding."""
        raw_pwd = "SecurePassword123!"
        hashed = hash_password(raw_pwd)
        self.assertTrue(verify_password(raw_pwd, hashed))
        self.assertFalse(verify_password("WrongPassword!", hashed))

        # Test JWT token lifecycle
        dummy_id = str(uuid.uuid4())
        token = create_access_token({"sub": dummy_id, "email": "test@example.com"})
        payload = decode_access_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["sub"], dummy_id)
        self.assertEqual(payload["email"], "test@example.com")

    def test_02_demo_seeded_users_and_roles(self):
        """Verify seeded demo users exist and have correct RBAC roles."""
        admin = self.db.query(Profile).filter(Profile.email == "admin@fixproof.org").first()
        self.assertIsNotNone(admin)
        admin_roles = [r.role for r in admin.role_assignments if r.is_active]
        self.assertIn("admin", admin_roles)

        reviewer = self.db.query(Profile).filter(Profile.email == "reviewer.gowdanahalli@fixproof.org").first()
        self.assertIsNotNone(reviewer)
        rev_roles = [r.role for r in reviewer.role_assignments if r.is_active]
        self.assertIn("reviewer", rev_roles)

        citizen = self.db.query(Profile).filter(Profile.email == "citizen.ananya@example.com").first()
        self.assertIsNotNone(citizen)
        cit_roles = [r.role for r in citizen.role_assignments if r.is_active]
        self.assertIn("citizen", cit_roles)
        self.assertNotIn("admin", cit_roles)
        self.assertNotIn("reviewer", cit_roles)

    def test_03_first_class_village_ward_hierarchy(self):
        """Verify village wards are first-class units linked to parent villages and GP."""
        gp = self.db.query(LocalityUnit).filter(LocalityUnit.official_code == "GP-KA-571434").first()
        self.assertIsNotNone(gp)
        self.assertEqual(gp.unit_type, "gram_panchayat")

        # Check child villages under GP
        villages = self.db.query(LocalityUnit).filter(LocalityUnit.parent_id == gp.id).all()
        self.assertGreaterEqual(len(villages), 3)

        # Check wards under Gowdanahalli village
        gowd_village = next((v for v in villages if v.name_en == "Gowdanahalli"), None)
        self.assertIsNotNone(gowd_village)
        wards = self.db.query(LocalityUnit).filter(LocalityUnit.parent_id == gowd_village.id).all()
        self.assertGreaterEqual(len(wards), 3)
        for w in wards:
            self.assertEqual(w.unit_type, "ward")
            self.assertTrue(len(w.name_en) > 0)
            self.assertTrue(len(w.name_kn) > 0)
            self.assertTrue(len(w.name_hi) > 0)

    def test_04_jurisdiction_scoping_enforcement(self):
        """
        Verify staff scope is strictly enforced by jurisdiction:
        - Gowdanahalli reviewer CAN act on Gowdanahalli GP, villages, and wards.
        - Gowdanahalli reviewer CANNOT act on Pandavapura Town (cross-jurisdiction block).
        """
        rev1 = self.db.query(Profile).filter(Profile.email == "reviewer.gowdanahalli@fixproof.org").first()
        self.assertIsNotNone(rev1)

        gp_gowdanahalli = self.db.query(LocalityUnit).filter(LocalityUnit.official_code == "GP-KA-571434").first()
        town_pandavapura = self.db.query(LocalityUnit).filter(LocalityUnit.official_code == "ULB-KA-571435").first()
        
        # Find a ward in Gowdanahalli
        ward_in_gowd = self.db.query(LocalityUnit).filter(LocalityUnit.official_code == "W1-GOWD").first()
        self.assertIsNotNone(ward_in_gowd)

        # 1. Staff can access target unit inside assigned GP
        can_access_own_gp = verify_jurisdiction_scope(self.db, rev1.id, gp_gowdanahalli.id)
        self.assertTrue(can_access_own_gp)

        # 2. Staff can access child ward inside assigned GP
        can_access_own_ward = verify_jurisdiction_scope(self.db, rev1.id, ward_in_gowd.id)
        self.assertTrue(can_access_own_ward)

        # 3. Staff CANNOT access town outside assigned GP (cross-jurisdiction check)
        can_access_cross_town = verify_jurisdiction_scope(self.db, rev1.id, town_pandavapura.id)
        self.assertFalse(can_access_cross_town, "Reviewer must be BLOCKED from accessing cross-jurisdiction town units")

    def test_05_separation_of_duty_enforcement(self):
        """Verify rule: A worker cannot approve their own repair resolution."""
        worker_id = "worker-uuid-101"
        different_reviewer_id = "reviewer-uuid-202"

        # Different reviewer -> Allowed
        self.assertTrue(verify_separation_of_duty(worker_id, different_reviewer_id))

        # Same person as worker and reviewer -> Strictly Forbidden
        self.assertFalse(
            verify_separation_of_duty(worker_id, worker_id),
            "Worker must not be allowed to self-approve their own repair resolution",
        )

    def test_06_admin_can_configure_new_village_and_ward(self):
        """Verify admin can add new locality units dynamically."""
        org = self.db.query(Organization).first()
        gp = self.db.query(LocalityUnit).filter(LocalityUnit.unit_type == "gram_panchayat").first()
        test_id = uuid.uuid4().hex[:6]

        new_village = LocalityUnit(
            organization_id=org.id,
            unit_type="village",
            parent_id=gp.id,
            official_code=f"VIL-NEW-{test_id}",
            name_en=f"Greenfield Village {test_id}",
            name_kn="ಟೆಸ್ಟ್ ಗ್ರೀನ್‌ಫೀಲ್ಡ್ ಗ್ರಾಮ",
            name_hi="टेस्ट ग्रीनफील्ड गांव",
            is_active=True,
        )
        self.db.add(new_village)
        self.db.flush()

        new_ward = LocalityUnit(
            organization_id=org.id,
            unit_type="ward",
            parent_id=new_village.id,
            official_code=f"W1-NEW-{test_id}",
            name_en="Ward 1 — Greenfield North",
            name_kn="ವಾರ್ಡ್ ೧ — ಗ್ರೀನ್‌ಫೀಲ್ಡ್ ಉತ್ತರ",
            name_hi="वार्ड १ — ग्रीनफील्ड उत्तर",
            is_active=True,
        )
        self.db.add(new_ward)
        self.db.commit()

        # Query back
        queried_ward = self.db.query(LocalityUnit).filter(LocalityUnit.official_code == f"W1-NEW-{test_id}").first()
        self.assertIsNotNone(queried_ward)
        self.assertEqual(queried_ward.parent_id, new_village.id)
        self.assertEqual(queried_ward.unit_type, "ward")

    def test_07_citizen_registration_and_login_flow(self):
        """Verify real end-to-end citizen registration, password hashing, and login token issuance."""
        test_email = f"newcitizen.{uuid.uuid4().hex[:6]}@example.com"
        reg_req = RegisterRequest(
            email=test_email,
            password="MySecretPassword123!",
            full_name="Pooja K.",
            preferred_locale="kn",
        )
        reg_result = register(reg_req, self.db)
        self.assertIn("access_token", reg_result)
        self.assertEqual(reg_result["profile"]["email"], test_email)
        self.assertEqual(reg_result["profile"]["roles"][0]["role"], "citizen")

        # Now test login
        login_req = LoginRequest(
            email=test_email,
            password="MySecretPassword123!",
        )
        login_result = login(login_req, self.db)
        self.assertIn("access_token", login_result)
        self.assertEqual(login_result["profile"]["full_name"], "Pooja K.")

if __name__ == "__main__":
    unittest.main()
