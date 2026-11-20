-- Migration 006: Taluk Announcements, Ward Members, Citizen Multiple Wards, and Citizen Documents

-- 1. Profiles extra fields
ALTER TABLE profiles ADD COLUMN address TEXT;
ALTER TABLE profiles ADD COLUMN taluk VARCHAR(100);
ALTER TABLE profiles ADD COLUMN district VARCHAR(100);
ALTER TABLE profiles ADD COLUMN state VARCHAR(100);
ALTER TABLE profiles ADD COLUMN avatar_url VARCHAR(500);

-- 2. Announcements table (Super Admin Taluk level)
CREATE TABLE IF NOT EXISTS announcements (
    id VARCHAR(36) PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    sender_id VARCHAR(36) REFERENCES profiles(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    target_type VARCHAR(50) NOT NULL, -- ALL_PDOS, SELECTED_VILLAGES, INDIVIDUAL_PDO
    target_village_ids TEXT,          -- JSON or comma-separated list
    target_pdo_id VARCHAR(36) REFERENCES profiles(id) ON DELETE SET NULL,
    delivered_count INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_announcements_sender ON announcements(sender_id);

-- 3. Ward members table (Village PDO Ward management)
CREATE TABLE IF NOT EXISTS ward_members (
    id VARCHAR(36) PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ward_unit_id VARCHAR(36) REFERENCES locality_units(id) ON DELETE CASCADE,
    profile_id VARCHAR(36) REFERENCES profiles(id) ON DELETE SET NULL,
    full_name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(50),
    email VARCHAR(255),
    designation VARCHAR(100) DEFAULT 'Ward Member',
    term_start TIMESTAMP WITH TIME ZONE,
    term_end TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_ward_members_ward ON ward_members(ward_unit_id);

-- 4. Citizen Multiple Wards
CREATE TABLE IF NOT EXISTS citizen_ward_registrations (
    id VARCHAR(36) PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    profile_id VARCHAR(36) REFERENCES profiles(id) ON DELETE CASCADE,
    ward_unit_id VARCHAR(36) REFERENCES locality_units(id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT FALSE,
    residence_type VARCHAR(50) DEFAULT 'RESIDENT',
    verification_status VARCHAR(50) DEFAULT 'SELF_DECLARED'
);
CREATE INDEX IF NOT EXISTS idx_citizen_wards_profile ON citizen_ward_registrations(profile_id);

-- 5. Citizen Documents
CREATE TABLE IF NOT EXISTS citizen_documents (
    id VARCHAR(36) PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    profile_id VARCHAR(36) REFERENCES profiles(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    file_url VARCHAR(500) NOT NULL,
    file_size_bytes INTEGER DEFAULT 0,
    verification_status VARCHAR(50) DEFAULT 'PENDING',
    rejection_reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_citizen_docs_profile ON citizen_documents(profile_id);
