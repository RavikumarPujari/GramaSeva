"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useTranslations, useLocale } from "next-intl";
import {
  ClipboardList,
  CheckCircle2,
  XCircle,
  Filter,
  Users,
  ShieldAlert,
  Building,
  Layers,
  FileCheck,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";

export default function StaffPage() {
  const locale = useLocale();
  const tNav = useTranslations("navigation");
  const tStatuses = useTranslations("statuses");

  const [activeTab, setActiveTab] = useState<"inbox" | "verification" | "duplicates">("inbox");

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:py-10 w-full">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 rounded text-xs font-semibold bg-indigo-100 text-indigo-800 border border-indigo-200">
              Authority Reviewer Portal
            </span>
            <span className="text-xs text-slate-500">
              Jurisdiction: <strong>Gowdanahalli Gram Panchayat</strong>
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Panchayat Triage & Independent Review
          </h1>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            Refresh Inbox
          </Button>
          <Button variant="primary" size="sm">
            Export Audit Log
          </Button>
        </div>
      </div>

      <Alert variant="info" className="mb-6">
        <strong>Separation of Duty Rule:</strong> Reviewers cannot approve repair closures for tasks they performed as field workers. All status changes produce immutable audit records.
      </Alert>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 mb-6 gap-2">
        <button
          type="button"
          onClick={() => setActiveTab("inbox")}
          className={`pb-3 px-3 text-sm font-semibold border-b-2 transition-colors inline-flex items-center gap-2 ${
            activeTab === "inbox"
              ? "border-civic-600 text-civic-700"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <ClipboardList className="w-4 h-4" />
          New Triage Inbox (3)
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("verification")}
          className={`pb-3 px-3 text-sm font-semibold border-b-2 transition-colors inline-flex items-center gap-2 ${
            activeTab === "verification"
              ? "border-civic-600 text-civic-700"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <FileCheck className="w-4 h-4" />
          Independent Resolution Verification (1)
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("duplicates")}
          className={`pb-3 px-3 text-sm font-semibold border-b-2 transition-colors inline-flex items-center gap-2 ${
            activeTab === "duplicates"
              ? "border-civic-600 text-civic-700"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Layers className="w-4 h-4" />
          Duplicate Candidates (2)
        </button>
      </div>

      {/* Content based on tab */}
      {activeTab === "inbox" && (
        <Card className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-700">
              <thead className="bg-slate-50 border-b border-slate-200 text-xs uppercase font-semibold text-slate-500">
                <tr>
                  <th className="py-3.5 px-4">Tracking ID</th>
                  <th className="py-3.5 px-4">Category</th>
                  <th className="py-3.5 px-4">Village / Ward</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4">Submitted</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                <tr className="hover:bg-slate-50/50">
                  <td className="py-3.5 px-4 font-mono font-semibold text-civic-700">
                    FP-2026-00412
                  </td>
                  <td className="py-3.5 px-4 font-medium">Road Damage & Potholes</td>
                  <td className="py-3.5 px-4">Gowdanahalli / Ward 2</td>
                  <td className="py-3.5 px-4">
                    <Badge status="UNDER_REVIEW">Under Review</Badge>
                  </td>
                  <td className="py-3.5 px-4 text-xs text-slate-500">2 hours ago</td>
                  <td className="py-3.5 px-4 text-right">
                    <Button variant="outline" size="sm">
                      Triage & Assign
                    </Button>
                  </td>
                </tr>

                <tr className="hover:bg-slate-50/50">
                  <td className="py-3.5 px-4 font-mono font-semibold text-civic-700">
                    FP-2026-00415
                  </td>
                  <td className="py-3.5 px-4 font-medium">Visible Water Leakage</td>
                  <td className="py-3.5 px-4">
                    Gowdanahalli / <span className="text-amber-600 font-semibold">Ward Unknown</span>
                  </td>
                  <td className="py-3.5 px-4">
                    <Badge status="SUBMITTED">Submitted</Badge>
                  </td>
                  <td className="py-3.5 px-4 text-xs text-slate-500">4 hours ago</td>
                  <td className="py-3.5 px-4 text-right">
                    <Button variant="outline" size="sm">
                      Assign Ward
                    </Button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {activeTab === "verification" && (
        <Card className="p-6">
          <div className="flex items-start justify-between pb-4 border-b border-slate-200 mb-6">
            <div>
              <span className="text-xs font-mono font-bold text-civic-700 bg-civic-50 px-2 py-0.5 rounded border border-civic-200">
                FP-2026-00398
              </span>
              <h3 className="text-lg font-bold text-slate-900 mt-1">
                Visible Water Leakage — Independent Verification Required
              </h3>
              <p className="text-xs text-slate-500">
                Field worker marked repair complete. Inspect evidence to confirm resolution.
              </p>
            </div>
            <Badge status="REPAIR_REPORTED">Repair Reported</Badge>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="border border-slate-200 rounded-xl p-4 bg-slate-50">
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                Original Citizen Evidence (Before)
              </h4>
              <div className="h-48 bg-slate-200 rounded-lg flex items-center justify-center text-slate-500 text-xs">
                [Original Photo: Water pipe leaking at junction]
              </div>
              <p className="text-xs text-slate-500 mt-2">Captured: 2026-11-12 09:30 AM</p>
            </div>

            <div className="border border-slate-200 rounded-xl p-4 bg-emerald-50/30 border-emerald-200">
              <h4 className="text-xs font-bold text-emerald-800 uppercase tracking-wider mb-2">
                Field Worker Repair Proof (After)
              </h4>
              <div className="h-48 bg-emerald-100/50 rounded-lg flex items-center justify-center text-emerald-700 text-xs">
                [Repair Photo: Replaced clamp & dry ground]
              </div>
              <p className="text-xs text-slate-500 mt-2">Submitted: 2026-11-16 04:15 PM by Worker ID: W-104</p>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
            <Button variant="danger" size="md">
              Request Better Evidence / Reopen
            </Button>
            <Button variant="success" size="md" leftIcon={<CheckCircle2 className="w-5 h-5" />}>
              Approve Independent Resolution
            </Button>
          </div>
        </Card>
      )}

      {activeTab === "duplicates" && (
        <Card className="p-6">
          <h3 className="text-lg font-bold text-slate-900 mb-2">
            Possible Duplicate Reports (Human Review Required)
          </h3>
          <p className="text-sm text-slate-600 mb-4">
            README Rule: Never auto-merge submissions. Nearby potholes or leaks can be separate physical issues. Reviewers decide whether to link submissions to one physical issue.
          </p>

          <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-3">
            <div className="flex justify-between items-center text-sm font-semibold">
              <span>Candidate Match: Submission A (#FP-412) & Submission B (#FP-418)</span>
              <Badge variant="warning">35m apart · Same category</Badge>
            </div>
            <p className="text-xs text-slate-600">
              Both reported on Primary School Road within 48 hours. Review photos before linking.
            </p>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" size="sm">Keep Separate Issues</Button>
              <Button variant="primary" size="sm">Link to Shared Issue</Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
