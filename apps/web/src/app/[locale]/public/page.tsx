"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import {
  LayoutDashboard,
  Building2,
  MapPin,
  CheckCircle2,
  Clock,
  ShieldCheck,
  AlertCircle,
  Eye,
  RefreshCw,
  ArrowRight,
  Filter,
  Search,
  Lock,
  Wrench,
  FileText,
  Calendar,
  Sparkles,
  Camera,
  Coins,
  CheckCircle,
  X,
  ExternalLink,
} from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { LeafletMap, MapComplaint } from "@/components/ui/LeafletMap";
import { GramaSevaLogo } from "@/components/ui/GramaSevaLogo";

type PublicSection = "overview" | "gallery" | "village_progress" | "map";

interface PublicGalleryItem {
  id: string;
  reference_number: string;
  category: string;
  title: string;
  description: string;
  village_name: string;
  status: string;
  is_demo: boolean;
  sample_badge: string;
  before_photo_url: string;
  after_photo_url: string;
  verified_cost?: number;
  ai_summary?: string;
  submitted_at: string;
  resolved_at?: string;
}

const BELAGAVI_VILLAGES = [
  "Peeranwadi",
  "Kuttalawadi",
  "Zad-Shahapur",
  "Santibastawad",
  "Yellur",
  "Sulge (Yellur)",
  "Mandoli",
  "Waghawade",
  "Navage",
];

const getMediaUrl = (url?: string) => {
  if (!url) return "";
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  const origin = base.replace(/\/api\/v1\/?$/, "");
  return url.startsWith("/") ? `${origin}${url}` : `${base}/public/media/${url}/view`;
};

interface PublicMediaItem {
  id: string;
  evidence_role: string;
  mime_type: string;
  view_url: string;
}

interface PublicTimelineItem {
  status: string;
  timestamp: string;
  actor_title: string;
  public_summary?: string;
}

interface PublicIssue {
  id: string;
  reference_number: string;
  category: string;
  status: string;
  priority: string;
  description?: string;
  village_name?: string;
  ward_name?: string;
  public_latitude?: number;
  public_longitude?: number;
  submissions_count: number;
  approved_media_count: number;
  thumbnail_url?: string;
  after_thumbnail_url?: string;
  has_after_photo: boolean;
  reporter_display_name: string;
  assigned_worker_display_name?: string;
  estimated_cost?: number;
  proposed_cost?: number;
  verified_cost?: number;
  cost_status: string;
  work_completed_at?: string;
  created_at: string;
  resolved_at?: string;
}

interface PublicIssueDetail extends PublicIssue {
  timeline: PublicTimelineItem[];
  approved_media: PublicMediaItem[];
  before_photos: PublicMediaItem[];
  after_photos: PublicMediaItem[];
  work_completion_description?: string;
  work_performed?: string;
  materials_used?: string;
  labour_details?: string;
  materials_cost?: number;
  labour_cost?: number;
  other_expenses_cost?: number;
  cost_verification_remarks?: string;
  ai_observation_summary?: string;
  ai_visual_consistency_score?: number;
  pdo_officer_title?: string;
  verification_date?: string;
}

interface PublicAnalytics {
  total_unique_issues: number;
  total_submissions: number;
  open_issues: number;
  repair_reported_issues: number;
  resolved_issues: number;
  reopened_issues: number;
  overdue_issues: number;
  average_resolution_hours: number;
  by_village: Array<{
    village_name: string;
    issues_count: number;
    resolved_count: number;
    overdue_count: number;
  }>;
  by_category: Array<{
    category: string;
    count: number;
    resolved_count: number;
  }>;
}

export default function PublicDashboardPage() {
  const locale = useLocale();
  const [activeSection, setActiveSection] = useState<PublicSection>("overview");
  const [issues, setIssues] = useState<PublicIssue[]>([]);
  const [analytics, setAnalytics] = useState<PublicAnalytics | null>(null);
  const [galleryItems, setGalleryItems] = useState<PublicGalleryItem[]>([]);
  const [galleryCategory, setGalleryCategory] = useState<string>("ALL");
  const [isLoading, setIsLoading] = useState(true);

  // Detail Modal State
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null);
  const [issueDetail, setIssueDetail] = useState<PublicIssueDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Real Database Filters
  const [selectedVillage, setSelectedVillage] = useState<string>("ALL");
  const [selectedWard, setSelectedWard] = useState<string>("ALL");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");
  const [dateRange, setDateRange] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedVillage !== "ALL") params.append("village_name", selectedVillage);
      if (selectedWard !== "ALL") params.append("ward_name", selectedWard);
      if (selectedCategory !== "ALL") params.append("category", selectedCategory);
      if (selectedStatus !== "ALL") params.append("status", selectedStatus);
      if (dateRange !== "all") params.append("date_range", dateRange);
      if (searchQuery.trim()) params.append("search", searchQuery.trim());

      const url = `/public/issues${params.toString() ? `?${params.toString()}` : ""}`;

      const [analyticsData, issuesData, galleryData] = await Promise.allSettled([
        apiClient.get<PublicAnalytics>("/public/analytics"),
        apiClient.get<PublicIssue[]>(url),
        apiClient.get<PublicGalleryItem[]>("/public/gallery"),
      ]);

      if (analyticsData.status === "fulfilled" && analyticsData.value) {
        setAnalytics(analyticsData.value);
      }

      if (issuesData.status === "fulfilled" && issuesData.value) {
        setIssues(issuesData.value);
      }

      if (galleryData.status === "fulfilled" && galleryData.value) {
        setGalleryItems(galleryData.value);
      }
    } catch {
      // Handled cleanly
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedVillage, selectedWard, selectedCategory, selectedStatus, dateRange]);

  // Load detailed issue data when modal opens
  const openIssueDetail = async (issueId: string) => {
    setSelectedIssueId(issueId);
    setDetailLoading(true);
    try {
      const data = await apiClient.get<PublicIssueDetail>(`/public/issues/${issueId}`);
      setIssueDetail(data);
    } catch {
      // Fallback to list item if detail fetch fails
      const fallback = issues.find((i) => i.id === issueId);
      if (fallback) {
        setIssueDetail({
          ...fallback,
          timeline: [],
          approved_media: [],
          before_photos: [],
          after_photos: [],
        });
      }
    } finally {
      setDetailLoading(false);
    }
  };

  const closeIssueDetail = () => {
    setSelectedIssueId(null);
    setIssueDetail(null);
  };

  // Map representation of complaints
  const publicMapComplaints: MapComplaint[] = issues
    .filter((i) => typeof i.public_latitude === "number" && typeof i.public_longitude === "number")
    .map((i) => ({
      id: i.id,
      reference_number: i.reference_number,
      category: i.category,
      status: i.status,
      latitude: i.public_latitude!,
      longitude: i.public_longitude!,
      priority: i.priority,
      village_name: i.village_name,
    }));

  const navItems = [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "gallery", label: "Before & After Gallery", icon: Camera },
    { id: "village_progress", label: "Village Progress", icon: Building2 },
    { id: "map", label: "Public Map", icon: MapPin },
  ];

  // Helper for status badge styling and readable labels
  const getStatusBadge = (statusStr: string) => {
    switch (statusStr) {
      case "SUBMITTED":
        return { label: "New", bg: "bg-blue-100 text-blue-800 border-blue-200" };
      case "UNDER_REVIEW":
        return { label: "Under Review", bg: "bg-indigo-100 text-indigo-800 border-indigo-200" };
      case "ASSIGNED":
        return { label: "Assigned", bg: "bg-purple-100 text-purple-800 border-purple-200" };
      case "IN_PROGRESS":
        return { label: "In Progress", bg: "bg-sky-100 text-sky-800 border-sky-200" };
      case "REPAIR_REPORTED":
      case "AWAITING_VERIFICATION":
        return { label: "Awaiting Verification", bg: "bg-amber-100 text-amber-800 border-amber-200" };
      case "RESOLVED":
        return { label: "Resolved", bg: "bg-emerald-100 text-emerald-800 border-emerald-200" };
      case "REOPENED":
      case "CORRECTION_REQUIRED":
        return { label: "Correction Required", bg: "bg-rose-100 text-rose-800 border-rose-200" };
      default:
        return { label: statusStr.replace("_", " "), bg: "bg-slate-100 text-slate-800 border-slate-200" };
    }
  };

  // Format expenditure text cleanly without assuming ₹0
  const getExpenditureDisplay = (item: PublicIssue) => {
    if (item.cost_status === "VERIFIED" && typeof item.verified_cost === "number" && item.verified_cost > 0) {
      return {
        text: `₹${item.verified_cost.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
        sub: "Verified Expenditure",
        badgeBg: "bg-emerald-50 text-emerald-700 border-emerald-200",
      };
    }
    if (item.cost_status === "PROPOSED" || item.status === "REPAIR_REPORTED" || item.status === "AWAITING_VERIFICATION") {
      return {
        text: "Cost verification pending",
        sub: "Awaiting PDO audit",
        badgeBg: "bg-amber-50 text-amber-700 border-amber-200",
      };
    }
    return {
      text: "Cost information not available",
      sub: "No cost recorded",
      badgeBg: "bg-slate-50 text-slate-500 border-slate-200",
    };
  };

  return (
    <div className="min-h-screen bg-[#F4F8FC] flex flex-col">
      {/* 1. MAIN PAGE HEADING & BELAGAVI TALUK CONTEXT */}
      <div className="bg-white border-b border-[#DCE5EE] px-4 sm:px-6 lg:px-8 pt-8 pb-6">
        <div className="max-w-[1440px] mx-auto space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <GramaSevaLogo size="sm" inverted={false} />
                <span className="h-4 w-px bg-slate-200" />
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-extrabold uppercase bg-[#087F78]/10 text-[#087F78] border border-[#087F78]/25">
                  Belagavi Taluk Administration
                </span>
                <span className="hidden sm:inline-block px-2 py-0.5 rounded-full text-[11px] font-bold bg-slate-100 text-slate-600">
                  9 Gram Panchayats
                </span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-black text-[#102B4E] tracking-tight">
                Public Civic Works & Complaint Tracker
              </h1>
              <p className="text-xs sm:text-sm text-[#40536B] mt-1 max-w-2xl">
                Explore reported civic issues, follow village development work, and view verified resolution records.
              </p>
            </div>

            <button
              type="button"
              onClick={fetchData}
              disabled={isLoading}
              className="self-start md:self-auto px-4 py-2 rounded-xl bg-white hover:bg-slate-50 text-xs font-bold text-[#102B4E] border border-[#DCE5EE] flex items-center gap-2 shadow-2xs transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-[#087F78]" : "text-[#40536B]"}`} />
              <span>Refresh Records</span>
            </button>
          </div>

          {/* 2. BELAGAVI TALUK VILLAGE FILTERS & SEARCH AREA */}
          <div className="bg-[#F8FAFC] border border-[#DCE5EE] rounded-2xl p-4 space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2.5 text-xs">
              {/* Village Filter */}
              <div>
                <label className="block text-[10px] font-bold text-[#40536B] uppercase mb-1">
                  Village / Gram Panchayat
                </label>
                <select
                  value={selectedVillage}
                  onChange={(e) => setSelectedVillage(e.target.value)}
                  className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl bg-white font-semibold text-[#102B4E] focus:outline-none focus:ring-1 focus:ring-[#087F78]"
                >
                  <option value="ALL">All 9 Villages</option>
                  {BELAGAVI_VILLAGES.map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </select>
              </div>

              {/* Ward Filter */}
              <div>
                <label className="block text-[10px] font-bold text-[#40536B] uppercase mb-1">
                  Ward
                </label>
                <select
                  value={selectedWard}
                  onChange={(e) => setSelectedWard(e.target.value)}
                  className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl bg-white font-semibold text-[#102B4E] focus:outline-none focus:ring-1 focus:ring-[#087F78]"
                >
                  <option value="ALL">All Wards</option>
                  <option value="Ward 1">Ward 1</option>
                  <option value="Ward 2">Ward 2</option>
                  <option value="Ward 3">Ward 3</option>
                  <option value="Ward 4">Ward 4</option>
                </select>
              </div>

              {/* Category Filter */}
              <div>
                <label className="block text-[10px] font-bold text-[#40536B] uppercase mb-1">
                  Category
                </label>
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl bg-white font-semibold text-[#102B4E] focus:outline-none focus:ring-1 focus:ring-[#087F78]"
                >
                  <option value="ALL">All Categories</option>
                  <option value="road_damage">Road Damage & Potholes</option>
                  <option value="water_leak">Drinking Water & Leaks</option>
                  <option value="garbage">Solid Waste & Garbage</option>
                  <option value="drainage">Drainage & Waterlogging</option>
                  <option value="streetlight">Streetlight Problems</option>
                  <option value="public_facility">Public Facilities & Sanitation</option>
                  <option value="other">Other Civic Complaints</option>
                </select>
              </div>

              {/* Status Filter */}
              <div>
                <label className="block text-[10px] font-bold text-[#40536B] uppercase mb-1">
                  Status
                </label>
                <select
                  value={selectedStatus}
                  onChange={(e) => setSelectedStatus(e.target.value)}
                  className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl bg-white font-semibold text-[#102B4E] focus:outline-none focus:ring-1 focus:ring-[#087F78]"
                >
                  <option value="ALL">All Statuses</option>
                  <option value="NEW">New</option>
                  <option value="UNDER_REVIEW">Under Review</option>
                  <option value="ASSIGNED">Assigned</option>
                  <option value="IN_PROGRESS">In Progress</option>
                  <option value="AWAITING_VERIFICATION">Awaiting Verification</option>
                  <option value="RESOLVED">Resolved</option>
                  <option value="REOPENED">Reopened</option>
                </select>
              </div>

              {/* Date Range Filter */}
              <div>
                <label className="block text-[10px] font-bold text-[#40536B] uppercase mb-1">
                  Date Range
                </label>
                <select
                  value={dateRange}
                  onChange={(e) => setDateRange(e.target.value)}
                  className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl bg-white font-semibold text-[#102B4E] focus:outline-none focus:ring-1 focus:ring-[#087F78]"
                >
                  <option value="all">All Time</option>
                  <option value="7d">Last 7 Days</option>
                  <option value="30d">Last 30 Days</option>
                  <option value="90d">Last 90 Days</option>
                  <option value="1y">Past Year</option>
                </select>
              </div>

              {/* Search Box */}
              <div>
                <label className="block text-[10px] font-bold text-[#40536B] uppercase mb-1">
                  Search Tracking ID / Keywords
                </label>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    fetchData();
                  }}
                  className="relative"
                >
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="e.g. GS-2026 or pothole"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-8 pr-3 py-2 border border-[#DCE5EE] rounded-xl bg-white text-xs focus:outline-none focus:ring-1 focus:ring-[#087F78]"
                  />
                </form>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 3. CLEAN THREE-SECTION SECONDARY NAVIGATION */}
      <div className="bg-white border-b border-[#DCE5EE] px-4 sm:px-6 lg:px-8 sticky top-16 z-20 shadow-2xs">
        <div className="max-w-[1440px] mx-auto flex items-center space-x-2 py-2.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setActiveSection(item.id as PublicSection)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all whitespace-nowrap ${
                  isActive
                    ? "bg-[#087F78] text-white shadow-2xs font-bold"
                    : "text-[#40536B] hover:text-[#102B4E] hover:bg-[#F4F8FC]"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-white" : "text-[#087F78]"}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* 4. MAIN CONTENT CONTAINER */}
      <div className="flex-1 max-w-[1440px] w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        {/* SECTION 1: OVERVIEW & RESPONSIVE COMPLAINT CARDS */}
        {activeSection === "overview" && (
          <div className="space-y-6">
            {/* KPI Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="bg-white p-5 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                <p className="text-[11px] font-bold text-[#40536B] uppercase">Total Complaints</p>
                <p className="text-3xl font-black text-[#102B4E]">
                  {analytics?.total_unique_issues ?? issues.length}
                </p>
                <p className="text-[10px] text-slate-500">Citizen submitted issues in Belagavi Taluk</p>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                <p className="text-[11px] font-bold text-[#40536B] uppercase">In Progress</p>
                <p className="text-3xl font-black text-sky-700">
                  {analytics?.open_issues ?? issues.filter((i) => i.status === "IN_PROGRESS").length}
                </p>
                <p className="text-[10px] text-slate-500">Field work actively underway</p>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                <p className="text-[11px] font-bold text-[#40536B] uppercase">Awaiting Verification</p>
                <p className="text-3xl font-black text-amber-600">
                  {analytics?.repair_reported_issues ??
                    issues.filter((i) => i.status === "REPAIR_REPORTED" || i.status === "AWAITING_VERIFICATION").length}
                </p>
                <p className="text-[10px] text-slate-500">Completion proof pending PDO audit</p>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                <p className="text-[11px] font-bold text-[#40536B] uppercase">Verified Resolved</p>
                <p className="text-3xl font-black text-emerald-600">
                  {analytics?.resolved_issues ?? issues.filter((i) => i.status === "RESOLVED").length}
                </p>
                <p className="text-[10px] text-slate-500">Independently approved by village PDO</p>
              </div>
            </div>

            {/* Complaint Cards Section Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-2">
              <div>
                <h2 className="text-lg font-black text-[#102B4E]">Community Complaints & Works Directory</h2>
                <p className="text-xs text-[#40536B]">
                  Showing {issues.length} {issues.length === 1 ? "record" : "records"} matching your selected filters.
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <ShieldCheck className="w-4 h-4 text-[#087F78]" />
                <span>All coordinates generalized (~100m) for citizen privacy</span>
              </div>
            </div>

            {/* Empty State */}
            {issues.length === 0 && (
              <div className="bg-white rounded-3xl border border-[#DCE5EE] p-12 text-center space-y-3 shadow-2xs">
                <div className="w-12 h-12 rounded-2xl bg-teal-50 text-[#087F78] flex items-center justify-center mx-auto">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
                <h3 className="text-base font-bold text-[#102B4E]">No public complaints available yet</h3>
                <p className="text-xs text-[#40536B] max-w-md mx-auto">
                  Citizen-reported issues will appear here when eligible.
                </p>
                {(selectedVillage !== "ALL" || selectedCategory !== "ALL" || selectedStatus !== "ALL" || searchQuery) && (
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedVillage("ALL");
                      setSelectedCategory("ALL");
                      setSelectedStatus("ALL");
                      setSearchQuery("");
                    }}
                    className="text-xs font-bold text-[#087F78] hover:underline pt-2 block mx-auto"
                  >
                    Reset all filters
                  </button>
                )}
              </div>
            )}

            {/* RESPONSIVE COMPLAINT CARDS GRID */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {issues.map((item) => {
                const statusMeta = getStatusBadge(item.status);
                const costInfo = getExpenditureDisplay(item);
                return (
                  <div
                    key={item.id}
                    className="bg-white rounded-3xl border border-[#DCE5EE] shadow-2xs hover:shadow-md transition-all flex flex-col overflow-hidden group"
                  >
                    {/* Card Thumbnail with Aspect Ratio */}
                    <div className="relative aspect-video w-full bg-slate-100 overflow-hidden border-b border-[#DCE5EE]">
                      {item.thumbnail_url ? (
                        <img
                          src={getMediaUrl(item.thumbnail_url)}
                          alt={item.category}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                          onError={(e) => {
                            (e.target as HTMLElement).style.display = "none";
                          }}
                        />
                      ) : (
                        <div className="w-full h-full flex flex-col items-center justify-center gap-1.5 text-slate-400 p-4">
                          <Camera className="w-8 h-8 stroke-1" />
                          <span className="text-[11px] font-semibold capitalize text-slate-500">
                            {item.category.replace("_", " ")}
                          </span>
                        </div>
                      )}

                      {/* Top Badges */}
                      <div className="absolute top-3 left-3 right-3 flex items-center justify-between gap-2 pointer-events-none">
                        <span className="px-2.5 py-1 rounded-lg text-[10px] font-mono font-black bg-white/95 text-[#102B4E] shadow-xs backdrop-blur-xs">
                          {item.reference_number}
                        </span>
                        <span
                          className={`px-2.5 py-1 rounded-lg text-[10px] font-bold border shadow-xs backdrop-blur-xs ${statusMeta.bg}`}
                        >
                          {statusMeta.label}
                        </span>
                      </div>

                      {/* Before / After Available Indicator */}
                      {item.has_after_photo && (
                        <div className="absolute bottom-2.5 right-3 px-2 py-0.5 rounded-md text-[9px] font-extrabold uppercase bg-emerald-600 text-white shadow-xs flex items-center gap-1">
                          <Sparkles className="w-3 h-3" />
                          <span>Before & After Proof</span>
                        </div>
                      )}
                    </div>

                    {/* Card Content */}
                    <div className="p-5 flex-1 flex flex-col justify-between space-y-4">
                      <div className="space-y-2">
                        {/* Category & Date */}
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-extrabold text-[#087F78] capitalize">
                            {item.category.replace("_", " ")}
                          </span>
                          <span className="text-[11px] text-slate-500 flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {new Date(item.created_at).toLocaleDateString("en-IN", {
                              day: "numeric",
                              month: "short",
                              year: "numeric",
                            })}
                          </span>
                        </div>

                        {/* Description */}
                        <p className="text-xs text-[#102B4E] font-medium line-clamp-2 leading-relaxed">
                          {item.description || "Civic infrastructure repair logged in Gram Panchayat jurisdiction."}
                        </p>

                        {/* Village & Location Details */}
                        <div className="pt-1 space-y-1 text-[11px] text-[#40536B]">
                          <p className="font-semibold text-[#102B4E] flex items-center gap-1.5 truncate">
                            <MapPin className="w-3.5 h-3.5 text-[#087F78] shrink-0" />
                            <span>
                              {item.village_name || "Belagavi Village"}
                              {item.ward_name ? ` • ${item.ward_name}` : ""}
                            </span>
                          </p>
                          <p className="text-[10px] text-slate-400 pl-5">
                            📍 Centroid: {item.public_latitude ? `${item.public_latitude}, ${item.public_longitude}` : "Belagavi Taluk"}
                          </p>
                        </div>
                      </div>

                      {/* Metadata: Reporter & Cost */}
                      <div className="pt-3 border-t border-[#DCE5EE] space-y-2 text-xs">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-slate-500">Reported By:</span>
                          <span className="font-bold text-[#102B4E] flex items-center gap-1">
                            <ShieldCheck className="w-3.5 h-3.5 text-[#087F78]" />
                            {item.reporter_display_name}
                          </span>
                        </div>

                        {item.assigned_worker_display_name && (
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="text-slate-500">Field Worker:</span>
                            <span className="font-semibold text-[#102B4E]">
                              {item.assigned_worker_display_name}
                            </span>
                          </div>
                        )}

                        {/* Verified Expenditure Badge */}
                        <div className={`p-2.5 rounded-xl border flex items-center justify-between ${costInfo.badgeBg}`}>
                          <div className="flex items-center gap-1.5">
                            <Coins className="w-4 h-4 shrink-0" />
                            <span className="text-[10px] font-bold uppercase">{costInfo.sub}</span>
                          </div>
                          <span className="font-black text-xs">{costInfo.text}</span>
                        </div>

                        {/* View Details Action */}
                        <button
                          type="button"
                          onClick={() => openIssueDetail(item.id)}
                          className="w-full mt-2 py-2 rounded-xl bg-[#087F78]/10 hover:bg-[#087F78] text-[#087F78] hover:text-white font-bold text-xs flex items-center justify-center gap-1.5 transition-all"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>View Public Details & Evidence</span>
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* SECTION: BEFORE & AFTER VERIFICATION GALLERY (PART 7) */}
        {activeSection === "gallery" && (
          <div className="space-y-6 animate-in fade-in duration-200">
            {/* Header & Category Filter */}
            <div className="bg-white p-6 rounded-3xl border border-[#DCE5EE] shadow-2xs space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-teal-50 text-[#087F78] text-xs font-bold border border-teal-200">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    Verified Photographic Evidence
                  </div>
                  <h2 className="text-xl sm:text-2xl font-black text-[#102B4E] tracking-tight">
                    Before & After Remediation Gallery
                  </h2>
                  <p className="text-xs sm:text-sm text-[#40536B]">
                    Side-by-side photographic records demonstrating physical civic repairs across Karnataka villages. Demonstration records are clearly marked <span className="font-bold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded">DEMO / SAMPLE</span> and isolated from operational counts.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <span className="px-3 py-1.5 rounded-xl bg-teal-50 border border-teal-200 text-[#087F78] font-bold text-xs">
                    📸 {galleryItems.length} Solved Examples
                  </span>
                </div>
              </div>

              {/* Category Filter Chips */}
              <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100">
                <span className="text-xs font-bold text-slate-500 mr-1">Category:</span>
                {[
                  { id: "ALL", label: "All Works" },
                  { id: "road_damage", label: "Road Potholes" },
                  { id: "garbage", label: "Garbage & Waste" },
                  { id: "waterlogging", label: "Waterlogging" },
                  { id: "street_light", label: "Streetlights" },
                  { id: "drainage", label: "Drainage" },
                  { id: "public_sanitation", label: "Public Sanitation" },
                ].map((cat) => {
                  const isActive = galleryCategory === cat.id;
                  return (
                    <button
                      key={cat.id}
                      type="button"
                      onClick={() => setGalleryCategory(cat.id)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                        isActive
                          ? "bg-[#087F78] text-white shadow-2xs"
                          : "bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-200"
                      }`}
                    >
                      {cat.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Gallery Cards Grid */}
            {galleryItems.length === 0 ? (
              <div className="bg-white rounded-3xl border border-[#DCE5EE] p-12 text-center space-y-3 shadow-2xs">
                <div className="w-12 h-12 rounded-2xl bg-teal-50 text-[#087F78] flex items-center justify-center mx-auto">
                  <ShieldCheck className="w-6 h-6" />
                </div>
                <h3 className="text-base font-bold text-[#102B4E]">No verified resolution records yet</h3>
                <p className="text-xs text-[#40536B] max-w-md mx-auto">
                  As field workers complete repairs and Village PDOs independently verify completion photographs, verified before-and-after work records will be showcased here.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {galleryItems
                .filter((item) => galleryCategory === "ALL" || item.category === galleryCategory)
                .map((item) => (
                  <div
                    key={item.id}
                    className="bg-white rounded-3xl border border-[#DCE5EE] p-5 sm:p-6 shadow-2xs space-y-4 flex flex-col justify-between hover:shadow-md transition-shadow"
                  >
                    <div className="space-y-4">
                      {/* Top Badges */}
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider bg-teal-50 text-teal-800 border border-teal-200">
                            {item.category.replace("_", " ")}
                          </span>
                          <span className="font-mono text-xs font-black text-slate-600">
                            {item.reference_number}
                          </span>
                        </div>

                        {item.is_demo ? (
                          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-amber-100 text-amber-900 border border-amber-300">
                            DEMO / SAMPLE RECORD
                          </span>
                        ) : (
                          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-emerald-100 text-emerald-800 border border-emerald-300">
                            OFFICIAL CITIZEN REPORT
                          </span>
                        )}
                      </div>

                      {/* Title & Location */}
                      <div>
                        <h3 className="font-extrabold text-base text-[#102B4E] leading-snug">
                          {item.title}
                        </h3>
                        <p className="text-xs text-slate-500 flex items-center gap-1 mt-1">
                          <MapPin className="w-3.5 h-3.5 text-rose-500" />
                          {item.village_name}, Belagavi Taluk
                        </p>
                      </div>

                      {/* Side-by-Side Photographic Proof */}
                      <div className="grid grid-cols-2 gap-3 pt-1">
                        {/* Before */}
                        <div className="rounded-2xl border border-rose-200 p-2 bg-rose-50/40 space-y-1.5">
                          <span className="text-[9px] font-extrabold uppercase tracking-wider text-rose-700 block">
                            CITIZEN EVIDENCE (BEFORE)
                          </span>
                          <div className="aspect-4/3 bg-slate-200 rounded-xl overflow-hidden flex items-center justify-center">
                            <img
                              src={item.before_photo_url}
                              alt="Before Repair"
                              className="w-full h-full object-cover hover:scale-105 transition-transform"
                            />
                          </div>
                        </div>

                        {/* After */}
                        <div className="rounded-2xl border border-emerald-200 p-2 bg-emerald-50/40 space-y-1.5">
                          <span className="text-[9px] font-extrabold uppercase tracking-wider text-emerald-700 block">
                            VERIFIED REPAIR (AFTER)
                          </span>
                          <div className="aspect-4/3 bg-slate-200 rounded-xl overflow-hidden flex items-center justify-center">
                            <img
                              src={item.after_photo_url}
                              alt="After Repair"
                              className="w-full h-full object-cover hover:scale-105 transition-transform"
                            />
                          </div>
                        </div>
                      </div>

                      {/* Description & AI Summary */}
                      <div className="space-y-2 text-xs">
                        <p className="text-slate-600 text-xs leading-relaxed">
                          {item.description}
                        </p>

                        {item.ai_summary && (
                          <div className="rounded-xl border border-teal-200 bg-teal-50/50 p-2.5 flex items-start gap-2">
                            <Sparkles className="w-4 h-4 text-[#087F78] shrink-0 mt-0.5" />
                            <p className="text-[11px] text-teal-900 leading-snug">
                              <strong className="font-bold">AI Advisory Summary:</strong> {item.ai_summary}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Card Footer: Cost & Lifecycle Link */}
                    <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                      <div>
                        {typeof item.verified_cost === "number" ? (
                          <span className="text-slate-700">
                            Verified Cost: <strong className="text-emerald-700 font-bold">₹{item.verified_cost.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</strong>
                          </span>
                        ) : (
                          <span className="text-slate-400">Routine Maintenance</span>
                        )}
                      </div>

                      <Link
                        href={`/${locale}/track/${item.reference_number}`}
                        className="font-bold text-[#087F78] hover:underline flex items-center gap-1"
                      >
                        Track Milestone Audit →
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* SECTION 2: VILLAGE PROGRESS TABLE */}
        {activeSection === "village_progress" && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-extrabold text-[#102B4E]">Belagavi Taluk Village Progress Index</h2>
              <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                Resolution performance broken down across the 9 Gram Panchayats. No fabricated scores; computed directly from database records.
              </p>
            </div>

            <div className="bg-white rounded-3xl border border-[#DCE5EE] shadow-2xs overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#F8FAFC] border-b border-[#DCE5EE] text-[#40536B] font-bold uppercase tracking-wider">
                    <tr>
                      <th className="py-3.5 px-5">Gram Panchayat</th>
                      <th className="py-3.5 px-4 text-center">Total Reported</th>
                      <th className="py-3.5 px-4 text-center">Verified Resolved</th>
                      <th className="py-3.5 px-4 text-center">In Progress</th>
                      <th className="py-3.5 px-5">Resolution Performance</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#DCE5EE]">
                    {BELAGAVI_VILLAGES.map((vName) => {
                      const vStats = analytics?.by_village?.find((b) => b.village_name.toLowerCase().includes(vName.toLowerCase())) || {
                        issues_count: issues.filter((i) => i.village_name?.toLowerCase().includes(vName.toLowerCase())).length,
                        resolved_count: issues.filter((i) => i.village_name?.toLowerCase().includes(vName.toLowerCase()) && i.status === "RESOLVED").length,
                        overdue_count: 0,
                      };
                      const inProg = issues.filter(
                        (i) => i.village_name?.toLowerCase().includes(vName.toLowerCase()) && i.status === "IN_PROGRESS"
                      ).length;
                      const pct = vStats.issues_count > 0 ? Math.round((vStats.resolved_count / vStats.issues_count) * 100) : 0;

                      return (
                        <tr key={vName} className="hover:bg-[#F4F8FC]/60 transition-colors">
                          <td className="py-4 px-5 font-bold text-[#102B4E] flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-[#087F78]" />
                            <span>{vName}</span>
                          </td>
                          <td className="py-4 px-4 text-center font-semibold text-[#102B4E]">{vStats.issues_count}</td>
                          <td className="py-4 px-4 text-center font-bold text-emerald-700">{vStats.resolved_count}</td>
                          <td className="py-4 px-4 text-center font-semibold text-sky-700">{inProg}</td>
                          <td className="py-4 px-5">
                            <div className="flex items-center gap-3">
                              <div className="w-36 h-2 rounded-full bg-slate-100 overflow-hidden">
                                <div className="h-full bg-[#087F78] transition-all" style={{ width: `${pct}%` }} />
                              </div>
                              <span className="font-bold text-[#102B4E]">{pct}%</span>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* SECTION 3: PUBLIC OPENSTREETMAP */}
        {activeSection === "map" && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-extrabold text-[#102B4E]">Public Infrastructure Map</h2>
                <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                  Interactive OpenStreetMap with generalized ~100m coordinates protecting citizen home locations.
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <span className="px-3 py-1 rounded-xl bg-white border border-[#DCE5EE] text-[#102B4E] font-semibold">
                  📍 {publicMapComplaints.length} Geotagged Records
                </span>
              </div>
            </div>

            {/* Leaflet Map Component */}
            <div className="bg-white rounded-3xl border border-[#DCE5EE] p-2 shadow-2xs overflow-hidden">
              <LeafletMap
                height="620px"
                complaints={publicMapComplaints}
                generalizeCoordinates={true}
                selectedComplaintId={selectedIssueId || undefined}
                onSelectComplaint={(c) => openIssueDetail(c.id)}
              />
            </div>
          </div>
        )}
      </div>

      {/* 5. PUBLIC ISSUE DETAILS MODAL (BEFORE/AFTER PROOF, COSTS, AI OBSERVATIONS) */}
      {selectedIssueId && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl max-w-3xl w-full p-6 sm:p-8 shadow-2xl border border-[#DCE5EE] space-y-6 text-xs max-h-[90vh] overflow-y-auto animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="flex items-start justify-between gap-4 pb-4 border-b border-[#DCE5EE]">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-sm font-black text-[#102B4E]">
                    {issueDetail?.reference_number}
                  </span>
                  {issueDetail && (
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${
                        getStatusBadge(issueDetail.status).bg
                      }`}
                    >
                      {getStatusBadge(issueDetail.status).label}
                    </span>
                  )}
                </div>
                <p className="text-xs font-semibold text-[#087F78] capitalize">
                  {issueDetail?.category.replace("_", " ")} • {issueDetail?.village_name || "Belagavi Village"}
                  {issueDetail?.ward_name ? ` • ${issueDetail.ward_name}` : ""}
                </p>
              </div>

              <button
                type="button"
                onClick={closeIssueDetail}
                className="w-8 h-8 rounded-full hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-700 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {detailLoading ? (
              <div className="py-12 text-center text-slate-400 flex flex-col items-center gap-2">
                <RefreshCw className="w-6 h-6 animate-spin text-[#087F78]" />
                <span>Loading verified public record...</span>
              </div>
            ) : issueDetail ? (
              <div className="space-y-6">
                {/* BEFORE & AFTER PHOTOGRAPHS */}
                <div className="space-y-2">
                  <h3 className="font-extrabold text-sm text-[#102B4E] flex items-center gap-1.5">
                    <Camera className="w-4 h-4 text-[#087F78]" />
                    <span>Photographic Evidence & Physical Verification</span>
                  </h3>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {/* Before Photo */}
                    <div className="rounded-2xl border border-[#DCE5EE] bg-slate-50 overflow-hidden">
                      <div className="bg-[#102B4E] text-white px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider flex items-center justify-between">
                        <span>Original Citizen Report</span>
                        <span className="text-slate-300">Before</span>
                      </div>
                      <div className="aspect-video w-full bg-slate-100 flex items-center justify-center">
                        {issueDetail.thumbnail_url ? (
                          <img
                            src={issueDetail.thumbnail_url}
                            alt="Before repair proof"
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <span className="text-slate-400 font-medium text-xs">No before image archived</span>
                        )}
                      </div>
                    </div>

                    {/* After Photo */}
                    <div className="rounded-2xl border border-[#DCE5EE] bg-slate-50 overflow-hidden">
                      <div className="bg-[#087F78] text-white px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider flex items-center justify-between">
                        <span>Worker Completed Fix</span>
                        <span className="text-teal-200">After</span>
                      </div>
                      <div className="aspect-video w-full bg-slate-100 flex items-center justify-center">
                        {issueDetail.after_thumbnail_url ? (
                          <img
                            src={issueDetail.after_thumbnail_url}
                            alt="After repair proof"
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="p-4 text-center text-slate-400 text-xs">
                            <Clock className="w-5 h-5 mx-auto mb-1 opacity-60" />
                            <span>Work completion photo pending upload</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* AI BEFORE/AFTER ADVISORY OBSERVATIONS */}
                {issueDetail.ai_observation_summary && (
                  <div className="p-4 rounded-2xl bg-teal-50/70 border border-teal-200/80 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 text-[#087F78] font-bold">
                        <Sparkles className="w-4 h-4" />
                        <span>AI Visual Difference Observation (Advisory Only)</span>
                      </div>
                      {typeof issueDetail.ai_visual_consistency_score === "number" && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-teal-100 text-[#087F78]">
                          {Math.round(issueDetail.ai_visual_consistency_score * 100)}% Scene Consistency
                        </span>
                      )}
                    </div>
                    <p className="text-slate-700 leading-relaxed">
                      {issueDetail.ai_observation_summary}
                    </p>
                    <p className="text-[10px] text-slate-500 italic">
                      *Note: AI output is strictly advisory. An authorized Village Panchayat Development Officer (PDO) must physically verify repairs and approve expenditures.
                    </p>
                  </div>
                )}

                {/* COMPLAINT DESCRIPTION */}
                <div className="p-4 rounded-2xl bg-[#F8FAFC] border border-[#DCE5EE] space-y-1">
                  <p className="font-bold text-[#102B4E]">Reported Issue Description:</p>
                  <p className="text-[#40536B] leading-relaxed">
                    {issueDetail.description || "Civic infrastructure issue recorded by resident."}
                  </p>
                </div>

                {/* WORK PERFORMED & WORKER SUMMARY */}
                {issueDetail.work_performed && (
                  <div className="p-4 rounded-2xl bg-[#F8FAFC] border border-[#DCE5EE] space-y-2">
                    <p className="font-bold text-[#102B4E]">Worker Completion Report:</p>
                    <p className="text-[#40536B] leading-relaxed">{issueDetail.work_performed}</p>
                    {issueDetail.materials_used && (
                      <p className="text-xs text-slate-600">
                        <strong>Materials Used:</strong> {issueDetail.materials_used}
                      </p>
                    )}
                    {issueDetail.labour_details && (
                      <p className="text-xs text-slate-600">
                        <strong>Labour Details:</strong> {issueDetail.labour_details}
                      </p>
                    )}
                  </div>
                )}

                {/* COST AND EXPENDITURE BREAKDOWN */}
                <div className="p-4 rounded-2xl bg-white border border-[#DCE5EE] space-y-3">
                  <h4 className="font-bold text-sm text-[#102B4E] flex items-center gap-1.5">
                    <Coins className="w-4 h-4 text-[#087F78]" />
                    <span>Civic Works Expenditure & Cost Transparency</span>
                  </h4>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                      <p className="text-[10px] font-bold text-slate-500 uppercase">Estimated Budget</p>
                      <p className="text-base font-black text-[#102B4E] mt-0.5">
                        {typeof issueDetail.estimated_cost === "number" && issueDetail.estimated_cost > 0
                          ? `₹${issueDetail.estimated_cost.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`
                          : "Not recorded"}
                      </p>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                      <p className="text-[10px] font-bold text-slate-500 uppercase">Worker Proposed Cost</p>
                      <p className="text-base font-black text-amber-700 mt-0.5">
                        {typeof issueDetail.proposed_cost === "number" && issueDetail.proposed_cost > 0
                          ? `₹${issueDetail.proposed_cost.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`
                          : "Pending submission"}
                      </p>
                    </div>

                    <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200">
                      <p className="text-[10px] font-bold text-emerald-800 uppercase">Verified Final Expenditure</p>
                      <p className="text-base font-black text-emerald-700 mt-0.5">
                        {issueDetail.cost_status === "VERIFIED" && typeof issueDetail.verified_cost === "number"
                          ? `₹${issueDetail.verified_cost.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`
                          : "Cost verification pending"}
                      </p>
                    </div>
                  </div>

                  {issueDetail.cost_verification_remarks && (
                    <div className="p-2.5 rounded-xl bg-slate-50 text-[11px] text-slate-700 border border-slate-200">
                      <strong>PDO Verification Remarks:</strong> {issueDetail.cost_verification_remarks}
                    </div>
                  )}
                </div>

                {/* AUDIT TIMELINE */}
                {issueDetail.timeline.length > 0 && (
                  <div className="space-y-3">
                    <h4 className="font-bold text-sm text-[#102B4E]">Resolution Audit Timeline</h4>
                    <div className="border-l-2 border-[#DCE5EE] ml-3 pl-4 space-y-3">
                      {issueDetail.timeline.map((ev, idx) => (
                        <div key={idx} className="relative space-y-0.5">
                          <div className="absolute -left-[23px] top-1 w-3 h-3 rounded-full bg-[#087F78] border-2 border-white" />
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-[#102B4E] uppercase text-[10px]">{ev.status}</span>
                            <span className="text-[10px] text-slate-400">
                              {new Date(ev.timestamp).toLocaleString("en-IN")}
                            </span>
                          </div>
                          <p className="text-slate-600 text-[11px]">{ev.public_summary || ev.actor_title}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* PRIVACY FOOTER */}
                <div className="pt-3 border-t border-[#DCE5EE] flex items-center justify-between text-[11px] text-slate-500">
                  <div className="flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4 text-[#087F78]" />
                    <span>All private citizen contact numbers, emails, and house addresses are permanently redacted.</span>
                  </div>
                  <button
                    type="button"
                    onClick={closeIssueDetail}
                    className="px-4 py-2 rounded-xl bg-[#102B4E] text-white font-bold hover:bg-[#0B2545] transition-colors"
                  >
                    Close
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
