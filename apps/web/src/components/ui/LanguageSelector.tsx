"use client";

import React, { useState, useRef, useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useLocale } from "next-intl";
import { Globe, Check } from "lucide-react";
import { locales, localeNames, type Locale } from "@/i18n";

interface LanguageSelectorProps {
  className?: string;
  variant?: "light" | "dark";
}

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  className = "",
  variant = "light",
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const locale = useLocale() as Locale;
  const pathname = usePathname();
  const router = useRouter();

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

  // Switch locale while preserving current path
  const handleSelectLanguage = (newLocale: Locale) => {
    setIsOpen(false);
    if (newLocale === locale) return;
    const segments = pathname.split("/");
    segments[1] = newLocale;
    const newPath = segments.join("/") || `/${newLocale}`;
    router.push(newPath);
  };

  const buttonStyles =
    variant === "dark"
      ? isOpen
        ? "bg-[#20B5A5]/20 text-[#20B5A5] border-[#20B5A5]/50 shadow-xs"
        : "bg-white/10 text-white hover:bg-white/15 hover:text-white border-white/20"
      : isOpen
      ? "bg-[#087F78]/10 text-[#087F78] border-[#087F78]/30 shadow-xs"
      : "bg-white text-[#40536B] hover:text-[#102B4E] hover:bg-slate-50 border-[#DCE5EE]";

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      {/* Single Compact Globe / Translation Icon Button */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className={`w-9 h-9 sm:w-10 sm:h-10 rounded-xl flex items-center justify-center transition-all duration-150 border ${buttonStyles} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#20B5A5]`}
        aria-label="Select Language (English, ಕನ್ನಡ, हिन्दी)"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <Globe className="w-4 h-4 sm:w-[18px] sm:h-[18px]" aria-hidden="true" />
      </button>

      {/* Compact Dropdown Menu */}
      {isOpen && (
        <div
          role="listbox"
          aria-label="Language options"
          className="absolute right-0 mt-2 w-40 bg-white rounded-xl shadow-lg border border-[#DCE5EE] py-1.5 z-50 animate-in fade-in zoom-in-95 duration-100"
        >
          <div className="px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-[#40536B]/80 border-b border-[#DCE5EE]/60 mb-1">
            Language / ಭಾಷೆ
          </div>
          {locales.map((l) => {
            const isSelected = locale === l;
            return (
              <button
                key={l}
                role="option"
                aria-selected={isSelected}
                type="button"
                onClick={() => handleSelectLanguage(l)}
                className={`w-full px-3 py-2 text-xs font-semibold flex items-center justify-between transition-colors ${
                  isSelected
                    ? "bg-[#087F78]/10 text-[#087F78] font-bold"
                    : "text-[#102B4E] hover:bg-[#F4F8FC]"
                }`}
              >
                <span>{localeNames[l]}</span>
                {isSelected && <Check className="w-3.5 h-3.5 text-[#087F78]" aria-hidden="true" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
