"use client";

// Click-dummy scratch route (#881) — visual review only, hardcoded data.
// Removed in #887 once the real dashboard replaces InfoChipRow.

import { MetricsDashboard } from "@/components/workbench/metrics-dashboard/MetricsDashboard";

export default function MetricsPreviewPage() {
  return (
    <div className="flex h-full w-full flex-col gap-3">
      <div className="shrink-0 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-[11px] text-amber-300">
        Click-dummy — metrics band (#881). Hardcoded data. The band is docked at the bottom (above the copilot strip);
        the views above get all remaining height. Click a column to expand it to full width; band height stays constant.
      </div>
      {/* the other views take all remaining height above the docked band */}
      <div className="flex min-h-0 flex-1 items-center justify-center rounded-lg border border-dashed border-border text-[12px] text-subtle-foreground">
        (analysis charts / other views fill this space)
      </div>
      {/* docked metrics band */}
      <div className="shrink-0">
        <MetricsDashboard />
      </div>
    </div>
  );
}
