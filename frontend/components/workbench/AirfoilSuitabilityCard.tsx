"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, AlertTriangle } from "lucide-react";
import type {
  SuitabilityItem,
  SuitabilityCaveat,
  TargetClProvenance,
} from "@/hooks/useAirfoilSuitability";

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
  sublabel,
  score,
}: {
  readonly label: string;
  readonly sublabel?: string;
  readonly score: number | null;
}) {
  if (score === null) {
    return (
      <div className="flex items-center gap-2">
        <div className="flex w-32 flex-col">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
            {label}
          </span>
          {sublabel && (
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-subtle-foreground">
              {sublabel}
            </span>
          )}
        </div>
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
      <div className="flex w-32 flex-col">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
          {label}
        </span>
        {sublabel && (
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-subtle-foreground">
            {sublabel}
          </span>
        )}
      </div>
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

function CaveatCallout({
  text,
  hasLowConfidence,
}: {
  readonly text: string;
  readonly hasLowConfidence?: boolean;
}) {
  // gh-825 item 3: low-confidence note must be ONE consistent language (German).
  // Use a standalone German UI string instead of appending the raw English backend text.
  const displayText = hasLowConfidence
    ? "Geringe Modell-Konfidenz bei diesem Re — Werte als grobe Orientierung verstehen."
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

// ── Provenance indicator ──────────────────────────────────────────
// gh-825: Shows whether the target CL values are design-derived or manually estimated.

function ProvenanceIndicator({
  provenance,
}: {
  readonly provenance: TargetClProvenance;
}) {
  let label: string;
  let tooltip: string;
  let color: string;

  if (provenance === "calculated") {
    label = "Ber. Referenz";
    tooltip =
      "calculated — bewegliche Referenz: Ziel-CL stammt aus den Design-Annahmen. " +
      "Der Wert verschiebt sich mit dem Design und Profil — Vergleiche sind relativ.";
    color = COLOR_GREEN;
  } else if (provenance === "mixed") {
    label = "Gem. Referenz";
    tooltip =
      "mixed — kombinierte Referenz: Ein Teil der Ziel-CL-Werte stammt aus automatischen " +
      "Design-Annahmen, ein Teil aus manuellen Schätzungen.";
    color = COLOR_AMBER;
  } else {
    // estimated
    label = "Geschätzte Ref.";
    tooltip =
      "estimated — feste Referenz: Ziel-CL basiert auf manuellen Schätzungen. " +
      "Der Wert bleibt konstant, unabhängig vom Design.";
    color = COLOR_AMBER;
  }

  return (
    <span
      data-testid="provenance-indicator"
      title={tooltip}
      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[9px] cursor-help"
      style={{
        color,
        backgroundColor:
          provenance === "calculated"
            ? "rgba(52, 211, 153, 0.10)"
            : "rgba(251, 191, 36, 0.10)",
        border: `1px solid ${color}40`,
      }}
    >
      ◆ {label}
    </span>
  );
}

// ── Stall/CLmax detail row ─────────────────────────────────────────
// gh-825: Surface stall_gentleness (raw dCL/dα, NOT 0..1) and cl_max_margin (signed CL margin).

function StallClMaxRow({
  stallGentleness,
  clMaxMargin,
}: {
  readonly stallGentleness: number | null;
  readonly clMaxMargin: number | null;
}) {
  if (stallGentleness === null && clMaxMargin === null) return null;

  const marginNegative = clMaxMargin !== null && clMaxMargin < 0;
  const stallAbrupt = stallGentleness !== null && stallGentleness < -0.05;

  return (
    <div className="flex flex-col gap-1 rounded-md border border-border bg-card px-2 py-1.5">
      {stallGentleness !== null && (
        <div className="flex items-center gap-2">
          <span className="w-32 font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-muted-foreground">
            Stall-Sanftheit
          </span>
          <span
            data-testid="stall-gentleness-value"
            className="font-[family-name:var(--font-jetbrains-mono)] text-[10px]"
            style={{ color: stallAbrupt ? COLOR_RED : COLOR_GREEN }}
          >
            dCL/dα {stallGentleness.toFixed(3)}
          </span>
          {stallAbrupt && (
            <span
              data-testid="stall-abrupt-warning"
              className="font-[family-name:var(--font-jetbrains-mono)] text-[9px]"
              style={{ color: COLOR_RED }}
            >
              abrupt
            </span>
          )}
        </div>
      )}
      {clMaxMargin !== null && (
        <div className="flex items-center gap-2">
          <span className="w-32 font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-muted-foreground">
            CL-Margin
          </span>
          <span
            data-testid="cl-max-margin-value"
            className="font-[family-name:var(--font-jetbrains-mono)] text-[10px]"
            style={{ color: marginNegative ? COLOR_RED : COLOR_GREEN }}
          >
            {clMaxMargin >= 0 ? "+" : ""}
            {clMaxMargin.toFixed(3)}
          </span>
          {marginNegative && (
            <span
              data-testid="cl-max-margin-warning"
              className="font-[family-name:var(--font-jetbrains-mono)] text-[9px]"
              style={{ color: COLOR_RED }}
            >
              Ziel &gt; CL_max!
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// ── Tip-Re CL_max collapse warning ─────────────────────────────────
// gh-825: Surface the warning when caveat.ignores_tip_re_clmax_collapse or tip_re_flag.

function TipReClMaxWarning() {
  return (
    <div
      data-testid="tip-re-clmax-warning"
      role="note"
      className="inline-flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-2.5 py-1 text-xs leading-tight text-amber-200"
    >
      <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" aria-hidden="true" />
      <span>
        Der Score ignoriert den Tip-Re-CL_max-Einbruch: An der Flügelspitze
        wirkt die verminderte Re auf CL_max (Tip-Stall-Zone). Dieser Effekt
        ist in der Profilbewertung nicht modelliert — XFoil-Validierung empfohlen.
      </span>
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
  /**
   * gh-825 ADDITIVE: provenance of the target CL values.
   * When provided, renders the ProvenanceIndicator chip.
   */
  targetClProvenance?: TargetClProvenance;
  /**
   * gh-825 ADDITIVE: full caveat object.
   * When provided (alongside item.caveat string), the
   * ignores_tip_re_clmax_collapse flag is used to show the tip-Re warning.
   */
  caveatObject?: SuitabilityCaveat;
}

export function AirfoilSuitabilityCard({
  item,
  defaultOpen = true,
  targetClProvenance,
  caveatObject: _caveatObject,  // kept for API compatibility; no longer used for warning gate
}: Readonly<AirfoilSuitabilityCardProps>) {
  const [open, setOpen] = useState(defaultOpen);
  const isLowConfidence = item.min_analysis_confidence < 0.85;

  // gh-825 item 4: gate the tip-Re CL_max warning on the PER-AIRFOIL flag ONLY.
  // The global caveat flag (caveatObject.ignores_tip_re_clmax_collapse) is always true
  // for the whole suitability response, so ORing it caused the warning to appear on
  // EVERY card. Only the per-airfoil item.tip_re_flag indicates that this specific
  // airfoil is affected by tip-Re CL_max collapse.
  const showTipReClMaxWarning = item.tip_re_flag === true;

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
        <div className="pl-4 flex items-center gap-2 flex-wrap">
          <ConfidenceChip confidence={item.min_analysis_confidence} />
          {targetClProvenance && (
            <ProvenanceIndicator provenance={targetClProvenance} />
          )}
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
          <ScoreBar
            label="Ziel-CL · Best-Glide"
            sublabel="Motorausfall / Segelflug"
            score={item.target_cl_best_glide}
          />
          <ScoreBar label="Ziel-CL · Min-Sink" score={item.target_cl_min_sink} />

          {/* gh-825: Stall gentleness + CL_max margin */}
          <StallClMaxRow
            stallGentleness={item.stall_gentleness}
            clMaxMargin={item.cl_max_margin}
          />

          {/* gh-825: Tip-Re CL_max collapse warning */}
          {showTipReClMaxWarning && (
            <div className="mt-1">
              <TipReClMaxWarning />
            </div>
          )}

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
