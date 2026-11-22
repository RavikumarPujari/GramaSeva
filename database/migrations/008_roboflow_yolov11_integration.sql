-- FixProof Database Migration: 008_roboflow_yolov11_integration.sql
-- Records Roboflow YOLOv11 model runs, model provider, citizen confirmed category, and error tracking

ALTER TABLE model_runs ADD COLUMN model_provider VARCHAR(50) DEFAULT 'roboflow';
ALTER TABLE model_runs ADD COLUMN citizen_confirmed_category VARCHAR(50);
ALTER TABLE model_runs ADD COLUMN error_info TEXT;
ALTER TABLE model_runs ADD COLUMN duplicate_candidates_json TEXT;
