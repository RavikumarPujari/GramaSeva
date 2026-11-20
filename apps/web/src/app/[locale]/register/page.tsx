"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { UserPlus, ArrowRight } from "lucide-react";

export default function RegisterPage() {
  const locale = useLocale();
  const tNav = useTranslations("navigation");
  const router = useRouter();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [village, setVillage] = useState("Gowdanahalli");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleRegister = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setTimeout(() => {
      setIsSubmitting(false);
      router.push(`/${locale}/report`);
    }, 400);
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
          Citizen Registration
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          Join GramaSeva to report and track infrastructure fixes
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 shadow-sm border border-slate-200/90 rounded-2xl sm:px-10">
          <form className="space-y-4" onSubmit={handleRegister}>
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Full Name
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Ananya Patel"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-[#0F766E] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Mobile Number
              </label>
              <input
                type="tel"
                required
                placeholder="10-digit mobile number"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-[#0F766E] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Email Address (Optional)
              </label>
              <input
                type="email"
                placeholder="citizen@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-[#0F766E] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Village / Ward
              </label>
              <select
                value={village}
                onChange={(e) => setVillage(e.target.value)}
                className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-[#0F766E] focus:outline-none bg-white"
              >
                <option value="Gowdanahalli">Gowdanahalli Gram Panchayat</option>
                <option value="Malleshwarapuram">Malleshwarapuram Gram Panchayat</option>
                <option value="MandyaWard1">Mandya City Ward 1</option>
                <option value="MandyaWard2">Mandya City Ward 2</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full h-11 flex justify-center items-center gap-2 rounded-lg bg-[#0F766E] hover:bg-[#0D655E] text-white font-semibold text-sm shadow-xs transition-colors mt-2"
            >
              <UserPlus className="w-4 h-4" />
              <span>{isSubmitting ? "Creating account..." : "Register & Start"}</span>
            </button>
          </form>

          <div className="mt-6 pt-4 text-center text-xs text-slate-500 border-t border-slate-100">
            Already have an account?{" "}
            <Link
              href={`/${locale}/login`}
              className="font-bold text-[#0F766E] hover:underline"
            >
              Sign in here
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
