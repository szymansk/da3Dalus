"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, AlertTriangle } from "lucide-react";
import type { SuitabilityItem } from "@/hooks/useAirfoilSuitability";

// ── Colour thresholds ─────────────────────────────────────────────
const COLOR_GREEN = "#34D399";
const COLOR_AMBER = "#FBBF24";
const COLOR_RED = "#F87171";

function scoreColor(score: number): string {
  if (score >= 0.7) return COLOR_GREEN;
  if (score >= 0.4) return COLOR_AMBER;
  return COLOR_RED;
}

// ── Score bar ─────────────────────────────────────────────────────

function ScoreBar({
  label,
  score,
}: {
  readonly label: string;
  readonly score: number | null;
}) {
  if (score === null) {
    return (
      <div className="flex items-center gap-2">
        <span className="w-32 font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
          {label}
        </span>
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
          n/a
        </span>
      </div>
    );
  }

  const color = scoreColor(score);
  const pct = Math.round(score * 100);

  return (
    <div className="flex items-center gap-2">
      <span className="w-32 font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
        {label}
      </span>
      <div className="flex-1 overflow-hidden rounded-full bg-card-muted" style={{ height: 6 }}>
        <div
          className="h-full rounded-full transition-all"
          style={{
            width: `${pct}%`,
            backgroundColor: color,
          }}
        />
      </div>
      <span
        className="w-8 text-right font-[family-name:var(--font-jetbrains-mono)] text-[10px]"
        style={{ color }}
      >
        {(score).toFixed(2)}
      </span>
    </div>
  );
}

// ── Confidence chip ───────────────────────────────────────────────

function ConfidenceChip({
  confidence,
}: {
  readonly confidence: number;
}) {
  const isLow = confidence < 0.85;
  const color = isLow ? COLOR_AMBER : COLOR_GREEN;
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px]"
      style={{
        color,
        backgroundColor: isLow ? "rgba(251, 191, 36, 0.12)" : "rgba(52, 211, 153, 0.12)",
        border: `1px solid ${color}40`,
      }}
    >
      ● Confidence {confidence.toFixed(2)}
    </span>
  );
}

// ── Caveat callout (mirrors PolarRejectionBadge amber pattern) ─────

function CaveatCallout({ text }: { readonly text: string }) {
  return (
    <div
      role="note"
      className="inline-flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-2.5 py-1 text-xs leading-tight text-amber-200"
    >
      <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" aria-hidden="true" />
      <span>{text}</span>
    </div>
  );
}

// ── Main card ─────────────────────────────────────────────────────

export interface AirfoilSuitabilityCardProps {
  item: SuitabilityItem;
  defaultOpen?: boolean;
}

export function AirfoilSuitabilityCard({
  item,
  defaultOpen = true,
}: Readonly<AirfoilSuitabilityCardProps>) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="flex flex-col gap-1 rounded-xl border border-border bg-card-muted px-3 py-2">
      {/* Header / toggle */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-1.5 text-left"
      >
        {open ? (
          <ChevronDown size={11} className="text-muted-foreground" />
        ) : (
          <ChevronRight size={11} className="text-muted-foreground" />
        )}
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
          Eignung
        </span>
        <span className="flex-1" />
        <ConfidenceChip confidence={item.min_analysis_confidence} />
      </button>

      {/* Body (collapsible) */}
      {open && (
        <div className="flex flex-col gap-1.5 pt-1">
          <ScoreBar label="Re-agnostisch" score={item.re_agnostic} />
          <ScoreBar
            label={`Mission`}
            score={item.mission}
          />
          <ScoreBar label="Ziel-CL · Cruise" score={item.target_cl_cruise} />
          <ScoreBar label="Ziel-CL · Loiter" score={item.target_cl_loiter} />
          {item.caveat && (
            <div className="mt-1">
              <CaveatCallout text={item.caveat} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
