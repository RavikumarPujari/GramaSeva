"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useTranslations, useLocale } from "next-intl";
import {
  Search,
  Filter,
  FileText,
  Clock,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Badge, type StatusType } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";

interface DemoReport {
  trackingId: string;
  category: string;
  categoryLabel: string;
  village: string;
  ward: string;
  status: StatusType;
  date: string;
  description: string;
}

export default function MyReportsPage() {
  const locale = useLocale();
  const tNav = useTranslations("navigation");
  const tStatuses = useTranslations("statuses");

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedFilter, setSelectedFilter] = useState<string>("ALL");

  // Sample structured demonstration records (labeled as sample per Section 0.2)
  const sampleReports: DemoReport[] = [
    {
      trackingId: "FP-2026-00412",
      category: "road_damage",
      categoryLabel: "Road Damage & Potholes",
      village: "Gowdanahalli",
      ward: "Ward 2 (Primary School Road)",
      status: "IN_PROGRESS",
      date: "2026-11-15",
      description: "Severe pothole on the curve causing traffic slowdown.",
    },
    {
      trackingId: "FP-2026-00398",
      category: "water_leak",
      categoryLabel: "Visible Water Leakage",
      village: "Gowdanahalli",
      ward: "Ward 1 (Post Office)",
      status: "REPAIR_REPORTED",
      date: "2026-11-12",
      description: "Drinking water pipe joint leaking continuously.",
    },
    {
      trackingId: "FP-2026-00350",
      category: "streetlight",
      categoryLabel: "Streetlight Not Working",
      village: "Malleshwarapuram",
      ward: "Ward 3 (Market Road)",
      status: "RESOLVED",
      date: "2026-11-08",
      description: "Light pole #14 has been dark for three nights.",
    },
  ];

  const filteredReports = sampleReports.filter((r) => {
    const matchesSearch =
      r.trackingId.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.categoryLabel.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.village.toLowerCase().includes(searchQuery.toLowerCase());
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
            Check live review, worker updates, and independent verification proof.
          </p>
        </div>
        <Link href={`/${locale}/report`}>
          <Button variant="primary" size="md">
            + New Complaint
          </Button>
        </Link>
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
            {["ALL", "UNDER_REVIEW", "IN_PROGRESS", "REPAIR_REPORTED", "RESOLVED"].map((status) => (
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
      <div className="space-y-4">
        {filteredReports.length === 0 ? (
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
          filteredReports.map((report) => (
            <Card key={report.trackingId} hoverEffect className="p-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs sm:text-sm font-bold text-civic-700 bg-civic-50 px-2.5 py-1 rounded border border-civic-200">
                    {report.trackingId}
                  </span>
                  <span className="text-xs text-slate-400 flex items-center">
                    <Clock className="w-3.5 h-3.5 mr-1" />
                    {report.date}
                  </span>
                </div>
                <Badge status={report.status}>
                  {tStatuses(report.status as any)}
                </Badge>
              </div>

              <div className="py-3">
                <h3 className="font-bold text-slate-900 text-base mb-1">
                  {report.categoryLabel}
                </h3>
                <p className="text-sm text-slate-600 line-clamp-2">{report.description}</p>
                <div className="flex flex-wrap items-center gap-y-1 gap-x-4 mt-2 text-xs text-slate-500">
                  <span>Village: <strong className="text-slate-700">{report.village}</strong></span>
                  <span>Ward: <strong className="text-slate-700">{report.ward}</strong></span>
                </div>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-slate-100 text-xs">
                <span className="text-slate-500">
                  {report.status === "RESOLVED"
                    ? "✓ Independently verified by Panchayat Reviewer"
                    : report.status === "REPAIR_REPORTED"
                    ? "⏳ Worker submitted proof; awaiting independent review"
                    : "ℹ Active in operational queue"}
                </span>

                <button
                  type="button"
                  className="font-semibold text-civic-600 hover:text-civic-800 inline-flex items-center"
                  onClick={() => alert(`Tracking detail view for ${report.trackingId} (Phase 3)`)}
                >
                  View Timeline & Proof <ArrowRight className="w-3.5 h-3.5 ml-1" />
                </button>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
