"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import {
  LayoutDashboard,
  ClipboardList,
  Clock,
  Activity,
  FileCheck,
  AlertTriangle,
  History,
  MapPin,
  User,
  Wrench,
  Camera,
  CheckCircle2,
  XCircle,
  Upload,
  ArrowRight,
  RefreshCw,
  Send,
  Navigation,
  FileText,
  Building2,
  Phone,
  Mail,
  ShieldCheck,
  RotateCcw,
} from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { LeafletMap, MapComplaint } from "@/components/ui/LeafletMap";
import { GramaSevaLogo } from "@/components/ui/GramaSevaLogo";

type WorkerSection =
  | "overview"
  | "assignments"
  | "pending"
  | "in_progress"
  | "awaiting_verification"
  | "correction_required"
  | "history"
  | "map"
  | "profile";

interface WorkerTask {
  assignment_id: string;
  issue_id: string;
  reference_number: string;
  category: string;
  status: string;
  priority: string;
  instructions?: string;
  village_name?: string;
  ward_name?: string;
  latitude?: number;
  longitude?: number;
  assigned_at: string;
  description?: string;
  worker_notes?: string;
  citizen_photo_ids?: string[];
  worker_after_photo_ids?: string[];
  estimated_cost?: number;
  proposed_cost?: number;
  materials_cost?: number;
  labour_cost?: number;
  other_expenses_cost?: number;
  verified_cost?: number;
  cost_status?: string;
  pdo_remarks?: string;
  work_completed_at?: string;
}

interface WorkerStatus {
  is_approved: boolean;
  approval_status: string;
  village_name?: string;
  jurisdiction_unit_id?: string;
  worker_name?: string;
  email?: string;
}

export default function WorkerDashboard() {
  const locale = useLocale();
  const [activeSection, setActiveSection] = useState<WorkerSection>("overview");
  const [isLoading, setIsLoading] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Status & Tasks
  const [workerStatus, setWorkerStatus] = useState<WorkerStatus | null>(null);
  const [tasks, setTasks] = useState<WorkerTask[]>([]);
  const [selectedTask, setSelectedTask] = useState<WorkerTask | null>(null);

  // Form states
  const [progressNotes, setProgressNotes] = useState("");
  const [evidenceNotes, setEvidenceNotes] = useState("");
  const [declineReason, setDeclineReason] = useState("");
  const [showDeclineModal, setShowDeclineModal] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Work Completion Form states
  const [showCompletionModal, setShowCompletionModal] = useState(false);
  const [completionTask, setCompletionTask] = useState<WorkerTask | null>(null);
  const [workDescription, setWorkDescription] = useState("");
  const [workPerformed, setWorkPerformed] = useState("");
  const [materialsUsed, setMaterialsUsed] = useState("");
  const [labourDetails, setLabourDetails] = useState("");
  const [materialsCost, setMaterialsCost] = useState<number | "">("");
  const [labourCost, setLabourCost] = useState<number | "">("");
  const [otherExpensesCost, setOtherExpensesCost] = useState<number | "">("");
  const [completionDate, setCompletionDate] = useState(new Date().toISOString().split("T")[0]);
  const [uploadedAfterMediaIds, setUploadedAfterMediaIds] = useState<string[]>([]);
  const [afterImagePreviews, setAfterImagePreviews] = useState<string[]>([]);
  const [isUploadingPhoto, setIsUploadingPhoto] = useState(false);

  // Worker GPS
  const [workerLat, setWorkerLat] = useState<number | null>(null);
  const [workerLng, setWorkerLng] = useState<number | null>(null);

  const loadWorkerData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // 1. Fetch status
      const statusRes = await apiClient.get<WorkerStatus>("/worker/status").catch(() => {
        // Fallback from localStorage if needed
        const raw = typeof window !== "undefined" ? localStorage.getItem("gramaseva_user") : null;
        if (raw) {
          const user = JSON.parse(raw);
          return {
            is_approved: user.is_approved ?? true,
            approval_status: user.approval_status || "APPROVED",
            worker_name: user.full_name,
            email: user.email,
          };
        }
        return { is_approved: true, approval_status: "APPROVED" };
      });

      setWorkerStatus(statusRes);

      // If approved, load tasks
      if (statusRes.is_approved && statusRes.approval_status !== "PENDING") {
        const tasksRes = await apiClient.get<WorkerTask[]>("/worker/tasks").catch(() => []);
        const loadedTasks = tasksRes || [];
        setTasks(loadedTasks);
        if (loadedTasks.length > 0) {
          if (!selectedTask || !loadedTasks.some((t) => t.assignment_id === selectedTask.assignment_id)) {
            setSelectedTask(loadedTasks[0]);
          }
        } else {
          setSelectedTask(null);
        }
      }
    } catch (err: any) {
      setError(err.message || "Failed to load worker workspace");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadWorkerData();
  }, []);

  // Worker Action: Start Work / Accept
  const handleAcceptTask = async (task: WorkerTask) => {
    try {
      await apiClient.post(`/worker/assignments/${task.assignment_id}/accept`);
      setNotice(`Task ${task.reference_number} accepted. Status updated to IN_PROGRESS.`);
      loadWorkerData();
    } catch (err: any) {
      setError(err.message || "Failed to accept task");
    }
  };

  // Worker Action: Add Progress Notes
  const handleAddProgressNote = async (task: WorkerTask) => {
    if (!progressNotes.trim()) return;
    try {
      await apiClient.post(`/worker/issues/${task.issue_id}/progress-notes`, {
        notes: progressNotes.trim(),
        latitude: workerLat,
        longitude: workerLng,
      });
      setNotice("Progress update recorded.");
      setProgressNotes("");
      loadWorkerData();
    } catch (err: any) {
      setError(err.message || "Failed to save progress update");
    }
  };

  // Open Work Completion Modal
  const openCompletionModal = (task: WorkerTask) => {
    setCompletionTask(task);
    setWorkDescription(task.description || "");
    setWorkPerformed(task.instructions ? `Executed: ${task.instructions}` : "");
    setMaterialsUsed("");
    setLabourDetails("");
    setMaterialsCost(task.materials_cost ?? "");
    setLabourCost(task.labour_cost ?? "");
    setOtherExpensesCost(task.other_expenses_cost ?? "");
    setUploadedAfterMediaIds(task.worker_after_photo_ids ?? []);
    setAfterImagePreviews([]);
    setShowCompletionModal(true);
  };

  // Upload After-Work Photo
  const handleUploadAfterPhoto = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0 || !completionTask) return;
    const file = e.target.files[0];
    const previewUrl = URL.createObjectURL(file);
    setAfterImagePreviews((prev) => [...prev, previewUrl]);

    setIsUploadingPhoto(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await apiClient.post<{ media_id: string; evidence_role: string; file_hash: string }>(
        `/worker/issues/${completionTask.issue_id}/repair-evidence`,
        formData
      );
      if (res && res.media_id) {
        setUploadedAfterMediaIds((prev) => [...prev, res.media_id]);
        setNotice("After-work repair photograph uploaded successfully.");
      }
    } catch (err: any) {
      setError(err.message || "Failed to upload photo evidence");
    } finally {
      setIsUploadingPhoto(false);
    }
  };

  // Submit Completion and Costs
  const handleSubmitCompletion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!completionTask) return;

    if (
      uploadedAfterMediaIds.length === 0 &&
      (!completionTask.worker_after_photo_ids || completionTask.worker_after_photo_ids.length === 0)
    ) {
      setError("Please upload at least one photograph of the completed repair work.");
      return;
    }

    if (!workDescription.trim()) {
      setError("Please provide a work completion description.");
      return;
    }

    const mat = typeof materialsCost === "number" ? materialsCost : 0;
    const lab = typeof labourCost === "number" ? labourCost : 0;
    const oth = typeof otherExpensesCost === "number" ? otherExpensesCost : 0;
    const totalProposed = mat + lab + oth;

    setIsSubmitting(true);
    try {
      await apiClient.post(`/worker/issues/${completionTask.issue_id}/completion`, {
        work_description: workDescription.trim(),
        work_performed: workPerformed.trim() || undefined,
        materials_used: materialsUsed.trim() || undefined,
        labour_details: labourDetails.trim() || undefined,
        materials_cost: mat,
        labour_cost: lab,
        other_expenses_cost: oth,
        proposed_cost: totalProposed,
        completion_date: completionDate,
        after_media_ids: uploadedAfterMediaIds,
      });

      setNotice(
        `Work completion & proposed expenditure (₹${totalProposed.toLocaleString("en-IN")}) submitted to Village PDO for verification.`
      );
      setShowCompletionModal(false);
      setCompletionTask(null);
      setWorkDescription("");
      setWorkPerformed("");
      setMaterialsUsed("");
      setLabourDetails("");
      setMaterialsCost("");
      setLabourCost("");
      setOtherExpensesCost("");
      setUploadedAfterMediaIds([]);
      setAfterImagePreviews([]);
      loadWorkerData();
    } catch (err: any) {
      setError(err.message || "Failed to submit work completion");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Worker Action: Submit for PDO Verification (CANNOT mark resolved)
  const handleSubmitForVerification = async (task: WorkerTask) => {
    openCompletionModal(task);
  };

  // Geolocation trigger
  const handleCaptureGps = () => {
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setWorkerLat(pos.coords.latitude);
          setWorkerLng(pos.coords.longitude);
          setNotice("GPS coordinates tagged successfully.");
        },
        () => {
          setNotice("Using approximate Panchayat centroid coordinates.");
          setWorkerLat(12.502);
          setWorkerLng(76.685);
        }
      );
    }
  };

  // Gate check: If worker is pending approval, show dedicated Account Pending Screen
  if (workerStatus && (!workerStatus.is_approved || workerStatus.approval_status === "PENDING")) {
    return (
      <div className="min-h-screen bg-[#F4F8FC] flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
        <div className="sm:mx-auto sm:w-full sm:max-w-lg">
          <div className="flex justify-center mb-4">
            <GramaSevaLogo size="md" />
          </div>

          <div className="bg-white border-2 border-amber-300 rounded-3xl shadow-xl overflow-hidden">
            <div className="bg-amber-500/10 border-b border-amber-200 px-6 py-5 flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-amber-500/20 text-amber-800 flex items-center justify-center shrink-0">
                <Clock className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-amber-950">
                  Worker Authorization Pending
                </h2>
                <p className="text-xs text-amber-800">
                  Panchayat Development Officer (PDO) Approval Required
                </p>
              </div>
            </div>

            <div className="p-6 sm:p-8 space-y-5 text-sm">
              <p className="text-[#40536B] leading-relaxed">
                Your field worker account is currently{" "}
                <strong className="text-amber-900 bg-amber-100 px-2 py-0.5 rounded">
                  PENDING PDO APPROVAL
                </strong>
                . In accordance with GramaSeva governance, field technicians cannot access complaints or accept assignments until authorized by the local Gram Panchayat.
              </p>

              <div className="rounded-2xl bg-[#F4F8FC] border border-[#DCE5EE] p-4 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-[#40536B]">Worker Account:</span>
                  <span className="font-bold text-[#102B4E]">{workerStatus.email || "Registered Technician"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#40536B]">Assigned GP:</span>
                  <span className="font-bold text-[#087F78]">{workerStatus.village_name || "Assigned Gram Panchayat"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#40536B]">Approval Authority:</span>
                  <span className="font-bold text-[#102B4E]">Village PDO</span>
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={loadWorkerData}
                  className="flex-1 h-11 px-4 rounded-xl bg-[#087F78] hover:bg-[#066B65] text-white font-semibold text-xs sm:text-sm flex items-center justify-center gap-2 shadow-2xs"
                >
                  <RotateCcw className="w-4 h-4" />
                  <span>Refresh Approval Status</span>
                </button>
                <Link href={`/${locale}/login`} className="flex-1">
                  <button
                    type="button"
                    className="w-full h-11 px-4 rounded-xl bg-white hover:bg-slate-50 text-[#102B4E] border border-[#DCE5EE] font-semibold text-xs sm:text-sm flex items-center justify-center"
                  >
                    Switch Account
                  </button>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Task filtering
  const pendingTasks = tasks.filter((t) => t.status === "ASSIGNED");
  const inProgressTasks = tasks.filter((t) => t.status === "IN_PROGRESS");
  const awaitingVerificationTasks = tasks.filter(
    (t) => t.status === "REPAIR_REPORTED" || t.status === "AWAITING_VERIFICATION"
  );
  const returnedTasks = tasks.filter((t) => t.status === "REOPENED" || t.status === "RETURNED");
  const historyTasks = tasks.filter((t) => t.status === "RESOLVED");

  // Map Tasks for worker map
  const workerMapComplaints: MapComplaint[] = tasks
    .filter((t) => typeof t.latitude === "number" && typeof t.longitude === "number")
    .map((t) => ({
      id: t.issue_id,
      reference_number: t.reference_number,
      category: t.category,
      status: t.status,
      latitude: t.latitude!,
      longitude: t.longitude!,
      description: t.description || t.instructions,
      priority: t.priority,
      village_name: t.village_name,
    }));

  const navItems = [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "assignments", label: "My Assignments", icon: ClipboardList, badge: tasks.length },
    { id: "pending", label: "Pending Tasks", icon: Clock, badge: pendingTasks.length },
    { id: "in_progress", label: "In Progress", icon: Activity, badge: inProgressTasks.length },
    {
      id: "awaiting_verification",
      label: "Awaiting Verification",
      icon: FileCheck,
      badge: awaitingVerificationTasks.length,
    },
    {
      id: "correction_required",
      label: "Correction Required",
      icon: AlertTriangle,
      badge: returnedTasks.length,
      highlight: returnedTasks.length > 0,
    },
    { id: "history", label: "Work History", icon: History, badge: historyTasks.length },
    { id: "map", label: "Task Map", icon: MapPin },
    { id: "profile", label: "Profile", icon: User },
  ];

  return (
    <div className="min-h-screen bg-[#F4F8FC] flex flex-col">
      {/* Top Header */}
      <div className="bg-[#102B4E] text-white border-b border-[#0B2545] px-4 sm:px-6 lg:px-8 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-sky-500/20 text-sky-300 flex items-center justify-center font-bold border border-sky-400/30">
            <Wrench className="w-5 h-5 text-sky-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm sm:text-base font-bold tracking-tight">
                Field Worker Operational Workspace
              </h1>
              <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-400/30">
                Authorized Worker
              </span>
            </div>
            <p className="text-[11px] text-slate-300">
              Assigned Work Orders, Evidence Submission & Verification Pipeline
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={loadWorkerData}
            disabled={isLoading}
            className="h-8 px-3 rounded-lg bg-white/10 hover:bg-white/20 text-xs font-semibold flex items-center gap-1.5 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">Refresh Tasks</span>
          </button>
          <Link
            href={`/${locale}`}
            className="text-xs text-slate-300 hover:text-white transition-colors"
          >
            Portal Home
          </Link>
        </div>
      </div>

      {/* Main Container */}
      <div className="flex-1 flex flex-col md:flex-row max-w-[1440px] w-full mx-auto p-4 sm:p-6 lg:p-8 gap-6">
        {/* Left Sidebar */}
        <aside className="w-full md:w-64 shrink-0">
          <div className="bg-white rounded-2xl border border-[#DCE5EE] p-3 shadow-2xs space-y-1">
            <div className="px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-[#40536B]">
              Field Navigation
            </div>
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeSection === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    setActiveSection(item.id as WorkerSection);
                    setNotice(null);
                    setError(null);
                  }}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all text-left ${
                    isActive
                      ? "bg-sky-700 text-white shadow-2xs font-bold"
                      : "text-[#40536B] hover:text-[#102B4E] hover:bg-[#F4F8FC]"
                  }`}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <Icon className={`w-4 h-4 shrink-0 ${isActive ? "text-white" : "text-sky-700"}`} />
                    <span className="truncate">{item.label}</span>
                  </div>
                  {item.badge !== undefined && item.badge > 0 && (
                    <span
                      className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${
                        item.highlight
                          ? "bg-red-500 text-white font-black animate-pulse"
                          : isActive
                          ? "bg-white/20 text-white"
                          : "bg-slate-100 text-slate-700"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </aside>

        {/* Right Content */}
        <main className="flex-1 space-y-6">
          {notice && (
            <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs sm:text-sm flex items-center justify-between">
              <div className="flex items-center gap-2">
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
            <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-900 text-xs sm:text-sm flex items-center justify-between">
              <div className="flex items-center gap-2">
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

          {/* 1. OVERVIEW */}
          {activeSection === "overview" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-extrabold text-[#102B4E]">Worker Work Orders</h2>
                <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                  Tasks assigned directly to your jurisdictional account by the Village PDO.
                </p>
              </div>

              {/* 5 Stats Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                <div className="bg-white p-4 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">Total Assigned</p>
                  <p className="text-2xl font-black text-[#102B4E]">{tasks.length}</p>
                </div>

                <div className="bg-white p-4 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">Pending Start</p>
                  <p className="text-2xl font-black text-amber-600">{pendingTasks.length}</p>
                </div>

                <div className="bg-white p-4 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">In Progress</p>
                  <p className="text-2xl font-black text-sky-700">{inProgressTasks.length}</p>
                </div>

                <div className="bg-white p-4 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">Submitted</p>
                  <p className="text-2xl font-black text-orange-600">
                    {awaitingVerificationTasks.length}
                  </p>
                </div>

                <div className="bg-white p-4 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-1">
                  <p className="text-[10px] font-bold text-[#40536B] uppercase">Returned</p>
                  <p className="text-2xl font-black text-rose-600">{returnedTasks.length}</p>
                </div>
              </div>

              {/* Active Task Highlight */}
              {tasks.length > 0 && (
                <div className="bg-white p-6 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-4">
                  <div className="flex justify-between items-center border-b border-slate-100 pb-3">
                    <h3 className="text-sm font-bold text-[#102B4E]">Priority Active Task</h3>
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-sky-100 text-sky-800">
                      {tasks[0].status}
                    </span>
                  </div>

                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Complaint ID:</span>
                      <span className="font-bold text-[#102B4E]">{tasks[0].reference_number}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Category:</span>
                      <span className="font-bold text-[#087F78] capitalize">{tasks[0].category.replace("_", " ")}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">PDO Instructions:</span>
                      <span className="text-[#102B4E] font-medium">{tasks[0].instructions || "Complete standard repair."}</span>
                    </div>
                  </div>

                  <div className="pt-2 flex gap-3">
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedTask(tasks[0]);
                        setActiveSection("in_progress");
                      }}
                      className="px-4 py-2 rounded-xl bg-sky-700 hover:bg-sky-800 text-white text-xs font-semibold shadow-2xs transition-colors"
                    >
                      Open Task Details
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedTask(tasks[0]);
                        setActiveSection("map");
                      }}
                      className="px-4 py-2 rounded-xl bg-white hover:bg-slate-50 text-[#102B4E] border border-[#DCE5EE] text-xs font-semibold"
                    >
                      View on Map
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 2. MY ASSIGNMENTS */}
          {activeSection === "assignments" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-extrabold text-[#102B4E]">My Assignments</h2>
                <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                  All work orders dispatched to you by the Village PDO.
                </p>
              </div>

              <div className="space-y-4">
                {tasks.map((task) => (
                  <div
                    key={task.assignment_id}
                    className="bg-white p-5 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-3 text-xs"
                  >
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-[#102B4E] text-sm">{task.reference_number}</span>
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700">
                          {task.status}
                        </span>
                        <span className="font-semibold text-[#087F78] capitalize">
                          {task.category.replace("_", " ")}
                        </span>
                      </div>
                      <span className="text-slate-400">
                        {new Date(task.assigned_at).toLocaleDateString()}
                      </span>
                    </div>

                    <p className="text-[#40536B]">{task.description}</p>
                    <div className="p-3 bg-[#F4F8FC] rounded-xl border border-[#DCE5EE] text-[#102B4E]">
                      <strong>PDO Instructions:</strong> {task.instructions || "Perform repair inspection."}
                    </div>

                    <div className="pt-1 flex justify-end gap-2">
                      {task.status === "ASSIGNED" && (
                        <button
                          type="button"
                          onClick={() => handleAcceptTask(task)}
                          className="px-3.5 py-1.5 rounded-xl bg-sky-700 text-white font-semibold hover:bg-sky-800"
                        >
                          Accept & Start
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedTask(task);
                          setActiveSection("in_progress");
                        }}
                        className="px-3.5 py-1.5 rounded-xl border border-[#DCE5EE] text-[#102B4E] font-semibold hover:bg-slate-50"
                      >
                        Manage Execution
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 3. PENDING TASKS */}
          {activeSection === "pending" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-extrabold text-[#102B4E]">Pending Tasks</h2>
                <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                  Newly assigned work orders requiring acceptance.
                </p>
              </div>

              {pendingTasks.length === 0 ? (
                <div className="p-8 bg-white rounded-2xl border border-[#DCE5EE] text-center space-y-2">
                  <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
                  <p className="font-bold text-[#102B4E]">No Pending Tasks</p>
                  <p className="text-xs text-slate-500">All assigned tasks have been acknowledged.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {pendingTasks.map((t) => (
                    <div key={t.assignment_id} className="p-5 bg-white rounded-2xl border border-[#DCE5EE] space-y-3 text-xs">
                      <div className="flex justify-between items-center">
                        <span className="font-bold text-[#102B4E]">{t.reference_number}</span>
                        <span className="text-amber-700 font-bold bg-amber-50 px-2 py-0.5 rounded">NEW ASSIGNMENT</span>
                      </div>
                      <p className="text-[#40536B]">{t.instructions}</p>
                      <button
                        type="button"
                        onClick={() => handleAcceptTask(t)}
                        className="px-4 py-2 rounded-xl bg-sky-700 hover:bg-sky-800 text-white font-semibold"
                      >
                        Accept Work Order
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 4. IN PROGRESS & EVIDENCE SUBMISSION */}
          {activeSection === "in_progress" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-extrabold text-[#102B4E]">In Progress Tasks</h2>
                <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                  Update progress notes, capture GPS coordinates, and submit completion evidence for PDO verification.
                </p>
              </div>

              {inProgressTasks.map((task) => (
                <div
                  key={task.assignment_id}
                  className="bg-white p-6 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-5 text-xs"
                >
                  <div className="flex justify-between items-center border-b border-slate-100 pb-3">
                    <div>
                      <p className="font-bold text-[#102B4E] text-sm">{task.reference_number}</p>
                      <p className="text-[#087F78] font-semibold capitalize">{task.category.replace("_", " ")}</p>
                    </div>
                    <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-sky-100 text-sky-800">
                      IN_PROGRESS
                    </span>
                  </div>

                  {/* PDO Instructions */}
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                    <p className="font-bold text-[#102B4E] mb-1">Panchayat PDO Instructions:</p>
                    <p className="text-[#40536B]">{task.instructions || "Repair according to standard specifications."}</p>
                  </div>

                  {/* Add Progress Note */}
                  <div className="space-y-2">
                    <label className="block font-bold text-[#102B4E] uppercase">
                      Add Progress Update Note
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        placeholder="e.g. Excavation complete, aggregate base laid..."
                        value={progressNotes}
                        onChange={(e) => setProgressNotes(e.target.value)}
                        className="flex-1 px-3 py-2 border border-[#DCE5EE] rounded-xl focus:outline-none"
                      />
                      <button
                        type="button"
                        onClick={() => handleAddProgressNote(task)}
                        className="px-4 py-2 rounded-xl bg-white border border-[#DCE5EE] text-[#102B4E] font-semibold hover:bg-slate-50"
                      >
                        Save Note
                      </button>
                    </div>
                  </div>

                  {/* Final Evidence & Submit for Verification */}
                  <div className="p-4 rounded-2xl bg-amber-50/50 border border-amber-200 space-y-3">
                    <div className="flex items-center gap-2">
                      <Camera className="w-4 h-4 text-amber-700" />
                      <p className="font-bold text-amber-950">Complete Repair & Submit to PDO</p>
                    </div>
                    <p className="text-[11px] text-amber-800">
                      Submitting here opens the comprehensive Work Completion & Cost Breakdown Form. Photos, materials, and proposed expenditure are submitted for independent PDO verification.
                    </p>

                    <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                      <button
                        type="button"
                        onClick={handleCaptureGps}
                        className="px-3 py-1.5 rounded-lg border border-[#DCE5EE] bg-white text-slate-700 flex items-center gap-1.5"
                      >
                        <Navigation className="w-3.5 h-3.5 text-[#087F78]" />
                        <span>{workerLat ? "GPS Tagged ✓" : "Tag Completion GPS"}</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => openCompletionModal(task)}
                        className="px-4 py-2 rounded-xl bg-[#087F78] hover:bg-[#066B65] text-white font-bold shadow-2xs transition-colors flex items-center gap-1.5"
                      >
                        <FileCheck className="w-4 h-4" />
                        <span>Submit Work Completion & Costs</span>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 5. AWAITING VERIFICATION */}
          {activeSection === "awaiting_verification" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-extrabold text-[#102B4E]">Awaiting Verification</h2>
                <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                  Tasks where repair work has been submitted and is currently undergoing independent PDO inspection.
                </p>
              </div>

              {awaitingVerificationTasks.map((t) => (
                <div key={t.assignment_id} className="p-5 bg-white rounded-2xl border border-[#DCE5EE] space-y-2 text-xs">
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-[#102B4E]">{t.reference_number}</span>
                    <span className="px-2 py-0.5 rounded-full bg-orange-100 text-orange-800 font-bold">
                      AWAITING_VERIFICATION
                    </span>
                  </div>
                  <p className="text-[#40536B]">Notes: {t.worker_notes || "Submitted for PDO sign-off."}</p>
                </div>
              ))}
            </div>
          )}

          {/* 6. CORRECTION REQUIRED */}
          {activeSection === "correction_required" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-extrabold text-[#102B4E]">Correction Required</h2>
                <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                  Tasks returned by the PDO requiring rework or supplementary photo proof.
                </p>
              </div>

              {returnedTasks.length === 0 ? (
                <div className="p-8 bg-white rounded-2xl border border-[#DCE5EE] text-center space-y-2">
                  <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
                  <p className="font-bold text-[#102B4E]">Zero Correction Orders</p>
                  <p className="text-xs text-slate-500">All submitted repairs have met PDO standards.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {returnedTasks.map((t) => (
                    <div
                      key={t.assignment_id}
                      className="p-5 bg-white rounded-2xl border-2 border-rose-300 space-y-3 text-xs shadow-2xs"
                    >
                      <div className="flex justify-between items-center">
                        <span className="font-bold text-[#102B4E]">{t.reference_number}</span>
                        <span className="px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 font-bold">
                          REWORK REQUIRED
                        </span>
                      </div>
                      <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-950 font-medium">
                        <strong>PDO Inspection Feedback:</strong>{" "}
                        {t.pdo_remarks ||
                          "Correction required by Village PDO. Please review on site and re-submit."}
                      </div>
                      <div className="flex justify-end pt-1">
                        <button
                          type="button"
                          onClick={() => openCompletionModal(t)}
                          className="px-4 py-2 rounded-xl bg-rose-700 hover:bg-rose-800 text-white font-bold text-xs flex items-center gap-1.5 shadow-2xs transition-colors"
                        >
                          <Camera className="w-3.5 h-3.5" />
                          <span>Revise & Resubmit Completion</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 7. WORK HISTORY */}
          {activeSection === "history" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-extrabold text-[#102B4E]">Completed Work History</h2>
                <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                  Officially resolved and independently verified tasks.
                </p>
              </div>

              {historyTasks.length === 0 ? (
                <div className="p-8 bg-white rounded-2xl border border-[#DCE5EE] text-center space-y-2">
                  <History className="w-8 h-8 text-slate-400 mx-auto" />
                  <p className="font-bold text-[#102B4E]">No Archived Tasks Yet</p>
                  <p className="text-xs text-slate-500">Verified completions will be archived here.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {historyTasks.map((t) => (
                    <div key={t.assignment_id} className="p-4 bg-white rounded-xl border border-[#DCE5EE] flex justify-between items-center text-xs">
                      <div>
                        <span className="font-bold text-[#102B4E]">{t.reference_number}</span>
                        <p className="text-slate-500 capitalize">{t.category.replace("_", " ")}</p>
                      </div>
                      <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-bold">VERIFIED_RESOLVED</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 8. TASK MAP */}
          {activeSection === "map" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-extrabold text-[#102B4E]">Worker Task Map</h2>
                <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                  Geographic location of authorized work orders assigned to you. Does not expose unrelated village complaints.
                </p>
              </div>

              <LeafletMap
                height="560px"
                complaints={workerMapComplaints}
                selectedComplaintId={selectedTask?.issue_id}
                onSelectComplaint={(c) => {
                  const match = tasks.find((t) => t.issue_id === c.id);
                  if (match) setSelectedTask(match);
                }}
              />
            </div>
          )}

          {/* 9. PROFILE */}
          {activeSection === "profile" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-extrabold text-[#102B4E]">Worker Profile</h2>
                <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                  Jurisdictional authorization and credentials.
                </p>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-[#DCE5EE] shadow-2xs space-y-4 max-w-md text-xs">
                <div className="flex justify-between border-b border-slate-100 pb-2">
                  <span className="text-slate-500">Name:</span>
                  <span className="font-bold text-[#102B4E]">{workerStatus?.worker_name || "Ramesh Kumar"}</span>
                </div>
                <div className="flex justify-between border-b border-slate-100 pb-2">
                  <span className="text-slate-500">Registered Email:</span>
                  <span className="font-bold text-[#102B4E]">{workerStatus?.email || "worker.ramesh@fixproof.org"}</span>
                </div>
                <div className="flex justify-between border-b border-slate-100 pb-2">
                  <span className="text-slate-500">Jurisdiction:</span>
                  <span className="font-bold text-[#087F78]">{workerStatus?.village_name || "Assigned Gram Panchayat"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Authorization Status:</span>
                  <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-bold">APPROVED</span>
                </div>
              </div>
            </div>
          )}
          {/* WORK COMPLETION & EXPENDITURE SUBMISSION MODAL */}
          {showCompletionModal && completionTask && (
            <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
              <div className="bg-white rounded-3xl max-w-2xl w-full p-6 shadow-2xl border border-[#DCE5EE] space-y-5 my-8 max-h-[90vh] overflow-y-auto text-xs">
                {/* Modal Header */}
                <div className="flex justify-between items-start border-b border-slate-100 pb-3">
                  <div>
                    <h3 className="text-base font-bold text-[#102B4E]">
                      Submit Work Completion: {completionTask.reference_number}
                    </h3>
                    <p className="text-xs text-slate-500">
                      {completionTask.village_name || "Belagavi Taluk"} • {completionTask.category.replace("_", " ")}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowCompletionModal(false)}
                    className="w-8 h-8 rounded-full hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-600"
                  >
                    ✕
                  </button>
                </div>

                {/* If Rework Required Alert */}
                {completionTask.pdo_remarks && (
                  <div className="p-3.5 rounded-2xl bg-rose-50 border border-rose-200 text-rose-950 space-y-1">
                    <p className="font-bold flex items-center gap-1.5 text-rose-900">
                      <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                      <span>PDO Rework Instructions:</span>
                    </p>
                    <p className="text-xs text-rose-800 pl-5.5">{completionTask.pdo_remarks}</p>
                  </div>
                )}

                {/* Before Photograph Reference */}
                <div className="p-3.5 bg-slate-50 rounded-2xl border border-slate-200 space-y-2">
                  <span className="text-[11px] font-bold text-[#102B4E] uppercase">
                    1. Citizen Before Evidence Photo
                  </span>
                  {completionTask.citizen_photo_ids && completionTask.citizen_photo_ids.length > 0 ? (
                    <div className="flex gap-2">
                      {completionTask.citizen_photo_ids.map((id) => (
                        <img
                          key={id}
                          src={`http://localhost:8000/api/v1/public/media/${id}/view`}
                          alt="Citizen Before Evidence"
                          className="w-28 h-20 object-cover rounded-xl border border-slate-300"
                          onError={(e) => {
                            (e.target as HTMLElement).style.display = "none";
                          }}
                        />
                      ))}
                    </div>
                  ) : (
                    <p className="text-slate-400 italic">No original photo attached to complaint record.</p>
                  )}
                </div>

                {/* Form */}
                <form onSubmit={handleSubmitCompletion} className="space-y-4">
                  {/* After-Work Photograph Upload */}
                  <div className="space-y-2">
                    <label className="block font-bold text-[#102B4E] uppercase">
                      2. Upload After-Work Photograph(s) *
                    </label>
                    <p className="text-[11px] text-slate-500">
                      Provide clear, on-site photographs of the completed repair. Photos will be analyzed by advisory AI and inspected by the Village PDO.
                    </p>

                    <div className="flex flex-wrap items-center gap-3">
                      <label className="cursor-pointer px-4 py-2 rounded-xl bg-sky-700 hover:bg-sky-800 text-white font-semibold flex items-center gap-2 shadow-2xs">
                        <Upload className="w-4 h-4" />
                        <span>{isUploadingPhoto ? "Uploading Photo..." : "Choose & Upload Photo"}</span>
                        <input
                          type="file"
                          accept="image/*"
                          className="hidden"
                          disabled={isUploadingPhoto}
                          onChange={handleUploadAfterPhoto}
                        />
                      </label>

                      {afterImagePreviews.map((src, i) => (
                        <img
                          key={i}
                          src={src}
                          alt="After Repair Preview"
                          className="w-16 h-16 object-cover rounded-xl border-2 border-emerald-500 shadow-2xs"
                        />
                      ))}
                      {completionTask.worker_after_photo_ids &&
                        completionTask.worker_after_photo_ids.map((id) => (
                          <img
                            key={id}
                            src={`http://localhost:8000/api/v1/public/media/${id}/view`}
                            alt="Existing Uploaded After Photo"
                            className="w-16 h-16 object-cover rounded-xl border border-slate-300"
                            onError={(e) => {
                              (e.target as HTMLElement).style.display = "none";
                            }}
                          />
                        ))}
                    </div>
                    {uploadedAfterMediaIds.length > 0 && (
                      <span className="text-emerald-700 font-semibold block text-[11px]">
                        ✓ {uploadedAfterMediaIds.length} after-work photo(s) attached.
                      </span>
                    )}
                  </div>

                  {/* Work Description */}
                  <div className="space-y-1">
                    <label className="block font-bold text-[#102B4E] uppercase">
                      3. Work Completion Description *
                    </label>
                    <textarea
                      required
                      rows={2}
                      value={workDescription}
                      onChange={(e) => setWorkDescription(e.target.value)}
                      placeholder="Summarize the repair work completed at the site..."
                      className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl focus:outline-none"
                    />
                  </div>

                  {/* Work Performed & Materials Grid */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="block font-bold text-[#102B4E] uppercase">
                        Work Performed
                      </label>
                      <input
                        type="text"
                        value={workPerformed}
                        onChange={(e) => setWorkPerformed(e.target.value)}
                        placeholder="e.g. Excavation, pipe joint replacement, backfilling"
                        className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl focus:outline-none"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="block font-bold text-[#102B4E] uppercase">
                        Materials Used
                      </label>
                      <input
                        type="text"
                        value={materialsUsed}
                        onChange={(e) => setMaterialsUsed(e.target.value)}
                        placeholder="e.g. 2x 3-inch PVC coupler, 1 bag cement, gravel"
                        className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl focus:outline-none"
                      />
                    </div>
                  </div>

                  {/* Labour Details */}
                  <div className="space-y-1">
                    <label className="block font-bold text-[#102B4E] uppercase">
                      Labour Details
                    </label>
                    <input
                      type="text"
                      value={labourDetails}
                      onChange={(e) => setLabourDetails(e.target.value)}
                      placeholder="e.g. 1 plumber + 1 assistant, 4 hours on site"
                      className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl focus:outline-none"
                    />
                  </div>

                  {/* Cost Breakdown */}
                  <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-[#102B4E] uppercase">
                        4. Proposed Expenditure Breakdown (₹)
                      </span>
                      <span className="text-[11px] text-slate-500">Itemized Work Cost</span>
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                          Materials Cost (₹)
                        </label>
                        <input
                          type="number"
                          min="0"
                          step="1"
                          value={materialsCost}
                          onChange={(e) =>
                            setMaterialsCost(
                              e.target.value === "" ? "" : parseFloat(e.target.value)
                            )
                          }
                          placeholder="0"
                          className="w-full px-3 py-1.5 border border-[#DCE5EE] rounded-xl bg-white font-semibold"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                          Labour Cost (₹)
                        </label>
                        <input
                          type="number"
                          min="0"
                          step="1"
                          value={labourCost}
                          onChange={(e) =>
                            setLabourCost(e.target.value === "" ? "" : parseFloat(e.target.value))
                          }
                          placeholder="0"
                          className="w-full px-3 py-1.5 border border-[#DCE5EE] rounded-xl bg-white font-semibold"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                          Other Expenses (₹)
                        </label>
                        <input
                          type="number"
                          min="0"
                          step="1"
                          value={otherExpensesCost}
                          onChange={(e) =>
                            setOtherExpensesCost(
                              e.target.value === "" ? "" : parseFloat(e.target.value)
                            )
                          }
                          placeholder="0"
                          className="w-full px-3 py-1.5 border border-[#DCE5EE] rounded-xl bg-white font-semibold"
                        />
                      </div>
                    </div>

                    <div className="flex justify-between items-center pt-2 border-t border-slate-200">
                      <span className="font-bold text-[#102B4E]">Total Proposed Cost:</span>
                      <span className="text-base font-black text-[#087F78]">
                        ₹
                        {(
                          (typeof materialsCost === "number" ? materialsCost : 0) +
                          (typeof labourCost === "number" ? labourCost : 0) +
                          (typeof otherExpensesCost === "number" ? otherExpensesCost : 0)
                        ).toLocaleString("en-IN")}
                      </span>
                    </div>
                  </div>

                  {/* Completion Date */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="block font-bold text-[#102B4E] uppercase">
                        Completion Date
                      </label>
                      <input
                        type="date"
                        required
                        value={completionDate}
                        onChange={(e) => setCompletionDate(e.target.value)}
                        className="w-full px-3 py-2 border border-[#DCE5EE] rounded-xl bg-white focus:outline-none"
                      />
                    </div>
                  </div>

                  {/* Governance Note */}
                  <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 text-amber-900 text-[11px] flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-amber-700 shrink-0" />
                    <span>
                      <strong>Strict Governance Rule:</strong> Field workers cannot approve costs or mark complaints resolved. Your submission will move to <em>AWAITING VERIFICATION</em> for independent Village PDO inspection.
                    </span>
                  </div>

                  {/* Action Buttons */}
                  <div className="pt-2 flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setShowCompletionModal(false)}
                      className="px-4 py-2.5 rounded-xl border border-[#DCE5EE] font-semibold text-[#40536B] hover:bg-slate-50"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmitting || isUploadingPhoto}
                      className="px-5 py-2.5 rounded-xl bg-[#087F78] hover:bg-[#066B65] text-white font-bold shadow-2xs disabled:opacity-50 flex items-center gap-2"
                    >
                      <FileCheck className="w-4 h-4" />
                      <span>{isSubmitting ? "Submitting to PDO..." : "Submit to PDO for Verification"}</span>
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
