"use client";

import React, { useEffect, useRef, useState } from "react";
import "leaflet/dist/leaflet.css";

export interface MapComplaint {
  id: string;
  reference_number?: string;
  category?: string;
  status: string;
  latitude: number;
  longitude: number;
  description?: string;
  priority?: string;
  assigned_worker_name?: string;
  village_name?: string;
  created_at?: string;
}

export interface LeafletMapProps {
  center?: [number, number];
  zoom?: number;
  boundaryGeoJson?: any;
  complaints?: MapComplaint[];
  selectedComplaintId?: string | null;
  onSelectComplaint?: (complaint: MapComplaint) => void;
  generalizeCoordinates?: boolean;
  height?: string;
  className?: string;
  showLegend?: boolean;
  interactive?: boolean;
}

const STATUS_COLORS: Record<string, { bg: string; border: string; label: string }> = {
  SUBMITTED: { bg: "#F59E0B", border: "#B45309", label: "Submitted" },
  UNDER_REVIEW: { bg: "#3B82F6", border: "#1D4ED8", label: "Under Review" },
  ASSIGNED: { bg: "#6366F1", border: "#4338CA", label: "Assigned" },
  IN_PROGRESS: { bg: "#8B5CF6", border: "#6D28D9", label: "In Progress" },
  REPAIR_REPORTED: { bg: "#F97316", border: "#C2410C", label: "Awaiting Verification" },
  AWAITING_VERIFICATION: { bg: "#F97316", border: "#C2410C", label: "Awaiting Verification" },
  RESOLVED: { bg: "#10B981", border: "#047857", label: "Resolved" },
  REOPENED: { bg: "#EF4444", border: "#B91C1C", label: "Reopened" },
};

export const LeafletMap: React.FC<LeafletMapProps> = ({
  center = [12.502, 76.685],
  zoom = 13,
  boundaryGeoJson,
  complaints = [],
  selectedComplaintId,
  onSelectComplaint,
  generalizeCoordinates = false,
  height = "520px",
  className = "",
  showLegend = true,
  interactive = true,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const markersLayerRef = useRef<any>(null);
  const boundaryLayerRef = useRef<any>(null);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Initialize Leaflet map
  useEffect(() => {
    if (!isMounted || !mapContainerRef.current) return;

    let isSubscribed = true;

    async function initMap() {
      const L = (await import("leaflet")).default;

      if (!isSubscribed || !mapContainerRef.current) return;

      // Clean up previous instance if exists
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }

      // Initialize map instance
      const map = L.map(mapContainerRef.current, {
        center,
        zoom,
        zoomControl: true,
        scrollWheelZoom: interactive,
        dragging: interactive,
      });

      // Add OpenStreetMap tile layer
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | GramaSeva Civic GIS',
        maxZoom: 19,
      }).addTo(map);

      // Create layers
      boundaryLayerRef.current = L.geoJSON(null, {
        style: {
          color: "#087F78",
          weight: 2.5,
          opacity: 0.85,
          fillColor: "#087F78",
          fillOpacity: 0.08,
          dashArray: "4, 4",
        },
      }).addTo(map);

      markersLayerRef.current = L.layerGroup().addTo(map);
      mapInstanceRef.current = map;

      // Render initial layers
      renderBoundary(L, map);
      renderMarkers(L, map);
    }

    initMap();

    return () => {
      isSubscribed = false;
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [isMounted]);

  // Helper to render boundary GeoJSON
  const renderBoundary = (L: any, map: any) => {
    if (!boundaryLayerRef.current) return;
    boundaryLayerRef.current.clearLayers();

    if (boundaryGeoJson) {
      try {
        boundaryLayerRef.current.addData(boundaryGeoJson);
        const bounds = boundaryLayerRef.current.getBounds();
        if (bounds.isValid()) {
          map.fitBounds(bounds, { padding: [24, 24] });
        }
      } catch (err) {
        console.warn("Could not parse or render boundary GeoJSON:", err);
      }
    }
  };

  // Helper to render complaint markers
  const renderMarkers = (L: any, map: any) => {
    if (!markersLayerRef.current) return;
    markersLayerRef.current.clearLayers();

    const validComplaints = complaints.filter(
      (c) => typeof c.latitude === "number" && typeof c.longitude === "number"
    );

    validComplaints.forEach((c) => {
      let lat = c.latitude;
      let lng = c.longitude;

      // Coordinate generalization for public privacy (~100m grid jitter / rounding)
      if (generalizeCoordinates) {
        lat = Math.round(lat * 1000) / 1000;
        lng = Math.round(lng * 1000) / 1000;
      }

      const st = (c.status || "SUBMITTED").toUpperCase();
      const colorInfo = STATUS_COLORS[st] || STATUS_COLORS.SUBMITTED;
      const isSelected = selectedComplaintId === c.id;

      // Custom HTML Pin DivIcon
      const pinHtml = `
        <div style="
          position: relative;
          width: ${isSelected ? "28px" : "22px"};
          height: ${isSelected ? "28px" : "22px"};
          border-radius: 50%;
          background-color: ${colorInfo.bg};
          border: 2.5px solid #ffffff;
          box-shadow: 0 2px 6px rgba(0,0,0,0.35);
          display: flex;
          align-items: center;
          justify-content: center;
          transform: ${isSelected ? "scale(1.2)" : "scale(1)"};
          transition: transform 0.15s ease;
        ">
          <div style="
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background-color: #ffffff;
          "></div>
        </div>
      `;

      const customIcon = L.divIcon({
        html: pinHtml,
        className: "custom-leaflet-pin",
        iconSize: [isSelected ? 28 : 22, isSelected ? 28 : 22],
        iconAnchor: [isSelected ? 14 : 11, isSelected ? 14 : 11],
      });

      const marker = L.marker([lat, lng], { icon: customIcon });

      // Popup Content
      const popupContent = `
        <div style="font-family: sans-serif; font-size: 12px; line-height: 1.4; min-width: 170px;">
          <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 4px;">
            <span style="font-weight: bold; color: #102B4E;">${c.reference_number || c.id.slice(0, 8)}</span>
            <span style="font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 9999px; background-color: ${colorInfo.bg}22; color: ${colorInfo.border};">
              ${colorInfo.label}
            </span>
          </div>
          <p style="margin: 0 0 4px 0; color: #40536B; font-size: 11px;">${c.category || "Infrastructure Issue"}</p>
          ${c.description ? `<p style="margin: 0 0 6px 0; color: #1E293B; font-size: 11px;">${c.description.slice(0, 80)}${c.description.length > 80 ? "..." : ""}</p>` : ""}
          <div style="font-size: 10px; color: #64748B; border-top: 1px solid #E2E8F0; padding-top: 4px;">
            ${c.village_name ? `<span>📍 ${c.village_name}</span><br/>` : ""}
            ${c.assigned_worker_name ? `<span>👷 ${c.assigned_worker_name}</span>` : ""}
          </div>
        </div>
      `;

      marker.bindPopup(popupContent);

      if (onSelectComplaint) {
        marker.on("click", () => {
          onSelectComplaint(c);
        });
      }

      markersLayerRef.current.addLayer(marker);
    });
  };

  // Update boundary when prop changes
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    import("leaflet").then((L) => {
      renderBoundary(L.default, mapInstanceRef.current);
    });
  }, [boundaryGeoJson]);

  // Update markers when complaints or selection changes
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    import("leaflet").then((L) => {
      renderMarkers(L.default, mapInstanceRef.current);
    });
  }, [complaints, selectedComplaintId, generalizeCoordinates]);

  if (!isMounted) {
    return (
      <div
        style={{ height }}
        className={`w-full rounded-2xl bg-slate-100 flex items-center justify-center border border-[#DCE5EE] ${className}`}
      >
        <div className="flex items-center gap-2 text-xs font-semibold text-[#40536B]">
          <span className="w-2 h-2 rounded-full bg-[#087F78] animate-pulse" />
          <span>Loading Interactive Civic Map...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`relative w-full rounded-2xl overflow-hidden border border-[#DCE5EE] shadow-xs ${className}`}>
      <div ref={mapContainerRef} style={{ height }} className="w-full z-0" />

      {/* Map Legend Overlay */}
      {showLegend && (
        <div className="absolute bottom-3 left-3 z-10 bg-white/95 backdrop-blur-md px-3 py-2 rounded-xl border border-[#DCE5EE] shadow-sm text-[11px] space-y-1.5 max-w-[200px] pointer-events-auto">
          <p className="font-bold text-[#102B4E] uppercase tracking-wider text-[10px]">
            Civic Status Legend
          </p>
          <div className="grid grid-cols-2 gap-x-2 gap-y-1">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#F59E0B] shrink-0" />
              <span className="text-[#40536B]">Submitted</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#3B82F6] shrink-0" />
              <span className="text-[#40536B]">Review</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#6366F1] shrink-0" />
              <span className="text-[#40536B]">Assigned</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#8B5CF6] shrink-0" />
              <span className="text-[#40536B]">In Progress</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#F97316] shrink-0" />
              <span className="text-[#40536B]">Verify</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#10B981] shrink-0" />
              <span className="text-[#40536B]">Resolved</span>
            </div>
          </div>
          {generalizeCoordinates && (
            <p className="text-[9px] text-[#64748B] pt-1 border-t border-slate-200">
              🛡️ Public View: ~100m generalized coordinates
            </p>
          )}
        </div>
      )}
    </div>
  );
};
