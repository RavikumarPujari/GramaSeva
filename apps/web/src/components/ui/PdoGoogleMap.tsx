"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import {
  MapPin,
  Layers,
  Navigation,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Eye,
  Maximize2,
  RotateCcw,
} from "lucide-react";

declare global {
  interface Window {
    google?: any;
  }
}
declare const google: any;

export interface PdoMapComplaint {
  id: string;
  reference_number?: string;
  category?: string;
  status: string;
  priority?: string;
  latitude: number;
  longitude: number;
  description?: string;
  assigned_worker_name?: string;
  village_name?: string;
  gps_accuracy?: number;
  submitted_at?: string;
}

export interface PdoGoogleMapProps {
  complaints: PdoMapComplaint[];
  selectedComplaintId?: string | null;
  onSelectComplaint?: (complaint: PdoMapComplaint) => void;
  centerLat?: number;
  centerLon?: number;
  height?: string;
  className?: string;
}

const STATUS_COLORS: Record<string, { pin: string; text: string; bg: string }> = {
  SUBMITTED: { pin: "#F59E0B", text: "#92400E", bg: "#FEF3C7" },
  UNDER_REVIEW: { pin: "#2563EB", text: "#1E40AF", bg: "#DBEAFE" },
  APPROVED: { pin: "#2563EB", text: "#1E40AF", bg: "#DBEAFE" },
  ASSIGNED: { pin: "#4F46E5", text: "#3730A3", bg: "#E0E7FF" },
  IN_PROGRESS: { pin: "#9333EA", text: "#6B21A8", bg: "#F3E8FF" },
  REPAIR_REPORTED: { pin: "#EA580C", text: "#9A3412", bg: "#FFEDD5" },
  AWAITING_VERIFICATION: { pin: "#EA580C", text: "#9A3412", bg: "#FFEDD5" },
  RESOLVED: { pin: "#059669", text: "#065F46", bg: "#D1FAE5" },
  REOPENED: { pin: "#DC2626", text: "#991B1B", bg: "#FEE2E2" },
};

function createPinSvg(color: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="42" viewBox="0 0 32 42">
    <path fill="${color}" stroke="#FFFFFF" stroke-width="2" d="M16 0C7.16 0 0 7.16 0 16c0 11.25 14.25 24.75 14.88 25.34a1.5 1.5 0 0 0 2.24 0C17.75 40.75 32 27.25 32 16 32 7.16 24.84 0 16 0z"/>
    <circle cx="16" cy="16" r="6" fill="#FFFFFF"/>
  </svg>`;
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

export function PdoGoogleMap({
  complaints = [],
  selectedComplaintId,
  onSelectComplaint,
  centerLat = 15.8152,
  centerLon = 74.461,
  height = "600px",
  className = "",
}: PdoGoogleMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const markersRef = useRef<Map<string, any>>(new Map());
  const activeInfoWindowRef = useRef<any>(null);
  const pdoLocationMarkerRef = useRef<any>(null);

  const [mapType, setMapType] = useState<"roadmap" | "hybrid">("roadmap");
  const [isLocatingPdo, setIsLocatingPdo] = useState(false);
  const [pdoCoords, setPdoCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [apiReady, setApiReady] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // Load Google Maps JavaScript API
  useEffect(() => {
    if (typeof window === "undefined") return;

    if (window.google?.maps) {
      setApiReady(true);
      return;
    }

    const existingScript = document.getElementById("google-maps-script");
    if (existingScript) {
      existingScript.addEventListener("load", () => setApiReady(true));
      return;
    }

    const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
    if (!apiKey) {
      setApiError("Google Maps API Key not configured.");
      return;
    }

    const script = document.createElement("script");
    script.id = "google-maps-script";
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places,geometry`;
    script.async = true;
    script.defer = true;
    script.onload = () => setApiReady(true);
    script.onerror = () => setApiError("Failed to load Google Maps JavaScript API.");
    document.head.appendChild(script);
  }, []);

  // Initialize Map
  useEffect(() => {
    if (!apiReady || !mapContainerRef.current || mapInstanceRef.current) return;

    const initialCenter = complaints.length > 0
      ? { lat: complaints[0].latitude, lng: complaints[0].longitude }
      : { lat: centerLat, lng: centerLon };

    const map = new google.maps.Map(mapContainerRef.current, {
      center: initialCenter,
      zoom: 13,
      mapTypeId: mapType,
      mapTypeControl: false,
      streetViewControl: false,
      fullscreenControl: true,
      zoomControl: true,
    });

    mapInstanceRef.current = map;
  }, [apiReady, centerLat, centerLon, complaints, mapType]);

  // Update Map Type (Roadmap / Satellite Hybrid)
  const toggleMapType = (type: "roadmap" | "hybrid") => {
    setMapType(type);
    if (mapInstanceRef.current) {
      mapInstanceRef.current.setMapTypeId(type);
    }
  };

  // Sync Markers
  useEffect(() => {
    if (!mapInstanceRef.current || !window.google?.maps) return;

    const map = mapInstanceRef.current;

    // Clear old markers
    markersRef.current.forEach((marker) => marker.setMap(null));
    markersRef.current.clear();

    const validComplaints = complaints.filter(
      (c) => typeof c.latitude === "number" && typeof c.longitude === "number" && !isNaN(c.latitude) && !isNaN(c.longitude)
    );

    validComplaints.forEach((comp) => {
      const statusStyle = STATUS_COLORS[comp.status] || STATUS_COLORS.SUBMITTED;
      const marker = new google.maps.Marker({
        position: { lat: comp.latitude, lng: comp.longitude },
        map,
        title: `${comp.reference_number || comp.id} - ${comp.category || "Issue"}`,
        icon: {
          url: createPinSvg(statusStyle.pin),
          scaledSize: new google.maps.Size(32, 42),
          anchor: new google.maps.Point(16, 42),
        },
      });

      const infoContent = `
        <div style="font-family: system-ui, -apple-system, sans-serif; padding: 10px; max-width: 280px; color: #102B4E;">
          <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 6px;">
            <span style="font-family: monospace; font-size: 13px; font-weight: 800; color: #102B4E;">
              ${comp.reference_number || comp.id.slice(0, 8)}
            </span>
            <span style="font-size: 10px; font-weight: 800; text-transform: uppercase; padding: 2px 8px; border-radius: 9999px; background: ${statusStyle.bg}; color: ${statusStyle.text};">
              ${comp.status.replace("_", " ")}
            </span>
          </div>
          <div style="font-size: 12px; font-weight: 700; color: #087F78; text-transform: capitalize; margin-bottom: 4px;">
            ${(comp.category || "Issue").replace("_", " ")}
          </div>
          ${comp.village_name ? `<div style="font-size: 11px; color: #64748B; margin-bottom: 4px;">📍 ${comp.village_name}</div>` : ""}
          ${comp.description ? `<p style="font-size: 11px; color: #475569; margin: 6px 0; line-height: 1.4; max-height: 48px; overflow: hidden;">${comp.description}</p>` : ""}
          <div style="font-size: 10px; color: #94A3B8; margin-top: 6px; padding-top: 6px; border-top: 1px solid #E2E8F0; display: flex; justify-content: space-between;">
            <span>${comp.latitude.toFixed(4)}, ${comp.longitude.toFixed(4)}</span>
            ${comp.gps_accuracy ? `<span>±${Math.round(comp.gps_accuracy)}m accuracy</span>` : ""}
          </div>
        </div>
      `;

      const infoWindow = new google.maps.InfoWindow({
        content: infoContent,
      });

      marker.addListener("click", () => {
        if (activeInfoWindowRef.current) {
          activeInfoWindowRef.current.close();
        }
        infoWindow.open(map, marker);
        activeInfoWindowRef.current = infoWindow;
        if (onSelectComplaint) {
          onSelectComplaint(comp);
        }
      });

      markersRef.current.set(comp.id, marker);
    });

    // Auto-center bounds if valid complaints exist
    if (validComplaints.length > 1) {
      const bounds = new google.maps.LatLngBounds();
      validComplaints.forEach((c) => bounds.extend({ lat: c.latitude, lng: c.longitude }));
      map.fitBounds(bounds);
    } else if (validComplaints.length === 1) {
      map.setCenter({ lat: validComplaints[0].latitude, lng: validComplaints[0].longitude });
      map.setZoom(15);
    }
  }, [complaints, onSelectComplaint]);

  // Center on Selected Complaint
  useEffect(() => {
    if (!selectedComplaintId || !mapInstanceRef.current) return;
    const marker = markersRef.current.get(selectedComplaintId);
    if (marker) {
      const pos = marker.getPosition();
      if (pos) {
        mapInstanceRef.current.panTo(pos);
        mapInstanceRef.current.setZoom(16);
        google.maps.event.trigger(marker, "click");
      }
    }
  }, [selectedComplaintId]);

  // Fit all complaints
  const handleFitAll = () => {
    if (!mapInstanceRef.current || complaints.length === 0) return;
    const bounds = new google.maps.LatLngBounds();
    complaints.forEach((c) => {
      if (c.latitude && c.longitude) bounds.extend({ lat: c.latitude, lng: c.longitude });
    });
    mapInstanceRef.current.fitBounds(bounds);
  };

  // PDO Live GPS Location (distinct blue pulse marker)
  const handlePdoLiveLocation = () => {
    if (!navigator.geolocation) {
      alert("Geolocation is not supported by your browser.");
      return;
    }
    setIsLocatingPdo(true);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setIsLocatingPdo(false);
        const { latitude, longitude } = pos.coords;
        setPdoCoords({ lat: latitude, lng: longitude });

        if (mapInstanceRef.current) {
          mapInstanceRef.current.panTo({ lat: latitude, lng: longitude });
          mapInstanceRef.current.setZoom(16);

          if (pdoLocationMarkerRef.current) {
            pdoLocationMarkerRef.current.setPosition({ lat: latitude, lng: longitude });
          } else {
            const pdoSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 30 30">
              <circle cx="15" cy="15" r="14" fill="#0284C7" fill-opacity="0.25" stroke="#0284C7" stroke-width="2"/>
              <circle cx="15" cy="15" r="7" fill="#0284C7" stroke="#FFFFFF" stroke-width="2"/>
            </svg>`;
            pdoLocationMarkerRef.current = new google.maps.Marker({
              position: { lat: latitude, lng: longitude },
              map: mapInstanceRef.current,
              title: "Your Live Location (PDO Staff)",
              icon: {
                url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(pdoSvg)}`,
                scaledSize: new google.maps.Size(30, 30),
                anchor: new google.maps.Point(15, 15),
              },
            });
          }
        }
      },
      (err) => {
        setIsLocatingPdo(false);
        alert(`Could not detect your GPS location: ${err.message}`);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  };

  return (
    <div className={`relative rounded-2xl border border-[#DCE5EE] overflow-hidden bg-slate-100 shadow-xs ${className}`}>
      {/* Map Action Controls Bar */}
      <div className="absolute top-3 left-3 z-10 flex flex-wrap items-center gap-2">
        {/* Satellite / Road View Toggle */}
        <div className="bg-white/95 backdrop-blur-xs p-1 rounded-xl shadow-md border border-slate-200 flex items-center gap-1">
          <button
            type="button"
            onClick={() => toggleMapType("roadmap")}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              mapType === "roadmap"
                ? "bg-[#087F78] text-white shadow-2xs"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
            }`}
          >
            Map
          </button>
          <button
            type="button"
            onClick={() => toggleMapType("hybrid")}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all ${
              mapType === "hybrid"
                ? "bg-[#087F78] text-white shadow-2xs"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            Satellite
          </button>
        </div>

        {/* Fit Bounds */}
        <button
          type="button"
          onClick={handleFitAll}
          title="Fit all complaints in view"
          className="bg-white/95 backdrop-blur-xs px-3 py-2 rounded-xl shadow-md border border-slate-200 text-xs font-bold text-slate-700 hover:bg-slate-50 flex items-center gap-1.5 cursor-pointer"
        >
          <Maximize2 className="w-3.5 h-3.5 text-[#087F78]" />
          Fit All ({complaints.length})
        </button>

        {/* PDO Live Location Button */}
        <button
          type="button"
          onClick={handlePdoLiveLocation}
          disabled={isLocatingPdo}
          title="Detect PDO staff GPS location"
          className="bg-white/95 backdrop-blur-xs px-3 py-2 rounded-xl shadow-md border border-slate-200 text-xs font-bold text-sky-700 hover:bg-sky-50 flex items-center gap-1.5 cursor-pointer disabled:opacity-60"
        >
          {isLocatingPdo ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin text-sky-600" />
          ) : (
            <Navigation className="w-3.5 h-3.5 text-sky-600" />
          )}
          My Location
        </button>
      </div>

      {/* Map Legend (Bottom Left) */}
      <div className="absolute bottom-3 left-3 z-10 bg-white/95 backdrop-blur-xs p-3 rounded-xl shadow-md border border-slate-200 text-xs space-y-1.5 hidden sm:block">
        <span className="font-bold text-[11px] uppercase tracking-wider text-slate-500 block mb-1">
          Complaint Status Legend
        </span>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> Submitted
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-600" /> Under Review
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-600" /> Assigned
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-600" /> In Progress
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-orange-500" /> Verification
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-600" /> Resolved
          </span>
        </div>
      </div>

      {/* Map Container */}
      <div ref={mapContainerRef} style={{ width: "100%", height }} />

      {/* API Loading / Error Overlay */}
      {!apiReady && !apiError && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-50/80 backdrop-blur-2xs gap-3">
          <Loader2 className="w-8 h-8 text-[#087F78] animate-spin" />
          <p className="text-xs font-bold text-slate-600">Loading Google Maps Platform...</p>
        </div>
      )}

      {apiError && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-red-50/90 p-6 text-center gap-2">
          <AlertCircle className="w-8 h-8 text-red-600" />
          <p className="text-sm font-bold text-red-800">{apiError}</p>
          <p className="text-xs text-red-600">Verify NEXT_PUBLIC_GOOGLE_MAPS_API_KEY configuration in environment.</p>
        </div>
      )}
    </div>
  );
}
