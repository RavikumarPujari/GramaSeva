"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import {
  Menu,
  X,
  Languages,
  ShieldCheck,
  FilePlus,
  Search,
  Eye,
  ClipboardList,
  Wrench,
  Settings,
} from "lucide-react";
import { locales, localeNames, type Locale } from "@/i18n";

export const Navbar: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const locale = useLocale() as Locale;
  const tNav = useTranslations("navigation");
  const tCommon = useTranslations("common");
  const pathname = usePathname();
  const router = useRouter();

  // Function to switch locale while preserving current path
  const handleLocaleChange = (newLocale: Locale) => {
    if (newLocale === locale) return;
    const segments = pathname.split("/");
    segments[1] = newLocale;
    const newPath = segments.join("/") || `/${newLocale}`;
    router.push(newPath);
  };

  const navLinks = [
    { href: `/${locale}`, label: tNav("home"), icon: null },
    { href: `/${locale}/report`, label: tNav("report"), icon: <FilePlus className="w-4 h-4 mr-1.5" /> },
    { href: `/${locale}/my-reports`, label: tNav("myReports"), icon: <Search className="w-4 h-4 mr-1.5" /> },
    { href: `/${locale}/public`, label: tNav("publicDashboard"), icon: <Eye className="w-4 h-4 mr-1.5" /> },
  ];

  const portalLinks = [
    { href: `/${locale}/staff`, label: tNav("staffPortal"), icon: <ClipboardList className="w-4 h-4 mr-1.5" /> },
    { href: `/${locale}/worker`, label: tNav("workerPortal"), icon: <Wrench className="w-4 h-4 mr-1.5" /> },
    { href: `/${locale}/admin`, label: tNav("adminPortal"), icon: <Settings className="w-4 h-4 mr-1.5" /> },
  ];

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <Link
              href={`/${locale}`}
              className="flex items-center gap-2 font-bold text-slate-900 tracking-tight text-xl focus:outline-none"
            >
              <div className="w-9 h-9 rounded-lg bg-civic-600 flex items-center justify-center text-white shadow-sm">
                <ShieldCheck className="w-5 h-5" aria-hidden="true" />
              </div>
              <span className="text-slate-900">Fix<span className="text-civic-600">Proof</span></span>
            </Link>
            <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 text-emerald-800 border border-emerald-200">
              {tCommon("pilotBadge")}
            </span>
          </div>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center space-x-1 lg:space-x-2">
            {navLinks.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`inline-flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-civic-50 text-civic-700 font-semibold"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                  }`}
                >
                  {link.icon}
                  {link.label}
                </Link>
              );
            })}

            {/* Portals Dropdown / Separator */}
            <div className="h-5 w-px bg-slate-200 mx-1" aria-hidden="true" />

            {portalLinks.map((link) => {
              const isActive = pathname.startsWith(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`inline-flex items-center px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    isActive
                      ? "bg-slate-200 text-slate-900 font-semibold"
                      : "text-slate-500 hover:text-slate-800 hover:bg-slate-100"
                  }`}
                >
                  {link.icon}
                  {link.label}
                </Link>
              );
            })}
          </nav>

          {/* Language Selector */}
          <div className="flex items-center gap-2">
            <div className="relative inline-flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200">
              <Languages className="w-4 h-4 text-slate-500 ml-2 mr-1 shrink-0" aria-hidden="true" />
              {locales.map((l) => (
                <button
                  key={l}
                  type="button"
                  onClick={() => handleLocaleChange(l)}
                  aria-pressed={locale === l}
                  className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all ${
                    locale === l
                      ? "bg-white text-civic-700 shadow-sm font-bold"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  {localeNames[l]}
                </button>
              ))}
            </div>

            {/* Mobile menu button */}
            <button
              onClick={() => setIsOpen(!isOpen)}
              type="button"
              className="md:hidden inline-flex items-center justify-center p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 focus:outline-none min-h-touch min-w-touch"
              aria-controls="mobile-menu"
              aria-expanded={isOpen}
            >
              <span className="sr-only">Open main menu</span>
              {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {isOpen && (
        <div className="md:hidden border-b border-slate-200 bg-white px-4 pt-2 pb-4 space-y-1 shadow-lg" id="mobile-menu">
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setIsOpen(false)}
                className={`flex items-center px-3 py-2.5 rounded-lg text-base font-medium min-h-touch ${
                  isActive
                    ? "bg-civic-50 text-civic-700 font-semibold"
                    : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                {link.icon}
                {link.label}
              </Link>
            );
          })}

          <div className="pt-2 pb-1 border-t border-slate-100">
            <p className="px-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Staff & Administration
            </p>
          </div>

          {portalLinks.map((link) => {
            const isActive = pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setIsOpen(false)}
                className={`flex items-center px-3 py-2 rounded-lg text-sm font-medium min-h-touch ${
                  isActive
                    ? "bg-slate-100 text-slate-900 font-semibold"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                {link.icon}
                {link.label}
              </Link>
            );
          })}
        </div>
      )}
    </header>
  );
};
