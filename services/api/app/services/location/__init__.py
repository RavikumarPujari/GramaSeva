from app.services.location.ocr_service import ocr_location_service, PhotoOCRLocationService
from app.services.location.landmark_service import (
    landmark_service,
    LandmarkRecognitionService,
    BELAGAVI_LANDMARK_REGISTER,
    VerifiedLandmark,
)
from app.services.location.boundary_service import (
    boundary_service,
    VillageBoundaryService,
    VERIFIED_BOUNDARIES,
    VerifiedVillageBoundary,
)
from app.services.location.dual_source_verifier import (
    dual_source_verifier,
    DualSourceLocationVerifier,
    DualSourceVerificationReport,
)

__all__ = [
    "ocr_location_service",
    "PhotoOCRLocationService",
    "landmark_service",
    "LandmarkRecognitionService",
    "BELAGAVI_LANDMARK_REGISTER",
    "VerifiedLandmark",
    "boundary_service",
    "VillageBoundaryService",
    "VERIFIED_BOUNDARIES",
    "VerifiedVillageBoundary",
    "dual_source_verifier",
    "DualSourceLocationVerifier",
    "DualSourceVerificationReport",
]
