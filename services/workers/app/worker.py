import sys
import os
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# Ensure services/api is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../api")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.database import SessionLocal
from app.models.issues import Job, Submission, Issue, MediaAsset, ModelRun
from app.storage.service import storage_service
from workers.adapters.road_damage.adapter import road_damage_adapter

def process_single_job(job_id: str, db=None) -> Dict[str, Any]:
    """
    Processes an individual queued AI inference task.
    Reads job payload, fetches photo, executes road damage model, and records ModelRun.
    """
    should_close_db = False
    if db is None:
        db = SessionLocal()
        should_close_db = True

    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return {"status": "error", "message": f"Job {job_id} not found"}

        job.status = "PROCESSING"
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        payload = json.loads(job.payload_json) if isinstance(job.payload_json, str) else job.payload_json
        submission_id = payload.get("submission_id")
        issue_id = payload.get("issue_id")

        submission = db.query(Submission).filter(Submission.id == submission_id).first() if submission_id else None
        issue = db.query(Issue).filter(Issue.id == issue_id).first() if issue_id else None

        # Fetch citizen before photo
        media = None
        if submission:
            media = (
                db.query(MediaAsset)
                .filter(MediaAsset.submission_id == submission.id, MediaAsset.evidence_role == "CITIZEN_BEFORE")
                .first()
            )
        elif issue:
            media = (
                db.query(MediaAsset)
                .filter(MediaAsset.issue_id == issue.id, MediaAsset.evidence_role == "CITIZEN_BEFORE")
                .first()
            )

        if not media:
            job.status = "COMPLETED"
            job.error_message = "No evidence media asset associated with complaint"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return {"status": "completed_no_media", "job_id": job.id}

        abs_path = storage_service.get_absolute_path(media.storage_path)

        # Run real inference adapter
        inference_res = road_damage_adapter.predict(abs_path)

        # Record ModelRun audit entry
        model_run = ModelRun(
            id=str(uuid.uuid4()),
            job_id=job.id,
            media_asset_id=media.id,
            issue_id=issue.id if issue else (submission.issue_id if submission else None),
            submission_id=submission.id if submission else None,
            model_id=inference_res["model_id"],
            model_revision=inference_res["model_revision"],
            task=inference_res["task"],
            status=inference_res["status"].upper(),
            category_suggestion=inference_res["category_suggestion"],
            confidence_score=inference_res["confidence_score"],
            detections_json=json.dumps(inference_res["observations"]),
            latency_ms=inference_res["latency_ms"],
            requires_human_review=True,
            limitations_json=json.dumps(inference_res["limitations"]),
            confirmed_decision="PENDING",
        )
        db.add(model_run)

        job.status = "COMPLETED"
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "status": "success",
            "job_id": job.id,
            "model_run_id": model_run.id,
            "inference": inference_res,
        }

    except Exception as e:
        if db:
            db.rollback()
        return {"status": "failed", "error": str(e)}
    finally:
        if should_close_db and db:
            db.close()

def process_all_queued_jobs(db=None) -> int:
    """Finds and executes all pending AI jobs in the queue."""
    should_close_db = False
    if db is None:
        db = SessionLocal()
        should_close_db = True

    try:
        queued_jobs = db.query(Job).filter(Job.status == "QUEUED").all()
        processed_count = 0
        for job in queued_jobs:
            process_single_job(job.id, db=db)
            processed_count += 1
        return processed_count
    finally:
        if should_close_db and db:
            db.close()
