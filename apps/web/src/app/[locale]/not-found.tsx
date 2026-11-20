import React from "react";
import Link from "next/link";
import { defaultLocale } from "@/i18n";
import {
  FilePlus,
  Search,
  Eye,
  Home,
  HelpCircle,
} from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-[#F4F8FB] flex flex-col justify-center items-center px-4 py-16 sm:px-6 lg:px-8">
      <div className="max-w-md w-full text-center space-y-6">
        {/* GramaSeva Logo */}
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-[#0B2545] shadow-xs">
          <svg viewBox="0 0 32 32" fill="none" className="w-8 h-8" aria-hidden="true">
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

        {/* 404 Header */}
        <div className="space-y-2">
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-[#0F766E]/10 text-[#0F766E]">
            HTTP 404 Error
          </span>
          <h1 className="text-4xl sm:text-5xl font-extrabold text-[#0B2545] tracking-tight">
            Page Not Found
          </h1>
          <p className="text-sm sm:text-base text-slate-600 max-w-sm mx-auto leading-relaxed">
            The civic page, complaint record, or URL you requested could not be located.
          </p>
        </div>

        {/* Quick Navigation Action Grid */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-xs space-y-3 text-left">
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
            Available Civic Portals
          </p>

          <Link
            href={`/${defaultLocale}`}
            className="flex items-center justify-between p-3 rounded-xl border border-slate-200 hover:border-[#0F766E]/50 hover:bg-[#F4F8FB] transition-all group"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-[#0B2545]/10 text-[#0B2545] flex items-center justify-center">
                <Home className="w-4 h-4" />
              </div>
              <div>
                <p className="text-sm font-bold text-[#0B2545] group-hover:text-[#0F766E]">
                  GramaSeva Homepage
                </p>
                <p className="text-xs text-slate-500">Return to main civic pilot portal</p>
              </div>
            </div>
          </Link>

          <Link
            href={`/${defaultLocale}/report`}
            className="flex items-center justify-between p-3 rounded-xl border border-slate-200 hover:border-[#0F766E]/50 hover:bg-[#F4F8FB] transition-all group"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-[#0F766E]/10 text-[#0F766E] flex items-center justify-center">
                <FilePlus className="w-4 h-4" />
              </div>
              <div>
                <p className="text-sm font-bold text-[#0B2545] group-hover:text-[#0F766E]">
                  Report a Problem
                </p>
                <p className="text-xs text-slate-500">Submit damaged road or water leak</p>
              </div>
            </div>
          </Link>

          <Link
            href={`/${defaultLocale}/track`}
            className="flex items-center justify-between p-3 rounded-xl border border-slate-200 hover:border-[#0F766E]/50 hover:bg-[#F4F8FB] transition-all group"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-sky-100 text-sky-700 flex items-center justify-center">
                <Search className="w-4 h-4" />
              </div>
              <div>
                <p className="text-sm font-bold text-[#0B2545] group-hover:text-[#0F766E]">
                  Track a Report
                </p>
                <p className="text-xs text-slate-500">Look up submission status</p>
              </div>
            </div>
          </Link>

          <Link
            href={`/${defaultLocale}/public`}
            className="flex items-center justify-between p-3 rounded-xl border border-slate-200 hover:border-[#0F766E]/50 hover:bg-[#F4F8FB] transition-all group"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center">
                <Eye className="w-4 h-4" />
              </div>
              <div>
                <p className="text-sm font-bold text-[#0B2545] group-hover:text-[#0F766E]">
                  Public Dashboard
                </p>
                <p className="text-xs text-slate-500">View ward transparency map</p>
              </div>
            </div>
          </Link>
        </div>

        {/* Prototype notice reminder */}
        <p className="text-xs text-slate-500 flex items-center justify-center gap-1.5">
          <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
          <span>GramaSeva Demonstration Prototype</span>
        </p>
      </div>
    </div>
  );
}
