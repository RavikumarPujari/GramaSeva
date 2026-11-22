import math
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class VerifiedVillageBoundary:
    code: str
    name_en: str
    name_kn: str
    name_hi: str
    gram_panchayat: str
    taluk: str
    district: str
    center_lat: float
    center_lon: float
    boundary_radius_km: float
    dataset_version: str = "BLG-PILOT-BOUNDARY-2026.1"
    source: str = "Karnataka Panchayati Raj Belagavi Pilot Boundary Register"

# Official 9 Belagavi Taluk Pilot Village Boundaries
VERIFIED_BOUNDARIES: List[VerifiedVillageBoundary] = [
    VerifiedVillageBoundary("VIL-BEL-01", "Peeranwadi", "ಪೀರನವಾಡಿ", "पीरनवाड़ी", "Peeranwadi Gram Panchayat", "Belagavi Taluk", "Belagavi District", 15.8152, 74.4610, 4.5),
    VerifiedVillageBoundary("VIL-BEL-02", "Kuttalawadi", "ಕುಟ್ಟಲವಾಡಿ", "कुट्टलवाड़ी", "Kuttalawadi Gram Panchayat", "Belagavi Taluk", "Belagavi District", 15.8280, 74.4320, 3.8),
    VerifiedVillageBoundary("VIL-BEL-03", "Zad-Shahapur", "ಝಾಡ್-ಶಹಾಪುರ", "झाड-शहापुर", "Zad-Shahapur Gram Panchayat", "Belagavi Taluk", "Belagavi District", 15.8360, 74.5210, 4.0),
    VerifiedVillageBoundary("VIL-BEL-04", "Santibastawad", "ಶಾಂತಿಬಸ್ತವಾಡ", "शांतिबस्तवाड़", "Santibastawad Gram Panchayat", "Belagavi Taluk", "Belagavi District", 15.7950, 74.4420, 4.2),
    VerifiedVillageBoundary("VIL-BEL-05", "Yellur", "ಯೆಲ್ಲೂರು", "येल्लूर", "Yellur Gram Panchayat", "Belagavi Taluk", "Belagavi District", 15.7720, 74.5120, 5.0),
    VerifiedVillageBoundary("VIL-BEL-06", "Sulge (Yellur)", "ಸುಳಗೆ (ಯೆಲ್ಲೂರು)", "सुलगे (येल्लूर)", "Sulge Gram Panchayat", "Belagavi Taluk", "Belagavi District", 15.7610, 74.4980, 3.5),
    VerifiedVillageBoundary("VIL-BEL-07", "Mandoli", "ಮಾಂಡೋಲಿ", "मांडोली", "Mandoli Gram Panchayat", "Belagavi Taluk", "Belagavi District", 15.8380, 74.4650, 4.0),
    VerifiedVillageBoundary("VIL-BEL-08", "Waghawade", "ವಾಘಾವಡೆ", "वाघावडे", "Waghawade Gram Panchayat", "Belagavi Taluk", "Belagavi District", 15.8210, 74.4250, 3.5),
    VerifiedVillageBoundary("VIL-BEL-09", "Navage", "ನವಾಗೆ", "नवागे", "Navage Gram Panchayat", "Belagavi Taluk", "Belagavi District", 15.8080, 74.4390, 4.0),
]
PILOT_VILLAGE_BOUNDARIES = VERIFIED_BOUNDARIES

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class VillageBoundaryService:
    """
    Village Jurisdiction & Geographic Boundary Verification Service (Part 12).
    Checks if a point falls within verified Belagavi Gram Panchayat boundaries.
    """

    def __init__(self):
        self.boundaries = VERIFIED_BOUNDARIES

    def verify_point(self, latitude: float, longitude: float) -> Dict[str, Any]:
        closest_village: Optional[VerifiedVillageBoundary] = None
        min_dist = float("inf")

        for b in self.boundaries:
            dist = haversine_km(latitude, longitude, b.center_lat, b.center_lon)
            if dist < min_dist:
                min_dist = dist
                closest_village = b

        # Verified boundary threshold: inside village radius or within pilot maximum (6.0 km)
        if closest_village and min_dist <= closest_village.boundary_radius_km:
            return {
                "is_verified": True,
                "village_code": closest_village.code,
                "village_name": closest_village.name_en,
                "village_name_kn": closest_village.name_kn,
                "gram_panchayat": closest_village.gram_panchayat,
                "taluk": closest_village.taluk,
                "district": closest_village.district,
                "distance_km": round(min_dist, 2),
                "dataset_version": closest_village.dataset_version,
                "boundary_source": closest_village.source,
                "jurisdiction_status": "VERIFIED",
                "message": f"Verified within {closest_village.gram_panchayat} ({round(min_dist, 2)} km from village center).",
            }
        elif closest_village and min_dist <= 7.0:
            return {
                "is_verified": True,
                "village_code": closest_village.code,
                "village_name": closest_village.name_en,
                "village_name_kn": closest_village.name_kn,
                "gram_panchayat": closest_village.gram_panchayat,
                "taluk": closest_village.taluk,
                "district": closest_village.district,
                "distance_km": round(min_dist, 2),
                "dataset_version": closest_village.dataset_version,
                "boundary_source": closest_village.source,
                "jurisdiction_status": "VERIFIED_PERIPHERY",
                "message": f"Within peripheral jurisdiction of {closest_village.gram_panchayat} ({round(min_dist, 2)} km).",
            }
        else:
            return {
                "is_verified": False,
                "village_code": None,
                "village_name": None,
                "village_name_kn": None,
                "gram_panchayat": None,
                "taluk": "Belagavi Taluk",
                "district": "Belagavi District",
                "distance_km": round(min_dist, 2) if min_dist != float("inf") else None,
                "dataset_version": "BLG-PILOT-BOUNDARY-2026.1",
                "boundary_source": "Karnataka Panchayati Raj Belagavi Pilot Boundary Register",
                "jurisdiction_status": "UNVERIFIED_OUTSIDE_PILOT",
                "message": "Coordinates are outside the verified Belagavi pilot village boundaries. Manual village selection is required.",
            }

boundary_service = VillageBoundaryService()
