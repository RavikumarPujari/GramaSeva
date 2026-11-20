import unittest
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models.users import Profile, RoleAssignment
from app.models.localities import LocalityUnit, Organization
from app.models.issues import Issue, Submission, MediaAsset, StatusEvent, DuplicateCandidate
from app.reports.schemas import DraftCreateRequest, SubmitReportRequest
from app.reports.router import (
    create_draft,
    submit_report,
    get_report_duplicate_suggestions,
)

class TestDuplicateDetectionAndLinking(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)

    def setUp(self):
        self.db: Session = SessionLocal()
        # Seed test organization
        self.org = self.db.query(Organization).first()
        if not self.org:
            self.org = Organization(id="test-org-belagavi", name="Belagavi Pilot Org", code="BGM-01")
            self.db.add(self.org)
            self.db.commit()

        # Seed Belagavi locality
        self.locality = self.db.query(LocalityUnit).filter(LocalityUnit.official_code == "BGM-VTU-01").first()
        if not self.locality:
            self.locality = LocalityUnit(
                id="loc-bgm-vtu",
                organization_id=self.org.id,
                unit_type="ward",
                official_code="BGM-VTU-01",
                name_en="Machhe (VTU Campus)",
                name_kn="ಮಚ್ಚೆ (ವಿಟಿಯು ಆವರಣ)",
                name_hi="माच्छे (वीटीयू परिसर)",
                is_active=True,
            )
            self.db.add(self.locality)
            self.db.commit()

        # Seed test citizen
        self.citizen = self.db.query(Profile).filter(Profile.phone_number == "+919888877771").first()
        if not self.citizen:
            self.citizen = Profile(
                id="test-citizen-dup-1",
                email="basavaraj.patil@example.com",
                password_hash="mock-hash",
                phone_number="+919888877771",
                full_name="Basavaraj Patil",
                preferred_locale="kn",
                is_active=True,
            )
            self.db.add(self.citizen)
            self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_01_confirmed_duplicate_linking(self):
        """Milestone 1: Verify citizen confirmed duplicate links to existing issue while preserving submission and tracking ID."""
        # 1. Existing physical issue reported earlier
        existing_issue = Issue(
            id="iss-existing-pothole-01",
            reference_number="GS-2026-10001",
            category="road_damage",
            status="IN_PROGRESS",
            priority="HIGH",
            organization_id=self.org.id,
            locality_unit_id=self.locality.id,
            latitude=15.8281,
            longitude=74.4691,
        )
        self.db.merge(existing_issue)
        self.db.commit()

        # 2. Citizen creates new draft report for same pothole
        draft_req = DraftCreateRequest(
            category="road_damage",
            description="Deep pothole right outside VTU main gate on Machhe road",
            village_name="Machhe",
            ward_name="Machhe (VTU Campus)",
            locality_unit_id=self.locality.id,
            latitude=15.8282,
            longitude=74.4692,
        )
        draft_report = create_draft(draft_req, self.citizen, self.db)
        original_draft_id = draft_report.id
        original_tracking_id = draft_report.tracking_id

        # Attach mock evidence photo
        media = MediaAsset(
            profile_id=self.citizen.id,
            submission_id=original_draft_id,
            evidence_role="CITIZEN_BEFORE",
            storage_path="private/test_evidence.jpg",
            file_hash="mocksha256potholeevidence",
            mime_type="image/jpeg",
            file_size_bytes=102400,
        )
        self.db.add(media)
        self.db.commit()

        # 3. Query duplicate suggestions
        suggestions = get_report_duplicate_suggestions(original_draft_id, self.db)
        self.assertGreaterEqual(len(suggestions), 1)
        top_suggestion = suggestions[0]
        self.assertEqual(top_suggestion.issue_id, existing_issue.id)
        self.assertLess(top_suggestion.distance_meters, 50.0)

        # 4. Citizen chooses 'Same problem' (CONFIRMED_DUPLICATE)
        submit_req = SubmitReportRequest(
            duplicate_decision="CONFIRMED_DUPLICATE",
            duplicate_target_issue_id=existing_issue.id,
        )
        final_report = submit_report(original_draft_id, submit_req, self.citizen, self.db)

        # 5. Verify database integrity
        # Citizen submission preserved with its own unique tracking ID
        self.assertEqual(final_report.tracking_id, original_tracking_id)

        # Linked to existing physical issue
        sub_in_db = self.db.query(Submission).filter(Submission.id == original_draft_id).first()
        self.assertEqual(sub_in_db.issue_id, existing_issue.id)

        # DuplicateCandidate record exists with decision CONFIRMED_DUPLICATE
        dup_rec = self.db.query(DuplicateCandidate).filter(
            DuplicateCandidate.submission_id == original_draft_id,
            DuplicateCandidate.target_issue_id == existing_issue.id,
        ).first()
        self.assertIsNotNone(dup_rec)
        self.assertEqual(dup_rec.decision, "CONFIRMED_DUPLICATE")

        # Status event logged on target issue
        events = self.db.query(StatusEvent).filter(StatusEvent.issue_id == existing_issue.id).all()
        self.assertTrue(any("confirmed as duplicate" in e.reason for e in events))

    def test_02_uncertain_duplicate_flag(self):
        """Milestone 1: Verify citizen uncertain choice flags submission for human reviewer adjudication."""
        existing_issue = Issue(
            id="iss-existing-pothole-02",
            reference_number="GS-2026-10002",
            category="road_damage",
            status="SUBMITTED",
            priority="MEDIUM",
            organization_id=self.org.id,
            locality_unit_id=self.locality.id,
            latitude=15.8285,
            longitude=74.4695,
        )
        self.db.merge(existing_issue)
        self.db.commit()

        # Citizen creates draft
        draft_req = DraftCreateRequest(
            category="road_damage",
            description="Road crack near bus shelter",
            village_name="Machhe",
            ward_name="Machhe (VTU Campus)",
            locality_unit_id=self.locality.id,
            latitude=15.8286,
            longitude=74.4696,
        )
        draft_report = create_draft(draft_req, self.citizen, self.db)

        # Attach mock evidence photo
        media = MediaAsset(
            profile_id=self.citizen.id,
            submission_id=draft_report.id,
            evidence_role="CITIZEN_BEFORE",
            storage_path="private/test_crack.jpg",
            file_hash="mocksha256crackevidence",
            mime_type="image/jpeg",
            file_size_bytes=102400,
        )
        self.db.add(media)
        self.db.commit()

        # Citizen selects 'I am not sure' (UNCERTAIN_NEEDS_REVIEW)
        submit_req = SubmitReportRequest(
            duplicate_decision="UNCERTAIN_NEEDS_REVIEW",
            duplicate_target_issue_id=existing_issue.id,
        )
        final_report = submit_report(draft_report.id, submit_req, self.citizen, self.db)

        # Verify submission has its own issue but audit trail records uncertain flag
        dup_rec = self.db.query(DuplicateCandidate).filter(
            DuplicateCandidate.submission_id == draft_report.id,
            DuplicateCandidate.target_issue_id == existing_issue.id,
        ).first()
        self.assertIsNotNone(dup_rec)
        self.assertEqual(dup_rec.decision, "UNCERTAIN_NEEDS_REVIEW")
