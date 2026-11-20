"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import {
  User,
  LogIn,
  LogOut,
  UserPlus,
  ShieldAlert,
  ClipboardList,
  Wrench,
  Settings,
  ArrowRight,
  UserCheck,
  FileText,
} from "lucide-react";

interface AccountMenuProps {
  className?: string;
  variant?: "light" | "dark";
  onNavigate?: () => void;
}

export const AccountMenu: React.FC<AccountMenuProps> = ({
  className = "",
  variant = "light",
  onNavigate,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<any>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const locale = useLocale();
  const tNav = useTranslations("navigation");

  // Load user from localStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      try {
        const raw = localStorage.getItem("gramaseva_user");
        if (raw) {
          setCurrentUser(JSON.parse(raw));
        } else {
          setCurrentUser(null);
        }
      } catch {
        setCurrentUser(null);
      }
    }
  }, [isOpen]);

  const handleSignOut = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("gramaseva_token");
      localStorage.removeItem("access_token");
      localStorage.removeItem("gramaseva_user");
      setCurrentUser(null);
      setIsOpen(false);
      window.location.href = `/${locale}/login`;
    }
  };

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleLinkClick = () => {
    setIsOpen(false);
    if (onNavigate) onNavigate();
  };

  const portalLinks = [
    {
      href: `/${locale}/staff`,
      label: "Reviewer Queue",
      role: "Panchayat Reviewer",
      icon: <ClipboardList className="w-3.5 h-3.5 text-[#087F78]" />,
    },
    {
      href: `/${locale}/worker`,
      label: "Field Worker",
      role: "Task Workspace",
      icon: <Wrench className="w-3.5 h-3.5 text-[#102B4E]" />,
    },
    {
      href: `/${locale}/admin`,
      label: "Administration",
      role: "Wards & Overview",
      icon: <Settings className="w-3.5 h-3.5 text-slate-600" />,
    },
  ];

  const buttonStyles =
    variant === "dark"
      ? isOpen
        ? "bg-[#20B5A5]/20 text-[#20B5A5] border-[#20B5A5]/50 shadow-xs"
        : "bg-white/10 text-white hover:bg-white/15 hover:text-white border-white/20"
      : isOpen
      ? "bg-[#102B4E] text-white border-[#102B4E] shadow-xs"
      : "bg-white text-[#40536B] hover:text-[#102B4E] hover:bg-slate-50 border-[#DCE5EE]";

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      {/* Single Elegant User / Account Icon Button */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className={`w-9 h-9 sm:w-10 sm:h-10 rounded-xl flex items-center justify-center transition-all duration-150 border ${buttonStyles} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#20B5A5]`}
        aria-label="Account and Authentication Menu"
        aria-expanded={isOpen}
        aria-haspopup="menu"
      >
        <User className="w-4 h-4 sm:w-[18px] sm:h-[18px]" aria-hidden="true" />
      </button>

      {/* Account Dropdown Menu */}
      {isOpen && (
        <div
          role="menu"
          aria-label="Account actions"
          className="absolute right-0 mt-2 w-64 bg-white rounded-2xl shadow-xl border border-[#DCE5EE] p-2.5 z-50 animate-in fade-in zoom-in-95 duration-100 space-y-2"
        >
          {/* Header */}
          <div className="px-2.5 py-1.5 border-b border-[#DCE5EE]/70">
            {currentUser ? (
              <div>
                <p className="text-xs font-bold text-[#102B4E] truncate">{currentUser.full_name || "Signed In"}</p>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className="text-[10px] text-slate-500 truncate">{currentUser.email}</span>
                  <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-teal-100 text-[#087F78] uppercase">
                    {currentUser.roles?.[0]?.role || "citizen"}
                  </span>
                </div>
              </div>
            ) : (
              <div>
                <p className="text-xs font-bold text-[#102B4E]">Citizen & Staff Access</p>
                <p className="text-[11px] text-[#40536B]">GramaSeva Civic Services</p>
              </div>
            )}
          </div>

          {currentUser ? (
            /* Logged In Citizen Actions */
            <div className="space-y-1">
              <Link
                href={`/${locale}/my-reports`}
                onClick={handleLinkClick}
                role="menuitem"
                className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-semibold text-[#102B4E] hover:bg-[#F4F8FC] transition-colors"
              >
                <FileText className="w-4 h-4 text-[#087F78]" />
                <span>My Complaints & Tracking</span>
              </Link>

              <button
                type="button"
                onClick={handleSignOut}
                role="menuitem"
                className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-semibold text-rose-700 hover:bg-rose-50 transition-colors text-left"
              >
                <LogOut className="w-4 h-4 text-rose-600" />
                <span>Sign Out</span>
              </button>
            </div>
          ) : (
            /* Primary Citizen Actions: Sign In & Register */
            <div className="space-y-1">
              <Link
                href={`/${locale}/login`}
                onClick={handleLinkClick}
                role="menuitem"
                className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-semibold text-[#102B4E] hover:bg-[#F4F8FC] transition-colors"
              >
                <LogIn className="w-4 h-4 text-[#087F78]" />
                <span>{tNav("signIn")}</span>
              </Link>

              <Link
                href={`/${locale}/register`}
                onClick={handleLinkClick}
                role="menuitem"
                className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-semibold text-white bg-[#087F78] hover:bg-[#066B65] shadow-2xs transition-colors"
              >
                <UserPlus className="w-4 h-4 text-white" />
                <span>{tNav("register")}</span>
              </Link>
            </div>
          )}

          {/* Role Portals Shortcut for Officials & Testers */}
          <div className="pt-2 border-t border-[#DCE5EE]/70">
            <p className="px-2.5 text-[10px] font-bold uppercase tracking-wider text-[#40536B] mb-1.5">
              Authorized Role Portals
            </p>
            <div className="space-y-1">
              {portalLinks.map((portal) => (
                <Link
                  key={portal.href}
                  href={portal.href}
                  onClick={handleLinkClick}
                  role="menuitem"
                  className="flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs hover:bg-[#F4F8FC] transition-colors group"
                >
                  <div className="flex items-center gap-2">
                    {portal.icon}
                    <div>
                      <p className="font-semibold text-[#102B4E] group-hover:text-[#087F78] text-[11px]">
                        {portal.label}
                      </p>
                      <p className="text-[9px] text-[#40536B]">{portal.role}</p>
                    </div>
                  </div>
                  <ArrowRight className="w-3 h-3 text-slate-400 group-hover:text-[#087F78] transition-colors" />
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
