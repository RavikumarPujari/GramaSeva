-- FixProof Database Migration: 002_public_notifications_feedback.sql
-- Adds tables for Citizen Feedback, In-app Notifications, and Public Projections

CREATE TABLE IF NOT EXISTS feedback (
    id VARCHAR(36) PRIMARY KEY,
    issue_id VARCHAR(36) NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    citizen_profile_id VARCHAR(36) NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    is_satisfied BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feedback_issue_id ON feedback(issue_id);
CREATE INDEX IF NOT EXISTS idx_feedback_citizen_profile_id ON feedback(citizen_profile_id);

CREATE TABLE IF NOT EXISTS notifications (
    id VARCHAR(36) PRIMARY KEY,
    profile_id VARCHAR(36) NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    issue_id VARCHAR(36) REFERENCES issues(id) ON DELETE SET NULL,
    event_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    locale VARCHAR(10) NOT NULL DEFAULT 'en',
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    dedup_key VARCHAR(150) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notifications_profile_id ON notifications(profile_id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_dedup_key ON notifications(dedup_key);

-- Sanitized Public View / Projection for transparency queries
CREATE OR REPLACE VIEW public_issues_projection AS
SELECT 
    i.id,
    i.reference_number,
    i.category,
    i.status,
    i.priority,
    i.created_at,
    i.resolved_at,
    ROUND(CAST(COALESCE(i.public_latitude, i.latitude) AS NUMERIC), 3) AS public_latitude,
    ROUND(CAST(COALESCE(i.public_longitude, i.longitude) AS NUMERIC), 3) AS public_longitude,
    lu.name_en AS locality_name,
    lu.unit_type AS locality_type,
    (SELECT COUNT(*) FROM submissions s WHERE s.issue_id = i.id) AS submissions_count,
    (SELECT COUNT(*) FROM media_assets m WHERE m.issue_id = i.id AND m.is_public_approved = TRUE AND m.is_quarantined = FALSE) AS public_media_count
FROM issues i
LEFT JOIN locality_units lu ON i.locality_unit_id = lu.id
WHERE i.status != 'DRAFT';
