"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { ShieldAlert, HeartHandshake } from "lucide-react";

export const Footer: React.FC = () => {
  const locale = useLocale();
  const tNav = useTranslations("navigation");
  const tLanding = useTranslations("landing");
  const tNotices = useTranslations("notices");
  const pathname = usePathname();

  // Remove public footer from authenticated dashboards
  const isDashboard = /^\/[a-z]{2}\/(admin|pdo|staff|worker|citizen|my-reports|track)(\/.*)?$/.test(pathname);
  if (isDashboard) {
    return null;
  }

  return (
    <footer className="bg-slate-900 text-slate-300 border-t border-slate-800 mt-auto">
      {/* Notice Banner */}
      <div className="bg-slate-950 py-3 px-4 sm:px-6 lg:px-8 xl:px-12 border-b border-slate-800 text-xs text-slate-400">
        <div className="max-w-[1440px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-center sm:text-left">
          <div className="flex items-center gap-2 text-amber-400 font-medium">
            <ShieldAlert className="w-4 h-4 shrink-0" aria-hidden="true" />
            <span>{tLanding("disclaimer")}</span>
          </div>
          <p className="text-slate-400">{tNotices("privacyGuaranteed")}</p>
        </div>
      </div>

      <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-10">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand info */}
          <div className="md:col-span-2 space-y-3">
            <div className="flex items-center gap-2 text-white font-bold text-xl tracking-tight">
              <div className="w-7 h-7 rounded-lg bg-[#0B2545] border border-teal-500/40 flex items-center justify-center shrink-0">
                <svg viewBox="0 0 32 32" fill="none" className="w-4 h-4" aria-hidden="true">
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
              <span className="text-white">Grama<span className="text-teal-400">Seva</span></span>
            </div>
            <p className="text-sm text-slate-400 max-w-md leading-relaxed">
              {tLanding("heroSubtitle")}
            </p>
            <div className="flex items-center gap-2 pt-2 text-xs text-slate-500">
              <HeartHandshake className="w-4 h-4 text-emerald-400" />
              <span>Village-first civic technology pilot for Gram Panchayats and municipal wards.</span>
            </div>
          </div>

          {/* Quick links */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              {tNav("brand")}
            </h4>
            <ul className="space-y-1.5 text-xs text-slate-400">
              <li>
                <Link href={`/${locale}`} className="hover:text-white transition-colors">
                  {tNav("home")}
                </Link>
              </li>
              <li>
                <Link href={`/${locale}#about`} className="hover:text-white transition-colors">
                  {tNav("about")}
                </Link>
              </li>
              <li>
                <Link href={`/${locale}#how-it-works`} className="hover:text-white transition-colors">
                  {tNav("howItWorks")}
                </Link>
              </li>
              <li>
                <Link href={`/${locale}/public`} className="hover:text-white transition-colors">
                  {tNav("publicDashboard")}
                </Link>
              </li>
            </ul>
          </div>

          {/* Portals & Legal */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Civic Governance
            </h4>
            <ul className="space-y-1.5 text-xs text-slate-400">
              <li>
                <Link href={`/${locale}/login`} className="hover:text-white transition-colors">
                  Role Sign In
                </Link>
              </li>
              <li>
                <Link href={`/${locale}/register`} className="hover:text-white transition-colors">
                  Citizen & Worker Registration
                </Link>
              </li>
              <li>
                <span className="text-slate-500">Verified Photo Evidence Protocol</span>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-slate-800 text-xs text-slate-500 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p>&copy; 2026 GramaSeva Civic Systems. Public Sector Initiative for Rural Karnataka.</p>
          <div className="flex items-center gap-4">
            <span className="hover:text-slate-400 cursor-pointer">Security & Privacy</span>
            <span className="hover:text-slate-400 cursor-pointer">Panchayat Portal SLA</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
