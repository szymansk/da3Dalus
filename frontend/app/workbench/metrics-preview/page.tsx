"use client";

// Click-dummy scratch route (#881) — visual review only, hardcoded data.
// Removed in #887 once the real dashboard replaces InfoChipRow.

import { MetricsDashboard } from "@/components/workbench/metrics-dashboard/MetricsDashboard";

export default function MetricsPreviewPage() {
  return (
    <div className="flex w-full flex-col gap-4 overflow-auto">
      <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-[11px] text-amber-300">
        Click-dummy — metrics dashboard prototype (#881). Hardcoded data, no backend. Toggle each section between
        collapsed / compact / large; only one section can be large at a time.
      </div>
      <div className="mx-auto w-full max-w-[920px]">
        <MetricsDashboard />
      </div>
    </div>
  );
}
