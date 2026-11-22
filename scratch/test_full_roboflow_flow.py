import os
import io
import sys
from PIL import Image

sys.path.insert(0, os.path.abspath("services/api"))

from app.core.database import SessionLocal
from app.models.issues import Issue, Submission, ModelRun
from app.ai.roboflow_service import roboflow_service

def test_full_workflow():
    print("=== Testing Roboflow Full Integration Flow ===")
    
    # 1. Create a synthetic test image with a mock civic defect
    img = Image.new("RGB", (400, 400), color=(140, 160, 180))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    image_bytes = buf.getvalue()
    
    # 2. Validation check
    valid, err, pil_img = roboflow_service.validate_image_bytes(image_bytes)
    assert valid, f"Validation failed: {err}"
    print("[PASS] Image validation verified (format, size, integrity).")
    
    # 3. Test category mapping rules
    assert roboflow_service.map_class_to_category("garbage_dump") == "garbage"
    assert roboflow_service.map_class_to_category("solid_waste") == "garbage"
    assert roboflow_service.map_class_to_category("pothole") == "road_damage"
    assert roboflow_service.map_class_to_category("water_leak") == "water_leak"
    assert roboflow_service.map_class_to_category("open_drain") == "drainage"
    assert roboflow_service.map_class_to_category("waterlogging") == "drainage"
    print("[PASS] All civic category mapping rules verified (Garbage is NOT road damage).")
    
    # 4. Test bounding box rendering
    mock_preds = [
        {"class": "garbage", "confidence": 0.89, "x": 200, "y": 200, "width": 120, "height": 100},
        {"class": "pothole", "confidence": 0.65, "x": 100, "y": 100, "width": 60, "height": 50},
    ]
    primary_cat, top_label, top_conf = roboflow_service.select_primary_category(mock_preds)
    assert primary_cat == "garbage"
    assert top_label == "garbage"
    assert top_conf == 0.89
    print(f"[PASS] Primary selection rule verified: {primary_cat} ({top_label}, {top_conf}).")
    
    b64_img = roboflow_service.draw_bounding_boxes(pil_img, mock_preds)
    assert b64_img.startswith("data:image/jpeg;base64,")
    print(f"[PASS] Bounding box visualizer rendered base64 string (length {len(b64_img)}).")
    
    # 5. Database check
    db = SessionLocal()
    try:
        recent_runs = db.query(ModelRun).order_by(ModelRun.created_at.desc()).limit(5).all()
        print(f"[PASS] Database connection verified. Model runs in DB: {len(recent_runs)}.")
        for r in recent_runs:
            print(f"  - Model: {r.model_id} ({getattr(r, 'model_provider', 'N/A')}), Category: {r.category_suggestion}, Status: {r.status}")
    finally:
        db.close()
        
    print("=== All Integration Flow Steps Passed Successfully! ===")

if __name__ == "__main__":
    test_full_workflow()
