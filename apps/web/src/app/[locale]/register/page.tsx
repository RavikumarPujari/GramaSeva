"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import {
  UserPlus,
  ArrowRight,
  UserCheck,
  Wrench,
  Clock,
  CheckCircle2,
  AlertCircle,
  Building2,
  Mail,
  Phone,
  Lock,
  User,
} from "lucide-react";
import { apiClient, ApiError } from "@/lib/api-client";
import { GramaSevaLogo } from "@/components/ui/GramaSevaLogo";

type RegisterType = "citizen" | "worker";

export default function RegisterPage() {
  const locale = useLocale();
  const tNav = useTranslations("navigation");
  const router = useRouter();

  const [registerType, setRegisterType] = useState<RegisterType>("citizen");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [password, setPassword] = useState("");
  const [villageId, setVillageId] = useState("peeranwadi");
  const [villageName, setVillageName] = useState("Peeranwadi Gram Panchayat");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Success state for Worker
  const [workerSubmitted, setWorkerSubmitted] = useState(false);

  const villages = [
    { id: "peeranwadi", name: "Peeranwadi Gram Panchayat" },
    { id: "kuttalawadi", name: "Kuttalawadi Gram Panchayat" },
    { id: "zad-shahapur", name: "Zad-Shahapur Gram Panchayat" },
    { id: "santibastawad", name: "Santibastawad Gram Panchayat" },
    { id: "yellur", name: "Yellur Gram Panchayat" },
    { id: "sulge-yellur", name: "Sulge (Yellur) Gram Panchayat" },
    { id: "mandoli", name: "Mandoli Gram Panchayat" },
    { id: "waghawade", name: "Waghawade Gram Panchayat" },
    { id: "navage", name: "Navage Gram Panchayat" },
  ];

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      if (registerType === "citizen") {
        const res = await apiClient.post<any>("/auth/register", {
          email: email.trim().toLowerCase(),
          password: password,
          full_name: fullName.trim(),
          phone_number: phoneNumber.trim() || undefined,
          preferred_locale: locale,
        });

        if (res.access_token) {
          localStorage.setItem("gramaseva_token", res.access_token);
          localStorage.setItem("access_token", res.access_token);
          localStorage.setItem("gramaseva_user", JSON.stringify(res.profile));
          router.push(`/${locale}/citizen`);
        }
      } else {
        // Field Worker Registration
        const res = await apiClient.post<any>("/auth/register-worker", {
          email: email.trim().toLowerCase(),
          password: password,
          full_name: fullName.trim(),
          phone_number: phoneNumber.trim() || undefined,
          village_id: villageId,
          preferred_locale: locale,
        });

        if (res.access_token) {
          localStorage.setItem("gramaseva_token", res.access_token);
          localStorage.setItem("access_token", res.access_token);
          localStorage.setItem("gramaseva_user", JSON.stringify(res.profile));
        }

        setWorkerSubmitted(true);
      }
    } catch (err: any) {
      setErrorMessage(
        err.message || "Failed to create account. Please ensure your email is unique and password has at least 6 characters."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  // If worker registered, show confirmation that account is pending approval
  if (workerSubmitted) {
    return (
      <div className="min-h-screen bg-[#F4F8FC] flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
        <div className="sm:mx-auto sm:w-full sm:max-w-lg">
          <div className="flex justify-center mb-4">
            <GramaSevaLogo size="md" />
          </div>

          <div className="bg-white border-2 border-amber-300 rounded-3xl shadow-xl p-8 space-y-6">
            <div className="w-12 h-12 rounded-2xl bg-amber-100 text-amber-800 flex items-center justify-center mx-auto">
              <Clock className="w-6 h-6" />
            </div>

            <div className="text-center space-y-2">
              <h2 className="text-xl font-extrabold text-[#102B4E]">
                Worker Application Submitted
              </h2>
              <p className="text-xs sm:text-sm text-[#40536B]">
                Your registration has been submitted and is currently{" "}
                <span className="font-bold text-amber-800 bg-amber-100 px-2 py-0.5 rounded">
                  Pending PDO Approval
                </span>
              </p>
            </div>

            <div className="rounded-2xl bg-[#F4F8FC] border border-[#DCE5EE] p-4 text-xs space-y-2.5">
              <div className="flex justify-between">
                <span className="text-[#40536B]">Applicant:</span>
                <span className="font-bold text-[#102B4E]">{fullName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#40536B]">Registered Email:</span>
                <span className="font-bold text-[#102B4E]">{email}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#40536B]">Assigned Gram Panchayat:</span>
                <span className="font-bold text-[#087F78]">{villageName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#40536B]">Account Status:</span>
                <span className="font-bold text-amber-700">PENDING_REVIEW</span>
              </div>
            </div>

            <p className="text-xs text-[#40536B] leading-relaxed">
              In accordance with GramaSeva governance, a field technician must be reviewed and authorized by the local Gram Panchayat Development Officer (PDO) before work orders can be viewed or assigned.
            </p>

            <div className="pt-2 flex flex-col sm:flex-row gap-3">
              <Link href={`/${locale}/login`} className="flex-1">
                <button
                  type="button"
                  className="w-full h-11 px-4 rounded-xl bg-[#087F78] hover:bg-[#066B65] text-white font-semibold text-xs sm:text-sm flex items-center justify-center gap-2 shadow-2xs transition-all"
                >
                  <ArrowRight className="w-4 h-4" />
                  <span>Go to Role Sign In</span>
                </button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F4F8FC] flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="flex justify-center mb-3">
          <GramaSevaLogo size="lg" />
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-[#102B4E] tracking-tight">
          Create an Account
        </h1>
        <p className="mt-1 text-xs sm:text-sm text-[#40536B]">
          Join the GramaSeva verified civic governance platform
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 sm:px-10 rounded-3xl shadow-sm border border-[#DCE5EE] space-y-6">
          {/* Account Type Toggle */}
          <div>
            <label className="block text-xs font-bold text-[#102B4E] uppercase tracking-wider mb-2">
              Registration Category
            </label>
            <div className="grid grid-cols-2 gap-2 p-1 bg-[#F4F8FC] border border-[#DCE5EE] rounded-2xl">
              <button
                type="button"
                onClick={() => setRegisterType("citizen")}
                className={`py-2 px-3 rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition-all ${
                  registerType === "citizen"
                    ? "bg-white text-[#087F78] shadow-xs border border-[#DCE5EE]"
                    : "text-[#40536B] hover:text-[#102B4E]"
                }`}
              >
                <UserCheck className="w-4 h-4" />
                <span>Citizen</span>
              </button>
              <button
                type="button"
                onClick={() => setRegisterType("worker")}
                className={`py-2 px-3 rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition-all ${
                  registerType === "worker"
                    ? "bg-white text-sky-700 shadow-xs border border-[#DCE5EE]"
                    : "text-[#40536B] hover:text-[#102B4E]"
                }`}
              >
                <Wrench className="w-4 h-4" />
                <span>Field Worker</span>
              </button>
            </div>
            {registerType === "worker" && (
              <p className="text-[11px] text-amber-700 mt-2 bg-amber-50 p-2.5 rounded-xl border border-amber-200">
                Notice: Worker registrations require verification and approval by your Gram Panchayat PDO before access is granted.
              </p>
            )}
          </div>

          {errorMessage && (
            <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-900 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form className="space-y-4" onSubmit={handleRegister}>
            <div>
              <label className="block text-xs font-bold text-[#102B4E] uppercase tracking-wider mb-1">
                Full Name
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  required
                  placeholder={registerType === "citizen" ? "e.g. Ananya Patel" : "e.g. Ramesh Kumar"}
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full pl-10 pr-3.5 py-2.5 text-sm border border-[#DCE5EE] rounded-xl focus:ring-2 focus:ring-[#087F78] focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-[#102B4E] uppercase tracking-wider mb-1">
                Mobile Number
              </label>
              <div className="relative">
                <Phone className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="tel"
                  required
                  placeholder="10-digit mobile number"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  className="w-full pl-10 pr-3.5 py-2.5 text-sm border border-[#DCE5EE] rounded-xl focus:ring-2 focus:ring-[#087F78] focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-[#102B4E] uppercase tracking-wider mb-1">
                Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  placeholder={registerType === "citizen" ? "citizen@example.com" : "worker@fixproof.org"}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10 pr-3.5 py-2.5 text-sm border border-[#DCE5EE] rounded-xl focus:ring-2 focus:ring-[#087F78] focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-[#102B4E] uppercase tracking-wider mb-1">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  required
                  placeholder="At least 6 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-3.5 py-2.5 text-sm border border-[#DCE5EE] rounded-xl focus:ring-2 focus:ring-[#087F78] focus:outline-none"
                />
              </div>
            </div>

            {registerType === "worker" && (
              <div>
                <label className="block text-xs font-bold text-[#102B4E] uppercase tracking-wider mb-1">
                  Gram Panchayat / Village Jurisdiction
                </label>
                <div className="relative">
                  <Building2 className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <select
                    value={villageId}
                    onChange={(e) => {
                      setVillageId(e.target.value);
                      const found = villages.find((v) => v.id === e.target.value);
                      if (found) setVillageName(found.name);
                    }}
                    className="w-full pl-10 pr-3.5 py-2.5 text-sm border border-[#DCE5EE] rounded-xl focus:ring-2 focus:ring-[#087F78] focus:outline-none bg-white"
                  >
                    {villages.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full h-11 flex justify-center items-center gap-2 rounded-xl bg-[#087F78] hover:bg-[#066B65] text-white font-semibold text-sm shadow-xs transition-all active:scale-[0.99] disabled:opacity-60 mt-2"
            >
              <UserPlus className="w-4 h-4" />
              <span>
                {isSubmitting
                  ? "Submitting Registration..."
                  : registerType === "citizen"
                  ? "Register as Citizen"
                  : "Submit Worker Application"}
              </span>
            </button>
          </form>

          <div className="pt-4 text-center text-xs text-[#40536B] border-t border-[#DCE5EE]">
            Already have an account?{" "}
            <Link
              href={`/${locale}/login`}
              className="font-bold text-[#087F78] hover:underline"
            >
              Sign in with your role
            </Link>{" "}
            or{" "}
            <Link href={`/${locale}`} className="text-slate-600 hover:underline">
              return to home
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
