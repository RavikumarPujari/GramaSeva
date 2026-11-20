"use client";

import React, { useState, useRef } from "react";
import { Eye, EyeOff, Sparkles, ShieldAlert, CheckCircle2, AlertCircle } from "lucide-react";
import { Badge } from "@/components/ui/Badge";

export interface DetectionObservation {
  class_id?: number;
  label: string;
  confidence: number;
  bbox: number[]; // [x1, y1, x2, y2] pixel or normalized coordinates
}

interface ImageAnnotationOverlayProps {
  imageUrl: string;
  observations?: DetectionObservation[];
  modelId?: string;
  latencyMs?: number;
  confidenceScore?: number;
  requiresHumanReview?: boolean;
  className?: string;
  showDetails?: boolean;
}

export function ImageAnnotationOverlay({
  imageUrl,
  observations = [],
  modelId = "oracl4-rdd-yolov8s",
  latencyMs,
  confidenceScore,
  requiresHumanReview = true,
  className = "",
  showDetails = true,
}: ImageAnnotationOverlayProps) {
  const [showAnnotations, setShowAnnotations] = useState(true);
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const [imgSize, setImgSize] = useState<{ width: number; height: number }>({ width: 640, height: 640 });
  const [imageLoaded, setImageLoaded] = useState(false);

  const hasDetections = observations && observations.length > 0;

  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const { naturalWidth, naturalHeight } = e.currentTarget;
    if (naturalWidth && naturalHeight) {
      setImgSize({ width: naturalWidth, height: naturalHeight });
      setImageLoaded(true);
    }
  };

  // Convert bbox coordinates to SVG rectangle parameters
  const getBoxCoords = (bbox: number[]) => {
    if (!bbox || bbox.length < 4) return null;
    let [x1, y1, x2, y2] = bbox;

    // Check if normalized (0.0 - 1.0)
    const isNormalized = x1 <= 1.0 && y1 <= 1.0 && x2 <= 1.0 && y2 <= 1.0;
    if (isNormalized) {
      x1 = x1 * imgSize.width;
      y1 = y1 * imgSize.height;
      x2 = x2 * imgSize.width;
      y2 = y2 * imgSize.height;
    }

    const width = Math.max(0, x2 - x1);
    const height = Math.max(0, y2 - y1);

    return { x: x1, y: y1, width, height, x2, y2 };
  };

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Visual Canvas Container */}
      <div className="relative rounded-2xl overflow-hidden border border-slate-200 bg-slate-950 flex items-center justify-center select-none shadow-xs">
        {/* Underlay Image */}
        <img
          src={imageUrl}
          alt="Defect visual inspection"
          onLoad={handleImageLoad}
          className="w-full max-h-[460px] object-contain transition-opacity duration-300"
        />

        {/* Responsive SVG Bounding Box Layer */}
        {showAnnotations && imageLoaded && hasDetections && (
          <svg
            className="absolute inset-0 w-full h-full pointer-events-auto"
            viewBox={`0 0 ${imgSize.width} ${imgSize.height}`}
            preserveAspectRatio="xMidYMid meet"
          >
            <defs>
              <filter id="boxShadow" x="-10%" y="-10%" width="120%" height="120%">
                <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.4" />
              </filter>
            </defs>

            {observations.map((obs, idx) => {
              const coords = getBoxCoords(obs.bbox);
              if (!coords) return null;

              const isHighSeverity =
                obs.confidence > 0.85 ||
                obs.label.toLowerCase().includes("pothole") ||
                obs.label.toLowerCase().includes("severe");

              const strokeColor = isHighSeverity ? "#EF4444" : "#EAB308";
              const fillColor = isHighSeverity ? "rgba(239, 68, 68, 0.18)" : "rgba(234, 179, 8, 0.16)";
              const isHovered = hoveredIdx === idx;

              // Position label pill nicely above or inside box
              const labelY = coords.y > 30 ? coords.y - 8 : coords.y + 24;
              const pillHeight = 22;
              const pillPadding = 8;
              const textStr = `${obs.label} · ${Math.round(obs.confidence * 100)}%`;
              // Approximate text width: 7.5px per character
              const pillWidth = textStr.length * 7.5 + pillPadding * 2;

              return (
                <g
                  key={idx}
                  onMouseEnter={() => setHoveredIdx(idx)}
                  onMouseLeave={() => setHoveredIdx(null)}
                  className="cursor-pointer transition-all duration-150"
                >
                  {/* Bounding Box Rectangle */}
                  <rect
                    x={coords.x}
                    y={coords.y}
                    width={coords.width}
                    height={coords.height}
                    fill={fillColor}
                    stroke={strokeColor}
                    strokeWidth={isHovered ? 4 : 2.5}
                    strokeDasharray={isHovered ? "none" : undefined}
                    rx="4"
                    ry="4"
                    filter="url(#boxShadow)"
                  />

                  {/* Corner Accent Handles */}
                  <line
                    x1={coords.x}
                    y1={coords.y}
                    x2={coords.x + Math.min(16, coords.width / 3)}
                    y2={coords.y}
                    stroke={strokeColor}
                    strokeWidth={4.5}
                  />
                  <line
                    x1={coords.x}
                    y1={coords.y}
                    x2={coords.x}
                    y2={coords.y + Math.min(16, coords.height / 3)}
                    stroke={strokeColor}
                    strokeWidth={4.5}
                  />
                  <line
                    x1={coords.x2}
                    y1={coords.y2}
                    x2={coords.x2 - Math.min(16, coords.width / 3)}
                    y2={coords.y2}
                    stroke={strokeColor}
                    strokeWidth={4.5}
                  />
                  <line
                    x1={coords.x2}
                    y1={coords.y2}
                    x2={coords.x2}
                    y2={coords.y2 - Math.min(16, coords.height / 3)}
                    stroke={strokeColor}
                    strokeWidth={4.5}
                  />

                  {/* Defect Label Pill */}
                  <rect
                    x={coords.x}
                    y={labelY - 16}
                    width={pillWidth}
                    height={pillHeight}
                    fill={isHighSeverity ? "#991B1B" : "#854D0E"}
                    rx="4"
                    ry="4"
                  />
                  <text
                    x={coords.x + pillPadding}
                    y={labelY}
                    fill="#FFFFFF"
                    fontSize="11"
                    fontWeight="bold"
                    fontFamily="sans-serif"
                  >
                    {textStr}
                  </text>
                </g>
              );
            })}
          </svg>
        )}

        {/* Overlay Controls Bar */}
        <div className="absolute top-3 right-3 flex items-center gap-2">
          {hasDetections && (
            <button
              type="button"
              onClick={() => setShowAnnotations(!showAnnotations)}
              className="px-2.5 py-1.5 rounded-lg text-xs font-bold bg-slate-900/85 hover:bg-slate-900 text-white backdrop-blur-xs flex items-center gap-1.5 border border-white/20 shadow-md transition-all"
              title={showAnnotations ? "Hide AI Bounding Boxes" : "Show AI Bounding Boxes"}
            >
              {showAnnotations ? (
                <>
                  <EyeOff className="w-3.5 h-3.5 text-amber-400" />
                  <span>Original Photo</span>
                </>
              ) : (
                <>
                  <Eye className="w-3.5 h-3.5 text-teal-400" />
                  <span>AI Overlay ({observations.length})</span>
                </>
              )}
            </button>
          )}

          <div className="px-2 py-1 rounded-lg text-[10px] font-bold bg-slate-900/80 text-white backdrop-blur-xs border border-white/10 hidden sm:flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-teal-400" />
            <span>YOLOv8 Vision</span>
          </div>
        </div>

        {/* Clean Fallback when no detections found */}
        {showAnnotations && !hasDetections && (
          <div className="absolute bottom-3 left-3 right-3 p-2.5 bg-slate-900/85 backdrop-blur-xs rounded-xl border border-white/15 text-white text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>No road defects detected with high confidence — routed to manual reviewer</span>
          </div>
        )}
      </div>

      {/* Observations Pill List & Model Provenance */}
      {showDetails && (
        <div className="space-y-2">
          {hasDetections ? (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-slate-500">Detections ({observations.length}):</span>
              {observations.map((obs, idx) => {
                const isHighSeverity =
                  obs.confidence > 0.85 || obs.label.toLowerCase().includes("pothole");
                return (
                  <span
                    key={idx}
                    onMouseEnter={() => setHoveredIdx(idx)}
                    onMouseLeave={() => setHoveredIdx(null)}
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                      hoveredIdx === idx
                        ? "ring-2 ring-offset-1 ring-slate-800"
                        : ""
                    } ${
                      isHighSeverity
                        ? "bg-red-50 text-red-800 border border-red-200"
                        : "bg-amber-50 text-amber-800 border border-amber-200"
                    }`}
                  >
                    <span
                      className={`w-2 h-2 rounded-full ${
                        isHighSeverity ? "bg-red-500" : "bg-amber-500"
                      }`}
                    />
                    <span>{obs.label}</span>
                    <span className="font-mono text-[11px] opacity-75">
                      {Math.round(obs.confidence * 100)}%
                    </span>
                  </span>
                );
              })}
            </div>
          ) : (
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-600 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#087F78]" />
                <span>Zero false-positive bounding boxes generated. Human inspection queue active.</span>
              </div>
              <Badge variant="neutral" size="sm">Manual Triage</Badge>
            </div>
          )}

          {/* Model Provenance Footer */}
          <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-100">
            <span className="font-mono">
              Model: {modelId} {latencyMs ? `· ${latencyMs}ms latency` : ""}
            </span>
            {requiresHumanReview && (
              <span className="flex items-center gap-1 text-[#087F78] font-semibold">
                <ShieldAlert className="w-3.5 h-3.5" />
                Human Review Governance Active
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
