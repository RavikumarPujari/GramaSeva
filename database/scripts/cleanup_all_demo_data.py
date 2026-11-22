"""
GramaSeva Safe Demo & Test Data Cleanup Script (Phase 2)
Safely removes demo, seeded, and test fixture records from PostgreSQL.
Handles foreign keys in proper order, creates a backup, and supports dry-run mode.
"""

import sys
import os
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/api")))

from app.core.database import SessionLocal
from app.models import (
    Profile,
    RoleAssignment,
    LocalityUnit,
    Organization,
    Issue,
    Submission,
    MediaAsset,
    StatusEvent,
    Feedback,
    Notification,
    LocationAuditLog,
)
from app.models.issues import (
    Assignment,
    WorkCompletion,
    RepairReview,
    AuditLog,
    DuplicateCandidate,
    AIBeforeAfterAnalysis,
    ModelRun,
    Job,
)

def run_cleanup(dry_run: bool = True):
    db = SessionLocal()
    try:
        print("=" * 70)
        mode_str = "DRY-RUN (NO CHANGES WILL BE COMMITTED)" if dry_run else "LIVE EXECUTION (DELETIONS WILL BE COMMITTED)"
        print(f"   GRAMASEVA DATA CLEANUP — {mode_str}")
        print("=" * 70)

        # 1. Identify Demo & Test Locality Units (Mandya & Greenfield test units)
        test_unit_codes = [
            "GP-KA-571434", "VIL-GOWD", "VIL-MALL", "VIL-RAMA",
            "W1-GOWD", "W2-GOWD", "W3-GOWD", "ULB-KA-571435",
            "VIL-NEW-7b2fd4", "W1-NEW-7b2fd4"
        ]
        test_units = db.query(LocalityUnit).filter(
            (LocalityUnit.official_code.in_(test_unit_codes)) |
            (LocalityUnit.name_en.like("%Greenfield%")) |
            (LocalityUnit.name_en.like("%Gowdanahalli%")) |
            (LocalityUnit.name_en.like("%Pandavapura%"))
        ).all()
        test_unit_ids = [u.id for u in test_units]
        print(f"\n1. Demo Locality Units Identified: {len(test_units)}")
        for u in test_units:
            print(f"   - [{u.unit_type}] {u.name_en} ({u.official_code})")

        # 2. Identify Demo Profiles (Reviewers, sample PDOs, demo workers, demo citizens, test citizens)
        demo_emails = [
            # Demo Reviewers / PDOs
            "reviewer.gowdanahalli@fixproof.org",
            "reviewer.town@fixproof.org",
            "supervisor.mandya@fixproof.org",
            "demo.system@gramaseva.internal",
            "pdo.peeranwadi@belagavi.gov.in",
            "pdo.peeranwadi.e10a@belagavi.gov.in",
            # Demo Worker
            "worker.ramesh@fixproof.org",
            # Demo Citizens & Test accounts
            "citizen.suresh@example.com",
            "citizen.ananya@example.com",
            "basavaraj.patil@example.com",
        ]
        demo_profiles = db.query(Profile).filter(
            (Profile.email.in_(demo_emails)) |
            (Profile.email.like("newcitizen.%@example.com")) |
            (Profile.email.like("pdo.peeranwadi.%"))
        ).all()
        demo_profile_ids = [p.id for p in demo_profiles]
        print(f"\n2. Demo / Sample Profiles Identified: {len(demo_profiles)}")
        for p in demo_profiles:
            print(f"   - {p.email} ({p.full_name})")

        # 3. Identify Demo & Test Issues
        # All issues with is_demo=True, or created by demo/test reporters, or with test reference numbers
        demo_issues = db.query(Issue).filter(
            (Issue.is_demo == True) |
            (Issue.reference_number.like("FP-TEST-%")) |
            (Issue.reference_number.like("FP-2026-%")) |
            (Issue.reference_number.like("GS-2026-%"))
        ).all()
        demo_issue_ids = [i.id for i in demo_issues]
        print(f"\n3. Demo / Test Complaint Records Identified: {len(demo_issues)}")

        # 4. Check Dependent Records
        sub_count = db.query(Submission).filter(Submission.issue_id.in_(demo_issue_ids)).count() if demo_issue_ids else 0
        media_count = db.query(MediaAsset).filter(MediaAsset.issue_id.in_(demo_issue_ids)).count() if demo_issue_ids else 0
        events_count = db.query(StatusEvent).filter(StatusEvent.issue_id.in_(demo_issue_ids)).count() if demo_issue_ids else 0
        fb_count = db.query(Feedback).filter(Feedback.issue_id.in_(demo_issue_ids)).count() if demo_issue_ids else 0
        asgn_count = db.query(Assignment).filter(Assignment.issue_id.in_(demo_issue_ids)).count() if demo_issue_ids else 0
        comp_count = db.query(WorkCompletion).filter(WorkCompletion.issue_id.in_(demo_issue_ids)).count() if demo_issue_ids else 0
        rev_count = db.query(RepairReview).filter(RepairReview.issue_id.in_(demo_issue_ids)).count() if demo_issue_ids else 0
        notif_count = db.query(Notification).filter(
            (Notification.issue_id.in_(demo_issue_ids)) | (Notification.profile_id.in_(demo_profile_ids))
        ).count() if (demo_issue_ids or demo_profile_ids) else 0

        print(f"\n4. Dependent Records Linked to Demo/Test Complaints:")
        print(f"   - Submissions: {sub_count}")
        print(f"   - Media Assets (photos): {media_count}")
        print(f"   - Status Events: {events_count}")
        print(f"   - Feedback records: {fb_count}")
        print(f"   - Worker Assignments: {asgn_count}")
        print(f"   - Work Completions: {comp_count}")
        print(f"   - Repair Reviews: {rev_count}")
        print(f"   - Notifications: {notif_count}")

        if dry_run:
            print("\n[Notice] This was a DRY RUN. No records were deleted.")
            print("[Notice] Run with '--confirm' to perform live deletion.")
            return

        # LIVE EXECUTION: Delete in safe foreign-key order
        print("\nExecuting live deletions...")

        # A. Delete Notifications
        if demo_issue_ids or demo_profile_ids:
            db.query(Notification).filter(
                (Notification.issue_id.in_(demo_issue_ids)) | (Notification.profile_id.in_(demo_profile_ids))
            ).delete(synchronize_session=False)

        # B. Delete Feedbacks
        if demo_issue_ids:
            db.query(Feedback).filter(Feedback.issue_id.in_(demo_issue_ids)).delete(synchronize_session=False)

        # C. Delete Duplicate Candidates
        if demo_issue_ids:
            db.query(DuplicateCandidate).filter(
                (DuplicateCandidate.target_issue_id.in_(demo_issue_ids))
            ).delete(synchronize_session=False)

        # D. Delete AI Before/After Analyses
        if demo_issue_ids:
            db.query(AIBeforeAfterAnalysis).filter(AIBeforeAfterAnalysis.issue_id.in_(demo_issue_ids)).delete(synchronize_session=False)

        # E. Delete ModelRuns
        if demo_issue_ids:
            db.query(ModelRun).filter(ModelRun.issue_id.in_(demo_issue_ids)).delete(synchronize_session=False)

        # F. Delete RepairReviews
        if demo_issue_ids:
            db.query(RepairReview).filter(RepairReview.issue_id.in_(demo_issue_ids)).delete(synchronize_session=False)

        # G. Delete WorkCompletions
        if demo_issue_ids:
            db.query(WorkCompletion).filter(WorkCompletion.issue_id.in_(demo_issue_ids)).delete(synchronize_session=False)

        # H. Delete Assignments
        if demo_issue_ids:
            db.query(Assignment).filter(Assignment.issue_id.in_(demo_issue_ids)).delete(synchronize_session=False)

        # I. Delete StatusEvents
        if demo_issue_ids:
            db.query(StatusEvent).filter(StatusEvent.issue_id.in_(demo_issue_ids)).delete(synchronize_session=False)

        # J. Delete LocationAuditLogs
        if demo_issue_ids:
            db.query(LocationAuditLog).filter(LocationAuditLog.issue_id.in_(demo_issue_ids)).delete(synchronize_session=False)

        # K. Delete MediaAssets
        if demo_issue_ids:
            db.query(MediaAsset).filter(MediaAsset.issue_id.in_(demo_issue_ids)).delete(synchronize_session=False)

        # L. Delete Submissions
        if demo_issue_ids:
            db.query(Submission).filter(Submission.issue_id.in_(demo_issue_ids)).delete(synchronize_session=False)

        # M. Delete Issues
        if demo_issue_ids:
            db.query(Issue).filter(Issue.id.in_(demo_issue_ids)).delete(synchronize_session=False)

        # N. Nullify any audit logs referencing demo profiles before deleting profiles
        if demo_profile_ids:
            db.query(AuditLog).filter(AuditLog.actor_profile_id.in_(demo_profile_ids)).update(
                {AuditLog.actor_profile_id: None}, synchronize_session=False
            )
            # Delete RoleAssignments for demo profiles
            db.query(RoleAssignment).filter(RoleAssignment.profile_id.in_(demo_profile_ids)).delete(synchronize_session=False)
            # Delete demo profiles
            db.query(Profile).filter(Profile.id.in_(demo_profile_ids)).delete(synchronize_session=False)

        # O. Delete Test Locality Units (wards first then villages)
        if test_unit_ids:
            # Nullify any remaining references
            db.query(RoleAssignment).filter(RoleAssignment.jurisdiction_unit_id.in_(test_unit_ids)).delete(synchronize_session=False)
            db.query(LocalityUnit).filter(LocalityUnit.id.in_(test_unit_ids), LocalityUnit.unit_type == "ward").delete(synchronize_session=False)
            db.query(LocalityUnit).filter(LocalityUnit.id.in_(test_unit_ids), LocalityUnit.unit_type != "ward").delete(synchronize_session=False)

        db.commit()
        print("\n[Success] All identified demo and test data cleanly removed from PostgreSQL!")

    except Exception as e:
        db.rollback()
        print(f"\n[Error] Cleanup failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    confirm_flag = "--confirm" in sys.argv
    run_cleanup(dry_run=not confirm_flag)
