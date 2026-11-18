-- FixProof Database Migration: 004_phase8_advanced_features.sql
-- Adds: Assets Register, Recurrence Candidates, Machine Translations Cache, and Issue Escalation tracking

-- 1. Public Infrastructure Asset Register
CREATE TABLE IF NOT EXISTS assets (
    id VARCHAR(36) PRIMARY KEY,
    official_code VARCHAR(50) UNIQUE NOT NULL,
    name_en VARCHAR(255) NOT NULL,
    name_kn VARCHAR(255),
    name_hi VARCHAR(255),
    category VARCHAR(50) NOT NULL, -- road, water_point, street_light, drain, public_facility
    locality_unit_id VARCHAR(36) REFERENCES locality_units(id) ON DELETE SET NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    condition_status VARCHAR(50) NOT NULL DEFAULT 'OPERATIONAL', -- OPERATIONAL, DAMAGED, UNDER_MAINTENANCE
    metadata_json TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_assets_official_code ON assets(official_code);
CREATE INDEX IF NOT EXISTS idx_assets_locality_unit_id ON assets(locality_unit_id);
CREATE INDEX IF NOT EXISTS idx_assets_category ON assets(category);

-- 2. Recurrence Candidates (Links new reports to prior resolved issues)
CREATE TABLE IF NOT EXISTS recurrence_candidates (
    id VARCHAR(36) PRIMARY KEY,
    new_issue_id VARCHAR(36) REFERENCES issues(id) ON DELETE CASCADE NOT NULL,
    prior_issue_id VARCHAR(36) REFERENCES issues(id) ON DELETE CASCADE NOT NULL,
    distance_meters DOUBLE PRECISION NOT NULL,
    days_since_resolution INTEGER NOT NULL,
    decision VARCHAR(50) NOT NULL DEFAULT 'PENDING', -- PENDING, CONFIRMED_RECURRENCE, REJECTED_UNRELATED
    adjudicated_by_id VARCHAR(36) REFERENCES profiles(id) ON DELETE SET NULL,
    adjudicated_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_recurrence_new_issue_id ON recurrence_candidates(new_issue_id);
CREATE INDEX IF NOT EXISTS idx_recurrence_prior_issue_id ON recurrence_candidates(prior_issue_id);

-- 3. Machine Translations Cache (Never overwrites original citizen text)
CREATE TABLE IF NOT EXISTS translations (
    id VARCHAR(36) PRIMARY KEY,
    source_text_hash VARCHAR(64) NOT NULL,
    source_language VARCHAR(10) NOT NULL,
    target_language VARCHAR(10) NOT NULL,
    original_text TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    model_id VARCHAR(100) NOT NULL DEFAULT 'indictrans2-civic-v1',
    is_machine_translated BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_translations_hash_pair ON translations(source_text_hash, source_language, target_language);

-- 4. Alter Issues table for asset linking, recurrence, and operational escalation
-- SQLite and PostgreSQL compatible idempotent column additions
ALTER TABLE issues ADD COLUMN asset_id VARCHAR(36) REFERENCES assets(id) ON DELETE SET NULL;
ALTER TABLE issues ADD COLUMN is_recurrence BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE issues ADD COLUMN prior_resolved_issue_id VARCHAR(36) REFERENCES issues(id) ON DELETE SET NULL;
ALTER TABLE issues ADD COLUMN is_escalated BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE issues ADD COLUMN escalated_at TIMESTAMPTZ;
ALTER TABLE issues ADD COLUMN escalation_reason TEXT;
