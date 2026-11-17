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
  MapPin,
  ShieldCheck,
  Building2,
  Droplets,
  Trash2,
  Lightbulb,
  Dam,
  Construction,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

interface HomePageProps {
  params: { locale: string };
}

export default function HomePage({ params: { locale } }: HomePageProps) {
  setRequestLocale(locale);
  const tLanding = useTranslations("landing");
  const tNav = useTranslations("navigation");
  const tCommon = useTranslations("common");
  const tCat = useTranslations("categories");

  const categories = [
    {
      id: "road_damage",
      name: tCat("road_damage"),
      icon: <Construction className="w-6 h-6 text-civic-600" />,
      desc: "Potholes, cracks, and surface damage",
    },
    {
      id: "water_leak",
      name: tCat("water_leak"),
      icon: <Droplets className="w-6 h-6 text-sky-600" />,
      desc: "Visible pipe leaks and drinking water overflow",
    },
    {
      id: "garbage",
      name: tCat("garbage"),
      icon: <Trash2 className="w-6 h-6 text-amber-600" />,
      desc: "Uncollected public waste and littering",
    },
    {
      id: "drainage",
      name: tCat("drainage"),
      icon: <Dam className="w-6 h-6 text-emerald-600" />,
      desc: "Blocked culverts, drains, and waterlogging",
    },
    {
      id: "streetlight",
      name: tCat("streetlight"),
      icon: <Lightbulb className="w-6 h-6 text-yellow-600" />,
      desc: "Non-functioning or broken public lighting",
    },
    {
      id: "public_facility",
      name: tCat("public_facility"),
      icon: <Building2 className="w-6 h-6 text-indigo-600" />,
      desc: "Community hall, bus stop, or toilet damage",
    },
  ];

  return (
    <div className="flex flex-col min-h-screen">
      {/* Hero Section */}
      <section className="bg-gradient-to-b from-civic-50/70 via-white to-slate-50 border-b border-slate-200 py-16 md:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-civic-100 text-civic-800 text-xs sm:text-sm font-semibold border border-civic-200">
              <ShieldCheck className="w-4 h-4 text-civic-600" />
              <span>Village & Ward Civic Accountability Pilot</span>
            </div>

            <h1 className="text-3xl sm:text-5xl md:text-6xl font-extrabold text-slate-900 tracking-tight leading-tight">
              {tLanding("heroTitle")}
            </h1>

            <p className="text-base sm:text-xl text-slate-600 leading-relaxed max-w-2xl mx-auto">
              {tLanding("heroSubtitle")}
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-4">
              <Link href={`/${locale}/report`} className="w-full sm:w-auto">
                <Button
                  size="lg"
                  variant="primary"
                  className="w-full sm:w-auto shadow-md"
                  leftIcon={<FilePlus className="w-5 h-5" />}
                >
                  {tLanding("reportButton")}
                </Button>
              </Link>
              <Link href={`/${locale}/my-reports`} className="w-full sm:w-auto">
                <Button
                  size="lg"
                  variant="secondary"
                  className="w-full sm:w-auto"
                  leftIcon={<Search className="w-5 h-5" />}
                >
                  {tLanding("trackButton")}
                </Button>
              </Link>
              <Link href={`/${locale}/public`} className="w-full sm:w-auto">
                <Button
                  size="lg"
                  variant="outline"
                  className="w-full sm:w-auto"
                  leftIcon={<Eye className="w-5 h-5" />}
                >
                  {tLanding("publicButton")}
                </Button>
              </Link>
            </div>

            {/* Quick trust metrics */}
            <div className="pt-10 grid grid-cols-2 md:grid-cols-4 gap-4 text-left">
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Pilot Scope
                </p>
                <p className="text-xl font-bold text-slate-900 mt-0.5">Village Wards</p>
                <p className="text-xs text-slate-500 mt-1">First-class administrative units</p>
              </div>

              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Resolution Rule
                </p>
                <p className="text-xl font-bold text-slate-900 mt-0.5">Independent Review</p>
                <p className="text-xs text-slate-500 mt-1">Workers cannot self-approve</p>
              </div>

              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Languages
                </p>
                <p className="text-xl font-bold text-slate-900 mt-0.5">EN · ಕನ್ನಡ · HI</p>
                <p className="text-xs text-slate-500 mt-1">Fully accessible in 3 languages</p>
              </div>

              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Citizen Privacy
                </p>
                <p className="text-xl font-bold text-slate-900 mt-0.5">Sanitized & Safe</p>
                <p className="text-xs text-slate-500 mt-1">Zero personal contacts exposed</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Categories Grid */}
      <section className="py-16 bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row md:items-end justify-between mb-10">
            <div>
              <Badge variant="info" size="sm" className="mb-2">
                Citizen Reporting
              </Badge>
              <h2 className="text-2xl sm:text-3xl font-bold text-slate-900">
                What would you like to report?
              </h2>
              <p className="text-slate-600 mt-1 text-sm sm:text-base">
                Select an infrastructure category to start with photographic evidence.
              </p>
            </div>
            <Link
              href={`/${locale}/report`}
              className="mt-4 md:mt-0 inline-flex items-center text-sm font-semibold text-civic-700 hover:text-civic-800"
            >
              Start general report <ArrowRight className="w-4 h-4 ml-1" />
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {categories.map((cat) => (
              <Link
                key={cat.id}
                href={`/${locale}/report?category=${cat.id}`}
                className="group focus:outline-none"
              >
                <Card
                  hoverEffect
                  className="h-full group-hover:border-civic-400 group-hover:shadow-md transition-all p-5"
                >
                  <div className="flex items-start gap-4">
                    <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 group-hover:bg-civic-50 group-hover:border-civic-200 transition-colors">
                      {cat.icon}
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-slate-900 text-base group-hover:text-civic-700 transition-colors">
                        {cat.name}
                      </h3>
                      <p className="text-sm text-slate-500 mt-1">{cat.desc}</p>
                    </div>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="py-16 bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-slate-900">
              {tLanding("howItWorksTitle")}
            </h2>
            <p className="text-slate-600 mt-2 text-sm sm:text-base">
              From first citizen report to independently reviewed resolution — every step is auditable.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {/* Step 1 */}
            <Card className="p-6 bg-white relative">
              <div className="w-10 h-10 rounded-lg bg-civic-100 text-civic-700 flex items-center justify-center font-bold text-lg mb-4">
                <Camera className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-slate-900 text-lg mb-2">
                {tLanding("step1Title")}
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                {tLanding("step1Desc")}
              </p>
            </Card>

            {/* Step 2 */}
            <Card className="p-6 bg-white relative">
              <div className="w-10 h-10 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center font-bold text-lg mb-4">
                <Layers className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-slate-900 text-lg mb-2">
                {tLanding("step2Title")}
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                {tLanding("step2Desc")}
              </p>
            </Card>

            {/* Step 3 */}
            <Card className="p-6 bg-white relative">
              <div className="w-10 h-10 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-lg mb-4">
                <Construction className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-slate-900 text-lg mb-2">
                {tLanding("step3Title")}
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                {tLanding("step3Desc")}
              </p>
            </Card>

            {/* Step 4 */}
            <Card className="p-6 bg-white relative border-emerald-200 bg-emerald-50/20">
              <div className="w-10 h-10 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-lg mb-4">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-slate-900 text-lg mb-2">
                {tLanding("step4Title")}
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                {tLanding("step4Desc")}
              </p>
            </Card>
          </div>
        </div>
      </section>
    </div>
  );
}
