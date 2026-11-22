import os
import sys
import uuid
import unittest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.core.database import SessionLocal, Base, engine
from app.models.users import Profile, RoleAssignment
from app.models.issues import ModelRun
from app.ai.evaluation_service import model_evaluation_service
from app.ai.router import evaluate_model_run_prediction, get_ai_evaluation_metrics, get_model_retraining_readiness, ModelEvaluationFeedbackRequest

class TestAIEvaluationService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()

        cls.reviewer = cls.db.query(Profile).filter(Profile.email == "admin@fixproof.org").first()
        if not cls.reviewer:
            cls.reviewer = Profile(
                email="admin@fixproof.org",
                full_name="Ravikumar",
                password_hash="test",
            )
            cls.db.add(cls.reviewer)
            cls.db.flush()
            cls.db.add(RoleAssignment(profile_id=cls.reviewer.id, role="admin", is_active=True))
            cls.db.commit()

        # Create a test ModelRun
        cls.test_run = ModelRun(
            id=str(uuid.uuid4()),
            model_id="road-damage-detection-fn0qh/1",
            model_revision="v1.0",
            task="detection",
            status="COMPLETED",
            category_suggestion="road_damage",
            confidence_score=0.88,
            confirmed_decision="PENDING",
        )
        cls.db.add(cls.test_run)
        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_empty_evaluation_metrics(self):
        """Verifies that an unreviewed model returns honest insufficient data flag."""
        metrics = model_evaluation_service.compute_evaluation_metrics(self.db, model_id="non-existent-model/1")
        self.assertTrue(metrics["insufficient_evaluation_data"])
        self.assertEqual(metrics["total_evaluated_samples"], 0)

    def test_02_record_reviewer_feedback(self):
        """Verifies recording human feedback confirms the ModelRun and appends to dataset."""
        req = ModelEvaluationFeedbackRequest(
            correct_category="road_damage",
            is_correct=True,
            audit_notes="Pothole detection verified by Panchayat Reviewer.",
        )
        res = evaluate_model_run_prediction(
            run_id=self.test_run.id,
            req=req,
            current_reviewer=self.reviewer,
            db=self.db,
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["decision"], "CONFIRMED")
        self.assertEqual(res["ground_truth_category"], "road_damage")

        # Directly verify in DB
        updated = self.db.query(ModelRun).filter(ModelRun.id == self.test_run.id).first()
        self.assertEqual(updated.confirmed_decision, "CONFIRMED")
        self.assertEqual(updated.citizen_confirmed_category, "road_damage")

    def test_03_compute_metrics_after_feedback(self):
        """Verifies empirical Precision, Recall, and F1 calculations after human feedback."""
        metrics = get_ai_evaluation_metrics(model_id="road-damage-detection-fn0qh/1", db=self.db)
        self.assertFalse(metrics["insufficient_evaluation_data"])
        self.assertGreaterEqual(metrics["total_evaluated_samples"], 1)
        self.assertEqual(metrics["global_accuracy"], 1.0)
        self.assertEqual(metrics["global_precision"], 1.0)
        self.assertEqual(metrics["global_recall"], 1.0)
        self.assertEqual(metrics["global_f1_score"], 1.0)

    def test_04_retraining_readiness(self):
        """Verifies governed retraining readiness reporting."""
        status_res = get_model_retraining_readiness(db=self.db)
        self.assertIn("verified_samples_count", status_res)
        self.assertIn("minimum_required_samples", status_res)
        self.assertIn("retraining_governance_rules", status_res)
        self.assertGreater(len(status_res["retraining_governance_rules"]), 3)

if __name__ == "__main__":
    unittest.main()
