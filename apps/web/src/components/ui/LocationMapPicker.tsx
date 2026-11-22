"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  MapPin,
  Navigation,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  RotateCcw,
  Check,
  Loader2,
  ShieldCheck,
  Globe,
  Layers,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { apiClient } from "@/lib/api-client";

export type GpsButtonState =
  | "ready"
  | "loading"
  | "success"
  | "permission_denied"
  | "timeout"
  | "unavailable"
  | "poor_accuracy";

export type FieldSource =
  | "Google detected"
  | "Verified official data"
  | "Citizen confirmed"
  | "Not available";

export interface AddressProvenance {
  village: FieldSource;
  taluk: FieldSource;
  gramPanchayat: FieldSource;
  district: FieldSource;
  state: FieldSource;
  country: FieldSource;
  postalCode: FieldSource;
  coordinates: FieldSource;
}

export interface RealGeocodedAddress {
  formattedAddress: string;
  village: string;
  taluk: string;
  gramPanchayat?: string | null;
  district: string;
  state: string;
  country: string;
  postalCode?: string | null;
  placeId?: string | null;
  geocodingStatus?: string;
  provider: "google_maps" | "fallback_geocoder";
  provenance: AddressProvenance;
}

export interface LocationPickerChangeData {
  // Real coordinates
  lat: number;
  lon: number;
  accuracy: number | null;
  method: "GPS_VERIFIED" | "MANUAL";
  timestamp: string;

  // Separate Original GPS Coordinates
  originalGpsLat: number | null;
  originalGpsLon: number | null;
  originalAccuracy: number | null;

  // Real Google Geocoding Results
  address: RealGeocodedAddress;

  // Status
  isConfirmed: boolean;
  jurisdictionStatus?: string;
  jurisdictionMessage?: string;
}

interface LocationMapPickerProps {
  latitude: number | null;
  longitude: number | null;
  accuracyMeters: number | null;
  locationMethod: "GPS_VERIFIED" | "MANUAL";
  isConfirmed: boolean;
  onLocationChange: (data: LocationPickerChangeData) => void;
  onConfirmLocation?: (confirmed: boolean) => void;
  className?: string;
}

// 9 Genuine, Verified Belagavi Taluk Pilot Villages
export const VERIFIED_BELAGAVI_VILLAGES = [
  { name_en: "Peeranwadi", gp: "Peeranwadi Gram Panchayat", lat: 15.8152, lon: 74.4610, code: "VIL-BEL-01" },
  { name_en: "Kuttalawadi", gp: "Kuttalawadi Gram Panchayat", lat: 15.8280, lon: 74.4320, code: "VIL-BEL-02" },
  { name_en: "Zad-Shahapur", gp: "Zad-Shahapur Gram Panchayat", lat: 15.8360, lon: 74.5210, code: "VIL-BEL-03" },
  { name_en: "Santibastawad", gp: "Santibastawad Gram Panchayat", lat: 15.7950, lon: 74.4420, code: "VIL-BEL-04" },
  { name_en: "Yellur", gp: "Yellur Gram Panchayat", lat: 15.7720, lon: 74.5120, code: "VIL-BEL-05" },
  { name_en: "Sulge (Yellur)", gp: "Sulge Gram Panchayat", lat: 15.7610, lon: 74.4980, code: "VIL-BEL-06" },
  { name_en: "Mandoli", gp: "Mandoli Gram Panchayat", lat: 15.8380, lon: 74.4650, code: "VIL-BEL-07" },
  { name_en: "Waghawade", gp: "Waghawade Gram Panchayat", lat: 15.8210, lon: 74.4250, code: "VIL-BEL-08" },
  { name_en: "Navage", gp: "Navage Gram Panchayat", lat: 15.8080, lon: 74.4390, code: "VIL-BEL-09" },
];

function haversineMeters(lat1: float_or_num, lon1: float_or_num, lat2: float_or_num, lon2: float_or_num): number {
  const R = 6371000;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

type float_or_num = number;

function ProvenanceBadge({ source }: { source: FieldSource }) {
  if (source === "Verified official data") {
    return (
      <span className="text-[9px] px-1.5 py-0.5 rounded-full font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
        Verified official data
      </span>
    );
  }
  if (source === "Google detected") {
    return (
      <span className="text-[9px] px-1.5 py-0.5 rounded-full font-bold bg-sky-100 text-sky-800 border border-sky-300">
        Google detected
      </span>
    );
  }
  if (source === "Citizen confirmed") {
    return (
      <span className="text-[9px] px-1.5 py-0.5 rounded-full font-bold bg-teal-100 text-teal-800 border border-teal-300">
        Citizen confirmed
      </span>
    );
  }
  return (
    <span className="text-[9px] px-1.5 py-0.5 rounded-full font-bold bg-slate-100 text-slate-500 border border-slate-200">
      Not available
    </span>
  );
}

// Convert lat/lon to OpenStreetMap tile numbers for fallback
function latLonToTile(lat: number, lon: number, zoom: number) {
  const n = Math.pow(2, zoom);
  const x = Math.floor(((lon + 180) / 360) * n);
  const latRad = (lat * Math.PI) / 180;
  const y = Math.floor(
    ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n
  );
  return { x, y };
}

export function LocationMapPicker({
  latitude,
  longitude,
  accuracyMeters,
  locationMethod,
  isConfirmed,
  onLocationChange,
  onConfirmLocation,
  className = "",
}: LocationMapPickerProps) {
  const googleMapsApiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "";
  const hasGoogleKey = Boolean(
    googleMapsApiKey &&
      googleMapsApiKey.length > 10 &&
      !googleMapsApiKey.includes("your_") &&
      !googleMapsApiKey.includes("placeholder")
  );

  // Default initial coordinates (Belagavi region center) before detection
  const defaultLat = 15.8497;
  const defaultLon = 74.5078;

  const currentLat = latitude ?? defaultLat;
  const currentLon = longitude ?? defaultLon;
  const hasLocation = latitude !== null && longitude !== null;

  const [zoom, setZoom] = useState(16);
  const [gpsState, setGpsState] = useState<GpsButtonState>(
    hasLocation ? (accuracyMeters && accuracyMeters > 50 ? "poor_accuracy" : "success") : "ready"
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isGeocoding, setIsGeocoding] = useState(false);

  // Original GPS coordinates preserved separately
  const [originalGpsLat, setOriginalGpsLat] = useState<number | null>(latitude);
  const [originalGpsLon, setOriginalGpsLon] = useState<number | null>(longitude);
  const [originalAccuracy, setOriginalAccuracy] = useState<number | null>(accuracyMeters);
  const [gpsTimestamp, setGpsTimestamp] = useState<string>(new Date().toISOString());

  // Real Geocoded Address Data with Provenance
  const [addressData, setAddressData] = useState<RealGeocodedAddress>({
    formattedAddress: hasLocation ? `${currentLat.toFixed(6)}, ${currentLon.toFixed(6)}` : "Location not yet detected",
    village: "Village not identified — please confirm manually.",
    taluk: "Taluk not identified — please confirm manually.",
    gramPanchayat: "Gram Panchayat not verified — please confirm manually.",
    district: "Not available — please confirm",
    state: "Karnataka",
    country: "India",
    provider: hasGoogleKey ? "google_maps" : "fallback_geocoder",
    provenance: {
      village: "Not available",
      taluk: "Not available",
      gramPanchayat: "Not available",
      district: "Not available",
      state: "Verified official data",
      country: "Google detected",
      postalCode: "Not available",
      coordinates: hasLocation ? (locationMethod === "GPS_VERIFIED" ? "Google detected" : "Citizen confirmed") : "Not available",
    },
  });

  const [isEditingLocality, setIsEditingLocality] = useState(false);
  const [customVillage, setCustomVillage] = useState("");
  const [customTaluk, setCustomTaluk] = useState("");
  const [customGramPanchayat, setCustomGramPanchayat] = useState("");

  // Map Provider Mode: "google" or "osm" (fallback)
  const [mapProvider, setMapProvider] = useState<"google" | "osm">(hasGoogleKey ? "google" : "osm");
  const [googleMapType, setGoogleMapType] = useState<"roadmap" | "satellite">("roadmap");
  const [isGoogleLoaded, setIsGoogleLoaded] = useState(false);

  const googleMapRef = useRef<HTMLDivElement>(null);
  const osmMapContainerRef = useRef<HTMLDivElement>(null);
  const googleMapObj = useRef<any>(null);
  const googleMarkerObj = useRef<any>(null);
  const googleCircleObj = useRef<any>(null);

  // Reverse geocode coordinates using Google Geocoding (Frontend JS API or Backend API)
  const performReverseGeocode = useCallback(
    async (lat: number, lon: number): Promise<RealGeocodedAddress> => {
      setIsGeocoding(true);

      // Check if coordinates match verified Belagavi pilot villages
      const matchedVillage = VERIFIED_BELAGAVI_VILLAGES.find((bv) => {
        const dist = haversineMeters(lat, lon, bv.lat, bv.lon);
        return dist <= 3500;
      });

      // 1. Try Google Maps JavaScript Geocoder in browser if available
      if (typeof window !== "undefined" && (window as any).google && (window as any).google.maps) {
        try {
          const geocoder = new (window as any).google.maps.Geocoder();
          const response = await new Promise<any>((resolve, reject) => {
            geocoder.geocode({ location: { lat, lng: lon } }, (results: any, status: any) => {
              if (status === "OK" && results && results.length > 0) {
                resolve(results);
              } else {
                reject(new Error(`Google Geocoder status: ${status}`));
              }
            });
          });

          if (response && response.length > 0) {
            const topRes = response[0];
            const comps: Array<{ long_name: string; short_name: string; types: string[] }> =
              topRes.address_components || [];

            let v_name: string | null = null;
            let t_name: string | null = null;
            let d_name: string | null = null;
            let s_name: string | null = null;
            let c_name = "India";
            let p_code: string | null = null;

            for (const c of comps) {
              const types = c.types || [];

              // Extract village / locality
              if (
                types.includes("sublocality_level_1") ||
                types.includes("sublocality_level_2") ||
                types.includes("sublocality") ||
                types.includes("neighborhood")
              ) {
                if (!v_name) v_name = c.long_name;
              } else if (types.includes("locality") && !v_name) {
                v_name = c.long_name;
              }

              // Extract taluk / subdistrict
              if (
                types.includes("administrative_area_level_3") ||
                types.includes("administrative_area_level_4")
              ) {
                if (!t_name) t_name = c.long_name;
              } else if (
                c.long_name.toLowerCase().includes("taluk") ||
                c.long_name.toLowerCase().includes("taluka") ||
                c.long_name.toLowerCase().includes("tehsil")
              ) {
                if (!t_name) t_name = c.long_name;
              }

              // District
              if (types.includes("administrative_area_level_2") && !d_name) {
                d_name = c.long_name;
              }

              // State
              if (types.includes("administrative_area_level_1") && !s_name) {
                s_name = c.long_name;
              }

              // Country
              if (types.includes("country")) {
                c_name = c.long_name || "India";
              }

              // Postal Code
              if (types.includes("postal_code") && !p_code) {
                p_code = c.long_name;
              }
            }

            // Determine field provenances
            const isVillageOfficial = Boolean(
              matchedVillage && (v_name?.toLowerCase().includes(matchedVillage.name_en.toLowerCase()) || !v_name)
            );

            const finalVillage = isVillageOfficial
              ? matchedVillage!.name_en
              : (v_name || "Village not identified — please confirm manually.");

            const villageSource: FieldSource = isVillageOfficial
              ? "Verified official data"
              : v_name
              ? "Google detected"
              : "Not available";

            const gpSource: FieldSource = isVillageOfficial ? "Verified official data" : "Not available";
            const finalGp = isVillageOfficial
              ? matchedVillage!.gp
              : "Gram Panchayat not verified — please confirm manually.";

            const talukSource: FieldSource = t_name ? "Google detected" : "Not available";
            const finalTaluk = t_name || "Taluk not identified — please confirm manually.";

            const districtSource: FieldSource = d_name ? "Google detected" : "Not available";
            const finalDistrict = d_name || "Not available — please confirm";

            const resultObj: RealGeocodedAddress = {
              formattedAddress: topRes.formatted_address || `${lat.toFixed(6)}, ${lon.toFixed(6)}`,
              village: finalVillage,
              taluk: finalTaluk,
              gramPanchayat: finalGp,
              district: finalDistrict,
              state: s_name || "Karnataka",
              country: c_name,
              postalCode: p_code || "Not available",
              placeId: topRes.place_id,
              geocodingStatus: "OK",
              provider: "google_maps",
              provenance: {
                village: villageSource,
                taluk: talukSource,
                gramPanchayat: gpSource,
                district: districtSource,
                state: s_name ? "Google detected" : "Verified official data",
                country: "Google detected",
                postalCode: p_code ? "Google detected" : "Not available",
                coordinates: "Google detected",
              },
            };
            setIsGeocoding(false);
            return resultObj;
          }
        } catch (clientErr) {
          console.warn("Client Google Geocoder notice, checking backend endpoint:", clientErr);
        }
      }

      // 2. Call backend Google Geocoding API endpoint
      try {
        const res = await apiClient.get<any>(
          `/localities/google-geocode?latitude=${lat}&longitude=${lon}`
        );
        if (res && res.formatted_address) {
          const isOfficial = Boolean(matchedVillage);
          const finalVillage = isOfficial
            ? matchedVillage!.name_en
            : res.village && !res.village.includes("not identified")
            ? res.village
            : "Village not identified — please confirm manually.";

          const villageSource: FieldSource = isOfficial
            ? "Verified official data"
            : res.village && !res.village.includes("not identified")
            ? "Google detected"
            : "Not available";

          const gpSource: FieldSource = isOfficial ? "Verified official data" : "Not available";
          const finalGp = isOfficial
            ? matchedVillage!.gp
            : "Gram Panchayat not verified — please confirm manually.";

          const talukSource: FieldSource =
            res.taluk && !res.taluk.includes("not identified") ? "Google detected" : "Not available";
          const finalTaluk =
            res.taluk && !res.taluk.includes("not identified")
              ? res.taluk
              : "Taluk not identified — please confirm manually.";

          const resultObj: RealGeocodedAddress = {
            formattedAddress: res.formatted_address,
            village: finalVillage,
            taluk: finalTaluk,
            gramPanchayat: finalGp,
            district: res.district || "Not available — please confirm",
            state: res.state || "Karnataka",
            country: res.country || "India",
            postalCode: res.postal_code || "Not available",
            placeId: res.place_id || null,
            geocodingStatus: res.geocoding_status || "OK",
            provider: res.provider || "google_maps",
            provenance: {
              village: villageSource,
              taluk: talukSource,
              gramPanchayat: gpSource,
              district: res.district ? "Google detected" : "Not available",
              state: res.state ? "Google detected" : "Verified official data",
              country: "Google detected",
              postalCode: res.postal_code ? "Google detected" : "Not available",
              coordinates: "Google detected",
            },
          };
          setIsGeocoding(false);
          return resultObj;
        }
      } catch (backendErr) {
        console.warn("Backend Google Geocode fallback notice:", backendErr);
      }

      setIsGeocoding(false);
      return {
        formattedAddress: `${lat.toFixed(6)}, ${lon.toFixed(6)}`,
        village: matchedVillage ? matchedVillage.name_en : "Village not identified — please confirm manually.",
        taluk: "Taluk not identified — please confirm manually.",
        gramPanchayat: matchedVillage ? matchedVillage.gp : "Gram Panchayat not verified — please confirm manually.",
        district: "Not available — please confirm",
        state: "Karnataka",
        country: "India",
        geocodingStatus: "UNAVAILABLE",
        provider: "fallback_geocoder",
        provenance: {
          village: matchedVillage ? "Verified official data" : "Not available",
          taluk: "Not available",
          gramPanchayat: matchedVillage ? "Verified official data" : "Not available",
          district: "Not available",
          state: "Verified official data",
          country: "Google detected",
          postalCode: "Not available",
          coordinates: "Citizen confirmed",
        },
      };
    },
    []
  );

  // Load Google Maps JavaScript API script
  useEffect(() => {
    if (!hasGoogleKey || typeof window === "undefined") {
      setMapProvider("osm");
      return;
    }

    if ((window as any).google && (window as any).google.maps) {
      setIsGoogleLoaded(true);
      return;
    }

    const scriptId = "google-maps-js-sdk";
    if (document.getElementById(scriptId)) {
      const interval = setInterval(() => {
        if ((window as any).google && (window as any).google.maps) {
          setIsGoogleLoaded(true);
          clearInterval(interval);
        }
      }, 100);
      return () => clearInterval(interval);
    }

    const script = document.createElement("script");
    script.id = scriptId;
    script.src = `https://maps.googleapis.com/maps/api/js?key=${googleMapsApiKey}&libraries=places,geometry`;
    script.async = true;
    script.defer = true;
    script.onload = () => {
      setIsGoogleLoaded(true);
    };
    script.onerror = () => {
      console.warn("Google Maps script load error, falling back to OpenStreetMap.");
      setMapProvider("osm");
    };
    document.head.appendChild(script);
  }, [hasGoogleKey, googleMapsApiKey]);

  // Mount and manage Google Map instance
  useEffect(() => {
    if (mapProvider !== "google" || !isGoogleLoaded || !googleMapRef.current || typeof window === "undefined") {
      return;
    }

    const google = (window as any).google;
    if (!google || !google.maps) return;

    try {
      if (!googleMapObj.current) {
        const map = new google.maps.Map(googleMapRef.current, {
          center: { lat: currentLat, lng: currentLon },
          zoom: zoom,
          mapTypeId: googleMapType,
          disableDefaultUI: false,
          zoomControl: true,
          streetViewControl: false,
          fullscreenControl: false,
          mapTypeControl: false,
        });
        googleMapObj.current = map;

        const marker = new google.maps.Marker({
          position: { lat: currentLat, lng: currentLon },
          map: map,
          draggable: true,
          title: "Drag marker to fine-tune complaint location",
          animation: google.maps.Animation.DROP,
        });
        googleMarkerObj.current = marker;

        // PART 5: Draggable Map Marker dragend listener
        marker.addListener("dragend", async (e: any) => {
          const newLat = Number(e.latLng.lat().toFixed(6));
          const newLon = Number(e.latLng.lng().toFixed(6));

          setIsGeocoding(true);
          try {
            const geocoded = await performReverseGeocode(newLat, newLon);
            setAddressData(geocoded);

            onLocationChange({
              lat: newLat,
              lon: newLon,
              accuracy: null,
              method: "MANUAL",
              timestamp: new Date().toISOString(),
              originalGpsLat: originalGpsLat,
              originalGpsLon: originalGpsLon,
              originalAccuracy: originalAccuracy,
              address: geocoded,
              isConfirmed: false,
              jurisdictionStatus: geocoded.provenance.village !== "Not available" ? "VERIFIED" : "UNVERIFIED",
            });
          } catch (err) {
            console.warn("Geocoding notice on drag:", err);
            // Preserve selected marker position even if geocoding fails
            marker.setPosition({ lat: newLat, lng: newLon });
          } finally {
            setIsGeocoding(false);
          }
        });

        // Map click listener to reposition marker
        map.addListener("click", async (e: any) => {
          const newLat = Number(e.latLng.lat().toFixed(6));
          const newLon = Number(e.latLng.lng().toFixed(6));
          marker.setPosition({ lat: newLat, lng: newLon });

          setIsGeocoding(true);
          try {
            const geocoded = await performReverseGeocode(newLat, newLon);
            setAddressData(geocoded);

            onLocationChange({
              lat: newLat,
              lon: newLon,
              accuracy: null,
              method: "MANUAL",
              timestamp: new Date().toISOString(),
              originalGpsLat: originalGpsLat,
              originalGpsLon: originalGpsLon,
              originalAccuracy: originalAccuracy,
              address: geocoded,
              isConfirmed: false,
              jurisdictionStatus: geocoded.provenance.village !== "Not available" ? "VERIFIED" : "UNVERIFIED",
            });
          } catch (err) {
            console.warn("Geocoding notice on click:", err);
          } finally {
            setIsGeocoding(false);
          }
        });
      } else {
        googleMapObj.current.panTo({ lat: currentLat, lng: currentLon });
        googleMapObj.current.setMapTypeId(googleMapType);
        if (googleMarkerObj.current) {
          googleMarkerObj.current.setPosition({ lat: currentLat, lng: currentLon });
        }
      }

      // Draw or update accuracy circle
      if (accuracyMeters && accuracyMeters > 0) {
        if (!googleCircleObj.current) {
          googleCircleObj.current = new google.maps.Circle({
            strokeColor: accuracyMeters > 50 ? "#d97706" : "#059669",
            strokeOpacity: 0.8,
            strokeWeight: 2,
            fillColor: accuracyMeters > 50 ? "#f59e0b" : "#10b981",
            fillOpacity: 0.15,
            map: googleMapObj.current,
            center: { lat: currentLat, lng: currentLon },
            radius: accuracyMeters,
          });
        } else {
          googleCircleObj.current.setCenter({ lat: currentLat, lng: currentLon });
          googleCircleObj.current.setRadius(accuracyMeters);
        }
      } else if (googleCircleObj.current) {
        googleCircleObj.current.setMap(null);
        googleCircleObj.current = null;
      }
    } catch (err) {
      console.warn("Google Maps init error, using OpenStreetMap fallback:", err);
      setMapProvider("osm");
    }
  }, [mapProvider, isGoogleLoaded, currentLat, currentLon, zoom, googleMapType, accuracyMeters, originalGpsLat, originalGpsLon, originalAccuracy, performReverseGeocode, onLocationChange]);

  // PRIMARY ACTION: "📍 Detect My Location" (Triggered strictly on citizen button click)
  const handleDetectLocation = () => {
    if (gpsState === "loading") return;

    if (typeof window === "undefined" || !navigator.geolocation) {
      setGpsState("unavailable");
      setErrorMessage("Geolocation is not supported by your browser or device.");
      return;
    }

    setGpsState("loading");
    setErrorMessage(null);

    // Exact required parameters: enableHighAccuracy: true, timeout: 20000, maximumAge: 0
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = Number(pos.coords.latitude.toFixed(6));
        const lon = Number(pos.coords.longitude.toFixed(6));
        const acc = Math.round(pos.coords.accuracy);
        const ts = new Date().toISOString();

        setOriginalGpsLat(lat);
        setOriginalGpsLon(lon);
        setOriginalAccuracy(acc);
        setGpsTimestamp(ts);

        // Check accuracy threshold
        if (acc > 50) {
          setGpsState("poor_accuracy");
          setErrorMessage(`GPS accuracy is low (±${acc}m). Please drag the map pin to adjust your exact spot.`);
        } else {
          setGpsState("success");
          setErrorMessage(null);
        }

        // Automatic reverse geocoding
        const geocoded = await performReverseGeocode(lat, lon);
        setAddressData(geocoded);

        // Pan Google Map and place marker
        if (googleMapObj.current) {
          googleMapObj.current.panTo({ lat, lng: lon });
          googleMapObj.current.setZoom(17);
          if (googleMarkerObj.current) {
            googleMarkerObj.current.setPosition({ lat, lng: lon });
          }
        }

        onLocationChange({
          lat,
          lon,
          accuracy: acc,
          method: "GPS_VERIFIED",
          timestamp: ts,
          originalGpsLat: lat,
          originalGpsLon: lon,
          originalAccuracy: acc,
          address: geocoded,
          isConfirmed: false,
          jurisdictionStatus: geocoded.provenance.village !== "Not available" ? "VERIFIED" : "UNVERIFIED",
        });
      },
      (error) => {
        let state: GpsButtonState = "unavailable";
        let message = "Your device could not provide a location.";

        switch (error.code) {
          case 1:
            state = "permission_denied";
            message = "Location permission denied. Please allow location access in your browser settings or drag the marker to your location.";
            break;
          case 2:
            state = "unavailable";
            message = "GPS is unavailable on your device. Please ensure location services are enabled or place a pin manually.";
            break;
          case 3:
            state = "timeout";
            message = "GPS request timed out after 20 seconds. Please try again or drag the map marker.";
            break;
          default:
            state = "unavailable";
            message = error.message || "Your device could not provide a location.";
        }

        setGpsState(state);
        setErrorMessage(message);
      },
      {
        enableHighAccuracy: true,
        timeout: 20000,
        maximumAge: 0,
      }
    );
  };

  // OSM Fallback map click
  const handleOsmClick = async (e: React.MouseEvent<HTMLDivElement>) => {
    if (!osmMapContainerRef.current) return;
    const rect = osmMapContainerRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const normX = clickX / rect.width - 0.5;
    const normY = clickY / rect.height - 0.5;

    const factor = 360 / Math.pow(2, zoom) / 2;
    const newLon = Number((currentLon + normX * factor).toFixed(6));
    const newLat = Number((currentLat - normY * (factor * 0.75)).toFixed(6));

    const geocoded = await performReverseGeocode(newLat, newLon);
    setAddressData(geocoded);

    onLocationChange({
      lat: newLat,
      lon: newLon,
      accuracy: null,
      method: "MANUAL",
      timestamp: new Date().toISOString(),
      originalGpsLat: originalGpsLat,
      originalGpsLon: originalGpsLon,
      originalAccuracy: originalAccuracy,
      address: geocoded,
      isConfirmed: false,
    });
  };

  // OpenStreetMap tile computation for fallback
  const centerTile = latLonToTile(currentLat, currentLon, zoom);
  const tiles: Array<{ x: number; y: number; key: string }> = [];
  for (let dx = -1; dx <= 1; dx++) {
    for (let dy = -1; dy <= 1; dy++) {
      tiles.push({
        x: centerTile.x + dx,
        y: centerTile.y + dy,
        key: `${zoom}/${centerTile.x + dx}/${centerTile.y + dy}`,
      });
    }
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* 1. TOP BAR: GPS DETECTION BUTTON & MAP STATUS */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-gradient-to-r from-teal-50 to-blue-50/60 p-4 rounded-2xl border border-teal-200/80">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <span className="font-bold text-[#062B46] text-sm flex items-center gap-1.5">
              <MapPin className="h-4 w-4 text-[#087F78]" />
              <span>Real Google Maps & GPS Location</span>
            </span>
            {hasGoogleKey ? (
              <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 text-[10px] font-semibold">
                Google Maps JS API Active
              </Badge>
            ) : (
              <Badge className="bg-amber-100 text-amber-800 border-amber-300 text-[10px] font-semibold">
                Fallback Map Provider
              </Badge>
            )}
          </div>
          <p className="text-xs text-slate-600">
            Click <strong>Detect My Location</strong> to fetch real GPS coordinates, or drag the marker directly to the civic defect.
          </p>
        </div>

        {/* PRIMARY GPS BUTTON: "📍 Detect My Location" */}
        <Button
          type="button"
          variant="primary"
          onClick={handleDetectLocation}
          disabled={gpsState === "loading"}
          className={`font-bold px-5 py-2.5 rounded-xl shadow-xs transition-all cursor-pointer flex items-center justify-center gap-2 shrink-0 ${
            gpsState === "success"
              ? "bg-emerald-600 hover:bg-emerald-700 text-white"
              : gpsState === "loading"
              ? "bg-teal-700 text-white opacity-85"
              : "bg-[#087F78] hover:bg-[#06635e] text-white"
          }`}
        >
          {gpsState === "loading" ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Acquiring GPS Signal...</span>
            </>
          ) : gpsState === "success" ? (
            <>
              <CheckCircle2 className="h-4 w-4 text-emerald-200" />
              <span>📍 Detect My Location</span>
            </>
          ) : (
            <>
              <Navigation className="h-4 w-4" />
              <span>📍 Detect My Location</span>
            </>
          )}
        </Button>
      </div>

      {/* GPS Status / Error Banners */}
      {errorMessage && (
        <div
          className={`rounded-2xl p-3.5 text-xs flex items-start gap-2.5 border shadow-2xs ${
            gpsState === "poor_accuracy"
              ? "bg-amber-50 border-amber-200 text-amber-900"
              : "bg-rose-50 border-rose-200 text-rose-900"
          }`}
        >
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-current" />
          <div className="flex-1">
            <span className="font-semibold block">{errorMessage}</span>
          </div>
        </div>
      )}

      {/* 2. MAP CANVAS: REAL GOOGLE MAPS OR INTERACTIVE FALLBACK */}
      <div className="rounded-2xl overflow-hidden border border-slate-200 shadow-sm relative bg-slate-100">
        {/* Map Header Bar */}
        <div className="bg-[#062B46] text-white px-4 py-2.5 text-xs font-semibold flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MapPin className="h-3.5 w-3.5 text-teal-400" />
            <span>Interactive Map — Drag marker or click anywhere to fine-tune</span>
          </div>

          <div className="flex items-center gap-2 font-mono text-[11px] text-teal-200">
            {isGeocoding ? (
              <span className="flex items-center gap-1 text-teal-300">
                <Loader2 className="h-3 w-3 animate-spin" />
                <span>Reverse Geocoding...</span>
              </span>
            ) : (
              <span>
                {currentLat.toFixed(6)}°N, {currentLon.toFixed(6)}°E
              </span>
            )}
          </div>
        </div>

        {/* Real Google Map Container */}
        {mapProvider === "google" && hasGoogleKey ? (
          <div
            ref={googleMapRef}
            className="w-full h-80 sm:h-96 relative bg-slate-200"
            style={{ minHeight: "320px" }}
          />
        ) : (
          /* OpenStreetMap Fallback Container */
          <div
            ref={osmMapContainerRef}
            onClick={handleOsmClick}
            className="w-full h-80 sm:h-96 relative cursor-crosshair overflow-hidden bg-[#e5eef4] select-none"
            style={{ minHeight: "320px" }}
          >
            <div className="absolute inset-0 grid grid-cols-3 grid-rows-3 opacity-95">
              {tiles.map((t) => (
                <img
                  key={t.key}
                  src={`https://tile.openstreetmap.org/${t.key}.png`}
                  alt="map tile"
                  className="w-full h-full object-cover pointer-events-none select-none"
                  loading="lazy"
                />
              ))}
            </div>

            {/* Pinned Center Marker */}
            <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-full pointer-events-none drop-shadow-lg flex flex-col items-center z-10">
              <div className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#062B46] text-white shadow-md mb-1 whitespace-nowrap flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                <span>Grievance Location</span>
              </div>
              <MapPin className="w-9 h-9 text-rose-600 fill-rose-500 animate-bounce" />
            </div>

            <div className="absolute bottom-2 left-2 bg-white/90 backdrop-blur-xs px-2.5 py-1 rounded-lg text-[11px] text-slate-700 border border-slate-200 shadow-xs pointer-events-none">
              Tip: Click anywhere to move the pin directly to the defect spot
            </div>
          </div>
        )}

        {/* Map Type / Layer Switcher (Roadmap vs Satellite) */}
        {mapProvider === "google" && (
          <div className="absolute top-12 right-3 z-10 flex rounded-xl overflow-hidden border border-slate-300 shadow-md bg-white text-xs font-bold">
            <button
              type="button"
              onClick={() => setGoogleMapType("roadmap")}
              className={`px-3 py-1.5 transition-all ${
                googleMapType === "roadmap"
                  ? "bg-[#087F78] text-white"
                  : "bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              Default
            </button>
            <button
              type="button"
              onClick={() => setGoogleMapType("satellite")}
              className={`px-3 py-1.5 transition-all ${
                googleMapType === "satellite"
                  ? "bg-[#087F78] text-white"
                  : "bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              Satellite
            </button>
          </div>
        )}
      </div>

      {/* 3. LOCATION INTELLIGENCE & ADMINISTRATIVE JURISDICTION BREAKDOWN */}
      {hasLocation && (
        <div className="rounded-2xl border border-teal-200/80 bg-teal-50/40 p-4 sm:p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-teal-200/60 pb-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-[#087F78]" />
              <h3 className="font-bold text-sm text-[#062B46]">
                Google Geocoded Address & Administrative Jurisdiction
              </h3>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-[11px] text-slate-500">Method:</span>
              <Badge className="bg-white text-[#087F78] border-teal-300 text-[10px] font-bold">
                {locationMethod}
              </Badge>
            </div>
          </div>

          {/* Full Formatted Address */}
          <div className="rounded-xl border border-teal-200/80 bg-white p-3 shadow-2xs">
            <div className="flex items-center justify-between mb-1">
              <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">
                Full Formatted Address
              </span>
              <ProvenanceBadge source={addressData.provenance.country} />
            </div>
            <p className="font-semibold text-slate-800 text-xs sm:text-sm">
              {addressData.formattedAddress}
            </p>
          </div>

          {/* Extracted Administrative Breakdown */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-700">
                Administrative Jurisdiction Components
              </span>
              <button
                type="button"
                onClick={() => {
                  setCustomVillage(
                    addressData.village.includes("not identified") || addressData.village.includes("Not available")
                      ? ""
                      : addressData.village
                  );
                  setCustomTaluk(
                    addressData.taluk.includes("not identified") || addressData.taluk.includes("Not available")
                      ? ""
                      : addressData.taluk
                  );
                  setCustomGramPanchayat(
                    addressData.gramPanchayat && !addressData.gramPanchayat.includes("not verified")
                      ? addressData.gramPanchayat
                      : ""
                  );
                  setIsEditingLocality(!isEditingLocality);
                }}
                className="text-[11px] text-[#087F78] hover:text-[#06635e] font-bold cursor-pointer underline"
              >
                {isEditingLocality ? "Cancel Edit" : "✏️ Correct Village / Taluk"}
              </button>
            </div>

            {/* Inline Locality Editor for Manual Adjustments */}
            {isEditingLocality && (
              <div className="rounded-xl border border-teal-300 bg-teal-50/70 p-3 space-y-2 text-xs">
                <p className="font-bold text-[#062B46] text-[11px]">
                  Correct or Specify Village, Taluk, and Gram Panchayat:
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 mb-0.5">Village Name</label>
                    <input
                      type="text"
                      value={customVillage}
                      onChange={(e) => setCustomVillage(e.target.value)}
                      placeholder="e.g. Peeranwadi"
                      className="w-full bg-white rounded-lg border border-slate-300 px-2.5 py-1.5 text-xs text-slate-800 font-medium"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 mb-0.5">Taluk Name</label>
                    <input
                      type="text"
                      value={customTaluk}
                      onChange={(e) => setCustomTaluk(e.target.value)}
                      placeholder="e.g. Belagavi Taluk"
                      className="w-full bg-white rounded-lg border border-slate-300 px-2.5 py-1.5 text-xs text-slate-800 font-medium"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 mb-0.5">Gram Panchayat</label>
                    <input
                      type="text"
                      value={customGramPanchayat}
                      onChange={(e) => setCustomGramPanchayat(e.target.value)}
                      placeholder="e.g. Peeranwadi Gram Panchayat"
                      className="w-full bg-white rounded-lg border border-slate-300 px-2.5 py-1.5 text-xs text-slate-800 font-medium"
                    />
                  </div>
                </div>
                <div className="flex justify-end pt-1">
                  <Button
                    type="button"
                    variant="primary"
                    size="sm"
                    onClick={() => {
                      const updated: RealGeocodedAddress = {
                        ...addressData,
                        village: customVillage.trim() || addressData.village,
                        taluk: customTaluk.trim() || addressData.taluk,
                        gramPanchayat: customGramPanchayat.trim() || "Gram Panchayat not verified — please confirm manually.",
                        provenance: {
                          ...addressData.provenance,
                          village: customVillage.trim() ? "Citizen confirmed" : addressData.provenance.village,
                          taluk: customTaluk.trim() ? "Citizen confirmed" : addressData.provenance.taluk,
                          gramPanchayat: customGramPanchayat.trim() ? "Citizen confirmed" : addressData.provenance.gramPanchayat,
                        },
                      };
                      setAddressData(updated);
                      setIsEditingLocality(false);
                      onLocationChange({
                        lat: currentLat,
                        lon: currentLon,
                        accuracy: accuracyMeters,
                        method: locationMethod,
                        timestamp: gpsTimestamp,
                        originalGpsLat: originalGpsLat,
                        originalGpsLon: originalGpsLon,
                        originalAccuracy: originalAccuracy,
                        address: updated,
                        isConfirmed: isConfirmed,
                      });
                    }}
                    className="bg-[#087F78] hover:bg-[#06635e] text-white text-[11px] h-7 px-3 font-bold"
                  >
                    Save Locality Details
                  </Button>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5 text-xs">
              {/* Village Component */}
              <div className="rounded-xl border border-teal-200/70 bg-white p-2.5 shadow-2xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Village
                  </span>
                  <ProvenanceBadge source={addressData.provenance.village} />
                </div>
                <span
                  className={`font-bold block truncate text-xs ${
                    addressData.village.includes("not identified") || addressData.village.includes("Not available")
                      ? "text-slate-500 italic font-normal"
                      : "text-[#087F78]"
                  }`}
                  title={addressData.village}
                >
                  {addressData.village}
                </span>
              </div>

              {/* Taluk Component */}
              <div className="rounded-xl border border-teal-200/70 bg-white p-2.5 shadow-2xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Taluk
                  </span>
                  <ProvenanceBadge source={addressData.provenance.taluk} />
                </div>
                <span
                  className={`font-bold block truncate text-xs ${
                    addressData.taluk.includes("not identified") || addressData.taluk.includes("Not available")
                      ? "text-slate-500 italic font-normal"
                      : "text-[#062B46]"
                  }`}
                  title={addressData.taluk}
                >
                  {addressData.taluk}
                </span>
              </div>

              {/* Gram Panchayat Component */}
              <div className="rounded-xl border border-teal-200/70 bg-white p-2.5 shadow-2xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Gram Panchayat
                  </span>
                  <ProvenanceBadge source={addressData.provenance.gramPanchayat} />
                </div>
                <span
                  className={`font-bold block truncate text-xs ${
                    !addressData.gramPanchayat || addressData.gramPanchayat.includes("not verified")
                      ? "text-slate-500 italic font-normal"
                      : "text-[#062B46]"
                  }`}
                  title={addressData.gramPanchayat || "Gram Panchayat not verified — please confirm manually."}
                >
                  {addressData.gramPanchayat || "Gram Panchayat not verified — please confirm manually."}
                </span>
              </div>

              {/* District Component */}
              <div className="rounded-xl border border-teal-200/70 bg-white p-2.5 shadow-2xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    District
                  </span>
                  <ProvenanceBadge source={addressData.provenance.district} />
                </div>
                <span
                  className={`font-bold block truncate text-xs ${
                    addressData.district.includes("Not available")
                      ? "text-slate-500 italic font-normal"
                      : "text-[#062B46]"
                  }`}
                  title={addressData.district}
                >
                  {addressData.district}
                </span>
              </div>

              {/* State */}
              <div className="rounded-xl border border-teal-200/70 bg-white p-2.5 shadow-2xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    State
                  </span>
                  <ProvenanceBadge source={addressData.provenance.state} />
                </div>
                <span className="font-bold text-[#062B46] block truncate text-xs">
                  {addressData.state || "Karnataka"}
                </span>
              </div>

              {/* Country */}
              <div className="rounded-xl border border-teal-200/70 bg-white p-2.5 shadow-2xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Country
                  </span>
                  <ProvenanceBadge source={addressData.provenance.country} />
                </div>
                <span className="font-bold text-[#062B46] block truncate text-xs">
                  {addressData.country || "India"}
                </span>
              </div>

              {/* PIN code */}
              <div className="rounded-xl border border-teal-200/70 bg-white p-2.5 shadow-2xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    PIN code
                  </span>
                  <ProvenanceBadge source={addressData.provenance.postalCode} />
                </div>
                <span className="font-mono font-bold text-xs text-slate-800">
                  {addressData.postalCode || "Not available"}
                </span>
              </div>

              {/* Latitude */}
              <div className="rounded-xl border border-teal-200/70 bg-white p-2.5 shadow-2xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Latitude
                  </span>
                  <ProvenanceBadge source={addressData.provenance.coordinates} />
                </div>
                <span className="font-mono font-bold text-[#062B46] text-xs">
                  {currentLat.toFixed(6)}°N
                </span>
              </div>

              {/* Longitude */}
              <div className="rounded-xl border border-teal-200/70 bg-white p-2.5 shadow-2xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Longitude
                  </span>
                  <ProvenanceBadge source={addressData.provenance.coordinates} />
                </div>
                <span className="font-mono font-bold text-[#062B46] text-xs">
                  {currentLon.toFixed(6)}°E
                </span>
              </div>

              {/* GPS Accuracy */}
              <div className="rounded-xl border border-teal-200/70 bg-white p-2.5 shadow-2xs space-y-1">
                <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">
                  GPS Accuracy
                </span>
                <span className="font-bold text-xs text-emerald-700 flex items-center gap-1">
                  {accuracyMeters ? `±${accuracyMeters} metres` : "Manual Marker Position"}
                </span>
              </div>
            </div>
          </div>

          {/* 4. CONFIRMATION ACTION BUTTON */}
          <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-teal-200/60">
            <div className="text-xs text-slate-600 flex items-center gap-1.5">
              {isConfirmed ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
              ) : (
                <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
              )}
              <span>
                {isConfirmed
                  ? "Location confirmed by citizen. Ready for complaint details."
                  : "Please review the detected location and click 'Confirm Location' to proceed."}
              </span>
            </div>

            <Button
              type="button"
              variant={isConfirmed ? "outline" : "primary"}
              onClick={() => {
                const nextState = !isConfirmed;
                if (onConfirmLocation) onConfirmLocation(nextState);
                onLocationChange({
                  lat: currentLat,
                  lon: currentLon,
                  accuracy: accuracyMeters,
                  method: locationMethod,
                  timestamp: gpsTimestamp,
                  originalGpsLat: originalGpsLat,
                  originalGpsLon: originalGpsLon,
                  originalAccuracy: originalAccuracy,
                  address: addressData,
                  isConfirmed: nextState,
                });
              }}
              className={`font-bold px-5 text-xs transition-all cursor-pointer ${
                isConfirmed
                  ? "bg-emerald-50 text-emerald-800 border-emerald-300 hover:bg-emerald-100"
                  : "bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm"
              }`}
            >
              <Check className="h-4 w-4 mr-1.5" />
              <span>{isConfirmed ? "Location Confirmed ✓" : "Confirm Location"}</span>
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
