"use client";

import React from "react";
import Link from "next/link";
import { useLocale } from "next-intl";

interface GramaSevaLogoProps {
  className?: string;
  size?: "sm" | "md" | "lg";
  showSubtitle?: boolean;
  inverted?: boolean;
}

export const GramaSevaLogo: React.FC<GramaSevaLogoProps> = ({
  className = "",
  size = "md",
  showSubtitle = true,
  inverted = false,
}) => {
  const locale = useLocale();

  const iconSizes = {
    sm: "w-8 h-8",
    md: "w-9 h-9 sm:w-10 sm:h-10",
    lg: "w-11 h-11",
  };

  const textSizes = {
    sm: "text-lg",
    md: "text-xl sm:text-2xl",
    lg: "text-2xl sm:text-3xl",
  };

  const subTextSizes = {
    sm: "text-[8px]",
    md: "text-[9px] sm:text-[10px]",
    lg: "text-[11px]",
  };

  return (
    <Link
      href={`/${locale}`}
      className={`inline-flex items-center gap-2.5 sm:gap-3 group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#20B5A5] rounded-xl transition-transform active:scale-[0.99] select-none ${className}`}
      aria-label="GramaSeva — Civic Resolution Homepage"
    >
      {/* Redesigned Premium Civic Symbol Mark */}
      <div
        className={`${iconSizes[size]} rounded-xl ${
          inverted
            ? "bg-white/10 p-2 border border-white/20 group-hover:border-[#20B5A5]/60 shadow-xs"
            : "bg-gradient-to-br from-[#102B4E] to-[#0A1D36] p-2 border border-[#102B4E]/20 shadow-xs group-hover:shadow-sm"
        } flex items-center justify-center shrink-0 transition-all duration-200`}
      >
        <svg
          viewBox="0 0 36 36"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-full h-full"
          aria-hidden="true"
        >
          {/* Village Civic Community Shelter Roof */}
          <path
            d="M18 3L4 14V30C4 31.6569 5.34315 33 7 33H29C30.6569 33 32 31.6569 32 30V14L18 3Z"
            fill={inverted ? "#1A3D6B" : "#102B4E"}
            opacity="0.9"
          />
          {/* Architectural Gabled Eaves */}
          <path
            d="M18 5.2L6 14.8V29H30V14.8L18 5.2Z"
            stroke={inverted ? "#FFFFFF" : "#DCE5EE"}
            strokeWidth="1.2"
            strokeLinejoin="round"
          />
          {/* Civic Sprout / Growth Leaf in Vibrant Teal */}
          <path
            d="M18 10C18 10 11.5 16.5 11.5 22.5C11.5 26.0899 14.4101 29 18 29C21.5899 29 24.5 26.0899 24.5 22.5C24.5 16.5 18 10 18 10Z"
            fill={inverted ? "#20B5A5" : "#087F78"}
          />
          {/* Center Civic Resolution Keyhole / Node */}
          <circle cx="18" cy="20.5" r="3.2" fill="#FFFFFF" />
          <circle cx="18" cy="20.5" r="1.5" fill={inverted ? "#0D2545" : "#102B4E"} />
          {/* Upward Resolution Pillar */}
          <path
            d="M18 23.7V29"
            stroke="#FFFFFF"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
        </svg>
      </div>

      {/* Brand Typography */}
      <div className="flex flex-col">
        <span
          className={`${textSizes[size]} font-extrabold tracking-tight ${
            inverted ? "text-white" : "text-[#102B4E]"
          } leading-none`}
        >
          Grama<span className={inverted ? "text-[#20B5A5]" : "text-[#087F78]"}>Seva</span>
        </span>
        {showSubtitle && (
          <span
            className={`${subTextSizes[size]} uppercase font-bold tracking-[0.2em] ${
              inverted ? "text-[#A0B8D0]" : "text-[#40536B]"
            } leading-tight mt-1`}
          >
            CIVIC RESOLUTION
          </span>
        )}
      </div>
    </Link>
  );
};
