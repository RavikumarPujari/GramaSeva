-- FixProof/GramaSeva Database Migration: 005_pdo_worker_governance.sql
-- Adds approval_status and is_primary to role_assignments for Super Admin, PDO, and Worker governance.

ALTER TABLE role_assignments ADD COLUMN IF NOT EXISTS approval_status VARCHAR(50) DEFAULT 'APPROVED';
ALTER TABLE role_assignments ADD COLUMN IF NOT EXISTS is_primary BOOLEAN DEFAULT FALSE;

-- Ensure existing records are marked APPROVED
UPDATE role_assignments SET approval_status = 'APPROVED' WHERE approval_status IS NULL;
