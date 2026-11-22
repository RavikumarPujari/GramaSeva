"""
GramaSeva Clean Start Execution Script
Phase 1: Database Backup & Complete Clean Start

1. Fully backups all database tables to database/backups/full_db_backup_clean_start_<timestamp>.json.
2. Removes 100% of complaints and dependent records.
3. Retains exactly four accounts:
   - Super Admin: admin@fixproof.org (Ravikumar)
   - Village PDO: pdo.peeranwadi@belagavi.gov.in (Basavaraj Patil) -> Peeranwadi GP
   - Field Worker: worker.ramesh@fixproof.org (Ramesh K.) -> Peeranwadi GP
   - Citizen: citizen.ananya@example.com (Ananya Sharma)
4. Deletes test/demo locality units (Mandya/Gowdanahalli and Greenfield test units).
5. Cleans up orphaned media files from disk storage.
6. Verifies all post-cleanup invariants.
"""

import sys
import os
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/api")))

from app.core.database import SessionLocal
from app.models.users import Profile, RoleAssignment, Announcement, CitizenDocument
from app.models.localities import LocalityUnit, Department, Organization
from app.models.issues import (
    Issue,
    Submission,
    MediaAsset,
    Assignment,
    WorkCompletion,
    RepairReview,
    StatusEvent,
    Feedback,
    Notification,
    LocationAuditLog,
    DuplicateCandidate,
    RecurrenceCandidate,
    ModelRun,
    AIBeforeAfterAnalysis,
    Dispute,
    Job,
    AuditLog,
)

RETAINED_PROFILES = {
    "fa0e4619-beb9-48a5-87c0-8d5ee2c96fdb": {
        "email": "admin@fixproof.org",
        "full_name": "Ravikumar",
        "role": "admin",
        "jurisdiction_unit_id": None,
    },
    "c89c0b54-6807-4723-af19-f0354330295b": {
        "email": "pdo.peeranwadi@belagavi.gov.in",
        "full_name": "Basavaraj Patil",
        "role": "reviewer",
        "jurisdiction_unit_id": "dfd115e1-d6c3-490d-9c69-c92247019be0",  # Peeranwadi GP
    },
    "d6f79b20-2453-409a-8c39-29ab4896264a": {
        "email": "worker.ramesh@fixproof.org",
        "full_name": "Ramesh K.",
        "role": "worker",
        "jurisdiction_unit_id": "dfd115e1-d6c3-490d-9c69-c92247019be0",  # Peeranwadi GP
    },
    "4a74bb53-41af-420b-8bf2-ff8d16717841": {
        "email": "citizen.ananya@example.com",
        "full_name": "Ananya Sharma",
        "role": "citizen",
        "jurisdiction_unit_id": None,
    },
}

TEST_LOCALITY_CODES_OR_NAMES = [
    "GP-KA-571434", "VIL-GOWD", "VIL-MALL", "VIL-RAMA",
    "W1-GOWD", "W2-GOWD", "W3-GOWD", "ULB-KA-571435",
    "Gowdanahalli", "Malleshwarapuram", "Ramanagara",
    "Pandavapura", "Greenfield"
]

def serialize_row(obj):
    """Convert an SQLAlchemy model instance into a JSON-serializable dictionary."""
    d = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if isinstance(val, datetime):
            d[col.name] = val.isoformat()
        else:
            d[col.name] = val
    return d

def perform_backup(db, backup_dir="database/backups"):
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"full_db_backup_clean_start_{ts}.json")

    tables = [
        ("profiles", Profile),
        ("role_assignments", RoleAssignment),
        ("announcements", Announcement),
        ("citizen_documents", CitizenDocument),
        ("locality_units", LocalityUnit),
        ("departments", Department),
        ("organizations", Organization),
        ("issues", Issue),
        ("submissions", Submission),
        ("media_assets", MediaAsset),
        ("assignments", Assignment),
        ("work_completions", WorkCompletion),
        ("repair_reviews", RepairReview),
        ("status_events", StatusEvent),
        ("feedback", Feedback),
        ("notifications", Notification),
        ("location_audit_logs", LocationAuditLog),
        ("duplicate_candidates", DuplicateCandidate),
        ("recurrence_candidates", RecurrenceCandidate),
        ("model_runs", ModelRun),
        ("ai_before_after_analyses", AIBeforeAfterAnalysis),
        ("disputes", Dispute),
        ("jobs", Job),
        ("audit_logs", AuditLog),
    ]

    backup_data = {}
    for name, model in tables:
        rows = db.query(model).all()
        backup_data[name] = [serialize_row(r) for r in rows]
        print(f"Backed up {name}: {len(rows)} records")

    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, indent=2)

    print(f"\n[BACKUP SUCCESS] Saved full pre-cleanup snapshot to: {backup_path}")
    return backup_path

def execute_clean_start():
    db = SessionLocal()
    try:
        print("=" * 80)
        print("   GRAMASEVA — PHASE 1: DATABASE BACKUP & COMPLETE CLEAN START")
        print("=" * 80)

        # 1. Full Backup
        backup_file = perform_backup(db)

        # 2. Get list of media file paths before deleting records
        all_media = db.query(MediaAsset).all()
        media_storage_paths = [m.storage_path for m in all_media if m.storage_path]
        print(f"\nFound {len(media_storage_paths)} media asset files on disk to clean.")

        # 3. Transactional Deletion of Complaints and Dependent Records
        print("\nDeleting 100% of complaint and dependent records...")

        c_feedback = db.query(Feedback).delete(synchronize_session=False)
        c_ai_analyses = db.query(AIBeforeAfterAnalysis).delete(synchronize_session=False)
        c_reviews = db.query(RepairReview).delete(synchronize_session=False)
        c_completions = db.query(WorkCompletion).delete(synchronize_session=False)
        c_assignments = db.query(Assignment).delete(synchronize_session=False)
        c_status_events = db.query(StatusEvent).delete(synchronize_session=False)
        c_dup_candidates = db.query(DuplicateCandidate).delete(synchronize_session=False)
        c_rec_candidates = db.query(RecurrenceCandidate).delete(synchronize_session=False)
        c_model_runs = db.query(ModelRun).delete(synchronize_session=False)
        c_loc_logs = db.query(LocationAuditLog).delete(synchronize_session=False)
        c_disputes = db.query(Dispute).delete(synchronize_session=False)
        c_jobs = db.query(Job).delete(synchronize_session=False)
        c_notifications = db.query(Notification).delete(synchronize_session=False)
        c_audit_logs = db.query(AuditLog).delete(synchronize_session=False)
        c_media = db.query(MediaAsset).delete(synchronize_session=False)
        c_submissions = db.query(Submission).delete(synchronize_session=False)
        c_issues = db.query(Issue).delete(synchronize_session=False)

        print(f"Deleted records: issues={c_issues}, submissions={c_submissions}, media_assets={c_media}, "
              f"assignments={c_assignments}, work_completions={c_completions}, repair_reviews={c_reviews}, "
              f"status_events={c_status_events}, feedback={c_feedback}, notifications={c_notifications}, "
              f"model_runs={c_model_runs}, ai_analyses={c_ai_analyses}, duplicates={c_dup_candidates}")

        # 4. Clean extra citizen documents and announcements
        retained_ids = list(RETAINED_PROFILES.keys())
        c_docs = db.query(CitizenDocument).filter(~CitizenDocument.profile_id.in_(retained_ids)).delete(synchronize_session=False)
        c_announcements = db.query(Announcement).filter(~Announcement.sender_id.in_(retained_ids)).delete(synchronize_session=False)
        print(f"Cleaned non-retained documents ({c_docs}) and announcements ({c_announcements})")

        # 5. Delete all profiles and role assignments EXCEPT the 4 retained accounts
        c_roles_deleted = db.query(RoleAssignment).filter(~RoleAssignment.profile_id.in_(retained_ids)).delete(synchronize_session=False)
        c_profiles_deleted = db.query(Profile).filter(~Profile.id.in_(retained_ids)).delete(synchronize_session=False)
        print(f"Deleted {c_profiles_deleted} extra profiles and {c_roles_deleted} unused role assignments.")

        # 6. Ensure the 4 retained profiles and their role assignments are perfectly configured
        for pid, meta in RETAINED_PROFILES.items():
            prof = db.query(Profile).filter(Profile.id == pid).first()
            if not prof:
                raise RuntimeError(f"Retained profile {pid} ({meta['email']}) not found in DB!")
            
            # Update profile info
            prof.full_name = meta["full_name"]
            prof.email = meta["email"]
            prof.is_active = True
            
            # Ensure correct role assignment exists
            asgn = db.query(RoleAssignment).filter(RoleAssignment.profile_id == pid).first()
            if not asgn:
                asgn = RoleAssignment(
                    profile_id=pid,
                    role=meta["role"],
                    jurisdiction_unit_id=meta["jurisdiction_unit_id"],
                    is_active=True,
                )
                db.add(asgn)
            else:
                asgn.role = meta["role"]
                asgn.jurisdiction_unit_id = meta["jurisdiction_unit_id"]
                asgn.is_active = True

        print("Configured exactly 4 retained accounts:")
        for pid, meta in RETAINED_PROFILES.items():
            print(f"   - [{meta['role'].upper()}] {meta['email']} ({meta['full_name']}) -> Jurisdiction: {meta['jurisdiction_unit_id']}")

        # 7. Delete Test / Demo Locality Units (Mandya/Gowdanahalli and Greenfield)
        test_units = db.query(LocalityUnit).filter(
            (LocalityUnit.official_code.in_(["GP-KA-571434", "VIL-GOWD", "VIL-MALL", "VIL-RAMA", "W1-GOWD", "W2-GOWD", "W3-GOWD", "ULB-KA-571435"])) |
            (LocalityUnit.name_en.like("%Greenfield%")) |
            (LocalityUnit.name_en.like("%Gowdanahalli%")) |
            (LocalityUnit.name_en.like("%Pandavapura%")) |
            (LocalityUnit.name_en.like("%Malleshwarapuram%")) |
            (LocalityUnit.name_en.like("%Ramanagara%"))
        ).all()
        test_unit_ids = [u.id for u in test_units]
        print(f"\nIdentified {len(test_units)} test locality units for removal:")
        for u in test_units:
            print(f"   - [{u.unit_type}] {u.name_en} (ID: {u.id})")

        # Delete in order: wards first, then villages, then GPs/ULBs
        for u_type in ["ward", "village", "urban_local_body", "gram_panchayat"]:
            for u in test_units:
                if u.unit_type == u_type:
                    db.query(LocalityUnit).filter(LocalityUnit.id == u.id).delete(synchronize_session=False)

        # Commit all changes atomically
        db.commit()
        print("\n[TRANSACTION COMMITTED] All deletions committed successfully.")

        # 8. Clean up media storage files on disk (preserving test images)
        cleaned_files_count = 0
        for p in media_storage_paths:
            if p and os.path.exists(p) and not p.endswith("road_pothole_sample.jpg") and not p.endswith(".gitkeep"):
                try:
                    os.remove(p)
                    cleaned_files_count += 1
                except Exception as ex:
                    print(f"Warning: could not delete file {p}: {ex}")
        print(f"Cleaned {cleaned_files_count} orphaned media files from disk storage.")

        # 9. Verification of Post-Cleanup State
        print("\n" + "=" * 80)
        print("   FINAL VERIFICATION OF CLEAN DATABASE STATE")
        print("=" * 80)

        remaining_profiles = db.query(Profile).all()
        remaining_roles = db.query(RoleAssignment).all()
        remaining_issues = db.query(Issue).count()
        remaining_submissions = db.query(Submission).count()
        remaining_media = db.query(MediaAsset).count()
        remaining_assignments = db.query(Assignment).count()
        remaining_localities = db.query(LocalityUnit).all()

        print(f"Profiles count: {len(remaining_profiles)} (EXPECTED: 4)")
        assert len(remaining_profiles) == 4, f"Expected 4 profiles, found {len(remaining_profiles)}"
        for p in remaining_profiles:
            r = db.query(RoleAssignment).filter(RoleAssignment.profile_id == p.id).first()
            print(f"   ✓ {p.email} | {p.full_name} | Role: {r.role if r else 'None'} | Jurisdiction: {r.jurisdiction_unit_id if r else 'None'}")

        print(f"Role Assignments count: {len(remaining_roles)} (EXPECTED: 4)")
        assert len(remaining_roles) == 4, f"Expected 4 role assignments, found {len(remaining_roles)}"

        print(f"Issues count: {remaining_issues} (EXPECTED: 0)")
        assert remaining_issues == 0, f"Expected 0 issues, found {remaining_issues}"

        print(f"Submissions count: {remaining_submissions} (EXPECTED: 0)")
        assert remaining_submissions == 0, f"Expected 0 submissions, found {remaining_submissions}"

        print(f"Media Assets count: {remaining_media} (EXPECTED: 0)")
        assert remaining_media == 0, f"Expected 0 media assets, found {remaining_media}"

        print(f"Assignments count: {remaining_assignments} (EXPECTED: 0)")
        assert remaining_assignments == 0, f"Expected 0 assignments, found {remaining_assignments}"

        print(f"Remaining Locality Units: {len(remaining_localities)}")
        for u in remaining_localities:
            print(f"   - [{u.unit_type}] {u.name_en} (ID: {u.id}, parent: {u.parent_id})")

        # Verify Belagavi hierarchy is intact
        belagavi_taluk = db.query(LocalityUnit).filter(LocalityUnit.name_en == "Belagavi Taluk").first()
        peeranwadi_gp = db.query(LocalityUnit).filter(LocalityUnit.id == "dfd115e1-d6c3-490d-9c69-c92247019be0").first()
        assert belagavi_taluk is not None, "Belagavi Taluk missing!"
        assert peeranwadi_gp is not None, "Peeranwadi GP missing!"
        print("\n✓ Belagavi administrative hierarchy verified intact.")
        print(f"✓ Backup file saved: {backup_file}")
        print("\nCLEAN START COMPLETED SUCCESSFULLY.")

    except Exception as e:
        db.rollback()
        print(f"\n[FATAL ERROR] Cleanup failed, transaction rolled back: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    execute_clean_start()
