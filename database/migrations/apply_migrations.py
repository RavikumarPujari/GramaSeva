import sqlite3
import os

db_paths = ["fixproof_dev.db", "services/api/fixproof_dev.db"]

for p in db_paths:
    if not os.path.exists(p):
        continue
    conn = sqlite3.connect(p)
    cur = conn.cursor()
    
    # Check role_assignments
    cur.execute("PRAGMA table_info(role_assignments);")
    cols = [r[1] for r in cur.fetchall()]
    if "approval_status" not in cols:
        cur.execute("ALTER TABLE role_assignments ADD COLUMN approval_status VARCHAR(50) DEFAULT 'APPROVED'")
        print(f"[{p}] Added approval_status column")
    if "is_primary" not in cols:
        cur.execute("ALTER TABLE role_assignments ADD COLUMN is_primary BOOLEAN DEFAULT 0")
        print(f"[{p}] Added is_primary column")

    # Check profiles extra columns
    cur.execute("PRAGMA table_info(profiles);")
    pcols = [r[1] for r in cur.fetchall()]
    for col, col_type in [("address", "TEXT"), ("taluk", "VARCHAR(100)"), ("district", "VARCHAR(100)"), ("state", "VARCHAR(100)"), ("avatar_url", "VARCHAR(500)")]:
        if col not in pcols:
            cur.execute(f"ALTER TABLE profiles ADD COLUMN {col} {col_type}")
            print(f"[{p}] Added profiles.{col} column")

    # Create announcements table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS announcements (
        id VARCHAR(36) PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        sender_id VARCHAR(36),
        title VARCHAR(255) NOT NULL,
        content TEXT NOT NULL,
        target_type VARCHAR(50) NOT NULL,
        target_village_ids TEXT,
        target_pdo_id VARCHAR(36),
        delivered_count INTEGER DEFAULT 0
    );
    """)

    # Create ward_members table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ward_members (
        id VARCHAR(36) PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ward_unit_id VARCHAR(36),
        profile_id VARCHAR(36),
        full_name VARCHAR(255) NOT NULL,
        phone_number VARCHAR(50),
        email VARCHAR(255),
        designation VARCHAR(100) DEFAULT 'Ward Member',
        term_start TIMESTAMP,
        term_end TIMESTAMP,
        is_active BOOLEAN DEFAULT 1
    );
    """)

    # Create citizen_ward_registrations table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS citizen_ward_registrations (
        id VARCHAR(36) PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        profile_id VARCHAR(36),
        ward_unit_id VARCHAR(36),
        is_primary BOOLEAN DEFAULT 0,
        residence_type VARCHAR(50) DEFAULT 'RESIDENT',
        verification_status VARCHAR(50) DEFAULT 'SELF_DECLARED'
    );
    """)

    # Create citizen_documents table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS citizen_documents (
        id VARCHAR(36) PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        profile_id VARCHAR(36),
        title VARCHAR(255) NOT NULL,
        document_type VARCHAR(50) NOT NULL,
        file_url VARCHAR(500) NOT NULL,
        file_size_bytes INTEGER DEFAULT 0,
        verification_status VARCHAR(50) DEFAULT 'PENDING',
        rejection_reason TEXT
    );
    """)

    # Migration 007: issues extra columns
    cur.execute("PRAGMA table_info(issues);")
    icols = [r[1] for r in cur.fetchall()]
    issue_fields = [
        ("estimated_cost", "FLOAT"),
        ("proposed_cost", "FLOAT"),
        ("materials_cost", "FLOAT"),
        ("labour_cost", "FLOAT"),
        ("other_expenses_cost", "FLOAT"),
        ("verified_cost", "FLOAT"),
        ("cost_status", "VARCHAR(50) DEFAULT 'UNRECORDED'"),
        ("work_completed_at", "TIMESTAMP"),
        ("work_completion_description", "TEXT"),
        ("work_performed", "TEXT"),
        ("materials_used", "TEXT"),
        ("labour_details", "TEXT"),
        ("cost_verification_remarks", "TEXT"),
        ("public_display_consent", "BOOLEAN DEFAULT 0"),
    ]
    for col, col_type in issue_fields:
        if col not in icols:
            cur.execute(f"ALTER TABLE issues ADD COLUMN {col} {col_type}")
            print(f"[{p}] Added issues.{col} column")

    # Migration 007: submissions extra columns
    cur.execute("PRAGMA table_info(submissions);")
    scols = [r[1] for r in cur.fetchall()]
    if "public_display_consent" not in scols:
        cur.execute("ALTER TABLE submissions ADD COLUMN public_display_consent BOOLEAN DEFAULT 0")
        print(f"[{p}] Added submissions.public_display_consent column")

    # Migration 007: media_assets extra columns
    cur.execute("PRAGMA table_info(media_assets);")
    mcols = [r[1] for r in cur.fetchall()]
    if "work_completion_id" not in mcols:
        cur.execute("ALTER TABLE media_assets ADD COLUMN work_completion_id VARCHAR(36)")
        print(f"[{p}] Added media_assets.work_completion_id column")

    # Create work_completions table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS work_completions (
        id VARCHAR(36) PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        issue_id VARCHAR(36),
        worker_profile_id VARCHAR(36),
        assignment_id VARCHAR(36),
        submission_number INTEGER DEFAULT 1,
        work_description TEXT NOT NULL,
        work_performed TEXT,
        materials_used TEXT,
        labour_details TEXT,
        materials_cost FLOAT DEFAULT 0.0,
        labour_cost FLOAT DEFAULT 0.0,
        other_expenses_cost FLOAT DEFAULT 0.0,
        proposed_cost FLOAT DEFAULT 0.0,
        completion_date TIMESTAMP,
        supporting_documents_paths TEXT,
        status VARCHAR(50) DEFAULT 'AWAITING_VERIFICATION',
        pdo_remarks TEXT,
        verified_cost FLOAT,
        verified_by_id VARCHAR(36),
        verified_at TIMESTAMP
    );
    """)

    # Create ai_before_after_analyses table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ai_before_after_analyses (
        id VARCHAR(36) PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        issue_id VARCHAR(36),
        work_completion_id VARCHAR(36),
        before_media_asset_id VARCHAR(36),
        after_media_asset_id VARCHAR(36),
        model_id VARCHAR(100) NOT NULL,
        model_revision VARCHAR(64) NOT NULL,
        visible_change BOOLEAN DEFAULT 0,
        possible_mismatch BOOLEAN DEFAULT 0,
        insufficient_evidence BOOLEAN DEFAULT 0,
        visual_consistency_score FLOAT DEFAULT 0.0,
        difference_summary TEXT NOT NULL,
        advisory_decision_suggestion VARCHAR(50) DEFAULT 'REVIEW_FOR_APPROVAL',
        suggested_description TEXT,
        status VARCHAR(50) DEFAULT 'COMPLETED',
        error_message TEXT,
        latency_ms INTEGER DEFAULT 0
    );
    """)

    conn.commit()
    conn.close()
    print(f"[{p}] Migrations applied successfully.")
