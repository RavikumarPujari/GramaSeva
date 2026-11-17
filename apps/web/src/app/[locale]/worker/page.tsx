"use client";

import React, { useState } from "react";
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
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Textarea } from "@/components/ui/Input";
import { Alert } from "@/components/ui/Alert";

export default function WorkerPage() {
  const locale = useLocale();
  const tNav = useTranslations("navigation");
  const tStatuses = useTranslations("statuses");

  const [activeTask, setActiveTask] = useState<string>("TASK-802");
  const [workNotes, setWorkNotes] = useState("");

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 sm:py-10 w-full">
      {/* Header */}
      <div className="mb-6">
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
          Accept assignments, log physical work notes, and submit photo proof of repair.
        </p>
      </div>

      <Alert variant="warning" className="mb-6">
        <strong>Important Rule:</strong> Submitting repair evidence moves the issue to <code>REPAIR_REPORTED</code>. An independent reviewer must inspect your evidence before it is marked resolved. Workers cannot self-approve.
      </Alert>

      {/* Task card */}
      <Card className="p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100 mb-6">
          <div>
            <span className="text-xs font-mono font-bold text-civic-700 bg-civic-50 px-2.5 py-1 rounded border border-civic-200">
              Task #{activeTask} · Issue #FP-2026-00412
            </span>
            <h2 className="text-xl font-bold text-slate-900 mt-2">
              Pothole Repair & Surface Restoration
            </h2>
            <p className="text-xs text-slate-500 flex items-center mt-1">
              <MapPin className="w-3.5 h-3.5 mr-1 text-slate-400" />
              Gowdanahalli — Ward 2, Near Primary School
            </p>
          </div>
          <Badge status="IN_PROGRESS">Work in Progress</Badge>
        </div>

        {/* Task Details */}
        <div className="space-y-6">
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
            <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              Assigned Instructions
            </h3>
            <p className="text-sm text-slate-700 leading-relaxed">
              Clear loose debris, fill base with gravel aggregate, apply asphalt cold-mix compaction, and photograph the finished level surface.
            </p>
          </div>

          {/* Proof Upload Area */}
          <div>
            <h3 className="text-sm font-bold text-slate-900 mb-2">
              Upload Repair Evidence (After Photos)
            </h3>
            <div className="border-2 border-dashed border-slate-300 rounded-xl p-6 text-center bg-slate-50/50 hover:bg-slate-50 transition-colors">
              <Camera className="w-8 h-8 text-slate-400 mx-auto mb-2" />
              <p className="text-sm font-semibold text-slate-800">
                Capture or upload completed repair photo
              </p>
              <p className="text-xs text-slate-500 mt-0.5">
                Take a photo from a similar angle as the original citizen report.
              </p>
              <div className="mt-3">
                <Button variant="outline" size="sm" leftIcon={<Upload className="w-4 h-4" />}>
                  Choose Photo File
                </Button>
              </div>
            </div>
          </div>

          <Textarea
            label="Work Summary & Materials Used"
            placeholder="e.g. 50kg cold-mix asphalt applied and roller compacted. Road cleared for two-way traffic."
            value={workNotes}
            onChange={(e) => setWorkNotes(e.target.value)}
            required
          />

          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-slate-100">
            <Button variant="ghost" size="sm">
              Mark Blocked / Request Materials
            </Button>
            <Button
              variant="primary"
              size="md"
              leftIcon={<CheckCircle2 className="w-5 h-5" />}
              onClick={() => alert("Proof submission wired to backend in Phase 4.")}
            >
              Submit for Resolution Review
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
