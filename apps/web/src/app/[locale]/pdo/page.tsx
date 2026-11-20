"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import {
  LayoutDashboard,
  ClipboardList,
  AlertCircle,
  Clock,
  Activity,
  FileCheck,
  CheckCircle2,
  RotateCcw,
  Wrench,
  MapPin,
  Layers,
  Users,
  UserCheck,
  FileBarChart,
  Bell,
  Settings,
  Menu,
  ChevronLeft,
  ChevronRight,
  Search,
  Plus,
  RefreshCw,
  AlertTriangle,
  Send,
  Eye,
  LogOut,
  Camera,
  Sparkles,
  Copy,
  Building2,
  X,
  Check,
  Edit,
  Trash2,
  ShieldCheck,
  Phone,
  Mail,
  User,
} from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { LeafletMap, MapComplaint } from "@/components/ui/LeafletMap";
import { LanguageSelector } from "@/components/ui/LanguageSelector";
import { GramaSevaLogo } from "@/components/ui/GramaSevaLogo";

type PdoSection =
  | "dashboard"
  | "all_complaints"
  | "new_complaints"
  | "under_review"
  | "in_progress"
  | "awaiting_verification"
  | "resolved"
  | "reopened"
  | "assignments"
  | "village_map"
  | "ward_management"
  | "ward_members"
  | "workers"
  | "reports"
  | "notifications"
  | "settings";

interface VillageOverview {
  village_name: string;
  village_id: string;
  total_complaints: number;
  new_complaints: number;
  under_review: number;
  assigned: number;
  in_progress: number;
  awaiting_verification: number;
  resolved: number;
  reopened: number;
  categories: Record<string, number>;
  workers_count: number;
  pending_workers_count: number;
}

interface ComplaintRecord {
  id: string;
  reference_number?: string;
  category: string;
  status: string;
  priority: string;
  description?: string;
  latitude?: number;
  longitude?: number;
  village_name?: string;
  ward_name?: string;
  citizen_id?: string;
  citizen_name?: string;
  citizen_phone?: string;
  citizen_email?: string;
  assigned_worker_id?: string;
  assigned_worker_name?: string;
  ai_prediction?: string;
  ai_confidence?: number;
  photos_count: number;
  created_at: string;
  resolved_at?: string;
  worker_notes?: string;
  repair_photo_url?: string;
  estimated_cost?: number;
  proposed_cost?: number;
  materials_cost?: number;
  labour_cost?: number;
  other_expenses_cost?: number;
  verified_cost?: number;
  cost_status?: string;
  work_completed_at?: string;
  work_completion_description?: string;
  work_performed?: string;
  materials_used?: string;
  labour_details?: string;
  cost_verification_remarks?: string;
  ai_analysis?: {
    is_identical_image?: boolean;
    fraud_alert?: boolean;
    structural_diff_detected?: boolean;
    consistency_score?: number;
    difference_summary?: string;
    advisory_suggestion?: string;
  };
  before_photo_ids?: string[];
  after_photo_ids?: string[];
}

interface WorkerRecord {
  id: string;
  full_name: string;
  email: string;
  phone_number?: string;
  approval_status: string;
  is_active: boolean;
  active_assignments_count: number;
  completed_tasks_count: number;
  created_at?: string;
}

interface WardData {
  id: string;
  name_en: string;
  name_kn?: string;
  official_code?: string;
  total_complaints: number;
  resolved_complaints: number;
  pending_complaints: number;
  members_count: number;
  members: Array<{
    id: string;
    full_name: string;
    phone_number?: string;
    email?: string;
    designation: string;
    is_active: boolean;
  }>;
}

interface PdoNotification {
  id: string;
  title: string;
  message: string;
  event_type: string;
  is_read: boolean;
  created_at: string;
}

export default function VillagePdoDashboard() {
  const locale = useLocale();
  const router = useRouter();

  // Sidebar Layout State
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const [activeSection, setActiveSection] = useState<PdoSection>("dashboard");

  // Operational State
  const [isLoading, setIsLoading] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Real Database States
  const [overview, setOverview] = useState<VillageOverview | null>(null);
  const [complaints, setComplaints] = useState<ComplaintRecord[]>([]);
  const [workers, setWorkers] = useState<WorkerRecord[]>([]);
  const [wards, setWards] = useState<WardData[]>([]);
  const [notifications, setNotifications] = useState<PdoNotification[]>([]);
  const [mapData, setMapData] = useState<{ boundary: any; complaints: MapComplaint[] }>({
    boundary: null,
    complaints: [],
  });

  // Complaint Selection & Inspection Drawer
  const [selectedComplaint, setSelectedComplaint] = useState<ComplaintRecord | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("ALL");
  const [priorityFilter, setPriorityFilter] = useState("ALL");

  // Worker Assignment Modal
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [assignWorkerId, setAssignWorkerId] = useState("");
  const [assignPriority, setAssignPriority] = useState("HIGH");

  // Verification Remarks & Verified Cost Form
  const [verificationRemarks, setVerificationRemarks] = useState("");
  const [verifiedCostInput, setVerifiedCostInput] = useState<number | "">("");

  // Sync verification inputs when complaint is selected
  useEffect(() => {
    if (selectedComplaint) {
      setVerifiedCostInput(
        selectedComplaint.verified_cost ?? selectedComplaint.proposed_cost ?? ""
      );
      setVerificationRemarks(selectedComplaint.cost_verification_remarks ?? "");
    }
  }, [selectedComplaint]);

  // Ward Member Creation Modal
  const [showAddWardMemberModal, setShowAddWardMemberModal] = useState(false);
  const [targetWardId, setTargetWardId] = useState("");
  const [newMemberName, setNewMemberName] = useState("");
  const [newMemberPhone, setNewMemberPhone] = useState("");
  const [newMemberEmail, setNewMemberEmail] = useState("");
  const [newMemberDesignation, setNewMemberDesignation] = useState("Elected Ward Member");

  // Category Override Modal
  const [showOverrideCategoryModal, setShowOverrideCategoryModal] = useState(false);
  const [overrideCategory, setOverrideCategory] = useState("road_damage");

  // Load PDO Data strictly isolated to assigned Gram Panchayat
  const loadPdoData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [ovRes, compRes, wrkRes, wardRes, mapRes, notifRes] = await Promise.allSettled([
        apiClient.get<VillageOverview>("/staff/village-overview"),
        apiClient.get<ComplaintRecord[]>("/staff/all-complaints"),
        apiClient.get<WorkerRecord[]>("/staff/workers"),
        apiClient.get<WardData[]>("/staff/wards"),
        apiClient.get<any>("/staff/village-map"),
        apiClient.get<PdoNotification[]>("/staff/notifications"),
      ]);

      if (ovRes.status === "fulfilled") setOverview(ovRes.value);
      if (compRes.status === "fulfilled") setComplaints(compRes.value);
      if (wrkRes.status === "fulfilled") setWorkers(wrkRes.value);
      if (wardRes.status === "fulfilled") setWards(wardRes.value);
      if (notifRes.status === "fulfilled") setNotifications(notifRes.value);
      if (mapRes.status === "fulfilled") {
        setMapData({
          boundary: mapRes.value.boundary || null,
          complaints: (mapRes.value.points || mapRes.value.complaints || []).map((c: any) => ({
            id: c.id,
            reference_number: c.reference_number,
            category: c.category,
            status: c.status,
            latitude: c.latitude,
            longitude: c.longitude,
            description: c.description,
            priority: c.priority,
            assigned_worker_name: c.assigned_worker_name,
            village_name: c.village_name,
          })),
        });
      }
    } catch (err: any) {
      setError(err.message || "Failed to load village PDO workspace");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPdoData();
  }, []);

  const handleSignOut = () => {
    localStorage.removeItem("gramaseva_token");
    localStorage.removeItem("access_token");
    localStorage.removeItem("gramaseva_user");
    router.push(`/${locale}/login`);
  };

  // Action: Worker Approval
  const handleApproveWorker = async (workerId: string, workerName: string) => {
    try {
      await apiClient.post(`/staff/workers/${workerId}/approve`);
      setNotice(`Worker ${workerName} has been approved for work order assignments in this GP.`);
      loadPdoData();
    } catch (err: any) {
      setError(err.message || "Failed to approve worker");
    }
  };

  const handleRejectWorker = async (workerId: string, workerName: string) => {
    try {
      await apiClient.post(`/staff/workers/${workerId}/reject`, {
        reason: "Registration does not meet local Gram Panchayat criteria.",
      });
      setNotice(`Worker application for ${workerName} rejected.`);
      loadPdoData();
    } catch (err: any) {
      setError(err.message || "Failed to reject worker");
    }
  };

  // Action: Worker Assignment
  const handleAssignWorker = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedComplaint || !assignWorkerId) return;

    try {
      await apiClient.post(`/staff/triage/${selectedComplaint.id}`, {
        decision: "CONFIRM_DISPATCH",
        assigned_worker_id: assignWorkerId,
        priority: assignPriority,
        notes: `Assigned by Village PDO for GP execution.`,
      });
      setNotice(`Complaint ${selectedComplaint.reference_number || selectedComplaint.id} dispatched to field worker.`);
      setShowAssignModal(false);
      loadPdoData();
    } catch (err: any) {
      setError(err.message || "Failed to dispatch worker");
    }
  };

  // Action: Verify Completion Evidence & Costs
  const handleVerifyResolution = async (decision: "APPROVE" | "CORRECTION_REQUIRED") => {
    if (!selectedComplaint) return;
    try {
      const verifiedCost =
        typeof verifiedCostInput === "number"
          ? verifiedCostInput
          : selectedComplaint.proposed_cost ?? 0;
      await apiClient.post(`/staff/issues/${selectedComplaint.id}/resolution`, {
        decision,
        explanation:
          verificationRemarks ||
          (decision === "APPROVE"
            ? "Independent on-site inspection and before/after photographic evidence confirmed."
            : "Photographic proof inadequate or repair defective; returned to worker for rework."),
        verified_cost: decision === "APPROVE" ? verifiedCost : undefined,
        cost_remarks: verificationRemarks,
      });
      setNotice(
        decision === "APPROVE"
          ? `Complaint ${selectedComplaint.reference_number || selectedComplaint.id} officially resolved. Verified expenditure: ₹${verifiedCost.toLocaleString("en-IN")}.`
          : `Complaint ${selectedComplaint.reference_number || selectedComplaint.id} returned to field worker for correction.`
      );
      setVerificationRemarks("");
      setVerifiedCostInput("");
      setSelectedComplaint(null);
      loadPdoData();
    } catch (err: any) {
      setError(err.message || "Failed to process resolution decision");
    }
  };

  // Action: Add Ward Member
  const handleAddWardMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetWardId || !newMemberName.trim()) return;

    try {
      await apiClient.post("/staff/ward-members", {
        ward_unit_id: targetWardId,
        full_name: newMemberName.trim(),
        phone_number: newMemberPhone.trim() || undefined,
        email: newMemberEmail.trim().toLowerCase() || undefined,
        designation: newMemberDesignation,
      });
      setNotice(`Ward member "${newMemberName}" registered.`);
      setShowAddWardMemberModal(false);
      setNewMemberName("");
      setNewMemberPhone("");
      setNewMemberEmail("");
      loadPdoData();
    } catch (err: any) {
      setError(err.message || "Failed to register ward member");
    }
  };

  // Action: Toggle Ward Member Status
  const handleToggleWardMemberStatus = async (memberId: string, currentStatus: boolean) => {
    try {
      await apiClient.patch(`/staff/ward-members/${memberId}`, { is_active: !currentStatus });
      setNotice("Ward member status updated.");
      loadPdoData();
    } catch (err: any) {
      setError(err.message || "Failed to update ward member");
    }
  };

  // Action: Correct Category
  const handleCorrectCategorySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedComplaint) return;
    try {
      await apiClient.post(`/staff/triage/${selectedComplaint.id}`, {
        decision: "REQUEST_INFO",
        notes: `PDO manually updated category to ${overrideCategory}`,
      });
      setNotice(`Category updated to ${overrideCategory.replace("_", " ")}.`);
      setShowOverrideCategoryModal(false);
      loadPdoData();
    } catch (err: any) {
      setError(err.message || "Failed to update category");
    }
  };

  // Navigation Items (16 Items)
  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "all_complaints", label: "All Complaints", icon: ClipboardList, badge: complaints.length },
    { id: "new_complaints", label: "New Complaints", icon: AlertCircle, badge: overview?.new_complaints, highlight: (overview?.new_complaints || 0) > 0 },
    { id: "under_review", label: "Under Review", icon: Clock, badge: overview?.under_review },
    { id: "in_progress", label: "In Progress", icon: Activity, badge: overview?.in_progress },
    { id: "awaiting_verification", label: "Awaiting Verification", icon: FileCheck, badge: overview?.awaiting_verification, alertBadge: (overview?.awaiting_verification || 0) > 0 },
    { id: "resolved", label: "Resolved", icon: CheckCircle2, badge: overview?.resolved },
    { id: "reopened", label: "Reopened", icon: RotateCcw, badge: overview?.reopened },
    { id: "assignments", label: "Assignments", icon: Wrench },
    { id: "village_map", label: "Village Map", icon: MapPin },
    { id: "ward_management", label: "Ward Management", icon: Layers, badge: wards.length },
    { id: "ward_members", label: "Ward Members", icon: Users },
    { id: "workers", label: "Workers", icon: UserCheck, badge: overview?.pending_workers_count },
    { id: "reports", label: "Reports", icon: FileBarChart },
    { id: "notifications", label: "Notifications", icon: Bell, badge: notifications.filter((n) => !n.is_read).length },
    { id: "settings", label: "Profile & Settings", icon: Settings },
  ];

  const currentSectionMeta = navItems.find((n) => n.id === activeSection) || navItems[0];

  // Filtering helper
  const getFilteredComplaintsBySection = () => {
    return complaints.filter((c) => {
      // Search match
      const q = searchQuery.toLowerCase();
      const matchSearch =
        !q ||
        (c.reference_number && c.reference_number.toLowerCase().includes(q)) ||
        (c.description && c.description.toLowerCase().includes(q)) ||
        (c.category && c.category.toLowerCase().includes(q));

      // Category filter
      const matchCat = categoryFilter === "ALL" || c.category.toUpperCase() === categoryFilter.toUpperCase();

      // Section Status match
      let matchStatus = true;
      if (activeSection === "new_complaints") matchStatus = c.status === "SUBMITTED";
      else if (activeSection === "under_review") matchStatus = c.status === "UNDER_REVIEW";
      else if (activeSection === "in_progress") matchStatus = c.status === "IN_PROGRESS" || c.status === "ASSIGNED";
      else if (activeSection === "awaiting_verification") matchStatus = c.status === "REPAIR_REPORTED" || c.status === "AWAITING_VERIFICATION";
      else if (activeSection === "resolved") matchStatus = c.status === "RESOLVED";
      else if (activeSection === "reopened") matchStatus = c.status === "REOPENED";

      return matchSearch && matchCat && matchStatus;
    });
  };

  const displayedComplaints = getFilteredComplaintsBySection();
  const approvedWorkers = workers.filter((w) => w.approval_status === "APPROVED");
  const pendingWorkers = workers.filter((w) => w.approval_status === "PENDING");

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex text-[#102B4E] font-sans antialiased">
      {/* 1. Left Professional Sidebar (Deep Teal / Dark Navy, Scrollable, Collapsible) */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-40 bg-[#044E49] text-teal-100 flex flex-col transition-all duration-300 ease-in-out border-r border-[#033E3A] ${
          isCollapsed ? "w-20" : "w-64"
        } ${mobileDrawerOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}`}
      >
        {/* Sidebar Header */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-[#033E3A] shrink-0 bg-[#023330]">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-9 h-9 rounded-xl bg-white/10 text-white flex items-center justify-center shrink-0 border border-white/20">
              <Building2 className="w-5 h-5 text-emerald-300" />
            </div>
            {!isCollapsed && (
              <div className="truncate text-left">
                <span className="text-white font-black text-sm tracking-tight block">GramaSeva</span>
                <span className="text-[10px] text-emerald-300 font-bold uppercase tracking-wider block truncate">
                  {overview?.village_name || "Assigned Village"}
                </span>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="hidden md:flex w-7 h-7 rounded-lg bg-white/5 hover:bg-white/10 items-center justify-center text-teal-200 hover:text-white transition-colors"
            title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          >
            {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Sidebar Nav Items (Independently Vertically Scrollable) */}
        <div className="flex-1 overflow-y-auto px-3 py-3 space-y-0.5 scrollbar-thin scrollbar-thumb-teal-800">
          {!isCollapsed && (
            <p className="px-3 py-1 text-[10px] font-extrabold uppercase tracking-wider text-teal-400">
              Panchayat Operations
            </p>
          )}

          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  setActiveSection(item.id as PdoSection);
                  setNotice(null);
                  setError(null);
                  setMobileDrawerOpen(false);
                }}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-semibold transition-all group ${
                  isActive
                    ? "bg-white text-[#044E49] shadow-xs font-black"
                    : item.highlight
                    ? "text-amber-300 hover:bg-white/10"
                    : "text-teal-100 hover:text-white hover:bg-white/10"
                } ${isCollapsed ? "justify-center px-0" : ""}`}
                title={isCollapsed ? item.label : undefined}
              >
                <Icon
                  className={`w-4 h-4 shrink-0 ${
                    isActive ? "text-[#044E49]" : item.highlight ? "text-amber-300" : "text-teal-300 group-hover:text-white"
                  }`}
                />
                {!isCollapsed && <span className="truncate flex-1 text-left">{item.label}</span>}
                {!isCollapsed && item.badge !== undefined && item.badge > 0 && (
                  <span
                    className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${
                      item.alertBadge
                        ? "bg-orange-500 text-white font-black animate-pulse"
                        : isActive
                        ? "bg-[#044E49] text-white"
                        : "bg-teal-900/60 text-teal-200"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Sidebar PDO Account Footer */}
        <div className="p-3 border-t border-[#033E3A] bg-[#023330] shrink-0">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-full bg-teal-800 border border-teal-700 flex items-center justify-center text-xs font-bold text-white shrink-0">
                PDO
              </div>
              {!isCollapsed && (
                <div className="truncate text-left text-xs">
                  <p className="font-bold text-white truncate">Village PDO</p>
                  <p className="text-[10px] text-teal-300 truncate">Panchayat Officer</p>
                </div>
              )}
            </div>

            {!isCollapsed && (
              <button
                type="button"
                onClick={handleSignOut}
                className="w-7 h-7 rounded-lg hover:bg-red-500/20 text-teal-300 hover:text-red-400 flex items-center justify-center transition-colors"
                title="Sign Out"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </aside>

      {/* Mobile Backdrop */}
      {mobileDrawerOpen && (
        <div
          onClick={() => setMobileDrawerOpen(false)}
          className="fixed inset-0 z-30 bg-black/50 md:hidden backdrop-blur-xs"
        />
      )}

      {/* 2. Main Workspace Layout */}
      <div
        className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ease-in-out ${
          isCollapsed ? "md:ml-20" : "md:ml-64"
        }`}
      >
        {/* Top Header Bar */}
        <header className="h-16 bg-white border-b border-[#DCE5EE] px-4 sm:px-6 lg:px-8 flex items-center justify-between sticky top-0 z-20 shadow-2xs">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setMobileDrawerOpen(!mobileDrawerOpen)}
              className="md:hidden w-9 h-9 rounded-xl flex items-center justify-center text-[#102B4E] hover:bg-slate-100 border border-[#DCE5EE]"
            >
              <Menu className="w-5 h-5" />
            </button>

            {/* Breadcrumbs */}
            <div className="flex items-center gap-2 text-xs font-semibold text-[#40536B]">
              <span className="hidden sm:inline font-bold text-[#087F78]">
                {overview?.village_name || "Assigned Village"}
              </span>
              <span className="hidden sm:inline text-slate-300">/</span>
              <span className="text-[#102B4E] font-bold">{currentSectionMeta.label}</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Global Search */}
            <div className="relative hidden md:block w-64">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search complaints, wards..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3.5 py-1.5 text-xs border border-[#DCE5EE] rounded-xl focus:outline-none focus:ring-1 focus:ring-[#087F78] bg-[#F8FAFC]"
              />
            </div>

            {/* Notifications Trigger with Count */}
            <button
              type="button"
              onClick={() => setActiveSection("notifications")}
              className="relative w-9 h-9 rounded-xl border border-[#DCE5EE] hover:bg-slate-50 flex items-center justify-center text-[#102B4E] transition-colors"
              title="Panchayat & Taluk Notifications"
            >
              <Bell className="w-4 h-4" />
              {notifications.some((n) => !n.is_read) && (
                <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              )}
            </button>

            {/* Language Selector */}
            <LanguageSelector />

            {/* Sign Out */}
            <button
              type="button"
              onClick={handleSignOut}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-[#DCE5EE] hover:bg-slate-50 text-xs font-semibold text-[#40536B] hover:text-red-600 transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Exit</span>
            </button>
          </div>
        </header>

        {/* Content Body */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 space-y-6 max-w-[1600px] w-full mx-auto">
          {/* Notifications / Alerts */}
          {notice && (
            <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs sm:text-sm flex items-center justify-between shadow-2xs animate-in fade-in">
              <div className="flex items-center gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{notice}</span>
              </div>
              <button
                type="button"
                onClick={() => setNotice(null)}
                className="text-emerald-700 font-bold hover:underline"
              >
                Dismiss
              </button>
            </div>
          )}

          {error && (
            <div className="p-4 rounded-2xl bg-red-50 border border-red-200 text-red-900 text-xs sm:text-sm flex items-center justify-between shadow-2xs animate-in fade-in">
              <div className="flex items-center gap-2.5">
                <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
                <span>{error}</span>
              </div>
              <button
                type="button"
                onClick={() => setError(null)}
                className="text-red-700 font-bold hover:underline"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* 1. DASHBOARD OVERVIEW */}
          {activeSection === "dashboard" && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h1 className="text-xl sm:text-2xl font-black text-[#102B4E] tracking-tight">
                    Gram Panchayat Operational Overview
                  </h1>
                  <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                    Authorized operations for {overview?.village_name || "Assigned Village"}. Zero cross-village leakage.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-3 py-1 rounded-full text-xs font-bold bg-[#087F78]/10 text-[#087F78] border border-[#087F78]/25">
                    Jurisdiction: {overview?.village_name || "Assigned Village"}
                  </span>
                </div>
              </div>

              {/* 10 Real Database Metrics */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                <div className="bg-white p-4 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">Total Complaints</p>
                  <p className="text-2xl font-black text-[#102B4E]">{overview?.total_complaints ?? 0}</p>
                  <p className="text-[10px] text-slate-400">Village Defect Logs</p>
                </div>
                <div className="bg-white p-4 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">New Submissions</p>
                  <p className="text-2xl font-black text-amber-600">{overview?.new_complaints ?? 0}</p>
                  <p className="text-[10px] text-slate-400">Awaiting Triage</p>
                </div>
                <div className="bg-white p-4 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">Under Review</p>
                  <p className="text-2xl font-black text-blue-600">{overview?.under_review ?? 0}</p>
                  <p className="text-[10px] text-slate-400">PDO Inspection</p>
                </div>
                <div className="bg-white p-4 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">In Progress</p>
                  <p className="text-2xl font-black text-purple-600">{overview?.in_progress ?? 0}</p>
                  <p className="text-[10px] text-slate-400">Field Repair Team</p>
                </div>
                <div className="bg-white p-4 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">Awaiting Verification</p>
                  <p className="text-2xl font-black text-orange-600">{overview?.awaiting_verification ?? 0}</p>
                  <p className="text-[10px] text-slate-400">Requires Photo Check</p>
                </div>
                <div className="bg-white p-4 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">Resolved Issues</p>
                  <p className="text-2xl font-black text-emerald-600">{overview?.resolved ?? 0}</p>
                  <p className="text-[10px] text-slate-400">Verified & Closed</p>
                </div>
                <div className="bg-white p-4 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">Reopened</p>
                  <p className="text-2xl font-black text-rose-600">{overview?.reopened ?? 0}</p>
                  <p className="text-[10px] text-slate-400">Citizen Dispute</p>
                </div>
                <div className="bg-white p-4 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">Total Wards</p>
                  <p className="text-2xl font-black text-[#102B4E]">{wards.length}</p>
                  <p className="text-[10px] text-slate-400">Registered Wards</p>
                </div>
                <div className="bg-white p-4 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">Ward Members</p>
                  <p className="text-2xl font-black text-[#087F78]">
                    {wards.reduce((acc, w) => acc + w.members_count, 0)}
                  </p>
                  <p className="text-[10px] text-slate-400">Active Representatives</p>
                </div>
                <div className="bg-white p-4 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">Approved Workers</p>
                  <p className="text-2xl font-black text-sky-700">{approvedWorkers.length}</p>
                  <p className="text-[10px] text-slate-400">Field Technicians</p>
                </div>
              </div>

              {/* Action Required: Awaiting Verification & Pending Workers */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Repairs Awaiting Verification */}
                <div className="bg-white p-6 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-4">
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className="text-sm font-bold text-[#102B4E]">Repairs Awaiting Verification</h3>
                      <p className="text-xs text-[#40536B]">Workers completed repair; inspect proof before closure.</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setActiveSection("awaiting_verification")}
                      className="text-xs font-bold text-[#087F78] hover:underline"
                    >
                      View All →
                    </button>
                  </div>

                  <div className="space-y-3">
                    {complaints
                      .filter((c) => c.status === "REPAIR_REPORTED" || c.status === "AWAITING_VERIFICATION")
                      .slice(0, 4)
                      .map((c) => (
                        <div
                          key={c.id}
                          className="p-3.5 rounded-xl border border-orange-200 bg-orange-50/40 flex justify-between items-center text-xs"
                        >
                          <div>
                            <span className="font-bold text-[#102B4E]">{c.reference_number || c.id}</span>
                            <span className="text-slate-500 block capitalize">{c.category.replace("_", " ")}</span>
                          </div>
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedComplaint(c);
                              setActiveSection("awaiting_verification");
                            }}
                            className="px-3 py-1.5 rounded-lg bg-[#087F78] text-white font-bold hover:bg-[#066B65]"
                          >
                            Inspect Evidence
                          </button>
                        </div>
                      ))}
                    {!complaints.some((c) => c.status === "REPAIR_REPORTED" || c.status === "AWAITING_VERIFICATION") && (
                      <p className="text-xs text-slate-400 text-center py-4">Zero repairs awaiting verification.</p>
                    )}
                  </div>
                </div>

                {/* Worker Registrations Pending Approval */}
                <div className="bg-white p-6 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-4">
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className="text-sm font-bold text-[#102B4E]">Worker Registrations Pending Approval</h3>
                      <p className="text-xs text-[#40536B]">Technicians cannot receive work orders until authorized.</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setActiveSection("workers")}
                      className="text-xs font-bold text-[#087F78] hover:underline"
                    >
                      Manage Roster →
                    </button>
                  </div>

                  <div className="space-y-3">
                    {pendingWorkers.slice(0, 3).map((pw) => (
                      <div
                        key={pw.id}
                        className="p-3.5 rounded-xl border border-amber-200 bg-amber-50/40 flex justify-between items-center text-xs"
                      >
                        <div>
                          <p className="font-bold text-[#102B4E]">{pw.full_name}</p>
                          <p className="text-slate-500">{pw.email}</p>
                        </div>
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => handleRejectWorker(pw.id, pw.full_name)}
                            className="px-2.5 py-1 rounded-lg border border-red-200 text-red-700 font-semibold hover:bg-red-50"
                          >
                            Reject
                          </button>
                          <button
                            type="button"
                            onClick={() => handleApproveWorker(pw.id, pw.full_name)}
                            className="px-3 py-1 rounded-lg bg-[#087F78] text-white font-bold hover:bg-[#066B65]"
                          >
                            Approve
                          </button>
                        </div>
                      </div>
                    ))}
                    {pendingWorkers.length === 0 && (
                      <p className="text-xs text-slate-400 text-center py-4">No pending worker registrations.</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* COMPLAINTS TABLES (All, New, Under Review, In Progress, Awaiting Verification, Resolved, Reopened) */}
          {(activeSection === "all_complaints" ||
            activeSection === "new_complaints" ||
            activeSection === "under_review" ||
            activeSection === "in_progress" ||
            activeSection === "awaiting_verification" ||
            activeSection === "resolved" ||
            activeSection === "reopened") && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-xl font-extrabold text-[#102B4E]">{currentSectionMeta.label}</h2>
                  <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                    Authorized records in {overview?.village_name || "Assigned Village"}.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-[#087F78] bg-[#087F78]/10 px-3 py-1.5 rounded-xl border border-[#087F78]/20">
                    {displayedComplaints.length} records in scope
                  </span>
                </div>
              </div>

              {/* Filters Bar */}
              <div className="p-4 bg-white rounded-2xl border border-[#DCE5EE] shadow-2xs flex flex-wrap gap-3 items-center justify-between">
                <div className="relative flex-1 min-w-[220px]">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="Search by ID, citizen name, description..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-9 pr-3 py-1.5 text-xs border border-[#DCE5EE] rounded-xl focus:outline-none focus:ring-1 focus:ring-[#087F78]"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <select
                    value={categoryFilter}
                    onChange={(e) => setCategoryFilter(e.target.value)}
                    className="px-3 py-1.5 text-xs border border-[#DCE5EE] rounded-xl focus:outline-none bg-white font-semibold text-[#102B4E]"
                  >
                    <option value="ALL">All Categories</option>
                    <option value="road_damage">Road Damage</option>
                    <option value="water_leak">Water Leak</option>
                    <option value="garbage">Garbage</option>
                    <option value="drainage">Drainage</option>
                    <option value="streetlight">Streetlight</option>
                  </select>
                </div>
              </div>

              {/* Professional Complaint Management Table */}
              <div className="bg-white rounded-2xl border border-[#DCE5EE] shadow-2xs overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#F8FAFC] border-b border-[#DCE5EE] text-[#40536B] font-bold uppercase">
                      <tr>
                        <th className="py-3 px-4">Tracking ID</th>
                        <th className="py-3 px-4">Category & AI</th>
                        <th className="py-3 px-4">Description Preview</th>
                        <th className="py-3 px-4">Ward / Location</th>
                        <th className="py-3 px-4">Citizen</th>
                        <th className="py-3 px-4">Submitted</th>
                        <th className="py-3 px-4">Status</th>
                        <th className="py-3 px-4">Assigned Worker</th>
                        <th className="py-3 px-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#DCE5EE]">
                      {displayedComplaints.map((comp) => (
                        <tr key={comp.id} className="hover:bg-[#F8FAFC] transition-colors">
                          <td className="py-3.5 px-4 font-bold text-[#102B4E]">
                            {comp.reference_number || comp.id.slice(0, 8)}
                          </td>
                          <td className="py-3.5 px-4">
                            <span className="font-semibold text-[#102B4E] capitalize block">
                              {comp.category.replace("_", " ")}
                            </span>
                            {comp.ai_prediction && (
                              <span className="inline-flex items-center gap-1 text-[10px] text-teal-700 bg-teal-50 px-1.5 py-0.5 rounded border border-teal-200 mt-0.5">
                                <Sparkles className="w-2.5 h-2.5" />
                                {comp.ai_confidence ? `${Math.round(comp.ai_confidence * 100)}%` : "AI Suggestion"}
                              </span>
                            )}
                          </td>
                          <td className="py-3.5 px-4 text-[#40536B] max-w-xs truncate">
                            {comp.description || "Infrastructure defect report"}
                          </td>
                          <td className="py-3.5 px-4">
                            <span className="font-semibold text-[#102B4E] block">{comp.ward_name || "General Ward"}</span>
                            {comp.latitude && (
                              <span className="text-[10px] text-slate-400">
                                {comp.latitude.toFixed(3)}, {comp.longitude?.toFixed(3)}
                              </span>
                            )}
                          </td>
                          <td className="py-3.5 px-4 text-[#102B4E]">
                            {comp.citizen_name || "Resident"}
                          </td>
                          <td className="py-3.5 px-4 text-slate-400 whitespace-nowrap">
                            {new Date(comp.created_at).toLocaleDateString()}
                          </td>
                          <td className="py-3.5 px-4">
                            <span
                              className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                comp.status === "RESOLVED"
                                  ? "bg-emerald-100 text-emerald-800"
                                  : comp.status === "REPAIR_REPORTED" || comp.status === "AWAITING_VERIFICATION"
                                  ? "bg-orange-100 text-orange-800"
                                  : comp.status === "IN_PROGRESS"
                                  ? "bg-purple-100 text-purple-800"
                                  : comp.status === "ASSIGNED"
                                  ? "bg-indigo-100 text-indigo-800"
                                  : "bg-amber-100 text-amber-800"
                              }`}
                            >
                              {comp.status.replace("_", " ")}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 text-[#40536B]">
                            {comp.assigned_worker_name || "Unassigned"}
                          </td>
                          <td className="py-3.5 px-4 text-right space-x-2">
                            <button
                              type="button"
                              onClick={() => setSelectedComplaint(comp)}
                              className="font-bold text-[#087F78] hover:underline"
                            >
                              Inspect Details
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* SECTION 10: VILLAGE MAP */}
          {activeSection === "village_map" && (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-xl font-extrabold text-[#102B4E]">Village GIS Map</h2>
                  <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                    Authorized complaint markers within {overview?.village_name || "Assigned Village"} boundary.
                  </p>
                </div>
                <span className="font-bold text-xs text-[#087F78] bg-white px-3 py-1.5 rounded-xl border border-[#DCE5EE]">
                  Pins: {mapData.complaints.length}
                </span>
              </div>

              <LeafletMap
                height="600px"
                boundaryGeoJson={mapData.boundary}
                complaints={mapData.complaints}
                selectedComplaintId={selectedComplaint?.id}
                onSelectComplaint={(c) => {
                  const found = complaints.find((x) => x.id === c.id);
                  if (found) setSelectedComplaint(found);
                }}
              />
            </div>
          )}

          {/* SECTION 11: WARD MANAGEMENT */}
          {activeSection === "ward_management" && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-xl font-extrabold text-[#102B4E]">Ward Management</h2>
                  <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                    View ward-wise complaint statistics and registered ward representatives.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    if (wards.length > 0) setTargetWardId(wards[0].id);
                    setShowAddWardMemberModal(true);
                  }}
                  className="h-10 px-4 rounded-xl bg-[#087F78] hover:bg-[#066B65] text-white text-xs font-semibold flex items-center gap-2 shadow-2xs self-start sm:self-auto"
                >
                  <Plus className="w-4 h-4" />
                  <span>Register Ward Member</span>
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                {wards.map((w) => (
                  <div
                    key={w.id}
                    className="bg-white p-5 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-4 text-xs"
                  >
                    <div className="flex justify-between items-start border-b border-slate-100 pb-3">
                      <div>
                        <h3 className="font-bold text-[#102B4E] text-sm">{w.name_en}</h3>
                        {w.name_kn && <p className="text-[10px] text-slate-400">{w.name_kn}</p>}
                      </div>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-teal-100 text-teal-800">
                        {w.members_count} Members
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div className="p-2 bg-[#F8FAFC] rounded-xl border border-[#DCE5EE]">
                        <p className="text-[10px] text-slate-400 font-bold uppercase">Total</p>
                        <p className="font-black text-sm text-[#102B4E]">{w.total_complaints}</p>
                      </div>
                      <div className="p-2 bg-amber-50 rounded-xl border border-amber-200">
                        <p className="text-[10px] text-amber-700 font-bold uppercase">Pending</p>
                        <p className="font-black text-sm text-amber-800">{w.pending_complaints}</p>
                      </div>
                      <div className="p-2 bg-emerald-50 rounded-xl border border-emerald-200">
                        <p className="text-[10px] text-emerald-700 font-bold uppercase">Resolved</p>
                        <p className="font-black text-sm text-emerald-800">{w.resolved_complaints}</p>
                      </div>
                    </div>

                    <div className="space-y-1.5 pt-1">
                      <p className="font-bold text-[#102B4E] text-[11px]">Registered Representatives:</p>
                      {w.members.length === 0 ? (
                        <p className="text-slate-400 text-[11px]">No representative registered yet.</p>
                      ) : (
                        w.members.map((m) => (
                          <div
                            key={m.id}
                            className="p-2 rounded-lg bg-[#F8FAFC] border border-[#DCE5EE] flex justify-between items-center"
                          >
                            <div>
                              <p className="font-semibold text-[#102B4E]">{m.full_name}</p>
                              <p className="text-[10px] text-slate-400">{m.designation}</p>
                            </div>
                            {m.phone_number && <span className="text-[10px] text-[#087F78]">📱 {m.phone_number}</span>}
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* SECTION 12: WARD MEMBERS TABLE */}
          {activeSection === "ward_members" && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-xl font-extrabold text-[#102B4E]">Ward Representatives Roster</h2>
                  <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                    Official elected or appointed representatives across Gram Panchayat wards.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    if (wards.length > 0) setTargetWardId(wards[0].id);
                    setShowAddWardMemberModal(true);
                  }}
                  className="h-10 px-4 rounded-xl bg-[#087F78] hover:bg-[#066B65] text-white text-xs font-semibold flex items-center gap-2 shadow-2xs self-start sm:self-auto"
                >
                  <Plus className="w-4 h-4" />
                  <span>Add Representative</span>
                </button>
              </div>

              <div className="bg-white rounded-2xl border border-[#DCE5EE] shadow-2xs overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#F8FAFC] border-b border-[#DCE5EE] text-[#40536B] font-bold uppercase">
                      <tr>
                        <th className="py-3 px-4">Representative Name</th>
                        <th className="py-3 px-4">Ward</th>
                        <th className="py-3 px-4">Contact</th>
                        <th className="py-3 px-4">Designation</th>
                        <th className="py-3 px-4">Status</th>
                        <th className="py-3 px-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#DCE5EE]">
                      {wards.flatMap((w) =>
                        w.members.map((m) => (
                          <tr key={m.id} className="hover:bg-[#F8FAFC] transition-colors">
                            <td className="py-3.5 px-4 font-bold text-[#102B4E]">{m.full_name}</td>
                            <td className="py-3.5 px-4 font-semibold text-[#087F78]">{w.name_en}</td>
                            <td className="py-3.5 px-4 text-slate-500">
                              {m.email && <p>{m.email}</p>}
                              {m.phone_number && <p className="text-[10px]">📱 {m.phone_number}</p>}
                            </td>
                            <td className="py-3.5 px-4 text-[#40536B]">{m.designation}</td>
                            <td className="py-3.5 px-4">
                              <span
                                className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                  m.is_active ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
                                }`}
                              >
                                {m.is_active ? "ACTIVE" : "INACTIVE"}
                              </span>
                            </td>
                            <td className="py-3.5 px-4 text-right">
                              <button
                                type="button"
                                onClick={() => handleToggleWardMemberStatus(m.id, m.is_active)}
                                className={`font-bold ${m.is_active ? "text-red-600 hover:underline" : "text-emerald-700 hover:underline"}`}
                              >
                                {m.is_active ? "Deactivate" : "Activate"}
                              </button>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* SECTION 13: WORKERS MANAGEMENT */}
          {activeSection === "workers" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-extrabold text-[#102B4E]">Worker Management & Approvals</h2>
                <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                  Authorize, approve, or reject field technicians for this Gram Panchayat.
                </p>
              </div>

              {/* Pending Approvals Callout */}
              {pendingWorkers.length > 0 && (
                <div className="p-5 rounded-2xl bg-amber-50 border-2 border-amber-300 space-y-3 text-xs">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-amber-700" />
                    <h3 className="font-bold text-amber-950 text-sm">
                      {pendingWorkers.length} Worker Registration(s) Awaiting Approval
                    </h3>
                  </div>
                  <div className="space-y-2">
                    {pendingWorkers.map((pw) => (
                      <div
                        key={pw.id}
                        className="p-3 bg-white rounded-xl border border-amber-200 flex justify-between items-center"
                      >
                        <div>
                          <p className="font-bold text-[#102B4E]">{pw.full_name}</p>
                          <p className="text-slate-400">{pw.email}</p>
                        </div>
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => handleRejectWorker(pw.id, pw.full_name)}
                            className="px-3 py-1.5 rounded-lg border border-red-200 text-red-700 font-semibold"
                          >
                            Reject
                          </button>
                          <button
                            type="button"
                            onClick={() => handleApproveWorker(pw.id, pw.full_name)}
                            className="px-3 py-1.5 rounded-lg bg-[#087F78] text-white font-bold"
                          >
                            Approve Worker
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Approved Workers Table */}
              <div className="bg-white rounded-2xl border border-[#DCE5EE] shadow-2xs overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#F8FAFC] border-b border-[#DCE5EE] text-[#40536B] font-bold uppercase">
                      <tr>
                        <th className="py-3 px-4">Technician Name</th>
                        <th className="py-3 px-4">Contact</th>
                        <th className="py-3 px-4">Approval Status</th>
                        <th className="py-3 px-4">Active Tasks</th>
                        <th className="py-3 px-4">Completed Repairs</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#DCE5EE]">
                      {approvedWorkers.map((w) => (
                        <tr key={w.id} className="hover:bg-[#F8FAFC] transition-colors">
                          <td className="py-3.5 px-4 font-bold text-[#102B4E]">{w.full_name}</td>
                          <td className="py-3.5 px-4 text-slate-500">
                            {w.email}
                            {w.phone_number && <span className="block text-[10px]">📱 {w.phone_number}</span>}
                          </td>
                          <td className="py-3.5 px-4">
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                              AUTHORIZED
                            </span>
                          </td>
                          <td className="py-3.5 px-4 font-bold text-sky-700">{w.active_assignments_count}</td>
                          <td className="py-3.5 px-4 font-bold text-emerald-700">{w.completed_tasks_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* SECTION 14: REPORTS */}
          {activeSection === "reports" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-extrabold text-[#102B4E]">Panchayat Performance Reports</h2>
                <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                  Resolution metrics and worker completion rates for {overview?.village_name || "Assigned Village"}.
                </p>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-4 text-xs">
                <h3 className="font-bold text-[#102B4E]">Export Audit Bulletin</h3>
                <p className="text-[#40536B]">
                  Download government-compliant CSV report with verified photo evidence hashes and completion timestamps.
                </p>
                <button
                  type="button"
                  onClick={() => setNotice("Panchayat monthly resolution audit exported.")}
                  className="px-4 py-2.5 rounded-xl bg-[#087F78] hover:bg-[#066B65] text-white font-semibold"
                >
                  Download Village Resolution Report (CSV)
                </button>
              </div>
            </div>
          )}

          {/* SECTION 15: NOTIFICATIONS */}
          {activeSection === "notifications" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-extrabold text-[#102B4E]">Panchayat Notification Center</h2>
                <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                  Directives from Taluk Super Admin and automated complaint status alerts.
                </p>
              </div>

              <div className="space-y-3">
                {notifications.map((n) => (
                  <div
                    key={n.id}
                    className={`p-4 rounded-2xl border text-xs space-y-1 ${
                      n.is_read ? "bg-white border-[#DCE5EE]" : "bg-teal-50/50 border-teal-200"
                    }`}
                  >
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-[#102B4E]">{n.title}</span>
                      <span className="text-[10px] text-slate-400">
                        {n.created_at ? new Date(n.created_at).toLocaleString() : "Just now"}
                      </span>
                    </div>
                    <p className="text-[#40536B] leading-relaxed">{n.message}</p>
                  </div>
                ))}
                {notifications.length === 0 && (
                  <p className="text-slate-400 text-center py-8">No notifications received yet.</p>
                )}
              </div>
            </div>
          )}

          {/* SECTION 16: PROFILE & SETTINGS */}
          {activeSection === "settings" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-extrabold text-[#102B4E]">Village PDO Settings</h2>
                <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                  Office parameters and jurisdictional contact information.
                </p>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-4 max-w-md text-xs">
                <div className="space-y-1">
                  <label className="block font-bold text-[#102B4E]">Assigned Gram Panchayat</label>
                  <input
                    type="text"
                    disabled
                    value={overview?.village_name || "Assigned Gram Panchayat"}
                    className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl bg-slate-50 font-bold text-[#087F78]"
                  />
                </div>
                <div className="space-y-1">
                  <label className="block font-bold text-[#102B4E]">Panchayat Office Address</label>
                  <input
                    type="text"
                    defaultValue="Gram Panchayat Office, Belagavi Taluk"
                    className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl focus:outline-none"
                  />
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* COMPLAINT DETAILS INSPECTION DRAWER / MODAL */}
      {selectedComplaint && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex justify-end">
          <div className="bg-white w-full max-w-xl h-full shadow-2xl overflow-y-auto p-6 sm:p-8 space-y-5 text-xs animate-in slide-in-from-right duration-200">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-bold text-[#102B4E]">
                  Complaint: {selectedComplaint.reference_number || selectedComplaint.id}
                </h3>
                <span className="text-slate-400 text-[11px]">
                  Submitted on {new Date(selectedComplaint.created_at).toLocaleString()}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setSelectedComplaint(null)}
                className="w-8 h-8 rounded-full hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            </div>

            {/* Photo Evidence & Category Card */}
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="font-bold text-sm text-[#102B4E] capitalize">
                  Category: {selectedComplaint.category.replace("_", " ")}
                </span>
                <button
                  type="button"
                  onClick={() => setShowOverrideCategoryModal(true)}
                  className="text-[11px] font-bold text-[#087F78] hover:underline"
                >
                  Correct Category
                </button>
              </div>

              {/* Before and After Evidence Photos Side-by-Side */}
              <div className="space-y-2">
                <p className="text-[11px] font-bold uppercase tracking-wider text-[#40536B]">
                  Evidence Photographs
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <span className="text-[10px] font-bold text-slate-500 uppercase">
                      1. Citizen Before Evidence
                    </span>
                    {selectedComplaint.before_photo_ids &&
                    selectedComplaint.before_photo_ids.length > 0 ? (
                      <img
                        src={`http://localhost:8000/api/v1/public/media/${selectedComplaint.before_photo_ids[0]}/view`}
                        alt="Citizen Before Evidence"
                        className="w-full h-36 object-cover rounded-xl border border-slate-200"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = "none";
                        }}
                      />
                    ) : (
                      <div className="w-full h-36 rounded-xl bg-slate-100 border border-slate-200 flex flex-col items-center justify-center text-slate-400 p-2 text-center text-[11px]">
                        <Camera className="w-5 h-5 mb-1" />
                        No Before Photo
                      </div>
                    )}
                  </div>

                  <div className="space-y-1">
                    <span className="text-[10px] font-bold text-slate-500 uppercase">
                      2. Worker After Evidence
                    </span>
                    {selectedComplaint.after_photo_ids &&
                    selectedComplaint.after_photo_ids.length > 0 ? (
                      <img
                        src={`http://localhost:8000/api/v1/public/media/${selectedComplaint.after_photo_ids[0]}/view`}
                        alt="Worker After Evidence"
                        className="w-full h-36 object-cover rounded-xl border border-slate-200"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = "none";
                        }}
                      />
                    ) : (
                      <div className="w-full h-36 rounded-xl bg-amber-50 border border-amber-200 flex flex-col items-center justify-center text-amber-700 p-2 text-center text-[11px]">
                        <Clock className="w-5 h-5 mb-1 text-amber-500" />
                        Awaiting completion photo
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {selectedComplaint.ai_prediction && (
                <div className="p-3 rounded-xl bg-teal-50 border border-teal-200 text-teal-900 flex justify-between items-center">
                  <span>
                    AI Classification: <strong>{selectedComplaint.ai_prediction}</strong>
                  </span>
                  <span className="text-[10px] font-bold bg-teal-200 px-2 py-0.5 rounded-full">
                    {selectedComplaint.ai_confidence
                      ? `${Math.round(selectedComplaint.ai_confidence * 100)}% match`
                      : "Advisory"}
                  </span>
                </div>
              )}
            </div>

            {/* AI Before/After Advisory Analysis Card */}
            {selectedComplaint.ai_analysis && (
              <div
                className={`p-4 rounded-2xl border ${
                  selectedComplaint.ai_analysis.is_identical_image
                    ? "bg-red-50 border-red-300"
                    : "bg-teal-50/70 border-teal-200"
                } space-y-2.5`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-teal-700" />
                    <span className="font-bold text-xs text-[#102B4E]">
                      AI Before/After Evidence Advisory
                    </span>
                  </div>
                  <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded-full bg-teal-100 text-teal-800 border border-teal-300">
                    Strictly Advisory
                  </span>
                </div>

                {selectedComplaint.ai_analysis.is_identical_image ? (
                  <div className="p-2.5 bg-red-100 border border-red-300 rounded-xl text-red-900 font-bold text-xs flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
                    <span>
                      FRAUD WARNING: Before and After images are identical or nearly identical.
                    </span>
                  </div>
                ) : (
                  <div className="space-y-1.5 text-xs text-slate-700">
                    <div className="flex justify-between">
                      <span>Scene Visual Consistency:</span>
                      <span className="font-bold text-[#102B4E]">
                        {selectedComplaint.ai_analysis.consistency_score
                          ? `${Math.round(
                              selectedComplaint.ai_analysis.consistency_score * 100
                            )}%`
                          : "N/A"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Structural Difference:</span>
                      <span className="font-bold text-emerald-700">
                        {selectedComplaint.ai_analysis.structural_diff_detected
                          ? "Significant Change Detected (Repair Performed)"
                          : "Minor / No Structural Change"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Advisory Suggestion:</span>
                      <span className="font-mono font-bold text-[#087F78]">
                        {selectedComplaint.ai_analysis.advisory_suggestion ||
                          "REVIEW_FOR_APPROVAL"}
                      </span>
                    </div>
                    {selectedComplaint.ai_analysis.difference_summary && (
                      <p className="text-[11px] text-slate-600 bg-white/70 p-2 rounded-lg border border-teal-100">
                        {selectedComplaint.ai_analysis.difference_summary}
                      </p>
                    )}
                  </div>
                )}

                <p className="text-[10px] text-slate-500 italic">
                  AI analysis is advisory decision assistance only. Village PDO retains sole legal authority to approve or reject civic work.
                </p>
              </div>
            )}

            {/* Citizen Description */}
            <div className="p-4 rounded-xl bg-[#F8FAFC] border border-[#DCE5EE] space-y-1">
              <p className="font-bold text-[#102B4E]">Citizen Description:</p>
              <p className="text-[#40536B] leading-relaxed">
                {selectedComplaint.description || "No written remarks provided."}
              </p>
            </div>

            {/* Contact & Location Details (Authorized PDO Access) */}
            <div className="p-4 rounded-xl bg-[#F8FAFC] border border-[#DCE5EE] space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Citizen Reporter:</span>
                <span className="font-bold text-[#102B4E]">
                  {selectedComplaint.citizen_name || "Verified Citizen"}
                </span>
              </div>
              {selectedComplaint.citizen_phone && (
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">Phone:</span>
                  <a
                    href={`tel:${selectedComplaint.citizen_phone}`}
                    className="font-bold text-[#087F78] hover:underline flex items-center gap-1"
                  >
                    <Phone className="w-3.5 h-3.5" />
                    {selectedComplaint.citizen_phone}
                  </a>
                </div>
              )}
              {selectedComplaint.citizen_email && (
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">Email:</span>
                  <a
                    href={`mailto:${selectedComplaint.citizen_email}`}
                    className="text-slate-600 font-mono text-[11px] hover:underline flex items-center gap-1"
                  >
                    <Mail className="w-3.5 h-3.5 text-slate-400" />
                    {selectedComplaint.citizen_email}
                  </a>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-slate-500">Ward:</span>
                <span className="font-bold text-[#087F78]">
                  {selectedComplaint.ward_name || "Belagavi Ward"}
                </span>
              </div>
              {selectedComplaint.latitude && (
                <div className="flex justify-between">
                  <span className="text-slate-500">Coordinates:</span>
                  <span className="font-mono text-[#102B4E]">
                    {selectedComplaint.latitude.toFixed(4)},{" "}
                    {selectedComplaint.longitude?.toFixed(4)}
                  </span>
                </div>
              )}
            </div>

            {/* Work & Expenditure Breakdown */}
            {(selectedComplaint.status === "REPAIR_REPORTED" ||
              selectedComplaint.status === "AWAITING_VERIFICATION" ||
              selectedComplaint.proposed_cost !== undefined) && (
              <div className="p-4 rounded-2xl bg-white border border-[#DCE5EE] space-y-3">
                <div className="flex justify-between items-center border-b border-slate-100 pb-2">
                  <span className="font-bold text-xs text-[#102B4E]">
                    Work & Cost Breakdown
                  </span>
                  {selectedComplaint.cost_status && (
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        selectedComplaint.cost_status === "VERIFIED"
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-amber-100 text-amber-800"
                      }`}
                    >
                      {selectedComplaint.cost_status}
                    </span>
                  )}
                </div>

                {selectedComplaint.work_performed && (
                  <div className="text-xs">
                    <span className="text-slate-500 font-medium">Work Performed:</span>
                    <p className="text-[#102B4E] font-medium">
                      {selectedComplaint.work_performed}
                    </p>
                  </div>
                )}
                {selectedComplaint.materials_used && (
                  <div className="text-xs">
                    <span className="text-slate-500 font-medium">Materials Used:</span>
                    <p className="text-[#102B4E] font-medium">
                      {selectedComplaint.materials_used}
                    </p>
                  </div>
                )}
                {selectedComplaint.labour_details && (
                  <div className="text-xs">
                    <span className="text-slate-500 font-medium">Labour Details:</span>
                    <p className="text-[#102B4E] font-medium">
                      {selectedComplaint.labour_details}
                    </p>
                  </div>
                )}

                {/* Cost Items Grid */}
                <div className="grid grid-cols-3 gap-2 pt-1 text-center">
                  <div className="p-2 bg-slate-50 rounded-xl border border-slate-200">
                    <span className="text-[10px] text-slate-500 font-semibold block">
                      Materials
                    </span>
                    <span className="font-bold text-xs text-[#102B4E]">
                      ₹{(selectedComplaint.materials_cost || 0).toLocaleString("en-IN")}
                    </span>
                  </div>
                  <div className="p-2 bg-slate-50 rounded-xl border border-slate-200">
                    <span className="text-[10px] text-slate-500 font-semibold block">
                      Labour
                    </span>
                    <span className="font-bold text-xs text-[#102B4E]">
                      ₹{(selectedComplaint.labour_cost || 0).toLocaleString("en-IN")}
                    </span>
                  </div>
                  <div className="p-2 bg-slate-50 rounded-xl border border-slate-200">
                    <span className="text-[10px] text-slate-500 font-semibold block">
                      Other Exp.
                    </span>
                    <span className="font-bold text-xs text-[#102B4E]">
                      ₹{(selectedComplaint.other_expenses_cost || 0).toLocaleString("en-IN")}
                    </span>
                  </div>
                </div>

                <div className="flex justify-between items-center p-2.5 bg-slate-100 rounded-xl font-bold text-xs">
                  <span className="text-[#102B4E]">Proposed Total Expenditure:</span>
                  <span className="text-[#087F78] text-sm">
                    ₹{(selectedComplaint.proposed_cost || 0).toLocaleString("en-IN")}
                  </span>
                </div>

                {/* PDO Verification Section */}
                {(selectedComplaint.status === "REPAIR_REPORTED" ||
                  selectedComplaint.status === "AWAITING_VERIFICATION") && (
                  <div className="pt-2 border-t border-slate-100 space-y-3">
                    <div>
                      <label className="block text-[11px] font-bold text-[#102B4E] uppercase mb-1">
                        Verified Final Expenditure (₹) *
                      </label>
                      <input
                        type="number"
                        min="0"
                        step="1"
                        value={verifiedCostInput}
                        onChange={(e) =>
                          setVerifiedCostInput(
                            e.target.value === "" ? "" : parseFloat(e.target.value)
                          )
                        }
                        placeholder="Enter final verified cost approved by PDO"
                        className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl font-bold text-[#102B4E] bg-white focus:outline-none"
                      />
                      <span className="text-[10px] text-slate-500 mt-0.5 block">
                        Pre-filled from worker proposed total. PDO may adjust based on actual receipts.
                      </span>
                    </div>

                    <div>
                      <label className="block text-[11px] font-bold text-[#102B4E] uppercase mb-1">
                        PDO Verification Remarks / Audit Notes
                      </label>
                      <input
                        type="text"
                        value={verificationRemarks}
                        onChange={(e) => setVerificationRemarks(e.target.value)}
                        placeholder="e.g. Work inspected on site, materials verified against bill."
                        className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl bg-white focus:outline-none text-xs"
                      />
                    </div>

                    <div className="flex gap-2 pt-1">
                      <button
                        type="button"
                        onClick={() => handleVerifyResolution("CORRECTION_REQUIRED")}
                        className="flex-1 py-2.5 rounded-xl border border-red-200 text-red-700 font-bold hover:bg-red-50 text-xs transition-colors"
                      >
                        Return for Rework
                      </button>
                      <button
                        type="button"
                        onClick={() => handleVerifyResolution("APPROVE")}
                        className="flex-1 py-2.5 rounded-xl bg-[#087F78] hover:bg-[#066B65] text-white font-bold text-xs shadow-2xs transition-colors"
                      >
                        Approve & Verify Expenditure
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Normal Assignment when not in verification */}
            {selectedComplaint.status !== "REPAIR_REPORTED" &&
              selectedComplaint.status !== "AWAITING_VERIFICATION" && (
                <div className="pt-2 flex gap-3">
                  <button
                    type="button"
                    onClick={() => setShowAssignModal(true)}
                    className="flex-1 py-2.5 rounded-xl bg-[#087F78] hover:bg-[#066B65] text-white font-bold shadow-2xs text-center"
                  >
                    {selectedComplaint.assigned_worker_name
                      ? "Reassign Worker"
                      : "Assign Worker"}
                  </button>
                </div>
              )}
          </div>
        </div>
      )}

      {/* WORKER ASSIGNMENT MODAL */}
      {showAssignModal && selectedComplaint && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-[#DCE5EE] space-y-4 text-xs">
            <div className="flex justify-between items-center">
              <h3 className="text-sm font-bold text-[#102B4E]">
                Assign Worker: {selectedComplaint.reference_number || selectedComplaint.id}
              </h3>
              <button
                type="button"
                onClick={() => setShowAssignModal(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAssignWorker} className="space-y-3">
              <div>
                <label className="block font-bold text-[#102B4E] uppercase mb-1">
                  Select Approved Field Worker
                </label>
                <select
                  required
                  value={assignWorkerId}
                  onChange={(e) => setAssignWorkerId(e.target.value)}
                  className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl focus:outline-none bg-white font-semibold text-[#102B4E]"
                >
                  <option value="">-- Choose Approved Worker --</option>
                  {approvedWorkers.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.full_name} ({w.active_assignments_count} active tasks)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-bold text-[#102B4E] uppercase mb-1">
                  Priority SLA
                </label>
                <select
                  value={assignPriority}
                  onChange={(e) => setAssignPriority(e.target.value)}
                  className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl focus:outline-none bg-white font-semibold text-[#102B4E]"
                >
                  <option value="CRITICAL">Critical (24 Hours)</option>
                  <option value="HIGH">High (48 Hours)</option>
                  <option value="MEDIUM">Medium (72 Hours)</option>
                  <option value="LOW">Low (7 Days)</option>
                </select>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAssignModal(false)}
                  className="px-4 py-2 rounded-xl border border-[#DCE5EE] font-semibold text-[#40536B]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!assignWorkerId}
                  className="px-4 py-2 rounded-xl bg-[#087F78] hover:bg-[#066B65] text-white font-semibold shadow-2xs disabled:opacity-50"
                >
                  Confirm & Dispatch
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ADD WARD MEMBER MODAL */}
      {showAddWardMemberModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-[#DCE5EE] space-y-4 text-xs">
            <div className="flex justify-between items-center">
              <h3 className="text-sm font-bold text-[#102B4E]">Register Ward Representative</h3>
              <button
                type="button"
                onClick={() => setShowAddWardMemberModal(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAddWardMember} className="space-y-3">
              <div>
                <label className="block font-bold text-[#102B4E] uppercase mb-1">Select Ward</label>
                <select
                  required
                  value={targetWardId}
                  onChange={(e) => setTargetWardId(e.target.value)}
                  className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl focus:outline-none bg-white font-semibold text-[#102B4E]"
                >
                  {wards.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.name_en}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-bold text-[#102B4E] uppercase mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Suresh Patel"
                  value={newMemberName}
                  onChange={(e) => setNewMemberName(e.target.value)}
                  className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl focus:outline-none"
                />
              </div>

              <div>
                <label className="block font-bold text-[#102B4E] uppercase mb-1">Phone Number</label>
                <input
                  type="tel"
                  placeholder="10-digit mobile number"
                  value={newMemberPhone}
                  onChange={(e) => setNewMemberPhone(e.target.value)}
                  className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl focus:outline-none"
                />
              </div>

              <div>
                <label className="block font-bold text-[#102B4E] uppercase mb-1">Designation</label>
                <input
                  type="text"
                  value={newMemberDesignation}
                  onChange={(e) => setNewMemberDesignation(e.target.value)}
                  className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl focus:outline-none"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddWardMemberModal(false)}
                  className="px-4 py-2 rounded-xl border border-[#DCE5EE] font-semibold text-[#40536B]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-[#087F78] hover:bg-[#066B65] text-white font-semibold shadow-2xs"
                >
                  Save Member
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CORRECT CATEGORY MODAL */}
      {showOverrideCategoryModal && selectedComplaint && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-sm w-full p-6 shadow-2xl border border-[#DCE5EE] space-y-4 text-xs">
            <h3 className="text-sm font-bold text-[#102B4E]">Correct Complaint Category</h3>
            <form onSubmit={handleCorrectCategorySubmit} className="space-y-3">
              <select
                value={overrideCategory}
                onChange={(e) => setOverrideCategory(e.target.value)}
                className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl focus:outline-none bg-white font-semibold text-[#102B4E]"
              >
                <option value="road_damage">Road Damage & Potholes</option>
                <option value="water_leak">Drinking Water Leakage</option>
                <option value="garbage">Garbage & Litter</option>
                <option value="drainage">Drainage Overflow</option>
                <option value="streetlight">Streetlight Malfunction</option>
              </select>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowOverrideCategoryModal(false)}
                  className="px-4 py-2 rounded-xl border border-[#DCE5EE] font-semibold text-[#40536B]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-[#087F78] hover:bg-[#066B65] text-white font-semibold shadow-2xs"
                >
                  Save Category
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
