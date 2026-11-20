"""
GramaSeva Belagavi Taluk & Complete Seed Script
Seeds Belagavi Taluk with the 9 actual village records, plus baseline pilot fixtures.
Avoids duplicate records if run multiple times.
"""

import sys
import os
import random

# Add services/api to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/api")))

from app.core.database import SessionLocal, engine, Base
from app.models import (
    Organization,
    LocalityUnit,
    Department,
    DepartmentJurisdiction,
    Profile,
    RoleAssignment,
)
from app.auth.security import hash_password

# 9 Village Records for Belagavi Taluk
BELAGAVI_VILLAGES = [
    {"code": "VIL-BEL-01", "en": "Peeranwadi", "kn": "ಪೀರನವಾಡಿ", "hi": "पीरनवाड़ी"},
    {"code": "VIL-BEL-02", "en": "Kuttalawadi", "kn": "ಕುಟ್ಟಲವಾಡಿ", "hi": "कुट्टलवाड़ी"},
    {"code": "VIL-BEL-03", "en": "Zad-Shahapur", "kn": "ಝಾಡ್-ಶಹಾಪುರ", "hi": "झाड-शहापुर"},
    {"code": "VIL-BEL-04", "en": "Santibastawad", "kn": "ಶಾಂತಿಬಸ್ತವಾಡ", "hi": "शांतिबस्तवाड़"},
    {"code": "VIL-BEL-05", "en": "Yellur", "kn": "ಯೆಲ್ಲೂರು", "hi": "येल्लूर"},
    {"code": "VIL-BEL-06", "en": "Sulge (Yellur)", "kn": "ಸುಳಗೆ (ಯೆಲ್ಲೂರು)", "hi": "सुलगे (येल्लूर)"},
    {"code": "VIL-BEL-07", "en": "Mandoli", "kn": "ಮಾಂಡೋಲಿ", "hi": "मांडोली"},
    {"code": "VIL-BEL-08", "en": "Waghawade", "kn": "ವಾಘಾವಡೆ", "hi": "वाघावडे"},
    {"code": "VIL-BEL-09", "en": "Navage", "kn": "ನವಾಗೆ", "hi": "नवागे"},
]

RANDOM_FIRST_NAMES = [
    "Santosh", "Ramesh", "Suresh", "Basavaraj", "Vinayak", "Anand", "Kiran",
    "Manjunath", "Prakash", "Geetha", "Sunita", "Laxmi", "Savita", "Pooja",
    "Mahadev", "Shivanand", "Mallikarjun", "Pradeep", "Raghavendra", "Anjana"
]
RANDOM_LAST_NAMES = [
    "Patil", "Kulkarni", "Deshmukh", "Jadhav", "Shinde", "Naik", "Biradar",
    "Hegde", "Gowda", "Bhat", "Angadi", "Kittur", "Kambale", "Chavan", "Mane"
]

def generate_random_pdo_name():
    return f"{random.choice(RANDOM_FIRST_NAMES)} {random.choice(RANDOM_LAST_NAMES)}"

def seed_database(reset_old_pilot: bool = False):
    print("[Seed] Initializing GramaSeva database tables...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Organization: Belagavi Taluk Administration
        org = db.query(Organization).filter(Organization.code == "TP-BELAGAVI").first()
        if not org:
            print("[Seed] Creating Belagavi Taluk Administration organization...")
            org = Organization(
                name="Belagavi Taluk Administration",
                code="TP-BELAGAVI",
                description="GramaSeva Civic Platform for Belagavi Taluk & Gram Panchayats.",
                is_active=True,
            )
            db.add(org)
            db.flush()

        # 2. State: Karnataka
        state = db.query(LocalityUnit).filter(LocalityUnit.official_code == "KA", LocalityUnit.unit_type == "state").first()
        if not state:
            state = LocalityUnit(
                organization_id=org.id,
                unit_type="state",
                official_code="KA",
                name_en="Karnataka",
                name_kn="ಕರ್ನಾಟಕ",
                name_hi="कर्नाटक",
                is_active=True,
            )
            db.add(state)
            db.flush()

        # 3. District: Belagavi District
        district = db.query(LocalityUnit).filter(LocalityUnit.official_code == "KA-BLG", LocalityUnit.unit_type == "district").first()
        if not district:
            district = LocalityUnit(
                organization_id=org.id,
                unit_type="district",
                parent_id=state.id,
                official_code="KA-BLG",
                name_en="Belagavi District",
                name_kn="ಬೆಳಗಾವಿ ಜಿಲ್ಲೆ",
                name_hi="बेलगावी जिला",
                is_active=True,
            )
            db.add(district)
            db.flush()

        # 4. Taluk: Belagavi Taluk
        taluk = db.query(LocalityUnit).filter(LocalityUnit.official_code == "KA-BLG-TLK", LocalityUnit.unit_type == "taluk").first()
        if not taluk:
            taluk = LocalityUnit(
                organization_id=org.id,
                unit_type="taluk",
                parent_id=district.id,
                official_code="KA-BLG-TLK",
                name_en="Belagavi Taluk",
                name_kn="ಬೆಳಗಾವಿ ತಾಲೂಕು",
                name_hi="बेलगावी तालुक",
                is_active=True,
            )
            db.add(taluk)
            db.flush()

        # 5. Create the 9 Village Records under Belagavi Taluk (Idempotent)
        print("[Seed] Seeding 9 Belagavi Taluk village records...")
        for v in BELAGAVI_VILLAGES:
            existing = db.query(LocalityUnit).filter(
                LocalityUnit.official_code == v["code"],
                LocalityUnit.parent_id == taluk.id,
            ).first()

            if not existing:
                village_unit = LocalityUnit(
                    organization_id=org.id,
                    unit_type="gram_panchayat",
                    parent_id=taluk.id,
                    official_code=v["code"],
                    name_en=v["en"],
                    name_kn=v["kn"],
                    name_hi=v["hi"],
                    is_active=True,
                )
                db.add(village_unit)
        db.flush()

        # 6. Legacy Test Baseline Units (for test_permissions & test_lifecycle)
        gp_test = db.query(LocalityUnit).filter(LocalityUnit.official_code == "GP-KA-571434").first()
        if not gp_test:
            gp_test = LocalityUnit(
                organization_id=org.id,
                unit_type="gram_panchayat",
                parent_id=taluk.id,
                official_code="GP-KA-571434",
                name_en="Gowdanahalli Gram Panchayat (Test)",
                name_kn="ಗೌಡನಹಳ್ಳಿ ಪಂಚಾಯತ್",
                name_hi="गौडनहल्ली पंचायत",
                is_active=False,  # Inactive so excluded from Belagavi active count
            )
            db.add(gp_test)
            db.flush()

            # Child villages under test GP
            v_gowd = LocalityUnit(
                organization_id=org.id,
                unit_type="village",
                parent_id=gp_test.id,
                official_code="VIL-GOWD",
                name_en="Gowdanahalli",
                name_kn="ಗೌಡನಹಳ್ಳಿ",
                name_hi="गौडनಹಳ್ಳಿ",
                is_active=False,
            )
            v_mall = LocalityUnit(
                organization_id=org.id,
                unit_type="village",
                parent_id=gp_test.id,
                official_code="VIL-MALL",
                name_en="Malleshwarapuram",
                name_kn="ಮಲ್ಲೇಶ್ವರಪುರಂ",
                name_hi="मल्लेश्वरपुरम",
                is_active=False,
            )
            v_rama = LocalityUnit(
                organization_id=org.id,
                unit_type="village",
                parent_id=gp_test.id,
                official_code="VIL-RAMA",
                name_en="Ramanagara",
                name_kn="ರಾಮನಗರ",
                name_hi="रामनगर",
                is_active=False,
            )
            db.add_all([v_gowd, v_mall, v_rama])
            db.flush()

            # Wards under Gowdanahalli village
            w1 = LocalityUnit(
                organization_id=org.id,
                unit_type="ward",
                parent_id=v_gowd.id,
                official_code="W1-GOWD",
                name_en="Ward 1 — Post Office Area",
                name_kn="ವಾರ್ಡ್ ೧",
                name_hi="वार्ड १",
                is_active=False,
            )
            w2 = LocalityUnit(
                organization_id=org.id,
                unit_type="ward",
                parent_id=v_gowd.id,
                official_code="W2-GOWD",
                name_en="Ward 2 — Primary School Road",
                name_kn="ವಾರ್ಡ್ ೨",
                name_hi="वार्ड २",
                is_active=False,
            )
            w3 = LocalityUnit(
                organization_id=org.id,
                unit_type="ward",
                parent_id=v_gowd.id,
                official_code="W3-GOWD",
                name_en="Ward 3 — Temple Street",
                name_kn="ವಾರ್ಡ್ ೩",
                name_hi="वार्ड ३",
                is_active=False,
            )
            db.add_all([w1, w2, w3])
            db.flush()

        town_test = db.query(LocalityUnit).filter(LocalityUnit.official_code == "ULB-KA-571435").first()
        if not town_test:
            town_test = LocalityUnit(
                organization_id=org.id,
                unit_type="urban_local_body",
                parent_id=taluk.id,
                official_code="ULB-KA-571435",
                name_en="Pandavapura Town Municipality (Test)",
                name_kn="ಪಾಂಡವಪುರ",
                name_hi="पांडवपुरा",
                is_active=False,
            )
            db.add(town_test)
            db.flush()

        # 7. Departments
        dept_codes = [
            ("DEPT-ROADS", "Roads & Public Works", "ರಸ್ತೆಗಳು ಮತ್ತು ಲೋಕೋಪಯೋಗಿ", "सड़क एवं लोक निर्माण"),
            ("DEPT-WATER", "Water Supply & Sanitation", "ಕುಡಿಯುವ ನೀರು ಸರಬರಾಜು ಮತ್ತು ನೈರ್ಮಲ್ಯ", "जल आपूर्ति एवं स्वच्छता"),
            ("DEPT-WASTE", "Solid Waste Management", "ಘನತ್ಯಾಜ್ಯ ನಿರ್ವಹಣೆ", "ठोस अपशिष्ट प्रबंधन"),
            ("DEPT-LIGHTS", "Rural Streetlighting", "ಗ್ರಾಮೀಣ ಬೀದಿ ದೀಪಗಳು", "ग्रामीण स्ट्रीट लाइट"),
        ]
        dept_roads = None
        for d_code, en, kn, hi in dept_codes:
            d = db.query(Department).filter(Department.code == d_code).first()
            if not d:
                d = Department(
                    organization_id=org.id,
                    code=d_code,
                    name_en=en,
                    name_kn=kn,
                    name_hi=hi,
                    is_active=True,
                )
                db.add(d)
                db.flush()
            if d_code == "DEPT-ROADS":
                dept_roads = d

        # 8. Demo User Profiles
        default_pwd_hash = hash_password("DemoPassword123!")

        # Super Admin
        admin_profile = db.query(Profile).filter(Profile.email == "admin@fixproof.org").first()
        if not admin_profile:
            admin_profile = Profile(
                email="admin@fixproof.org",
                password_hash=default_pwd_hash,
                full_name=f"{generate_random_pdo_name()} (Taluk Officer)",
                preferred_locale="en",
                taluk="Belagavi Taluk",
                district="Belagavi District",
                state="Karnataka",
            )
            db.add(admin_profile)
            db.flush()
            db.add(RoleAssignment(profile_id=admin_profile.id, role="admin", is_active=True))

        # Reviewer 1 (Test GP Reviewer)
        rev1 = db.query(Profile).filter(Profile.email == "reviewer.gowdanahalli@fixproof.org").first()
        if not rev1:
            rev1 = Profile(
                email="reviewer.gowdanahalli@fixproof.org",
                password_hash=default_pwd_hash,
                full_name="Panchayat Reviewer (Demo)",
                preferred_locale="kn",
            )
            db.add(rev1)
            db.flush()
        
        rev1_asgn = db.query(RoleAssignment).filter(
            RoleAssignment.profile_id == rev1.id,
            RoleAssignment.role == "reviewer",
        ).first()
        if not rev1_asgn:
            db.add(RoleAssignment(profile_id=rev1.id, role="reviewer", jurisdiction_unit_id=gp_test.id, is_active=True, is_primary=False))
        else:
            rev1_asgn.jurisdiction_unit_id = gp_test.id
            rev1_asgn.is_active = True

        # Reviewer 2 (Town Reviewer)
        rev2 = db.query(Profile).filter(Profile.email == "reviewer.town@fixproof.org").first()
        if not rev2:
            rev2 = Profile(
                email="reviewer.town@fixproof.org",
                password_hash=default_pwd_hash,
                full_name="Town Reviewer (Demo)",
                preferred_locale="en",
            )
            db.add(rev2)
            db.flush()
        
        rev2_asgn = db.query(RoleAssignment).filter(
            RoleAssignment.profile_id == rev2.id,
            RoleAssignment.role == "reviewer",
        ).first()
        if not rev2_asgn:
            db.add(RoleAssignment(profile_id=rev2.id, role="reviewer", jurisdiction_unit_id=town_test.id, is_active=True, is_primary=False))
        else:
            rev2_asgn.jurisdiction_unit_id = town_test.id
            rev2_asgn.is_active = True

        # Field Worker
        worker_profile = db.query(Profile).filter(Profile.email == "worker.ramesh@fixproof.org").first()
        if not worker_profile:
            worker_profile = Profile(
                email="worker.ramesh@fixproof.org",
                password_hash=default_pwd_hash,
                full_name="Ramesh K.",
                preferred_locale="kn",
            )
            db.add(worker_profile)
            db.flush()
        
        worker_asgn = db.query(RoleAssignment).filter(
            RoleAssignment.profile_id == worker_profile.id,
            RoleAssignment.role == "worker",
        ).first()
        if not worker_asgn:
            db.add(RoleAssignment(profile_id=worker_profile.id, role="worker", department_id=dept_roads.id, jurisdiction_unit_id=gp_test.id, is_active=True, approval_status="APPROVED"))
        else:
            worker_asgn.jurisdiction_unit_id = gp_test.id
            worker_asgn.department_id = dept_roads.id
            worker_asgn.is_active = True
            worker_asgn.approval_status = "APPROVED"

        # Citizens
        cit1 = db.query(Profile).filter(Profile.email == "citizen.ananya@example.com").first()
        if not cit1:
            cit1 = Profile(
                email="citizen.ananya@example.com",
                password_hash=default_pwd_hash,
                full_name="Ananya Sharma",
                preferred_locale="en",
                taluk="Belagavi Taluk",
                district="Belagavi District",
                state="Karnataka",
            )
            db.add(cit1)
            db.flush()
            db.add(RoleAssignment(profile_id=cit1.id, role="citizen", is_active=True))

        db.commit()
        print("[Seed] Successfully seeded Belagavi Taluk with 9 active villages!")

    except Exception as e:
        db.rollback()
        print(f"[Seed] Error seeding database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
