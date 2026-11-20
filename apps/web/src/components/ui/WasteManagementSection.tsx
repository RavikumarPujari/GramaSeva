"use client";

import React from "react";
import Link from "next/link";
import { useLocale } from "next-intl";
import {
  Trash2,
  Recycle,
  CheckCircle2,
  MapPin,
  Building2,
  ShieldCheck,
  Lock,
  ArrowRight,
  Sparkles,
} from "lucide-react";

export const WasteManagementSection: React.FC = () => {
  const locale = useLocale();

  return (
    <section id="about" className="py-14 sm:py-18 lg:py-20 bg-white border-t border-b border-[#DCE5EE]">
      <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 space-y-12">
        {/* Main Cleanliness & Waste Management Feature Block */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 xl:gap-16 items-center">
          {/* Left Text & Information Points (7 cols) */}
          <div className="lg:col-span-7 space-y-6">
            <div className="space-y-3">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#087F78]/10 text-[#087F78] border border-[#087F78]/20">
                <Recycle className="w-3.5 h-3.5 text-[#087F78]" aria-hidden="true" />
                <span>Civic Cleanliness & Sanitation</span>
              </div>
              <h2 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-[#102B4E] tracking-tight leading-[1.2]">
                Cleaner villages start with better reporting
              </h2>
              <p className="text-sm sm:text-base text-[#40536B] leading-relaxed max-w-2xl">
                Help keep our villages clean and healthy. Report overflowing bins, missed waste collection, illegal dumping and blocked drains. Your reports help local authorities identify problems and track progress.
              </p>
            </div>

            {/* Three Information Points */}
            <div className="space-y-3.5 pt-1 max-w-2xl">
              {/* Point 1 */}
              <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-[#F4F8FC] border border-[#DCE5EE] transition-colors">
                <div className="w-9 h-9 rounded-lg bg-[#087F78]/15 text-[#087F78] flex items-center justify-center shrink-0 mt-0.5 font-bold">
                  <MapPin className="w-5 h-5 text-[#087F78]" aria-hidden="true" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-[#102B4E]">
                    Report Waste Hotspots
                  </h3>
                  <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                    Tell us where waste problems need attention.
                  </p>
                </div>
              </div>

              {/* Point 2 */}
              <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-[#F4F8FC] border border-[#DCE5EE] transition-colors">
                <div className="w-9 h-9 rounded-lg bg-emerald-100 text-emerald-800 flex items-center justify-center shrink-0 mt-0.5 font-bold">
                  <Recycle className="w-5 h-5 text-emerald-700" aria-hidden="true" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-[#102B4E]">
                    Encourage Wet & Dry Segregation
                  </h3>
                  <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                    Separate biodegradable and recyclable waste.
                  </p>
                </div>
              </div>

              {/* Point 3 */}
              <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-[#F4F8FC] border border-[#DCE5EE] transition-colors">
                <div className="w-9 h-9 rounded-lg bg-blue-100 text-blue-800 flex items-center justify-center shrink-0 mt-0.5 font-bold">
                  <CheckCircle2 className="w-5 h-5 text-blue-700" aria-hidden="true" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-[#102B4E]">
                    Track Collection and Cleanup
                  </h3>
                  <p className="text-xs sm:text-sm text-[#40536B] mt-0.5">
                    See reported issues and verified progress.
                  </p>
                </div>
              </div>
            </div>

            {/* Quick Action Button */}
            <div className="pt-2">
              <Link
                href={`/${locale}/report?category=garbage`}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#087F78] hover:bg-[#066B65] text-white text-xs sm:text-sm font-semibold shadow-2xs transition-colors"
              >
                <Trash2 className="w-4 h-4" aria-hidden="true" />
                <span>Report a Cleanliness or Waste Problem</span>
                <ArrowRight className="w-4 h-4 ml-1" aria-hidden="true" />
              </Link>
            </div>
          </div>

          {/* Right Image Container (5 cols): Second Homepage Photograph */}
          <div className="lg:col-span-5">
            <div className="relative rounded-2xl sm:rounded-3xl overflow-hidden border border-[#DCE5EE] bg-slate-100 shadow-md group">
              {/* Realistic Photograph of Village Civic Supervisor, Elders, Youth & Completed Infrastructure */}
              <img
                src="/village-community-infrastructure.png"
                alt="Indian village civic supervisor with tablet alongside community elders and youth on a repaired village street with clean drainage and solar streetlight"
                className="w-full h-[360px] sm:h-[420px] lg:h-[460px] object-cover group-hover:scale-[1.02] transition-transform duration-500"
                loading="lazy"
              />

              {/* Dignified Caption Overlay */}
              <div className="absolute bottom-3 left-3 right-3 sm:bottom-4 sm:left-4 sm:right-4 bg-white/95 backdrop-blur-md p-3.5 rounded-2xl border border-[#DCE5EE] shadow-md">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-bold text-[#102B4E] flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block shrink-0 shadow-xs animate-pulse" />
                    Community-Verified Ward Infrastructure
                  </p>
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                    Verified Fix
                  </span>
                </div>
                <p className="text-[11px] text-[#40536B] mt-1 leading-snug">
                  Village elders, youth, and panchayat supervisors verifying newly completed works on-site.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Below: Three Concise Core Feature Points */}
        <div className="pt-6 border-t border-[#DCE5EE]/80 grid grid-cols-1 md:grid-cols-3 gap-5">
          {/* Feature 1 */}
          <div className="bg-[#F4F8FC] p-5 rounded-2xl border border-[#DCE5EE] flex items-start gap-4 transition-all">
            <div className="w-10 h-10 rounded-xl bg-[#102B4E]/10 text-[#102B4E] flex items-center justify-center shrink-0 mt-0.5">
              <Building2 className="w-5 h-5 text-[#102B4E]" aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-[#102B4E]">
                Village & Ward Coverage
              </h3>
              <p className="text-xs text-[#40536B] mt-1 leading-relaxed">
                Supporting accountable local governance.
              </p>
            </div>
          </div>

          {/* Feature 2 */}
          <div className="bg-[#F4F8FC] p-5 rounded-2xl border border-[#DCE5EE] flex items-start gap-4 transition-all">
            <div className="w-10 h-10 rounded-xl bg-[#087F78]/10 text-[#087F78] flex items-center justify-center shrink-0 mt-0.5">
              <ShieldCheck className="w-5 h-5 text-[#087F78]" aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-[#102B4E]">
                Human-Reviewed Resolutions
              </h3>
              <p className="text-xs text-[#40536B] mt-1 leading-relaxed">
                Reports are reviewed by authorized officials.
              </p>
            </div>
          </div>

          {/* Feature 3 */}
          <div className="bg-[#F4F8FC] p-5 rounded-2xl border border-[#DCE5EE] flex items-start gap-4 transition-all">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-700 flex items-center justify-center shrink-0 mt-0.5">
              <Lock className="w-5 h-5 text-indigo-700" aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-[#102B4E]">
                Privacy-Conscious Reporting
              </h3>
              <p className="text-xs text-[#40536B] mt-1 leading-relaxed">
                Only necessary information is collected and protected.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
