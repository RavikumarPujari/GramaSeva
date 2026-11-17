"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useTranslations, useLocale } from "next-intl";
import {
  Map as MapIcon,
  List,
  Filter,
  CheckCircle2,
  Clock,
  ShieldCheck,
  AlertCircle,
  Eye,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge, type StatusType } from "@/components/ui/Badge";
import { Select } from "@/components/ui/Select";

export default function PublicDashboardPage() {
  const locale = useLocale();
  const tNav = useTranslations("navigation");
  const tStatuses = useTranslations("statuses");

  const [viewMode, setViewMode] = useState<"list" | "map">("list");
  const [selectedVillage, setSelectedVillage] = useState<string>("all");
  const [selectedWard, setSelectedWard] = useState<string>("all");

  // Sample sanitized issues (strictly sanitized public projection: no phone, no reporter names, generalized location)
  const publicIssues = [
    {
      id: "ISSUE-101",
      category: "Road Damage & Potholes",
      village: "Gowdanahalli",
      ward: "Ward 2 (Primary School Road)",
      status: "IN_PROGRESS" as StatusType,
      submissionsCount: 3, // Multiple citizens linked to 1 physical issue
      reportedDate: "2026-11-14",
      summary: "Pothole on Main School Curve",
    },
    {
      id: "ISSUE-098",
      category: "Visible Water Leakage",
      village: "Gowdanahalli",
      ward: "Ward 1 (Post Office)",
      status: "REPAIR_REPORTED" as StatusType,
      submissionsCount: 2,
      reportedDate: "2026-11-12",
      summary: "Pipeline leakage near public tap",
    },
    {
      id: "ISSUE-089",
      category: "Streetlight Not Working",
      village: "Malleshwarapuram",
      ward: "Ward 1 (Lakeview Road)",
      status: "RESOLVED" as StatusType,
      submissionsCount: 1,
      reportedDate: "2026-11-05",
      summary: "Pole #14 LED bulb replaced",
    },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:py-10 w-full">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
              Sanitized Public Transparency Portal
            </span>
            <span className="text-xs text-slate-500">
              Coverage: <strong>Mandya District · Pilot Panchayats</strong>
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Village & Ward Issue Tracker
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Real civic progress open to everyone. Privacy guaranteed — reporter details and private coordinates are never shown.
          </p>
        </div>

        {/* View mode toggle */}
        <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1 shadow-sm">
          <button
            type="button"
            onClick={() => setViewMode("list")}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              viewMode === "list"
                ? "bg-civic-600 text-white shadow-sm font-semibold"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <List className="w-4 h-4" /> List View
          </button>
          <button
            type="button"
            onClick={() => setViewMode("map")}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              viewMode === "map"
                ? "bg-civic-600 text-white shadow-sm font-semibold"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <MapIcon className="w-4 h-4" /> Map View
          </button>
        </div>
      </div>

      {/* Ward-level Accountability Metrics Bar (README Section 3.4) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-8">
        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <p className="text-xs font-semibold text-slate-500 uppercase">Unique Issues</p>
          <p className="text-2xl font-extrabold text-slate-900 mt-1">24</p>
          <p className="text-[11px] text-slate-400 mt-0.5">Physical problems</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <p className="text-xs font-semibold text-slate-500 uppercase">Submissions</p>
          <p className="text-2xl font-extrabold text-slate-900 mt-1">42</p>
          <p className="text-[11px] text-slate-400 mt-0.5">Total citizen reports</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <p className="text-xs font-semibold text-slate-500 uppercase">In Progress</p>
          <p className="text-2xl font-extrabold text-blue-600 mt-1">8</p>
          <p className="text-[11px] text-slate-400 mt-0.5">Active field tasks</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <p className="text-xs font-semibold text-slate-500 uppercase">Repair Reported</p>
          <p className="text-2xl font-extrabold text-orange-600 mt-1">3</p>
          <p className="text-[11px] text-slate-400 mt-0.5">Awaiting verification</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <p className="text-xs font-semibold text-slate-500 uppercase">Verified Resolved</p>
          <p className="text-2xl font-extrabold text-emerald-600 mt-1">11</p>
          <p className="text-[11px] text-slate-400 mt-0.5">Independently closed</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <p className="text-xs font-semibold text-slate-500 uppercase">Reopened</p>
          <p className="text-2xl font-extrabold text-rose-600 mt-1">1</p>
          <p className="text-[11px] text-slate-400 mt-0.5">Disputed by citizens</p>
        </div>
      </div>

      {/* Main View Area */}
      {viewMode === "list" ? (
        <Card className="p-0 overflow-hidden">
          <div className="p-4 border-b border-slate-100 bg-slate-50 flex items-center justify-between text-xs text-slate-500">
            <span>Showing verified public issues. Note: Multiple citizen reports link to one physical issue.</span>
            <span>Refreshed: Today</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-700">
              <thead className="bg-white border-b border-slate-200 text-xs uppercase font-semibold text-slate-500">
                <tr>
                  <th className="py-3.5 px-4">Issue ID</th>
                  <th className="py-3.5 px-4">Category & Summary</th>
                  <th className="py-3.5 px-4">Village / Ward</th>
                  <th className="py-3.5 px-4">Reports Linked</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {publicIssues.map((issue) => (
                  <tr key={issue.id} className="hover:bg-slate-50/50">
                    <td className="py-3.5 px-4 font-mono font-bold text-slate-800 text-xs">
                      {issue.id}
                    </td>
                    <td className="py-3.5 px-4">
                      <p className="font-semibold text-slate-900">{issue.summary}</p>
                      <p className="text-xs text-slate-500">{issue.category}</p>
                    </td>
                    <td className="py-3.5 px-4 text-xs">
                      <p className="font-medium text-slate-800">{issue.village}</p>
                      <p className="text-slate-500">{issue.ward}</p>
                    </td>
                    <td className="py-3.5 px-4 text-xs">
                      <span className="font-semibold text-civic-700 bg-civic-50 px-2 py-0.5 rounded border border-civic-200">
                        {issue.submissionsCount} {issue.submissionsCount > 1 ? "submissions" : "submission"}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <Badge status={issue.status}>
                        {tStatuses(issue.status as any)}
                      </Badge>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <Button variant="ghost" size="sm">
                        View Public Timeline
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        <Card className="p-8 text-center bg-slate-50 border-dashed border-slate-300">
          <MapIcon className="w-12 h-12 text-slate-400 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-800">Public Geographic Map</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 mb-4">
            Interactive OpenStreetMap layer with ward polygon boundaries and generalized issue markers. (Full Leaflet integration wired in Phase 5).
          </p>
          <Button variant="outline" size="sm" onClick={() => setViewMode("list")}>
            Switch to Accessible Table View
          </Button>
        </Card>
      )}
    </div>
  );
}
