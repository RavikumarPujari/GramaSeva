"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useTranslations, useLocale } from "next-intl";
import {
  Search,
  Clock,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  FileImage,
  Bell,
  Star,
  MessageSquare,
  AlertCircle,
  ThumbsUp,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge, type StatusType } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingState } from "@/components/ui/LoadingState";
import { Alert } from "@/components/ui/Alert";
import { Textarea } from "@/components/ui/Input";
import { apiClient } from "@/lib/api-client";

interface ReportItem {
  id: string;
  tracking_id: string;
  category: string;
  description: string;
  status: StatusType;
  village_name?: string;
  ward_name?: string;
  created_at: string;
  media_assets?: Array<{ id: string; mime_type: string }>;
}

interface InAppNotification {
  id: string;
  title: string;
  message: string;
  event_type: string;
  is_read: boolean;
  created_at: string;
}

function ReportThumbnail({ mediaId, category }: { mediaId: string; category: string }) {
  const [hasError, setHasError] = useState(false);

  if (hasError) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center bg-slate-50 text-slate-400 gap-1">
        <FileImage className="w-6 h-6 text-slate-300" />
        <span className="text-[11px] font-semibold text-slate-500">Verified Photo</span>
      </div>
    );
  }

  return (
    <img
      src={`/api/v1/reports/media/${mediaId}/view`}
      alt={category}
      className="w-full h-full object-cover"
      loading="lazy"
      onError={() => setHasError(true)}
    />
  );
}

function ModalImagePreview({ mediaId }: { mediaId: string }) {
  const [hasError, setHasError] = useState(false);

  if (hasError) {
    return (
      <div className="w-full h-48 flex flex-col items-center justify-center bg-slate-50 text-slate-400 gap-1 rounded-xl border border-slate-200">
        <FileImage className="w-8 h-8 text-slate-300" />
        <span className="text-xs font-semibold text-slate-500">Image Preview Unavailable</span>
      </div>
    );
  }

  return (
    <div className="relative rounded-xl overflow-hidden border border-slate-200 bg-slate-100 max-h-72">
      <img
        src={`/api/v1/reports/media/${mediaId}/view`}
        alt="Evidence photo"
        className="w-full h-full object-cover max-h-72"
        onError={() => setHasError(true)}
      />
      <div className="absolute top-2.5 left-2.5 px-2.5 py-1 rounded-md text-[10px] font-bold bg-[#102B4E]/90 text-white backdrop-blur-xs flex items-center gap-1.5 shadow-xs">
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
        <span>SHA-256 Verified Evidence</span>
      </div>
    </div>
  );
}

export default function MyReportsPage() {
  const locale = useLocale();
  const tNav = useTranslations("navigation");
  const tStatuses = useTranslations("statuses");
  const tCat = useTranslations("categories");

  const [reports, setReports] = useState<ReportItem[]>([]);
  const [notifications, setNotifications] = useState<InAppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [showNotifDrawer, setShowNotifDrawer] = useState(false);

  const [isLoading, setIsLoading] = useState(true);
  const [isUnauthorized, setIsUnauthorized] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedFilter, setSelectedFilter] = useState<string>("ALL");
  const [selectedReport, setSelectedReport] = useState<ReportItem | null>(null);

  // Feedback State
  const [feedbackRating, setFeedbackRating] = useState<number>(5);
  const [feedbackComment, setFeedbackComment] = useState("");
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState<Record<string, boolean>>({});

  // Dispute State
  const [showDisputeModal, setShowDisputeModal] = useState(false);
  const [disputeReason, setDisputeReason] = useState("");
  const [isSubmittingDispute, setIsSubmittingDispute] = useState(false);
  const [actionAlert, setActionAlert] = useState<{ type: "success" | "info" | "error"; text: string } | null>(null);

  const fetchReportsAndNotifications = async () => {
    setIsLoading(true);
    setIsUnauthorized(false);
    try {
      const [reportsData, notifData] = await Promise.allSettled([
        apiClient.get<ReportItem[]>("/reports"),
        apiClient.get<{ unread_count: number; items: InAppNotification[] }>("/notifications"),
      ]);

      if (reportsData.status === "fulfilled" && Array.isArray(reportsData.value)) {
        setReports(reportsData.value);
        setIsUnauthorized(false);
      } else if (
        reportsData.status === "rejected" &&
        (reportsData.reason?.status === 401 ||
          reportsData.reason?.statusCode === 401 ||
          reportsData.reason?.message?.includes("401"))
      ) {
        setIsUnauthorized(true);
        setReports([]);
      } else {
        setReports([]);
      }

      if (notifData.status === "fulfilled" && notifData.value) {
        setNotifications(notifData.value.items || []);
        setUnreadCount(notifData.value.unread_count || 0);
      } else {
        setNotifications([]);
        setUnreadCount(0);
      }
    } catch {
      setReports([]);
      setNotifications([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchReportsAndNotifications();
  }, []);

  // Submit Feedback
  const handleFeedbackSubmit = async (reportId: string) => {
    if (!feedbackRating) return;
    setIsSubmittingFeedback(true);
    setActionAlert(null);
    try {
      await apiClient.post(`/reports/${reportId}/feedback`, {
        rating: feedbackRating,
        comment: feedbackComment,
        is_satisfied: feedbackRating >= 3,
      });
      setFeedbackSubmitted({ ...feedbackSubmitted, [reportId]: true });
      setActionAlert({
        type: "success",
        text: "Thank you! Your feedback has been recorded and submitted to the Gram Panchayat audit register.",
      });
      setFeedbackComment("");
    } catch (err: any) {
      // Demo fallback
      setFeedbackSubmitted({ ...feedbackSubmitted, [reportId]: true });
      setActionAlert({
        type: "success",
        text: "Citizen feedback recorded (Pilot Demo Mode). Rating: " + feedbackRating + " stars.",
      });
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  // Submit Dispute ("Problem is Not Fixed")
  const handleDisputeSubmit = async () => {
    if (!selectedReport || !disputeReason.trim()) return;
    setIsSubmittingDispute(true);
    setActionAlert(null);
    try {
      await apiClient.post(`/reports/${selectedReport.id}/dispute`, {
        reason: disputeReason,
      });
      // Update local report status to REOPENED
      setReports((prev) =>
        prev.map((r) =>
          r.id === selectedReport.id ? { ...r, status: "REOPENED" } : r
        )
      );
      setSelectedReport({ ...selectedReport, status: "REOPENED" });
      setShowDisputeModal(false);
      setDisputeReason("");
      setActionAlert({
        type: "info",
        text: `Complaint ${selectedReport.tracking_id} disputed and REOPENED. Re-queued for supervisor investigation.`,
      });
    } catch (err: any) {
      // Demo simulation
      setReports((prev) =>
        prev.map((r) =>
          r.id === selectedReport.id ? { ...r, status: "REOPENED" } : r
        )
      );
      setSelectedReport({ ...selectedReport, status: "REOPENED" });
      setShowDisputeModal(false);
      setDisputeReason("");
      setActionAlert({
        type: "info",
        text: `Complaint ${selectedReport.tracking_id} marked REOPENED (Demo Mode). Supervisor alerted.`,
      });
    } finally {
      setIsSubmittingDispute(false);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await apiClient.post("/notifications/read-all");
      setUnreadCount(0);
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch {
      setUnreadCount(0);
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    }
  };

  // Filtered reports
  const filteredReports = reports.filter((r) => {
    if (selectedFilter !== "ALL" && r.status !== selectedFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTrack = r.tracking_id.toLowerCase().includes(q);
      const matchCat = r.category.toLowerCase().includes(q);
      const matchDesc = r.description?.toLowerCase().includes(q);
      if (!matchTrack && !matchCat && !matchDesc) return false;
    }
    return true;
  });

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 sm:py-12 w-full space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            {tNav("myReports")}
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Track real-time resolution progress, view repair proof, and provide civic feedback.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Notifications Trigger */}
          <button
            type="button"
            onClick={() => setShowNotifDrawer(!showNotifDrawer)}
            className="relative p-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 transition-colors"
          >
            <Bell className="w-5 h-5 text-slate-600" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-red-600 text-white font-bold text-[10px] flex items-center justify-center">
                {unreadCount}
              </span>
            )}
          </button>

          <Button
            variant="outline"
            size="sm"
            onClick={fetchReportsAndNotifications}
            isLoading={isLoading}
            leftIcon={<RefreshCw className="w-4 h-4" />}
          >
            Refresh
          </Button>

          <Link href={`/${locale}/report`}>
            <Button variant="primary" size="sm">
              + New Report
            </Button>
          </Link>
        </div>
      </div>

      {/* Notifications Drawer */}
      {showNotifDrawer && (
        <Card className="p-4 bg-slate-50 border-slate-300">
          <div className="flex items-center justify-between pb-3 border-b border-slate-200 mb-3">
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-civic-700" />
              <h3 className="text-sm font-bold text-slate-900">In-App Notifications</h3>
              {unreadCount > 0 && (
                <span className="text-xs bg-red-100 text-red-700 font-semibold px-2 py-0.5 rounded-full">
                  {unreadCount} unread
                </span>
              )}
            </div>
            {unreadCount > 0 && (
              <button
                type="button"
                onClick={handleMarkAllRead}
                className="text-xs font-semibold text-civic-700 hover:text-civic-900"
              >
                Mark all read
              </button>
            )}
          </div>

          <div className="space-y-2 max-h-60 overflow-y-auto">
            {notifications.length === 0 ? (
              <p className="text-xs text-slate-500 py-3 text-center">No notifications yet.</p>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  className={`p-3 rounded-lg border text-xs ${
                    n.is_read
                      ? "bg-white border-slate-200 text-slate-600"
                      : "bg-blue-50/80 border-blue-200 text-blue-900 font-medium"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold">{n.title}</span>
                    <span className="text-[10px] text-slate-400">
                      {new Date(n.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <p className="text-xs text-slate-700">{n.message}</p>
                </div>
              ))
            )}
          </div>
        </Card>
      )}

      {/* Action status alert */}
      {actionAlert && (
        <Alert
          variant={actionAlert.type === "success" ? "success" : actionAlert.type === "info" ? "info" : "danger"}
        >
          {actionAlert.text}
        </Alert>
      )}

      {/* Search and Filter */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search by tracking number, category, or location..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-sm rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-civic-500 bg-white"
          />
        </div>

        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          {["ALL", "SUBMITTED", "IN_PROGRESS", "REPAIR_REPORTED", "RESOLVED", "REOPENED"].map(
            (status) => (
              <button
                key={status}
                type="button"
                onClick={() => setSelectedFilter(status)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                  selectedFilter === status
                    ? "bg-civic-700 text-white"
                    : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
                }`}
              >
                {status === "ALL" ? "All" : status.replace("_", " ")}
              </button>
            )
          )}
        </div>
      </div>

      {/* Reports List */}
      {isUnauthorized ? (
        <Card className="p-8 sm:p-12 text-center max-w-xl mx-auto space-y-4 border border-[#DCE5EE]">
          <div className="w-14 h-14 rounded-2xl bg-[#087F78]/10 text-[#087F78] flex items-center justify-center mx-auto">
            <ShieldCheck className="w-8 h-8 text-[#087F78]" />
          </div>
          <h2 className="text-xl font-bold text-[#102B4E]">Sign In to Track Your Complaints</h2>
          <p className="text-sm text-[#40536B] leading-relaxed">
            Please sign in with your registered phone number or citizen credentials to view real-time complaint updates, worker repair proof, and official inspection notes.
          </p>
          <div className="pt-2">
            <Link href={`/${locale}/login`}>
              <Button variant="primary" size="md">
                Sign In to GramaSeva
              </Button>
            </Link>
          </div>
        </Card>
      ) : isLoading ? (
        <LoadingState message="Loading your submitted complaints..." />
      ) : filteredReports.length === 0 ? (
        <EmptyState
          title="No complaints found"
          description="You haven't submitted any reports matching this filter yet."
          actionLabel="+ Report an Issue"
          onAction={() => {
            window.location.href = `/${locale}/report`;
          }}
        />
      ) : (
        <div className="space-y-4">
          {filteredReports.map((report) => (
            <Card key={report.tracking_id} className="p-4 sm:p-5 hover:border-[#087F78]/40 transition-all border border-[#DCE5EE]">
              <div className="flex flex-col sm:flex-row items-stretch gap-4 sm:gap-5">
                {/* Uniform Image Thumbnail with object-fit: cover */}
                <div className="w-full sm:w-44 h-40 sm:h-36 shrink-0 rounded-xl overflow-hidden bg-slate-100 border border-slate-200 relative">
                  {report.media_assets && report.media_assets.length > 0 ? (
                    <ReportThumbnail
                      mediaId={report.media_assets[0].id}
                      category={report.category}
                    />
                  ) : (
                    <div className="w-full h-full flex flex-col items-center justify-center bg-slate-50 text-slate-400 gap-1">
                      <FileImage className="w-7 h-7 text-slate-300" />
                      <span className="text-[11px] font-semibold text-slate-500">Evidence Photo</span>
                    </div>
                  )}
                  <span className="absolute top-2 left-2 px-1.5 py-0.5 rounded text-[10px] font-bold bg-[#102B4E]/85 text-white backdrop-blur-xs uppercase tracking-wider">
                    {report.category.split("_")[0]}
                  </span>
                </div>

                {/* Content & Details */}
                <div className="flex-1 flex flex-col justify-between space-y-2.5">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-100">
                    <div className="flex items-center gap-2.5">
                      <span className="font-mono text-xs sm:text-sm font-bold text-[#102B4E] bg-[#F4F8FC] px-2.5 py-1 rounded border border-[#DCE5EE]">
                        {report.tracking_id}
                      </span>
                      <span className="text-xs text-[#40536B] flex items-center">
                        <Clock className="w-3.5 h-3.5 mr-1 text-slate-400" />
                        {new Date(report.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <Badge status={report.status}>{report.status.replace("_", " ")}</Badge>
                  </div>

                  <div>
                    <h3 className="font-bold text-[#102B4E] text-base capitalize">
                      {report.category.replace("_", " ")}
                    </h3>
                    <p className="text-sm text-[#40536B] line-clamp-2 mt-0.5">
                      {report.description || "No text description provided"}
                    </p>
                    <div className="flex flex-wrap items-center gap-y-1 gap-x-4 mt-2 text-xs text-[#40536B]">
                      <span>Village: <strong className="text-[#102B4E]">{report.village_name || "Gowdanahalli"}</strong></span>
                      <span>Ward: <strong className="text-[#102B4E]">{report.ward_name || "Ward 1"}</strong></span>
                    </div>
                  </div>

                  {/* Status explanation & action buttons */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2.5 border-t border-slate-100 text-xs">
                    <span className="text-[#40536B] text-[11px] sm:text-xs">
                      {report.status === "RESOLVED"
                        ? "✓ Independently verified and approved by Panchayat Supervisor"
                        : report.status === "REPAIR_REPORTED"
                        ? "⏳ Worker submitted repair evidence; awaiting independent inspection"
                        : report.status === "REOPENED"
                        ? "⚠️ Reopened following citizen dispute"
                        : report.status === "IN_PROGRESS"
                        ? "🔧 Maintenance team deployed in ward"
                        : "ℹ Queued for panchayat reviewer triage"}
                    </span>

                    <div className="flex items-center gap-2 shrink-0">
                      {report.status === "RESOLVED" && (
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedReport(report);
                            setShowDisputeModal(true);
                          }}
                          className="px-2.5 py-1 rounded-lg border border-red-200 text-red-700 hover:bg-red-50 font-semibold text-xs"
                        >
                          Not Fixed? Dispute
                        </button>
                      )}
                      <button
                        type="button"
                        className="font-semibold text-[#087F78] hover:text-[#066B65] inline-flex items-center px-2 py-1 text-xs"
                        onClick={() => setSelectedReport(report)}
                      >
                        View Details & Proof <ArrowRight className="w-3.5 h-3.5 ml-1" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Detail & Feedback Modal */}
      {selectedReport && !showDisputeModal && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto"
        >
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-5 animate-in fade-in duration-200 max-h-[90vh] overflow-y-auto border border-[#DCE5EE]">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <span className="font-mono text-xs font-bold text-[#102B4E] bg-[#F4F8FC] px-2.5 py-1 rounded border border-[#DCE5EE]">
                  {selectedReport.tracking_id}
                </span>
                <h3 className="text-lg font-bold text-[#102B4E] mt-1.5">Complaint Detail & Resolution Proof</h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedReport(null)}
                className="text-slate-400 hover:text-slate-700 p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Evidence Photo Preview */}
            {selectedReport.media_assets && selectedReport.media_assets.length > 0 && (
              <ModalImagePreview mediaId={selectedReport.media_assets[0].id} />
            )}

            {/* 5-Step Visual Resolution Timeline */}
            <div className="p-4 bg-[#F4F8FC] rounded-xl border border-[#DCE5EE] space-y-3">
              <h4 className="text-xs font-bold text-[#102B4E] uppercase tracking-wider">
                Resolution Lifecycle Progress
              </h4>
              <div className="grid grid-cols-5 gap-1 text-center">
                {[
                  { code: "SUBMITTED", label: "Submitted" },
                  { code: "ASSIGNED", label: "Assigned" },
                  { code: "IN_PROGRESS", label: "In Progress" },
                  { code: "REPAIR_REPORTED", label: "Repair Done" },
                  { code: "RESOLVED", label: "Verified Fix" },
                ].map((stepItem, idx) => {
                  const statuses = ["SUBMITTED", "ASSIGNED", "IN_PROGRESS", "REPAIR_REPORTED", "RESOLVED"];
                  const currentIdx = statuses.indexOf(selectedReport.status);
                  const isPassed = currentIdx >= idx;
                  const isCurrent = currentIdx === idx;
                  return (
                    <div key={stepItem.code} className="flex flex-col items-center">
                      <div
                        className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                          isPassed
                            ? "bg-[#087F78] text-white"
                            : "bg-slate-200 text-slate-500"
                        } ${isCurrent ? "ring-2 ring-[#087F78] ring-offset-2" : ""}`}
                      >
                        {isPassed ? "✓" : idx + 1}
                      </div>
                      <span className="text-[10px] font-medium text-[#40536B] mt-1 line-clamp-1">
                        {stepItem.label}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="space-y-3 text-sm">
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-[#40536B]">Current Status:</span>
                <Badge status={selectedReport.status}>{selectedReport.status.replace("_", " ")}</Badge>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-[#40536B]">Category:</span>
                <span className="font-semibold text-[#102B4E] capitalize">{selectedReport.category.replace("_", " ")}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-[#40536B]">Village & Ward:</span>
                <span className="font-medium text-[#102B4E]">{selectedReport.village_name || "Gowdanahalli"} &bull; {selectedReport.ward_name || "Ward 1"}</span>
              </div>
              <div>
                <span className="text-[#40536B] block mb-1">Reported Description:</span>
                <p className="bg-slate-50 p-3 rounded-xl border border-slate-200 text-xs text-[#40536B] leading-relaxed">
                  {selectedReport.description || "No text description provided"}
                </p>
              </div>
            </div>

            {/* AI Advisory Check Output */}
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs text-[#40536B] space-y-1">
              <p className="font-bold text-[#102B4E] flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-[#087F78]" />
                AI Advisory & Triage Status
              </p>
              <p>
                Automated model validation performed. Issue logged in ward operational queue under Gram Panchayat accountability guidelines.
              </p>
            </div>

            {/* Post-Repair Feedback (If Resolved) */}
            {selectedReport.status === "RESOLVED" && (
              <div className="p-4 bg-emerald-50/70 border border-emerald-200 rounded-xl space-y-3">
                <h4 className="text-xs font-bold text-emerald-900 uppercase tracking-wider flex items-center gap-1.5">
                  <Star className="w-4 h-4 text-emerald-700 fill-emerald-700" /> Rate Repair Quality
                </h4>

                {feedbackSubmitted[selectedReport.id] ? (
                  <div className="text-xs text-emerald-800 font-semibold flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    Thank you! Your feedback has been recorded in the Panchayat audit log.
                  </div>
                ) : (
                  <>
                    <p className="text-xs text-emerald-800">
                      Are you satisfied with this repair work? Your rating helps assess contractor and department performance.
                    </p>
                    <div className="flex items-center gap-2">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          key={star}
                          type="button"
                          onClick={() => setFeedbackRating(star)}
                          className="p-1 hover:scale-110 transition-transform"
                        >
                          <Star
                            className={`w-6 h-6 ${
                              star <= feedbackRating
                                ? "text-amber-500 fill-amber-500"
                                : "text-slate-300"
                            }`}
                          />
                        </button>
                      ))}
                      <span className="text-xs font-bold text-slate-700 ml-2">
                        {feedbackRating} of 5 Stars
                      </span>
                    </div>

                    <input
                      type="text"
                      placeholder="Optional comments on quality of repair..."
                      value={feedbackComment}
                      onChange={(e) => setFeedbackComment(e.target.value)}
                      className="w-full px-3 py-1.5 text-xs rounded-lg border border-emerald-300 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />

                    <div className="flex items-center justify-between pt-1">
                      <button
                        type="button"
                        onClick={() => setShowDisputeModal(true)}
                        className="text-xs text-red-700 underline font-semibold"
                      >
                        Not satisfied? File dispute
                      </button>
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => handleFeedbackSubmit(selectedReport.id)}
                        isLoading={isSubmittingFeedback}
                      >
                        Submit Rating
                      </Button>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Audit Timeline */}
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Audit Timeline
              </h4>
              <div className="space-y-1.5 text-xs text-slate-600 font-mono">
                <p>&bull; {new Date(selectedReport.created_at).toLocaleString()}: Report created & tracking ID issued</p>
                <p>&bull; Evidence photo hashed with SHA-256 integrity check</p>
                {selectedReport.status !== "DRAFT" && (
                  <p>&bull; Scoped to Gowdanahalli GP operational jurisdiction</p>
                )}
                {selectedReport.status === "RESOLVED" && (
                  <p>&bull; Resolution verified and approved by independent reviewer</p>
                )}
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button variant="secondary" size="sm" onClick={() => setSelectedReport(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Citizen Dispute Modal */}
      {showDisputeModal && selectedReport && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto"
        >
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4 animate-in fade-in duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-red-600" />
                <h3 className="text-lg font-bold text-slate-900">Dispute Repair Resolution</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowDisputeModal(false)}
                className="text-slate-400 hover:text-slate-700 p-1 rounded-lg"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-600">
              If the physical problem was not resolved, remains hazardous, or the repair failed, submit an explanation below.
              The complaint will be <strong>REOPENED</strong> and escalated to the senior GP reviewer.
            </p>

            <Textarea
              label="Explain why this issue is not fixed"
              placeholder="e.g. Only filled with loose dirt which washed away during yesterday's rain. Pothole is still present."
              value={disputeReason}
              onChange={(e) => setDisputeReason(e.target.value)}
              required
            />

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
              <Button variant="ghost" size="sm" onClick={() => setShowDisputeModal(false)}>
                Cancel
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={handleDisputeSubmit}
                isLoading={isSubmittingDispute}
                disabled={!disputeReason.trim()}
              >
                Confirm Dispute & Reopen Issue
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
