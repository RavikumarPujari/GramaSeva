"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import {
  ShieldCheck,
  LogIn,
  ArrowRight,
  ClipboardList,
  Wrench,
  Settings,
  UserCheck,
  AlertCircle,
} from "lucide-react";
import { apiClient, ApiError } from "@/lib/api-client";
import { Alert } from "@/components/ui/Alert";

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
    }>;
  };
}

export default function LoginPage() {
  const locale = useLocale();
  const tNav = useTranslations("navigation");
  const router = useRouter();

  const [email, setEmail] = useState("citizen.ananya@example.com");
  const [password, setPassword] = useState("DemoPassword123!");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const demoAccounts = [
    {
      role: "Registered Citizen",
      email: "citizen.ananya@example.com",
      destination: `/${locale}/track`,
      icon: <UserCheck className="w-4 h-4 text-[#0F766E]" />,
    },
    {
      role: "Panchayat Reviewer",
      email: "reviewer.gowdanahalli@fixproof.org",
      destination: `/${locale}/staff`,
      icon: <ClipboardList className="w-4 h-4 text-[#0B2545]" />,
    },
    {
      role: "Field Worker",
      email: "worker.ramesh@fixproof.org",
      destination: `/${locale}/worker`,
      icon: <Wrench className="w-4 h-4 text-[#13315C]" />,
    },
    {
      role: "Ward Supervisor / Admin",
      email: "supervisor.mandya@fixproof.org",
      destination: `/${locale}/admin`,
      icon: <Settings className="w-4 h-4 text-slate-600" />,
    },
  ];

  const performLogin = async (loginEmail: string, loginPass: string) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await apiClient.post<TokenResponse>("/auth/login", {
        email: loginEmail,
        password: loginPass,
      });

      if (res.access_token) {
        localStorage.setItem("gramaseva_token", res.access_token);
        localStorage.setItem("access_token", res.access_token);
        localStorage.setItem("gramaseva_user", JSON.stringify(res.profile));

        // Determine destination by primary role
        const roles = res.profile.roles || [];
        const roleNames = roles.map((r) => r.role.toLowerCase());

        let target = `/${locale}/track`;
        if (roleNames.includes("admin") || roleNames.includes("supervisor")) {
          target = `/${locale}/admin`;
        } else if (roleNames.includes("reviewer") || roleNames.includes("staff")) {
          target = `/${locale}/staff`;
        } else if (roleNames.includes("worker")) {
          target = `/${locale}/worker`;
        } else {
          target = `/${locale}/my-reports`;
        }

        router.push(target);
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Invalid credentials. Please check your email and password.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    performLogin(email, password);
  };

  return (
    <div className="min-h-screen bg-[#F4F8FB] flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        {/* GramaSeva Logo */}
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[#0B2545] shadow-xs mb-3">
          <svg viewBox="0 0 32 32" fill="none" className="w-7 h-7" aria-hidden="true">
            <path
              d="M16 4L5 12V25C5 26.1046 5.89543 27 7 27H25C26.1046 27 27 26.1046 27 25V12L16 4Z"
              fill="#13315C"
            />
            <path
              d="M16 11C16 11 11.5 15.5 11.5 20C11.5 22.4853 13.5147 24.5 16 24.5C18.4853 24.5 20.5 22.4853 20.5 20C20.5 15.5 16 11 16 11Z"
              fill="#0F766E"
            />
            <circle cx="16" cy="18.5" r="2" fill="#F4F8FB" />
          </svg>
        </div>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-[#0B2545]">
          Sign in to GramaSeva
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          Civic Problem Reporting & Verified Resolution
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 shadow-sm border border-slate-200/90 rounded-2xl sm:px-10">
          {errorMessage && (
            <div className="mb-4">
              <Alert variant="danger" title="Authentication Failed">
                {errorMessage}
              </Alert>
            </div>
          )}

          <form className="space-y-4" onSubmit={handleLogin}>
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Email or Mobile Number
              </label>
              <input
                type="text"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-[#0F766E] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-[#0F766E] focus:outline-none"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full h-11 flex justify-center items-center gap-2 rounded-lg bg-[#0F766E] hover:bg-[#0D655E] text-white font-semibold text-sm shadow-xs transition-colors"
            >
              <LogIn className="w-4 h-4" />
              <span>{isLoading ? "Signing in..." : "Sign In"}</span>
            </button>
          </form>

          {/* Quick Demo Accounts */}
          <div className="mt-6 pt-6 border-t border-slate-200">
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
              One-Click Demo Portals (Real Backend Login)
            </p>
            <div className="space-y-2">
              {demoAccounts.map((account) => (
                <button
                  key={account.email}
                  type="button"
                  onClick={() => {
                    setEmail(account.email);
                    setPassword("DemoPassword123!");
                    performLogin(account.email, "DemoPassword123!");
                  }}
                  className="w-full flex items-center justify-between p-2.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-xs transition-colors text-left"
                >
                  <div className="flex items-center gap-2.5">
                    {account.icon}
                    <div>
                      <p className="font-bold text-[#0B2545]">{account.role}</p>
                      <p className="text-slate-500 text-[11px]">{account.email}</p>
                    </div>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                </button>
              ))}
            </div>
          </div>

          <div className="mt-6 pt-4 text-center text-xs text-slate-500 border-t border-slate-100">
            Don&apos;t have an account?{" "}
            <Link
              href={`/${locale}/register`}
              className="font-bold text-[#0F766E] hover:underline"
            >
              Register here
            </Link>{" "}
            or{" "}
            <Link href={`/${locale}`} className="text-slate-600 hover:underline">
              return home
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
