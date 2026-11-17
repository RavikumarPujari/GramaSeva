import Link from "next/link";
import { defaultLocale } from "@/i18n";

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 text-center bg-slate-50">
      <h1 className="text-4xl font-extrabold text-slate-900 mb-2">404</h1>
      <h2 className="text-lg font-semibold text-slate-700 mb-4">Page Not Found</h2>
      <p className="text-sm text-slate-500 max-w-sm mb-6">
        The requested civic portal page or complaint could not be located.
      </p>
      <Link
        href={`/${defaultLocale}`}
        className="px-4 py-2 bg-civic-600 text-white rounded-lg text-sm font-semibold hover:bg-civic-700 transition-colors"
      >
        Return to Home
      </Link>
    </div>
  );
}
