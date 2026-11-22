-- FixProof / GramaSeva Migration: 009_advanced_location_and_photo_recognition.sql
-- Adds support for 5-model Roboflow inference records, OCR & landmark location clues,
-- confirmed coordinates, dual-source jurisdiction verification, and location audit trail.

-- 1. Extend submissions table with photo location & confirmed coordinates
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS gps_timestamp TIMESTAMPTZ;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS ocr_extracted_text TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS ocr_detections_json TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS landmark_candidates_json TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS photo_location_status VARCHAR(50) DEFAULT 'NOT_EVALUATED';
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS photo_location_provider VARCHAR(100);
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS confirmed_latitude DOUBLE PRECISION;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS confirmed_longitude DOUBLE PRECISION;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS confirmed_village VARCHAR(255);
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS confirmed_address TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS confirmation_method VARCHAR(50) DEFAULT 'CITIZEN_CONFIRMED';
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS jurisdiction_status VARCHAR(50) DEFAULT 'VERIFIED';
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS location_conflict_flag BOOLEAN DEFAULT FALSE;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS location_conflict_details TEXT;

-- 2. Extend issues table with jurisdiction status and location conflict flags
ALTER TABLE issues ADD COLUMN IF NOT EXISTS jurisdiction_status VARCHAR(50) DEFAULT 'VERIFIED';
ALTER TABLE issues ADD COLUMN IF NOT EXISTS has_location_conflict BOOLEAN DEFAULT FALSE;
ALTER TABLE issues ADD COLUMN IF NOT EXISTS location_conflict_details TEXT;

-- 3. Create immutable Location Audit Log table
CREATE TABLE IF NOT EXISTS location_audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    submission_id VARCHAR(36) REFERENCES submissions(id) ON DELETE CASCADE,
    issue_id VARCHAR(36) REFERENCES issues(id) ON DELETE CASCADE,
    actor_id VARCHAR(36) REFERENCES profiles(id) ON DELETE SET NULL,
    actor_role VARCHAR(50) NOT NULL DEFAULT 'citizen',
    field_changed VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_loc_audit_submission_id ON location_audit_logs(submission_id);
CREATE INDEX IF NOT EXISTS idx_loc_audit_issue_id ON location_audit_logs(issue_id);
CREATE INDEX IF NOT EXISTS idx_loc_audit_actor_id ON location_audit_logs(actor_id);
