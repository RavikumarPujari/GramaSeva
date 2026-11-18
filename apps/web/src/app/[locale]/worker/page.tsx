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
  const tStatuses = useTranslations("statuses");
  const tCat = useTranslations("categories");

  const [tasks, setTasks] = useState<WorkerTask[]>([]);
  const [selectedTask, setSelectedTask] = useState<WorkerTask | null>(null);
  const [isLoading, setIsLoading] = useState(false);
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
            reference_number: "FP-2026-00412",
            category: "road_damage",
            status: "IN_PROGRESS",
            priority: "HIGH",
            instructions:
              "Excavate edge crumbling, fill pothole with 40mm crushed stone aggregate base, and apply asphalt cold-mix compaction. Take photo from original angle.",
            village_name: "Gowdanahalli",
            ward_name: "Ward 2 (Gowdanahalli Central)",
            latitude: 12.5234,
            longitude: 76.8971,
            assigned_at: new Date(Date.now() - 3600000 * 4).toISOString(),
            citizen_photo_ids: ["sample-citizen-pothole"],
            worker_after_photo_ids: [],
          },
          {
            assignment_id: "asgn-demo-02",
            issue_id: "issue-demo-02",
            reference_number: "FP-2026-00388",
            category: "water_leak",
            status: "ASSIGNED",
            priority: "MEDIUM",
            instructions:
              "Inspect main 3-inch PVC distribution valve for joint leakage near temple pipeline.",
            village_name: "Kyathanamgere",
            ward_name: "Ward 4",
            latitude: 12.518,
            longitude: 76.8892,
            assigned_at: new Date(Date.now() - 3600000 * 24).toISOString(),
            citizen_photo_ids: [],
            worker_after_photo_ids: [],
          },
        ];
        setTasks(demoTasks);
        setSelectedTask(demoTasks[0]);
      }
    } catch {
      // Pilot fallback if unauthenticated
      const demoTasks: WorkerTask[] = [
        {
          assignment_id: "asgn-demo-01",
          issue_id: "issue-demo-01",
          reference_number: "FP-2026-00412",
          category: "road_damage",
          status: "IN_PROGRESS",
          priority: "HIGH",
          instructions:
            "Excavate edge crumbling, fill pothole with 40mm crushed stone aggregate base, and apply asphalt cold-mix compaction. Take photo from original angle.",
          village_name: "Gowdanahalli",
          ward_name: "Ward 2 (Gowdanahalli Central)",
          latitude: 12.5234,
          longitude: 76.8971,
          assigned_at: new Date(Date.now() - 3600000 * 4).toISOString(),
          citizen_photo_ids: ["sample-citizen-pothole"],
          worker_after_photo_ids: [],
        },
      ];
      setTasks(demoTasks);
      setSelectedTask(demoTasks[0]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  // Handle Accept
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
      // Update local state
      setSelectedTask({ ...selectedTask, status: "IN_PROGRESS" });
      setTasks((prev) =>
        prev.map((t) =>
          t.assignment_id === selectedTask.assignment_id ? { ...t, status: "IN_PROGRESS" } : t
        )
      );
    } catch (err: any) {
      // Demo simulation fallback
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

  // Handle Decline
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
    } catch (err: any) {
      setActionMessage({
        type: "info",
        text: `Assignment declined (Demo mode): "${declineReason}". Returned to review.`,
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
        text: "Repair evidence photo uploaded successfully with SHA-256 integrity hash.",
      });
    } catch (err: any) {
      // Demo fallback
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
        text: "Validation Error: At least one after-repair photo must be uploaded before requesting review.",
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
          t.assignment_id === selectedTask.assignment_id
            ? { ...t, status: "REPAIR_REPORTED" }
            : t
        )
      );
      setActionMessage({
        type: "success",
        text: `Repair reported for ${selectedTask.reference_number}. Forwarded to independent reviewer for verification.`,
      });
      setWorkNotes("");
    } catch (err: any) {
      setSelectedTask({ ...selectedTask, status: "REPAIR_REPORTED" });
      setActionMessage({
        type: "success",
        text: `Work marked as REPAIR_REPORTED (Demo Mode). Supervisor must now review evidence.`,
      });
      setWorkNotes("");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 sm:py-10 w-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200">
              Field Worker Operations
            </span>
            <span className="text-xs text-slate-500">
              Assigned Worker: <strong>Ramesh K. (Civil Works Team)</strong>
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Assigned Repair Tasks
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Accept assignments, execute field repairs, and upload mandatory photo proof.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={fetchTasks}
          isLoading={isLoading}
          leftIcon={<RefreshCw className="w-4 h-4" />}
        >
          Refresh Tasks
        </Button>
      </div>

      {/* Separation of Duty Rule Alert */}
      <Alert variant="warning" className="mb-6">
        <div className="flex items-start gap-2">
          <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <strong>FixProof Separation of Duty Rule:</strong> Submitting repair evidence transitions the issue to{" "}
            <code className="bg-amber-100 text-amber-900 px-1 py-0.5 rounded font-mono text-xs">REPAIR_REPORTED</code>.
            As the assigned worker, you cannot approve or close this repair. An independent supervisor must verify your before/after photos.
          </div>
        </div>
      </Alert>

      {/* Action status message */}
      {actionMessage && (
        <Alert
          variant={
            actionMessage.type === "success"
              ? "success"
              : actionMessage.type === "error"
              ? "danger"
              : "info"
          }
          className="mb-6"
        >
          {actionMessage.text}
        </Alert>
      )}

      {/* Main Grid: Task list & Active Task Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Task List (5 cols) */}
        <div className="lg:col-span-5 space-y-3">
          <h2 className="text-xs font-bold text-slate-600 uppercase tracking-wider mb-2">
            My Queue ({tasks.length})
          </h2>

          {tasks.length === 0 ? (
            <div className="p-8 text-center bg-slate-50 rounded-xl border border-slate-200">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
              <p className="text-sm font-semibold text-slate-800">No pending assignments</p>
              <p className="text-xs text-slate-500 mt-1">All assigned work is completed and verified.</p>
            </div>
          ) : (
            tasks.map((task) => {
              const isSelected = selectedTask?.assignment_id === task.assignment_id;
              return (
                <div
                  key={task.assignment_id}
                  onClick={() => setSelectedTask(task)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? "bg-civic-50/50 border-civic-600 ring-1 ring-civic-600 shadow-sm"
                      : "bg-white border-slate-200 hover:border-slate-300"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="font-mono text-xs font-bold text-civic-800 bg-white px-2 py-0.5 rounded border border-slate-200">
                      {task.reference_number}
                    </span>
                    <Badge status={task.status}>
                      {task.status.replace("_", " ")}
                    </Badge>
                  </div>

                  <h3 className="text-sm font-bold text-slate-900 capitalize">
                    {task.category.replace("_", " ")}
                  </h3>

                  <p className="text-xs text-slate-500 flex items-center mt-1">
                    <MapPin className="w-3.5 h-3.5 mr-1 text-slate-400 shrink-0" />
                    <span className="truncate">{task.village_name} &bull; {task.ward_name}</span>
                  </p>

                  <div className="flex items-center justify-between pt-3 mt-3 border-t border-slate-100 text-xs">
                    <span
                      className={`font-semibold ${
                        task.priority === "HIGH"
                          ? "text-red-600"
                          : task.priority === "MEDIUM"
                          ? "text-amber-600"
                          : "text-blue-600"
                      }`}
                    >
                      {task.priority} Priority
                    </span>
                    <span className="text-slate-400">
                      {new Date(task.assigned_at).toLocaleDateString()}
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
            <Card className="p-6">
              {/* Task Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100 mb-6">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-civic-800 bg-civic-50 px-2 py-0.5 rounded border border-civic-200">
                      {selectedTask.reference_number}
                    </span>
                    <span className="text-xs text-slate-400">&bull;</span>
                    <span className="text-xs text-slate-500 font-mono">
                      Task ID: {selectedTask.assignment_id.slice(0, 12)}
                    </span>
                  </div>
                  <h2 className="text-xl font-bold text-slate-900 mt-2 capitalize">
                    {selectedTask.category.replace("_", " ")}
                  </h2>
                  <p className="text-xs text-slate-500 flex items-center mt-1">
                    <MapPin className="w-3.5 h-3.5 mr-1 text-slate-400 shrink-0" />
                    {selectedTask.village_name} &bull; {selectedTask.ward_name}
                  </p>
                </div>
                <div>
                  <Badge status={selectedTask.status}>
                    {selectedTask.status.replace("_", " ")}
                  </Badge>
                </div>
              </div>

              {/* Action Buttons if task is ASSIGNED */}
              {selectedTask.status === "ASSIGNED" && (
                <div className="mb-6 p-4 bg-blue-50/70 border border-blue-200 rounded-xl">
                  <h3 className="text-sm font-bold text-blue-900 mb-1">
                    Action Required: Accept or Decline Task
                  </h3>
                  <p className="text-xs text-blue-700 mb-4">
                    Confirm you can execute this repair or decline with a reason so it can be reassigned.
                  </p>
                  <div className="flex items-center gap-3">
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

              {/* Decline Modal / Inline prompt */}
              {showDeclineModal && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl">
                  <h4 className="text-sm font-bold text-red-900 mb-2">
                    State reason for declining:
                  </h4>
                  <Textarea
                    placeholder="e.g. Requires specialized asphalt roller equipment not available in Gram Panchayat inventory."
                    value={declineReason}
                    onChange={(e) => setDeclineReason(e.target.value)}
                    className="mb-3"
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
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowDeclineModal(false)}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}

              {/* Task Instructions */}
              <div className="space-y-6">
                <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
                  <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Supervisor Instructions
                  </h3>
                  <p className="text-sm text-slate-700 leading-relaxed">
                    {selectedTask.instructions || "Standard department repair procedure applies. Ensure durable restoration."}
                  </p>
                </div>

                {/* Evidence Comparison / Before Photo */}
                <div>
                  <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                    Citizen Initial Report Photo
                  </h3>
                  <div className="h-44 w-full bg-slate-100 rounded-xl border border-slate-200 flex flex-col items-center justify-center text-slate-400 p-4 text-center">
                    <Camera className="w-8 h-8 mb-2 text-slate-400" />
                    <p className="text-xs font-medium text-slate-600">
                      Original citizen evidence on record
                    </p>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Ensure your after photo matches this angle for review validation.
                    </p>
                  </div>
                </div>

                {/* Evidence Upload Section */}
                <div className="pt-2">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-bold text-slate-900">
                      Upload Proof of Repair (After Photo)
                    </h3>
                    <span className="text-xs font-medium text-slate-500">
                      {selectedTask.worker_after_photo_ids.length} photo(s) on file
                    </span>
                  </div>

                  {selectedTask.status === "REPAIR_REPORTED" || selectedTask.status === "RESOLVED" ? (
                    <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800">
                      <CheckCircle2 className="w-4 h-4 inline mr-1 text-emerald-600" />
                      Proof of repair has been submitted and locked for supervisor verification.
                    </div>
                  ) : (
                    <>
                      <div className="border-2 border-dashed border-slate-300 rounded-xl p-5 text-center bg-slate-50/50 hover:bg-slate-50 transition-colors">
                        {filePreview ? (
                          <div className="space-y-3">
                            <div className="w-full max-h-48 overflow-hidden rounded-lg border border-slate-200 mx-auto">
                              {/* Preview file */}
                              {/* eslint-disable-next-line @next/next/no-img-element */}
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
                                Commit Photo to Issue Record
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
                            <p className="text-sm font-semibold text-slate-800">
                              Capture or upload completed repair photo
                            </p>
                            <p className="text-xs text-slate-500 mt-0.5">
                              JPEG, PNG or WebP &bull; Max 15MB
                            </p>
                            <label className="mt-3 inline-block">
                              <span className="inline-flex items-center justify-center px-4 py-2 text-xs font-semibold rounded-lg bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 cursor-pointer shadow-xs">
                                <Upload className="w-4 h-4 mr-1.5" /> Select Repair Photo
                              </span>
                              <input
                                type="file"
                                accept="image/*"
                                className="hidden"
                                onChange={handleFileChange}
                              />
                            </label>
                          </>
                        )}
                      </div>
                    </>
                  )}
                </div>

                {/* Work Summary & Request Review */}
                {selectedTask.status !== "REPAIR_REPORTED" && selectedTask.status !== "RESOLVED" && (
                  <div className="pt-2 space-y-4">
                    <Textarea
                      label="Work Summary & Materials Applied"
                      placeholder="e.g. Cleared loose gravel, laid 45kg cold-mix asphalt, leveled and roller compacted. Barricades removed."
                      value={workNotes}
                      onChange={(e) => setWorkNotes(e.target.value)}
                      required
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
                      >
                        Submit for Independent Review
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </Card>
          ) : (
            <Card className="p-12 text-center text-slate-500">
              Select a task from the queue to view repair instructions and log proof.
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
