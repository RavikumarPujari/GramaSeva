-- Migration 007: Work Completion, Cost Tracking, Before/After AI Analysis & Citizen Consent
-- GramaSeva Civic Resolution & Public Transparency Architecture

-- 1. Issues extra cost and completion tracking columns
ALTER TABLE issues ADD COLUMN estimated_cost FLOAT;
ALTER TABLE issues ADD COLUMN proposed_cost FLOAT;
ALTER TABLE issues ADD COLUMN materials_cost FLOAT;
ALTER TABLE issues ADD COLUMN labour_cost FLOAT;
ALTER TABLE issues ADD COLUMN other_expenses_cost FLOAT;
ALTER TABLE issues ADD COLUMN verified_cost FLOAT;
ALTER TABLE issues ADD COLUMN cost_status VARCHAR(50) DEFAULT 'UNRECORDED';
ALTER TABLE issues ADD COLUMN work_completed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE issues ADD COLUMN work_completion_description TEXT;
ALTER TABLE issues ADD COLUMN work_performed TEXT;
ALTER TABLE issues ADD COLUMN materials_used TEXT;
ALTER TABLE issues ADD COLUMN labour_details TEXT;
ALTER TABLE issues ADD COLUMN cost_verification_remarks TEXT;
ALTER TABLE issues ADD COLUMN public_display_consent BOOLEAN DEFAULT FALSE;

-- 2. Submissions public display consent
ALTER TABLE submissions ADD COLUMN public_display_consent BOOLEAN DEFAULT FALSE;

-- 3. MediaAssets link to completion submission
ALTER TABLE media_assets ADD COLUMN work_completion_id VARCHAR(36);

-- 4. Work Completions Table (Preserves historical submissions for rework/audit)
CREATE TABLE IF NOT EXISTS work_completions (
    id VARCHAR(36) PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    issue_id VARCHAR(36) REFERENCES issues(id) ON DELETE CASCADE,
    worker_profile_id VARCHAR(36) REFERENCES profiles(id) ON DELETE CASCADE,
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
    completion_date TIMESTAMP WITH TIME ZONE,
    supporting_documents_paths TEXT,
    status VARCHAR(50) DEFAULT 'AWAITING_VERIFICATION',
    pdo_remarks TEXT,
    verified_cost FLOAT,
    verified_by_id VARCHAR(36) REFERENCES profiles(id) ON DELETE SET NULL,
    verified_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS idx_work_completions_issue ON work_completions(issue_id);
CREATE INDEX IF NOT EXISTS idx_work_completions_worker ON work_completions(worker_profile_id);

-- 5. AI Before/After Verification Analyses
CREATE TABLE IF NOT EXISTS ai_before_after_analyses (
    id VARCHAR(36) PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    issue_id VARCHAR(36) REFERENCES issues(id) ON DELETE CASCADE,
    work_completion_id VARCHAR(36),
    before_media_asset_id VARCHAR(36) REFERENCES media_assets(id) ON DELETE SET NULL,
    after_media_asset_id VARCHAR(36) REFERENCES media_assets(id) ON DELETE SET NULL,
    model_id VARCHAR(100) NOT NULL,
    model_revision VARCHAR(64) NOT NULL,
    visible_change BOOLEAN DEFAULT FALSE,
    possible_mismatch BOOLEAN DEFAULT FALSE,
    insufficient_evidence BOOLEAN DEFAULT FALSE,
    visual_consistency_score FLOAT DEFAULT 0.0,
    difference_summary TEXT NOT NULL,
    advisory_decision_suggestion VARCHAR(50) DEFAULT 'REVIEW_FOR_APPROVAL',
    suggested_description TEXT,
    status VARCHAR(50) DEFAULT 'COMPLETED',
    error_message TEXT,
    latency_ms INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_ai_ba_analyses_issue ON ai_before_after_analyses(issue_id);
