-- Migration 010: Google Maps Geocoding Persistence
-- Persists Google Maps reverse geocoding address components, place_id, and confirmation status.

ALTER TABLE submissions ADD COLUMN IF NOT EXISTS detected_village VARCHAR(255);
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS detected_taluk VARCHAR(100);
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS detected_district VARCHAR(100);
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS detected_state VARCHAR(100);
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS detected_country VARCHAR(100) DEFAULT 'India';
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS detected_postal_code VARCHAR(20);
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS google_place_id VARCHAR(255);
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS geocoding_status VARCHAR(50);
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS location_confirmation_status VARCHAR(50) DEFAULT 'UNCONFIRMED';
