import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.issues import Issue, RecurrenceCandidate
from workers.adapters.duplicate.similarity import compute_haversine_distance

def detect_recurrence_candidates(
    db: Session,
    new_issue_id: str,
    category: str,
    latitude: Optional[float],
    longitude: Optional[float],
    max_distance_meters: float = 100.0,
    max_days_past: int = 180,
) -> List[RecurrenceCandidate]:
    """
    Identifies candidate links to prior resolved issues at the same location.
    README Rule: AI flags recurrence candidates; human reviewer confirms relationship.
    """
    if latitude is None or longitude is None:
        return []

    # Query resolved issues of the same category
    resolved_issues = (
        db.query(Issue)
        .filter(
            Issue.id != new_issue_id,
            Issue.category == category,
            Issue.status == "RESOLVED",
            Issue.resolved_at.isnot(None),
        )
        .all()
    )

    candidates = []
    now = datetime.now(timezone.utc)

    for prior in resolved_issues:
        if prior.latitude is None or prior.longitude is None:
            continue

        # Proximity check
        dist = compute_haversine_distance(latitude, longitude, prior.latitude, prior.longitude)
        if dist > max_distance_meters:
            continue

        # Recurrence time window check
        prior_res_at = prior.resolved_at
        if prior_res_at.tzinfo is None:
            prior_res_at = prior_res_at.replace(tzinfo=timezone.utc)

        days_past = max(0, (now - prior_res_at).days)
        if days_past > max_days_past:
            continue

        # Check if already recorded
        existing = (
            db.query(RecurrenceCandidate)
            .filter(
                RecurrenceCandidate.new_issue_id == new_issue_id,
                RecurrenceCandidate.prior_issue_id == prior.id,
            )
            .first()
        )

        if not existing:
            cand = RecurrenceCandidate(
                new_issue_id=new_issue_id,
                prior_issue_id=prior.id,
                distance_meters=dist,
                days_since_resolution=days_past,
                decision="PENDING",
                notes=f"Reported {int(dist)}m from prior resolved defect {prior.reference_number} ({days_past} days ago)",
            )
            db.add(cand)
            candidates.append(cand)

    if candidates:
        db.commit()

    return candidates
