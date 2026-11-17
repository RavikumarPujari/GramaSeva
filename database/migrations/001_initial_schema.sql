-- FixProof Database Initial Schema Migration (PostgreSQL + PostGIS)
-- Version: 001_initial_schema.sql
-- Enables PostGIS spatial engine, UUID generation, core entities, spatial indexes and RLS policies.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- 1. Organizations (Pilot tenancy)
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Locality Units (First-class Village & Ward hierarchy)
CREATE TABLE IF NOT EXISTS locality_units (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    unit_type VARCHAR(50) NOT NULL, -- state, district, taluk, gram_panchayat, village, ward, etc.
    parent_id UUID REFERENCES locality_units(id) ON DELETE CASCADE,
    official_code VARCHAR(50),
    name_en VARCHAR(255) NOT NULL,
    name_kn VARCHAR(255) NOT NULL,
    name_hi VARCHAR(255) NOT NULL,
    boundary GEOMETRY(MultiPolygon, 4326),
    boundary_geojson TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_locality_units_org ON locality_units(organization_id);
CREATE INDEX IF NOT EXISTS idx_locality_units_parent ON locality_units(parent_id);
CREATE INDEX IF NOT EXISTS idx_locality_units_type ON locality_units(unit_type);
CREATE INDEX IF NOT EXISTS idx_locality_units_geom ON locality_units USING GIST(boundary);

-- 3. Departments
CREATE TABLE IF NOT EXISTS departments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    name_en VARCHAR(255) NOT NULL,
    name_kn VARCHAR(255) NOT NULL,
    name_hi VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_departments_org ON departments(organization_id);

-- 4. Department Jurisdictions
CREATE TABLE IF NOT EXISTS department_jurisdictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    department_id UUID NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    locality_unit_id UUID NOT NULL REFERENCES locality_units(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. Profiles (Users)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(50), -- Private
    preferred_locale VARCHAR(10) NOT NULL DEFAULT 'en',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_profiles_email ON profiles(email);

-- 6. Role Assignments (RBAC + Jurisdiction Scope)
CREATE TABLE IF NOT EXISTS role_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL, -- citizen, reviewer, worker, admin
    department_id UUID REFERENCES departments(id) ON DELETE SET NULL,
    jurisdiction_unit_id UUID REFERENCES locality_units(id) ON DELETE SET NULL,
    granted_by UUID REFERENCES profiles(id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    valid_from TIMESTAMPTZ,
    valid_to TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_role_assignments_profile ON role_assignments(profile_id);
CREATE INDEX IF NOT EXISTS idx_role_assignments_role ON role_assignments(role);
CREATE INDEX IF NOT EXISTS idx_role_assignments_jurisdiction ON role_assignments(jurisdiction_unit_id);

-- 7. Issues (Shared Physical Issue)
CREATE TABLE IF NOT EXISTS issues (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reference_number VARCHAR(50) UNIQUE NOT NULL,
    category VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'SUBMITTED',
    priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    locality_unit_id UUID REFERENCES locality_units(id) ON DELETE SET NULL,
    location GEOMETRY(Point, 4326), -- Restricted operational location
    public_location GEOMETRY(Point, 4326), -- Sanitized public location
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    public_latitude DOUBLE PRECISION,
    public_longitude DOUBLE PRECISION,
    department_id UUID REFERENCES departments(id) ON DELETE SET NULL,
    assigned_worker_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    reviewed_by_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    resolved_at TIMESTAMPTZ,
    resolution_review_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_issues_ref ON issues(reference_number);
CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status);
CREATE INDEX IF NOT EXISTS idx_issues_locality ON issues(locality_unit_id);
CREATE INDEX IF NOT EXISTS idx_issues_location ON issues USING GIST(location);

-- 8. Submissions (Citizen Reports)
CREATE TABLE IF NOT EXISTS submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tracking_id VARCHAR(50) UNIQUE NOT NULL,
    reporter_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    issue_id UUID REFERENCES issues(id) ON DELETE SET NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    locale VARCHAR(10) NOT NULL DEFAULT 'en',
    original_text TEXT,
    locality_unit_id UUID REFERENCES locality_units(id) ON DELETE SET NULL,
    village_name VARCHAR(255),
    ward_name VARCHAR(255),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    is_anonymous BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_submissions_tracking ON submissions(tracking_id);
CREATE INDEX IF NOT EXISTS idx_submissions_reporter ON submissions(reporter_id);
CREATE INDEX IF NOT EXISTS idx_submissions_issue ON submissions(issue_id);

-- 9. Media Assets (Evidence storage)
CREATE TABLE IF NOT EXISTS media_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    submission_id UUID REFERENCES submissions(id) ON DELETE CASCADE,
    issue_id UUID REFERENCES issues(id) ON DELETE CASCADE,
    evidence_role VARCHAR(50) NOT NULL, -- CITIZEN_BEFORE, WORKER_PROGRESS, WORKER_AFTER
    storage_path VARCHAR(500) NOT NULL,
    file_hash VARCHAR(64),
    mime_type VARCHAR(100) NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    is_quarantined BOOLEAN NOT NULL DEFAULT TRUE,
    is_public_approved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 10. Audit Logs (Immutable privileged history)
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor_profile_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    target_type VARCHAR(100) NOT NULL,
    target_id VARCHAR(36) NOT NULL,
    details_json TEXT,
    client_ip VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Row Level Security (RLS) Baseline
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE media_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Citizens can only select/update their own profile
CREATE POLICY profiles_owner_policy ON profiles
    FOR ALL USING (id = auth.uid());

-- Citizens can only select their own submissions; Staff with active role can select scoped submissions
CREATE POLICY submissions_citizen_policy ON submissions
    FOR ALL USING (reporter_id = auth.uid());
