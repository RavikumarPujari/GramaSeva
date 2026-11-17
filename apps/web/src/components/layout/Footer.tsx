import React from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { ShieldAlert, HeartHandshake } from "lucide-react";

export const Footer: React.FC = () => {
  const locale = useLocale();
  const tNav = useTranslations("navigation");
  const tLanding = useTranslations("landing");
  const tNotices = useTranslations("notices");

  return (
    <footer className="bg-slate-900 text-slate-300 border-t border-slate-800 mt-auto">
      {/* Notice Banner */}
      <div className="bg-slate-950 py-3 px-4 border-b border-slate-800 text-xs text-slate-400">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-center sm:text-left">
          <div className="flex items-center gap-2 text-amber-400 font-medium">
            <ShieldAlert className="w-4 h-4 shrink-0" aria-hidden="true" />
            <span>{tLanding("disclaimer")}</span>
          </div>
          <p className="text-slate-400">{tNotices("privacyGuaranteed")}</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand info */}
          <div className="md:col-span-2 space-y-3">
            <div className="flex items-center gap-2 text-white font-bold text-lg tracking-tight">
              <span className="text-white">Fix<span className="text-civic-400">Proof</span></span>
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
          <div>
            <h4 className="text-sm font-semibold text-white tracking-wider uppercase mb-3">
              Citizens
            </h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href={`/${locale}/report`} className="hover:text-white transition-colors">
                  {tNav("report")}
                </Link>
              </li>
              <li>
                <Link href={`/${locale}/my-reports`} className="hover:text-white transition-colors">
                  {tNav("myReports")}
                </Link>
              </li>
              <li>
                <Link href={`/${locale}/public`} className="hover:text-white transition-colors">
                  {tNav("publicDashboard")}
                </Link>
              </li>
            </ul>
          </div>

          {/* Governance & Staff */}
          <div>
            <h4 className="text-sm font-semibold text-white tracking-wider uppercase mb-3">
              Staff & Portals
            </h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href={`/${locale}/staff`} className="hover:text-white transition-colors">
                  {tNav("staffPortal")}
                </Link>
              </li>
              <li>
                <Link href={`/${locale}/worker`} className="hover:text-white transition-colors">
                  {tNav("workerPortal")}
                </Link>
              </li>
              <li>
                <Link href={`/${locale}/admin`} className="hover:text-white transition-colors">
                  {tNav("adminPortal")}
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="pt-8 mt-8 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-4">
          <p>© {new Date().getFullYear()} FixProof Civic Pilot. All rights reserved.</p>
          <p className="text-slate-400">{tNotices("advisoryAi")}</p>
        </div>
      </div>
    </footer>
  );
};
