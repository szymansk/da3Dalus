"use client";

// Click-dummy scratch route (#881) — visual review only, hardcoded data.
// Removed in #887 once the real dashboard replaces InfoChipRow.

import { MetricsDashboard } from "@/components/workbench/metrics-dashboard/MetricsDashboard";

export default function MetricsPreviewPage() {
  return (
    <div className="flex w-full flex-col gap-3">
      <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-[11px] text-amber-300">
        Click-dummy — metrics band (#881). Hardcoded data. Five compact columns in a ~20vh strip; click a column to
        expand it to full width (others shrink to tabs). Height stays constant.
      </div>
      {/* simulate the chart area above, so the band's 20vh proportion is visible */}
      <div className="flex h-[55vh] items-center justify-center rounded-lg border border-dashed border-border text-[12px] text-subtle-foreground">
        (analysis charts would be here)
      </div>
      <MetricsDashboard />
    </div>
  );
}
