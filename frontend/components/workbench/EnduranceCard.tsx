"use client";

import { useState } from "react";
import { AlertTriangle, Battery, Gauge, Loader2, Navigation } from "lucide-react";
import { useEndurance } from "@/hooks/useEndurance";

type Mode = "endurance" | "range";

interface Props {
  readonly aeroplaneId: string | null;
}

function formatMinutes(seconds: number | null | undefined): string {
  if (seconds == null) return "–";
  const minutes = seconds / 60;
  if (minutes < 1) return `${seconds.toFixed(0)} s`;
  return `${minutes.toFixed(1)} min`;
}

function formatKm(meters: number | null | undefined): string {
  if (meters == null) return "–";
  const km = meters / 1000;
  return `${km.toFixed(1)} km`;
}

function formatWatts(watts: number | null | undefined): string {
  if (watts == null) return "–";
  return `${watts.toFixed(1)} W`;
}

const P_MARGIN_STYLES: Record<string, { bg: string; text: string }> = {
  comfortable: { bg: "bg-emerald-500/15", text: "text-emerald-400" },
  "feasible but tight": { bg: "bg-yellow-500/15", text: "text-yellow-400" },
  default: { bg: "bg-red-500/15", text: "text-red-400" },
};

function pMarginStyle(cls: string | null) {
  if (!cls) return P_MARGIN_STYLES.default;
  if (cls === "comfortable") return P_MARGIN_STYLES.comfortable;
  if (cls === "feasible but tight") return P_MARGIN_STYLES["feasible but tight"];
  return P_MARGIN_STYLES.default;
}

export function EnduranceCard({ aeroplaneId }: Props) {
  const [mode, setMode] = useState<Mode>("endurance");
  const { data, error, isLoading } = useEndurance(aeroplaneId);

  if (!aeroplaneId) return null;

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-border bg-card p-4">
        <Loader2 size={14} className="animate-spin text-muted-foreground" />
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
          Computing endurance…
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-border bg-card p-4">
        <AlertTriangle size={14} className="text-red-400" />
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-red-400">
          Endurance unavailable
        </span>
      </div>
    );
  }

  if (!data) return null;

  const isEstimated = data.confidence === "estimated";
  const hasWarnings = data.warnings.length > 0;

  const mainValue = mode === "endurance" ? formatMinutes(data.t_endurance_max_s) : formatKm(data.range_max_m);
  const mainLabel = mode === "endurance" ? "Max Endurance" : "Max Range";
  const mainSpeed = mode === "endurance" ? "at V_min_sink" : "at V_md";
  const pReqW = mode === "endurance" ? data.p_req_at_v_min_sink_w : data.p_req_at_v_md_w;
  const marginStyle = pMarginStyle(data.p_margin_class);

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Battery size={14} className="text-muted-foreground" />
          <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-muted-foreground">
            Endurance / Range
          </span>
          {(isEstimated || hasWarnings) && (
            <AlertTriangle
              size={12}
              className="text-yellow-400"
              title={
                isEstimated
                  ? "Estimated — polar fit unreliable. Run assumption recompute to improve."
                  : data.warnings[0]
              }
            />
          )}
        </div>
        {/* Mode toggle */}
        <div className="flex overflow-hidden rounded-md border border-border">
          <button
            onClick={() => setMode("endurance")}
            className={`px-2.5 py-1 font-[family-name:var(--font-geist-sans)] text-[10px] transition-colors ${
              mode === "endurance"
                ? "bg-primary text-primary-foreground"
                : "bg-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Max Endurance
          </button>
          <button
            onClick={() => setMode("range")}
            className={`px-2.5 py-1 font-[family-name:var(--font-geist-sans)] text-[10px] transition-colors ${
              mode === "range"
                ? "bg-primary text-primary-foreground"
                : "bg-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Max Range
          </button>
        </div>
      </div>

      {/* Main value */}
      <div className="flex items-baseline gap-1.5">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[24px] font-semibold text-foreground">
          {mainValue}
        </span>
        <span className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
          {mainLabel}
        </span>
      </div>

      {/* Speed annotation */}
      <span className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
        {mainSpeed}
      </span>

      {/* Sub-metrics row */}
      <div className="flex items-center gap-3 border-t border-border pt-2">
        {/* P_req */}
        <div className="flex items-center gap-1.5">
          <Gauge size={11} className="text-muted-foreground" />
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
            P_req = {formatWatts(pReqW)}
          </span>
        </div>

        {/* p_margin chip */}
        {data.p_margin_class && (
          <span
            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-[family-name:var(--font-geist-sans)] text-[10px] font-medium ${marginStyle.bg} ${marginStyle.text}`}
          >
            <Navigation size={9} />
            {data.p_margin_class}
          </span>
        )}

        {/* Confidence chip */}
        <span
          className={`ml-auto inline-flex rounded-full px-2 py-0.5 font-[family-name:var(--font-geist-sans)] text-[10px] font-medium ${
            isEstimated ? "bg-yellow-500/15 text-yellow-400" : "bg-emerald-500/15 text-emerald-400"
          }`}
        >
          {isEstimated ? "Estimated" : "Computed"}
        </span>
      </div>

      {/* Warnings (collapsed to first warning) */}
      {hasWarnings && (
        <div className="flex items-start gap-1.5 rounded-lg bg-yellow-500/10 p-2">
          <AlertTriangle size={11} className="mt-0.5 flex-shrink-0 text-yellow-400" />
          <span className="font-[family-name:var(--font-geist-sans)] text-[10px] text-yellow-300">
            {data.warnings[0]}
          </span>
        </div>
      )}
    </div>
  );
}
