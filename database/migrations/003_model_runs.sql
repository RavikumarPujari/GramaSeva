-- FixProof Database Migration: 003_model_runs.sql
-- Records real AI model inference runs, version provenance, metrics, and confirmation decisions

CREATE TABLE IF NOT EXISTS model_runs (
    id VARCHAR(36) PRIMARY KEY,
    job_id VARCHAR(36),
    media_asset_id VARCHAR(36) REFERENCES media_assets(id) ON DELETE CASCADE,
    issue_id VARCHAR(36) REFERENCES issues(id) ON DELETE CASCADE,
    submission_id VARCHAR(36) REFERENCES submissions(id) ON DELETE CASCADE,
    model_id VARCHAR(100) NOT NULL,
    model_revision VARCHAR(64) NOT NULL,
    task VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'COMPLETED',
    category_suggestion VARCHAR(50),
    confidence_score DOUBLE PRECISION,
    detections_json TEXT,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    requires_human_review BOOLEAN NOT NULL DEFAULT TRUE,
    limitations_json TEXT,
    confirmed_by_profile_id VARCHAR(36) REFERENCES profiles(id) ON DELETE SET NULL,
    confirmed_decision VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_model_runs_media_asset_id ON model_runs(media_asset_id);
CREATE INDEX IF NOT EXISTS idx_model_runs_issue_id ON model_runs(issue_id);
CREATE INDEX IF NOT EXISTS idx_model_runs_submission_id ON model_runs(submission_id);
CREATE INDEX IF NOT EXISTS idx_model_runs_model_id ON model_runs(model_id);
