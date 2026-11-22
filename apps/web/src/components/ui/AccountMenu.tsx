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
  RefreshCw,
} from "lucide-react";
import { apiClient } from "@/lib/api-client";

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
  const [connectingPortal, setConnectingPortal] = useState<string | null>(null);
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

  const handleRolePortalClick = async (e: React.MouseEvent, portalLabel: string, href: string) => {
    e.preventDefault();
    setConnectingPortal(portalLabel);
    try {
      const endpoint =
        portalLabel === "Super Admin"
          ? "/auth/dev-admin-session"
          : portalLabel === "Field Worker"
          ? "/auth/dev-worker-session"
          : portalLabel === "Citizen Dashboard"
          ? "/auth/dev-citizen-session"
          : "/auth/dev-pdo-session";

      const res = await apiClient.post<any>(endpoint);
      if (res && res.access_token) {
        localStorage.setItem("gramaseva_token", res.access_token);
        localStorage.setItem("access_token", res.access_token);
        if (res.profile) {
          localStorage.setItem("gramaseva_user", JSON.stringify(res.profile));
          setCurrentUser(res.profile);
        }
      }
      setIsOpen(false);
      if (onNavigate) onNavigate();
      window.location.href = href;
    } catch (err) {
      console.warn("Dev session establishment error:", err);
      setIsOpen(false);
      if (onNavigate) onNavigate();
      window.location.href = href;
    } finally {
      setConnectingPortal(null);
    }
  };

  const portalLinks = [
    {
      href: `/${locale}/admin`,
      label: "Super Admin",
      subtitle: "State & District",
      icon: <ShieldAlert className="w-4 h-4 text-[#102B4E] group-hover:text-[#087F78] transition-colors" />,
    },
    {
      href: `/${locale}/pdo`,
      label: "Village PDO",
      subtitle: "Gram Panchayat Operations",
      icon: <ClipboardList className="w-4 h-4 text-[#087F78] group-hover:text-[#087F78] transition-colors" />,
    },
    {
      href: `/${locale}/worker`,
      label: "Field Worker",
      subtitle: "Assigned Work Orders",
      icon: <Wrench className="w-4 h-4 text-sky-700 group-hover:text-[#087F78] transition-colors" />,
    },
    {
      href: `/${locale}/citizen`,
      label: "Citizen Dashboard",
      subtitle: "My Submissions & History",
      icon: <UserCheck className="w-4 h-4 text-amber-700 group-hover:text-[#087F78] transition-colors" />,
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
        title="Account & Access (Role Portals, Sign In & Register)"
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
          className="absolute right-0 mt-2 w-72 sm:w-80 max-w-[calc(100vw-1.5rem)] bg-white rounded-2xl shadow-xl border border-[#DCE5EE] p-2.5 z-50 animate-in fade-in zoom-in-95 duration-100 space-y-1"
        >
          {/* Section 1: AUTHORIZED ROLE PORTALS (Mandatory Order: 1. Super Admin, 2. Village PDO, 3. Field Worker, 4. Citizen Dashboard) */}
          <div className="px-2.5 pt-1 pb-1.5">
            <p className="text-[10px] font-extrabold uppercase tracking-wider text-[#40536B]">
              Authorized Role Portals
            </p>
          </div>

          <div className="space-y-0.5">
            {portalLinks.map((portal) => {
              const isConnecting = connectingPortal === portal.label;
              return (
                <Link
                  key={portal.href}
                  href={portal.href}
                  onClick={(e) => handleRolePortalClick(e, portal.label, portal.href)}
                  role="menuitem"
                  className="flex items-center justify-between px-2.5 py-2 rounded-xl hover:bg-[#F4F8FC] group transition-all"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="w-7 h-7 rounded-lg bg-slate-50 border border-slate-200/60 flex items-center justify-center shrink-0 group-hover:border-teal-200 group-hover:bg-teal-50/50 transition-colors">
                      {isConnecting ? (
                        <RefreshCw className="w-4 h-4 text-[#087F78] animate-spin" />
                      ) : (
                        portal.icon
                      )}
                    </div>
                    <div className="truncate text-left">
                      <p className="font-bold text-[#102B4E] group-hover:text-[#087F78] text-xs transition-colors truncate">
                        {portal.label}
                      </p>
                      <p className="text-[10px] text-[#40536B] truncate">
                        {isConnecting ? `Connecting demo ${portal.label}...` : portal.subtitle}
                      </p>
                    </div>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-[#087F78] group-hover:translate-x-0.5 transition-all shrink-0 ml-2" />
                </Link>
              );
            })}
          </div>

          {/* Subtle Divider */}
          <div className="my-1.5 border-t border-[#DCE5EE]" />

          {/* Section 2: AUTHENTICATION ACTIONS (Mandatory Order: 5. Sign In, 6. Register) */}
          <div className="px-2.5 pt-1 pb-1">
            <p className="text-[10px] font-extrabold uppercase tracking-wider text-[#40536B]">
              Authentication Actions
            </p>
          </div>

          <div className="space-y-1">
            {/* 5. Sign In */}
            <Link
              href={`/${locale}/login`}
              onClick={handleLinkClick}
              role="menuitem"
              className="flex items-center justify-between px-2.5 py-2 rounded-xl text-xs font-semibold text-[#102B4E] hover:bg-[#F4F8FC] group transition-all"
            >
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-slate-50 border border-slate-200/60 flex items-center justify-center shrink-0 group-hover:border-teal-200 group-hover:bg-teal-50/50 transition-colors">
                  <LogIn className="w-4 h-4 text-[#087F78]" />
                </div>
                <div className="text-left">
                  <p className="font-bold text-[#102B4E] group-hover:text-[#087F78] text-xs transition-colors">
                    {tNav("signIn")}
                  </p>
                  <p className="text-[10px] text-[#40536B]">Access your authorized account</p>
                </div>
              </div>
              <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-[#087F78] group-hover:translate-x-0.5 transition-all" />
            </Link>

            {/* 6. Register */}
            <Link
              href={`/${locale}/register`}
              onClick={handleLinkClick}
              role="menuitem"
              className="flex items-center justify-between px-2.5 py-2 rounded-xl text-xs font-semibold text-white bg-[#087F78] hover:bg-[#066B65] shadow-xs group transition-all"
            >
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-white/20 flex items-center justify-center shrink-0">
                  <UserPlus className="w-4 h-4 text-white" />
                </div>
                <div className="text-left">
                  <p className="font-bold text-white text-xs">
                    {tNav("register")}
                  </p>
                  <p className="text-[10px] text-teal-100">Create new citizen account</p>
                </div>
              </div>
              <ArrowRight className="w-3.5 h-3.5 text-teal-100 group-hover:translate-x-0.5 transition-all" />
            </Link>
          </div>

          {/* Active Session Management (If Signed In) */}
          {currentUser && (
            <div className="pt-2 mt-1 border-t border-[#DCE5EE]">
              <div className="p-2 rounded-xl bg-slate-50 flex items-center justify-between gap-2">
                <div className="truncate text-left text-xs">
                  <p className="font-bold text-[#102B4E] truncate">
                    {currentUser.full_name || "Active Session"}
                  </p>
                  <p className="text-[10px] text-slate-500 truncate">
                    {currentUser.email}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleSignOut}
                  className="px-2.5 py-1 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 text-[11px] font-bold border border-rose-200 transition-colors shrink-0 flex items-center gap-1"
                >
                  <LogOut className="w-3 h-3 text-rose-600" />
                  <span>Exit</span>
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
