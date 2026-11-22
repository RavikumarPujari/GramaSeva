import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from app.core.config import settings

@dataclass
class ModelDescriptor:
    key: str
    model_id: str
    name: str
    specialist_type: str  # "garbage", "road_damage", "waterlogging", "general_civic"
    primary_category: str
    description: str
    is_enabled: bool = True
    last_status: str = "READY"
    last_error: Optional[str] = None
    latency_ms: int = 0
    version: str = "1"

class RoboflowModelRegistry:
    """
    Central Model Registry for the Five Exact Roboflow Models:
      1. garbage_detection-wvzwv-n8vsv/1 (Garbage Dumps, Waste, Litter)
      2. road-damage-detection-fn0qh/1 (Potholes, Road Cracks, Damaged Asphalt)
      3. water-logging-a7zhi/1 (Waterlogging, Flooding, Stagnant Water)
      4. civic-issues-lroee/3 (General Civic & Infrastructure Issues)
      5. civic-issues-nq7sy-bh8t3/1 (Secondary Civic Issue Recognition & Consensus)
    """

    def __init__(self):
        self._models: Dict[str, ModelDescriptor] = {}
        self._initialize_registry()

    def _initialize_registry(self):
        # Model 1 — Garbage Detection
        m1_id = os.environ.get("ROBOFLOW_MODEL_GARBAGE") or settings.roboflow_model_garbage or "garbage_detection-wvzwv-n8vsv/1"
        self._models["garbage"] = ModelDescriptor(
            key="garbage",
            model_id=m1_id,
            name="Roboflow Garbage & Solid Waste Specialist",
            specialist_type="garbage",
            primary_category="garbage",
            description="Dedicated detection of garbage heaps, illegal dumping, plastic waste, and roadside litter.",
            version=m1_id.split("/")[-1] if "/" in m1_id else "1",
        )

        # Model 2 — Road Damage Detection
        m2_id = os.environ.get("ROBOFLOW_MODEL_ROAD") or settings.roboflow_model_road or "road-damage-detection-fn0qh/1"
        self._models["road"] = ModelDescriptor(
            key="road",
            model_id=m2_id,
            name="Roboflow Road Damage & Pothole Specialist",
            specialist_type="road_damage",
            primary_category="road_damage",
            description="High-precision detection of potholes, longitudinal cracks, alligator cracks, and damaged road surfaces.",
            version=m2_id.split("/")[-1] if "/" in m2_id else "1",
        )

        # Model 3 — Waterlogging Detection
        m3_id = os.environ.get("ROBOFLOW_MODEL_WATERLOGGING") or settings.roboflow_model_waterlogging or "water-logging-a7zhi/1"
        self._models["waterlogging"] = ModelDescriptor(
            key="waterlogging",
            model_id=m3_id,
            name="Roboflow Waterlogging & Flood Specialist",
            specialist_type="waterlogging",
            primary_category="drainage",
            description="Detection of waterlogged roads, standing/stagnant water pools, and overflowing drain basins.",
            version=m3_id.split("/")[-1] if "/" in m3_id else "1",
        )

        # Model 4 — Civic Issues Detection
        m4_id = os.environ.get("ROBOFLOW_MODEL_CIVIC_1") or settings.roboflow_model_civic_1 or "civic-issues-lroee/3"
        self._models["civic_1"] = ModelDescriptor(
            key="civic_1",
            model_id=m4_id,
            name="Roboflow Primary Civic Infrastructure Detector",
            specialist_type="general_civic",
            primary_category="other",
            description="Multi-class civic infrastructure problem detector covering public fixtures, drainage, and road hazards.",
            version=m4_id.split("/")[-1] if "/" in m4_id else "3",
        )

        # Model 5 — Civic Issues Detection 2
        m5_id = os.environ.get("ROBOFLOW_MODEL_CIVIC_2") or settings.roboflow_model_civic_2 or "civic-issues-nq7sy-bh8t3/1"
        self._models["civic_2"] = ModelDescriptor(
            key="civic_2",
            model_id=m5_id,
            name="Roboflow Secondary Civic Issue Detector",
            specialist_type="general_civic",
            primary_category="other",
            description="Secondary multi-class civic issue detector providing independent validation and consensus scoring.",
            version=m5_id.split("/")[-1] if "/" in m5_id else "1",
        )

    def get_model(self, key: str) -> Optional[ModelDescriptor]:
        return self._models.get(key)

    def get_all_models(self) -> List[ModelDescriptor]:
        return list(self._models.values())

    def update_model_health(self, key: str, status: str, latency_ms: int = 0, error: Optional[str] = None):
        if key in self._models:
            self._models[key].last_status = status
            self._models[key].latency_ms = latency_ms
            self._models[key].last_error = error
            if status in ("UNAUTHORIZED", "MODEL_NOT_FOUND"):
                # Mark as disabled independently without impacting other models
                self._models[key].is_enabled = False

    def get_status_summary(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": m.key,
                "model_id": m.model_id,
                "name": m.name,
                "specialist_type": m.specialist_type,
                "primary_category": m.primary_category,
                "is_enabled": m.is_enabled,
                "status": m.last_status,
                "latency_ms": m.latency_ms,
                "error": m.last_error,
                "version": m.version,
            }
            for m in self._models.values()
        ]

# Global registry instance
model_registry = RoboflowModelRegistry()
