"use client";

import React from "react";
import Link from "next/link";
import Image from "next/image";
import { useLocale } from "next-intl";

interface GramaSevaLogoProps {
  className?: string;
  size?: "sm" | "md" | "lg";
  showSubtitle?: boolean;
  inverted?: boolean;
  href?: string;
}

export const GramaSevaLogo: React.FC<GramaSevaLogoProps> = ({
  className = "",
  size = "md",
  showSubtitle = true,
  inverted = false,
  href,
}) => {
  const locale = useLocale();
  const targetHref = href || `/${locale}`;

  // Dimensions maintaining original aspect ratio (356:70 ≈ 5.08:1) without distortion or stretching
  const sizeClasses = {
    sm: "h-7 sm:h-8 w-auto max-w-[155px] sm:max-w-[170px]",
    md: "h-8 sm:h-9 lg:h-10 w-auto max-w-[185px] sm:max-w-[210px]",
    lg: "h-10 sm:h-12 w-auto max-w-[230px] sm:max-w-[260px]",
  };

  // On dark backgrounds (inverted=true), use the official crisp white+teal logo.
  // On light backgrounds (inverted=false), use the official navy+teal logo.
  const logoSrc = inverted
    ? "/images/gramaseva-logo.png"
    : "/images/gramaseva-logo-dark.png";

  return (
    <Link
      href={targetHref}
      className={`inline-flex items-center group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#20B5A5] rounded-xl transition-transform active:scale-[0.99] select-none ${className}`}
      aria-label="GramaSeva — Civic Resolution Homepage"
    >
      <div className="relative flex items-center">
        <Image
          src={logoSrc}
          alt="GramaSeva — Civic Resolution"
          width={356}
          height={70}
          priority
          className={`${sizeClasses[size]} object-contain object-left transition-opacity duration-150 group-hover:opacity-95`}
        />
      </div>
    </Link>
  );
};

