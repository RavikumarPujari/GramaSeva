import sys
import os
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/api")))

from app.core.database import SessionLocal
from app.models import Profile, RoleAssignment, LocalityUnit
from app.models.issues import Issue, Submission, Assignment, RepairReview, StatusEvent, AuditLog

def clean_demo_data():
    db = SessionLocal()
    try:
        # Target PDO profiles to remove
        target_emails = [
            'pdo.peeranwadi@belagavi.gov.in',
            'pdo.kuttalawadi@belagavi.gov.in',
            'pdo.zadshahapur@belagavi.gov.in',
            'pdo.santibastawad@belagavi.gov.in',
            'pdo.yellur@belagavi.gov.in',
            'pdo.sulge@belagavi.gov.in',
            'pdo.mandoli@belagavi.gov.in',
            'pdo.waghawade@belagavi.gov.in',
            'pdo.navage@belagavi.gov.in',
            'pdo.trainee1@belagavi.gov.in',
            'pdo.probationary@belagavi.gov.in',
            'pdo.kiniye@belagavi.gov.in',
            'pdo.karle@belagavi.gov.in',
        ]
        
        all_pdo_profiles = db.query(Profile).filter(
            (Profile.email.in_(target_emails)) | 
            (Profile.email.like('pdo.peeranwadi.%'))
        ).all()

        test_units = db.query(LocalityUnit).filter(LocalityUnit.name_en.like('%Greenfield%')).all()

        print(f"[Backup] Found {len(all_pdo_profiles)} demo PDO profiles.")
        print(f"[Backup] Found {len(test_units)} demo test locality units.")

        # Full backup
        backup_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'pdo_profiles': [
                {
                    'id': p.id,
                    'email': p.email,
                    'full_name': p.full_name,
                    'role_assignments': [
                        {
                            'role': r.role,
                            'jurisdiction_unit_id': r.jurisdiction_unit_id,
                            'is_active': r.is_active,
                        }
                        for r in p.role_assignments
                    ]
                }
                for p in all_pdo_profiles
            ],
            'test_units': [
                {
                    'id': u.id,
                    'official_code': u.official_code,
                    'name_en': u.name_en,
                    'unit_type': u.unit_type,
                    'parent_id': u.parent_id,
                }
                for u in test_units
            ]
        }

        backup_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../backups"))
        os.makedirs(backup_dir, exist_ok=True)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"backup_before_demo_cleanup_{timestamp_str}.json")
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=2)
        print(f"[Backup] Data safely backed up to {backup_path}")

        # Safe removal of foreign-key references before deleting profiles
        pdo_ids = [p.id for p in all_pdo_profiles]
        if pdo_ids:
            # Nullify reviewed_by_id in issues
            db.query(Issue).filter(Issue.reviewed_by_id.in_(pdo_ids)).update({Issue.reviewed_by_id: None}, synchronize_session=False)
            # Nullify rejection_by_id in issues
            db.query(Issue).filter(Issue.rejection_by_id.in_(pdo_ids)).update({Issue.rejection_by_id: None}, synchronize_session=False)
            # Nullify assigned_by_id in assignments
            db.query(Assignment).filter(Assignment.assigned_by_id.in_(pdo_ids)).update({Assignment.assigned_by_id: None}, synchronize_session=False)
            # Nullify actor_profile_id in StatusEvent
            db.query(StatusEvent).filter(StatusEvent.actor_profile_id.in_(pdo_ids)).update({StatusEvent.actor_profile_id: None}, synchronize_session=False)
            # Nullify actor_profile_id in AuditLog
            db.query(AuditLog).filter(AuditLog.actor_profile_id.in_(pdo_ids)).update({AuditLog.actor_profile_id: None}, synchronize_session=False)
            # Delete repair reviews by these PDOs if any
            db.query(RepairReview).filter(RepairReview.reviewer_profile_id.in_(pdo_ids)).delete(synchronize_session=False)
            # Delete role assignments
            db.query(RoleAssignment).filter(RoleAssignment.profile_id.in_(pdo_ids)).delete(synchronize_session=False)
            # Delete profiles
            for p in all_pdo_profiles:
                db.delete(p)

        # Delete test locality units (wards first then villages)
        unit_ids = [u.id for u in test_units]
        if unit_ids:
            # Check if any issue or submission references these units
            db.query(Issue).filter(Issue.locality_unit_id.in_(unit_ids)).update({Issue.locality_unit_id: None}, synchronize_session=False)
            db.query(Submission).filter(Submission.locality_unit_id.in_(unit_ids)).update({Submission.locality_unit_id: None}, synchronize_session=False)
            # Delete wards first
            db.query(LocalityUnit).filter(LocalityUnit.id.in_(unit_ids), LocalityUnit.unit_type == "ward").delete(synchronize_session=False)
            # Delete villages
            db.query(LocalityUnit).filter(LocalityUnit.id.in_(unit_ids), LocalityUnit.unit_type == "village").delete(synchronize_session=False)

        db.commit()
        print(f"[Cleanup] Successfully removed {len(all_pdo_profiles)} demo PDO profiles and {len(test_units)} demo locality units.")

    except Exception as e:
        db.rollback()
        print(f"[Cleanup] Error during demo cleanup: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    clean_demo_data()
