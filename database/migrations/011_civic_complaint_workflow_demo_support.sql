-- Migration 011: Complete Civic Complaint Workflow & Demonstration Data Support
-- Adds demonstration flags, PDO clarification/rejection metadata, and worker target assignment dates.

-- 1. Issues table enhancements
ALTER TABLE issues ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT FALSE NOT NULL;
ALTER TABLE issues ADD COLUMN IF NOT EXISTS clarification_message TEXT;
ALTER TABLE issues ADD COLUMN IF NOT EXISTS clarification_response TEXT;
ALTER TABLE issues ADD COLUMN IF NOT EXISTS rejection_reason TEXT;
ALTER TABLE issues ADD COLUMN IF NOT EXISTS rejection_by_id VARCHAR(36);

-- 2. Submissions table enhancements
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT FALSE NOT NULL;

-- 3. Assignments table enhancements
ALTER TABLE assignments ADD COLUMN IF NOT EXISTS target_date TIMESTAMP;

-- Indices for rapid demonstration filtering & isolation
CREATE INDEX IF NOT EXISTS idx_issues_is_demo ON issues(is_demo);
CREATE INDEX IF NOT EXISTS idx_submissions_is_demo ON submissions(is_demo);
