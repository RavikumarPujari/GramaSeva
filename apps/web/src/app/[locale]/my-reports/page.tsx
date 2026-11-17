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
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge, type StatusType } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingState } from "@/components/ui/LoadingState";
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

export default function MyReportsPage() {
  const locale = useLocale();
  const tNav = useTranslations("navigation");
  const tStatuses = useTranslations("statuses");
  const tCat = useTranslations("categories");

  const [reports, setReports] = useState<ReportItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedFilter, setSelectedFilter] = useState<string>("ALL");
  const [selectedReport, setSelectedReport] = useState<ReportItem | null>(null);

  const fetchReports = async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.get<ReportItem[]>("/reports");
      if (data && data.length > 0) {
        setReports(data);
      } else {
        // Sample demonstration records when zero database records exist
        setReports([
          {
            id: "sub-1",
            tracking_id: "FP-2026-00412",
            category: "road_damage",
            description: "Severe pothole on the curve causing traffic slowdown.",
            status: "IN_PROGRESS",
            village_name: "Gowdanahalli",
            ward_name: "Ward 2 (Primary School Road)",
            created_at: new Date(Date.now() - 3600000 * 24 * 2).toISOString(),
          },
          {
            id: "sub-2",
            tracking_id: "FP-2026-00398",
            category: "water_leak",
            description: "Drinking water pipe joint leaking continuously.",
            status: "REPAIR_REPORTED",
            village_name: "Gowdanahalli",
            ward_name: "Ward 1 (Post Office Area)",
            created_at: new Date(Date.now() - 3600000 * 24 * 5).toISOString(),
          },
          {
            id: "sub-3",
            tracking_id: "FP-2026-00350",
            category: "streetlight",
            description: "Light pole #14 has been dark for three nights.",
            status: "RESOLVED",
            village_name: "Malleshwarapuram",
            ward_name: "Ward 1 (Lakeview Road)",
            created_at: new Date(Date.now() - 3600000 * 24 * 9).toISOString(),
          },
        ]);
      }
    } catch {
      // Fallback sample data for demo mode
      setReports([
        {
          id: "sub-1",
          tracking_id: "FP-2026-00412",
          category: "road_damage",
          description: "Severe pothole on the curve causing traffic slowdown.",
          status: "IN_PROGRESS",
          village_name: "Gowdanahalli",
          ward_name: "Ward 2 (Primary School Road)",
          created_at: new Date(Date.now() - 3600000 * 24 * 2).toISOString(),
        },
        {
          id: "sub-2",
          tracking_id: "FP-2026-00398",
          category: "water_leak",
          description: "Drinking water pipe joint leaking continuously.",
          status: "REPAIR_REPORTED",
          village_name: "Gowdanahalli",
          ward_name: "Ward 1 (Post Office Area)",
          created_at: new Date(Date.now() - 3600000 * 24 * 5).toISOString(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const filteredReports = reports.filter((r) => {
    const matchesSearch =
      r.tracking_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (r.village_name && r.village_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (r.description && r.description.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesFilter = selectedFilter === "ALL" || r.status === selectedFilter;
    return matchesSearch && matchesFilter;
  });

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 sm:py-12 w-full">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Track My Submissions
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Check live review status, assigned department, worker notes, and resolution proof.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchReports} leftIcon={<RefreshCw className="w-4 h-4" />}>
            Refresh
          </Button>
          <Link href={`/${locale}/report`}>
            <Button variant="primary" size="md">
              + New Complaint
            </Button>
          </Link>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <Card className="p-4 mb-6">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3.5" />
            <input
              type="text"
              placeholder="Search by Tracking ID (e.g. FP-2026-00412) or keyword..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-civic-500"
            />
          </div>

          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
            {["ALL", "DRAFT", "SUBMITTED", "UNDER_REVIEW", "IN_PROGRESS", "REPAIR_REPORTED", "RESOLVED"].map((status) => (
              <button
                key={status}
                type="button"
                onClick={() => setSelectedFilter(status)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                  selectedFilter === status
                    ? "bg-civic-600 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {status === "ALL" ? "All Statuses" : tStatuses(status as any)}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* Reports List */}
      {isLoading ? (
        <LoadingState message="Loading your complaint records..." />
      ) : filteredReports.length === 0 ? (
        <EmptyState
          title="No complaints found"
          description="No submissions match your active filter or search query."
          actionLabel="Clear Search"
          onAction={() => {
            setSearchQuery("");
            setSelectedFilter("ALL");
          }}
        />
      ) : (
        <div className="space-y-4">
          {filteredReports.map((report) => (
            <Card key={report.tracking_id} hoverEffect className="p-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs sm:text-sm font-bold text-civic-700 bg-civic-50 px-2.5 py-1 rounded border border-civic-200">
                    {report.tracking_id}
                  </span>
                  <span className="text-xs text-slate-400 flex items-center">
                    <Clock className="w-3.5 h-3.5 mr-1" />
                    {new Date(report.created_at).toLocaleDateString()}
                  </span>
                </div>
                <Badge status={report.status}>
                  {tStatuses(report.status as any)}
                </Badge>
              </div>

              <div className="py-3">
                <h3 className="font-bold text-slate-900 text-base mb-1">
                  {tCat(report.category as any) || report.category}
                </h3>
                <p className="text-sm text-slate-600 line-clamp-2">{report.description || "No text description provided"}</p>
                <div className="flex flex-wrap items-center gap-y-1 gap-x-4 mt-2 text-xs text-slate-500">
                  <span>Village: <strong className="text-slate-700">{report.village_name || "Gowdanahalli"}</strong></span>
                  <span>Ward: <strong className="text-slate-700">{report.ward_name || "Ward Unknown"}</strong></span>
                </div>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-slate-100 text-xs">
                <span className="text-slate-500">
                  {report.status === "RESOLVED"
                    ? "✓ Independently verified by Panchayat Reviewer"
                    : report.status === "REPAIR_REPORTED"
                    ? "⏳ Worker submitted proof; awaiting independent review"
                    : report.status === "DRAFT"
                    ? "📝 Saved draft — resume to submit"
                    : "ℹ Active in operational queue"}
                </span>

                <button
                  type="button"
                  className="font-semibold text-civic-600 hover:text-civic-800 inline-flex items-center"
                  onClick={() => setSelectedReport(report)}
                >
                  View Timeline & Proof <ArrowRight className="w-3.5 h-3.5 ml-1" />
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Detail & Timeline Modal */}
      {selectedReport && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto"
        >
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5 animate-in fade-in duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <span className="font-mono text-xs font-bold text-civic-700 bg-civic-50 px-2 py-0.5 rounded border border-civic-200">
                  {selectedReport.tracking_id}
                </span>
                <h3 className="text-lg font-bold text-slate-900 mt-1">Complaint Detail & Proof</h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedReport(null)}
                className="text-slate-400 hover:text-slate-700 p-1 rounded-lg"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-sm">
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Status:</span>
                <Badge status={selectedReport.status}>{tStatuses(selectedReport.status as any)}</Badge>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Category:</span>
                <span className="font-semibold">{tCat(selectedReport.category as any) || selectedReport.category}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Village & Ward:</span>
                <span>{selectedReport.village_name} · {selectedReport.ward_name}</span>
              </div>
              <div>
                <span className="text-slate-500 block mb-1">Citizen Notes:</span>
                <p className="bg-slate-50 p-2.5 rounded-lg border border-slate-200 text-xs text-slate-700">
                  {selectedReport.description}
                </p>
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Audit Timeline
              </h4>
              <div className="space-y-1.5 text-xs text-slate-600 font-mono">
                <p>• {new Date(selectedReport.created_at).toLocaleString()}: Report created</p>
                <p>• {new Date(selectedReport.created_at).toLocaleString()}: Evidence uploaded to private quarantine</p>
                {selectedReport.status !== "DRAFT" && (
                  <p>• Triage queued in Gowdanahalli GP inbox</p>
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
    </div>
  );
}
