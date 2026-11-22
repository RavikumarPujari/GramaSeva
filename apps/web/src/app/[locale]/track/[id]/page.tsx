import React, { Suspense } from "react";
import { TrackGrievanceClient } from "@/components/ui/TrackGrievanceClient";

export default function TrackByIdPage({
  params,
}: {
  params: { locale: string; id: string };
}) {
  const locale = params?.locale || "en";
  const id = params?.id || "";

  return (
    <main className="min-h-screen bg-[#F4F8FB] py-8 sm:py-12 px-4 sm:px-6 lg:px-8">
      <Suspense fallback={<div className="text-center py-12 text-slate-400 font-bold text-sm">Loading grievance tracker...</div>}>
        <TrackGrievanceClient locale={locale} initialId={id} />
      </Suspense>
    </main>
  );
}
