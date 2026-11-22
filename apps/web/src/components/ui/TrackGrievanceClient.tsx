"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  Search,
  CheckCircle2,
  Clock,
  AlertCircle,
  MapPin,
  Calendar,
  ShieldCheck,
  ArrowRight,
  Copy,
  Check,
  Camera,
  RefreshCw,
  FileText,
} from "lucide-react";
import { apiClient } from "@/lib/api-client";

interface TimelineItem {
  status: string;
  timestamp: string;
  actor_title: string;
  public_summary?: string;
}

interface MediaItem {
  id: string;
  evidence_role: string;
  mime_type: string;
  view_url: string;
}

interface TrackedIssue {
  id: string;
  reference_number: string;
  category: string;
  status: string;
  priority: string;
  village_name?: string;
  ward_name?: string;
  public_latitude?: number;
  public_longitude?: number;
  created_at: string;
  resolved_at?: string;
  sla_status?: {
    is_overdue: boolean;
    remaining_hours?: number;
    hours_elapsed?: number;
  };
  timeline?: TimelineItem[];
  before_photos?: MediaItem[];
  after_photos?: MediaItem[];
  thumbnail_url?: string;
  after_thumbnail_url?: string;
  has_after_photo?: boolean;
  reporter_display_name?: string;
  assigned_worker_display_name?: string;
  work_completion_description?: string;
}

const LIFECYCLE_STEPS = [
  { key: "SUBMITTED", label: "Submitted" },
  { key: "UNDER_REVIEW", label: "Under Review" },
  { key: "ASSIGNED", label: "Assigned" },
  { key: "IN_PROGRESS", label: "In Progress" },
  { key: "REPAIR_REPORTED", label: "Repair Reported" },
  { key: "RESOLVED", label: "Verified & Resolved" },
];

export function TrackGrievanceClient({
  locale,
  initialId = "",
}: {
  locale: string;
  initialId?: string;
}) {
  const searchParams = useSearchParams();
  const queryId = searchParams?.get("id") || initialId;

  const [searchInput, setSearchInput] = useState(queryId);
  const [activeTrackingId, setActiveTrackingId] = useState(queryId);
  const [data, setData] = useState<TrackedIssue | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const fetchTracking = async (trackingRef: string) => {
    if (!trackingRef.trim()) return;
    setLoading(true);
    setError(null);

    const cleanRef = trackingRef.trim();
    try {
      const res = await apiClient.get<TrackedIssue>(`/public/track/${encodeURIComponent(cleanRef)}`);
      setData(res);
      setActiveTrackingId(cleanRef);
    } catch {
      try {
        // Fallback to /public/issues/{cleanRef}
        const fallbackRes = await apiClient.get<TrackedIssue>(`/public/issues/${encodeURIComponent(cleanRef)}`);
        setData(fallbackRes);
        setActiveTrackingId(cleanRef);
      } catch (err: any) {
        setError(`Complaint '${cleanRef}' could not be found. Please check your Tracking ID and try again.`);
        setData(null);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (queryId) {
      setSearchInput(queryId);
      fetchTracking(queryId);
    }
  }, [queryId]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchInput.trim()) {
      fetchTracking(searchInput);
    }
  };

  const handleCopy = () => {
    if (typeof window !== "undefined" && data) {
      navigator.clipboard.writeText(data.reference_number);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getCurrentStepIndex = (status: string) => {
    if (status === "RESOLVED") return 5;
    if (status === "REPAIR_REPORTED" || status === "AWAITING_VERIFICATION") return 4;
    if (status === "IN_PROGRESS") return 3;
    if (status === "ASSIGNED") return 2;
    if (status === "UNDER_REVIEW") return 1;
    return 0;
  };

  const currentStep = data ? getCurrentStepIndex(data.status) : 0;

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Top Search Card */}
      <div className="rounded-3xl border border-[#DCE5EE] bg-white p-6 sm:p-8 shadow-xs space-y-4">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-teal-50 text-[#087F78] text-xs font-bold border border-teal-200">
            <ShieldCheck className="w-3.5 h-3.5" />
            Official Public Verification Tracker
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-[#102B4E] tracking-tight">
            Track Grievance Lifecycle
          </h1>
          <p className="text-sm text-slate-500">
            Enter your official Tracking ID (e.g. <span className="font-mono font-bold text-slate-700">GS-2026-BEL-XXXX</span>) to audit real-time physical repair milestones.
          </p>
        </div>

        <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-3 pt-2">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Enter Tracking ID (e.g. GS-2026-BEL-0010)"
              className="w-full pl-10 pr-4 py-3 text-sm font-mono border border-slate-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-[#087F78] bg-slate-50/50"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !searchInput.trim()}
            className="px-6 py-3 rounded-2xl bg-[#087F78] text-white text-sm font-bold hover:bg-[#066B65] transition-all flex items-center justify-center gap-2 shadow-xs disabled:opacity-50 cursor-pointer"
          >
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            Track Now
          </button>
        </form>

        {/* Suggested Quick Reference Tags */}
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 pt-1">
          <span>Sample references:</span>
          {["GS-2026-07923", "GS-2026-04118", "GS-2026-09214"].map((ref) => (
            <button
              key={ref}
              type="button"
              onClick={() => {
                setSearchInput(ref);
                fetchTracking(ref);
              }}
              className="font-mono px-2 py-0.5 rounded-lg bg-slate-100 text-slate-700 hover:bg-teal-50 hover:text-teal-800 transition-colors cursor-pointer"
            >
              {ref}
            </button>
          ))}
        </div>
      </div>

      {/* Error Notice */}
      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50/80 p-5 flex items-start gap-3.5 text-sm text-red-800">
          <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <strong className="font-bold">Complaint Not Found</strong>
            <p className="text-xs text-red-700">{error}</p>
          </div>
        </div>
      )}

      {/* Active Tracked Issue Card */}
      {data && (
        <div className="rounded-3xl border border-[#DCE5EE] bg-white p-6 sm:p-8 shadow-xs space-y-8 animate-in fade-in duration-200">
          {/* Header Bar */}
          <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-slate-100">
            <div className="space-y-1.5">
              <div className="flex items-center gap-2.5">
                <span className="font-mono text-xl sm:text-2xl font-black text-[#102B4E]">
                  {data.reference_number}
                </span>
                <button
                  type="button"
                  onClick={handleCopy}
                  className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 cursor-pointer"
                  title="Copy Tracking ID"
                >
                  {copied ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
                </button>
                <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-teal-50 text-teal-800 border border-teal-200">
                  {data.category.replace("_", " ")}
                </span>
              </div>

              <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                {data.village_name && (
                  <span className="flex items-center gap-1 font-semibold text-slate-700">
                    <MapPin className="w-3.5 h-3.5 text-rose-500" />
                    {data.village_name} {data.ward_name ? `• ${data.ward_name}` : ""}
                  </span>
                )}
                <span className="flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5" />
                  Reported on {new Date(data.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>

            <div className="text-right">
              <span
                className={`inline-flex items-center px-4 py-1.5 rounded-full text-xs font-black uppercase tracking-wider ${
                  data.status === "RESOLVED"
                    ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                    : data.status === "IN_PROGRESS" || data.status === "REPAIR_REPORTED"
                    ? "bg-amber-100 text-amber-900 border border-amber-300"
                    : "bg-blue-100 text-blue-900 border border-blue-300"
                }`}
              >
                {data.status.replace("_", " ")}
              </span>
            </div>
          </div>

          {/* 6-Stage Progress Indicator */}
          <div className="space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Civic Milestone Progress
            </h3>

            <div className="grid grid-cols-2 sm:grid-cols-6 gap-2">
              {LIFECYCLE_STEPS.map((step, idx) => {
                const isPassed = idx <= currentStep;
                const isCurrent = idx === currentStep;

                return (
                  <div
                    key={step.key}
                    className={`rounded-2xl p-3 border text-center transition-all ${
                      isCurrent
                        ? "border-[#087F78] bg-teal-50/50 text-[#087F78] shadow-xs"
                        : isPassed
                        ? "border-emerald-200 bg-emerald-50/40 text-emerald-800"
                        : "border-slate-100 bg-slate-50/50 text-slate-400"
                    }`}
                  >
                    <div className="flex items-center justify-center mb-1.5">
                      {isPassed ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      ) : (
                        <Clock className="w-4 h-4 text-slate-300" />
                      )}
                    </div>
                    <span className="text-[11px] font-bold block leading-tight">{step.label}</span>
                    <span className="text-[9px] font-bold uppercase tracking-wider opacity-60">Step {idx + 1}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Photographic Evidence (Before & After) */}
          {((data.before_photos && data.before_photos.length > 0) ||
            (data.after_photos && data.after_photos.length > 0)) && (
            <div className="space-y-3 pt-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Camera className="w-3.5 h-3.5" />
                Physical Photographic Evidence
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Citizen Before Photo */}
                {data.before_photos && data.before_photos.length > 0 && (
                  <div className="rounded-2xl border border-slate-200 p-3 bg-slate-50 space-y-2">
                    <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-500 block">
                      Citizen Upload (Before)
                    </span>
                    <div className="aspect-video bg-slate-200 rounded-xl overflow-hidden flex items-center justify-center">
                      <img
                        src={data.before_photos[0].view_url}
                        alt="Issue Before Repair"
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = "none";
                        }}
                      />
                    </div>
                  </div>
                )}

                {/* Worker After Photo */}
                {data.after_photos && data.after_photos.length > 0 ? (
                  <div className="rounded-2xl border border-emerald-200 p-3 bg-emerald-50/50 space-y-2">
                    <span className="text-[10px] font-extrabold uppercase tracking-wider text-emerald-700 block">
                      Field Repair Proof (After)
                    </span>
                    <div className="aspect-video bg-emerald-100 rounded-xl overflow-hidden flex items-center justify-center">
                      <img
                        src={data.after_photos[0].view_url}
                        alt="Issue After Repair"
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = "none";
                        }}
                      />
                    </div>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-dashed border-slate-200 p-6 flex flex-col items-center justify-center text-center text-slate-400 text-xs">
                    <Clock className="w-6 h-6 mb-1 text-slate-300" />
                    <p className="font-semibold">Repair Verification Photo Pending</p>
                    <p className="text-[10px] text-slate-400">
                      Uploaded by field team upon task completion.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Timeline Events Log */}
          {data.timeline && data.timeline.length > 0 && (
            <div className="space-y-3 pt-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5" />
                Physical Audit Trail
              </h3>

              <div className="rounded-2xl border border-slate-200 divide-y divide-slate-100 overflow-hidden">
                {data.timeline.map((event, i) => (
                  <div key={i} className="p-3.5 flex items-start justify-between gap-4 text-xs">
                    <div className="space-y-0.5">
                      <span className="font-bold text-slate-800 block">
                        Status transitioned to: {event.status.replace("_", " ")}
                      </span>
                      {event.public_summary && (
                        <p className="text-slate-500 text-[11px]">{event.public_summary}</p>
                      )}
                      <span className="text-[10px] text-slate-400 font-semibold block">
                        Actor: {event.actor_title}
                      </span>
                    </div>
                    <span className="font-mono text-[10px] text-slate-400 shrink-0">
                      {new Date(event.timestamp).toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action Row */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-slate-100">
            <Link
              href={`/${locale}/report`}
              className="w-full sm:w-auto px-5 py-2.5 rounded-xl border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-bold text-center"
            >
              Report Another Issue
            </Link>

            <Link
              href={`/${locale}/public`}
              className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-[#087F78] text-white hover:bg-[#066B65] text-xs font-bold text-center flex items-center justify-center gap-1.5 shadow-xs"
            >
              Public Civic Works Dashboard
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
