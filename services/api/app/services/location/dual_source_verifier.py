from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from app.services.geocoding.reverse_geocoder import reverse_geocoder, GeocodedAddress
from app.services.location.boundary_service import boundary_service
from app.services.location.ocr_service import ocr_location_service
from app.services.location.landmark_service import landmark_service
from PIL import Image

@dataclass
class DualSourceVerificationReport:
    # 1. Coordinate Status
    latitude: float
    longitude: float
    gps_accuracy_meters: Optional[float]
    acquisition_method: str  # "GPS_VERIFIED" or "MANUAL"

    # 2. Reverse-Geocoded Address
    formatted_address: str
    geocoded_village: Optional[str]
    taluk: str
    district: str

    # 3. Boundary & Jurisdiction
    is_boundary_verified: bool
    verified_village: Optional[str]
    gram_panchayat: Optional[str]
    jurisdiction_status: str  # "VERIFIED", "VERIFIED_PERIPHERY", "UNVERIFIED_OUTSIDE_PILOT", "CONFLICT_REVIEW"

    # 4. Photo Clues & Comparison
    has_photo_clues: bool
    ocr_extracted_text: Optional[str]
    ocr_matched_villages: List[str]
    landmark_candidates_count: int
    top_landmark_name: Optional[str]
    top_landmark_similarity: float

    # 5. Dual-Source Agreement / Conflict
    gps_photo_agreement: bool
    gps_photo_conflict: bool
    conflict_details: Optional[str]

    # 6. Overall Status & Recommendation
    overall_status: str  # "VERIFIED_AGREEMENT", "VERIFIED_GPS_ONLY", "PHOTO_CONFLICT_PENDING_REVIEW", "OUTSIDE_PILOT_MANUAL"
    summary_message: str
    requires_pdo_review: bool

class DualSourceLocationVerifier:
    """
    Dual-Source Location Verification Engine (Part 13).
    Cross-references hardware GPS coordinates, reverse-geocoded addresses,
    official village boundaries, OCR-extracted signboards, and visual landmark matches.
    """

    @staticmethod
    def verify(
        latitude: float,
        longitude: float,
        gps_accuracy: Optional[float] = None,
        acquisition_method: str = "GPS_VERIFIED",
        img: Optional[Image.Image] = None,
        selected_village: Optional[str] = None,
    ) -> DualSourceVerificationReport:
        # 1. Reverse-geocode coordinates
        addr = reverse_geocoder.reverse_geocode(latitude, longitude)

        # 2. Check verified Belagavi village boundaries
        boundary_res = boundary_service.verify_point(latitude, longitude)
        is_boundary_verified = boundary_res["is_verified"]
        verified_village = boundary_res["village_name"]
        gram_panchayat = boundary_res["gram_panchayat"]
        jurisdiction_status = boundary_res["jurisdiction_status"]

        # 3. Analyze Photo Clues (OCR & Landmarks) if image provided
        ocr_res = {"status": "NO_IMAGE", "has_location_clues": False, "matched_villages": [], "extracted_text": None}
        lm_res = {"status": "NO_IMAGE", "has_candidate_landmarks": False, "candidates": []}

        if img is not None:
            ocr_res = ocr_location_service.extract_location_clues(img)
            lm_res = landmark_service.find_candidate_landmarks(img, latitude, longitude)

        has_photo_clues = ocr_res["has_location_clues"] or lm_res["has_candidate_landmarks"]
        ocr_matched_villages = ocr_res["matched_villages"]

        top_landmark = lm_res["candidates"][0] if lm_res["candidates"] else None
        top_landmark_name = top_landmark["name"] if top_landmark else None
        top_landmark_similarity = float(top_landmark["similarity_score"]) if top_landmark else 0.0

        # 4. Compare GPS vs Photo Clues (Dual-Source Agreement / Conflict)
        gps_photo_agreement = False
        gps_photo_conflict = False
        conflict_details = None

        if ocr_matched_villages:
            # Check if any OCR-matched village corresponds to verified village or citizen selection
            ref_village = verified_village or selected_village
            if ref_village and any(ref_village.lower() in mv.lower() for mv in ocr_matched_villages):
                gps_photo_agreement = True
            elif ref_village:
                # OCR found a distinct village name that differs from GPS location
                gps_photo_conflict = True
                conflict_details = (
                    f"Photo signboard indicates '{', '.join(ocr_matched_villages)}', "
                    f"which differs from GPS detected village '{ref_village}'."
                )

        if not gps_photo_conflict and top_landmark and verified_village:
            if top_landmark["village"].lower() == verified_village.lower():
                gps_photo_agreement = True

        # 5. Formulate Overall Status & Recommendation
        requires_pdo_review = False

        if gps_photo_conflict:
            overall_status = "PHOTO_CONFLICT_PENDING_REVIEW"
            summary_message = f"Location conflict detected: {conflict_details} Routed for PDO review."
            jurisdiction_status = "CONFLICT_REVIEW"
            requires_pdo_review = True
        elif is_boundary_verified and gps_photo_agreement:
            overall_status = "VERIFIED_AGREEMENT"
            summary_message = f"High-confidence dual-source verification: GPS and photo evidence both confirm {verified_village}."
        elif is_boundary_verified:
            overall_status = "VERIFIED_GPS_ONLY"
            summary_message = f"GPS coordinates verified within {gram_panchayat}. Photo contains no conflicting location clues."
        else:
            overall_status = "OUTSIDE_PILOT_MANUAL"
            summary_message = f"Coordinates are outside verified Belagavi pilot boundaries ({selected_village or 'Manual Selection'})."
            jurisdiction_status = "UNVERIFIED_OUTSIDE_PILOT"
            requires_pdo_review = True

        return DualSourceVerificationReport(
            latitude=latitude,
            longitude=longitude,
            gps_accuracy_meters=gps_accuracy,
            acquisition_method=acquisition_method,
            formatted_address=addr.formatted_address,
            geocoded_village=addr.village_locality,
            taluk=addr.taluk,
            district=addr.district,
            is_boundary_verified=is_boundary_verified,
            verified_village=verified_village,
            gram_panchayat=gram_panchayat,
            jurisdiction_status=jurisdiction_status,
            has_photo_clues=has_photo_clues,
            ocr_extracted_text=ocr_res.get("extracted_text"),
            ocr_matched_villages=ocr_matched_villages,
            landmark_candidates_count=len(lm_res.get("candidates", [])),
            top_landmark_name=top_landmark_name,
            top_landmark_similarity=top_landmark_similarity,
            gps_photo_agreement=gps_photo_agreement,
            gps_photo_conflict=gps_photo_conflict,
            conflict_details=conflict_details,
            overall_status=overall_status,
            summary_message=summary_message,
            requires_pdo_review=requires_pdo_review,
        )

dual_source_verifier = DualSourceLocationVerifier()
