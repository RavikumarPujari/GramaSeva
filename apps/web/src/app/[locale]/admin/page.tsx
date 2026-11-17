"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useTranslations, useLocale } from "next-intl";
import {
  Settings,
  Map,
  Building2,
  Users,
  Shield,
  Plus,
  GitFork,
  Check,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";

export default function AdminPage() {
  const locale = useLocale();

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:py-10 w-full">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 rounded text-xs font-semibold bg-purple-100 text-purple-800 border border-purple-200">
              Platform & Locality Administration
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Locality Hierarchy & Ward Configuration
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Configure Gram Panchayats, villages, wards, departments, and scoped staff roles.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            Import Official GeoJSON
          </Button>
          <Button variant="primary" size="sm" leftIcon={<Plus className="w-4 h-4" />}>
            Add Locality Unit
          </Button>
        </div>
      </div>

      <Alert variant="info" className="mb-6">
        <strong>First-Class Village Wards:</strong> Wards are structured administrative units in the <code>locality_units</code> table, not freeform text labels. Never hard-code ward counts or boundaries into application logic.
      </Alert>

      {/* Grid of Admin Sections */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card className="p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2.5 rounded-lg bg-civic-50 text-civic-700 border border-civic-200">
              <Map className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-base">Pilot Hierarchy</h3>
              <p className="text-xs text-slate-500">Karnataka &gt; Mandya &gt; Pandavapura</p>
            </div>
          </div>
          <ul className="text-xs text-slate-600 space-y-1.5 border-t border-slate-100 pt-3">
            <li className="flex justify-between">
              <span>Gram Panchayats:</span>
              <strong>1 Configured</strong>
            </li>
            <li className="flex justify-between">
              <span>Villages:</span>
              <strong>3 Units</strong>
            </li>
            <li className="flex justify-between">
              <span>Configured Wards:</span>
              <strong>7 Units</strong>
            </li>
          </ul>
        </Card>

        <Card className="p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2.5 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-base">Departments</h3>
              <p className="text-xs text-slate-500">Category routing & teams</p>
            </div>
          </div>
          <ul className="text-xs text-slate-600 space-y-1.5 border-t border-slate-100 pt-3">
            <li className="flex justify-between">
              <span>Roads & Engineering:</span>
              <Badge variant="success" size="sm">Active</Badge>
            </li>
            <li className="flex justify-between">
              <span>Water Supply & Sanitation:</span>
              <Badge variant="success" size="sm">Active</Badge>
            </li>
            <li className="flex justify-between">
              <span>Solid Waste Management:</span>
              <Badge variant="success" size="sm">Active</Badge>
            </li>
          </ul>
        </Card>

        <Card className="p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2.5 rounded-lg bg-amber-50 text-amber-700 border border-amber-200">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-base">Staff & Scopes</h3>
              <p className="text-xs text-slate-500">RBAC with jurisdiction</p>
            </div>
          </div>
          <ul className="text-xs text-slate-600 space-y-1.5 border-t border-slate-100 pt-3">
            <li className="flex justify-between">
              <span>Authority Reviewers:</span>
              <strong>2 Scoped</strong>
            </li>
            <li className="flex justify-between">
              <span>Field Workers:</span>
              <strong>4 Scoped</strong>
            </li>
            <li className="flex justify-between">
              <span>Admins:</span>
              <strong>1 Scoped</strong>
            </li>
          </ul>
        </Card>
      </div>

      {/* Locality Hierarchy Tree Card */}
      <Card className="p-6">
        <h3 className="text-lg font-bold text-slate-900 mb-4">
          Configured Locality Units (Demo Pilot Set)
        </h3>
        <div className="space-y-3 font-mono text-xs">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <p className="font-bold text-slate-900">
              [GP] Gowdanahalli Gram Panchayat (Official Code: GP-KA-571434)
            </p>
            <div className="pl-6 pt-2 space-y-2 border-l-2 border-slate-300 ml-2 mt-2 font-sans">
              <div>
                <p className="font-semibold text-slate-800">├── Village: Gowdanahalli</p>
                <div className="pl-6 pt-1 space-y-1 text-slate-600 text-xs font-mono">
                  <p>├── Ward 1 — Old Post Office Area</p>
                  <p>├── Ward 2 — Primary School Road</p>
                  <p>└── Ward 3 — Temple Street</p>
                </div>
              </div>

              <div>
                <p className="font-semibold text-slate-800">├── Village: Malleshwarapuram</p>
                <div className="pl-6 pt-1 space-y-1 text-slate-600 text-xs font-mono">
                  <p>├── Ward 1 — Lakeview Road</p>
                  <p>└── Ward 2 — Commercial Cross</p>
                </div>
              </div>

              <div>
                <p className="font-semibold text-slate-800">└── Village: Ramanagara</p>
                <div className="pl-6 pt-1 space-y-1 text-slate-600 text-xs font-mono">
                  <p>├── Ward 1 — Main Bazaar</p>
                  <p>└── Ward 2 — Hospital Road</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
