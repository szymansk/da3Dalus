"use client";

import type { PerformanceKPI } from "@/hooks/useFlightEnvelope";

const CONFIDENCE_STYLES: Record<
  PerformanceKPI["confidence"],
  { bg: string; text: string; label: string }
> = {
  trimmed: {
    bg: "bg-emerald-500/15",
    text: "text-emerald-400",
    label: "Trimmed",
  },
  computed: {
    bg: "bg-sky-500/15",
    text: "text-sky-400",
    label: "Computed",
  },
  estimated: {
    bg: "bg-yellow-500/15",
    text: "text-yellow-400",
    label: "Estimated",
  },
  limit: {
    bg: "bg-red-500/15",
    text: "text-red-400",
    label: "Limit",
  },
};

function KpiCard({ kpi }: Readonly<{ kpi: PerformanceKPI }>) {
  // Defensive fallback: if backend adds a new confidence literal before
  // this map is updated, surface as 'Estimated' rather than crashing
  // the entire analysis page (gh-521).
  const style = CONFIDENCE_STYLES[kpi.confidence] ?? CONFIDENCE_STYLES.estimated;

  return (
    <div className="flex flex-col gap-1.5 rounded-xl border border-border bg-card p-4">
      <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-muted-foreground">
        {kpi.display_name}
      </span>
      <div className="flex items-baseline gap-1.5">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[20px] font-semibold text-foreground">
          {typeof kpi.value === "number" ? kpi.value.toFixed(1) : kpi.value}
        </span>
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          {kpi.unit}
        </span>
      </div>
      <span
        className={`inline-flex w-fit rounded-full px-2 py-0.5 font-[family-name:var(--font-geist-sans)] text-[10px] font-medium ${style.bg} ${style.text}`}
      >
        {style.label}
      </span>
    </div>
  );
}

interface Props {
  readonly kpis: PerformanceKPI[];
}

export function PerformanceOverview({ kpis }: Props) {
  if (kpis.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-muted-foreground">
          No performance data available
        </span>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {kpis.map((kpi) => (
        <KpiCard key={kpi.label} kpi={kpi} />
      ))}
    </div>
  );
}
