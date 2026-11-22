"""
Safe Demonstration Data Seed & Removal Script for GramaSeva (Part 7).
Creates realistic, clearly labeled demonstration complaints and solved before-and-after examples across 6 civic categories:
1. Road pothole
2. Garbage accumulation
3. Waterlogging
4. Damaged streetlight
5. Drainage blockage
6. Public sanitation issue

Guarantees:
- Flagged with is_demo = True and reference_numbers starting with "DEMO-2026-BEL-"
- Clearly identified as DEMO / SAMPLE
- Fully isolated from operational PDO and citizen complaint metrics
- Provides safe --clean and --seed modes
"""

import sys
import os
import io
import uuid
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont

# Add services/api to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../services/api")))

from app.core.database import SessionLocal, Base, engine
from app.models import (
    Organization,
    LocalityUnit,
    Department,
    Profile,
    RoleAssignment,
)
from app.models.issues import (
    Issue,
    Submission,
    MediaAsset,
    WorkCompletion,
    AIBeforeAfterAnalysis,
    StatusEvent,
)
from app.storage.service import storage_service

DEMO_RECORDS = [
    {
        "ref": "DEMO-2026-BEL-001",
        "category": "road_damage",
        "title": "Severe Pothole on Village Connecting Road",
        "description": "Deep asphalt crater (approx. 1.2m wide, 15cm deep) hazardous to two-wheelers and school transport.",
        "village": "Peeranwadi",
        "latitude": 15.8152,
        "longitude": 74.4610,
        "before_label": "DAMAGED ASPHALT & POTHOLE",
        "before_color": (110, 80, 70),
        "after_label": "REPAIRED & LEVELLED ASPHALT PATCH",
        "after_color": (50, 55, 60),
        "days_ago": 6,
        "verified_cost": 4200.0,
        "materials": "Bituminous cold mix (6 bags), stone dust base",
        "labour": "2 field crew workers, 1 compactor roller session",
        "ai_summary": "Visual analysis confirms road crater filled and rolled level with surrounding asphalt surface.",
    },
    {
        "ref": "DEMO-2026-BEL-002",
        "category": "garbage",
        "title": "Overflowing Public Waste Accumulation",
        "description": "Uncollected organic and plastic refuse accumulating near weekly village market square.",
        "village": "Kuttalawadi",
        "latitude": 15.8280,
        "longitude": 74.4320,
        "before_label": "WASTE PILE & OVERFLOW",
        "before_color": (120, 110, 80),
        "after_label": "CLEANED GROUND & SANITIZED BIN",
        "after_color": (60, 100, 70),
        "days_ago": 5,
        "verified_cost": 1800.0,
        "materials": "Disinfectant powder, 240L covered collection bin",
        "labour": "Sanitation sweep team (3 workers)",
        "ai_summary": "Substantial visible change. Open refuse heap removed and ground bleached clean.",
    },
    {
        "ref": "DEMO-2026-BEL-003",
        "category": "waterlogging",
        "title": "Monsoon Waterlogging on Bus Route",
        "description": "Stagnant stormwater pooling across 20-meter stretch obstructing pedestrian and bus transit.",
        "village": "Zad-Shahapur",
        "latitude": 15.8500,
        "longitude": 74.4900,
        "before_label": "WATERLOGGED ROAD EMBANKMENT",
        "before_color": (60, 90, 130),
        "after_label": "DRAINED EMBANKMENT & RUNOFF CHANNEL",
        "after_color": (70, 85, 95),
        "days_ago": 4,
        "verified_cost": 3100.0,
        "materials": "Diesel water pump rental, shoulder gravel bedding",
        "labour": "Pump operator and 2 maintenance labourers",
        "ai_summary": "Water pooling successfully drained; roadside embankment reprofiled for gravity runoff.",
    },
    {
        "ref": "DEMO-2026-BEL-004",
        "category": "street_light",
        "title": "Non-Functional Streetlight Luminaire",
        "description": "Dark stretch on temple road due to burned out luminaire fixture and damaged bracket.",
        "village": "Santibastawad",
        "latitude": 15.8650,
        "longitude": 74.4400,
        "before_label": "BROKEN SODIUM STREETLIGHT FIXTURE",
        "before_color": (40, 45, 60),
        "after_label": "REPLACED 45W ENERGY-EFFICIENT LED",
        "after_color": (70, 95, 110),
        "days_ago": 4,
        "verified_cost": 2250.0,
        "materials": "45W LED streetlight luminaire, connector clamp, 10m cable",
        "labour": "1 certified linesman, 1 helper with ladder truck",
        "ai_summary": "Damaged fixture replaced with working LED unit; lighting circuit operational.",
    },
    {
        "ref": "DEMO-2026-BEL-005",
        "category": "drainage",
        "title": "Blocked Stormwater Channel & Silt Build-up",
        "description": "Concrete stormwater roadside drain completely choked with dry silt, tree branches, and trash.",
        "village": "Yellur",
        "latitude": 15.7770,
        "longitude": 74.4660,
        "before_label": "SILTED & OBSTRUCTED CONCRETE DRAIN",
        "before_color": (90, 80, 65),
        "after_label": "DESILTED CHANNEL WITH FREE OUTFLOW",
        "after_color": (55, 75, 70),
        "days_ago": 3,
        "verified_cost": 2600.0,
        "materials": "Desilting shovels, safety boots, transport disposal",
        "labour": "3 drain maintenance workers (full day)",
        "ai_summary": "Silt and obstructions excavated; clear continuous drain gradient restored.",
    },
    {
        "ref": "DEMO-2026-BEL-006",
        "category": "public_sanitation",
        "title": "Unsanitary Community Facility Environs",
        "description": "Littering and neglected mud buildup outside community hall and public wash facility.",
        "village": "Sulge (Yellur)",
        "latitude": 15.7900,
        "longitude": 74.4500,
        "before_label": "NEGLECTED MUD & LITTER AT ENTRANCE",
        "before_color": (100, 90, 75),
        "after_label": "PRESSURE WASHED & DISINFECTED PAVEMENT",
        "after_color": (80, 110, 100),
        "days_ago": 2,
        "verified_cost": 1500.0,
        "materials": "Bleaching agent, high-pressure jet wash fuel, lime powder",
        "labour": "2 facility maintenance workers",
        "ai_summary": "Entrance washed, disinfected and swept clean. Public facility restored to sanitary condition.",
    },
]

def generate_demo_image(title: str, subtext: str, bg_color: tuple, is_after: bool) -> bytes:
    """Creates a high-contrast, informative demonstration image with clear DEMO labels."""
    w, h = 640, 480
    img = Image.new("RGB", (w, h), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Frame & Banner
    border_color = (46, 204, 113) if is_after else (231, 76, 60)
    draw.rectangle([0, 0, w - 1, h - 1], outline=border_color, width=8)

    # Top Tag
    draw.rectangle([10, 10, w - 10, 60], fill=(20, 30, 45))
    tag_text = "[DEMO / SAMPLE RECORD] - " + ("SOLVED / COMPLETED REPAIR" if is_after else "ORIGINAL REPORT EVIDENCE")
    draw.text((24, 25), tag_text, fill=(255, 255, 255))

    # Center Block
    draw.rectangle([30, 100, w - 30, 380], fill=(0, 0, 0, 120), outline=border_color, width=3)
    draw.text((50, 130), title, fill=(255, 255, 255))
    draw.text((50, 180), subtext, fill=(220, 230, 240))
    status_label = "OFFICIAL STATUS: VERIFIED RESOLVED" if is_after else "OFFICIAL STATUS: SUBMITTED"
    draw.text((50, 240), status_label, fill=(46, 204, 113) if is_after else (255, 193, 7))

    # Watermark
    draw.text((50, 320), "GramaSeva Civic Verification Pilot - Belagavi Taluk", fill=(180, 190, 205))

    # Bottom Banner
    draw.rectangle([10, h - 50, w - 10, h - 10], fill=(20, 30, 45))
    draw.text((24, h - 40), "SAFE DEMONSTRATION DATA (ISOLATED FROM PRODUCTION COMPLAINTS)", fill=(255, 220, 100))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()

def clean_demo_data():
    """Safely deletes only demonstration records without altering real citizen data."""
    print("[DemoGallery] Cleaning existing demonstration records...")
    db = SessionLocal()
    try:
        # Find demo issues
        demo_issues = db.query(Issue).filter(
            (Issue.is_demo == True) | (Issue.reference_number.like("DEMO-%"))
        ).all()
        issue_ids = [i.id for i in demo_issues]

        if issue_ids:
            # Delete associated records
            db.query(AIBeforeAfterAnalysis).filter(AIBeforeAfterAnalysis.issue_id.in_(issue_ids)).delete(synchronize_session=False)
            db.query(WorkCompletion).filter(WorkCompletion.issue_id.in_(issue_ids)).delete(synchronize_session=False)
            db.query(StatusEvent).filter(StatusEvent.issue_id.in_(issue_ids)).delete(synchronize_session=False)
            db.query(MediaAsset).filter(MediaAsset.issue_id.in_(issue_ids)).delete(synchronize_session=False)
            db.query(Submission).filter(Submission.issue_id.in_(issue_ids)).delete(synchronize_session=False)
            db.query(Issue).filter(Issue.id.in_(issue_ids)).delete(synchronize_session=False)
            db.commit()
            print(f"[DemoGallery] Successfully removed {len(issue_ids)} demonstration records.")
        else:
            print("[DemoGallery] No existing demonstration records found to clean.")
    finally:
        db.close()

def seed_demo_data():
    """Seeds the 6 realistic demonstration records across civic categories."""
    clean_demo_data()
    print("[DemoGallery] Seeding 6 realistic demonstration complaints and solved examples...")
    db = SessionLocal()

    try:
        org = db.query(Organization).first()
        if not org:
            org = Organization(name="GramaSeva Pilot Organization", code="TP-BELAGAVI")
            db.add(org)
            db.flush()

        # Find or create demo demo system profile
        demo_citizen = db.query(Profile).filter(Profile.email == "demo.system@gramaseva.internal").first()
        if not demo_citizen:
            demo_citizen = Profile(
                id=str(uuid.uuid4()),
                email="demo.system@gramaseva.internal",
                password_hash="DEMO_SYSTEM_ONLY",
                full_name="GramaSeva Demonstration System",
                preferred_locale="en",
                taluk="Belagavi Taluk",
                district="Belagavi",
                state="Karnataka",
                is_active=True,
            )
            db.add(demo_citizen)
            db.flush()

        # Find PDO reviewer
        pdo_reviewer = db.query(Profile).filter(Profile.email.like("%reviewer%")).first() or demo_citizen
        worker_profile = db.query(Profile).filter(Profile.email.like("%worker%")).first() or demo_citizen

        now = datetime.now(timezone.utc)

        for rec in DEMO_RECORDS:
            created_at = now - timedelta(days=rec["days_ago"])
            resolved_at = created_at + timedelta(hours=36)

            # Resolve LocalityUnit
            loc = db.query(LocalityUnit).filter(LocalityUnit.name_en.ilike(f"%{rec['village']}%")).first()

            # 1. Create Issue
            issue = Issue(
                reference_number=rec["ref"],
                category=rec["category"],
                status="RESOLVED",
                priority="HIGH" if rec["category"] in ["road_damage", "waterlogging"] else "MEDIUM",
                organization_id=org.id,
                locality_unit_id=loc.id if loc else None,
                latitude=rec["latitude"],
                longitude=rec["longitude"],
                public_latitude=round(rec["latitude"], 3),
                public_longitude=round(rec["longitude"], 3),
                assigned_worker_id=worker_profile.id,
                reviewed_by_id=pdo_reviewer.id,
                resolved_at=resolved_at,
                resolution_review_notes=f"Demonstration verified resolution. {rec['ai_summary']}",
                estimated_cost=rec["verified_cost"] * 1.1,
                proposed_cost=rec["verified_cost"],
                verified_cost=rec["verified_cost"],
                cost_status="VERIFIED",
                work_completed_at=resolved_at - timedelta(hours=4),
                work_completion_description=f"Completed physical remediation for {rec['title']}.",
                work_performed=rec["materials"],
                materials_used=rec["materials"],
                labour_details=rec["labour"],
                cost_verification_remarks=f"Verified against GP schedule of rates. Total: Rs {rec['verified_cost']:,.2f}",
                public_display_consent=True,
                is_demo=True,
            )
            issue.created_at = created_at
            db.add(issue)
            db.flush()

            # 2. Create Submission
            submission = Submission(
                tracking_id=rec["ref"],
                reporter_id=demo_citizen.id,
                issue_id=issue.id,
                category=rec["category"],
                description=rec["description"],
                locale="en",
                village_name=rec["village"],
                taluk_name="Belagavi Taluk",
                latitude=rec["latitude"],
                longitude=rec["longitude"],
                reporter_name="GramaSeva Demo Citizen",
                location_method="GPS_VERIFIED",
                confirmed_latitude=rec["latitude"],
                confirmed_longitude=rec["longitude"],
                confirmed_village=rec["village"],
                confirmed_address=f"{rec['village']}, Belagavi Taluk, Karnataka, India",
                confirmation_method="CITIZEN_CONFIRMED",
                jurisdiction_status="VERIFIED",
                detected_village=rec["village"],
                detected_taluk="Belagavi Taluk",
                detected_district="Belagavi District",
                detected_state="Karnataka",
                detected_country="India",
                detected_postal_code="590014",
                geocoding_status="OK",
                location_confirmation_status="CITIZEN_CONFIRMED",
                public_display_consent=True,
                is_demo=True,
            )
            submission.created_at = created_at
            db.add(submission)
            db.flush()

            # 3. Create Before Media Image
            before_bytes = generate_demo_image(
                title=f"BEFORE: {rec['title']}",
                subtext=f"Location: {rec['village']} • {rec['before_label']}",
                bg_color=rec["before_color"],
                is_after=False,
            )
            b_path, b_mime, b_size, b_hash = storage_service.store_private_media(before_bytes, f"{rec['ref']}_before.jpg")
            before_media = MediaAsset(
                profile_id=demo_citizen.id,
                submission_id=submission.id,
                issue_id=issue.id,
                evidence_role="CITIZEN_BEFORE",
                storage_path=b_path,
                file_hash=b_hash,
                mime_type=b_mime,
                file_size_bytes=b_size,
                is_quarantined=False,
                is_public_approved=True,
            )
            before_media.created_at = created_at
            db.add(before_media)
            db.flush()

            # 4. Create After Media Image
            after_bytes = generate_demo_image(
                title=f"AFTER: {rec['title']} - SOLVED",
                subtext=f"Remediation: {rec['after_label']}",
                bg_color=rec["after_color"],
                is_after=True,
            )
            a_path, a_mime, a_size, a_hash = storage_service.store_private_media(after_bytes, f"{rec['ref']}_after.jpg")
            after_media = MediaAsset(
                profile_id=worker_profile.id,
                submission_id=submission.id,
                issue_id=issue.id,
                evidence_role="WORKER_AFTER",
                storage_path=a_path,
                file_hash=a_hash,
                mime_type=a_mime,
                file_size_bytes=a_size,
                is_quarantined=False,
                is_public_approved=True,
            )
            after_media.created_at = resolved_at - timedelta(hours=4)
            db.add(after_media)
            db.flush()

            # 5. Work Completion
            completion = WorkCompletion(
                issue_id=issue.id,
                worker_profile_id=worker_profile.id,
                submission_number=1,
                work_description=f"Physical repair completed for {rec['title']}.",
                work_performed=rec["materials"],
                materials_used=rec["materials"],
                labour_details=rec["labour"],
                materials_cost=rec["verified_cost"] * 0.7,
                labour_cost=rec["verified_cost"] * 0.3,
                proposed_cost=rec["verified_cost"],
                verified_cost=rec["verified_cost"],
                completion_date=resolved_at - timedelta(hours=4),
                status="APPROVED",
                pdo_remarks=f"Verified on-site by Village PDO. {rec['ai_summary']}",
                verified_by_id=pdo_reviewer.id,
                verified_at=resolved_at,
            )
            completion.created_at = resolved_at - timedelta(hours=4)
            db.add(completion)
            db.flush()

            # 6. AI Before & After Analysis
            ai_analysis = AIBeforeAfterAnalysis(
                issue_id=issue.id,
                work_completion_id=completion.id,
                before_media_asset_id=before_media.id,
                after_media_asset_id=after_media.id,
                model_id="gemini-1.5-flash-before-after",
                model_revision="rev-demo-v1",
                visible_change=True,
                possible_mismatch=False,
                insufficient_evidence=False,
                visual_consistency_score=0.92,
                difference_summary=rec["ai_summary"],
                advisory_decision_suggestion="RECOMMEND_APPROVAL",
                status="COMPLETED",
            )
            ai_analysis.created_at = resolved_at - timedelta(hours=3)
            db.add(ai_analysis)

            # 7. Lifecycle Status Events
            events = [
                ("SUBMITTED", created_at, "Citizen registered grievance with photograph"),
                ("UNDER_REVIEW", created_at + timedelta(hours=2), "Panchayat Development Officer verified complaint"),
                ("APPROVED", created_at + timedelta(hours=4), "Grievance accepted and approved for field execution"),
                ("ASSIGNED", created_at + timedelta(hours=6), f"Assigned to village worker {worker_profile.full_name}"),
                ("IN_PROGRESS", created_at + timedelta(hours=12), "Field maintenance team on-site"),
                ("REPAIR_REPORTED", resolved_at - timedelta(hours=4), "Worker uploaded completion proof and notes"),
                ("RESOLVED", resolved_at, f"PDO verified completion. Approved expenditure: Rs {rec['verified_cost']:,.2f}"),
            ]
            for st, ts, reason in events:
                ev = StatusEvent(
                    issue_id=issue.id,
                    actor_profile_id=pdo_reviewer.id,
                    previous_status=None,
                    next_status=st,
                    reason=reason,
                )
                ev.created_at = ts
                db.add(ev)

        db.commit()
        print(f"[DemoGallery] Successfully seeded {len(DEMO_RECORDS)} demonstration records across all 6 civic categories!")
    finally:
        db.close()

if __name__ == "__main__":
    if "--clean" in sys.argv:
        clean_demo_data()
    else:
        seed_demo_data()
