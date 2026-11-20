"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Menu, X, Home, FilePlus, Search, Eye } from "lucide-react";
import { GramaSevaLogo } from "@/components/ui/GramaSevaLogo";
import { LanguageSelector } from "@/components/ui/LanguageSelector";
import { AccountMenu } from "@/components/ui/AccountMenu";
import type { Locale } from "@/i18n";

export const Navbar: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const locale = useLocale() as Locale;
  const tNav = useTranslations("navigation");
  const pathname = usePathname();

  // Exactly FOUR core centered navigation items as required
  const navLinks = [
    { href: `/${locale}`, label: tNav("home"), icon: <Home className="w-4 h-4 mr-1.5 opacity-80" /> },
    { href: `/${locale}/report`, label: tNav("report"), icon: <FilePlus className="w-4 h-4 mr-1.5 opacity-80" /> },
    { href: `/${locale}/track`, label: tNav("myReports"), icon: <Search className="w-4 h-4 mr-1.5 opacity-80" /> },
    { href: `/${locale}/public`, label: tNav("publicDashboard"), icon: <Eye className="w-4 h-4 mr-1.5 opacity-80" /> },
  ];

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-[#DCE5EE] shadow-2xs">
      <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 xl:px-12">
        <div className="flex items-center justify-between h-16">
          {/* Left: Reusable GramaSeva Logo */}
          <div className="flex items-center shrink-0">
            <GramaSevaLogo size="md" />
          </div>

          {/* Middle Navigation — Maximum FOUR Centered Items */}
          <nav
            className="hidden md:flex items-center space-x-1 lg:space-x-2"
            aria-label="Main Navigation"
          >
            {navLinks.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`relative inline-flex items-center px-3.5 py-2 text-xs lg:text-sm font-semibold transition-all duration-150 whitespace-nowrap rounded-lg ${
                    isActive
                      ? "text-[#087F78] font-bold bg-[#087F78]/8"
                      : "text-[#40536B] hover:text-[#102B4E] hover:bg-[#F4F8FC]"
                  }`}
                >
                  <span>{link.label}</span>
                  {isActive && (
                    <span className="absolute bottom-0 left-2 right-2 h-[2.5px] bg-[#087F78] rounded-full" />
                  )}
                </Link>
              );
            })}
          </nav>

          {/* Right Side: Language Icon & Account Icon */}
          <div className="hidden sm:flex items-center gap-2.5 shrink-0">
            {/* Single Globe Icon Dropdown */}
            <LanguageSelector />

            {/* Single Elegant Account Icon Dropdown */}
            <AccountMenu />
          </div>

          {/* Mobile Controls (below sm breakpoint) */}
          <div className="flex sm:hidden items-center gap-2">
            <LanguageSelector />
            <AccountMenu />
            <button
              type="button"
              onClick={() => setMobileMenuOpen((prev) => !prev)}
              className="w-9 h-9 rounded-xl flex items-center justify-center text-[#102B4E] hover:bg-slate-100 border border-[#DCE5EE] transition-colors focus:outline-none"
              aria-label="Toggle navigation menu"
              aria-expanded={mobileMenuOpen}
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer Navigation */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-[#DCE5EE] bg-white px-4 pt-3 pb-5 space-y-3 shadow-lg animate-in fade-in slide-in-from-top-2 duration-150">
          <div className="space-y-1">
            {navLinks.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-colors ${
                    isActive
                      ? "bg-[#087F78]/10 text-[#087F78] font-bold"
                      : "text-[#102B4E] hover:bg-[#F4F8FC]"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </header>
  );
};
