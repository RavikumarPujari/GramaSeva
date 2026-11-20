"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import {
  ShieldAlert,
  Building2,
  Wrench,
  UserCheck,
  LogIn,
  ArrowRight,
  AlertCircle,
  Clock,
  CheckCircle2,
  Lock,
  Mail,
  KeyRound,
  RotateCcw,
} from "lucide-react";
import { apiClient, ApiError } from "@/lib/api-client";
import { Alert } from "@/components/ui/Alert";
import { GramaSevaLogo } from "@/components/ui/GramaSevaLogo";

type RoleKey = "super_admin" | "village_pdo" | "worker" | "citizen";

interface RoleConfig {
  id: RoleKey;
  label: string;
  badge: string;
  description: string;
  icon: React.ElementType;
  colorScheme: {
    activeBorder: string;
    activeBg: string;
    iconBg: string;
    iconColor: string;
    badgeBg: string;
    badgeText: string;
  };
  demoEmail: string;
  demoPassword: string;
  destination: string;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
  profile: {
    id: string;
    email: string;
    full_name: string;
    preferred_locale: string;
    roles: Array<{
      role: string;
      jurisdiction_unit_id?: string;
      jurisdiction_name?: string;
      approval_status?: string;
      is_primary?: boolean;
    }>;
    is_approved: boolean;
    approval_status: string;
  };
}

export default function LoginPage() {
  const locale = useLocale();
  const tNav = useTranslations("navigation");
  const router = useRouter();

  const [selectedRole, setSelectedRole] = useState<RoleKey>("super_admin");
  const [email, setEmail] = useState("admin@fixproof.org");
  const [password, setPassword] = useState("DemoPassword123!");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  
  // Pending worker state
  const [isPendingWorker, setIsPendingWorker] = useState(false);
  const [pendingWorkerProfile, setPendingWorkerProfile] = useState<any>(null);

  const roles: RoleConfig[] = [
    {
      id: "super_admin",
      label: "Super Admin",
      badge: "Belagavi Taluk",
      description: "Panchayat governance, PDO assignments, and system audit logs",
      icon: ShieldAlert,
      colorScheme: {
        activeBorder: "border-[#102B4E]",
        activeBg: "bg-[#102B4E]/5",
        iconBg: "bg-[#102B4E]/10",
        iconColor: "text-[#102B4E]",
        badgeBg: "bg-[#102B4E]/10",
        badgeText: "text-[#102B4E]",
      },
      demoEmail: "admin@fixproof.org",
      demoPassword: "DemoPassword123!",
      destination: `/${locale}/admin`,
    },
    {
      id: "village_pdo",
      label: "Village PDO",
      badge: "Gram Panchayat",
      description: "Primary operational hub: triage, worker assignment, and verification",
      icon: Building2,
      colorScheme: {
        activeBorder: "border-[#087F78]",
        activeBg: "bg-[#087F78]/5",
        iconBg: "bg-[#087F78]/10",
        iconColor: "text-[#087F78]",
        badgeBg: "bg-[#087F78]/10",
        badgeText: "text-[#087F78]",
      },
      demoEmail: "pdo.peeranwadi@belagavi.gov.in",
      demoPassword: "DemoPassword123!",
      destination: `/${locale}/pdo`,
    },
    {
      id: "worker",
      label: "Worker",
      badge: "Field Operations",
      description: "Execute assigned work orders and upload photographic evidence",
      icon: Wrench,
      colorScheme: {
        activeBorder: "border-sky-600",
        activeBg: "bg-sky-50",
        iconBg: "bg-sky-100",
        iconColor: "text-sky-700",
        badgeBg: "bg-sky-100",
        badgeText: "text-sky-800",
      },
      demoEmail: "worker.ramesh@fixproof.org",
      demoPassword: "DemoPassword123!",
      destination: `/${locale}/worker`,
    },
    {
      id: "citizen",
      label: "Citizen",
      badge: "Resident",
      description: "Report local issues and track real verified community fixes",
      icon: UserCheck,
      colorScheme: {
        activeBorder: "border-amber-600",
        activeBg: "bg-amber-50/60",
        iconBg: "bg-amber-100",
        iconColor: "text-amber-700",
        badgeBg: "bg-amber-100",
        badgeText: "text-amber-800",
      },
      demoEmail: "citizen.ananya@example.com",
      demoPassword: "DemoPassword123!",
      destination: `/${locale}/citizen`,
    },
  ];

  const handleSelectRole = (role: RoleConfig) => {
    setSelectedRole(role.id);
    setEmail(role.demoEmail);
    setPassword(role.demoPassword);
    setErrorMessage(null);
    setIsPendingWorker(false);
  };

  const handleSetPendingDemo = () => {
    setSelectedRole("worker");
    setEmail("pending.worker@fixproof.org");
    setPassword("DemoPassword123!");
    setErrorMessage(null);
  };

  const performLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMessage(null);
    setIsPendingWorker(false);

    try {
      const res = await apiClient.post<TokenResponse>("/auth/login", {
        email: email.trim(),
        password: password,
        selected_role: selectedRole,
      });

      if (res.access_token) {
        // Check if worker account is pending approval
        if (
          selectedRole === "worker" &&
          (res.profile.approval_status === "PENDING" || !res.profile.is_approved)
        ) {
          setIsPendingWorker(true);
          setPendingWorkerProfile(res.profile);
          localStorage.setItem("gramaseva_token", res.access_token);
          localStorage.setItem("access_token", res.access_token);
          localStorage.setItem("gramaseva_user", JSON.stringify(res.profile));
          return;
        }

        // Store tokens
        localStorage.setItem("gramaseva_token", res.access_token);
        localStorage.setItem("access_token", res.access_token);
        localStorage.setItem("gramaseva_user", JSON.stringify(res.profile));

        // Strict role-based destination routing
        const targetConfig = roles.find((r) => r.id === selectedRole);
        const destination = targetConfig ? targetConfig.destination : `/${locale}/citizen`;
        router.push(destination);
      }
    } catch (err: any) {
      if (err.status === 403) {
        // Detailed role mismatch or approval block
        if (
          err.message &&
          (err.message.toLowerCase().includes("pending") ||
            err.message.toLowerCase().includes("approval"))
        ) {
          setIsPendingWorker(true);
          setPendingWorkerProfile({ email, full_name: "Registered Worker" });
        } else {
          setErrorMessage(
            err.message ||
              `Access Denied: Your account is not authorized for the selected role (${selectedRole}). Please select your registered role.`
          );
        }
      } else if (err.status === 401) {
        setErrorMessage("Invalid credentials. Please verify your email and password.");
      } else {
        setErrorMessage(err.message || "Authentication failed. Please check your credentials.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  // If worker account is pending, render dedicated Account Pending Screen
  if (isPendingWorker) {
    return (
      <div className="min-h-screen bg-[#F4F8FC] flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
        <div className="sm:mx-auto sm:w-full sm:max-w-lg">
          <div className="flex justify-center mb-4">
            <GramaSevaLogo size="md" />
          </div>

          <div className="bg-white border-2 border-amber-300 rounded-3xl shadow-xl overflow-hidden">
            {/* Banner */}
            <div className="bg-amber-500/10 border-b border-amber-200 px-6 py-5 flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-amber-500/20 text-amber-800 flex items-center justify-center shrink-0">
                <Clock className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-amber-950">
                  Worker Account Pending PDO Approval
                </h2>
                <p className="text-xs text-amber-800">
                  Civic Governance Gate — Action Required by Gram Panchayat
                </p>
              </div>
            </div>

            {/* Content */}
            <div className="p-6 sm:p-8 space-y-5 text-sm">
              <p className="text-[#40536B] leading-relaxed">
                Thank you for registering as a GramaSeva Field Worker. Your account credentials have been verified, but your work authorization is currently{" "}
                <span className="font-bold text-amber-900 bg-amber-100 px-2 py-0.5 rounded">
                  PENDING APPROVAL
                </span>.
              </p>

              <div className="rounded-2xl bg-[#F4F8FC] border border-[#DCE5EE] p-4 space-y-2.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-[#40536B]">Registered Email:</span>
                  <span className="font-bold text-[#102B4E]">
                    {pendingWorkerProfile?.email || email}
                  </span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-[#40536B]">Worker Name:</span>
                  <span className="font-bold text-[#102B4E]">
                    {pendingWorkerProfile?.full_name || "Field Technician"}
                  </span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-[#40536B]">Approval Authority:</span>
                  <span className="font-bold text-[#087F78]">Village PDO (Panchayat Development Officer)</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-[#40536B]">Governance Rule:</span>
                  <span className="text-[#102B4E] font-medium">Workers cannot view or accept jobs until approved</span>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-blue-50 border border-blue-200 text-xs text-blue-900 leading-relaxed">
                <strong>What happens next?</strong> Your village PDO will inspect your trade skills and jurisdiction assignment in their PDO Dashboard. Once approved, you can log in immediately to receive assignments.
              </div>

              <div className="flex flex-col sm:flex-row gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => performLogin({ preventDefault: () => {} } as any)}
                  className="flex-1 h-11 px-4 rounded-xl bg-[#087F78] hover:bg-[#066B65] text-white font-semibold text-xs sm:text-sm flex items-center justify-center gap-2 shadow-2xs transition-all"
                >
                  <RotateCcw className="w-4 h-4" />
                  <span>Check Status Again</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsPendingWorker(false);
                    setSelectedRole("village_pdo");
                    setEmail("pdo.peeranwadi@belagavi.gov.in");
                    setPassword("DemoPassword123!");
                  }}
                  className="flex-1 h-11 px-4 rounded-xl bg-white hover:bg-slate-50 text-[#102B4E] border border-[#DCE5EE] font-semibold text-xs sm:text-sm flex items-center justify-center transition-all"
                >
                  <span>Switch Account / Sign In as PDO</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const currentRoleConfig = roles.find((r) => r.id === selectedRole)!;

  return (
    <div className="min-h-screen bg-[#F4F8FC] flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-2xl text-center">
        <div className="flex justify-center mb-4">
          <GramaSevaLogo size="lg" />
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-[#102B4E] tracking-tight">
          Sign In to GramaSeva
        </h1>
        <p className="mt-1.5 text-xs sm:text-sm text-[#40536B] max-w-md mx-auto">
          Select your authorized government civic role to access your dedicated dashboard.
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-2xl">
        <div className="bg-white py-8 px-6 sm:px-10 rounded-3xl shadow-sm border border-[#DCE5EE] space-y-6">
          {/* Step 1: Role Selection Cards */}
          <div>
            <label className="block text-xs font-bold text-[#102B4E] uppercase tracking-wider mb-2.5">
              Select Your Official Role
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {roles.map((role) => {
                const isSelected = selectedRole === role.id;
                const IconComponent = role.icon;
                return (
                  <button
                    key={role.id}
                    type="button"
                    onClick={() => handleSelectRole(role)}
                    className={`relative p-4 rounded-2xl border-2 text-left transition-all duration-150 flex flex-col justify-between ${
                      isSelected
                        ? `${role.colorScheme.activeBorder} ${role.colorScheme.activeBg} shadow-sm`
                        : "border-[#DCE5EE] hover:border-slate-300 bg-white"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2.5">
                        <div
                          className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${role.colorScheme.iconBg} ${role.colorScheme.iconColor}`}
                        >
                          <IconComponent className="w-5 h-5" />
                        </div>
                        <div>
                          <p className="font-bold text-sm text-[#102B4E]">{role.label}</p>
                          <span
                            className={`inline-block text-[10px] font-bold px-2 py-0.5 rounded-full ${role.colorScheme.badgeBg} ${role.colorScheme.badgeText}`}
                          >
                            {role.badge}
                          </span>
                        </div>
                      </div>
                      {isSelected && (
                        <span className="w-5 h-5 rounded-full bg-[#087F78] text-white flex items-center justify-center text-xs">
                          ✓
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-[#40536B] leading-snug">
                      {role.description}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Quick Demo Credentials Assistant */}
          <div className="p-3.5 rounded-2xl bg-[#F4F8FC] border border-[#DCE5EE] flex flex-wrap items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[#102B4E] font-semibold">
                Selected: <span className="text-[#087F78]">{currentRoleConfig.label}</span>
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => handleSelectRole(currentRoleConfig)}
                className="text-[11px] font-semibold text-[#087F78] hover:underline"
              >
                Auto-fill {currentRoleConfig.label} Demo
              </button>
              {selectedRole === "worker" && (
                <button
                  type="button"
                  onClick={handleSetPendingDemo}
                  className="text-[11px] font-semibold text-amber-700 hover:underline bg-amber-50 px-2 py-0.5 rounded border border-amber-200"
                >
                  Test Pending Worker
                </button>
              )}
            </div>
          </div>

          {/* Error Message */}
          {errorMessage && (
            <div className="p-4 rounded-2xl bg-red-50 border border-red-200 text-red-900 text-xs sm:text-sm flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-bold">Access Verification Error</p>
                <p className="leading-relaxed">{errorMessage}</p>
                <p className="text-[11px] text-red-700">
                  Note: In compliance with GramaSeva role-based security, accounts must be authenticated strictly against their authorized administrative role.
                </p>
              </div>
            </div>
          )}

          {/* Step 2: Login Form */}
          <form className="space-y-4" onSubmit={performLogin}>
            <div>
              <label className="block text-xs font-bold text-[#102B4E] uppercase tracking-wider mb-1">
                Official Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  placeholder="e.g. pdo.peeranwadi@belagavi.gov.in"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10 pr-3.5 py-2.5 text-sm border border-[#DCE5EE] rounded-xl focus:ring-2 focus:ring-[#087F78] focus:outline-none transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-[#102B4E] uppercase tracking-wider mb-1">
                Password
              </label>
              <div className="relative">
                <KeyRound className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  required
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-3.5 py-2.5 text-sm border border-[#DCE5EE] rounded-xl focus:ring-2 focus:ring-[#087F78] focus:outline-none transition-all"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full h-12 flex justify-center items-center gap-2 rounded-xl bg-[#087F78] hover:bg-[#066B65] text-white font-semibold text-sm shadow-xs transition-all active:scale-[0.99] disabled:opacity-60"
            >
              <LogIn className="w-4 h-4" />
              <span>{isLoading ? "Authenticating & Verifying Role..." : `Sign In as ${currentRoleConfig.label}`}</span>
            </button>
          </form>

          {/* Registration link */}
          <div className="pt-4 text-center text-xs text-[#40536B] border-t border-[#DCE5EE]">
            New to GramaSeva?{" "}
            <Link
              href={`/${locale}/register`}
              className="font-bold text-[#087F78] hover:underline"
            >
              Register as Citizen or Field Worker
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
