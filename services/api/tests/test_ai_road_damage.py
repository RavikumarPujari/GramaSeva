import unittest
import uuid
import sys
import os
import json
from io import BytesIO
from PIL import Image
from datetime import datetime, timezone

# Ensure local test environment
os.environ["DATABASE_URL"] = "sqlite:///./fixproof_dev.db"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.core.database import SessionLocal, Base, engine
from app.models.users import Profile, RoleAssignment
from app.models.localities import Organization
from app.models.issues import Issue, Submission, MediaAsset, Job, ModelRun
from app.storage.service import storage_service
from workers.adapters.road_damage.adapter import RoadDamageAdapter, road_damage_adapter, EXPECTED_SHA256
from workers.app.worker import process_single_job
from app.ai.router import confirm_model_run_suggestion, ConfirmRunRequest
from fastapi import HTTPException

class TestAIRoadDamageModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()

        cls.org = cls.db.query(Organization).first()
        if not cls.org:
            cls.org = Organization(name="AI Test Org", code=f"AI-ORG-{uuid.uuid4().hex[:6]}")
            cls.db.add(cls.org)
            cls.db.flush()

        cls.reviewer = cls.db.query(Profile).filter((Profile.email.like("%pdo%")) | (Profile.email.like("%reviewer%"))).first()
        cls.citizen = cls.db.query(Profile).filter(Profile.email.like("%citizen%")).first()
        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.db.query(ModelRun).filter(ModelRun.model_id == "oracl4-rdd-yolov8s").delete(synchronize_session=False)
            cls.db.commit()
        except Exception:
            cls.db.rollback()
        finally:
            cls.db.close()

    def test_01_actual_checkpoint_loads_and_verifies_hash(self):
        """Verifies the actual YOLOv8_Small_RDD.pt checkpoint loads and matches expected provenance hash."""
        readiness = road_damage_adapter.check_readiness()
        self.assertTrue(readiness["ready"], f"Model failed to load: {readiness.get('error')}")
        self.assertEqual(readiness["model_id"], "oracl4-rdd-yolov8s")
        self.assertEqual(readiness["checkpoint_sha256"], EXPECTED_SHA256)
        self.assertEqual(len(readiness["classes"]), 4)
        self.assertIn("Potholes", readiness["classes"])
        self.assertIn("Alligator Crack", readiness["classes"])
        self.assertIsNone(readiness["error"])

    def test_02_actual_forward_pass_inference_succeeds(self):
        """Runs actual PyTorch forward pass on an image fixture and verifies structured output."""
        # Create a test road image (640x640 RGB)
        img = Image.new("RGB", (640, 640), color=(100, 100, 100))
        result = road_damage_adapter.predict(img)

        # Output must come from actual model, not mock data
        self.assertIn(result["status"], ["completed", "no_detections"])
        self.assertEqual(result["task"], "road_damage_detection")
        self.assertEqual(result["model_id"], "oracl4-rdd-yolov8s")
        self.assertEqual(result["model_revision"], EXPECTED_SHA256)
        self.assertTrue(result["requires_human_review"])
        self.assertGreater(result["latency_ms"], 0)
        self.assertGreater(len(result["limitations"]), 0)

    def test_03_missing_model_returns_clear_unavailable_without_crashing(self):
        """Missing or corrupt model checkpoint returns status='unavailable' with zero mock predictions."""
        broken_adapter = RoadDamageAdapter(checkpoint_path="/nonexistent/model.pt")
        res = broken_adapter.predict(Image.new("RGB", (640, 640), color="white"))

        self.assertEqual(res["status"], "unavailable")
        self.assertIsNone(res["category_suggestion"])
        self.assertEqual(len(res["observations"]), 0)
        self.assertTrue(res["requires_human_review"])
        self.assertIn("unavailable", res["limitations"][0].lower())

    def test_04_job_worker_processes_inference_and_persists_model_run(self):
        """Validates persistent background AI job execution and ModelRun audit trail."""
        # 1. Store a test image
        buf = BytesIO()
        Image.new("RGB", (300, 300), color="gray").save(buf, format="JPEG")
        rel_path, mime, size_bytes, file_hash = storage_service.store_private_media(buf.getvalue(), "road_test.jpg")

        unique_ref = f"FP-2026-AI-{uuid.uuid4().hex[:6]}"
        issue = Issue(
            reference_number=unique_ref,
            category="road_damage",
            status="SUBMITTED",
            priority="MEDIUM",
            organization_id=self.org.id,
        )
        self.db.add(issue)
        self.db.flush()

        sub = Submission(
            tracking_id=unique_ref,
            reporter_id=self.citizen.id,
            issue_id=issue.id,
            category="road_damage",
            description="Pothole near crossroad",
            locale="en",
        )
        self.db.add(sub)
        self.db.flush()

        media = MediaAsset(
            profile_id=self.citizen.id,
            submission_id=sub.id,
            issue_id=issue.id,
            evidence_role="CITIZEN_BEFORE",
            storage_path=rel_path,
            file_hash=file_hash,
            mime_type=mime,
            file_size_bytes=size_bytes,
            is_quarantined=False,
            is_public_approved=False,
        )
        self.db.add(media)
        self.db.flush()

        # Enqueue background job
        job = Job(
            task_name="road_damage_inference",
            payload_json=json.dumps({"submission_id": sub.id, "issue_id": issue.id}),
            status="QUEUED",
        )
        self.db.add(job)
        self.db.commit()

        # Process job via worker
        process_res = process_single_job(job.id, db=self.db)
        self.assertEqual(process_res["status"], "success")

        # Verify Job updated to COMPLETED
        self.db.refresh(job)
        self.assertEqual(job.status, "COMPLETED")
        self.assertIsNotNone(job.completed_at)

        # Verify ModelRun audit created
        model_run = self.db.query(ModelRun).filter(ModelRun.job_id == job.id).first()
        self.assertIsNotNone(model_run)
        self.assertEqual(model_run.model_id, "oracl4-rdd-yolov8s")
        self.assertEqual(model_run.model_revision, EXPECTED_SHA256)
        self.assertTrue(model_run.requires_human_review)
        self.assertEqual(model_run.confirmed_decision, "PENDING")

    def test_05_human_confirmation_workflow(self):
        """Reviewer or citizen confirms AI detection suggestion; updates issue status and records audit."""
        # Create a pending ModelRun
        run = ModelRun(
            id=str(uuid.uuid4()),
            model_id="oracl4-rdd-yolov8s",
            model_revision=EXPECTED_SHA256,
            task="road_damage_detection",
            status="COMPLETED",
            category_suggestion="road_damage",
            confidence_score=0.82,
            latency_ms=195,
            requires_human_review=True,
            confirmed_decision="PENDING",
        )
        self.db.add(run)
        self.db.commit()

        # Confirm the suggestion
        res = confirm_model_run_suggestion(
            run_id=run.id,
            req=ConfirmRunRequest(decision="CONFIRMED", notes="Confirmed visible pothole by reviewer"),
            current_user=self.reviewer,
            db=self.db,
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["confirmed_decision"], "CONFIRMED")

        self.db.refresh(run)
        self.assertEqual(run.confirmed_decision, "CONFIRMED")
        self.assertEqual(run.confirmed_by_profile_id, self.reviewer.id)

if __name__ == "__main__":
    unittest.main()
