import time
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class GeocodedAddress:
    country: str
    state: str
    district: str
    taluk: str
    village_locality: Optional[str]
    road: Optional[str]
    street: Optional[str]
    postal_code: Optional[str]
    formatted_address: str
    provider: str
    is_estimated: bool = True
    response_reference: Optional[str] = None

class ReverseGeocoderService:
    """
    Reusable, rate-limited, and cached reverse-geocoding service (Part 10).
    Note: Reverse-geocoded addresses are estimates and not legally verified Gram Panchayat boundaries.
    """
    _cache: Dict[str, Tuple[float, GeocodedAddress]] = {}
    _cache_ttl_seconds = 3600  # 1 hour
    _last_request_time: float = 0.0

    def __init__(self, user_agent: Optional[str] = None):
        self.user_agent = user_agent or settings.nominatim_user_agent or "GramaSeva-Belagavi-Pilot/1.0"
        self.timeout_seconds = 3.0

    def _get_cache_key(self, lat: float, lon: float) -> str:
        # Cache key rounded to 4 decimals (~11m spatial bucket)
        return f"{round(lat, 4)}:{round(lon, 4)}"

    def reverse_geocode(self, latitude: float, longitude: float) -> GeocodedAddress:
        cache_key = self._get_cache_key(latitude, longitude)
        now = time.time()

        # Check cache
        if cache_key in self._cache:
            cached_time, cached_result = self._cache[cache_key]
            if now - cached_time < self._cache_ttl_seconds:
                return cached_result

        # Check Google Maps Geocoding API if key is present
        g_key = getattr(settings, "google_maps_api_key", None)
        if g_key and len(g_key.strip()) > 10 and not any(p in g_key.lower() for p in ["your_", "placeholder"]):
            try:
                g_url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={latitude},{longitude}&key={g_key}&language=en"
                g_req = urllib.request.Request(g_url)
                with urllib.request.urlopen(g_req, timeout=self.timeout_seconds) as g_resp:
                    if g_resp.status == 200:
                        g_data = json.loads(g_resp.read().decode("utf-8"))
                        if g_data.get("status") == "OK" and g_data.get("results"):
                            top_res = g_data["results"][0]
                            comps = top_res.get("address_components", [])
                            v_name = None
                            taluk_name = "Belagavi Taluk"
                            district_name = "Belagavi District"
                            road_name = None
                            street_name = None
                            postcode = None
                            for c in comps:
                                types = c.get("types", [])
                                if any(t in types for t in ["sublocality", "locality", "neighborhood"]):
                                    if not v_name:
                                        v_name = c.get("long_name")
                                if "administrative_area_level_3" in types or "administrative_area_level_2" in types:
                                    if "taluk" in c.get("long_name", "").lower():
                                        taluk_name = c.get("long_name")
                                    elif "district" in c.get("long_name", "").lower():
                                        district_name = c.get("long_name")
                                if "route" in types:
                                    road_name = c.get("long_name")
                                if "street_number" in types:
                                    street_name = c.get("long_name")
                                if "postal_code" in types:
                                    postcode = c.get("long_name")

                            addr_obj = GeocodedAddress(
                                country="India",
                                state="Karnataka",
                                district=district_name,
                                taluk=taluk_name,
                                village_locality=v_name,
                                road=road_name,
                                street=street_name,
                                postal_code=postcode,
                                formatted_address=top_res.get("formatted_address", ""),
                                provider="google_maps",
                                is_estimated=True,
                                response_reference=top_res.get("place_id"),
                            )
                            self._cache[cache_key] = (now, addr_obj)
                            return addr_obj
            except Exception as e:
                logger.warning(f"Google Maps reverse geocoding fallback: {e}")

        # Rate limiting: wait if less than 1.0s since last external call (Nominatim policy)
        elapsed = now - self._last_request_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)

        url = (
            f"https://nominatim.openstreetmap.org/reverse"
            f"?lat={latitude}&lon={longitude}&format=jsonv2&addressdetails=1"
        )
        headers = {
            "User-Agent": self.user_agent,
            "Accept-Language": "en,kn",
        }

        try:
            req = urllib.request.Request(url, headers=headers)
            ReverseGeocoderService._last_request_time = time.time()
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    addr = data.get("address", {})

                    village_name = (
                        addr.get("village")
                        or addr.get("suburb")
                        or addr.get("hamlet")
                        or addr.get("neighbourhood")
                        or addr.get("residential")
                        or addr.get("town")
                    )

                    taluk_name = (
                        addr.get("county")
                        or addr.get("taluk")
                        or addr.get("tehsil")
                        or "Belagavi Taluk"
                    )

                    district_name = (
                        addr.get("state_district")
                        or addr.get("district")
                        or "Belagavi District"
                    )

                    road_name = addr.get("road")
                    street_name = addr.get("pedestrian") or addr.get("path")
                    postcode = addr.get("postcode")
                    display_name = data.get("display_name", f"{latitude:.5f}, {longitude:.5f}")

                    geocoded = GeocodedAddress(
                        country=addr.get("country", "India"),
                        state=addr.get("state", "Karnataka"),
                        district=district_name,
                        taluk=taluk_name,
                        village_locality=village_name,
                        road=road_name,
                        street=street_name,
                        postal_code=postcode,
                        formatted_address=display_name,
                        provider="OpenStreetMap Nominatim",
                        is_estimated=True,
                        response_reference=str(data.get("osm_id", "osm_ref")),
                    )

                    self._cache[cache_key] = (now, geocoded)
                    return geocoded

        except Exception as e:
            logger.warning("External reverse-geocoding failed or timed out: %s. Using local fallback.", e)

        # Fallback for offline / timeout / rate-limit:
        fallback = GeocodedAddress(
            country="India",
            state="Karnataka",
            district="Belagavi District",
            taluk="Belagavi Taluk",
            village_locality=None,
            road=None,
            street=None,
            postal_code=None,
            formatted_address=f"Location at coordinates {latitude:.5f}°N, {longitude:.5f}°E",
            provider="GramaSeva Offline Geocoder",
            is_estimated=True,
            response_reference="local_fallback",
        )
        self._cache[cache_key] = (now, fallback)
        return fallback

reverse_geocoder = ReverseGeocoderService()
