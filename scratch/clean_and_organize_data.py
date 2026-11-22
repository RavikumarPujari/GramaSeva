import os
import sys
import uuid
from io import BytesIO
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../services/api")))

from app.core.database import SessionLocal
from app.models.localities import LocalityUnit
from app.models.users import Profile, RoleAssignment
from app.models.issues import Issue, Submission, MediaAsset
from app.auth.security import hash_password
from app.storage.service import storage_service

def clean_and_organize():
    db = SessionLocal()
    try:
        print("=== Step 1: Physical Media Files for Missing Paths ===")
        # Ensure base directories exist
        test_dir = os.path.join(storage_service.base_path, "test")
        private_dir = os.path.join(storage_service.base_path, "private")
        os.makedirs(test_dir, exist_ok=True)
        os.makedirs(private_dir, exist_ok=True)

        # Generate realistic fallback images
        files_to_create = [
            ("test/citizen_before.jpg", "CIVIC DEFECT - REPORTED ISSUE", (180, 70, 60)),
            ("test/worker_after.jpg", "REPAIR COMPLETED - VERIFIED WORK", (50, 140, 90)),
            ("private/test_evidence.jpg", "EVIDENCE PHOTOGRAPH - VERIFIED", (70, 90, 130)),
            ("private/test_crack.jpg", "ROAD CRACK EVIDENCE - VERIFIED", (120, 100, 80)),
        ]

        for rel_path, banner, color in files_to_create:
            full_path = os.path.abspath(os.path.join(storage_service.base_path, rel_path))
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            if not os.path.exists(full_path):
                img = Image.new("RGB", (640, 480), color=color)
                draw = ImageDraw.Draw(img)
                draw.rectangle([10, 10, 630, 70], fill=(20, 30, 45))
                draw.text((25, 30), banner, fill=(255, 255, 255))
                draw.rectangle([30, 100, 610, 380], fill=(0, 0, 0, 100))
                draw.text((50, 150), "GramaSeva Civic Infrastructure Audit Record", fill=(255, 255, 255))
                draw.text((50, 200), f"File: {rel_path}", fill=(200, 220, 240))
                draw.rectangle([10, 420, 630, 470], fill=(20, 30, 45))
                draw.text((25, 435), "BELAGAVI TALUK CIVIC WORKS TRANSPARENCY", fill=(255, 220, 100))
                img.save(full_path, "JPEG", quality=85)
                print(f"Created media file: {rel_path}")
            else:
                print(f"Already exists: {rel_path}")

        print("\n=== Step 2: Category Normalization ===")
        category_map = {
            "street_light": "streetlight",
            "garbage_dump": "garbage",
            "water_leakage": "water_leak",
            "waterlogging": "drainage",
            "public_sanitation": "public_facility",
        }
        for old_cat, new_cat in category_map.items():
            updated_issues = db.query(Issue).filter(Issue.category == old_cat).update({"category": new_cat})
            updated_subs = db.query(Submission).filter(Submission.category == old_cat).update({"category": new_cat})
            if updated_issues or updated_subs:
                print(f"Normalized '{old_cat}' -> '{new_cat}': {updated_issues} issues, {updated_subs} submissions")
        db.commit()

        print("\n=== Step 3: Clean Obsolete Greenfield Test Localities ===")
        greenfields = db.query(LocalityUnit).filter(LocalityUnit.name_en.ilike("%Greenfield Village%")).all()
        print(f"Found {len(greenfields)} Greenfield test localities.")
        for gf in greenfields:
            # Reassign any issues to Peeranwadi
            peeranwadi = db.query(LocalityUnit).filter(LocalityUnit.name_en == "Peeranwadi").first()
            if peeranwadi:
                db.query(Issue).filter(Issue.locality_unit_id == gf.id).update({"locality_unit_id": peeranwadi.id})
                db.query(Submission).filter(Submission.locality_unit_id == gf.id).update({"locality_unit_id": peeranwadi.id})
            # Delete child wards of this greenfield
            child_wards = db.query(LocalityUnit).filter(LocalityUnit.parent_id == gf.id).all()
            for w in child_wards:
                db.delete(w)
            db.delete(gf)
        db.commit()
        print("Cleaned up Greenfield test localities and associated wards.")

        print("\n=== Step 4: Clean Duplicate Peeranwadi PDOs ===")
        peeranwadi = db.query(LocalityUnit).filter(LocalityUnit.name_en == "Peeranwadi").first()
        if peeranwadi:
            # Keep one primary PDO: pdo.peeranwadi@belagavi.gov.in
            keep_profile = db.query(Profile).filter(Profile.email == "pdo.peeranwadi@belagavi.gov.in").first()
            if not keep_profile:
                keep_profile = Profile(
                    id=str(uuid.uuid4()),
                    email="pdo.peeranwadi@belagavi.gov.in",
                    password_hash=hash_password("DemoPassword123!"),
                    full_name="Basavaraj Patil",
                    phone_number="+91 9845112233",
                    preferred_locale="en",
                    taluk="Belagavi Taluk",
                    is_active=True,
                )
                db.add(keep_profile)
                db.flush()

            # Find all other duplicate pdo.peeranwadi.* accounts
            dup_pdos = db.query(Profile).filter(
                Profile.email.like("pdo.peeranwadi.%@belagavi.gov.in"),
                Profile.id != keep_profile.id,
            ).all()
            print(f"Found {len(dup_pdos)} duplicate test PDO accounts for Peeranwadi.")
            for p in dup_pdos:
                db.query(RoleAssignment).filter(RoleAssignment.profile_id == p.id).delete()
                db.delete(p)
            db.commit()

        print("\n=== Step 5: Assign Exactly One Primary PDO to Each of the 9 Belagavi Villages ===")
        village_pdo_data = [
            ("Peeranwadi", "pdo.peeranwadi@belagavi.gov.in", "Basavaraj Patil", "+91 9845112233"),
            ("Kuttalawadi", "pdo.kuttalawadi@belagavi.gov.in", "Suresh Deshmukh", "+91 9845223344"),
            ("Zad-Shahapur", "pdo.zadshahapur@belagavi.gov.in", "Kiran Hegde", "+91 9845334455"),
            ("Santibastawad", "pdo.santibastawad@belagavi.gov.in", "Geetha Kulkarni", "+91 9845445566"),
            ("Yellur", "pdo.yellur@belagavi.gov.in", "Manjunath Biradar", "+91 9845556677"),
            ("Sulge (Yellur)", "pdo.sulge@belagavi.gov.in", "Pooja Chavan", "+91 9845667788"),
            ("Mandoli", "pdo.mandoli@belagavi.gov.in", "Vinayak Naik", "+91 9845778899"),
            ("Waghawade", "pdo.waghawade@belagavi.gov.in", "Mallikarjun Angadi", "+91 9845889900"),
            ("Navage", "pdo.navage@belagavi.gov.in", "Sunita Shinde", "+91 9845990011"),
        ]

        pwd_hash = hash_password("DemoPassword123!")

        for v_name, email, full_name, phone in village_pdo_data:
            village = db.query(LocalityUnit).filter(LocalityUnit.name_en.ilike(f"%{v_name}%")).first()
            if not village:
                print(f"Warning: Village '{v_name}' not found!")
                continue

            # Ensure profile exists
            prof = db.query(Profile).filter(Profile.email == email).first()
            if not prof:
                prof = Profile(
                    id=str(uuid.uuid4()),
                    email=email,
                    password_hash=pwd_hash,
                    full_name=full_name,
                    phone_number=phone,
                    preferred_locale="en",
                    taluk="Belagavi Taluk",
                    is_active=True,
                )
                db.add(prof)
                db.flush()
                print(f"Created PDO profile: {full_name} ({email})")
            else:
                prof.is_active = True
                prof.full_name = full_name
                prof.password_hash = pwd_hash

            # Clear any other primary reviewer assignments for this village
            db.query(RoleAssignment).filter(
                RoleAssignment.jurisdiction_unit_id == village.id,
                RoleAssignment.role == "reviewer",
            ).update({"is_primary": False})

            # Upsert role assignment
            asgn = db.query(RoleAssignment).filter(
                RoleAssignment.profile_id == prof.id,
                RoleAssignment.role == "reviewer",
            ).first()
            if not asgn:
                asgn = RoleAssignment(
                    id=str(uuid.uuid4()),
                    profile_id=prof.id,
                    role="reviewer",
                    jurisdiction_unit_id=village.id,
                    is_primary=True,
                    is_active=True,
                    approval_status="APPROVED",
                )
                db.add(asgn)
            else:
                asgn.jurisdiction_unit_id = village.id
                asgn.is_primary = True
                asgn.is_active = True

            print(f"Assigned {full_name} as Primary PDO for {village.name_en}")

        print("\n=== Step 6: Create 2 Unassigned PDO Accounts for Super Admin Management ===")
        unassigned_pdos = [
            ("pdo.trainee1@belagavi.gov.in", "Pradeep Kambale", "+91 9845001122"),
            ("pdo.probationary@belagavi.gov.in", "Anand Kittur", "+91 9845002233"),
        ]
        for email, full_name, phone in unassigned_pdos:
            p = db.query(Profile).filter(Profile.email == email).first()
            if not p:
                p = Profile(
                    id=str(uuid.uuid4()),
                    email=email,
                    password_hash=pwd_hash,
                    full_name=full_name,
                    phone_number=phone,
                    preferred_locale="en",
                    taluk="Belagavi Taluk",
                    is_active=True,
                )
                db.add(p)
                db.flush()

            ra = db.query(RoleAssignment).filter(RoleAssignment.profile_id == p.id, RoleAssignment.role == "reviewer").first()
            if not ra:
                ra = RoleAssignment(
                    id=str(uuid.uuid4()),
                    profile_id=p.id,
                    role="reviewer",
                    jurisdiction_unit_id=None,
                    is_primary=False,
                    is_active=True,
                    approval_status="APPROVED",
                )
                db.add(ra)
            else:
                ra.jurisdiction_unit_id = None
                ra.is_primary = False
                ra.is_active = True
            print(f"Ensured unassigned PDO: {full_name} ({email})")

        db.commit()
        print("\n=== Successfully completed clean up and database organization! ===")

    except Exception as e:
        db.rollback()
        print("Error during clean up:", e)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    clean_and_organize()
