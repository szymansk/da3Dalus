"use client";

/**
 * TailVolumeCard — Tail volume coefficient sizing hint (gh-491).
 *
 * Displays V_H and V_V for the current aircraft configuration and
 * offers a pencil-action to fill in recommended S_H / S_V + single
 * recompute (no cascade).
 *
 * Card is hidden when classification === "not_applicable".
 */

import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle,
  Info,
  Pencil,
  XCircle,
} from "lucide-react";
import {
  type TailClassification,
  useTailSizing,
} from "@/hooks/useTailSizing";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function classColor(cls: TailClassification): string {
  switch (cls) {
    case "in_range":
      return "text-green-400";
    case "below_range":
    case "above_range":
      return "text-orange-400";
    case "out_of_physical_range":
      return "text-red-400";
    default:
      return "text-muted-foreground";
  }
}

function classBg(cls: TailClassification): string {
  switch (cls) {
    case "in_range":
      return "bg-green-500/10 border-green-500/30";
    case "below_range":
    case "above_range":
      return "bg-orange-500/10 border-orange-500/30";
    case "out_of_physical_range":
      return "bg-red-500/10 border-red-500/30";
    default:
      return "bg-zinc-800/60 border-zinc-700";
  }
}

function ClassIcon({ cls }: { readonly cls: TailClassification }) {
  switch (cls) {
    case "in_range":
      return <CheckCircle size={13} className="text-green-400 shrink-0" />;
    case "below_range":
    case "above_range":
      return <AlertTriangle size={13} className="text-orange-400 shrink-0" />;
    case "out_of_physical_range":
      return <XCircle size={13} className="text-red-400 shrink-0" />;
    default:
      return <Info size={13} className="text-muted-foreground shrink-0" />;
  }
}

function fmt(v: number | null | undefined, digits = 3): string {
  if (v == null) return "—";
  return v.toFixed(digits);
}

function fmtMm2(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${Math.round(v).toLocaleString()} mm²`;
}

// ---------------------------------------------------------------------------
// Volume row
// ---------------------------------------------------------------------------

interface VolumeRowProps {
  readonly label: string;
  readonly value: number | null | undefined;
  readonly classification: TailClassification;
  readonly targetMin: number | null | undefined;
  readonly targetMax: number | null | undefined;
  readonly citation: string;
  readonly recommended_mm2: number | null | undefined;
  readonly onApply?: () => void;
  readonly applyLabel?: string;
}

function VolumeRow({
  label,
  value,
  classification,
  targetMin,
  targetMax,
  citation,
  recommended_mm2,
  onApply,
  applyLabel,
}: VolumeRowProps) {
  const color = classColor(classification);
  const bg = classBg(classification);

  return (
    <div className={`rounded-lg border px-3 py-2 ${bg}`} data-testid={`tail-volume-row-${label}`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <ClassIcon cls={classification} />
          <span className="text-[11px] font-semibold text-foreground">{label}</span>
        </div>
        <span className={`font-[family-name:var(--font-jetbrains-mono)] text-[13px] ${color}`}>
          {fmt(value)}
        </span>
      </div>
      {targetMin != null && targetMax != null && (
        <div className="mt-1 flex items-center justify-between gap-2">
          <span className="text-[10px] text-muted-foreground">
            target {targetMin.toFixed(3)}–{targetMax.toFixed(3)}
            {citation ? (
              <span className="ml-1 text-zinc-500"> ({citation})</span>
            ) : null}
          </span>
          {recommended_mm2 != null && onApply && (
            <button
              onClick={onApply}
              title={`Apply recommended ${applyLabel ?? label}: ${fmtMm2(recommended_mm2)}`}
              className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] text-muted-foreground hover:bg-[#FF8400]/10 hover:text-[#FF8400]"
              data-testid={`tail-volume-apply-${label}`}
            >
              <Pencil size={10} />
              {fmtMm2(recommended_mm2)}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Secondary metric
// ---------------------------------------------------------------------------

interface SecondaryMetricProps {
  readonly label: string;
  readonly value: number | null | undefined;
  readonly unit: string;
}

function SecondaryMetric({ label, value, unit }: SecondaryMetricProps) {
  return (
    <div className="flex items-center justify-between text-[10px] text-muted-foreground">
      <span>{label}</span>
      <span className="font-[family-name:var(--font-jetbrains-mono)]">
        {value != null ? `${value.toFixed(3)} ${unit}` : "—"}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main card
// ---------------------------------------------------------------------------

interface TailVolumeCardProps {
  readonly aeroplaneId: string;
  /** Called after pencil-action: parent should trigger one recompute. */
  readonly onApplySh?: (recommended_mm2: number) => void;
  readonly onApplySv?: (recommended_mm2: number) => void;
}

export function TailVolumeCard({
  aeroplaneId,
  onApplySh,
  onApplySv,
}: TailVolumeCardProps) {
  const { data, isLoading, recomputeOnce } = useTailSizing(aeroplaneId);
  const [applying, setApplying] = useState(false);

  // Completely hide the card when not applicable
  if (!isLoading && data?.classification === "not_applicable") {
    return null;
  }

  async function handleApply(kind: "sh" | "sv") {
    if (!data) return;
    setApplying(true);
    try {
      if (kind === "sh" && data.s_h_recommended_mm2 != null) {
        onApplySh?.(data.s_h_recommended_mm2);
      } else if (kind === "sv" && data.s_v_recommended_mm2 != null) {
        onApplySv?.(data.s_v_recommended_mm2);
      }
      // Single-shot recompute — no cascade (gh-491 spec)
      await recomputeOnce();
    } finally {
      setApplying(false);
    }
  }

  return (
    <section
      className="flex flex-col gap-3 rounded-xl border border-zinc-700 bg-zinc-900 p-4"
      data-testid="tail-volume-card"
    >
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="text-[11px] uppercase tracking-wider text-muted-foreground">
          Tail Volume
        </span>
        {!data?.cg_aware && !isLoading && (
          <span
            title="Neutral point not yet computed — recommendation uses wing-AC reference only"
            className="rounded-full bg-zinc-700/60 px-1.5 py-0.5 text-[9px] text-zinc-400"
          >
            no polar
          </span>
        )}
      </div>

      {isLoading && (
        <div className="text-[11px] text-muted-foreground">Computing…</div>
      )}

      {!isLoading && data && (
        <>
          {/* Volume coefficient rows */}
          <div className="flex flex-col gap-2">
            <VolumeRow
              label="V_H"
              value={data.v_h_current}
              classification={data.classification_h}
              targetMin={data.v_h_target_min}
              targetMax={data.v_h_target_max}
              citation={data.v_h_citation}
              recommended_mm2={data.s_h_recommended_mm2}
              applyLabel="S_H"
              onApply={applying ? undefined : () => handleApply("sh")}
            />
            <VolumeRow
              label="V_V"
              value={data.v_v_current}
              classification={data.classification_v}
              targetMin={data.v_v_target_min}
              targetMax={data.v_v_target_max}
              citation={data.v_v_citation}
              recommended_mm2={data.s_v_recommended_mm2}
              applyLabel="S_V"
              onApply={applying ? undefined : () => handleApply("sv")}
            />
          </div>

          {/* Secondary metrics */}
          <div className="flex flex-col gap-1 border-t border-zinc-800 pt-2">
            <SecondaryMetric
              label="l_H (wing-AC → tail-AC)"
              value={data.l_h_m}
              unit="m"
            />
            <SecondaryMetric
              label="l_H eff (aft-CG → tail-AC)"
              value={data.l_h_eff_from_aft_cg_m}
              unit="m"
            />
          </div>

          {/* Warnings */}
          {data.warnings.length > 0 && (
            <div className="flex flex-col gap-1 rounded-lg border border-orange-500/20 bg-orange-500/5 px-3 py-2">
              {data.warnings.map((w, i) => (
                <div key={i} className="flex items-start gap-1.5">
                  <AlertTriangle
                    size={11}
                    className="mt-0.5 shrink-0 text-orange-400"
                  />
                  <span className="text-[10px] text-orange-300">{w}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}
