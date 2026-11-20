import React from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { unstable_setRequestLocale as setRequestLocale } from "next-intl/server";
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
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { WasteManagementSection } from "@/components/ui/WasteManagementSection";

interface HomePageProps {
  params: { locale: string };
}

export default function HomePage({ params: { locale } }: HomePageProps) {
  setRequestLocale(locale);
  const tLanding = useTranslations("landing");
  const tCat = useTranslations("categories");

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
      {/* 1. Hero Section — Modern Split Layout with Village Background */}
      <section className="relative overflow-hidden bg-[#F4F8FC] border-b border-[#DCE5EE] pt-8 pb-12 sm:pt-12 sm:pb-16 lg:pt-16 lg:pb-20">
        {/* Subtle Decorative Village Civic Background Illustration */}
        <div className="absolute inset-0 pointer-events-none select-none overflow-hidden opacity-35" aria-hidden="true">
          <svg
            className="w-full h-full object-cover"
            viewBox="0 0 1440 480"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            preserveAspectRatio="none"
          >
            {/* Distant Hills */}
            <path
              d="M0 340 C 240 280, 480 360, 720 310 C 960 260, 1200 340, 1440 290 L 1440 480 L 0 480 Z"
              fill="#E2EDF8"
            />
            {/* Midground Village Outlines */}
            <path
              d="M0 380 C 280 330, 560 410, 840 360 C 1120 310, 1320 380, 1440 350 L 1440 480 L 0 480 Z"
              fill="#D4E4F4"
            />
            {/* Distant Trees & Huts Silhouette */}
            <g opacity="0.35" fill="#B9D5EE">
              {/* Hut 1 */}
              <polygon points="120,360 145,335 170,360" />
              <rect x="130" y="360" width="30" height="20" />
              {/* Tree 1 */}
              <circle cx="210" cy="350" r="18" />
              <rect x="207" y="360" width="6" height="20" fill="#A8C9E8" />
              {/* Hut 2 */}
              <polygon points="1120,335 1145,310 1170,335" />
              <rect x="1130" y="335" width="30" height="25" />
              {/* Tree 2 */}
              <circle cx="1210" cy="320" r="22" />
              <rect x="1207" y="335" width="6" height="25" fill="#A8C9E8" />
            </g>
          </svg>
        </div>

        {/* Subtle Micro-Dot Overlay */}
        <div
          className="absolute inset-0 opacity-[0.03] pointer-events-none"
          style={{
            backgroundImage: `radial-gradient(#102B4E 1px, transparent 1px)`,
            backgroundSize: "24px 24px",
          }}
          aria-hidden="true"
        />

        <div className="relative max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 xl:px-12">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 xl:gap-16 items-center">
            {/* Left Column (7 cols): Heading, Subtitle, Balanced CTAs */}
            <div className="lg:col-span-7 space-y-5 sm:space-y-6 text-left">
              {/* Hero Pilot Badge */}
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#087F78]/10 text-[#087F78] text-xs sm:text-sm font-semibold border border-[#087F78]/25 shadow-2xs">
                <ShieldCheck className="w-4 h-4 text-[#087F78]" aria-hidden="true" />
                <span>Village & Ward Civic Accountability Platform</span>
              </div>

              {/* Controlled Max-Width Heading */}
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#102B4E] tracking-tight leading-[1.18]">
                {tLanding("heroTitle") || "Report local issues. Track real fixes."}
              </h1>

              {/* Readable Description */}
              <p className="text-sm sm:text-base lg:text-lg text-[#40536B] leading-relaxed max-w-2xl">
                {tLanding("heroSubtitle") ||
                  "Report problems in your village, such as damaged roads, water supply issues, drainage overflows and streetlight failures. Every repair requires verified inspection before closure."}
              </p>

              {/* Two Main Uniform Balanced CTA Buttons */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-2 max-w-lg w-full">
                {/* Primary CTA: Report a Problem */}
                <Link href={`/${locale}/report`} className="flex-1">
                  <button
                    type="button"
                    className="w-full h-12 px-6 rounded-xl bg-[#087F78] hover:bg-[#066B65] text-white font-semibold text-sm sm:text-base flex items-center justify-center gap-2 shadow-xs hover:shadow-sm transition-all whitespace-nowrap min-h-touch active:scale-[0.99]"
                  >
                    <FilePlus className="w-4 h-4 shrink-0" aria-hidden="true" />
                    <span>Report a Problem</span>
                  </button>
                </Link>

                {/* Secondary CTA: Track a Report */}
                <Link href={`/${locale}/track`} className="flex-1">
                  <button
                    type="button"
                    className="w-full h-12 px-6 rounded-xl bg-white hover:bg-[#F4F8FC] text-[#102B4E] border border-[#DCE5EE] hover:border-[#102B4E]/30 font-semibold text-sm sm:text-base flex items-center justify-center gap-2 shadow-2xs transition-all whitespace-nowrap min-h-touch active:scale-[0.99]"
                  >
                    <Search className="w-4 h-4 shrink-0 text-[#087F78]" aria-hidden="true" />
                    <span>Track a Report</span>
                  </button>
                </Link>
              </div>

              {/* Secondary Dashboard Transparency Link */}
              <div className="pt-1">
                <Link
                  href={`/${locale}/public`}
                  className="inline-flex items-center text-xs sm:text-sm font-semibold text-[#40536B] hover:text-[#087F78] transition-colors group"
                >
                  <Eye className="w-4 h-4 mr-1.5 text-[#087F78] group-hover:scale-110 transition-transform" aria-hidden="true" />
                  <span>View Public Accountability Map & Statistics</span>
                  <ArrowRight className="w-3.5 h-3.5 ml-1 text-[#087F78] group-hover:translate-x-0.5 transition-transform" aria-hidden="true" />
                </Link>
              </div>

              {/* Three Civic Guarantee Badges */}
              <div className="pt-2 flex flex-wrap items-center gap-4 text-xs font-medium text-[#40536B] border-t border-[#DCE5EE]/70">
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" aria-hidden="true" />
                  <span>GPS-Verified Locations</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-[#087F78]" aria-hidden="true" />
                  <span>Assigned to Ward Teams</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-sky-600" aria-hidden="true" />
                  <span>Photographic Repair Proof</span>
                </div>
              </div>
            </div>

            {/* Right Column (5 cols): Curved Softly Rounded Frame with Authentic Photograph */}
            <div className="lg:col-span-5">
              <div className="relative rounded-2xl sm:rounded-3xl shadow-xl ring-1 ring-slate-200/90 overflow-hidden bg-white group">
                {/* Realistic Photograph of Sanitation Worker with Segregated Wet & Dry Bins */}
                <img
                  src="/sanitation-worker-bins.png"
                  alt="Indian village sanitation worker with segregated green wet-waste and blue dry-waste bins"
                  className="w-full h-[380px] sm:h-[440px] lg:h-[480px] xl:h-[520px] object-cover group-hover:scale-[1.02] transition-transform duration-500"
                  loading="eager"
                />

                {/* Subtle Gradient Vignette at Bottom */}
                <div className="absolute inset-0 bg-gradient-to-t from-[#102B4E]/80 via-transparent to-transparent pointer-events-none" />

                {/* Dignified Caption Badge Overlay */}
                <div className="absolute bottom-4 left-4 right-4 bg-white/95 backdrop-blur-md p-3.5 rounded-2xl border border-white/80 shadow-lg">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shrink-0 shadow-xs animate-pulse" />
                      <p className="text-xs font-bold text-[#102B4E]">Verified Civic Sanitation & Segregation</p>
                    </div>
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                      Active Pilot
                    </span>
                  </div>
                  <p className="text-[11px] text-[#40536B] mt-1 leading-snug">
                    Connecting village residents, ward sanitation teams, and verified cleanup inspections.
                  </p>
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
      <section className="py-14 sm:py-18 bg-white border-t border-[#DCE5EE]">
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
