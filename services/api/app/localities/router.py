from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import math
import base64
import io
import json
import urllib.request
import urllib.error
from PIL import Image
from app.core.config import settings
from app.core.database import get_db
from app.models.localities import LocalityUnit, Department, Organization
from app.auth.dependencies import require_roles
from app.services.location.dual_source_verifier import DualSourceLocationVerifier
from app.services.location.landmark_service import landmark_service, BELAGAVI_LANDMARK_REGISTER
from app.services.location.boundary_service import boundary_service, PILOT_VILLAGE_BOUNDARIES
from app.services.geocoding.reverse_geocoder import reverse_geocoder

router = APIRouter(prefix="/localities", tags=["Localities & Village Wards"])

class LocalityUnitResponse(BaseModel):
    id: str
    organization_id: str
    unit_type: str
    parent_id: Optional[str] = None
    official_code: Optional[str] = None
    name_en: str
    name_kn: str
    name_hi: str
    is_active: bool

class CreateLocalityRequest(BaseModel):
    organization_id: str
    unit_type: str  # gram_panchayat, village, ward, etc.
    parent_id: Optional[str] = None
    official_code: Optional[str] = None
    name_en: str
    name_kn: str
    name_hi: str
    boundary_geojson: Optional[str] = None

class DepartmentResponse(BaseModel):
    id: str
    code: str
    name_en: str
    name_kn: str
    name_hi: str
    is_active: bool

class ResolveGPSResponse(BaseModel):
    is_verified: bool
    village_name: Optional[str] = None
    village_name_kn: Optional[str] = None
    gram_panchayat: Optional[str] = None
    taluk: str = "Belagavi Taluk"
    district: str = "Belagavi District"
    state: str = "Karnataka"
    distance_km: Optional[float] = None
    locality_unit_id: Optional[str] = None
    message: str
    allow_manual_selection: bool = True

class ResolveGPSRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)

VERIFIED_BELAGAVI_VILLAGES = [
    {"name_en": "Peeranwadi", "name_kn": "ಪೀರನವಾಡಿ", "lat": 15.8152, "lon": 74.4610, "gp": "Peeranwadi Gram Panchayat", "code": "VIL-BEL-01"},
    {"name_en": "Kuttalawadi", "name_kn": "ಕುಟ್ಟಲವಾಡಿ", "lat": 15.8280, "lon": 74.4320, "gp": "Kuttalawadi Gram Panchayat", "code": "VIL-BEL-02"},
    {"name_en": "Zad-Shahapur", "name_kn": "ಝಾಡ್-ಶಹಾಪುರ", "lat": 15.8360, "lon": 74.5210, "gp": "Zad-Shahapur Gram Panchayat", "code": "VIL-BEL-03"},
    {"name_en": "Santibastawad", "name_kn": "ಶಾಂತಿಬಸ್ತವಾಡ", "lat": 15.7950, "lon": 74.4420, "gp": "Santibastawad Gram Panchayat", "code": "VIL-BEL-04"},
    {"name_en": "Yellur", "name_kn": "ಯೆಲ್ಲೂರು", "lat": 15.7720, "lon": 74.5120, "gp": "Yellur Gram Panchayat", "code": "VIL-BEL-05"},
    {"name_en": "Sulge (Yellur)", "name_kn": "ಸುಳಗೆ (ಯೆಲ್ಲೂರು)", "lat": 15.7610, "lon": 74.4980, "gp": "Sulge Gram Panchayat", "code": "VIL-BEL-06"},
    {"name_en": "Mandoli", "name_kn": "ಮಾಂಡೋಲಿ", "lat": 15.8380, "lon": 74.4650, "gp": "Mandoli Gram Panchayat", "code": "VIL-BEL-07"},
    {"name_en": "Waghawade", "name_kn": "ವಾಘಾವಡೆ", "lat": 15.8210, "lon": 74.4250, "gp": "Waghawade Gram Panchayat", "code": "VIL-BEL-08"},
    {"name_en": "Navage", "name_kn": "ನವಾಗೆ", "lat": 15.8080, "lon": 74.4390, "gp": "Navage Gram Panchayat", "code": "VIL-BEL-09"},
]

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@router.get("/resolve-gps", response_model=ResolveGPSResponse)
def resolve_gps_get(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
    db: Session = Depends(get_db),
):
    """
    Reverse-geocodes GPS coordinates against verified Belagavi Taluk pilot villages.
    Identifies jurisdiction without fabricating boundaries.
    """
    return _resolve_coordinates(latitude, longitude, db)

@router.post("/resolve-gps", response_model=ResolveGPSResponse)
def resolve_gps_post(
    req: ResolveGPSRequest,
    db: Session = Depends(get_db),
):
    """
    POST reverse-geocoding for GPS coordinates against verified Belagavi Taluk pilot villages.
    """
    return _resolve_coordinates(req.latitude, req.longitude, db)

def _resolve_coordinates(latitude: float, longitude: float, db: Session) -> ResolveGPSResponse:
    closest_village = None
    min_dist = float("inf")

    for v in VERIFIED_BELAGAVI_VILLAGES:
        dist = haversine_km(latitude, longitude, v["lat"], v["lon"])
        if dist < min_dist:
            min_dist = dist
            closest_village = v

    # Maximum pilot boundary threshold: 7.0 km
    if closest_village and min_dist <= 7.0:
        loc = db.query(LocalityUnit).filter(
            LocalityUnit.name_en.ilike(f"%{closest_village['name_en']}%")
        ).first()

        return ResolveGPSResponse(
            is_verified=True,
            village_name=closest_village["name_en"],
            village_name_kn=closest_village["name_kn"],
            gram_panchayat=closest_village["gp"],
            taluk="Belagavi Taluk",
            district="Belagavi District",
            state="Karnataka",
            distance_km=round(min_dist, 2),
            locality_unit_id=loc.id if loc else None,
            message=f"Verified within {closest_village['gp']} ({round(min_dist, 2)} km from village center).",
            allow_manual_selection=True,
        )

    return ResolveGPSResponse(
        is_verified=False,
        village_name=None,
        village_name_kn=None,
        gram_panchayat=None,
        taluk="Belagavi Taluk",
        district="Belagavi District",
        state="Karnataka",
        distance_km=round(min_dist, 2) if min_dist != float("inf") else None,
        locality_unit_id=None,
        message="Coordinates fall outside verified Belagavi pilot villages. Manual village selection is required.",
        allow_manual_selection=True,
    )

@router.get("", response_model=List[LocalityUnitResponse])
def list_localities(
    unit_type: Optional[str] = None,
    parent_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(LocalityUnit).filter(LocalityUnit.is_active == True)
    if unit_type:
        query = query.filter(LocalityUnit.unit_type == unit_type)
    if parent_id:
        query = query.filter(LocalityUnit.parent_id == parent_id)
    return query.all()

@router.get("/{id}/children", response_model=List[LocalityUnitResponse])
def get_locality_children(id: str, db: Session = Depends(get_db)):
    parent = db.query(LocalityUnit).filter(LocalityUnit.id == id).first()
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Locality unit not found",
        )
    return db.query(LocalityUnit).filter(LocalityUnit.parent_id == id, LocalityUnit.is_active == True).all()

@router.post("", response_model=LocalityUnitResponse, status_code=status.HTTP_201_CREATED)
def create_locality(
    req: CreateLocalityRequest,
    current_admin=Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Admin-only endpoint to configure new villages, wards, or administrative units."""
    unit = LocalityUnit(
        organization_id=req.organization_id,
        unit_type=req.unit_type,
        parent_id=req.parent_id,
        official_code=req.official_code,
        name_en=req.name_en,
        name_kn=req.name_kn,
        name_hi=req.name_hi,
        boundary_geojson=req.boundary_geojson,
        is_active=True,
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit

@router.get("/departments/list", response_model=List[DepartmentResponse])
def list_departments(db: Session = Depends(get_db)):
    return db.query(Department).filter(Department.is_active == True).all()

class DualSourceVerifyRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    gps_accuracy: Optional[float] = None
    acquisition_method: Optional[str] = "GPS_VERIFIED"
    selected_village: Optional[str] = None
    image_base64: Optional[str] = None

@router.post("/verify-dual-source")
def verify_dual_source(req: DualSourceVerifyRequest):
    """
    Cross-references hardware GPS coordinates, reverse-geocoded addresses,
    official village boundaries, OCR-extracted signboards, and visual landmark matches.
    """
    img = None
    if req.image_base64:
        try:
            b64_clean = req.image_base64.split(",")[-1] if "," in req.image_base64 else req.image_base64
            img_bytes = base64.b64decode(b64_clean)
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        except Exception as e:
            pass
    report = DualSourceLocationVerifier.verify(
        latitude=req.latitude,
        longitude=req.longitude,
        gps_accuracy=req.gps_accuracy,
        acquisition_method=req.acquisition_method or "GPS_VERIFIED",
        img=img,
        selected_village=req.selected_village,
    )
    return report.__dict__

@router.get("/landmarks")
def list_landmarks():
    """Returns official registry of verified Belagavi landmarks with verified coordinates."""
    return BELAGAVI_LANDMARK_REGISTER

@router.get("/boundaries")
def list_boundaries():
    """Returns official verified Belagavi Taluk pilot village boundary anchors."""
    return PILOT_VILLAGE_BOUNDARIES

@router.get("/reverse-geocode")
def reverse_geocode_endpoint(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
):
    """Returns rate-limited, cached reverse-geocoded address with estimate disclaimer."""
    addr = reverse_geocoder.reverse_geocode(latitude, longitude)
    return addr.__dict__

class GoogleGeocodeResponse(BaseModel):
    formatted_address: str
    village: str
    taluk: str
    district: str
    state: str
    country: str = "India"
    postal_code: Optional[str] = None
    place_id: Optional[str] = None
    geocoding_status: str = "OK"
    provider: str = "google_maps"
    raw_components: List[Dict[str, Any]] = []

@router.get("/google-geocode", response_model=GoogleGeocodeResponse)
def google_geocode_endpoint(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
):
    """
    Performs live reverse-geocoding using Google Geocoding API.
    Strictly follows Karnataka / India specific rules:
    - Extracts village only if a true locality/sublocality is present; otherwise 'Village not available from Google Maps response'.
    - Extracts taluk only if administrative_area_level_3/4 or taluk keyword is present; otherwise 'Taluk not available from Google Maps response'.
    - Does not invent or fabricate village or taluk from unrelated components.
    """
    g_key = getattr(settings, "google_maps_api_key", None) or getattr(settings, "google_maps_public_key", None)
    
    if g_key and len(g_key.strip()) > 10 and not any(p in g_key.lower() for p in ["your_", "placeholder"]):
        try:
            url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={latitude},{longitude}&key={g_key}&language=en"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("status") == "OK" and data.get("results"):
                        top_res = data["results"][0]
                        comps = top_res.get("address_components", [])
                        
                        v_name = None
                        t_name = None
                        d_name = None
                        s_name = None
                        c_name = "India"
                        p_code = None

                        for c in comps:
                            types = c.get("types", [])
                            # Village / Locality
                            if any(t in types for t in ["sublocality_level_1", "sublocality_level_2", "sublocality", "neighborhood"]):
                                if not v_name:
                                    v_name = c.get("long_name")
                            elif "locality" in types and not v_name:
                                v_name = c.get("long_name")

                            # Taluk / Subdistrict
                            if any(t in types for t in ["administrative_area_level_3", "administrative_area_level_4"]):
                                if not t_name:
                                    t_name = c.get("long_name")
                            elif any(w in c.get("long_name", "").lower() for w in ["taluk", "taluka", "tehsil"]):
                                if not t_name:
                                    t_name = c.get("long_name")

                            # District
                            if "administrative_area_level_2" in types and not d_name:
                                d_name = c.get("long_name")

                            # State
                            if "administrative_area_level_1" in types and not s_name:
                                s_name = c.get("long_name")

                            # Country
                            if "country" in types:
                                c_name = c.get("long_name", "India")

                            # Postal Code
                            if "postal_code" in types and not p_code:
                                p_code = c.get("long_name")

                        return GoogleGeocodeResponse(
                            formatted_address=top_res.get("formatted_address", f"{latitude:.6f}, {longitude:.6f}"),
                            village=v_name if v_name else "Village not identified — please confirm manually.",
                            taluk=t_name if t_name else "Taluk not identified — please confirm manually.",
                            district=d_name if d_name else "District not available from Google Maps response",
                            state=s_name if s_name else "State not available from Google Maps response",
                            country=c_name,
                            postal_code=p_code,
                            place_id=top_res.get("place_id"),
                            geocoding_status="OK",
                            provider="google_maps",
                            raw_components=comps,
                        )
        except Exception as e:
            pass

    # Fallback to backend reverse-geocoder (Nominatim / local boundary cache)
    addr = reverse_geocoder.reverse_geocode(latitude, longitude)
    v_cand = addr.village_locality
    t_cand = addr.taluk
    d_cand = addr.district
    s_cand = addr.state

    return GoogleGeocodeResponse(
        formatted_address=addr.formatted_address or f"{latitude:.6f}, {longitude:.6f}",
        village=v_cand if v_cand else "Village not identified — please confirm manually.",
        taluk=t_cand if t_cand and "belagavi" in t_cand.lower() else (t_cand or "Taluk not identified — please confirm manually."),
        district=d_cand if d_cand else "District not available from Google Maps response",
        state=s_cand if s_cand else "State not available from Google Maps response",
        country=addr.country or "India",
        postal_code=addr.postal_code,
        place_id=addr.response_reference,
        geocoding_status="FALLBACK_ESTIMATE",
        provider=addr.provider or "fallback_geocoder",
        raw_components=[],
    )
