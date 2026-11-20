"""
FixProof Demo Seed Script
Populates standardized pilot demo hierarchy, departments, and scoped staff profiles.
All records are explicitly labeled as demo/pilot data per Section 0.2.
"""

import sys
import os

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

def seed_database():
    print("[Seed] Creating all tables if not present...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if already seeded
        existing_org = db.query(Organization).filter(Organization.code == "ZP-MANDYA-PILOT").first()
        if existing_org:
            from app.models.issues import Asset
            if db.query(Asset).count() == 0:
                print("[Seed] Seeding verified assets into existing pilot DB...")
                first_ward = db.query(LocalityUnit).filter(LocalityUnit.unit_type == "ward").first()
                first_ward_id = first_ward.id if first_ward else None

                asset1 = Asset(
                    official_code="ASSET-RD-01",
                    name_en="Primary School Main Road",
                    name_kn="ಪ್ರಾಥಮಿಕ ಶಾಲಾ ಮುಖ್ಯ ರಸ್ತೆ",
                    name_hi="प्राथमिक विद्यालय मुख्य सड़क",
                    category="road_damage",
                    locality_unit_id=first_ward_id,
                    latitude=12.5205,
                    longitude=76.8905,
                    condition_status="OPERATIONAL",
                )
                asset2 = Asset(
                    official_code="ASSET-WP-01",
                    name_en="Ward 1 Drinking Water Pipeline Junction",
                    name_kn="ವಾರ್ಡ್ 1 ಕುಡಿಯುವ ನೀರಿನ ಪೈಪ್‌ಲೈನ್ ಜಂಕ್ಷನ್",
                    name_hi="वार्ड 1 पेयजल पाइपलाइन जंक्शन",
                    category="water_leak",
                    locality_unit_id=first_ward_id,
                    latitude=12.5215,
                    longitude=76.8915,
                    condition_status="OPERATIONAL",
                )
                asset3 = Asset(
                    official_code="ASSET-SL-01",
                    name_en="Temple Square High-Mast Street Light",
                    name_kn="ದೇವಾಲಯ ವೃತ್ತದ ಹೈ-ಮಾಸ್ಟ್ ಬೀದಿ ದೀಪ",
                    name_hi="मंदिर चौराहा हाई-मास्ट स्ट्रीट लाइट",
                    category="streetlight",
                    locality_unit_id=first_ward_id,
                    latitude=12.5220,
                    longitude=76.8920,
                    condition_status="OPERATIONAL",
                )
                db.add_all([asset1, asset2, asset3])
                db.commit()
                print("[Seed] Successfully seeded verified public assets into pilot DB.")
            print("[Seed] Database already contains pilot data. Skipping duplicate seed.")
            return

        print("[Seed] Seeding pilot organization...")
        org = Organization(
            name="Mandya District Panchayat (Demo Pilot)",
            code="ZP-MANDYA-PILOT",
            description="Civic pilot organization for rural and semi-urban infrastructure triage.",
            is_active=True,
        )
        db.add(org)
        db.flush()

        # 1. State
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

        # 2. District
        district = LocalityUnit(
            organization_id=org.id,
            unit_type="district",
            parent_id=state.id,
            official_code="KA-MND",
            name_en="Mandya District",
            name_kn="ಮಂಡ್ಯ ಜಿಲ್ಲೆ",
            name_hi="मंड्या जिला",
            is_active=True,
        )
        db.add(district)
        db.flush()

        # 3. Taluk
        taluk = LocalityUnit(
            organization_id=org.id,
            unit_type="taluk",
            parent_id=district.id,
            official_code="KA-MND-PDP",
            name_en="Pandavapura Taluk",
            name_kn="ಪಾಂಡವಪುರ ತಾಲೂಕು",
            name_hi="पांडवपुरा तालुक",
            is_active=True,
        )
        db.add(taluk)
        db.flush()

        # 4. Primary Gram Panchayat (Gowdanahalli GP)
        gp_gowdanahalli = LocalityUnit(
            organization_id=org.id,
            unit_type="gram_panchayat",
            parent_id=taluk.id,
            official_code="GP-KA-571434",
            name_en="Gowdanahalli Gram Panchayat",
            name_kn="ಗೌಡನಹಳ್ಳಿ ಗ್ರಾಮ ಪಂಚಾಯತಿ",
            name_hi="गौडनहल्ली ग्राम पंचायत",
            is_active=True,
        )
        db.add(gp_gowdanahalli)

        # 4b. Secondary Town Municipality (for cross-jurisdiction testing)
        town_pandavapura = LocalityUnit(
            organization_id=org.id,
            unit_type="urban_local_body",
            parent_id=taluk.id,
            official_code="ULB-KA-571435",
            name_en="Pandavapura Town Municipality",
            name_kn="ಪಾಂಡವಪುರ ಪುರಸಭೆ",
            name_hi="पांडवपुरा नगर पालिका",
            is_active=True,
        )
        db.add(town_pandavapura)
        db.flush()

        # 5. Villages under Gowdanahalli GP
        villages_data = [
            {
                "code": "VIL-GOWD",
                "en": "Gowdanahalli",
                "kn": "ಗೌಡನಹಳ್ಳಿ",
                "hi": "गौडनहल्ली",
                "wards": [
                    {"code": "W1-GOWD", "en": "Ward 1 — Post Office Area", "kn": "ವಾರ್ಡ್ ೧ — ಅಂಚೆ ಕಚೇರಿ ಪ್ರದೇಶ", "hi": "वार्ड १ — डाकघर क्षेत्र"},
                    {"code": "W2-GOWD", "en": "Ward 2 — Primary School Road", "kn": "ವಾರ್ಡ್ ೨ — ಪ್ರಾಥಮಿಕ ಶಾಲೆ ರಸ್ತೆ", "hi": "वार्ड २ — प्राथमिक विद्यालय मार्ग"},
                    {"code": "W3-GOWD", "en": "Ward 3 — Temple Street", "kn": "ವಾರ್ಡ್ ೩ — ದೇವಾಲಯ ರಸ್ತೆ", "hi": "वार्ड ३ — मंदिर मार्ग"},
                ],
            },
            {
                "code": "VIL-MALL",
                "en": "Malleshwarapuram",
                "kn": "ಮಲ್ಲೇಶ್ವರಪುರಂ",
                "hi": "मल्लेश्वरपुरम",
                "wards": [
                    {"code": "W1-MALL", "en": "Ward 1 — Lakeview Road", "kn": "ವಾರ್ಡ್ ೧ — ಕೆರೆ ರಸ್ತೆ", "hi": "वार्ड १ — झील मार्ग"},
                    {"code": "W2-MALL", "en": "Ward 2 — Commercial Cross", "kn": "ವಾರ್ಡ್ ೨ — ವಾಣಿಜ್ಯ ಕ್ರಾಸ್", "hi": "वार्ड २ — वाणिज्यिक क्रॉस"},
                ],
            },
            {
                "code": "VIL-RAMA",
                "en": "Ramanagara",
                "kn": "ರಾಮನಗರ",
                "hi": "रामनगर",
                "wards": [
                    {"code": "W1-RAMA", "en": "Ward 1 — Main Bazaar", "kn": "ವಾರ್ಡ್ ೧ — ಮುಖ್ಯ ಬಜಾರ್", "hi": "वार्ड १ — मुख्य बाजार"},
                    {"code": "W2-RAMA", "en": "Ward 2 — Hospital Road", "kn": "ವಾರ್ಡ್ ೨ — ಆಸ್ಪತ್ರೆ ರಸ್ತೆ", "hi": "वार्ड २ — अस्पताल मार्ग"},
                ],
            },
        ]

        for v_data in villages_data:
            village = LocalityUnit(
                organization_id=org.id,
                unit_type="village",
                parent_id=gp_gowdanahalli.id,
                official_code=v_data["code"],
                name_en=v_data["en"],
                name_kn=v_data["kn"],
                name_hi=v_data["hi"],
                is_active=True,
            )
            db.add(village)
            db.flush()

            for w_data in v_data["wards"]:
                ward = LocalityUnit(
                    organization_id=org.id,
                    unit_type="ward",
                    parent_id=village.id,
                    official_code=w_data["code"],
                    name_en=w_data["en"],
                    name_kn=w_data["kn"],
                    name_hi=w_data["hi"],
                    is_active=True,
                )
                db.add(ward)

        # 6. Departments
        dept_roads = Department(
            organization_id=org.id,
            code="DEPT-ROADS",
            name_en="Roads & Public Works",
            name_kn="ರಸ್ತೆಗಳು ಮತ್ತು ಲೋಕೋಪಯೋಗಿ",
            name_hi="सड़क एवं लोक निर्माण",
            is_active=True,
        )
        dept_water = Department(
            organization_id=org.id,
            code="DEPT-WATER",
            name_en="Water Supply & Sanitation",
            name_kn="ಕುಡಿಯುವ ನೀರು ಸರಬರಾಜು ಮತ್ತು ನೈರ್ಮಲ್ಯ",
            name_hi="जल आपूर्ति एवं स्वच्छता",
            is_active=True,
        )
        dept_waste = Department(
            organization_id=org.id,
            code="DEPT-WASTE",
            name_en="Solid Waste Management",
            name_kn="ಘನತ್ಯಾಜ್ಯ ನಿರ್ವಹಣೆ",
            name_hi="ठोस अपशिष्ट प्रबंधन",
            is_active=True,
        )
        db.add_all([dept_roads, dept_water, dept_waste])
        db.flush()

        # 7. Seed Demo Users & Scoped Roles
        default_pwd_hash = hash_password("DemoPassword123!")

        # 7a. Admin & Supervisor
        admin_profile = Profile(
            email="admin@fixproof.org",
            password_hash=default_pwd_hash,
            full_name="Platform Administrator (Demo)",
            preferred_locale="en",
        )
        supervisor_profile = Profile(
            email="supervisor.mandya@fixproof.org",
            password_hash=default_pwd_hash,
            full_name="Mandya Ward Supervisor (Demo)",
            preferred_locale="en",
        )
        db.add_all([admin_profile, supervisor_profile])
        db.flush()
        db.add(RoleAssignment(profile_id=admin_profile.id, role="admin", is_active=True))
        db.add(RoleAssignment(profile_id=supervisor_profile.id, role="admin", is_active=True))

        # 7b. Reviewer 1 (Scoped to Gowdanahalli GP)
        rev1_profile = Profile(
            email="reviewer.gowdanahalli@fixproof.org",
            password_hash=default_pwd_hash,
            full_name="Panchayat Reviewer Gowdanahalli (Demo)",
            preferred_locale="kn",
        )
        db.add(rev1_profile)
        db.flush()
        db.add(
            RoleAssignment(
                profile_id=rev1_profile.id,
                role="reviewer",
                jurisdiction_unit_id=gp_gowdanahalli.id,
                is_active=True,
            )
        )

        # 7c. Reviewer 2 (Scoped to Pandavapura Town)
        rev2_profile = Profile(
            email="reviewer.town@fixproof.org",
            password_hash=default_pwd_hash,
            full_name="Town Reviewer Pandavapura (Demo)",
            preferred_locale="en",
        )
        db.add(rev2_profile)
        db.flush()
        db.add(
            RoleAssignment(
                profile_id=rev2_profile.id,
                role="reviewer",
                jurisdiction_unit_id=town_pandavapura.id,
                is_active=True,
            )
        )

        # 7d. Field Worker (Civil Works, Gowdanahalli)
        worker_profile = Profile(
            email="worker.ramesh@fixproof.org",
            password_hash=default_pwd_hash,
            full_name="Ramesh K. (Field Worker Demo)",
            preferred_locale="kn",
        )
        db.add(worker_profile)
        db.flush()
        db.add(
            RoleAssignment(
                profile_id=worker_profile.id,
                role="worker",
                department_id=dept_roads.id,
                jurisdiction_unit_id=gp_gowdanahalli.id,
                is_active=True,
            )
        )

        # 7e. Citizens
        citizen_profile1 = Profile(
            email="citizen.ananya@example.com",
            password_hash=default_pwd_hash,
            full_name="Ananya Sharma (Citizen Demo)",
            preferred_locale="en",
        )
        citizen_profile2 = Profile(
            email="citizen.suresh@example.com",
            password_hash=default_pwd_hash,
            full_name="Suresh Gowda (Citizen Demo)",
            preferred_locale="kn",
        )
        db.add_all([citizen_profile1, citizen_profile2])
        db.flush()
        db.add(RoleAssignment(profile_id=citizen_profile1.id, role="citizen", is_active=True))
        db.add(RoleAssignment(profile_id=citizen_profile2.id, role="citizen", is_active=True))

        # 8. Seed Verified Public Infrastructure Assets (Phase 8)
        from app.models.issues import Asset
        if db.query(Asset).count() == 0:
            print("[Seed] Seeding verified public infrastructure assets...")
            first_ward = db.query(LocalityUnit).filter(LocalityUnit.unit_type == "ward").first()
            first_ward_id = first_ward.id if first_ward else None

            asset1 = Asset(
                official_code="ASSET-RD-01",
                name_en="Primary School Main Road",
                name_kn="ಪ್ರಾಥಮಿಕ ಶಾಲಾ ಮುಖ್ಯ ರಸ್ತೆ",
                name_hi="प्राथमिक विद्यालय मुख्य सड़क",
                category="road_damage",
                locality_unit_id=first_ward_id,
                latitude=12.5205,
                longitude=76.8905,
                condition_status="OPERATIONAL",
            )
            asset2 = Asset(
                official_code="ASSET-WP-01",
                name_en="Ward 1 Drinking Water Pipeline Junction",
                name_kn="ವಾರ್ಡ್ 1 ಕುಡಿಯುವ ನೀರಿನ ಪೈಪ್‌ಲೈನ್ ಜಂಕ್ಷನ್",
                name_hi="वार्ड 1 पेयजल पाइपलाइन जंक्शन",
                category="water_leak",
                locality_unit_id=first_ward_id,
                latitude=12.5215,
                longitude=76.8915,
                condition_status="OPERATIONAL",
            )
            asset3 = Asset(
                official_code="ASSET-SL-01",
                name_en="Temple Square High-Mast Street Light",
                name_kn="ದೇವಾಲಯ ವೃತ್ತದ ಹೈ-ಮಾಸ್ಟ್ ಬೀದಿ ದೀಪ",
                name_hi="मंदिर चौराहा हाई-मास्ट स्ट्रीट लाइट",
                category="streetlight",
                locality_unit_id=first_ward_id,
                latitude=12.5220,
                longitude=76.8920,
                condition_status="OPERATIONAL",
            )
            db.add_all([asset1, asset2, asset3])

        db.commit()
        print("[Seed] Successfully seeded pilot database with organization, hierarchy, departments, demo users, and assets!")

    except Exception as e:
        db.rollback()
        print(f"[Seed] Error seeding database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
