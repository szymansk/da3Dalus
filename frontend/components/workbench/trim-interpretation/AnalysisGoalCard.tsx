"use client";

import type { TrimEnrichment } from "@/hooks/useOperatingPoints";

function computeStatusLevel(enrichment: TrimEnrichment): "healthy" | "marginal" | "critical" {
  if (enrichment.design_warnings.some((w) => w.level === "critical")) return "critical";
  const maxUsage = Math.max(
    0,
    ...Object.values(enrichment.deflection_reserves).map((r) => r.usage_fraction),
  );
  if (maxUsage > 0.8) return "critical";
  if (maxUsage > 0.6) return "marginal";
  if (enrichment.design_warnings.some((w) => w.level === "warning")) return "marginal";
  return "healthy";
}

const BADGE_STYLES = {
  healthy: "bg-emerald-500",
  marginal: "bg-amber-500",
  critical: "bg-red-500",
} as const;

const BADGE_LABELS = {
  healthy: "Healthy",
  marginal: "Marginal",
  critical: "Critical",
} as const;

interface Props {
  readonly enrichment: TrimEnrichment | null;
}

export function AnalysisGoalCard({ enrichment }: Props) {
  if (!enrichment) return null;

  const level = computeStatusLevel(enrichment);

  return (
    <div className="rounded-lg border border-[#FF8400]/30 bg-[#FF8400]/10 px-4 py-3">
      <div className="flex items-center justify-between">
        <span className="font-[family-name:var(--font-geist-sans)] text-[11px] font-medium uppercase tracking-wider text-[#FF8400]">
          Analysis Goal
        </span>
        <span
          data-testid="status-badge"
          className={`rounded-full px-2 py-0.5 text-[10px] font-semibold text-white ${BADGE_STYLES[level]}`}
        >
          {BADGE_LABELS[level]}
        </span>
      </div>
      <p className="mt-1 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground">
        {enrichment.analysis_goal}
      </p>
      {enrichment.result_summary && (
        <p className="mt-1 font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          {enrichment.result_summary}
        </p>
      )}
    </div>
  );
}
