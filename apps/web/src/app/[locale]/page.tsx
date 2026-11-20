import React from "react";
import Link from "next/link";
import Image from "next/image";
import { getTranslations, unstable_setRequestLocale as setRequestLocale } from "next-intl/server";
import {
  FilePlus,
  Search,
  Eye,
  CheckCircle2,
  Camera,
  Layers,
  ShieldCheck,
  Building2,
  Droplets,
  Trash2,
  Lightbulb,
  Dam,
  Construction,
  ArrowRight,
  MapPin,
  Sparkles,
  Users,
  FileText,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { WasteManagementSection } from "@/components/ui/WasteManagementSection";

interface HomePageProps {
  params: { locale: string };
}

async function getHeroStats() {
  try {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const res = await fetch(`${apiBase}/api/v1/public/analytics`, {
      next: { revalidate: 30 },
      signal: AbortSignal.timeout(2000),
    });
    if (res.ok) {
      const data = await res.json();
      return {
        totalIssues: data.total_unique_issues ?? 0,
        resolvedIssues: data.resolved_issues ?? 0,
        villagesCovered: (data.village_metrics && data.village_metrics.length) || 9,
      };
    }
  } catch {
    // Return legitimate baseline for Belagavi Taluk
  }
  return {
    totalIssues: 0,
    resolvedIssues: 0,
    villagesCovered: 9,
  };
}

export default async function HomePage({ params: { locale } }: HomePageProps) {
  setRequestLocale(locale);
  const stats = await getHeroStats();
  const tLanding = await getTranslations({ locale, namespace: "landing" });
  const tCat = await getTranslations({ locale, namespace: "categories" });

  const categories = [
    {
      id: "road_damage",
      name: tCat("road_damage"),
      icon: <Construction className="w-5 h-5 text-[#087F78]" />,
      desc: "Potholes, cracks, and road surface damage",
    },
    {
      id: "water_leak",
      name: tCat("water_leak"),
      icon: <Droplets className="w-5 h-5 text-sky-600" />,
      desc: "Visible pipe leaks and drinking water supply issues",
    },
    {
      id: "garbage",
      name: tCat("garbage"),
      icon: <Trash2 className="w-5 h-5 text-amber-600" />,
      desc: "Overflowing bins, litter, and uncollected waste",
    },
    {
      id: "drainage",
      name: tCat("drainage"),
      icon: <Dam className="w-5 h-5 text-emerald-600" />,
      desc: "Blocked culverts, drains, and road waterlogging",
    },
    {
      id: "streetlight",
      name: tCat("streetlight"),
      icon: <Lightbulb className="w-5 h-5 text-yellow-600" />,
      desc: "Non-functioning, dark, or broken streetlight poles",
    },
    {
      id: "public_facility",
      name: tCat("public_facility"),
      icon: <Building2 className="w-5 h-5 text-[#102B4E]" />,
      desc: "Community hall, bus stop, or sanitation facility damage",
    },
  ];

  return (
    <div className="flex flex-col min-h-screen bg-[#F4F8FC]">
      {/* 1. Master Full-Width Hero Section matching Approved Reference */}
      <section className="relative w-full overflow-hidden bg-white border-b border-[#DCE5EE] min-h-[580px] lg:min-h-[660px] xl:min-h-[720px] flex flex-col justify-between">
        {/* Full-Bleed Photograph on Desktop (Occupies right and center of hero) */}
        <div className="hidden lg:block absolute inset-y-0 right-0 w-[58%] xl:w-[62%] h-full pointer-events-none select-none z-0">
          <Image
            src="/images/gramaseva-hero-farmer.png"
            alt="Indian male farmer holding smartphone and photographing road potholes with automated detection markers"
            fill
            priority
            sizes="(min-width: 1024px) 62vw, 100vw"
            className="object-cover object-[center_35%]"
          />
          {/* Smooth White Gradient Overlay fading from left into photo */}
          <div className="absolute inset-0 bg-gradient-to-r from-white via-white/80 via-25% to-transparent w-[45%]" />
          {/* Subtle Top & Bottom Vignettes for integration */}
          <div className="absolute inset-x-0 top-0 h-12 bg-gradient-to-b from-white/30 to-transparent" />
          <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-white/40 to-transparent" />
        </div>

        {/* Foreground Content Container with flush left alignment */}
        <div className="relative z-10 w-full max-w-[1536px] mx-auto pl-3 sm:pl-5 lg:pl-8 pr-4 sm:pr-6 lg:pr-8 pt-8 sm:pt-12 lg:pt-14 pb-8 sm:pb-12 flex-1 flex flex-col justify-between">
          <div className="max-w-xl lg:max-w-2xl space-y-5 sm:space-y-6 text-left">
            {/* Small Badge */}
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#00A99D]/10 text-[#00A99D] text-xs sm:text-sm font-bold border border-[#00A99D]/25 shadow-2xs">
              <ShieldCheck className="w-4 h-4 text-[#00A99D]" aria-hidden="true" />
              <span>Village & Ward Civic Accountability Platform</span>
            </div>

            {/* Main Heading */}
            <h1 className="text-3xl sm:text-4xl lg:text-5xl xl:text-6xl font-black text-[#062B46] tracking-tight leading-[1.12]">
              Report local issues.<br className="hidden sm:inline" />
              Track real fixes.
            </h1>

            {/* Description */}
            <p className="text-sm sm:text-base lg:text-lg text-[#40536B] leading-relaxed max-w-xl">
              Report civic problems in your village or ward. Our system verifies, tracks, and ensures real resolution with complete transparency.
            </p>

            {/* Primary & Secondary Action Buttons */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3.5 pt-1 max-w-md w-full">
              {/* Primary CTA: Report a Problem */}
              <Link href={`/${locale}/report`} className="flex-1">
                <button
                  type="button"
                  className="w-full h-12 px-6 rounded-xl bg-[#00A99D] hover:bg-[#008f85] text-white font-bold text-sm sm:text-base flex items-center justify-center gap-2.5 shadow-sm hover:shadow transition-all whitespace-nowrap min-h-touch active:scale-[0.99]"
                >
                  <FilePlus className="w-5 h-5 shrink-0" aria-hidden="true" />
                  <span>Report a Problem</span>
                </button>
              </Link>

              {/* Secondary CTA: Track a Report */}
              <Link href={`/${locale}/track`} className="flex-1">
                <button
                  type="button"
                  className="w-full h-12 px-6 rounded-xl bg-white hover:bg-[#F5F8FC] text-[#062B46] border border-[#DCE5EE] hover:border-[#062B46]/30 font-bold text-sm sm:text-base flex items-center justify-center gap-2.5 shadow-2xs transition-all whitespace-nowrap min-h-touch active:scale-[0.99]"
                >
                  <Search className="w-5 h-5 shrink-0 text-[#00A99D]" aria-hidden="true" />
                  <span>Track a Report</span>
                </button>
              </Link>
            </div>

            {/* Mobile Hero Image Presentation (Visible on mobile/tablet below lg) */}
            <div className="lg:hidden mt-4 mb-3 rounded-2xl overflow-hidden shadow-lg ring-1 ring-slate-200/90 bg-white">
              <Image
                src="/images/gramaseva-hero-farmer.png"
                alt="Indian male farmer holding smartphone and photographing road potholes"
                width={1300}
                height={1008}
                priority
                className="w-full h-[260px] sm:h-[340px] object-cover object-center"
              />
            </div>

            {/* 4 Supporting Feature Points */}
            <div className="pt-2 space-y-2 sm:space-y-2.5 text-xs sm:text-sm font-bold text-[#062B46]">
              <div className="flex items-center gap-2.5">
                <div className="w-5 h-5 rounded-full bg-[#00A99D]/15 flex items-center justify-center shrink-0">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#00A99D]" aria-hidden="true" />
                </div>
                <span>GPS-Verified Locations</span>
              </div>
              <div className="flex items-center gap-2.5">
                <div className="w-5 h-5 rounded-full bg-[#00A99D]/15 flex items-center justify-center shrink-0">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#00A99D]" aria-hidden="true" />
                </div>
                <span>Photographic Proof</span>
              </div>
              <div className="flex items-center gap-2.5">
                <div className="w-5 h-5 rounded-full bg-[#00A99D]/15 flex items-center justify-center shrink-0">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#00A99D]" aria-hidden="true" />
                </div>
                <span>Verified Resolutions</span>
              </div>
              <div className="flex items-center gap-2.5">
                <div className="w-5 h-5 rounded-full bg-[#00A99D]/15 flex items-center justify-center shrink-0">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#00A99D]" aria-hidden="true" />
                </div>
                <span>Transparent to All</span>
              </div>
            </div>
          </div>

          {/* Floating White Statistics Panel near Bottom */}
          <div className="mt-8 lg:mt-12 bg-white/95 backdrop-blur-md rounded-2xl border border-[#DCE5EE] shadow-md p-4 sm:p-5 max-w-xl lg:max-w-2xl xl:max-w-3xl">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 divide-y sm:divide-y-0 sm:divide-x divide-[#DCE5EE]">
              {/* Stat 1: Issues Reported */}
              <div className="flex items-center gap-3 pt-2.5 sm:pt-0 sm:px-2">
                <div className="w-10 h-10 rounded-xl bg-[#00A99D]/10 border border-[#00A99D]/20 flex items-center justify-center shrink-0">
                  <FileText className="w-5 h-5 text-[#00A99D]" />
                </div>
                <div>
                  <div className="text-lg sm:text-xl font-black text-[#062B46]">
                    {stats.totalIssues.toLocaleString()}
                  </div>
                  <div className="text-[11px] font-semibold text-[#40536B]">Issues Reported</div>
                </div>
              </div>

              {/* Stat 2: Resolved */}
              <div className="flex items-center gap-3 pt-2.5 sm:pt-0 sm:px-2">
                <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-500/20 flex items-center justify-center shrink-0">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                </div>
                <div>
                  <div className="text-lg sm:text-xl font-black text-[#062B46]">
                    {stats.resolvedIssues.toLocaleString()}
                  </div>
                  <div className="text-[11px] font-semibold text-[#40536B]">Resolved</div>
                </div>
              </div>

              {/* Stat 3: Villages Covered */}
              <div className="flex items-center gap-3 pt-2.5 sm:pt-0 sm:px-2">
                <div className="w-10 h-10 rounded-xl bg-sky-50 border border-sky-500/20 flex items-center justify-center shrink-0">
                  <Users className="w-5 h-5 text-sky-600" />
                </div>
                <div>
                  <div className="text-lg sm:text-xl font-black text-[#062B46]">
                    {stats.villagesCovered}
                  </div>
                  <div className="text-[11px] font-semibold text-[#40536B]">Villages Covered</div>
                </div>
              </div>

              {/* Stat 4: Transparent */}
              <div className="flex items-center gap-3 pt-2.5 sm:pt-0 sm:px-2">
                <div className="w-10 h-10 rounded-xl bg-[#00A99D]/10 border border-[#00A99D]/20 flex items-center justify-center shrink-0">
                  <ShieldCheck className="w-5 h-5 text-[#00A99D]" />
                </div>
                <div>
                  <div className="text-lg sm:text-xl font-black text-[#062B46]">100%</div>
                  <div className="text-[11px] font-semibold text-[#40536B]">Transparent & Audited</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. Waste Management & Civic Cleanliness Section (Replaces lower 4 generic cards) */}
      <WasteManagementSection />

      {/* 3. Problem Categories Grid */}
      <section className="py-14 sm:py-18 bg-[#F4F8FC]">
        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 xl:px-12">
          <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 sm:mb-10">
            <div>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#087F78]/10 text-[#087F78] mb-2 border border-[#087F78]/20">
                Civic Categories
              </span>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-[#102B4E]">
                What would you like to report?
              </h2>
              <p className="text-[#40536B] mt-1 text-sm sm:text-base">
                Select an infrastructure problem category to start reporting with photographic proof.
              </p>
            </div>
            <Link
              href={`/${locale}/report`}
              className="mt-4 md:mt-0 inline-flex items-center text-sm font-bold text-[#087F78] hover:text-[#066B65] transition-colors"
            >
              Start general report <ArrowRight className="w-4 h-4 ml-1" />
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {categories.map((cat) => (
              <Link
                key={cat.id}
                href={`/${locale}/report?category=${cat.id}`}
                className="group focus:outline-none"
              >
                <Card
                  hoverEffect
                  className="h-full bg-white border border-[#DCE5EE] hover:border-[#087F78]/60 hover:shadow-sm transition-all p-5 rounded-2xl"
                >
                  <div className="flex items-start gap-4">
                    <div className="p-3 rounded-xl bg-[#F4F8FC] border border-[#DCE5EE] group-hover:bg-[#087F78]/10 group-hover:border-[#087F78]/30 transition-colors">
                      {cat.icon}
                    </div>
                    <div className="flex-1">
                      <h3 className="font-bold text-[#102B4E] text-base group-hover:text-[#087F78] transition-colors">
                        {cat.name}
                      </h3>
                      <p className="text-xs sm:text-sm text-[#40536B] mt-1 leading-relaxed">
                        {cat.desc}
                      </p>
                    </div>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* 4. How It Works Section */}
      <section id="how-it-works" className="py-14 sm:py-18 bg-white border-t border-[#DCE5EE]">
        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 xl:px-12">
          <div className="text-center max-w-2xl mx-auto mb-10 sm:mb-12 space-y-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#102B4E]/10 text-[#102B4E] border border-[#102B4E]/20">
              Audit Process
            </span>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-[#102B4E]">
              {tLanding("howItWorksTitle") || "How GramaSeva Works"}
            </h2>
            <p className="text-[#40536B] text-sm sm:text-base">
              From first citizen report to independently reviewed resolution — every step is verified.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {/* Step 1 */}
            <Card className="p-5 bg-[#F4F8FC] border border-[#DCE5EE] rounded-2xl shadow-2xs">
              <div className="w-10 h-10 rounded-xl bg-[#087F78]/15 text-[#087F78] flex items-center justify-center font-bold text-lg mb-4">
                <Camera className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-[#102B4E] text-base mb-1.5">
                {tLanding("step1Title") || "1. Report with Photo"}
              </h3>
              <p className="text-xs sm:text-sm text-[#40536B] leading-relaxed">
                {tLanding("step1Desc") ||
                  "Upload a photo of damaged roads, water leaks, or waste. Select your village or pin the location on the map."}
              </p>
            </Card>

            {/* Step 2 */}
            <Card className="p-5 bg-[#F4F8FC] border border-[#DCE5EE] rounded-2xl shadow-2xs">
              <div className="w-10 h-10 rounded-xl bg-amber-100 text-amber-800 flex items-center justify-center font-bold text-lg mb-4">
                <Layers className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-[#102B4E] text-base mb-1.5">
                {tLanding("step2Title") || "2. Triage & Assignment"}
              </h3>
              <p className="text-xs sm:text-sm text-[#40536B] leading-relaxed">
                {tLanding("step2Desc") ||
                  "Panchayat reviewers inspect the issue with AI advisory checks, assign priority, and route to the field team."}
              </p>
            </Card>

            {/* Step 3 */}
            <Card className="p-5 bg-[#F4F8FC] border border-[#DCE5EE] rounded-2xl shadow-2xs">
              <div className="w-10 h-10 rounded-xl bg-[#102B4E]/10 text-[#102B4E] flex items-center justify-center font-bold text-lg mb-4">
                <Construction className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-[#102B4E] text-base mb-1.5">
                {tLanding("step3Title") || "3. Work & Repair Proof"}
              </h3>
              <p className="text-xs sm:text-sm text-[#40536B] leading-relaxed">
                {tLanding("step3Desc") ||
                  "Field workers carry out the physical repair and upload verified photo evidence along with current GPS coordinates."}
              </p>
            </Card>

            {/* Step 4 */}
            <Card className="p-5 bg-emerald-50/40 border border-emerald-200 rounded-2xl shadow-2xs">
              <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold text-lg mb-4">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-[#102B4E] text-base mb-1.5">
                {tLanding("step4Title") || "4. Verified Closure"}
              </h3>
              <p className="text-xs sm:text-sm text-[#40536B] leading-relaxed">
                {tLanding("step4Desc") ||
                  "An authorized official independently confirms the before/after photos before the issue is marked 'Resolved'."}
              </p>
            </Card>
          </div>
        </div>
      </section>
    </div>
  );
}
