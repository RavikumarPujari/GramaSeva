"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Menu, X } from "lucide-react";
import { GramaSevaLogo } from "@/components/ui/GramaSevaLogo";
import { LanguageSelector } from "@/components/ui/LanguageSelector";
import { AccountMenu } from "@/components/ui/AccountMenu";
import type { Locale } from "@/i18n";

export const Navbar: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const locale = useLocale() as Locale;
  const tNav = useTranslations("navigation");
  const pathname = usePathname();

  // Remove public navigation from authenticated dashboards
  const isDashboard = /^\/[a-z]{2}\/(admin|pdo|staff|worker|citizen|my-reports|track)(\/.*)?$/.test(pathname);
  if (isDashboard) {
    return null;
  }

  // Public homepage navigation: Home, About, How It Works, Public Dashboard
  const navLinks = [
    { href: `/${locale}`, label: tNav("home") },
    { href: `/${locale}#about`, label: tNav("about") },
    { href: `/${locale}#how-it-works`, label: tNav("howItWorks") },
    { href: `/${locale}/public`, label: tNav("publicDashboard") },
  ];

  return (
    <header className="sticky top-0 z-40 bg-[#062B46] border-b border-[#05243C] shadow-md">
      <div className="w-full max-w-[1536px] mx-auto pl-3 sm:pl-5 lg:pl-8 pr-4 sm:pr-6 lg:pr-8">
        <div className="flex items-center justify-between h-16 gap-4">
          {/* Left: Reusable GramaSeva Logo with zero extra left indent */}
          <div className="flex items-center shrink-0 pl-0">
            <GramaSevaLogo size="md" inverted={true} />
          </div>

          {/* Middle Navigation — Centered Four Main Items */}
          <nav
            className="hidden md:flex items-center justify-center flex-1 space-x-1 lg:space-x-3 px-2"
            aria-label="Main Navigation"
          >
            {navLinks.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`inline-flex items-center px-4 py-1.5 text-xs lg:text-sm font-semibold transition-all duration-150 whitespace-nowrap rounded-lg ${
                    isActive
                      ? "bg-[#00A99D] text-white font-bold shadow-xs"
                      : "text-white/85 hover:text-white hover:bg-white/10"
                  }`}
                >
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Right Side: Language Selector, Account/Profile Menu & Mobile Toggle */}
          <div className="flex items-center gap-2 sm:gap-2.5 shrink-0">
            {/* Single Globe Icon Dropdown */}
            <LanguageSelector variant="dark" />

            {/* Account / Profile Icon Dropdown (Contains Sign In, Register & Portals) */}
            <AccountMenu variant="dark" />

            {/* Mobile Hamburger Button (visible only below md breakpoint) */}
            <button
              type="button"
              onClick={() => setMobileMenuOpen((prev) => !prev)}
              className="md:hidden w-9 h-9 sm:w-10 sm:h-10 rounded-xl flex items-center justify-center text-white hover:bg-white/10 border border-white/20 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00A99D]"
              aria-label="Toggle navigation menu"
              aria-expanded={mobileMenuOpen}
            >
              {mobileMenuOpen ? <X className="w-5 h-5 text-white" /> : <Menu className="w-5 h-5 text-white" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer Navigation */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-white/10 bg-[#062B46] px-4 pt-3 pb-5 space-y-2 shadow-xl animate-in fade-in slide-in-from-top-2 duration-150">
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
                      ? "bg-[#00A99D] text-white font-bold"
                      : "text-white/85 hover:bg-white/10 hover:text-white"
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
