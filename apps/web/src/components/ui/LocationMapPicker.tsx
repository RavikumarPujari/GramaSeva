"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  MapPin,
  Navigation,
  Crosshair,
  ZoomIn,
  ZoomOut,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

export interface LocationShortcut {
  name: string;
  village: string;
  lat: number;
  lon: number;
  description: string;
}

export const BELAGAVI_SHORTCUTS: LocationShortcut[] = [
  {
    name: "VTU Campus",
    village: "Machhe GP",
    lat: 15.8028,
    lon: 74.4827,
    description: "Visvesvaraya Technological University (Jnana Sangama)",
  },
  {
    name: "Belagavi Central",
    village: "Belagavi City",
    lat: 15.8497,
    lon: 74.5078,
    description: "Central Municipal Corporation Zone / Khasbag",
  },
  {
    name: "Machhe GP Office",
    village: "Machhe GP",
    lat: 15.7981,
    lon: 74.4752,
    description: "Machhe Gram Panchayat Office & Industrial Area",
  },
  {
    name: "Peeranwadi GP",
    village: "Peeranwadi GP",
    lat: 15.8152,
    lon: 74.461,
    description: "Peeranwadi Junction & Khanapur Road",
  },
  {
    name: "Kakati GP",
    village: "Kakati GP",
    lat: 15.9189,
    lon: 74.5385,
    description: "Kakati Gram Panchayat & NH4 Highway junction",
  },
];

interface LocationMapPickerProps {
  latitude: number | null;
  longitude: number | null;
  accuracyMeters: number | null;
  onChange: (
    lat: number,
    lon: number,
    accuracy: number,
    method: "gps" | "manual",
    villageSuggestion?: string
  ) => void;
  className?: string;
}

// Convert lat/lon to OpenStreetMap tile numbers
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
  onChange,
  className = "",
}: LocationMapPickerProps) {
  // Belagavi default center
  const defaultLat = 15.8497;
  const defaultLon = 74.5078;

  const currentLat = latitude ?? defaultLat;
  const currentLon = longitude ?? defaultLon;

  const [zoom, setZoom] = useState(15);
  const [isLocating, setIsLocating] = useState(false);
  const [gpsError, setGpsError] = useState<string | null>(null);
  const [activeShortcut, setActiveShortcut] = useState<string | null>(null);

  // Map viewport dimensions
  const mapContainerRef = useRef<HTMLDivElement>(null);

  // Calculate 3x3 tiles around center
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

  // Handle map click to reposition pin
  const handleMapClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!mapContainerRef.current) return;
    const rect = mapContainerRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const normX = (clickX / rect.width) - 0.5;
    const normY = (clickY / rect.height) - 0.5;

    // Delta mapping based on zoom level
    const factor = 360 / Math.pow(2, zoom) / 2;
    const newLon = Number((currentLon + normX * factor).toFixed(6));
    const newLat = Number((currentLat - normY * (factor * 0.75)).toFixed(6));

    // Find closest Belagavi village shortcut
    let closestVillage = "Belagavi Central";
    let minDistance = Infinity;
    BELAGAVI_SHORTCUTS.forEach((sc) => {
      const d = Math.hypot(sc.lat - newLat, sc.lon - newLon);
      if (d < minDistance) {
        minDistance = d;
        closestVillage = sc.village;
      }
    });

    setActiveShortcut(null);
    onChange(newLat, newLon, 5, "manual", closestVillage);
  };

  // Browser Geolocation
  const handleGetGPS = () => {
    if (!navigator.geolocation) {
      setGpsError("Geolocation is not supported by your browser.");
      return;
    }
    setIsLocating(true);
    setGpsError(null);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = Number(pos.coords.latitude.toFixed(6));
        const lon = Number(pos.coords.longitude.toFixed(6));
        const acc = Math.round(pos.coords.accuracy);

        let closestVillage = "Belagavi Central";
        let minDistance = Infinity;
        BELAGAVI_SHORTCUTS.forEach((sc) => {
          const d = Math.hypot(sc.lat - lat, sc.lon - lon);
          if (d < minDistance) {
            minDistance = d;
            closestVillage = sc.village;
          }
        });

        setIsLocating(false);
        setActiveShortcut(null);
        onChange(lat, lon, acc, "gps", closestVillage);
      },
      (err) => {
        setIsLocating(false);
        let msg = "Could not obtain GPS coordinates.";
        if (err.code === 1) msg = "Location permission denied. Please select location using shortcut pills or click on the map.";
        else if (err.code === 2) msg = "GPS signal unavailable. Please select your village below.";
        else if (err.code === 3) msg = "Location request timed out. Please try again.";
        setGpsError(msg);
      },
      { timeout: 12000, enableHighAccuracy: true, maximumAge: 0 }
    );
  };

  const handleSelectShortcut = (sc: LocationShortcut) => {
    setActiveShortcut(sc.name);
    onChange(sc.lat, sc.lon, 10, "manual", sc.village);
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Geolocation Button and Accuracy Header */}
      <div className="p-4 rounded-2xl bg-gradient-to-r from-teal-50 via-sky-50 to-indigo-50/40 border border-teal-200/80 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#087F78] text-white flex items-center justify-center shrink-0 shadow-xs">
              <Navigation className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-[#102B4E]">
                Belagavi Pilot GPS & Pin Verification
              </h3>
              <p className="text-xs text-slate-600">
                Pinpoint exact coordinates for field inspection and verified resolution.
              </p>
            </div>
          </div>

          <Button
            variant="primary"
            size="sm"
            onClick={handleGetGPS}
            isLoading={isLocating}
            leftIcon={<Crosshair className="w-4 h-4" />}
            className="shrink-0"
          >
            {isLocating ? "Acquiring GPS..." : "Capture Current GPS"}
          </Button>
        </div>

        {gpsError && (
          <div className="p-2.5 bg-amber-50 rounded-xl border border-amber-200 text-xs text-amber-900 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>{gpsError}</span>
          </div>
        )}

        {latitude && longitude && (
          <div className="pt-2 border-t border-teal-200/60 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
            <div className="bg-white p-2.5 rounded-xl border border-teal-200/60 shadow-2xs">
              <span className="text-slate-500 block text-[10px] uppercase font-bold">Latitude</span>
              <span className="font-mono font-bold text-[#102B4E]">{latitude}°</span>
            </div>
            <div className="bg-white p-2.5 rounded-xl border border-teal-200/60 shadow-2xs">
              <span className="text-slate-500 block text-[10px] uppercase font-bold">Longitude</span>
              <span className="font-mono font-bold text-[#102B4E]">{longitude}°</span>
            </div>
            <div className="bg-white p-2.5 rounded-xl border border-teal-200/60 shadow-2xs">
              <span className="text-slate-500 block text-[10px] uppercase font-bold">Accuracy</span>
              <span className="font-bold text-emerald-700">
                {accuracyMeters ? `±${accuracyMeters}m` : "High"}
              </span>
            </div>
            <div className="bg-white p-2.5 rounded-xl border border-teal-200/60 shadow-2xs">
              <span className="text-slate-500 block text-[10px] uppercase font-bold">Jurisdiction</span>
              <span className="font-bold text-[#087F78] truncate block">
                {activeShortcut ? activeShortcut : "Belagavi Pilot GP"}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Belagavi Quick Shortcut Pills */}
      <div className="space-y-1.5">
        <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
          Quick Belagavi Pilot Landmarks:
        </label>
        <div className="flex flex-wrap gap-2">
          {BELAGAVI_SHORTCUTS.map((sc) => {
            const isSelected =
              activeShortcut === sc.name ||
              (latitude === sc.lat && longitude === sc.lon);
            return (
              <button
                key={sc.name}
                type="button"
                onClick={() => handleSelectShortcut(sc)}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all border flex items-center gap-1.5 ${
                  isSelected
                    ? "bg-[#102B4E] text-white border-[#102B4E] shadow-xs"
                    : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
                }`}
                title={sc.description}
              >
                <MapPin
                  className={`w-3.5 h-3.5 ${
                    isSelected ? "text-amber-400" : "text-[#087F78]"
                  }`}
                />
                <span>{sc.name}</span>
                <span className="text-[10px] opacity-75 font-normal">({sc.village})</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Interactive Map Canvas */}
      <div className="border border-slate-200 rounded-2xl overflow-hidden bg-slate-100 shadow-xs relative">
        <div className="bg-[#102B4E] text-white px-4 py-2 text-xs font-semibold flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <MapPin className="w-3.5 h-3.5 text-amber-400" />
            Click anywhere on map to reposition pin
          </span>
          <span className="text-[11px] text-slate-300 font-mono">
            {currentLat.toFixed(4)}°N, {currentLon.toFixed(4)}°E
          </span>
        </div>

        {/* Map Viewport */}
        <div
          ref={mapContainerRef}
          onClick={handleMapClick}
          className="relative h-60 sm:h-72 w-full cursor-crosshair overflow-hidden bg-[#e5eef4] select-none"
        >
          {/* Tile Layer (OpenStreetMap / Carto Style) */}
          <div className="absolute inset-0 grid grid-cols-3 grid-rows-3 opacity-90">
            {tiles.map((t) => (
              <img
                key={t.key}
                src={`https://tile.openstreetmap.org/${t.key}.png`}
                alt="map tile"
                className="w-full h-full object-cover pointer-events-none select-none"
                loading="lazy"
                onError={(e) => {
                  // Fallback tile color if offline
                  e.currentTarget.style.display = "none";
                }}
              />
            ))}
          </div>

          {/* SVG Road and Landmark Overlay for Belagavi Region */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-40" viewBox="0 0 400 300">
            <line x1="0" y1="150" x2="400" y2="150" stroke="#102B4E" strokeWidth="3" />
            <line x1="200" y1="0" x2="200" y2="300" stroke="#102B4E" strokeWidth="3" />
            <circle cx="200" cy="150" r="16" fill="#087F78" opacity="0.3" />
            <text x="215" y="145" fontSize="10" fill="#102B4E" fontWeight="bold">
              Belagavi Center
            </text>
          </svg>

          {/* Centered Pinned Marker */}
          <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-full pointer-events-none drop-shadow-lg flex flex-col items-center">
            <div className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#102B4E] text-white shadow-md mb-1 whitespace-nowrap flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
              <span>Grievance Site</span>
            </div>
            <MapPin className="w-9 h-9 text-rose-600 fill-rose-500 animate-bounce" />
          </div>

          {/* Zoom Controls */}
          <div className="absolute bottom-3 right-3 flex flex-col gap-1.5 z-10">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setZoom((z) => Math.min(18, z + 1));
              }}
              className="p-2 rounded-xl bg-white/95 backdrop-blur-xs hover:bg-white text-slate-800 shadow-md border border-slate-200 transition-transform active:scale-95"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setZoom((z) => Math.max(12, z - 1));
              }}
              className="p-2 rounded-xl bg-white/95 backdrop-blur-xs hover:bg-white text-slate-800 shadow-md border border-slate-200 transition-transform active:scale-95"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
          </div>

          <div className="absolute bottom-2 left-2 bg-white/90 backdrop-blur-xs px-2.5 py-1 rounded-lg text-[11px] text-slate-700 border border-slate-200 shadow-xs pointer-events-none">
            Tip: Click anywhere to move the pin directly to the defect spot
          </div>
        </div>
      </div>
    </div>
  );
}
