"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useLocale } from "next-intl";
import {
  Camera,
  Upload,
  MapPin,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Sparkles,
  ArrowRight,
  ArrowLeft,
  Copy,
  Check,
  Loader2,
  X,
  Mic,
  MicOff,
  RotateCcw,
  CheckCircle,
  FileText,
  User,
  Phone,
  Layers,
  Search,
  ExternalLink,
  ShieldCheck,
  Clock,
  Printer,
  Award,
  Edit,
  Globe,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input, Textarea } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Badge } from "@/components/ui/Badge";
import { apiClient } from "@/lib/api-client";
import {
  LocationMapPicker,
  LocationPickerChangeData,
} from "@/components/ui/LocationMapPicker";

const CATEGORY_OPTIONS = [
  { value: "road_damage", label: "Road Damage & Potholes (ರಸ್ತೆ ಹಾನಿ ಮತ್ತು ಗುಂಡಿಗಳು)" },
  { value: "garbage", label: "Garbage and Waste (ಕಸದ ರಾಶಿ ಮತ್ತು ನೈರ್ಮಲ್ಯ)" },
  { value: "waterlogging", label: "Waterlogging (ನೀರು ನಿಲ್ಲುವುದು)" },
  { value: "drainage", label: "Drainage and Sewage Blockage (ಚರಂಡಿ ಮತ್ತು ಒಳಚರಂಡಿ)" },
  { value: "streetlight", label: "Streetlights & Electrical (ಬೀದಿ ದೀಪ ಸಮಸ್ಯೆ)" },
  { value: "water_leak", label: "Drinking Water & Pipe Leak (ಕುಡಿಯುವ ನೀರು ಮತ್ತು ಸೋರಿಕೆ)" },
  { value: "sanitation", label: "Public Sanitation (ಸಾರ್ವಜನಿಕ ನೈರ್ಮಲ್ಯ)" },
  { value: "public_facility", label: "Public Infrastructure & Buildings (ಸಾರ್ವಜನಿಕ ಕಟ್ಟಡಗಳು)" },
  { value: "other", label: "Other Civic Problem (ಇತರ ನಾಗರಿಕ ಸಮಸ್ಯೆ)" },
];

const SEVERITY_LEVELS = [
  { id: "LOW", label: "Low", color: "bg-blue-100 text-blue-800 border-blue-200" },
  { id: "MEDIUM", label: "Medium", color: "bg-amber-100 text-amber-800 border-amber-200" },
  { id: "HIGH", label: "High", color: "bg-orange-100 text-orange-800 border-orange-200" },
  { id: "CRITICAL", label: "Critical", color: "bg-rose-100 text-rose-800 border-rose-200" },
];

export interface DuplicateSuggestionItem {
  issue_id: string;
  reference_number: string;
  category: string;
  status: string;
  distance_meters: number;
  summary?: string | null;
  ward_name?: string | null;
  composite_score: number;
  explanation: string;
  target_media_id?: string | null;
  created_at: string;
}

export default function ReportProblemPage() {
  const locale = useLocale();

  // Workflow Stages (Exact Six Steps):
  // 1: Photo & Citizen Details
  // 2: Location & Google Maps
  // 3: Details & Language
  // 4: AI Analysis
  // 5: Match (Duplicates)
  // 6: Confirm
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [trackingId, setTrackingId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState(false);

  // PHASE 2: Citizen Details & Authentication state
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [accountId, setAccountId] = useState<string | null>(null);
  const [citizenName, setCitizenName] = useState<string>("");
  const [citizenPhone, setCitizenPhone] = useState<string>("");

  // PHASE 3.1: Image Upload State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);

  // PHASE 3.2 - 3.4: Location State
  const [locationData, setLocationData] = useState<LocationPickerChangeData | null>(null);
  const [isLocationConfirmed, setIsLocationConfirmed] = useState(false);

  // PHASE 4: Language Selection
  const [selectedLanguage, setSelectedLanguage] = useState<"kn" | "en" | "hi">(
    locale === "kn" ? "kn" : locale === "hi" ? "hi" : "en"
  );

  // STEP 3: Details State
  const [issueTitle, setIssueTitle] = useState<string>("");
  const [activeCategory, setActiveCategory] = useState<string>("road_damage");
  const [activeDescription, setActiveDescription] = useState<string>("");
  const [additionalLandmark, setAdditionalLandmark] = useState<string>("");

  // Voice Recording State
  const [isRecording, setIsRecording] = useState(false);
  const recognitionRef = useRef<any>(null);

  // STEP 4: AI Analysis State (Gemini Multimodal Vision + Specialist Models)
  const [isAiAnalyzing, setIsAiAnalyzing] = useState(false);
  const [aiPredictedCategory, setAiPredictedCategory] = useState<string>("road_damage");
  const [aiConfidenceScore, setAiConfidenceScore] = useState<number | null>(null);
  const [aiDefectLabel, setAiDefectLabel] = useState<string | null>(null);
  const [aiOcrText, setAiOcrText] = useState<string | null>(null);
  const [aiSeverity, setAiSeverity] = useState<string>("MEDIUM");
  const [hasAiRun, setHasAiRun] = useState(false);
  const [aiAnalysisError, setAiAnalysisError] = useState<string | null>(null);

  // STEP 5: Match State (Duplicate Suggestions)
  const [isCheckingDuplicates, setIsCheckingDuplicates] = useState(false);
  const [duplicateMatches, setDuplicateMatches] = useState<DuplicateSuggestionItem[]>([]);
  const [duplicateChoice, setDuplicateChoice] = useState<"separate" | "same">("separate");
  const [selectedDuplicateRef, setSelectedDuplicateRef] = useState<string | null>(null);

  // Indian Mobile Number Validation Regex (10 digits starting with 6, 7, 8, or 9)
  const validateIndianPhone = (phone: string): boolean => {
    const clean = phone.replace(/^(\+91|91)/, "").replace(/[\s-]/g, "").trim();
    return /^[6-9]\d{9}$/.test(clean);
  };

  // Load authenticated citizen profile on mount (PHASE 2)
  useEffect(() => {
    async function loadProfile() {
      const token =
        typeof window !== "undefined"
          ? localStorage.getItem("gramaseva_token") || localStorage.getItem("access_token")
          : null;
      if (!token) {
        setIsAuthenticated(false);
        return;
      }

      try {
        const res = await apiClient.get<any>("/citizen/profile");
        if (res && (res.id || res.full_name || res.email)) {
          setIsAuthenticated(true);
          if (res.id) setAccountId(res.id);
          if (res.full_name) setCitizenName(res.full_name);
          else if (res.name) setCitizenName(res.name);
          if (res.phone_number) setCitizenPhone(res.phone_number);
          else if (res.phone) setCitizenPhone(res.phone);
        } else {
          setIsAuthenticated(false);
        }
      } catch {
        setIsAuthenticated(false);
      }
    }
    loadProfile();
  }, []);

  // Web Speech Recognition for voice description
  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        const rec = new SpeechRecognition();
        rec.continuous = true;
        rec.interimResults = true;
        rec.lang =
          selectedLanguage === "kn"
            ? "kn-IN"
            : selectedLanguage === "hi"
            ? "hi-IN"
            : "en-IN";

        rec.onresult = (event: any) => {
          let transcript = "";
          for (let i = event.resultIndex; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
          }
          if (transcript.trim()) {
            setActiveDescription((prev) => {
              const base = prev.trim();
              return base ? `${base} ${transcript.trim()}` : transcript.trim();
            });
          }
        };

        recognitionRef.current = rec;
      }
    }
  }, [selectedLanguage]);

  // Camera Controls (PHASE 3.1)
  const startCamera = async () => {
    try {
      setIsCameraOpen(true);
      setErrorMessage(null);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      setCameraStream(stream);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
    } catch {
      setIsCameraOpen(false);
      cameraInputRef.current?.click();
    }
  };

  const stopCamera = () => {
    if (cameraStream) {
      cameraStream.getTracks().forEach((track) => track.stop());
      setCameraStream(null);
    }
    setIsCameraOpen(false);
  };

  const capturePhoto = () => {
    if (!videoRef.current) return;
    const canvas = document.createElement("canvas");
    canvas.width = videoRef.current.videoWidth || 640;
    canvas.height = videoRef.current.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
      if (blob) {
        const file = new File([blob], `evidence_${Date.now()}.jpg`, { type: "image/jpeg" });
        setSelectedFile(file);
        setPreviewUrl(URL.createObjectURL(file));
        setErrorMessage(null);
        stopCamera();
      }
    }, "image/jpeg", 0.9);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setErrorMessage("Please select a valid photograph (JPEG, PNG, WebP).");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setErrorMessage("Image file exceeds the 10 MB limit.");
      return;
    }

    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setErrorMessage(null);
  };

  // Gemini Vision AI Multimodal Analysis (PHASE 4)
  const triggerGeminiAnalysis = async (file: File, langOverride?: "kn" | "en" | "hi") => {
    setIsAiAnalyzing(true);
    setHasAiRun(true);
    setAiAnalysisError(null);
    const lang = langOverride || selectedLanguage;
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("locale", lang);
      if (locationData?.address?.village && !locationData.address.village.includes("not identified")) {
        formData.append("village_name", locationData.address.village);
      }

      const geminiRes = await apiClient.postForm<any>("/ai/gemini/analyze-problem", formData);
      if (geminiRes) {
        if (geminiRes.suggested_category) {
          setAiPredictedCategory(geminiRes.suggested_category);
          setActiveCategory(geminiRes.suggested_category);
        }
        if (geminiRes.confidence) setAiConfidenceScore(geminiRes.confidence);
        if (geminiRes.visual_summary) setAiDefectLabel(geminiRes.visual_summary);
        if (geminiRes.title) setIssueTitle(geminiRes.title);
        if (geminiRes.description) setActiveDescription(geminiRes.description);
        if (geminiRes.ocr_text) {
          setAiOcrText(Array.isArray(geminiRes.ocr_text) ? geminiRes.ocr_text.join(", ") : geminiRes.ocr_text);
        }
        if (geminiRes.severity) setAiSeverity(geminiRes.severity.toUpperCase());
      }
    } catch (err: any) {
      console.warn("AI analysis error:", err);
      setAiAnalysisError(
        err?.message || "AI Vision model temporarily unavailable. You can enter complaint details manually."
      );
    } finally {
      setIsAiAnalyzing(false);
    }
  };

  // Step 5: Duplicate Complaint Matching (PHASE 5)
  const runDuplicateMatching = async () => {
    setIsCheckingDuplicates(true);
    try {
      const payload = {
        category: activeCategory,
        latitude: locationData?.lat,
        longitude: locationData?.lon,
        threshold_meters: 1000,
        similarity_threshold: 0.5,
      };

      const res = await apiClient.post<DuplicateSuggestionItem[]>("/reports/check-duplicates", payload);
      if (Array.isArray(res)) {
        setDuplicateMatches(res);
      } else {
        setDuplicateMatches([]);
      }
    } catch (err) {
      console.warn("Duplicate matching note:", err);
      setDuplicateMatches([]);
    } finally {
      setIsCheckingDuplicates(false);
    }
  };

  // Final Atomic Submission (PHASE 7)
  const handleSubmitComplaint = async () => {
    if (!selectedFile) {
      setErrorMessage("Please capture or upload an evidence photograph.");
      setCurrentStep(1);
      return;
    }

    if (!citizenName.trim()) {
      setErrorMessage("Please enter your name.");
      setCurrentStep(1);
      return;
    }

    if (!isAuthenticated && !validateIndianPhone(citizenPhone)) {
      setErrorMessage("Please enter a valid 10-digit Indian mobile number (e.g. 9876543210).");
      setCurrentStep(1);
      return;
    }

    if (!locationData || !locationData.lat || !locationData.lon) {
      setErrorMessage("Please detect and confirm the incident location.");
      setCurrentStep(2);
      return;
    }

    if (!isLocationConfirmed) {
      setErrorMessage("Please confirm the detected location before submitting.");
      setCurrentStep(2);
      return;
    }

    if (!issueTitle.trim()) {
      setErrorMessage("Please enter a complaint title.");
      setCurrentStep(3);
      return;
    }

    if (!activeDescription.trim()) {
      setErrorMessage("Please enter a short description of the problem.");
      setCurrentStep(3);
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const submitForm = new FormData();
      submitForm.append("file", selectedFile);
      submitForm.append("category", activeCategory);
      submitForm.append("title", issueTitle.trim());
      submitForm.append("description", activeDescription.trim());
      if (additionalLandmark.trim()) {
        submitForm.append("landmark", additionalLandmark.trim());
      }
      submitForm.append("citizen_name", citizenName.trim());
      if (citizenPhone.trim()) {
        submitForm.append("citizen_phone", citizenPhone.trim());
      }
      submitForm.append("is_guest", (!isAuthenticated).toString());

      // Original GPS coordinates
      const origLat = locationData.originalGpsLat ?? locationData.lat;
      const origLon = locationData.originalGpsLon ?? locationData.lon;
      submitForm.append("latitude", origLat.toString());
      submitForm.append("longitude", origLon.toString());
      if (locationData.originalAccuracy) {
        submitForm.append("gps_accuracy", locationData.originalAccuracy.toString());
      }
      submitForm.append("location_method", locationData.method);

      // Citizen-Confirmed Coordinates
      submitForm.append("confirmed_latitude", locationData.lat.toString());
      submitForm.append("confirmed_longitude", locationData.lon.toString());
      submitForm.append("confirmation_method", "CITIZEN_CONFIRMED");
      submitForm.append("location_confirmation_status", "CITIZEN_CONFIRMED");

      // Address components
      const addr = locationData.address;
      submitForm.append("confirmed_address", addr.formattedAddress);
      const effectiveVill = addr.village && !addr.village.includes("Not available") ? addr.village : (addr.gramPanchayat && !addr.gramPanchayat.includes("Not available") ? addr.gramPanchayat : "");
      if (effectiveVill) {
        submitForm.append("village_name", effectiveVill);
        submitForm.append("confirmed_village", effectiveVill);
        submitForm.append("detected_village", effectiveVill);
      }
      if (addr.taluk && !addr.taluk.includes("Not available")) {
        submitForm.append("taluk_name", addr.taluk);
        submitForm.append("detected_taluk", addr.taluk);
      }
      if (addr.gramPanchayat && !addr.gramPanchayat.includes("Not available")) {
        submitForm.append("detected_gram_panchayat", addr.gramPanchayat);
      }
      if (addr.district && !addr.district.includes("Not available")) {
        submitForm.append("detected_district", addr.district);
      }
      submitForm.append("detected_state", addr.state || "Karnataka");
      submitForm.append("detected_country", addr.country || "India");
      if (addr.postalCode && !addr.postalCode.includes("Not available")) {
        submitForm.append("detected_postal_code", addr.postalCode);
      }
      if (addr.placeId) submitForm.append("google_place_id", addr.placeId);
      submitForm.append("geocoding_status", addr.geocodingStatus || "OK");

      // AI Metadata & Language
      submitForm.append("selected_language", selectedLanguage);
      if (aiPredictedCategory) submitForm.append("ai_category_suggestion", aiPredictedCategory);
      if (aiConfidenceScore) submitForm.append("ai_confidence", aiConfidenceScore.toString());
      if (aiSeverity) submitForm.append("severity", aiSeverity);
      if (aiOcrText) submitForm.append("ocr_extracted_text", aiOcrText);

      // Duplicate Handling Note
      if (duplicateChoice === "same" && selectedDuplicateRef) {
        submitForm.append("linked_duplicate_reference", selectedDuplicateRef);
      }

      // Submit atomically to backend API
      const res = await apiClient.postForm<any>("/reports/submit", submitForm);
      if (res && res.tracking_id) {
        setTrackingId(res.tracking_id);
      } else {
        throw new Error("Complaint submission response did not contain a valid tracking ID.");
      }
    } catch (err: any) {
      setErrorMessage(
        err.message || "Failed to submit complaint. Please check your network connection and try again."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const copyTrackingId = () => {
    if (trackingId) {
      navigator.clipboard.writeText(trackingId);
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
    }
  };

  const stepsList = [
    { number: 1, title: "Citizen & Photo" },
    { number: 2, title: "Location" },
    { number: 3, title: "Details & Language" },
    { number: 4, title: "AI Analysis" },
    { number: 5, title: "Match" },
    { number: 6, title: "Confirm" },
  ];

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header Banner */}
        <div className="text-center space-y-2">
          <Badge className="bg-teal-100 text-teal-800 border-teal-300 font-semibold px-3 py-1">
            GramaSeva Citizen Grievance Portal
          </Badge>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-[#062B46] tracking-tight">
            Report a Civic Problem
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 max-w-xl mx-auto">
            Report civic defects in your Gram Panchayat. Follow the verified 6-step reporting wizard for live Google Maps GPS location, AI analysis, and real-time tracking.
          </p>
        </div>

        {/* Six-Step Workflow Progress Stepper */}
        {!trackingId && (
          <div className="rounded-2xl border border-slate-200 bg-white p-3 sm:p-4 shadow-xs">
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 text-center text-xs font-bold">
              {stepsList.map((step) => {
                const isCurrent = currentStep === step.number;
                const isCompleted = currentStep > step.number;
                return (
                  <button
                    key={step.number}
                    type="button"
                    onClick={() => {
                      if (step.number < currentStep) {
                        setCurrentStep(step.number);
                      }
                    }}
                    disabled={step.number > currentStep}
                    className={`flex items-center justify-center gap-1.5 py-2 px-2.5 rounded-xl transition-all ${
                      isCurrent
                        ? "bg-[#087F78] text-white shadow-xs"
                        : isCompleted
                        ? "bg-emerald-50 text-emerald-800 border border-emerald-200 cursor-pointer hover:bg-emerald-100"
                        : "bg-slate-100 text-slate-400 cursor-not-allowed"
                    }`}
                  >
                    <span>{step.number}. {step.title}</span>
                    {isCompleted && <Check className="h-3.5 w-3.5 shrink-0" />}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Global Error Banner */}
        {errorMessage && (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-xs sm:text-sm text-rose-900 flex items-start gap-3 shadow-xs">
            <AlertCircle className="h-5 w-5 text-rose-600 shrink-0 mt-0.5" />
            <div className="flex-1 font-medium">{errorMessage}</div>
            <button
              type="button"
              onClick={() => setErrorMessage(null)}
              className="text-rose-500 hover:text-rose-700 cursor-pointer"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* =========================================================================
            STEP 1: CITIZEN DETAILS & EVIDENCE PHOTO (PHASE 2 & PHASE 3.1)
           ========================================================================= */}
        {!trackingId && currentStep === 1 && (
          <Card className="p-6 sm:p-8 space-y-6 rounded-3xl border-slate-200 shadow-sm bg-white">
            <div className="border-b border-slate-100 pb-4">
              <h2 className="text-lg font-bold text-[#062B46]">
                Step 1: Citizen Contact & Problem Evidence
              </h2>
              <p className="text-xs text-slate-500">
                Provide your contact details so the Village PDO can communicate updates, and capture or upload an evidence photo.
              </p>
            </div>

            {/* PHASE 2: Citizen Details Section */}
            <div className="rounded-2xl border border-teal-200/80 bg-gradient-to-r from-teal-50/50 to-blue-50/40 p-4 sm:p-5 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-[#062B46] flex items-center gap-1.5">
                  <User className="h-4 w-4 text-[#087F78]" />
                  <span>Citizen Contact Details</span>
                </span>
                {isAuthenticated ? (
                  <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 text-[10px] font-bold">
                    Authenticated Citizen Account ✓
                  </Badge>
                ) : (
                  <Badge className="bg-amber-100 text-amber-800 border-amber-300 text-[10px] font-bold">
                    Guest Reporting (No Registration Required)
                  </Badge>
                )}
              </div>

              {isAuthenticated ? (
                /* Authenticated Confirmation Card */
                <div className="bg-white rounded-xl p-3.5 border border-teal-200/70 text-xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-slate-500">Citizen Name:</span>{" "}
                      <strong className="text-slate-900">{citizenName}</strong>
                    </div>
                    {accountId && (
                      <span className="text-[10px] font-mono text-slate-400">ID: {accountId.slice(0, 8)}...</span>
                    )}
                  </div>
                  <div>
                    <span className="text-slate-500">Mobile Number:</span>{" "}
                    <strong className="text-slate-900">{citizenPhone || "Verified"}</strong>
                  </div>
                  <p className="text-[11px] text-emerald-700 font-medium pt-1">
                    ✓ Your contact information is confirmed from your profile. No need to register again.
                  </p>
                </div>
              ) : (
                /* Guest Reporting Input Card */
                <div className="space-y-3 text-xs">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] font-bold text-slate-700 mb-1">
                        Full Name *
                      </label>
                      <Input
                        value={citizenName}
                        onChange={(e) => setCitizenName(e.target.value)}
                        placeholder="Enter your full name"
                        className="bg-white rounded-xl text-xs font-medium"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-bold text-slate-700 mb-1">
                        Mobile Number * (10-Digit Indian Mobile)
                      </label>
                      <Input
                        value={citizenPhone}
                        onChange={(e) => setCitizenPhone(e.target.value)}
                        placeholder="e.g. 9876543210"
                        className="bg-white rounded-xl text-xs font-medium"
                      />
                    </div>
                  </div>
                  <p className="text-[11px] text-slate-500">
                    Your contact details will be safely preserved with your complaint so the Village Panchayat can notify you upon resolution.
                  </p>
                </div>
              )}
            </div>

            {/* PHASE 3.1: Image Upload / Camera Box */}
            <div className="space-y-4">
              <span className="block text-xs font-bold uppercase tracking-wider text-[#062B46] flex items-center gap-1.5">
                <Camera className="h-4 w-4 text-[#087F78]" />
                <span>Problem Photograph Evidence</span>
              </span>

              {/* Hidden file and camera inputs */}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handleFileChange}
                className="hidden"
              />
              <input
                ref={cameraInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                onChange={handleFileChange}
                className="hidden"
              />

              {/* Live Web Camera View if Active */}
              {isCameraOpen && (
                <div className="rounded-2xl overflow-hidden border border-slate-300 bg-black relative max-h-96">
                  <video ref={videoRef} autoPlay playsInline className="w-full max-h-96 object-contain" />
                  <div className="absolute bottom-4 inset-x-0 flex items-center justify-center gap-3">
                    <Button
                      type="button"
                      variant="primary"
                      onClick={capturePhoto}
                      className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-6 py-2 rounded-xl text-xs flex items-center gap-2 cursor-pointer shadow-md"
                    >
                      <Camera className="h-4 w-4" />
                      <span>Take Photo</span>
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={stopCamera}
                      className="bg-white/90 text-slate-800 text-xs px-4 py-2 rounded-xl cursor-pointer"
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}

              {/* Upload Dropzone / Gallery & Camera Buttons */}
              {!previewUrl && !isCameraOpen ? (
                <div className="space-y-4">
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    className="border-2 border-dashed border-teal-300 hover:border-teal-500 rounded-2xl p-8 sm:p-10 text-center bg-teal-50/30 hover:bg-teal-50/60 transition-all cursor-pointer flex flex-col items-center justify-center gap-3"
                  >
                    <div className="h-14 w-14 rounded-full bg-teal-100 text-[#087F78] flex items-center justify-center shadow-xs">
                      <Upload className="h-7 w-7" />
                    </div>
                    <div>
                      <p className="font-bold text-[#062B46] text-sm">
                        Select Problem Photograph
                      </p>
                      <p className="text-xs text-slate-500 mt-1">
                        Supports JPEG, PNG, WebP up to 10 MB
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                    <Button
                      type="button"
                      variant="primary"
                      onClick={startCamera}
                      className="w-full sm:w-auto bg-[#087F78] hover:bg-[#06635e] text-white font-bold px-6 py-2.5 rounded-xl shadow-xs flex items-center justify-center gap-2 cursor-pointer"
                    >
                      <Camera className="h-4 w-4" />
                      <span>Open Camera</span>
                    </Button>

                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => fileInputRef.current?.click()}
                      className="w-full sm:w-auto border-slate-300 text-slate-700 font-semibold px-6 py-2.5 rounded-xl cursor-pointer flex items-center justify-center gap-2"
                    >
                      <Upload className="h-4 w-4 text-slate-500" />
                      <span>Upload from Gallery</span>
                    </Button>
                  </div>
                </div>
              ) : previewUrl && !isCameraOpen ? (
                /* Image Preview Box */
                <div className="space-y-3">
                  <div className="relative rounded-2xl overflow-hidden border border-slate-200 bg-slate-900 max-h-80 flex items-center justify-center">
                    <img
                      src={previewUrl}
                      alt="Complaint Preview"
                      className="w-full max-h-80 object-contain"
                    />
                  </div>

                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => fileInputRef.current?.click()}
                        className="text-xs text-slate-700"
                      >
                        <RotateCcw className="h-3.5 w-3.5 mr-1" />
                        Replace Image
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setSelectedFile(null);
                          setPreviewUrl(null);
                        }}
                        className="text-xs text-rose-600 hover:bg-rose-50"
                      >
                        <Trash2 className="h-3.5 w-3.5 mr-1" />
                        Remove
                      </Button>
                    </div>

                    <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 text-[10px] font-bold">
                      ✓ Image Ready ({selectedFile?.name})
                    </Badge>
                  </div>
                </div>
              ) : null}
            </div>

            {/* Navigation to Step 2 */}
            <div className="flex justify-end pt-4 border-t border-slate-100">
              <Button
                type="button"
                variant="primary"
                onClick={() => {
                  if (!citizenName.trim()) {
                    setErrorMessage("Please enter your name.");
                    return;
                  }
                  if (!isAuthenticated && !validateIndianPhone(citizenPhone)) {
                    setErrorMessage("Please enter a valid 10-digit Indian mobile number (e.g. 9876543210).");
                    return;
                  }
                  if (!selectedFile) {
                    setErrorMessage("Please select or capture a photograph of the civic defect.");
                    return;
                  }
                  setErrorMessage(null);
                  setCurrentStep(2);
                }}
                disabled={!selectedFile || !citizenName.trim() || (!isAuthenticated && !validateIndianPhone(citizenPhone))}
                className="bg-[#087F78] hover:bg-[#06635e] text-white font-bold px-6 text-xs transition-all cursor-pointer disabled:opacity-50"
              >
                <span>Continue to Location</span>
                <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
              </Button>
            </div>
          </Card>
        )}

        {/* =========================================================================
            STEP 2: LOCATION — EXISTING LIVE GOOGLE MAPS (PHASE 3.2 - 3.5)
           ========================================================================= */}
        {!trackingId && currentStep === 2 && (
          <Card className="p-6 sm:p-8 space-y-6 rounded-3xl border-slate-200 shadow-sm bg-white">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-4">
              <div>
                <h2 className="text-lg font-bold text-[#062B46]">
                  Step 2: Google Maps & Location Confirmation
                </h2>
                <p className="text-xs text-slate-500">
                  Detect your current GPS coordinates. Google Geocoding will retrieve the real address, village, taluk, and district.
                </p>
              </div>

              {previewUrl && (
                <div className="flex items-center gap-2 shrink-0">
                  <img
                    src={previewUrl}
                    alt="Thumbnail"
                    className="h-10 w-10 rounded-lg object-cover border border-slate-200"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setCurrentStep(1)}
                    className="text-xs text-slate-600"
                  >
                    Edit Photo
                  </Button>
                </div>
              )}
            </div>

            {/* Reusable Real Google Maps Picker Component (PRESERVED INTACT) */}
            <LocationMapPicker
              latitude={locationData?.lat ?? null}
              longitude={locationData?.lon ?? null}
              accuracyMeters={locationData?.accuracy ?? null}
              locationMethod={locationData?.method ?? "GPS_VERIFIED"}
              isConfirmed={isLocationConfirmed}
              onLocationChange={(data) => {
                setLocationData(data);
                setIsLocationConfirmed(data.isConfirmed);
                if (data.isConfirmed) setErrorMessage(null);
              }}
              onConfirmLocation={(conf) => setIsLocationConfirmed(conf)}
            />

            {/* PHASE 3.4: Location Confirmation Card */}
            {locationData && locationData.lat && (
              <div className="rounded-2xl border border-teal-200 bg-gradient-to-r from-teal-50/70 to-blue-50/50 p-4 sm:p-5 space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="space-y-1">
                    <p className="font-bold text-[#062B46] text-sm">
                      Your location has been detected. Please verify that this is the actual location of the problem.
                    </p>
                    <p className="text-xs text-slate-600">
                      Village: <strong>{locationData.address.village}</strong> • Taluk: <strong>{locationData.address.taluk}</strong> • PIN: <strong>{locationData.address.postalCode || "Not available"}</strong>
                    </p>
                    <p className="font-mono text-[11px] text-teal-800">
                      📍 {locationData.lat.toFixed(6)}°N, {locationData.lon.toFixed(6)}°E
                    </p>
                  </div>

                  <Button
                    type="button"
                    variant="primary"
                    onClick={() => {
                      setIsLocationConfirmed(true);
                      setErrorMessage(null);
                    }}
                    className={`shrink-0 font-bold px-5 py-2.5 rounded-xl text-xs flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                      isLocationConfirmed
                        ? "bg-emerald-600 text-white hover:bg-emerald-700"
                        : "bg-[#087F78] hover:bg-[#06635e] text-white"
                    }`}
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    <span>{isLocationConfirmed ? "Location Confirmed ✓" : "Confirm Location"}</span>
                  </Button>
                </div>
              </div>
            )}

            {/* PHASE 3.5: Visual Confirmation Indicators */}
            {selectedFile && isLocationConfirmed && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                <div className="rounded-xl p-3 border border-emerald-200 bg-emerald-50/80 flex items-center gap-2.5 text-xs text-emerald-900 font-bold">
                  <span className="text-base">📸</span>
                  <span>Problem Image — Uploaded successfully.</span>
                </div>

                <div className="rounded-xl p-3 border border-emerald-200 bg-emerald-50/80 flex items-center gap-2.5 text-xs text-emerald-900 font-bold">
                  <span className="text-base">📍</span>
                  <span>Problem Location — Detected and confirmed.</span>
                </div>
              </div>
            )}

            {/* Step Navigation Actions */}
            <div className="flex items-center justify-between pt-4 border-t border-slate-100">
              <Button
                type="button"
                variant="outline"
                onClick={() => setCurrentStep(1)}
                className="text-xs text-slate-700"
              >
                <ArrowLeft className="h-3.5 w-3.5 mr-1" />
                Back to Photo
              </Button>

              <Button
                type="button"
                variant="primary"
                onClick={() => {
                  if (!locationData || !locationData.lat) {
                    setErrorMessage("Please detect your location using 'Detect My Location' first.");
                    return;
                  }
                  if (!isLocationConfirmed) {
                    setErrorMessage("Please confirm the detected location by clicking 'Confirm Location'.");
                    return;
                  }
                  setErrorMessage(null);
                  setCurrentStep(3);
                }}
                disabled={!locationData || !locationData.lat || !isLocationConfirmed}
                className="bg-[#087F78] hover:bg-[#06635e] text-white font-bold px-6 text-xs transition-all disabled:opacity-50 cursor-pointer"
              >
                <span>Continue to Details & Language</span>
                <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
              </Button>
            </div>
          </Card>
        )}

        {/* =========================================================================
            STEP 3: DETAILS & LANGUAGE SELECTION (PHASE 4 PREP)
           ========================================================================= */}
        {!trackingId && currentStep === 3 && (
          <Card className="p-6 sm:p-8 space-y-6 rounded-3xl border-slate-200 shadow-sm bg-white">
            <div className="border-b border-slate-100 pb-4">
              <h2 className="text-lg font-bold text-[#062B46]">
                Step 3: Complaint Language & Problem Details
              </h2>
              <p className="text-xs text-slate-500">
                Choose your preferred language for the complaint description and provide title or notes.
              </p>
            </div>

            {/* PHASE 4: Language Selection */}
            <div className="rounded-2xl border border-teal-200 bg-teal-50/50 p-4 sm:p-5 space-y-2.5">
              <label className="block text-xs font-bold uppercase tracking-wider text-[#062B46] flex items-center gap-1.5">
                <Globe className="h-4 w-4 text-[#087F78]" />
                <span>Which language would you like to use for your complaint? *</span>
              </label>

              <div className="grid grid-cols-3 gap-3 pt-1">
                <button
                  type="button"
                  onClick={() => setSelectedLanguage("kn")}
                  className={`p-3 rounded-xl border text-center transition-all cursor-pointer ${
                    selectedLanguage === "kn"
                      ? "border-[#087F78] bg-white ring-2 ring-[#087F78] text-[#087F78] font-bold shadow-xs"
                      : "border-slate-200 bg-white/70 text-slate-700 hover:bg-white"
                  }`}
                >
                  <span className="block text-sm font-black">ಕನ್ನಡ</span>
                  <span className="block text-[10px] text-slate-500">Kannada</span>
                </button>

                <button
                  type="button"
                  onClick={() => setSelectedLanguage("en")}
                  className={`p-3 rounded-xl border text-center transition-all cursor-pointer ${
                    selectedLanguage === "en"
                      ? "border-[#087F78] bg-white ring-2 ring-[#087F78] text-[#087F78] font-bold shadow-xs"
                      : "border-slate-200 bg-white/70 text-slate-700 hover:bg-white"
                  }`}
                >
                  <span className="block text-sm font-black">English</span>
                  <span className="block text-[10px] text-slate-500">Standard English</span>
                </button>

                <button
                  type="button"
                  onClick={() => setSelectedLanguage("hi")}
                  className={`p-3 rounded-xl border text-center transition-all cursor-pointer ${
                    selectedLanguage === "hi"
                      ? "border-[#087F78] bg-white ring-2 ring-[#087F78] text-[#087F78] font-bold shadow-xs"
                      : "border-slate-200 bg-white/70 text-slate-700 hover:bg-white"
                  }`}
                >
                  <span className="block text-sm font-black">हिन्दी</span>
                  <span className="block text-[10px] text-slate-500">Hindi</span>
                </button>
              </div>
            </div>

            {/* Form Fields: Category, Title, Description, Voice */}
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                  Problem Category *
                </label>
                <Select
                  value={activeCategory}
                  onChange={(e) => setActiveCategory(e.target.value)}
                  options={CATEGORY_OPTIONS}
                  className="rounded-xl border-slate-200 text-xs font-semibold"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                  Complaint Title *
                </label>
                <Input
                  value={issueTitle}
                  onChange={(e) => setIssueTitle(e.target.value)}
                  placeholder="e.g. Broken water pipe leaking on main road"
                  className="rounded-xl text-xs font-medium"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">
                    Complaint Description *
                  </label>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      if (isRecording) {
                        recognitionRef.current?.stop();
                        setIsRecording(false);
                      } else {
                        recognitionRef.current?.start();
                        setIsRecording(true);
                      }
                    }}
                    className={`h-7 px-2.5 text-[11px] rounded-lg flex items-center gap-1 cursor-pointer ${
                      isRecording ? "bg-rose-50 border-rose-300 text-rose-700 animate-pulse" : "border-teal-200 text-[#087F78]"
                    }`}
                  >
                    {isRecording ? <MicOff className="h-3 w-3" /> : <Mic className="h-3 w-3" />}
                    <span>{isRecording ? "Stop Recording" : "Voice Input"}</span>
                  </Button>
                </div>
                <Textarea
                  value={activeDescription}
                  onChange={(e) => setActiveDescription(e.target.value)}
                  rows={4}
                  placeholder="Describe the issue, location context, hazard level, or surrounding landmarks..."
                  className="rounded-xl text-xs font-medium"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                  Nearby Landmark (Optional)
                </label>
                <Input
                  value={additionalLandmark}
                  onChange={(e) => setAdditionalLandmark(e.target.value)}
                  placeholder="e.g. Opposite Government Primary School, near temple"
                  className="rounded-xl text-xs font-medium"
                />
              </div>
            </div>

            {/* Navigation Actions */}
            <div className="flex items-center justify-between pt-4 border-t border-slate-100">
              <Button
                type="button"
                variant="outline"
                onClick={() => setCurrentStep(2)}
                className="text-xs text-slate-700"
              >
                <ArrowLeft className="h-3.5 w-3.5 mr-1" />
                Back to Location
              </Button>

              <Button
                type="button"
                variant="primary"
                onClick={() => {
                  setErrorMessage(null);
                  setCurrentStep(4);
                  // Run AI analysis if not already executed
                  if (selectedFile && !hasAiRun) {
                    triggerGeminiAnalysis(selectedFile, selectedLanguage);
                  }
                }}
                className="bg-[#087F78] hover:bg-[#06635e] text-white font-bold px-6 text-xs transition-all cursor-pointer"
              >
                <span>Continue to AI Analysis</span>
                <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
              </Button>
            </div>
          </Card>
        )}

        {/* =========================================================================
            STEP 4: AI ANALYSIS — GEMINI & ROBOFLOW MODELS (PHASE 4)
           ========================================================================= */}
        {!trackingId && currentStep === 4 && (
          <Card className="p-6 sm:p-8 space-y-6 rounded-3xl border-slate-200 shadow-sm bg-white">
            <div className="border-b border-slate-100 pb-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-[#062B46] flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-[#087F78]" />
                    <span>Step 4: AI Problem Analysis (Gemini Vision)</span>
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Google Gemini AI inspects your photo to detect defects and generate natural descriptions in your chosen language ({selectedLanguage.toUpperCase()}).
                  </p>
                </div>

                {selectedFile && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => triggerGeminiAnalysis(selectedFile, selectedLanguage)}
                    disabled={isAiAnalyzing}
                    className="text-xs border-teal-300 text-teal-800 hover:bg-teal-50 cursor-pointer"
                  >
                    {isAiAnalyzing ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <RotateCcw className="h-3.5 w-3.5 mr-1" />}
                    <span>Re-analyze</span>
                  </Button>
                )}
              </div>
            </div>

            {/* AI Analysis State */}
            {isAiAnalyzing ? (
              <div className="p-8 text-center bg-teal-50/50 rounded-2xl border border-teal-200 space-y-3">
                <Loader2 className="h-8 w-8 animate-spin text-[#087F78] mx-auto" />
                <p className="font-bold text-[#062B46] text-sm">
                  GramaSeva AI Multimodal Vision Analysis in Progress...
                </p>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  Analysing civic defect patterns, estimating hazard severity, and generating natural descriptions in {selectedLanguage === "kn" ? "Kannada" : selectedLanguage === "hi" ? "Hindi" : "English"}.
                </p>
              </div>
            ) : (
              <div className="space-y-5">
                {/* PHASE 4.3: Friendly AI Message Banner */}
                <div className="bg-gradient-to-r from-teal-50/90 to-blue-50/90 rounded-2xl p-5 border border-teal-200 space-y-3">
                  <div className="flex items-start gap-3">
                    <div className="h-10 w-10 rounded-full bg-teal-100 text-[#087F78] flex items-center justify-center shrink-0 shadow-2xs">
                      <Sparkles className="h-5 w-5" />
                    </div>
                    <div className="space-y-1">
                      <h3 className="font-bold text-sm text-[#062B46]">
                        Hello! I am GramaSeva AI.
                      </h3>
                      <p className="text-xs text-slate-700 leading-relaxed">
                        I analysed your uploaded photograph and identified a possible civic problem. Review the detected details below:
                      </p>
                    </div>
                  </div>

                  {/* AI Results Dossier */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 text-xs">
                    <div className="bg-white/90 p-3 rounded-xl border border-teal-200/60 space-y-1">
                      <span className="block text-[10px] font-bold uppercase text-slate-400">Detected Category</span>
                      <strong className="text-slate-900 block">{activeCategory.replace("_", " ").toUpperCase()}</strong>
                      {aiConfidenceScore && (
                        <span className="text-[11px] text-teal-700 font-semibold block">
                          AI Confidence: {Math.round(aiConfidenceScore * 100)}%
                        </span>
                      )}
                    </div>

                    <div className="bg-white/90 p-3 rounded-xl border border-teal-200/60 space-y-1">
                      <span className="block text-[10px] font-bold uppercase text-slate-400">Severity Assessment</span>
                      <Badge className="bg-amber-100 text-amber-800 border-amber-300 font-bold text-[10px]">
                        Severity: {aiSeverity}
                      </Badge>
                      {aiDefectLabel && (
                        <span className="text-[11px] text-slate-600 block truncate">Findings: {aiDefectLabel}</span>
                      )}
                    </div>

                    <div className="bg-white/90 p-3 rounded-xl border border-teal-200/60 sm:col-span-2 space-y-1">
                      <span className="block text-[10px] font-bold uppercase text-slate-400">Generated Title ({selectedLanguage.toUpperCase()})</span>
                      <strong className="text-slate-900 text-sm block">{issueTitle}</strong>
                    </div>

                    <div className="bg-white/90 p-3 rounded-xl border border-teal-200/60 sm:col-span-2 space-y-1">
                      <span className="block text-[10px] font-bold uppercase text-slate-400">Generated Description ({selectedLanguage.toUpperCase()})</span>
                      <p className="text-slate-700 text-xs leading-relaxed">{activeDescription}</p>
                    </div>
                  </div>

                  <p className="text-[11px] text-slate-500 italic pt-1">
                    Note: This is an AI suggestion. You can freely edit the title, category, and description before final confirmation.
                  </p>
                </div>

                {/* Edit Suggestions Inline */}
                <div className="p-4 rounded-2xl border border-slate-200 bg-slate-50 space-y-3">
                  <span className="block text-xs font-bold text-[#062B46]">
                    Fine-tune AI Generated Title & Description:
                  </span>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 mb-1">Title</label>
                    <Input
                      value={issueTitle}
                      onChange={(e) => setIssueTitle(e.target.value)}
                      className="bg-white rounded-xl text-xs font-medium"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 mb-1">Description</label>
                    <Textarea
                      value={activeDescription}
                      onChange={(e) => setActiveDescription(e.target.value)}
                      rows={3}
                      className="bg-white rounded-xl text-xs font-medium"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Navigation Actions */}
            <div className="flex items-center justify-between pt-4 border-t border-slate-100">
              <Button
                type="button"
                variant="outline"
                onClick={() => setCurrentStep(3)}
                className="text-xs text-slate-700"
              >
                <ArrowLeft className="h-3.5 w-3.5 mr-1" />
                Back to Details
              </Button>

              <Button
                type="button"
                variant="primary"
                onClick={() => {
                  setErrorMessage(null);
                  setCurrentStep(5);
                  runDuplicateMatching();
                }}
                disabled={isAiAnalyzing}
                className="bg-[#087F78] hover:bg-[#06635e] text-white font-bold px-6 text-xs transition-all cursor-pointer"
              >
                <span>Continue to Duplicate Check</span>
                <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
              </Button>
            </div>
          </Card>
        )}

        {/* =========================================================================
            STEP 5: MATCH — DUPLICATE COMPLAINT VERIFICATION (PHASE 5)
           ========================================================================= */}
        {!trackingId && currentStep === 5 && (
          <Card className="p-6 sm:p-8 space-y-6 rounded-3xl border-slate-200 shadow-sm bg-white">
            <div className="border-b border-slate-100 pb-4">
              <h2 className="text-lg font-bold text-[#062B46] flex items-center gap-2">
                <Search className="h-5 w-5 text-[#087F78]" />
                <span>Step 5: Similar Complaint Check</span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                We check whether this problem has already been reported nearby to avoid duplicate civic tickets and accelerate resolution.
              </p>
            </div>

            {/* Duplicate Candidate Results */}
            {isCheckingDuplicates ? (
              <div className="p-8 text-center bg-teal-50/50 rounded-2xl border border-teal-200 space-y-3">
                <Loader2 className="h-8 w-8 animate-spin text-[#087F78] mx-auto" />
                <p className="font-bold text-[#062B46] text-sm">
                  Checking for similar complaints in your vicinity...
                </p>
                <p className="text-xs text-slate-500">
                  Comparing geographic proximity, visual similarity, and issue category.
                </p>
              </div>
            ) : duplicateMatches.length > 0 ? (
              /* Case A: Similar complaints found */
              <div className="space-y-4">
                <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-xs text-amber-900 flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <strong className="block font-bold">
                      Similar complaints found ({duplicateMatches.length} nearby)
                    </strong>
                    <span>
                      Other citizens may have already reported an issue near this location. Review the existing tickets below:
                    </span>
                  </div>
                </div>

                {/* Match Cards List */}
                <div className="space-y-3">
                  {duplicateMatches.map((match) => (
                    <div
                      key={match.issue_id}
                      className="rounded-2xl border border-slate-200 p-4 bg-slate-50/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-[#087F78]">
                            {match.reference_number}
                          </span>
                          <Badge className="bg-slate-200 text-slate-800 text-[10px] uppercase font-bold">
                            {match.status}
                          </Badge>
                          <Badge className="bg-amber-100 text-amber-900 border-amber-300 text-[10px] font-semibold">
                            {Math.round(match.distance_meters)}m away
                          </Badge>
                        </div>
                        <p className="font-semibold text-[#062B46]">{match.summary}</p>
                        <p className="text-slate-500 text-[11px]">{match.explanation}</p>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <Link href={`/${locale}/track/${match.reference_number}`} target="_blank">
                          <Button variant="ghost" size="sm" className="text-xs text-slate-600 h-8">
                            <span>View Ticket</span>
                            <ExternalLink className="h-3 w-3 ml-1" />
                          </Button>
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Citizen Action Choice */}
                <div className="p-4 rounded-2xl border border-teal-200 bg-teal-50/50 space-y-2">
                  <span className="block text-xs font-bold text-[#062B46]">
                    How would you like to proceed?
                  </span>
                  <div className="space-y-2">
                    <label className="flex items-center gap-2.5 cursor-pointer text-xs font-semibold text-slate-800">
                      <input
                        type="radio"
                        name="duplicate_choice"
                        checked={duplicateChoice === "separate"}
                        onChange={() => setDuplicateChoice("separate")}
                        className="text-[#087F78] focus:ring-[#087F78]"
                      />
                      <span>This is a separate issue or still requires reporting (Continue submission)</span>
                    </label>

                    <label className="flex items-center gap-2.5 cursor-pointer text-xs font-semibold text-slate-800">
                      <input
                        type="radio"
                        name="duplicate_choice"
                        checked={duplicateChoice === "same"}
                        onChange={() => {
                          setDuplicateChoice("same");
                          if (duplicateMatches.length > 0) {
                            setSelectedDuplicateRef(duplicateMatches[0].reference_number);
                          }
                        }}
                        className="text-[#087F78] focus:ring-[#087F78]"
                      />
                      <span>This is the same issue (I want to link my evidence to this existing ticket)</span>
                    </label>
                  </div>
                </div>
              </div>
            ) : (
              /* Case B: No likely duplicate found */
              <div className="p-8 text-center bg-emerald-50 rounded-2xl border border-emerald-200 space-y-2.5">
                <div className="h-12 w-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto">
                  <CheckCircle className="h-6 w-6 stroke-[2.5]" />
                </div>
                <h3 className="font-bold text-emerald-950 text-sm">
                  Good news! We did not find a likely duplicate complaint. You can continue with your submission.
                </h3>
                <p className="text-xs text-emerald-800 max-w-sm mx-auto">
                  Your report appears unique in this vicinity. No active duplicate tickets were detected for this category and location.
                </p>
                <p className="text-[11px] text-emerald-700 italic pt-1">
                  Note: This is an AI-assisted similarity check.
                </p>
              </div>
            )}

            {/* Navigation Actions */}
            <div className="flex items-center justify-between pt-4 border-t border-slate-100">
              <Button
                type="button"
                variant="outline"
                onClick={() => setCurrentStep(4)}
                className="text-xs text-slate-700"
              >
                <ArrowLeft className="h-3.5 w-3.5 mr-1" />
                Back to AI Analysis
              </Button>

              <Button
                type="button"
                variant="primary"
                onClick={() => setCurrentStep(6)}
                disabled={isCheckingDuplicates}
                className="bg-[#087F78] hover:bg-[#06635e] text-white font-bold px-6 text-xs transition-all cursor-pointer"
              >
                <span>Continue to Review & Confirm</span>
                <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
              </Button>
            </div>
          </Card>
        )}

        {/* =========================================================================
            STEP 6: CONFIRM — FULL PREVIEW WITH EDIT BUTTONS (PHASE 6)
           ========================================================================= */}
        {!trackingId && currentStep === 6 && (
          <Card className="p-6 sm:p-8 space-y-6 rounded-3xl border-slate-200 shadow-sm bg-white">
            <div className="border-b border-slate-100 pb-4">
              <h2 className="text-lg font-bold text-[#062B46]">
                Step 6: Review & Confirm Submission
              </h2>
              <p className="text-xs text-slate-500">
                Please review all complaint details before final submission. Click Edit beside any section to adjust without losing entered information.
              </p>
            </div>

            {/* Full Preview Dossier with Edit Buttons on Every Section */}
            <div className="space-y-4 text-xs">
              {/* Section 1: Citizen Details */}
              <div className="p-4 rounded-2xl border border-slate-200 bg-white space-y-2">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <span className="font-bold text-xs uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                    <User className="h-3.5 w-3.5 text-[#087F78]" />
                    <span>Citizen Contact Details</span>
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setCurrentStep(1)}
                    className="text-xs text-[#087F78] hover:bg-teal-50 h-7 px-2 font-bold flex items-center gap-1"
                  >
                    <Edit className="h-3 w-3" />
                    <span>Edit</span>
                  </Button>
                </div>
                <div className="grid grid-cols-2 gap-2 text-slate-700 pt-1">
                  <div>Name: <strong className="text-slate-900">{citizenName || "Guest"}</strong></div>
                  <div>Mobile: <strong className="text-slate-900">{citizenPhone || "Not provided"}</strong></div>
                  <div className="col-span-2 text-[11px] text-slate-500">
                    Status: {isAuthenticated ? "Verified Citizen Account" : "Guest Citizen Submission"}
                  </div>
                </div>
              </div>

              {/* Section 2: Uploaded Evidence */}
              <div className="p-4 rounded-2xl border border-slate-200 bg-white space-y-2">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <span className="font-bold text-xs uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                    <Camera className="h-3.5 w-3.5 text-[#087F78]" />
                    <span>Uploaded Evidence Photograph</span>
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setCurrentStep(1)}
                    className="text-xs text-[#087F78] hover:bg-teal-50 h-7 px-2 font-bold flex items-center gap-1"
                  >
                    <Edit className="h-3 w-3" />
                    <span>Edit</span>
                  </Button>
                </div>
                {previewUrl && (
                  <div className="flex items-center gap-4 pt-1">
                    <img
                      src={previewUrl}
                      alt="Complaint Evidence"
                      className="h-20 w-20 rounded-xl object-cover border border-slate-200 shrink-0"
                    />
                    <div className="space-y-0.5 text-slate-600">
                      <p className="font-semibold text-slate-900">{selectedFile?.name}</p>
                      <p className="text-[11px]">Size: {selectedFile ? Math.round(selectedFile.size / 1024) : 0} KB</p>
                      <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 text-[10px] font-bold">
                        ✓ Image Verified
                      </Badge>
                    </div>
                  </div>
                )}
              </div>

              {/* Section 3: Location & Jurisdiction */}
              {locationData && (
                <div className="p-4 rounded-2xl border border-slate-200 bg-white space-y-2">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                    <span className="font-bold text-xs uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                      <MapPin className="h-3.5 w-3.5 text-[#087F78]" />
                      <span>Confirmed Location & Jurisdiction</span>
                    </span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setCurrentStep(2)}
                      className="text-xs text-[#087F78] hover:bg-teal-50 h-7 px-2 font-bold flex items-center gap-1"
                    >
                      <Edit className="h-3 w-3" />
                      <span>Edit</span>
                    </Button>
                  </div>
                  <p className="font-bold text-slate-800 pt-1">{locationData.address.formattedAddress}</p>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-[11px] text-slate-600">
                    <div>Village: <strong className="text-slate-800">{locationData.address.village}</strong></div>
                    <div>Taluk: <strong className="text-slate-800">{locationData.address.taluk}</strong></div>
                    <div>District: <strong className="text-slate-800">{locationData.address.district}</strong></div>
                    <div>PIN: <strong className="text-slate-800">{locationData.address.postalCode || "Not available"}</strong></div>
                    <div className="sm:col-span-2 font-mono text-teal-800">
                      Coordinates: {locationData.lat.toFixed(6)}°N, {locationData.lon.toFixed(6)}°E
                    </div>
                  </div>
                </div>
              )}

              {/* Section 4: Complaint Details */}
              <div className="p-4 rounded-2xl border border-slate-200 bg-white space-y-2">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <span className="font-bold text-xs uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                    <FileText className="h-3.5 w-3.5 text-[#087F78]" />
                    <span>Complaint Details ({selectedLanguage.toUpperCase()})</span>
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setCurrentStep(3)}
                    className="text-xs text-[#087F78] hover:bg-teal-50 h-7 px-2 font-bold flex items-center gap-1"
                  >
                    <Edit className="h-3 w-3" />
                    <span>Edit</span>
                  </Button>
                </div>
                <div className="space-y-1 pt-1">
                  <div className="flex items-center gap-2">
                    <Badge className="bg-teal-100 text-teal-800 border-teal-300 font-bold text-[10px]">
                      {activeCategory.replace("_", " ").toUpperCase()}
                    </Badge>
                    <Badge className="bg-slate-100 text-slate-700 text-[10px]">
                      Language: {selectedLanguage === "kn" ? "Kannada" : selectedLanguage === "hi" ? "Hindi" : "English"}
                    </Badge>
                  </div>
                  <h3 className="font-bold text-sm text-[#062B46]">{issueTitle}</h3>
                  <p className="text-slate-600">{activeDescription}</p>
                  {additionalLandmark && (
                    <p className="text-slate-500 text-[11px]">Landmark: {additionalLandmark}</p>
                  )}
                </div>
              </div>

              {/* Section 5: AI Verification & Duplicate Result */}
              <div className="p-4 rounded-2xl border border-slate-200 bg-white space-y-2">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <span className="font-bold text-xs uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                    <Sparkles className="h-3.5 w-3.5 text-[#087F78]" />
                    <span>AI Verification & Similarity Status</span>
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setCurrentStep(4)}
                    className="text-xs text-[#087F78] hover:bg-teal-50 h-7 px-2 font-bold flex items-center gap-1"
                  >
                    <Edit className="h-3 w-3" />
                    <span>Edit</span>
                  </Button>
                </div>
                <div className="grid grid-cols-2 gap-2 text-slate-700 pt-1 text-[11px]">
                  <div>Duplicate Status: <strong className="text-slate-900">{duplicateChoice === "same" ? "Linked to Existing Ticket" : "Verified Separate Complaint"}</strong></div>
                  <div>Estimated Severity: <strong className="text-slate-900">{aiSeverity}</strong></div>
                  {aiConfidenceScore && (
                    <div className="col-span-2 text-slate-500">Gemini Vision Defect Confidence: {Math.round(aiConfidenceScore * 100)}%</div>
                  )}
                </div>
              </div>
            </div>

            {/* Navigation & Submit Action */}
            <div className="flex items-center justify-between pt-4 border-t border-slate-100">
              <Button
                type="button"
                variant="outline"
                onClick={() => setCurrentStep(5)}
                disabled={isSubmitting}
                className="text-xs text-slate-700"
              >
                <ArrowLeft className="h-3.5 w-3.5 mr-1" />
                Back to Edit
              </Button>

              <Button
                type="button"
                variant="primary"
                onClick={handleSubmitComplaint}
                disabled={isSubmitting}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-8 py-2.5 text-xs rounded-xl shadow-sm transition-all cursor-pointer flex items-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Registering Complaint in PostgreSQL...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-4 w-4" />
                    <span>Confirm and Submit</span>
                  </>
                )}
              </Button>
            </div>
          </Card>
        )}

        {/* =========================================================================
            PHASE 7: POST-SUBMISSION SUCCESS MESSAGE
           ========================================================================= */}
        {trackingId && (
          <Card className="p-6 sm:p-10 text-center space-y-8 rounded-3xl border border-teal-200/80 shadow-lg bg-gradient-to-b from-white via-teal-50/20 to-white overflow-hidden relative">
            <div className="space-y-4">
              <div className="relative mx-auto w-24 h-24 flex items-center justify-center">
                <div className="absolute inset-0 rounded-full bg-emerald-200/60 animate-ping opacity-30" />
                <div className="relative w-20 h-20 rounded-full bg-gradient-to-tr from-emerald-600 to-teal-500 text-white flex items-center justify-center shadow-lg shadow-emerald-600/30">
                  <CheckCircle2 className="h-10 w-10 stroke-[2.5]" />
                </div>
                <div className="absolute -top-1 -right-1 bg-amber-400 text-amber-950 p-1.5 rounded-full shadow-md border-2 border-white flex items-center justify-center">
                  <Sparkles className="h-4 w-4 fill-amber-950 text-amber-950" />
                </div>
              </div>

              <div className="space-y-2">
                <div className="inline-flex items-center gap-1.5 bg-gradient-to-r from-amber-50 to-emerald-50 border border-emerald-300 px-3.5 py-1 rounded-full text-emerald-900 font-bold text-xs shadow-2xs">
                  <span className="text-amber-500">⭐</span>
                  <span>Grievance Officially Registered & Authenticated</span>
                </div>
                <h2 className="text-2xl sm:text-3xl font-extrabold text-[#062B46] tracking-tight">
                  Your complaint has been submitted successfully!
                </h2>
                <p className="text-xs sm:text-sm text-slate-600 max-w-lg mx-auto leading-relaxed">
                  Your complaint will now be reviewed by the responsible Village PDO. After approval, a field worker may be assigned to resolve the issue. You can track every update from your dashboard.
                </p>
              </div>
            </div>

            {/* Official Tracking Token Card */}
            <div className="rounded-2xl border-2 border-dashed border-[#087F78] bg-gradient-to-br from-teal-50/90 to-blue-50/70 p-6 sm:p-7 max-w-lg mx-auto space-y-4 shadow-sm relative">
              <div className="flex items-center justify-between border-b border-teal-200/80 pb-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-5 w-5 text-[#087F78]" />
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                    Official Grievance Tracking ID
                  </span>
                </div>
                <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 text-[10px] font-bold">
                  STATUS: SUBMITTED
                </Badge>
              </div>

              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 py-1">
                <div className="text-center sm:text-left">
                  <span className="font-mono text-3xl sm:text-4xl font-black text-[#087F78] tracking-wider select-all block">
                    {trackingId}
                  </span>
                  <span className="text-[11px] text-slate-500 block pt-0.5">
                    Karnataka Belagavi Taluk Civic Authority
                  </span>
                </div>

                <Button
                  type="button"
                  variant="outline"
                  onClick={copyTrackingId}
                  className="rounded-xl border-teal-300 bg-white hover:bg-teal-50 text-[#087F78] font-bold text-xs px-4 py-2 shadow-xs flex items-center gap-2 cursor-pointer shrink-0 transition-all"
                >
                  {copiedId ? (
                    <>
                      <Check className="h-4 w-4 text-emerald-600" />
                      <span className="text-emerald-700">Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-4 w-4" />
                      <span>Copy Tracking ID</span>
                    </>
                  )}
                </Button>
              </div>

              <div className="pt-2 border-t border-teal-200/60 flex items-center justify-between text-[11px] text-slate-500">
                <span className="flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5 text-teal-600" />
                  <span>Submission Date: {new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
                </span>
                <span className="text-emerald-700 font-semibold flex items-center gap-1">
                  <CheckCircle className="h-3.5 w-3.5" />
                  <span>Permanent PostgreSQL Record</span>
                </span>
              </div>
            </div>

            {/* Summary Details */}
            {locationData && (
              <div className="rounded-2xl border border-slate-200 bg-white p-5 max-w-xl mx-auto text-left text-xs space-y-2 shadow-2xs">
                <span className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-100 pb-2">
                  Confirmed Grievance Details
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-slate-700 pt-1">
                  <div>Category: <strong className="text-slate-900">{activeCategory.replace("_", " ").toUpperCase()}</strong></div>
                  <div>Village: <strong className="text-slate-900">{locationData.address.village}</strong></div>
                  <div className="sm:col-span-2">Location: <span className="text-slate-800">{locationData.address.formattedAddress}</span></div>
                  <div className="sm:col-span-2 font-mono text-teal-800 text-[11px]">
                    GPS Coordinates: {locationData.lat.toFixed(6)}°N, {locationData.lon.toFixed(6)}°E
                  </div>
                </div>
              </div>
            )}

            {/* Action Buttons Toolbar */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2 max-w-md mx-auto">
              <Link href={`/${locale}/track/${trackingId}`} className="w-full sm:w-auto flex-1">
                <Button
                  variant="primary"
                  className="w-full bg-[#087F78] hover:bg-[#06635e] text-white text-xs font-bold py-3 px-6 rounded-xl shadow-sm flex items-center justify-center gap-2 cursor-pointer"
                >
                  <span>Track Grievance Live</span>
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>

              <Button
                variant="outline"
                type="button"
                onClick={() => {
                  if (typeof window !== "undefined") window.print();
                }}
                className="w-full sm:w-auto border-slate-300 text-slate-700 hover:bg-slate-50 text-xs font-semibold py-3 px-4 rounded-xl flex items-center justify-center gap-2 cursor-pointer"
              >
                <Printer className="h-4 w-4 text-slate-500" />
                <span>Print Receipt</span>
              </Button>

              <Button
                variant="ghost"
                type="button"
                onClick={() => {
                  setSelectedFile(null);
                  setPreviewUrl(null);
                  setLocationData(null);
                  setIsLocationConfirmed(false);
                  setIssueTitle("");
                  setActiveDescription("");
                  setAdditionalLandmark("");
                  setTrackingId(null);
                  setHasAiRun(false);
                  setCurrentStep(1);
                }}
                className="w-full sm:w-auto text-[#087F78] hover:bg-teal-50 text-xs font-semibold py-3 px-4 rounded-xl cursor-pointer"
              >
                <span>Report Another Problem</span>
              </Button>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
