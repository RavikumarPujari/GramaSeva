"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useTranslations, useLocale } from "next-intl";
import {
  Camera,
  MapPin,
  CheckCircle2,
  AlertCircle,
  FileText,
  Sparkles,
  ArrowRight,
  ArrowLeft,
  Upload,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Input, Textarea } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";

export default function ReportPage() {
  const locale = useLocale();
  const tNav = useTranslations("navigation");
  const tCommon = useTranslations("common");
  const tCat = useTranslations("categories");

  const [step, setStep] = useState<number>(1);
  const [category, setCategory] = useState<string>("road_damage");
  const [description, setDescription] = useState<string>("");
  const [village, setVillage] = useState<string>("village_a");
  const [ward, setWard] = useState<string>("unknown");
  const [isUnknownWard, setIsUnknownWard] = useState<boolean>(true);

  const categoryOptions = [
    { value: "road_damage", label: tCat("road_damage") },
    { value: "water_leak", label: tCat("water_leak") },
    { value: "garbage", label: tCat("garbage") },
    { value: "drainage", label: tCat("drainage") },
    { value: "streetlight", label: tCat("streetlight") },
    { value: "public_facility", label: tCat("public_facility") },
    { value: "other", label: tCat("other") },
  ];

  const villageOptions = [
    { value: "village_a", label: "Gowdanahalli (Village A)" },
    { value: "village_b", label: "Malleshwarapuram (Village B)" },
    { value: "village_c", label: "Ramanagara (Village C)" },
  ];

  const wardOptions = [
    { value: "unknown", label: "I don't know my ward / Not configured" },
    { value: "ward_1", label: "Ward 1 — Old Post Office Area" },
    { value: "ward_2", label: "Ward 2 — Primary School Road" },
    { value: "ward_3", label: "Ward 3 — Market Road" },
  ];

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 sm:py-12 w-full">
      {/* Header and Step Indicator */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <Link
            href={`/${locale}`}
            className="text-sm font-medium text-slate-500 hover:text-slate-800 inline-flex items-center"
          >
            <ArrowLeft className="w-4 h-4 mr-1" /> {tNav("home")}
          </Link>
          <span className="text-slate-300">/</span>
          <span className="text-sm font-medium text-slate-800">{tNav("report")}</span>
        </div>

        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Report a Public Infrastructure Issue
        </h1>
        <p className="text-sm sm:text-base text-slate-600 mt-1">
          Provide photo evidence and location. You can submit even if you do not know your ward.
        </p>

        {/* Step indicator */}
        <div className="grid grid-cols-4 gap-2 mt-6">
          {[
            { num: 1, title: "1. Problem" },
            { num: 2, title: "2. Evidence" },
            { num: 3, title: "3. Location" },
            { num: 4, title: "4. Review" },
          ].map((s) => (
            <div
              key={s.num}
              className={`pb-2 border-b-2 font-medium text-xs sm:text-sm transition-all ${
                step === s.num
                  ? "border-civic-600 text-civic-700 font-bold"
                  : step > s.num
                  ? "border-emerald-500 text-emerald-700"
                  : "border-slate-200 text-slate-400"
              }`}
            >
              {s.title}
            </div>
          ))}
        </div>
      </div>

      {/* Guided Form Container */}
      <Card className="shadow-sm">
        {step === 1 && (
          <div className="p-6 space-y-6">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Step 1: Category & Description</h2>
              <p className="text-sm text-slate-500">
                Choose the category that best matches the issue.
              </p>
            </div>

            <Select
              label="Infrastructure Category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              options={categoryOptions}
              required
            />

            <Textarea
              label="Issue Description (Optional)"
              placeholder="e.g. Large pothole near the water tank, difficult for two-wheelers at night."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              helperText="Brief details help the Panchayat team triage faster. Text is optional if photos are clear."
            />

            <div className="flex justify-end pt-4 border-t border-slate-100">
              <Button
                variant="primary"
                onClick={() => setStep(2)}
                rightIcon={<ArrowRight className="w-4 h-4" />}
              >
                Continue to Evidence
              </Button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="p-6 space-y-6">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Step 2: Photographic Evidence</h2>
              <p className="text-sm text-slate-500">
                Upload clear photos of the issue. Real evidence is required before review.
              </p>
            </div>

            <div className="border-2 border-dashed border-slate-300 rounded-xl p-8 text-center bg-slate-50/50 hover:bg-slate-50 transition-colors">
              <div className="w-12 h-12 rounded-full bg-civic-100 text-civic-700 flex items-center justify-center mx-auto mb-3">
                <Camera className="w-6 h-6" />
              </div>
              <p className="text-sm font-semibold text-slate-800">
                Take photo or browse files
              </p>
              <p className="text-xs text-slate-500 mt-1">
                PNG, JPG, or WEBP up to 10MB. Stored in private quarantine before verification.
              </p>
              <div className="mt-4">
                <Button variant="outline" size="sm" leftIcon={<Upload className="w-4 h-4" />}>
                  Select Photo
                </Button>
              </div>
            </div>

            <Alert variant="info" title="Privacy Note">
              Original full-resolution photos are kept private in secure storage. Any public views strip personal identifiers and metadata.
            </Alert>

            <div className="flex justify-between pt-4 border-t border-slate-100">
              <Button variant="ghost" onClick={() => setStep(1)} leftIcon={<ArrowLeft className="w-4 h-4" />}>
                Back
              </Button>
              <Button
                variant="primary"
                onClick={() => setStep(3)}
                rightIcon={<ArrowRight className="w-4 h-4" />}
              >
                Continue to Location
              </Button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="p-6 space-y-6">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Step 3: Location Details</h2>
              <p className="text-sm text-slate-500">
                Specify your Gram Panchayat, village, and ward. Ward can be left unknown.
              </p>
            </div>

            <Select
              label="Village / Settlement"
              value={village}
              onChange={(e) => setVillage(e.target.value)}
              options={villageOptions}
              required
            />

            <div>
              <Select
                label="Village Ward"
                value={ward}
                onChange={(e) => {
                  setWard(e.target.value);
                  setIsUnknownWard(e.target.value === "unknown");
                }}
                options={wardOptions}
              />
              <p className="text-xs text-slate-500 mt-1.5">
                If unsure, select &ldquo;I don&apos;t know my ward&rdquo;. Panchayat staff will verify the ward during review.
              </p>
            </div>

            <div className="p-4 rounded-lg bg-slate-100 border border-slate-200 text-center">
              <MapPin className="w-6 h-6 text-civic-600 mx-auto mb-1" />
              <p className="text-sm font-medium text-slate-800">Map Pin Placement</p>
              <p className="text-xs text-slate-500 mt-0.5">
                Manual pin placement and optional one-time GPS available.
              </p>
            </div>

            <div className="flex justify-between pt-4 border-t border-slate-100">
              <Button variant="ghost" onClick={() => setStep(2)} leftIcon={<ArrowLeft className="w-4 h-4" />}>
                Back
              </Button>
              <Button
                variant="primary"
                onClick={() => setStep(4)}
                rightIcon={<ArrowRight className="w-4 h-4" />}
              >
                Review & Confirm
              </Button>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="p-6 space-y-6">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Step 4: Review Your Report</h2>
              <p className="text-sm text-slate-500">
                Review your details before final submission. An audit tracking ID will be generated.
              </p>
            </div>

            <div className="bg-slate-50 rounded-xl p-4 space-y-3 border border-slate-200">
              <div className="flex justify-between items-center text-sm pb-2 border-b border-slate-200">
                <span className="text-slate-500">Category:</span>
                <span className="font-semibold text-slate-900">
                  {categoryOptions.find((c) => c.value === category)?.label}
                </span>
              </div>

              <div className="flex justify-between items-center text-sm pb-2 border-b border-slate-200">
                <span className="text-slate-500">Village:</span>
                <span className="font-semibold text-slate-900">
                  {villageOptions.find((v) => v.value === village)?.label}
                </span>
              </div>

              <div className="flex justify-between items-center text-sm pb-2 border-b border-slate-200">
                <span className="text-slate-500">Ward:</span>
                <Badge variant={isUnknownWard ? "warning" : "info"} size="sm">
                  {isUnknownWard ? "Ward Unknown (Will be triaged)" : ward}
                </Badge>
              </div>

              {description && (
                <div className="text-sm pt-1">
                  <span className="text-slate-500 block mb-1">Notes:</span>
                  <p className="text-slate-700 bg-white p-2.5 rounded border border-slate-200 text-xs">
                    {description}
                  </p>
                </div>
              )}
            </div>

            <Alert variant="warning" title="Advisory Notice">
              Submissions are verified by local officers before physical work begins. AI assistance is advisory only.
            </Alert>

            <div className="flex justify-between pt-4 border-t border-slate-100">
              <Button variant="ghost" onClick={() => setStep(3)} leftIcon={<ArrowLeft className="w-4 h-4" />}>
                Back
              </Button>
              <Button
                variant="success"
                onClick={() => alert("Report submission API will be wired in Phase 3.")}
                leftIcon={<CheckCircle2 className="w-5 h-5" />}
              >
                Confirm & Submit Report
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
