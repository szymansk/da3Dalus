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

// ── Qualitative label (issue #4a) ─────────────────────────────────
// >= 0.75 → "Gut", 0.5–0.75 → "Mäßig", < 0.5 → "Schwach"
export function qualitativeLabel(score: number): string {
  if (score >= 0.75) return "Gut";
  if (score >= 0.5) return "Mäßig";
  return "Schwach";
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
  const qlabel = qualitativeLabel(score);

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
      <span
        data-testid="qualitative-label"
        className="w-12 text-right font-[family-name:var(--font-jetbrains-mono)] text-[9px]"
        style={{ color }}
      >
        {qlabel}
      </span>
    </div>
  );
}

// ── Confidence chip ───────────────────────────────────────────────
// Issue #1 fix: chip moved to its own row below the toggle label so it never
// overflows the 480 px panel at any text size.
// Issue #4c fix: title tooltip explains what the number means.

function ConfidenceChip({
  confidence,
}: {
  readonly confidence: number;
}) {
  const isLow = confidence < 0.85;
  const color = isLow ? COLOR_AMBER : COLOR_GREEN;
  const tooltipText =
    "Modell-Konfidenz: Anteil der Re-Stützstellen mit konvergenter XFoil-Analyse. " +
    "1.0 = alle Stützstellen zuverlässig; < 0.85 = Werte als grobe Orientierung verstehen.";
  return (
    <span
      title={tooltipText}
      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px] cursor-help"
      style={{
        color,
        backgroundColor: isLow ? "rgba(251, 191, 36, 0.12)" : "rgba(52, 211, 153, 0.12)",
        border: `1px solid ${color}40`,
      }}
    >
      ● Konfidenz {confidence.toFixed(2)}
    </span>
  );
}

// ── Caveat callout (mirrors PolarRejectionBadge amber pattern) ─────
// Issue #4b: softer, actionable wording for hobbyists.

function CaveatCallout({ text, hasLowConfidence }: { readonly text: string; readonly hasLowConfidence?: boolean }) {
  const displayText = hasLowConfidence
    ? `Geringe Modell-Konfidenz bei diesem Re — Werte als grobe Orientierung verstehen. ${text}`
    : text;
  return (
    <div
      role="note"
      className="inline-flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-2.5 py-1 text-xs leading-tight text-amber-200"
    >
      <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" aria-hidden="true" />
      <span>{displayText}</span>
    </div>
  );
}

// ── No-data placeholder (issue #3) ───────────────────────────────

export function AirfoilSuitabilityNoData({ airfoilName }: { readonly airfoilName?: string }) {
  return (
    <div
      data-testid="suitability-no-data"
      className="flex flex-col gap-1 rounded-xl border border-border bg-card-muted px-3 py-2"
    >
      <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
        Eignung
      </span>
      <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-subtle-foreground">
        {airfoilName
          ? `Keine Low-Re-Eignungsdaten für „${airfoilName}"`
          : "Keine Low-Re-Eignungsdaten für dieses Profil"}
      </span>
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
  const isLowConfidence = item.min_analysis_confidence < 0.85;

  return (
    <div className="flex flex-col gap-1 rounded-xl border border-border bg-card-muted px-3 py-2">
      {/* Header / toggle — issue #1 fix: chip on its own row to prevent overflow */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full flex-col gap-0.5 text-left"
      >
        <div className="flex items-center gap-1.5">
          {open ? (
            <ChevronDown size={11} className="text-muted-foreground" />
          ) : (
            <ChevronRight size={11} className="text-muted-foreground" />
          )}
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
            Eignung
          </span>
        </div>
        <div className="pl-4">
          <ConfidenceChip confidence={item.min_analysis_confidence} />
        </div>
      </button>

      {/* Body (collapsible) */}
      {open && (
        <div className="flex flex-col gap-1.5 pt-1">
          <ScoreBar label="Re-agnostisch" score={item.re_agnostic} />
          <ScoreBar
            label="Mission"
            score={item.mission}
          />
          <ScoreBar label="Ziel-CL · Cruise" score={item.target_cl_cruise} />
          <ScoreBar label="Ziel-CL · Loiter" score={item.target_cl_loiter} />
          {item.caveat && (
            <div className="mt-1">
              <CaveatCallout text={item.caveat} hasLowConfidence={isLowConfidence} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
