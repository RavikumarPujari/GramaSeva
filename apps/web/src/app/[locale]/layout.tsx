import React from "react";
import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import { getMessages, unstable_setRequestLocale as setRequestLocale } from "next-intl/server";
import { NextIntlClientProvider } from "next-intl";
import { defaultLocale, locales, type Locale } from "@/i18n";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import "../globals.css";

export const metadata: Metadata = {
  title: "GramaSeva — Verified Civic Complaint & Repair Tracking",
  description:
    "Village-first civic technology pilot for Gram Panchayats and municipal wards. Report issues, track verified repairs with photo evidence, and ensure independent review.",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/images/gramaseva-favicon.png", type: "image/png", sizes: "32x32" },
      { url: "/images/gramaseva-favicon.png", type: "image/png", sizes: "64x64" },
    ],
    apple: [
      { url: "/images/gramaseva-favicon.png", sizes: "64x64", type: "image/png" },
    ],
  },
};

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

interface RootLayoutProps {
  children: React.ReactNode;
  params: { locale: string };
}

export default async function LocaleLayout({
  children,
  params: { locale },
}: RootLayoutProps) {
  if (!locales.includes(locale as Locale)) {
    const knownRoutes = [
      "report",
      "track",
      "public",
      "admin",
      "pdo",
      "citizen",
      "staff",
      "worker",
      "login",
      "register",
      "my-reports",
      "ai-processing",
    ];
    if (knownRoutes.includes(locale)) {
      redirect(`/${defaultLocale}/${locale}`);
    }
    notFound();
  }

  setRequestLocale(locale);
  const messages = await getMessages();

  return (
    <html lang={locale}>
      <body className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans">
        <NextIntlClientProvider locale={locale} messages={messages}>
          <Navbar />
          <main className="flex-1 flex flex-col">{children}</main>
          <Footer />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
