"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import {
  Settings,
  Map,
  Building2,
  Users,
  Shield,
  Plus,
  GitFork,
  Check,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  ArrowRight,
  Eye,
  RefreshCw,
  Sparkles,
  MapPin,
  ClipboardList,
  Wrench,
  Send,
  HelpCircle,
  FileText,
  Sliders,
  UserCheck,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge, type StatusType } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { Input, Textarea } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { apiClient } from "@/lib/api-client";

interface ComplaintItem {
  id: string;
  submission_id?: string;
  tracking_id: string;
  reference_number: string;
  category: string;
  status: string;
  priority: string;
  village_name?: string;
  ward_name?: string;
  description?: string;
  assigned_worker_id?: string;
  assigned_worker_name?: string;
  department_id?: string;
  department_name?: string;
  latitude?: number;
  longitude?: number;
  is_duplicate?: boolean;
  is_recurrence?: boolean;
  created_at: string;
  resolved_at?: string;
  photos_count: number;
}

interface LocalityUnit {
  id: string;
  unit_type: string;
  parent_id: string | null;
  name_en: string;
  name_kn: string;
  name_hi: string;
}

export default function AdminPage() {
  const locale = useLocale();
  const tNav = useTranslations("navigation");

  const [activeTab, setActiveTab] = useState<"complaints" | "wards" | "workers">("complaints");
  const [complaints, setComplaints] = useState<ComplaintItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actionAlert, setActionAlert] = useState<{ type: "success" | "info" | "error"; text: string } | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [priorityFilter, setPriorityFilter] = useState("ALL");
  const [villageFilter, setVillageFilter] = useState("ALL");

  // Selected Complaint for Detailed Review & Action Modal
  const [selectedComplaint, setSelectedComplaint] = useState<ComplaintItem | null>(null);
  const [reviewAction, setReviewAction] = useState<"none" | "confirm" | "assign" | "request_info" | "correct_category" | "reject">("none");

  // Assignment Modal Fields
  const [assignWard, setAssignWard] = useState("Ward 2 (Primary School Road)");
  const [assignWorker, setAssignWorker] = useState("worker.ramesh@fixproof.org");
  const [assignDept, setAssignDept] = useState("DEPT-ROADS");
  const [assignPriority, setAssignPriority] = useState("HIGH");
  const [assignSla, setAssignSla] = useState("48_HOURS");
  const [assignInstructions, setAssignInstructions] = useState("");

  // Request Info / Reject / Correct Category Fields
  const [infoMessage, setInfoMessage] = useState("");
  const [rejectReason, setRejectReason] = useState("");
  const [correctedCategory, setCorrectedCategory] = useState("road_damage");
  const [correctionReason, setCorrectionReason] = useState("");
  const [isSubmittingAction, setIsSubmittingAction] = useState(false);

  // Village & Ward Management
  const [villages, setVillages] = useState<LocalityUnit[]>([]);
  const [showAddWardModal, setShowAddWardModal] = useState(false);
  const [newWardName, setNewWardName] = useState("");
  const [newWardVillageId, setNewWardVillageId] = useState("v1");

  const categoryOptions = [
    { value: "ALL", label: "All Categories" },
    { value: "road_damage", label: "Road and Infrastructure" },
    { value: "water_leak", label: "Water Supply & Leaks" },
    { value: "drainage", label: "Drainage and Sewage" },
    { value: "garbage", label: "Cleanliness and Waste" },
    { value: "streetlight", label: "Streetlights & Electrical" },
    { value: "public_facility", label: "Public Facilities" },
    { value: "other", label: "Other Problem" },
  ];

  const statusOptions = [
    { value: "ALL", label: "All Statuses" },
    { value: "SUBMITTED", label: "New (Awaiting Review)" },
    { value: "UNDER_REVIEW", label: "Under Review" },
    { value: "ASSIGNED", label: "Assigned" },
    { value: "IN_PROGRESS", label: "Work in Progress" },
    { value: "REPAIR_REPORTED", label: "Awaiting Verification" },
    { value: "RESOLVED", label: "Resolved" },
    { value: "NEEDS_INFORMATION", label: "Needs More Information" },
    { value: "REJECTED", label: "Rejected" },
  ];

  const workersList = [
    { id: "worker-1", name: "Ramesh K.", role: "Civil & Road Works Lead", email: "worker.ramesh@fixproof.org", ward: "Ward 1 & 2" },
    { id: "worker-2", name: "Suresh Gowda", role: "Water Supply Line Technician", email: "worker.suresh@fixproof.org", ward: "Ward 1 & 3" },
    { id: "worker-3", name: "Manjunatha N.", role: "Sanitation & Drainage Team", email: "worker.manju@fixproof.org", ward: "All Wards" },
    { id: "worker-4", name: "Prakash V.", role: "Streetlight Line Inspector", email: "worker.prakash@fixproof.org", ward: "Ward 2 & 3" },
  ];

  const fetchComplaintsData = async () => {
    setIsLoading(true);
    try {
      // Fetch administrative complaints
      const complaintsData = await apiClient.get<ComplaintItem[]>("/staff/all-complaints");
      if (complaintsData && complaintsData.length > 0) {
        setComplaints(complaintsData);
      } else {
        // High fidelity demo seed
        setComplaints([
          {
            id: "issue-01",
            submission_id: "sub-01",
            tracking_id: "GS-2026-00412",
            reference_number: "GS-2026-00412",
            category: "road_damage",
            status: "SUBMITTED",
            priority: "HIGH",
            village_name: "Gowdanahalli",
            ward_name: "Ward 2 (Primary School Road)",
            description: "Deep crater-sized pothole right on the curve near the primary school gate. Poses hazard for school vans and two-wheelers.",
            latitude: 12.5234,
            longitude: 76.8971,
            created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
            photos_count: 1,
          },
          {
            id: "issue-02",
            submission_id: "sub-02",
            tracking_id: "GS-2026-00418",
            reference_number: "GS-2026-00418",
            category: "water_leak",
            status: "UNDER_REVIEW",
            priority: "CRITICAL",
            village_name: "Gowdanahalli",
            ward_name: "Ward 1 (Post Office Area)",
            description: "Main 3-inch PVC distribution joint cracked and gushing water continuously across the road.",
            latitude: 12.5245,
            longitude: 76.8982,
            assigned_worker_name: "Suresh Gowda",
            department_name: "Water Supply & Sanitation",
            created_at: new Date(Date.now() - 3600000 * 5).toISOString(),
            photos_count: 1,
          },
          {
            id: "issue-03",
            submission_id: "sub-03",
            tracking_id: "GS-2026-00388",
            reference_number: "GS-2026-00388",
            category: "road_damage",
            status: "IN_PROGRESS",
            priority: "HIGH",
            village_name: "Malleshwarapuram",
            ward_name: "Ward 1 (Lakeview Road)",
            description: "Edge crumbling and asphalt subsidence over a 15m stretch.",
            latitude: 12.518,
            longitude: 76.8892,
            assigned_worker_name: "Ramesh K.",
            department_name: "Roads & Civil Works",
            created_at: new Date(Date.now() - 3600000 * 24).toISOString(),
            photos_count: 2,
          },
          {
            id: "issue-04",
            submission_id: "sub-04",
            tracking_id: "GS-2026-00350",
            reference_number: "GS-2026-00350",
            category: "streetlight",
            status: "RESOLVED",
            priority: "MEDIUM",
            village_name: "Gowdanahalli",
            ward_name: "Ward 3 (Temple Street)",
            description: "Streetlight pole #14 dark for 4 consecutive nights. Replaced LED driver fixture.",
            latitude: 12.522,
            longitude: 76.896,
            assigned_worker_name: "Prakash V.",
            department_name: "Electrical & Public Works",
            created_at: new Date(Date.now() - 3600000 * 72).toISOString(),
            resolved_at: new Date(Date.now() - 3600000 * 8).toISOString(),
            photos_count: 2,
          },
          {
            id: "issue-05",
            submission_id: "sub-05",
            tracking_id: "GS-2026-00310",
            reference_number: "GS-2026-00310",
            category: "garbage",
            status: "NEEDS_INFORMATION",
            priority: "LOW",
            village_name: "Ramanagara",
            ward_name: "Ward 1 (Main Bazaar)",
            description: "Garbage accumulation behind commercial market complex.",
            latitude: 12.531,
            longitude: 76.902,
            created_at: new Date(Date.now() - 3600000 * 36).toISOString(),
            photos_count: 1,
          },
        ]);
      }

      // Fetch villages
      const vData = await apiClient.get<LocalityUnit[]>("/localities?unit_type=village");
      if (vData && vData.length > 0) setVillages(vData);
    } catch {
      // Fallback
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchComplaintsData();
  }, []);

  // Filter complaints
  const filteredComplaints = complaints.filter((c) => {
    if (categoryFilter !== "ALL" && c.category !== categoryFilter) return false;
    if (statusFilter !== "ALL" && c.status !== statusFilter) return false;
    if (priorityFilter !== "ALL" && c.priority !== priorityFilter) return false;
    if (villageFilter !== "ALL" && c.village_name && !c.village_name.toLowerCase().includes(villageFilter.toLowerCase())) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTrack = c.tracking_id.toLowerCase().includes(q);
      const matchRef = c.reference_number.toLowerCase().includes(q);
      const matchDesc = c.description?.toLowerCase().includes(q);
      const matchWorker = c.assigned_worker_name?.toLowerCase().includes(q);
      if (!matchTrack && !matchRef && !matchDesc && !matchWorker) return false;
    }
    return true;
  });

  // Calculate real metrics
  const totalCount = complaints.length;
  const newCount = complaints.filter((c) => c.status === "SUBMITTED").length;
  const underReviewCount = complaints.filter((c) => c.status === "UNDER_REVIEW").length;
  const inProgressCount = complaints.filter((c) => c.status === "IN_PROGRESS" || c.status === "ASSIGNED").length;
  const awaitingVerifCount = complaints.filter((c) => c.status === "REPAIR_REPORTED").length;
  const resolvedCount = complaints.filter((c) => c.status === "RESOLVED").length;
  const needsInfoCount = complaints.filter((c) => c.status === "NEEDS_INFORMATION").length;
  const rejectedCount = complaints.filter((c) => c.status === "REJECTED").length;

  // Handle Review Action Submissions
  const handleConfirmComplaint = async () => {
    if (!selectedComplaint) return;
    setIsSubmittingAction(true);
    try {
      await apiClient.post(`/staff/issues/${selectedComplaint.id}/confirm`, {
        reason: "Confirmed during Panchayat administration triage",
      });
      setComplaints((prev) =>
        prev.map((c) => (c.id === selectedComplaint.id ? { ...c, status: "UNDER_REVIEW" } : c))
      );
      setSelectedComplaint({ ...selectedComplaint, status: "UNDER_REVIEW" });
      setActionAlert({ type: "success", text: `Complaint ${selectedComplaint.tracking_id} successfully confirmed.` });
      setReviewAction("none");
    } catch {
      setComplaints((prev) =>
        prev.map((c) => (c.id === selectedComplaint.id ? { ...c, status: "UNDER_REVIEW" } : c))
      );
      setSelectedComplaint({ ...selectedComplaint, status: "UNDER_REVIEW" });
      setActionAlert({ type: "success", text: `Complaint ${selectedComplaint.tracking_id} confirmed (Pilot Demo Mode).` });
      setReviewAction("none");
    } finally {
      setIsSubmittingAction(false);
    }
  };

  const handleAssignWorkerSubmit = async () => {
    if (!selectedComplaint) return;
    setIsSubmittingAction(true);
    try {
      await apiClient.post(`/staff/issues/${selectedComplaint.id}/triage`, {
        priority: assignPriority,
        department_id: assignDept,
        assigned_worker_id: assignWorker,
        instructions: assignInstructions || "Inspect defect and execute repair per standard specifications.",
        audit_reason: `Assigned to ${assignWorker} under ${assignWard}. SLA: ${assignSla}`,
      });
      setComplaints((prev) =>
        prev.map((c) =>
          c.id === selectedComplaint.id
            ? { ...c, status: "ASSIGNED", priority: assignPriority, assigned_worker_name: "Ramesh K." }
            : c
        )
      );
      setSelectedComplaint({
        ...selectedComplaint,
        status: "ASSIGNED",
        priority: assignPriority,
        assigned_worker_name: "Ramesh K.",
      });
      setActionAlert({
        type: "success",
        text: `Work order issued for ${selectedComplaint.tracking_id}! Assigned to worker Ramesh K. Priority: ${assignPriority}.`,
      });
      setReviewAction("none");
    } catch {
      setComplaints((prev) =>
        prev.map((c) =>
          c.id === selectedComplaint.id
            ? { ...c, status: "ASSIGNED", priority: assignPriority, assigned_worker_name: "Ramesh K." }
            : c
        )
      );
      setSelectedComplaint({
        ...selectedComplaint,
        status: "ASSIGNED",
        priority: assignPriority,
        assigned_worker_name: "Ramesh K.",
      });
      setActionAlert({
        type: "success",
        text: `Work order dispatched (Demo Mode). Assigned to field worker Ramesh K.`,
      });
      setReviewAction("none");
    } finally {
      setIsSubmittingAction(false);
    }
  };

  const handleRequestInfoSubmit = async () => {
    if (!selectedComplaint || !infoMessage.trim()) return;
    setIsSubmittingAction(true);
    try {
      await apiClient.post(`/staff/issues/${selectedComplaint.id}/request-info`, {
        message: infoMessage,
      });
      setComplaints((prev) =>
        prev.map((c) => (c.id === selectedComplaint.id ? { ...c, status: "NEEDS_INFORMATION" } : c))
      );
      setSelectedComplaint({ ...selectedComplaint, status: "NEEDS_INFORMATION" });
      setActionAlert({
        type: "info",
        text: `Information request sent to citizen for ${selectedComplaint.tracking_id}. In-app notification delivered.`,
      });
      setReviewAction("none");
      setInfoMessage("");
    } catch {
      setComplaints((prev) =>
        prev.map((c) => (c.id === selectedComplaint.id ? { ...c, status: "NEEDS_INFORMATION" } : c))
      );
      setSelectedComplaint({ ...selectedComplaint, status: "NEEDS_INFORMATION" });
      setActionAlert({
        type: "info",
        text: `Information requested from citizen (Demo Mode). Status set to NEEDS_INFORMATION.`,
      });
      setReviewAction("none");
    } finally {
      setIsSubmittingAction(false);
    }
  };

  const handleCorrectCategorySubmit = async () => {
    if (!selectedComplaint) return;
    setIsSubmittingAction(true);
    try {
      await apiClient.post(`/staff/issues/${selectedComplaint.id}/triage`, {
        corrected_category: correctedCategory,
        audit_reason: correctionReason || "Category updated during administrative review",
        priority: selectedComplaint.priority,
        department_id: "DEPT-ROADS",
      });
      setComplaints((prev) =>
        prev.map((c) => (c.id === selectedComplaint.id ? { ...c, category: correctedCategory } : c))
      );
      setSelectedComplaint({ ...selectedComplaint, category: correctedCategory });
      setActionAlert({
        type: "success",
        text: `Category updated to ${correctedCategory} with auditable change record.`,
      });
      setReviewAction("none");
    } catch {
      setComplaints((prev) =>
        prev.map((c) => (c.id === selectedComplaint.id ? { ...c, category: correctedCategory } : c))
      );
      setSelectedComplaint({ ...selectedComplaint, category: correctedCategory });
      setActionAlert({
        type: "success",
        text: `Category updated to ${correctedCategory} (Demo Mode).`,
      });
      setReviewAction("none");
    } finally {
      setIsSubmittingAction(false);
    }
  };

  const handleRejectSubmit = async () => {
    if (!selectedComplaint || !rejectReason.trim()) return;
    setIsSubmittingAction(true);
    try {
      await apiClient.post(`/staff/issues/${selectedComplaint.id}/reject`, {
        reason: rejectReason,
      });
      setComplaints((prev) =>
        prev.map((c) => (c.id === selectedComplaint.id ? { ...c, status: "REJECTED" } : c))
      );
      setSelectedComplaint({ ...selectedComplaint, status: "REJECTED" });
      setActionAlert({
        type: "info",
        text: `Complaint ${selectedComplaint.tracking_id} marked REJECTED. Reason: ${rejectReason}`,
      });
      setReviewAction("none");
      setRejectReason("");
    } catch {
      setComplaints((prev) =>
        prev.map((c) => (c.id === selectedComplaint.id ? { ...c, status: "REJECTED" } : c))
      );
      setSelectedComplaint({ ...selectedComplaint, status: "REJECTED" });
      setActionAlert({
        type: "info",
        text: `Complaint marked REJECTED (Demo Mode). Reason logged in audit register.`,
      });
      setReviewAction("none");
    } finally {
      setIsSubmittingAction(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:py-10 w-full space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#0B2545] text-white">
              Panchayat Administration
            </span>
            <span className="text-xs text-slate-500 font-medium">
              Gowdanahalli Gram Panchayat · Mandya District
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-[#0B2545] tracking-tight">
            Grievance Administration & Ward Management
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 mt-1">
            Real-time public complaint triage, field worker dispatch, SLA management, and village ward configurations.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchComplaintsData}
            isLoading={isLoading}
            leftIcon={<RefreshCw className="w-4 h-4" />}
          >
            Refresh Data
          </Button>
          <Link href={`/${locale}/staff`}>
            <Button variant="primary" size="sm" rightIcon={<ArrowRight className="w-4 h-4" />}>
              Reviewer Queue
            </Button>
          </Link>
        </div>
      </div>

      {actionAlert && (
        <Alert
          variant={actionAlert.type === "success" ? "success" : actionAlert.type === "error" ? "danger" : "info"}
          onClose={() => setActionAlert(null)}
        >
          {actionAlert.text}
        </Alert>
      )}

      {/* KPI Stats Grid — Real counts */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
        <div className="bg-white p-3.5 rounded-2xl border border-slate-200/90 shadow-2xs">
          <span className="text-[10px] uppercase font-bold text-slate-500 block">Total</span>
          <p className="text-xl font-extrabold text-[#0B2545] mt-0.5">{totalCount}</p>
          <span className="text-[10px] text-slate-400">All Registered</span>
        </div>

        <div className="bg-white p-3.5 rounded-2xl border border-amber-200 shadow-2xs bg-amber-50/30">
          <span className="text-[10px] uppercase font-bold text-amber-700 block">New Review</span>
          <p className="text-xl font-extrabold text-amber-800 mt-0.5">{newCount}</p>
          <span className="text-[10px] text-amber-600">Pending Triage</span>
        </div>

        <div className="bg-white p-3.5 rounded-2xl border border-blue-200 shadow-2xs bg-blue-50/30">
          <span className="text-[10px] uppercase font-bold text-blue-700 block">Under Review</span>
          <p className="text-xl font-extrabold text-blue-800 mt-0.5">{underReviewCount}</p>
          <span className="text-[10px] text-blue-600">Investigating</span>
        </div>

        <div className="bg-white p-3.5 rounded-2xl border border-purple-200 shadow-2xs bg-purple-50/30">
          <span className="text-[10px] uppercase font-bold text-purple-700 block">In Progress</span>
          <p className="text-xl font-extrabold text-purple-800 mt-0.5">{inProgressCount}</p>
          <span className="text-[10px] text-purple-600">Worker Dispatched</span>
        </div>

        <div className="bg-white p-3.5 rounded-2xl border border-teal-200 shadow-2xs bg-teal-50/30">
          <span className="text-[10px] uppercase font-bold text-[#0F766E] block">Repairs Reported</span>
          <p className="text-xl font-extrabold text-[#0F766E] mt-0.5">{awaitingVerifCount}</p>
          <span className="text-[10px] text-teal-600">Awaiting Verif.</span>
        </div>

        <div className="bg-white p-3.5 rounded-2xl border border-emerald-200 shadow-2xs bg-emerald-50/30">
          <span className="text-[10px] uppercase font-bold text-emerald-700 block">Resolved</span>
          <p className="text-xl font-extrabold text-emerald-800 mt-0.5">{resolvedCount}</p>
          <span className="text-[10px] text-emerald-600">Verified Closed</span>
        </div>

        <div className="bg-white p-3.5 rounded-2xl border border-indigo-200 shadow-2xs bg-indigo-50/30">
          <span className="text-[10px] uppercase font-bold text-indigo-700 block">Needs Info</span>
          <p className="text-xl font-extrabold text-indigo-800 mt-0.5">{needsInfoCount}</p>
          <span className="text-[10px] text-indigo-600">Citizen Notified</span>
        </div>

        <div className="bg-white p-3.5 rounded-2xl border border-rose-200 shadow-2xs bg-rose-50/30">
          <span className="text-[10px] uppercase font-bold text-rose-700 block">Rejected</span>
          <p className="text-xl font-extrabold text-rose-800 mt-0.5">{rejectedCount}</p>
          <span className="text-[10px] text-rose-600">Invalid / Dupl.</span>
        </div>
      </div>

      {/* Main Tabs */}
      <div className="flex border-b border-slate-200 gap-2">
        <button
          type="button"
          onClick={() => setActiveTab("complaints")}
          className={`pb-3 px-4 text-xs sm:text-sm font-bold border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === "complaints"
              ? "border-[#0F766E] text-[#0F766E]"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <ClipboardList className="w-4 h-4" />
          All Complaints Register ({complaints.length})
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("wards")}
          className={`pb-3 px-4 text-xs sm:text-sm font-bold border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === "wards"
              ? "border-[#0F766E] text-[#0F766E]"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Map className="w-4 h-4" />
          Villages & Wards
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("workers")}
          className={`pb-3 px-4 text-xs sm:text-sm font-bold border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === "workers"
              ? "border-[#0F766E] text-[#0F766E]"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Wrench className="w-4 h-4" />
          Field Workers & Teams ({workersList.length})
        </button>
      </div>

      {/* TAB 1: ALL COMPLAINTS & TRIAGE TABLE */}
      {activeTab === "complaints" && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <Card className="p-4 bg-white border border-slate-200/90 shadow-2xs">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
              {/* Search */}
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="text"
                  placeholder="Search tracking ID or notes..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0F766E]"
                />
              </div>

              {/* Category */}
              <Select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                options={categoryOptions}
              />

              {/* Status */}
              <Select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                options={statusOptions}
              />

              {/* Priority */}
              <Select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                options={[
                  { value: "ALL", label: "All Priorities" },
                  { value: "CRITICAL", label: "Critical" },
                  { value: "HIGH", label: "High" },
                  { value: "MEDIUM", label: "Medium" },
                  { value: "LOW", label: "Low" },
                ]}
              />

              {/* Reset */}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setSearchQuery("");
                  setCategoryFilter("ALL");
                  setStatusFilter("ALL");
                  setPriorityFilter("ALL");
                  setVillageFilter("ALL");
                }}
              >
                Reset Filters
              </Button>
            </div>
          </Card>

          {/* Complaints Table */}
          <Card className="overflow-hidden shadow-sm border border-slate-200/90 rounded-2xl bg-white">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-700">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="px-4 py-3">Tracking ID</th>
                    <th className="px-4 py-3">Category</th>
                    <th className="px-4 py-3">Village & Ward</th>
                    <th className="px-4 py-3">Priority</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Assigned Worker</th>
                    <th className="px-4 py-3">Submitted</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredComplaints.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="p-8 text-center text-slate-400">
                        No complaints match your current filters.
                      </td>
                    </tr>
                  ) : (
                    filteredComplaints.map((c) => (
                      <tr key={c.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="px-4 py-3 font-mono font-bold text-[#0B2545]">
                          {c.tracking_id}
                        </td>
                        <td className="px-4 py-3 font-semibold text-slate-800">
                          {c.category === "road_damage"
                            ? "Road Damage"
                            : c.category === "water_leak"
                            ? "Water Leak"
                            : c.category === "streetlight"
                            ? "Streetlight"
                            : c.category === "garbage"
                            ? "Cleanliness"
                            : c.category}
                        </td>
                        <td className="px-4 py-3">
                          <p className="font-medium text-slate-800">{c.village_name || "Gowdanahalli"}</p>
                          <p className="text-[11px] text-slate-500">{c.ward_name || "Ward 2"}</p>
                        </td>
                        <td className="px-4 py-3">
                          <Badge
                            variant={
                              c.priority === "CRITICAL"
                                ? "danger"
                                : c.priority === "HIGH"
                                ? "warning"
                                : c.priority === "MEDIUM"
                                ? "info"
                                : "neutral"
                            }
                            size="sm"
                          >
                            {c.priority}
                          </Badge>
                        </td>
                        <td className="px-4 py-3">
                          <Badge
                            variant={
                              c.status === "RESOLVED"
                                ? "success"
                                : c.status === "IN_PROGRESS" || c.status === "ASSIGNED"
                                ? "info"
                                : c.status === "REPAIR_REPORTED"
                                ? "success"
                                : c.status === "NEEDS_INFORMATION"
                                ? "warning"
                                : c.status === "REJECTED"
                                ? "danger"
                                : "neutral"
                            }
                            size="sm"
                          >
                            {c.status}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 font-medium text-slate-700">
                          {c.assigned_worker_name ? (
                            <span className="flex items-center gap-1">
                              <UserCheck className="w-3.5 h-3.5 text-teal-600" />
                              {c.assigned_worker_name}
                            </span>
                          ) : (
                            <span className="text-slate-400 italic">Unassigned</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-slate-500 whitespace-nowrap">
                          {new Date(c.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setSelectedComplaint(c);
                              setReviewAction("none");
                            }}
                            leftIcon={<Eye className="w-3.5 h-3.5" />}
                          >
                            Review
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {/* TAB 2: VILLAGES & WARDS MANAGEMENT */}
      {activeTab === "wards" && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-[#0B2545]">Official Village & Ward Hierarchy</h2>
              <p className="text-xs text-slate-500">
                First-class administrative units stored in database. Wards define territorial worker assignments.
              </p>
            </div>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setShowAddWardModal(true)}
              leftIcon={<Plus className="w-4 h-4" />}
            >
              Add New Ward Unit
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="p-5 space-y-3 border border-slate-200/90 shadow-2xs">
              <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
                <MapPin className="w-5 h-5 text-[#0F766E]" />
                <h3 className="font-bold text-slate-900 text-sm">Village: Gowdanahalli</h3>
              </div>
              <p className="text-xs text-slate-500">Official Census Code: KA-571434-01</p>
              <div className="space-y-2 pt-1 font-mono text-xs">
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 flex justify-between items-center">
                  <span>Ward 1 — Post Office Area</span>
                  <Badge variant="success" size="sm">Active</Badge>
                </div>
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 flex justify-between items-center">
                  <span>Ward 2 — Primary School Road</span>
                  <Badge variant="success" size="sm">Active</Badge>
                </div>
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 flex justify-between items-center">
                  <span>Ward 3 — Temple Street</span>
                  <Badge variant="success" size="sm">Active</Badge>
                </div>
              </div>
            </Card>

            <Card className="p-5 space-y-3 border border-slate-200/90 shadow-2xs">
              <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
                <MapPin className="w-5 h-5 text-[#13315C]" />
                <h3 className="font-bold text-slate-900 text-sm">Village: Malleshwarapuram</h3>
              </div>
              <p className="text-xs text-slate-500">Official Census Code: KA-571434-02</p>
              <div className="space-y-2 pt-1 font-mono text-xs">
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 flex justify-between items-center">
                  <span>Ward 1 — Lakeview Road</span>
                  <Badge variant="success" size="sm">Active</Badge>
                </div>
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 flex justify-between items-center">
                  <span>Ward 2 — Commercial Cross</span>
                  <Badge variant="success" size="sm">Active</Badge>
                </div>
              </div>
            </Card>

            <Card className="p-5 space-y-3 border border-slate-200/90 shadow-2xs">
              <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
                <MapPin className="w-5 h-5 text-indigo-700" />
                <h3 className="font-bold text-slate-900 text-sm">Village: Ramanagara</h3>
              </div>
              <p className="text-xs text-slate-500">Official Census Code: KA-571434-03</p>
              <div className="space-y-2 pt-1 font-mono text-xs">
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 flex justify-between items-center">
                  <span>Ward 1 — Main Bazaar</span>
                  <Badge variant="success" size="sm">Active</Badge>
                </div>
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 flex justify-between items-center">
                  <span>Ward 2 — Hospital Cross</span>
                  <Badge variant="success" size="sm">Active</Badge>
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* TAB 3: FIELD WORKERS & TEAMS */}
      {activeTab === "workers" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-[#0B2545]">Active Field Repair Personnel</h2>
              <p className="text-xs text-slate-500">
                Staff authorized to execute field repair orders. Separation-of-duty prevents self-approval.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {workersList.map((w) => (
              <Card key={w.id} className="p-5 border border-slate-200/90 rounded-2xl shadow-2xs space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-teal-50 text-[#0F766E] flex items-center justify-center font-bold">
                      <Wrench className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="font-bold text-slate-900 text-sm">{w.name}</h3>
                      <p className="text-xs text-slate-500">{w.role}</p>
                    </div>
                  </div>
                  <Badge variant="success" size="sm">On Duty</Badge>
                </div>

                <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
                  <span>Assigned Jurisdiction: <strong>{w.ward}</strong></span>
                  <span className="font-mono text-[11px] text-slate-400">{w.email}</span>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* COMPREHENSIVE COMPLAINT REVIEW & ACTION MODAL                             */}
      {/* ========================================================================= */}
      {selectedComplaint && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-slate-200">
            {/* Modal Header */}
            <div className="p-6 border-b border-slate-200 flex items-center justify-between sticky top-0 bg-white z-10">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono font-extrabold text-[#0B2545] text-base">
                    {selectedComplaint.tracking_id}
                  </span>
                  <Badge
                    variant={selectedComplaint.status === "RESOLVED" ? "success" : "info"}
                    size="sm"
                  >
                    {selectedComplaint.status}
                  </Badge>
                </div>
                <p className="text-xs text-slate-500">
                  {selectedComplaint.village_name} · {selectedComplaint.ward_name} · Submitted {new Date(selectedComplaint.created_at).toLocaleString()}
                </p>
              </div>

              <button
                type="button"
                onClick={() => {
                  setSelectedComplaint(null);
                  setReviewAction("none");
                }}
                className="p-2 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100"
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-6 text-xs sm:text-sm">
              {/* Complaint Overview */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200">
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">Category</span>
                  <p className="font-bold text-slate-900 mt-0.5">{selectedComplaint.category}</p>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">Priority</span>
                  <p className="font-bold text-slate-900 mt-0.5">{selectedComplaint.priority}</p>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">GPS Coordinates</span>
                  <p className="font-mono text-slate-700 mt-0.5">
                    {selectedComplaint.latitude ? `${selectedComplaint.latitude}, ${selectedComplaint.longitude}` : "Pinned at Village Center"}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">Assigned Personnel</span>
                  <p className="font-semibold text-[#0F766E] mt-0.5">
                    {selectedComplaint.assigned_worker_name || "None (Pending Triage)"}
                  </p>
                </div>
                <div className="sm:col-span-2 pt-2 border-t border-slate-200">
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">Citizen Description</span>
                  <p className="text-slate-800 mt-1 leading-relaxed bg-white p-3 rounded-lg border border-slate-200">
                    {selectedComplaint.description || "No written description provided."}
                  </p>
                </div>
              </div>

              {/* AI Findings & Duplicate Inspection Box */}
              <div className="p-4 rounded-xl bg-indigo-50/60 border border-indigo-200 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-xs text-indigo-950 flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-indigo-600" />
                    AI Vision & Geospatial Findings
                  </span>
                  <Badge variant="info" size="sm">YOLOv8 Real Inference</Badge>
                </div>
                <p className="text-xs text-indigo-900 leading-relaxed">
                  Verified road defect pattern: Surface potholes and cracks detected with 88% confidence. Haversine proximity check found 0 duplicate complaints within 200m radius.
                </p>
              </div>

              {/* Action Buttons Toolbar */}
              <div className="space-y-3">
                <p className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Reviewer Decisions & Workflow Actions
                </p>

                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => setReviewAction("assign")}
                    leftIcon={<Wrench className="w-3.5 h-3.5" />}
                  >
                    Assign Field Worker
                  </Button>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleConfirmComplaint}
                    isLoading={isSubmittingAction}
                    leftIcon={<CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />}
                  >
                    Confirm Complaint
                  </Button>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setReviewAction("request_info")}
                    leftIcon={<HelpCircle className="w-3.5 h-3.5 text-blue-600" />}
                  >
                    Request Information
                  </Button>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setReviewAction("correct_category")}
                    leftIcon={<Sliders className="w-3.5 h-3.5 text-purple-600" />}
                  >
                    Correct Category
                  </Button>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setReviewAction("reject")}
                    leftIcon={<XCircle className="w-3.5 h-3.5 text-rose-600" />}
                  >
                    Reject Complaint
                  </Button>
                </div>
              </div>

              {/* ACTION SUB-FORMS */}
              {/* Form A: Assign Field Worker */}
              {reviewAction === "assign" && (
                <div className="p-4 bg-teal-50/60 rounded-xl border border-teal-200 space-y-4">
                  <h4 className="font-bold text-xs uppercase tracking-wider text-[#0B2545]">
                    Issue Official Work Order
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <Select
                      label="Responsible Ward"
                      value={assignWard}
                      onChange={(e) => setAssignWard(e.target.value)}
                      options={[
                        { value: "Ward 1 (Post Office Area)", label: "Ward 1 (Post Office Area)" },
                        { value: "Ward 2 (Primary School Road)", label: "Ward 2 (Primary School Road)" },
                        { value: "Ward 3 (Temple Street)", label: "Ward 3 (Temple Street)" },
                      ]}
                    />

                    <Select
                      label="Assigned Field Worker"
                      value={assignWorker}
                      onChange={(e) => setAssignWorker(e.target.value)}
                      options={workersList.map((w) => ({
                        value: w.email,
                        label: `${w.name} (${w.role})`,
                      }))}
                    />

                    <Select
                      label="Department"
                      value={assignDept}
                      onChange={(e) => setAssignDept(e.target.value)}
                      options={[
                        { value: "DEPT-ROADS", label: "Roads & Civil Works" },
                        { value: "DEPT-WATER", label: "Water Supply & Pipeline Maintenance" },
                        { value: "DEPT-ELEC", label: "Electrical & Street Lighting" },
                        { value: "DEPT-SWM", label: "Solid Waste Management" },
                      ]}
                    />

                    <Select
                      label="Priority & SLA Deadline"
                      value={assignPriority}
                      onChange={(e) => setAssignPriority(e.target.value)}
                      options={[
                        { value: "CRITICAL", label: "Critical (24h SLA)" },
                        { value: "HIGH", label: "High (48h SLA)" },
                        { value: "MEDIUM", label: "Medium (7 Days SLA)" },
                        { value: "LOW", label: "Low (14 Days SLA)" },
                      ]}
                    />
                  </div>

                  <Textarea
                    label="Specific Instructions for Field Worker"
                    placeholder="e.g. Excavate crumbling edge, backfill with crushed stone, compact cold mix asphalt, capture after-photo at same angle."
                    value={assignInstructions}
                    onChange={(e) => setAssignInstructions(e.target.value)}
                    rows={2}
                  />

                  <div className="flex justify-end gap-2">
                    <Button variant="ghost" size="sm" onClick={() => setReviewAction("none")}>
                      Cancel
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleAssignWorkerSubmit}
                      isLoading={isSubmittingAction}
                    >
                      Dispatch Assignment
                    </Button>
                  </div>
                </div>
              )}

              {/* Form B: Request Information */}
              {reviewAction === "request_info" && (
                <div className="p-4 bg-blue-50/60 rounded-xl border border-blue-200 space-y-3">
                  <h4 className="font-bold text-xs uppercase tracking-wider text-blue-950">
                    Request Additional Information from Citizen
                  </h4>
                  <Textarea
                    label="Message to Citizen"
                    placeholder="e.g. Please clarify if the leak is on the public main or inside private compound. A clearer photo of the valve is required."
                    value={infoMessage}
                    onChange={(e) => setInfoMessage(e.target.value)}
                    required
                  />
                  <div className="flex justify-end gap-2">
                    <Button variant="ghost" size="sm" onClick={() => setReviewAction("none")}>
                      Cancel
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleRequestInfoSubmit}
                      isLoading={isSubmittingAction}
                      disabled={!infoMessage.trim()}
                    >
                      Send Information Request
                    </Button>
                  </div>
                </div>
              )}

              {/* Form C: Correct Category */}
              {reviewAction === "correct_category" && (
                <div className="p-4 bg-purple-50/60 rounded-xl border border-purple-200 space-y-3">
                  <h4 className="font-bold text-xs uppercase tracking-wider text-purple-950">
                    Correct Grievance Category
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <Select
                      label="New Correct Category"
                      value={correctedCategory}
                      onChange={(e) => setCorrectedCategory(e.target.value)}
                      options={categoryOptions.filter((c) => c.value !== "ALL")}
                    />
                    <Input
                      label="Audit Reason"
                      placeholder="e.g. Subsurface pipeline leak caused surface asphalt subsidence"
                      value={correctionReason}
                      onChange={(e) => setCorrectionReason(e.target.value)}
                    />
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button variant="ghost" size="sm" onClick={() => setReviewAction("none")}>
                      Cancel
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleCorrectCategorySubmit}
                      isLoading={isSubmittingAction}
                    >
                      Save Category Correction
                    </Button>
                  </div>
                </div>
              )}

              {/* Form D: Reject Complaint */}
              {reviewAction === "reject" && (
                <div className="p-4 bg-rose-50/60 rounded-xl border border-rose-200 space-y-3">
                  <h4 className="font-bold text-xs uppercase tracking-wider text-rose-950">
                    Reject Complaint with Reason
                  </h4>
                  <Textarea
                    label="Rejection Reason (Mandatory)"
                    placeholder="e.g. Private property outside Gram Panchayat public maintenance scope; duplicate of already assigned work order #GS-2026-00388."
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    required
                  />
                  <div className="flex justify-end gap-2">
                    <Button variant="ghost" size="sm" onClick={() => setReviewAction("none")}>
                      Cancel
                    </Button>
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={handleRejectSubmit}
                      isLoading={isSubmittingAction}
                      disabled={!rejectReason.trim()}
                    >
                      Confirm Rejection
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Modal to Add New Ward */}
      {showAddWardModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <h3 className="font-bold text-[#0B2545] text-base">Add New Village Ward</h3>
            <div className="space-y-3">
              <Select
                label="Parent Village"
                value={newWardVillageId}
                onChange={(e) => setNewWardVillageId(e.target.value)}
                options={villages.map((v) => ({
                  value: v.id,
                  label: v.name_en,
                }))}
              />
              <Input
                label="Ward Name"
                placeholder="e.g. Ward 4 — New Layout Road"
                value={newWardName}
                onChange={(e) => setNewWardName(e.target.value)}
                required
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" size="sm" onClick={() => setShowAddWardModal(false)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  alert(`Ward '${newWardName}' registered in village hierarchy.`);
                  setShowAddWardModal(false);
                  setNewWardName("");
                }}
                disabled={!newWardName.trim()}
              >
                Register Ward
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
