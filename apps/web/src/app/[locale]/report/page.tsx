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
  // 1: Photo
  // 2: Location
  // 3: Details
  // 4: AI Analysis
  // 5: Match
  // 6: Confirm
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [trackingId, setTrackingId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState(false);

  // Authenticated user state
  const [citizenName, setCitizenName] = useState<string>("");
  const [citizenPhone, setCitizenPhone] = useState<string>("");

  // STEP 1: Photo State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);

  // STEP 2: Location State
  const [locationData, setLocationData] = useState<LocationPickerChangeData | null>(null);
  const [isLocationConfirmed, setIsLocationConfirmed] = useState(false);

  // STEP 3: Details State
  const [issueTitle, setIssueTitle] = useState<string>("");
  const [activeCategory, setActiveCategory] = useState<string>("road_damage");
  const [activeDescription, setActiveDescription] = useState<string>("");
  const [additionalLandmark, setAdditionalLandmark] = useState<string>("");

  // Voice Recording State
  const [isRecording, setIsRecording] = useState(false);
  const recognitionRef = useRef<any>(null);

  // STEP 4: AI Analysis State (Gemini Multimodal Vision)
  const [isAiAnalyzing, setIsAiAnalyzing] = useState(false);
  const [aiPredictedCategory, setAiPredictedCategory] = useState<string>("road_damage");
  const [aiConfidenceScore, setAiConfidenceScore] = useState<number | null>(null);
  const [aiDefectLabel, setAiDefectLabel] = useState<string | null>(null);
  const [aiOcrText, setAiOcrText] = useState<string | null>(null);
  const [aiSeverity, setAiSeverity] = useState<string>("MEDIUM");
  const [hasAiRun, setHasAiRun] = useState(false);

  // STEP 5: Match State (Duplicate Suggestions)
  const [isCheckingDuplicates, setIsCheckingDuplicates] = useState(false);
  const [duplicateMatches, setDuplicateMatches] = useState<DuplicateSuggestionItem[]>([]);
  const [duplicateChoice, setDuplicateChoice] = useState<"separate" | "same">("separate");
  const [selectedDuplicateRef, setSelectedDuplicateRef] = useState<string | null>(null);

  // Load authenticated citizen profile on mount
  useEffect(() => {
    async function loadProfile() {
      const token =
        typeof window !== "undefined"
          ? localStorage.getItem("gramaseva_token") || localStorage.getItem("access_token")
          : null;
      if (!token) return;

      try {
        const res = await apiClient.get<any>("/citizen/profile");
        if (res) {
          if (res.full_name) setCitizenName(res.full_name);
          else if (res.name) setCitizenName(res.name);
          if (res.phone_number) setCitizenPhone(res.phone_number);
          else if (res.phone) setCitizenPhone(res.phone);
        }
      } catch {
        // Unauthenticated or profile fetch skipped
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
        rec.lang = locale === "kn" ? "kn-IN" : "en-IN";

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
  }, [locale]);

  // Camera Controls
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
    if (ctx) {
      ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
      canvas.toBlob((blob) => {
        if (blob) {
          const file = new File([blob], `civic_evidence_${Date.now()}.jpg`, { type: "image/jpeg" });
          setSelectedFile(file);
          setPreviewUrl(URL.createObjectURL(file));
          stopCamera();
          triggerGeminiAnalysis(file);
        }
      }, "image/jpeg", 0.92);
    }
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

    // Trigger Gemini multimodal analysis in background
    triggerGeminiAnalysis(file);
  };

  // Gemini Vision AI Multimodal Analysis (Step 4 preparation)
  const triggerGeminiAnalysis = async (file: File) => {
    setIsAiAnalyzing(true);
    setHasAiRun(true);
    try {
      const formData = new FormData();
      formData.append("file", file);

      const geminiRes = await apiClient.postForm<any>("/ai/gemini/analyze-problem", formData).catch(() => null);
      if (geminiRes) {
        if (geminiRes.suggested_category) {
          setAiPredictedCategory(geminiRes.suggested_category);
          setActiveCategory(geminiRes.suggested_category);
        }
        if (geminiRes.confidence) setAiConfidenceScore(geminiRes.confidence);
        if (geminiRes.visual_summary) setAiDefectLabel(geminiRes.visual_summary);
        if (geminiRes.title && !issueTitle) setIssueTitle(geminiRes.title);
        if (geminiRes.description && !activeDescription) setActiveDescription(geminiRes.description);
        if (geminiRes.ocr_text) setAiOcrText(geminiRes.ocr_text);
        if (geminiRes.severity) setAiSeverity(geminiRes.severity.toUpperCase());
      } else {
        // Fallback to Roboflow/CV endpoint
        const cvRes = await apiClient.postForm<any>("/ai/analyze-complaint", formData).catch(() => null);
        if (cvRes) {
          if (cvRes.predicted_category) {
            setAiPredictedCategory(cvRes.predicted_category);
            setActiveCategory(cvRes.predicted_category);
          }
          if (cvRes.confidence_score) setAiConfidenceScore(cvRes.confidence_score);
          if (cvRes.defect_label) setAiDefectLabel(cvRes.defect_label);
          if (cvRes.issue_title && !issueTitle) setIssueTitle(cvRes.issue_title);
          if (cvRes.ai_description && !activeDescription) setActiveDescription(cvRes.ai_description);
        }
      }
    } catch (err) {
      console.warn("AI analysis note:", err);
    } finally {
      setIsAiAnalyzing(false);
    }
  };

  // Step 5: Duplicate Complaint Matching
  const runDuplicateMatching = async () => {
    setIsCheckingDuplicates(true);
    try {
      const payload = {
        category: activeCategory,
        latitude: locationData?.lat,
        longitude: locationData?.lon,
        description: activeDescription,
        max_radius: 1000.0,
      };
      const res = await apiClient.post<DuplicateSuggestionItem[]>("/reports/check-duplicates", payload);
      if (Array.isArray(res)) {
        setDuplicateMatches(res);
      } else {
        setDuplicateMatches([]);
      }
    } catch (err) {
      console.warn("Duplicate matching check notice:", err);
      setDuplicateMatches([]);
    } finally {
      setIsCheckingDuplicates(false);
    }
  };

  // Voice Recording Toggle
  const toggleRecording = () => {
    if (isRecording) {
      recognitionRef.current?.stop();
      setIsRecording(false);
    } else {
      try {
        recognitionRef.current?.start();
        setIsRecording(true);
      } catch (e) {
        console.warn("Mic error:", e);
      }
    }
  };

  // Final Atomic Submission
  const handleSubmitComplaint = async () => {
    if (!selectedFile) {
      setErrorMessage("Please select or upload a photograph.");
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
      if (citizenName.trim()) {
        submitForm.append("citizen_name", citizenName.trim());
      }
      if (citizenPhone.trim()) {
        submitForm.append("citizen_phone", citizenPhone.trim());
      }

      // Original GPS coordinates
      const origLat = locationData.originalGpsLat ?? locationData.lat;
      const origLon = locationData.originalGpsLon ?? locationData.lon;
      submitForm.append("latitude", origLat.toString());
      submitForm.append("longitude", origLon.toString());
      if (locationData.originalAccuracy) {
        submitForm.append("gps_accuracy", locationData.originalAccuracy.toString());
      }
      submitForm.append("location_method", locationData.method);

      // Citizen-Confirmed / Adjusted Coordinates
      submitForm.append("confirmed_latitude", locationData.lat.toString());
      submitForm.append("confirmed_longitude", locationData.lon.toString());
      submitForm.append("confirmation_method", "CITIZEN_CONFIRMED");
      submitForm.append("location_confirmation_status", "CITIZEN_CONFIRMED");

      // Address components
      const addr = locationData.address;
      submitForm.append("confirmed_address", addr.formattedAddress);
      if (addr.village && !addr.village.includes("Not available")) {
        submitForm.append("detected_village", addr.village);
      }
      if (addr.taluk && !addr.taluk.includes("Not available")) {
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

      // AI Metadata
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
    { number: 1, title: "Photo" },
    { number: 2, title: "Location" },
    { number: 3, title: "Details" },
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
            Report civic defects in your Gram Panchayat. Follow the 6-step reporting wizard for verified GPS location, AI analysis, and real-time tracking.
          </p>
        </div>

        {/* Six-Step Workflow Progress Stepper (Always visible before final confirmation) */}
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
                      // Allow navigating back to completed steps
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
            STEP 1: PHOTO — CAPTURE OR UPLOAD A PHOTOGRAPH
           ========================================================================= */}
        {!trackingId && currentStep === 1 && (
          <Card className="p-6 sm:p-8 space-y-6 rounded-3xl border-slate-200 shadow-sm bg-white">
            <div className="text-center space-y-1">
              <h2 className="text-lg font-bold text-[#062B46]">
                Step 1: Capture or Upload a Photograph
              </h2>
              <p className="text-xs text-slate-500">
                A clear photo helps the AI and public works team assess the defect and dispatch the right repair crew.
              </p>
            </div>

            {/* Photo Upload / Capture Box */}
            {!previewUrl ? (
              <div className="space-y-4">
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-teal-300 hover:border-teal-500 rounded-2xl p-8 sm:p-12 text-center bg-teal-50/30 hover:bg-teal-50/60 transition-all cursor-pointer flex flex-col items-center justify-center gap-3"
                >
                  <div className="h-16 w-16 rounded-full bg-teal-100 text-[#087F78] flex items-center justify-center shadow-xs">
                    <Upload className="h-8 w-8" />
                  </div>
                  <div>
                    <p className="font-bold text-[#062B46] text-sm sm:text-base">
                      Click to Browse or Drag Photograph Here
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      Supports JPEG, PNG, WebP up to 10 MB
                    </p>
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
                  <Button
                    type="button"
                    variant="primary"
                    onClick={startCamera}
                    className="w-full sm:w-auto bg-[#087F78] hover:bg-[#06635e] text-white font-bold px-6 py-2.5 rounded-xl shadow-xs flex items-center justify-center gap-2 cursor-pointer"
                  >
                    <Camera className="h-4 w-4" />
                    <span>Open Mobile Camera</span>
                  </Button>

                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => fileInputRef.current?.click()}
                    className="w-full sm:w-auto border-slate-300 text-slate-700 font-semibold px-6 py-2.5 rounded-xl cursor-pointer"
                  >
                    <Upload className="h-4 w-4 mr-1.5" />
                    <span>Upload from Gallery</span>
                  </Button>
                </div>
              </div>
            ) : (
              /* Image Preview Box */
              <div className="space-y-4">
                <div className="relative rounded-2xl overflow-hidden border border-slate-200 bg-slate-900 max-h-96 flex items-center justify-center">
                  <img
                    src={previewUrl}
                    alt="Problem Preview"
                    className="w-full max-h-96 object-contain"
                  />
                  {isAiAnalyzing && (
                    <div className="absolute inset-0 bg-black/50 backdrop-blur-xs flex flex-col items-center justify-center text-white p-4">
                      <Loader2 className="h-8 w-8 animate-spin text-teal-400 mb-2" />
                      <p className="font-bold text-sm">Gemini AI analyzing problem evidence...</p>
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between gap-3">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSelectedFile(null);
                      setPreviewUrl(null);
                    }}
                    className="text-xs border-slate-300 text-slate-700"
                  >
                    <RotateCcw className="h-3.5 w-3.5 mr-1" />
                    Replace Photograph
                  </Button>

                  <Button
                    type="button"
                    variant="primary"
                    onClick={() => setCurrentStep(2)}
                    disabled={!selectedFile}
                    className="bg-[#087F78] hover:bg-[#06635e] text-white font-bold px-6 text-xs cursor-pointer disabled:opacity-50"
                  >
                    <span>Continue to Location</span>
                    <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
                  </Button>
                </div>
              </div>
            )}

            {/* Hidden File Inputs */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleFileChange}
            />
            <input
              ref={cameraInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              onChange={handleFileChange}
            />
          </Card>
        )}

        {/* Live Camera Modal */}
        {isCameraOpen && (
          <div className="fixed inset-0 z-50 bg-black/90 flex flex-col items-center justify-center p-4">
            <div className="w-full max-w-lg bg-black rounded-3xl overflow-hidden relative border border-slate-800">
              <video ref={videoRef} autoPlay playsInline className="w-full h-80 sm:h-96 object-cover" />
              <div className="absolute top-4 right-4 flex items-center gap-2">
                <button
                  type="button"
                  onClick={stopCamera}
                  className="p-2 rounded-full bg-black/60 text-white hover:bg-black/80"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
              <div className="p-4 bg-slate-950 flex items-center justify-around">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={stopCamera}
                  className="text-white border-slate-700"
                >
                  Cancel
                </Button>
                <button
                  type="button"
                  onClick={capturePhoto}
                  className="h-16 w-16 rounded-full border-4 border-white bg-rose-600 flex items-center justify-center active:scale-95 transition-all shadow-lg"
                >
                  <Camera className="h-7 w-7 text-white" />
                </button>
                <div className="w-16" />
              </div>
            </div>
          </div>
        )}

        {/* =========================================================================
            STEP 2: LOCATION — GOOGLE MAPS & LOCATION CONFIRMATION
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

            {/* Reusable Real Google Maps Picker Component */}
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
                className="bg-[#087F78] hover:bg-[#06635e] text-white font-bold px-6 text-xs transition-all disabled:opacity-50"
              >
                <span>Continue to Details</span>
                <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
              </Button>
            </div>
          </Card>
        )}

        {/* =========================================================================
            STEP 3: DETAILS — CITIZEN & COMPLAINT DETAILS
           ========================================================================= */}
        {!trackingId && currentStep === 3 && (
          <Card className="p-6 sm:p-8 space-y-6 rounded-3xl border-slate-200 shadow-sm bg-white">
            <div className="border-b border-slate-100 pb-4">
              <h2 className="text-lg font-bold text-[#062B46]">
                Step 3: Citizen & Complaint Details
              </h2>
              <p className="text-xs text-slate-500">
                Your contact details are pre-filled from your profile. Provide a title and description for the issue.
              </p>
            </div>

            {/* Confirmed Location Badge Pill */}
            {locationData && (
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 flex items-start gap-2.5 text-xs text-slate-700">
                <MapPin className="h-4 w-4 text-[#087F78] shrink-0 mt-0.5" />
                <div className="flex-1">
                  <strong>Confirmed Location:</strong> {locationData.address.formattedAddress}
                  <div className="text-[11px] text-slate-500 mt-0.5">
                    Village: {locationData.address.village} • Taluk: {locationData.address.taluk}
                  </div>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setCurrentStep(2)}
                  className="text-xs text-teal-700 h-7 px-2"
                >
                  Adjust Pin
                </Button>
              </div>
            )}

            {/* Citizen Contact Details (Editable) */}
            <div className="bg-slate-50 rounded-2xl p-4 border border-slate-200 space-y-3">
              <span className="block text-xs font-bold uppercase tracking-wider text-slate-600">
                Citizen Contact Information
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1 flex items-center gap-1">
                    <User className="h-3 w-3 text-slate-400" />
                    <span>Citizen Full Name</span>
                  </label>
                  <Input
                    value={citizenName}
                    onChange={(e) => setCitizenName(e.target.value)}
                    placeholder="Enter your name"
                    className="bg-white rounded-xl text-xs font-medium"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1 flex items-center gap-1">
                    <Phone className="h-3 w-3 text-slate-400" />
                    <span>Contact Phone Number</span>
                  </label>
                  <Input
                    value={citizenPhone}
                    onChange={(e) => setCitizenPhone(e.target.value)}
                    placeholder="e.g. 9876543210"
                    className="bg-white rounded-xl text-xs font-medium"
                  />
                </div>
              </div>
            </div>

            {/* Form Fields: Title, Description, Landmark */}
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                  Complaint Title *
                </label>
                <Input
                  value={issueTitle}
                  onChange={(e) => setIssueTitle(e.target.value)}
                  placeholder="e.g. Deep Pothole on Main Road near Bus Stop"
                  className="rounded-xl border-slate-200 text-sm font-semibold text-[#062B46]"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">
                    Detailed Problem Description *
                  </label>
                  <Button
                    type="button"
                    variant={isRecording ? "primary" : "outline"}
                    size="sm"
                    onClick={toggleRecording}
                    className={`text-xs h-7 px-2.5 font-semibold ${
                      isRecording ? "bg-rose-600 hover:bg-rose-700 text-white animate-pulse" : "border-slate-300"
                    }`}
                  >
                    {isRecording ? <MicOff className="h-3 w-3 mr-1" /> : <Mic className="h-3 w-3 mr-1" />}
                    <span>{isRecording ? "Stop Recording" : "Voice Typing"}</span>
                  </Button>
                </div>
                <Textarea
                  rows={4}
                  value={activeDescription}
                  onChange={(e) => setActiveDescription(e.target.value)}
                  placeholder="Describe the problem, severity, hazards, or impact on local residents..."
                  className="rounded-xl border-slate-200 text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                  Additional Relevant Information / Landmark (Optional)
                </label>
                <Input
                  value={additionalLandmark}
                  onChange={(e) => setAdditionalLandmark(e.target.value)}
                  placeholder="e.g. Opposite Government Primary School, near cross road"
                  className="rounded-xl border-slate-200 text-xs"
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
                  if (!issueTitle.trim()) {
                    setErrorMessage("Please enter a complaint title.");
                    return;
                  }
                  if (!activeDescription.trim()) {
                    setErrorMessage("Please enter a problem description.");
                    return;
                  }
                  setErrorMessage(null);
                  setCurrentStep(4);
                }}
                disabled={!issueTitle.trim() || !activeDescription.trim()}
                className="bg-[#087F78] hover:bg-[#06635e] text-white font-bold px-6 text-xs transition-all disabled:opacity-50"
              >
                <span>Continue to AI Analysis</span>
                <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
              </Button>
            </div>
          </Card>
        )}

        {/* =========================================================================
            STEP 4: AI ANALYSIS — GEMINI VISION MULTIMODAL FINDINGS
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
                    Google Gemini AI multimodal analysis inspects your photo to detect civic defects, suggest categories, estimate severity, and extract visible landmarks.
                  </p>
                </div>
                {selectedFile && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => triggerGeminiAnalysis(selectedFile)}
                    disabled={isAiAnalyzing}
                    className="text-xs border-teal-300 text-teal-800 hover:bg-teal-50"
                  >
                    {isAiAnalyzing ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <RotateCcw className="h-3.5 w-3.5 mr-1" />}
                    <span>Re-analyze</span>
                  </Button>
                )}
              </div>
            </div>

            {/* AI Analysis Results Card */}
            {isAiAnalyzing ? (
              <div className="p-8 text-center bg-teal-50/50 rounded-2xl border border-teal-200 space-y-3">
                <Loader2 className="h-8 w-8 animate-spin text-[#087F78] mx-auto" />
                <p className="font-bold text-[#062B46] text-sm">
                  Gemini Vision Multimodal Analysis in Progress...
                </p>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  Extracting visual defect patterns, estimating hazard severity, and detecting road or infrastructure boundaries.
                </p>
              </div>
            ) : (
              <div className="space-y-5">
                {/* Visual Summary & Badges */}
                <div className="bg-gradient-to-r from-teal-50/80 to-blue-50/80 rounded-2xl p-5 border border-teal-200/80 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-xs font-bold text-[#062B46] uppercase tracking-wider">
                      Gemini Visual Assessment
                    </span>
                    <div className="flex items-center gap-2">
                      {aiConfidenceScore && (
                        <Badge className="bg-teal-100 text-teal-900 border-teal-300 font-bold text-[11px]">
                          {Math.round(aiConfidenceScore * 100)}% Confidence
                        </Badge>
                      )}
                      <Badge className="bg-blue-100 text-blue-900 border-blue-300 font-bold text-[11px]">
                        AI Assisted
                      </Badge>
                    </div>
                  </div>

                  {aiDefectLabel && (
                    <p className="text-xs font-semibold text-slate-800">
                      Visual Findings: <span className="font-normal text-slate-700">{aiDefectLabel}</span>
                    </p>
                  )}

                  {aiOcrText && (
                    <div className="rounded-lg bg-white/80 p-2.5 border border-teal-200 text-xs">
                      <span className="block text-[10px] font-bold text-slate-500 uppercase">
                        Detected Signage / OCR Text
                      </span>
                      <p className="font-mono text-slate-800">{aiOcrText}</p>
                    </div>
                  )}

                  <p className="text-[11px] text-slate-500 italic">
                    Note: Gemini provides suggestions only. You can adjust or override every field below before continuing.
                  </p>
                </div>

                {/* Citizen Editable Fields */}
                <div className="space-y-4">
                  {/* Category Selection */}
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                      Problem Category (Gemini Suggestion) *
                    </label>
                    <Select
                      value={activeCategory}
                      onChange={(e) => setActiveCategory(e.target.value)}
                      options={CATEGORY_OPTIONS}
                      className="rounded-xl border-slate-200 text-sm font-semibold"
                    />
                  </div>

                  {/* Severity Level Selector */}
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                      Estimated Defect Severity *
                    </label>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                      {SEVERITY_LEVELS.map((sev) => {
                        const isSelected = aiSeverity === sev.id;
                        return (
                          <button
                            key={sev.id}
                            type="button"
                            onClick={() => setAiSeverity(sev.id)}
                            className={`py-2 px-3 rounded-xl border text-xs font-bold transition-all text-center ${
                              isSelected
                                ? "bg-[#087F78] text-white border-[#087F78] shadow-xs"
                                : "bg-white text-slate-700 border-slate-200 hover:border-slate-300"
                            }`}
                          >
                            {sev.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Title & Description Corrections */}
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                      Complaint Title
                    </label>
                    <Input
                      value={issueTitle}
                      onChange={(e) => setIssueTitle(e.target.value)}
                      placeholder="Title"
                      className="rounded-xl border-slate-200 text-sm font-semibold text-[#062B46]"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                      Complaint Description
                    </label>
                    <Textarea
                      rows={3}
                      value={activeDescription}
                      onChange={(e) => setActiveDescription(e.target.value)}
                      placeholder="Description"
                      className="rounded-xl border-slate-200 text-sm"
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
                  runDuplicateMatching();
                  setCurrentStep(5);
                }}
                disabled={isAiAnalyzing}
                className="bg-[#087F78] hover:bg-[#06635e] text-white font-bold px-6 text-xs transition-all cursor-pointer"
              >
                <span>Continue to Similar Match</span>
                <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
              </Button>
            </div>
          </Card>
        )}

        {/* =========================================================================
            STEP 5: MATCH — SIMILAR COMPLAINT CHECK
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
                  Comparing geographic proximity, category, and issue description.
                </p>
              </div>
            ) : duplicateMatches.length > 0 ? (
              <div className="space-y-4">
                <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-xs text-amber-900 flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <strong className="block font-bold">
                      {duplicateMatches.length} Similar Complaint{duplicateMatches.length > 1 ? "s" : ""} Found Nearby
                    </strong>
                    <span>
                      Other citizens may have already reported an issue at or near this location. Review the existing tickets below:
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
                      <span>This is a separate issue or still requires fresh reporting (Continue)</span>
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
              <div className="p-8 text-center bg-emerald-50 rounded-2xl border border-emerald-200 space-y-2">
                <div className="h-12 w-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto">
                  <CheckCircle className="h-6 w-6 stroke-[2.5]" />
                </div>
                <h3 className="font-bold text-emerald-950 text-sm">
                  No Similar Civic Complaints Found Nearby
                </h3>
                <p className="text-xs text-emerald-800 max-w-sm mx-auto">
                  Your report appears unique in this vicinity. No active duplicate tickets were detected for this category and location.
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
            STEP 6: CONFIRM — REVIEW & CONFIRM SUBMISSION
           ========================================================================= */}
        {!trackingId && currentStep === 6 && (
          <Card className="p-6 sm:p-8 space-y-6 rounded-3xl border-slate-200 shadow-sm bg-white">
            <div className="border-b border-slate-100 pb-4">
              <h2 className="text-lg font-bold text-[#062B46]">
                Step 6: Review & Confirm Submission
              </h2>
              <p className="text-xs text-slate-500">
                Please review all complaint details before final submission. Your grievance will be permanently recorded in the Gram Panchayat ledger.
              </p>
            </div>

            {/* Submission Preview Breakdown */}
            <div className="space-y-4 text-xs">
              {/* Photo & Summary Header */}
              <div className="p-4 rounded-2xl border border-slate-200 bg-slate-50 flex flex-col sm:flex-row items-center gap-4">
                {previewUrl && (
                  <img
                    src={previewUrl}
                    alt="Complaint Evidence"
                    className="h-28 w-28 rounded-xl object-cover border border-slate-200 shrink-0"
                  />
                )}
                <div className="space-y-1.5 flex-1 text-center sm:text-left">
                  <Badge className="bg-teal-100 text-teal-800 border-teal-300 font-bold text-[10px]">
                    {activeCategory.replace("_", " ").toUpperCase()}
                  </Badge>
                  <h3 className="font-bold text-sm text-[#062B46]">{issueTitle}</h3>
                  <p className="text-slate-600 line-clamp-2">{activeDescription}</p>
                  {additionalLandmark && (
                    <p className="text-slate-500 text-[11px]">Landmark: {additionalLandmark}</p>
                  )}
                </div>
              </div>

              {/* Location Summary */}
              {locationData && (
                <div className="p-4 rounded-2xl border border-slate-200 bg-white space-y-2">
                  <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Confirmed Location & Jurisdiction
                  </span>
                  <p className="font-bold text-slate-800">{locationData.address.formattedAddress}</p>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-[11px] text-slate-600">
                    <div>Village: <strong>{locationData.address.village}</strong></div>
                    <div>Taluk: <strong>{locationData.address.taluk}</strong></div>
                    <div>District: <strong>{locationData.address.district}</strong></div>
                    <div>GPS Coordinates: <strong>{locationData.lat.toFixed(6)}°N, {locationData.lon.toFixed(6)}°E</strong></div>
                  </div>
                </div>
              )}

              {/* Citizen Contact & Duplicate Status */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="p-3.5 rounded-2xl border border-slate-200 bg-white space-y-1">
                  <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Reporting Citizen
                  </span>
                  <p className="font-bold text-[#062B46]">{citizenName || "Anonymous Resident"}</p>
                  <p className="text-slate-500 text-[11px]">Phone: {citizenPhone || "Not provided"}</p>
                </div>

                <div className="p-3.5 rounded-2xl border border-slate-200 bg-white space-y-1">
                  <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Duplicate Status & Severity
                  </span>
                  <div className="flex items-center gap-2">
                    <Badge className="bg-emerald-100 text-emerald-800 font-bold text-[10px]">
                      {duplicateChoice === "same" ? "Linked to Existing" : "Verified Separate Issue"}
                    </Badge>
                    <Badge className="bg-amber-100 text-amber-800 font-bold text-[10px]">
                      Severity: {aiSeverity}
                    </Badge>
                  </div>
                  {aiConfidenceScore && (
                    <p className="text-slate-500 text-[11px]">
                      Gemini Vision Confidence: {Math.round(aiConfidenceScore * 100)}%
                    </p>
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
                className="bg-[#087F78] hover:bg-[#06635e] text-white font-bold px-8 py-2.5 rounded-xl shadow-md cursor-pointer flex items-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Submitting Complaint...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle className="h-4 w-4" />
                    <span>Confirm & Submit Complaint ✓</span>
                  </>
                )}
              </Button>
            </div>
          </Card>
        )}

        {/* =========================================================================
            FINAL SUCCESS CONFIRMATION & TRACKING ID — STARRED OFFICIAL UI
           ========================================================================= */}
        {trackingId && (
          <Card className="p-6 sm:p-10 text-center space-y-8 rounded-3xl border border-teal-200/80 shadow-lg bg-gradient-to-b from-white via-teal-50/20 to-white overflow-hidden relative">
            {/* Background Decorative Rings */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-96 bg-teal-100/40 rounded-full blur-3xl pointer-events-none -z-10" />

            {/* Celebratory Icon & Badge */}
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
                  Thank You! Your Grievance is Lodged
                </h2>
                <p className="text-xs sm:text-sm text-slate-600 max-w-lg mx-auto leading-relaxed">
                  Your complaint has been securely registered in the official <strong>GramaSeva Public Grievance Ledger</strong> and routed to the <strong>Panchayat Development Officer (PDO)</strong> for immediate field verification.
                </p>
              </div>
            </div>

            {/* Prominent Official Tracking Token Card */}
            <div className="rounded-2xl border-2 border-dashed border-[#087F78] bg-gradient-to-br from-teal-50/90 to-blue-50/70 p-6 sm:p-7 max-w-lg mx-auto space-y-4 shadow-sm relative">
              <div className="flex items-center justify-between border-b border-teal-200/80 pb-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-5 w-5 text-[#087F78]" />
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                    Official Grievance Tracking ID
                  </span>
                </div>
                <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 text-[10px] font-bold">
                  ACTIVE • STATUS: SUBMITTED
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
                      <span className="text-emerald-700">Copied to Clipboard!</span>
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
                  <span>Logged on: {new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
                </span>
                <span className="text-emerald-700 font-semibold flex items-center gap-1">
                  <CheckCircle className="h-3.5 w-3.5" />
                  <span>Tamper-Proof Audit Sealed</span>
                </span>
              </div>
            </div>

            {/* Karnataka Sakala Civic Guarantee 4-Step SLA Timeline */}
            <div className="max-w-xl mx-auto rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-2xs space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-[#062B46] uppercase tracking-wider flex items-center gap-1.5">
                  <Award className="h-4 w-4 text-[#087F78]" />
                  <span>Karnataka Sakala Civic Guarantee Timeline</span>
                </span>
                <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                  Target: 72 Hours
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                {/* Step 1 */}
                <div className="rounded-xl p-2.5 bg-emerald-50 border border-emerald-200 space-y-1">
                  <div className="flex items-center gap-1 text-emerald-700 font-bold text-[11px]">
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                    <span>1. Submitted</span>
                  </div>
                  <p className="text-[10px] text-emerald-800 leading-tight">Recorded in database</p>
                </div>

                {/* Step 2 */}
                <div className="rounded-xl p-2.5 bg-sky-50 border border-sky-200 space-y-1">
                  <div className="flex items-center gap-1 text-sky-800 font-bold text-[11px]">
                    <Clock className="h-3.5 w-3.5 shrink-0 animate-pulse text-sky-600" />
                    <span>2. PDO Triage</span>
                  </div>
                  <p className="text-[10px] text-sky-900 leading-tight">Within 24 hours</p>
                </div>

                {/* Step 3 */}
                <div className="rounded-xl p-2.5 bg-slate-50 border border-slate-200 space-y-1">
                  <div className="flex items-center gap-1 text-slate-700 font-bold text-[11px]">
                    <Layers className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                    <span>3. Work Order</span>
                  </div>
                  <p className="text-[10px] text-slate-500 leading-tight">Staff dispatched</p>
                </div>

                {/* Step 4 */}
                <div className="rounded-xl p-2.5 bg-slate-50 border border-slate-200 space-y-1">
                  <div className="flex items-center gap-1 text-slate-700 font-bold text-[11px]">
                    <CheckCircle className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                    <span>4. Verified</span>
                  </div>
                  <p className="text-[10px] text-slate-500 leading-tight">After-photo closure</p>
                </div>
              </div>
            </div>

            {/* Official Complaint Dossier Breakdown */}
            {locationData && (
              <div className="rounded-2xl border border-slate-200 bg-white p-5 max-w-xl mx-auto text-left text-xs space-y-3 shadow-2xs">
                <span className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-100 pb-2">
                  Registered Incident Summary
                </span>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-slate-700">
                  <div className="space-y-0.5">
                    <span className="text-[10px] font-bold uppercase text-slate-400 block">Civic Category & Title</span>
                    <strong className="text-slate-900 font-semibold block">{issueTitle || activeCategory.replace("_", " ").toUpperCase()}</strong>
                    <span className="text-[11px] text-[#087F78] font-bold">{activeCategory.replace("_", " ").toUpperCase()}</span>
                  </div>

                  <div className="space-y-0.5">
                    <span className="text-[10px] font-bold uppercase text-slate-400 block">Assigned Gram Panchayat</span>
                    <strong className="text-slate-900 font-semibold block">{locationData.address.village}</strong>
                    <span className="text-[11px] text-slate-500">{locationData.address.taluk} • Belagavi</span>
                  </div>

                  <div className="space-y-0.5 sm:col-span-2">
                    <span className="text-[10px] font-bold uppercase text-slate-400 block">Incident Coordinates & Address</span>
                    <span className="text-slate-800 block">{locationData.address.formattedAddress}</span>
                    <span className="font-mono text-[11px] text-teal-700 block">
                      📍 {locationData.lat.toFixed(6)}°N, {locationData.lon.toFixed(6)}°E
                    </span>
                  </div>

                  {citizenPhone && (
                    <div className="space-y-0.5 sm:col-span-2 pt-1 border-t border-slate-100 flex items-center justify-between text-[11px]">
                      <span className="text-slate-500">Citizen Mobile: <strong className="text-slate-800">{citizenPhone}</strong></span>
                      <span className="text-emerald-700 font-semibold">✓ SMS & WhatsApp Updates Enabled</span>
                    </div>
                  )}
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
