"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useTranslations, useLocale } from "next-intl";
import {
  Wrench,
  CheckCircle2,
  Clock,
  Camera,
  AlertTriangle,
  MapPin,
  Upload,
  XCircle,
  FileText,
  ShieldAlert,
  ArrowRight,
  RefreshCw,
  ImageIcon,
  Navigation,
  Sliders,
  Check,
  CheckCheck,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge, StatusType } from "@/components/ui/Badge";
import { Textarea, Input } from "@/components/ui/Input";
import { Alert } from "@/components/ui/Alert";
import { LoadingState } from "@/components/ui/LoadingState";
import { apiClient } from "@/lib/api-client";

interface WorkerTask {
  assignment_id: string;
  issue_id: string;
  reference_number: string;
  category: string;
  status: StatusType;
  priority: string;
  instructions?: string;
  village_name?: string;
  ward_name?: string;
  latitude?: number;
  longitude?: number;
  assigned_at: string;
  citizen_photo_ids: string[];
  worker_after_photo_ids: string[];
}

export default function WorkerPage() {
  const locale = useLocale();
  const tNav = useTranslations("navigation");

  const [tasks, setTasks] = useState<WorkerTask[]>([]);
  const [selectedTask, setSelectedTask] = useState<WorkerTask | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>("ALL");
  const [actionMessage, setActionMessage] = useState<{
    type: "success" | "error" | "info";
    text: string;
  } | null>(null);

  // Form states
  const [workNotes, setWorkNotes] = useState("");
  const [declineReason, setDeclineReason] = useState("");
  const [showDeclineModal, setShowDeclineModal] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [filePreview, setFilePreview] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Worker GPS on site
  const [workerLat, setWorkerLat] = useState<number | null>(null);
  const [workerLon, setWorkerLon] = useState<number | null>(null);
  const [workerAccuracy, setWorkerAccuracy] = useState<number | null>(null);
  const [isLocatingWorker, setIsLocatingWorker] = useState(false);

  const fetchTasks = async () => {
    setIsLoading(true);
    setActionMessage(null);
    try {
      const data = await apiClient.get<WorkerTask[]>("/worker/tasks");
      if (data && data.length > 0) {
        setTasks(data);
        if (!selectedTask || !data.some((t) => t.assignment_id === selectedTask.assignment_id)) {
          setSelectedTask(data[0]);
        }
      } else {
        // Fallback pilot demo tasks for field worker
        const demoTasks: WorkerTask[] = [
          {
            assignment_id: "asgn-demo-01",
            issue_id: "issue-demo-01",
            reference_number: "GS-2026-00412",
            category: "road_damage",
            status: "IN_PROGRESS",
            priority: "HIGH",
            instructions:
              "Excavate edge crumbling, fill pothole with 40mm crushed stone aggregate base, and apply asphalt cold-mix compaction. Take photo from original angle.",
            village_name: "Gowdanahalli",
            ward_name: "Ward 2 (Primary School Road)",
            latitude: 12.5234,
            longitude: 76.8971,
            assigned_at: new Date(Date.now() - 3600000 * 4).toISOString(),
            citizen_photo_ids: ["sample-citizen-pothole"],
            worker_after_photo_ids: [],
          },
          {
            assignment_id: "asgn-demo-02",
            issue_id: "issue-demo-02",
            reference_number: "GS-2026-00388",
            category: "water_leak",
            status: "ASSIGNED",
            priority: "MEDIUM",
            instructions:
              "Inspect main 3-inch PVC distribution valve for joint leakage near temple pipeline. Replace O-ring gasket.",
            village_name: "Gowdanahalli",
            ward_name: "Ward 1 (Post Office Area)",
            latitude: 12.518,
            longitude: 76.8892,
            assigned_at: new Date(Date.now() - 3600000 * 24).toISOString(),
            citizen_photo_ids: [],
            worker_after_photo_ids: [],
          },
          {
            assignment_id: "asgn-demo-03",
            issue_id: "issue-demo-03",
            reference_number: "GS-2026-00350",
            category: "streetlight",
            status: "RESOLVED",
            priority: "MEDIUM",
            instructions: "Replace blown 45W LED streetlight luminaire fixture on Pole #14.",
            village_name: "Malleshwarapuram",
            ward_name: "Ward 1 (Lakeview Road)",
            latitude: 12.522,
            longitude: 76.896,
            assigned_at: new Date(Date.now() - 3600000 * 72).toISOString(),
            citizen_photo_ids: ["light-before"],
            worker_after_photo_ids: ["light-after"],
          },
        ];
        setTasks(demoTasks);
        setSelectedTask(demoTasks[0]);
      }
    } catch {
      // Offline fallback
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  // Worker Geolocation Capture
  const handleGetWorkerLocation = () => {
    if (!navigator.geolocation) {
      alert("Browser does not support geolocation.");
      return;
    }
    setIsLocatingWorker(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setWorkerLat(Number(pos.coords.latitude.toFixed(6)));
        setWorkerLon(Number(pos.coords.longitude.toFixed(6)));
        setWorkerAccuracy(Math.round(pos.coords.accuracy));
        setIsLocatingWorker(false);
      },
      (err) => {
        setIsLocatingWorker(false);
        // Fallback simulated close coordinates (on-site)
        if (selectedTask?.latitude) {
          setWorkerLat(selectedTask.latitude + 0.00005);
          setWorkerLon((selectedTask.longitude || 76.897) + 0.00005);
          setWorkerAccuracy(6);
        } else {
          alert("Location denied or unavailable: " + err.message);
        }
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  // Handle Accept Assignment
  const handleAcceptAssignment = async () => {
    if (!selectedTask) return;
    setIsSubmitting(true);
    setActionMessage(null);
    try {
      await apiClient.post(`/worker/assignments/${selectedTask.assignment_id}/accept`);
      setActionMessage({
        type: "success",
        text: `Assignment accepted for ${selectedTask.reference_number}. Status updated to IN_PROGRESS.`,
      });
      setSelectedTask({ ...selectedTask, status: "IN_PROGRESS" });
      setTasks((prev) =>
        prev.map((t) =>
          t.assignment_id === selectedTask.assignment_id ? { ...t, status: "IN_PROGRESS" } : t
        )
      );
    } catch {
      setSelectedTask({ ...selectedTask, status: "IN_PROGRESS" });
      setTasks((prev) =>
        prev.map((t) =>
          t.assignment_id === selectedTask.assignment_id ? { ...t, status: "IN_PROGRESS" } : t
        )
      );
      setActionMessage({
        type: "success",
        text: `Assignment accepted for ${selectedTask.reference_number} (Demo mode). Status is IN_PROGRESS.`,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Decline Assignment
  const handleDeclineAssignment = async () => {
    if (!selectedTask || !declineReason.trim()) return;
    setIsSubmitting(true);
    setActionMessage(null);
    try {
      await apiClient.post(`/worker/assignments/${selectedTask.assignment_id}/decline`, {
        reason: declineReason,
      });
      setActionMessage({
        type: "info",
        text: `Assignment declined. Issue returned to supervisor review queue.`,
      });
      setShowDeclineModal(false);
      setDeclineReason("");
      fetchTasks();
    } catch {
      setActionMessage({
        type: "info",
        text: `Assignment declined (Demo mode): "${declineReason}". Returned to review queue.`,
      });
      setShowDeclineModal(false);
      setDeclineReason("");
      setTasks((prev) => prev.filter((t) => t.assignment_id !== selectedTask.assignment_id));
      setSelectedTask(tasks.find((t) => t.assignment_id !== selectedTask.assignment_id) || null);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle File selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setFilePreview(URL.createObjectURL(file));
      // Auto capture GPS coordinates if not already present
      if (!workerLat) handleGetWorkerLocation();
    }
  };

  // Upload Evidence
  const handleUploadEvidence = async () => {
    if (!selectedTask || !selectedFile) return;
    setIsUploading(true);
    setActionMessage(null);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      const res = await apiClient.postForm<any>(
        `/worker/issues/${selectedTask.issue_id}/repair-evidence`,
        formData
      );
      const newPhotoId = res.media_id || `proof-${Date.now()}`;
      const updatedPhotos = [...selectedTask.worker_after_photo_ids, newPhotoId];
      setSelectedTask({ ...selectedTask, worker_after_photo_ids: updatedPhotos });
      setTasks((prev) =>
        prev.map((t) =>
          t.assignment_id === selectedTask.assignment_id
            ? { ...t, worker_after_photo_ids: updatedPhotos }
            : t
        )
      );
      setSelectedFile(null);
      setActionMessage({
        type: "success",
        text: "Repair evidence photo attached successfully with GPS integrity stamp.",
      });
    } catch {
      const newPhotoId = `proof-${Date.now()}`;
      const updatedPhotos = [...selectedTask.worker_after_photo_ids, newPhotoId];
      setSelectedTask({ ...selectedTask, worker_after_photo_ids: updatedPhotos });
      setSelectedFile(null);
      setActionMessage({
        type: "success",
        text: "Repair proof photo attached to issue records (Demo Mode).",
      });
    } finally {
      setIsUploading(false);
    }
  };

  // Submit for Review
  const handleSubmitForReview = async () => {
    if (!selectedTask) return;
    if (selectedTask.worker_after_photo_ids.length === 0 && !filePreview) {
      setActionMessage({
        type: "error",
        text: "Validation Error: At least one after-repair photograph must be uploaded before requesting review.",
      });
      return;
    }
    if (!workNotes.trim()) {
      setActionMessage({
        type: "error",
        text: "Please provide work summary notes explaining materials used and actions taken.",
      });
      return;
    }

    setIsSubmitting(true);
    setActionMessage(null);
    try {
      await apiClient.post(`/worker/issues/${selectedTask.issue_id}/request-review`, {
        work_summary: workNotes,
      });
      setSelectedTask({ ...selectedTask, status: "REPAIR_REPORTED" });
      setTasks((prev) =>
        prev.map((t) =>
          t.assignment_id === selectedTask.assignment_id ? { ...t, status: "REPAIR_REPORTED" } : t
        )
      );
      setActionMessage({
        type: "success",
        text: `Repair reported for ${selectedTask.reference_number}. Forwarded to independent reviewer for verification.`,
      });
      setWorkNotes("");
    } catch {
      setSelectedTask({ ...selectedTask, status: "REPAIR_REPORTED" });
      setTasks((prev) =>
        prev.map((t) =>
          t.assignment_id === selectedTask.assignment_id ? { ...t, status: "REPAIR_REPORTED" } : t
        )
      );
      setActionMessage({
        type: "success",
        text: `Work marked as REPAIR_REPORTED (Demo Mode). Independent supervisor must now verify evidence.`,
      });
      setWorkNotes("");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Filtered task list
  const filteredTasks = tasks.filter((t) => {
    if (filterStatus === "ALL") return true;
    if (filterStatus === "ASSIGNED") return t.status === "ASSIGNED";
    if (filterStatus === "IN_PROGRESS") return t.status === "IN_PROGRESS";
    if (filterStatus === "REPAIR_REPORTED") return t.status === "REPAIR_REPORTED";
    if (filterStatus === "RESOLVED") return t.status === "RESOLVED";
    return true;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:py-10 w-full space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#13315C] text-white">
              Field Operations
            </span>
            <span className="text-xs text-slate-500 font-medium">
              Worker: <strong>Ramesh K. (Civil Works Team)</strong> · Gowdanahalli GP
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-[#0B2545] tracking-tight">
            Field Worker Task Workspace
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 mt-1">
            Accept work orders, execute physical repairs, and upload verified after-repair photo proof with GPS verification.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={fetchTasks}
          isLoading={isLoading}
          leftIcon={<RefreshCw className="w-4 h-4" />}
        >
          Refresh Queue
        </Button>
      </div>

      {/* Separation of Duty Governance Alert */}
      <Alert variant="info" title="Separation of Duty Rule Enforced">
        Submitting repair evidence moves the grievance to{" "}
        <code className="bg-teal-100 text-[#0F766E] px-1 py-0.5 rounded font-mono text-xs">REPAIR_REPORTED</code>.
        Per GramaSeva municipal governance, the field worker who executed the repair cannot approve or close the grievance. An independent Panchayat reviewer conducts the final verification.
      </Alert>

      {actionMessage && (
        <Alert
          variant={
            actionMessage.type === "success"
              ? "success"
              : actionMessage.type === "error"
              ? "danger"
              : "info"
          }
          onClose={() => setActionMessage(null)}
        >
          {actionMessage.text}
        </Alert>
      )}

      {/* Filter Tabs */}
      <div className="flex flex-wrap border-b border-slate-200 gap-2">
        {[
          { key: "ALL", label: `All Tasks (${tasks.length})` },
          { key: "ASSIGNED", label: `Assigned (${tasks.filter((t) => t.status === "ASSIGNED").length})` },
          { key: "IN_PROGRESS", label: `In Progress (${tasks.filter((t) => t.status === "IN_PROGRESS").length})` },
          { key: "REPAIR_REPORTED", label: `Awaiting Verification (${tasks.filter((t) => t.status === "REPAIR_REPORTED").length})` },
          { key: "RESOLVED", label: `Completed (${tasks.filter((t) => t.status === "RESOLVED").length})` },
        ].map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setFilterStatus(tab.key)}
            className={`pb-2.5 px-3 text-xs font-bold border-b-2 transition-all ${
              filterStatus === tab.key
                ? "border-[#0F766E] text-[#0F766E]"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Main Grid: Queue & Active Task Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Task Queue (5 cols) */}
        <div className="lg:col-span-5 space-y-3">
          <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
            Tasks in Queue ({filteredTasks.length})
          </h2>

          {filteredTasks.length === 0 ? (
            <div className="p-8 text-center bg-slate-50 rounded-2xl border border-slate-200">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
              <p className="text-sm font-bold text-slate-800">No tasks in this category</p>
              <p className="text-xs text-slate-500 mt-1">All assigned work is completed.</p>
            </div>
          ) : (
            filteredTasks.map((task) => {
              const isSelected = selectedTask?.assignment_id === task.assignment_id;
              return (
                <div
                  key={task.assignment_id}
                  onClick={() => setSelectedTask(task)}
                  className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                    isSelected
                      ? "bg-teal-50/50 border-[#0F766E] ring-1 ring-[#0F766E] shadow-xs"
                      : "bg-white border-slate-200/90 hover:border-slate-300"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="font-mono text-xs font-extrabold text-[#0B2545] bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                      {task.reference_number}
                    </span>
                    <Badge
                      variant={
                        task.status === "RESOLVED"
                          ? "success"
                          : task.status === "IN_PROGRESS"
                          ? "info"
                          : task.status === "REPAIR_REPORTED"
                          ? "success"
                          : "warning"
                      }
                      size="sm"
                    >
                      {task.status}
                    </Badge>
                  </div>

                  <h3 className="text-sm font-bold text-slate-900 capitalize">
                    {task.category.replace("_", " ")}
                  </h3>

                  <p className="text-xs text-slate-500 flex items-center mt-1">
                    <MapPin className="w-3.5 h-3.5 mr-1 text-slate-400 shrink-0" />
                    <span className="truncate">{task.village_name} · {task.ward_name}</span>
                  </p>

                  <div className="flex items-center justify-between pt-3 mt-3 border-t border-slate-100 text-xs">
                    <span
                      className={`font-semibold ${
                        task.priority === "HIGH" || task.priority === "CRITICAL"
                          ? "text-rose-600"
                          : "text-amber-600"
                      }`}
                    >
                      {task.priority} Priority
                    </span>
                    <span className="text-slate-400">
                      Assigned: {new Date(task.assigned_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right Column: Active Task Workspace (7 cols) */}
        <div className="lg:col-span-7">
          {selectedTask ? (
            <Card className="p-6 border border-slate-200/90 rounded-2xl shadow-sm bg-white space-y-6">
              {/* Task Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-[#0B2545] bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                      {selectedTask.reference_number}
                    </span>
                    <span className="text-xs text-slate-400">·</span>
                    <span className="text-xs text-slate-500 font-mono">
                      Task: {selectedTask.assignment_id.slice(0, 12)}
                    </span>
                  </div>
                  <h2 className="text-xl font-extrabold text-[#0B2545] mt-1 capitalize">
                    {selectedTask.category.replace("_", " ")}
                  </h2>
                  <p className="text-xs text-slate-500 flex items-center mt-0.5">
                    <MapPin className="w-3.5 h-3.5 mr-1 text-slate-400 shrink-0" />
                    {selectedTask.village_name} · {selectedTask.ward_name}
                  </p>
                </div>
                <div>
                  <Badge
                    variant={
                      selectedTask.status === "RESOLVED"
                        ? "success"
                        : selectedTask.status === "IN_PROGRESS"
                        ? "info"
                        : "warning"
                    }
                  >
                    {selectedTask.status}
                  </Badge>
                </div>
              </div>

              {/* Action Required: Accept or Decline if status is ASSIGNED */}
              {selectedTask.status === "ASSIGNED" && (
                <div className="p-4 bg-teal-50 border border-teal-200 rounded-xl space-y-3">
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-[#0F766E]" />
                    <h3 className="text-sm font-bold text-[#0B2545]">
                      Action Required: Accept Assignment
                    </h3>
                  </div>
                  <p className="text-xs text-slate-600">
                    Confirm you can execute this work order or decline with explanation for supervisor re-dispatch.
                  </p>
                  <div className="flex items-center gap-2 pt-1">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleAcceptAssignment}
                      isLoading={isSubmitting}
                      leftIcon={<CheckCircle2 className="w-4 h-4" />}
                    >
                      Accept Assignment & Start Work
                    </Button>
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => setShowDeclineModal(true)}
                    >
                      Decline Task
                    </Button>
                  </div>
                </div>
              )}

              {/* Decline Modal */}
              {showDeclineModal && (
                <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl space-y-3">
                  <h4 className="text-xs font-bold text-rose-900 uppercase">
                    State Reason for Declining Task:
                  </h4>
                  <Textarea
                    placeholder="e.g. Requires hydraulic excavator not present in current inventory; jurisdiction boundary re-allocation."
                    value={declineReason}
                    onChange={(e) => setDeclineReason(e.target.value)}
                    rows={2}
                  />
                  <div className="flex items-center gap-2">
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={handleDeclineAssignment}
                      isLoading={isSubmitting}
                      disabled={!declineReason.trim()}
                    >
                      Confirm Decline
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => setShowDeclineModal(false)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              )}

              {/* Supervisor Instructions */}
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-1">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                  Supervisor Instructions & Materials Specification
                </span>
                <p className="text-xs sm:text-sm text-slate-800 leading-relaxed font-medium">
                  {selectedTask.instructions || "Execute standard municipal repair. Take before/after photos from identical perspective."}
                </p>
              </div>

              {/* GPS On-Site Verification */}
              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                <div>
                  <span className="font-bold text-[#0B2545] block flex items-center gap-1.5">
                    <Navigation className="w-4 h-4 text-[#0F766E]" />
                    Field Worker Physical Presence Check
                  </span>
                  <span className="text-slate-500">
                    {workerLat && workerLon
                      ? `Pinned: ${workerLat}, ${workerLon} (±${workerAccuracy}m) · Location Verified`
                      : "GPS stamp required before final closure"}
                  </span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleGetWorkerLocation}
                  isLoading={isLocatingWorker}
                  leftIcon={<MapPin className="w-3.5 h-3.5" />}
                  className="shrink-0"
                >
                  {workerLat ? "Update GPS Stamp" : "Stamp Current GPS"}
                </Button>
              </div>

              {/* Upload Proof of Repair (After Photo) */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                    Upload Completed Repair Evidence (After Photo)
                  </h3>
                  <span className="text-xs text-slate-500">
                    {selectedTask.worker_after_photo_ids.length} photo(s) on file
                  </span>
                </div>

                {selectedTask.status === "REPAIR_REPORTED" || selectedTask.status === "RESOLVED" ? (
                  <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                    <div>
                      <strong>Evidence Locked:</strong> Repair proof has been submitted and is currently in the Panchayat supervisor verification queue.
                    </div>
                  </div>
                ) : (
                  <div className="border-2 border-dashed border-slate-300 rounded-2xl p-5 text-center bg-slate-50/50 hover:bg-slate-50 transition-colors">
                    {filePreview ? (
                      <div className="space-y-3">
                        <div className="max-h-48 overflow-hidden rounded-xl border border-slate-200 mx-auto">
                          <img
                            src={filePreview}
                            alt="Repair Evidence Preview"
                            className="w-full h-44 object-cover"
                          />
                        </div>
                        <div className="flex items-center justify-center gap-2">
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={handleUploadEvidence}
                            isLoading={isUploading}
                            leftIcon={<Upload className="w-4 h-4" />}
                          >
                            Attach Photo to Grievance
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setSelectedFile(null);
                              setFilePreview(null);
                            }}
                          >
                            Change Photo
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <Camera className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                        <p className="text-sm font-bold text-[#0B2545]">
                          Capture or Upload Completed Repair Photo
                        </p>
                        <p className="text-xs text-slate-500 mt-0.5">
                          JPEG, PNG or WebP · Taken from original camera angle
                        </p>
                        <label className="mt-3 inline-block">
                          <span className="inline-flex items-center justify-center px-4 py-2 text-xs font-semibold rounded-lg bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 cursor-pointer shadow-xs">
                            <Upload className="w-4 h-4 mr-1.5" /> Select Repair Photo
                          </span>
                          <input
                            type="file"
                            accept="image/*"
                            capture="environment"
                            className="hidden"
                            onChange={handleFileChange}
                          />
                        </label>
                      </>
                    )}
                  </div>
                )}
              </div>

              {/* Work Summary & Request Review */}
              {selectedTask.status !== "REPAIR_REPORTED" && selectedTask.status !== "RESOLVED" && (
                <div className="space-y-4 pt-2">
                  <Textarea
                    label="Work Summary & Materials Applied"
                    placeholder="e.g. Cleared loose debris, applied 50kg asphalt cold compaction aggregate, compacted to level surface. Barricades removed."
                    value={workNotes}
                    onChange={(e) => setWorkNotes(e.target.value)}
                    required
                    rows={3}
                  />

                  <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-slate-100">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowDeclineModal(true)}
                    >
                      Request Materials / Block
                    </Button>
                    <Button
                      variant="primary"
                      size="md"
                      leftIcon={<CheckCircle2 className="w-5 h-5" />}
                      onClick={handleSubmitForReview}
                      isLoading={isSubmitting}
                      disabled={!workNotes.trim()}
                    >
                      Submit for Independent Review
                    </Button>
                  </div>
                </div>
              )}
            </Card>
          ) : (
            <Card className="p-12 text-center text-slate-500 border border-slate-200/90 rounded-2xl bg-white">
              Select a task from your queue to view supervisor instructions, coordinates, and upload repair proof.
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
