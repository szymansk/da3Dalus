"use client";

/**
 * SparSizingPanel — gh-1008
 *
 * Collapsible panel displayed below the Spanwise Loads V/M chart.
 * Lets the user choose material + shape, then calls the spar-sizing
 * endpoint and shows the tapered per-station results.
 *
 * All UI text is English per project convention.
 */

import { useState, useCallback } from "react";
import { ChevronDown, ChevronRight, AlertTriangle } from "lucide-react";

import type { SparShape, SparSizingResult, SparSizingStation } from "@/hooks/useSparSizing";
import { useComponents } from "@/hooks/useComponents";
import {
  filterStructuralMaterials,
  getSigmaAllow,
  solvedDimLabel,
  feasibilityLabel,
  buildRootHeadline,
  buildMassSummary,
} from "@/lib/sparSizingHelpers";

// ---- Types -----------------------------------------------------------------

export interface SparSizingInputs {
  materialId: number | null;
  shape: SparShape;
  sigmaAllowOverride: string; // editable string; empty → use material value
  safetyFactorJ: string;
  packingFactor: string;
  capWidthMm: string; // only for capped
}

export interface SparSizingPanelProps {
  /** Current spar sizing results, or null when not yet computed. */
  sizingResults: SparSizingResult[] | null;
  /** Whether the sizing computation is running. */
  isRunning: boolean;
  /** Error message from the last run, if any. */
  error: string | null;
  /**
   * Called when the user clicks "Compute Spar Sizing".
   * The parent is responsible for calling useSparSizing.run().
   */
  onCompute: (inputs: SparSizingInputs) => void;
  /** g_limit from design assumptions (shown read-only). */
  gLimit?: number | null;
  /** True when g_limit is a fallback default. */
  gLimitFallback?: boolean;
}

// ---- Helpers ---------------------------------------------------------------

function parsePositiveFloat(s: string, fallback: number): number {
  const v = parseFloat(s);
  return Number.isFinite(v) && v > 0 ? v : fallback;
}

function StationRow({
  station,
  solvedLabel,
}: {
  station: SparSizingStation;
  solvedLabel: string;
}) {
  const feasOk = station.feasible;
  return (
    <tr className="border-b border-border/30 font-[family-name:var(--font-jetbrains-mono)] text-[12px]">
      <td className="px-2 py-1 tabular-nums">{station.y_m.toFixed(2)}</td>
      <td className="px-2 py-1 tabular-nums">{(station.chord_m * 1000).toFixed(0)}</td>
      <td className="px-2 py-1 tabular-nums">{station.outer_mm.toFixed(1)}</td>
      <td className="px-2 py-1 tabular-nums">{station.required_W_mm3.toFixed(0)}</td>
      <td className="px-2 py-1 tabular-nums">
        {station.solved_mm != null ? station.solved_mm.toFixed(2) : "—"}
      </td>
      <td
        className={`px-2 py-1 ${feasOk ? "text-green-400" : "text-yellow-400"}`}
        title={station.infeasibility_reason ?? undefined}
      >
        {feasOk ? "OK" : feasibilityLabel(station)}
      </td>
    </tr>
  );
}

function SizingResultCard({ result }: { result: SparSizingResult }) {
  const solvedLabel = solvedDimLabel(result.shape);
  return (
    <div className="rounded border border-border/40 bg-card p-3 text-[13px] space-y-3">
      {/* Root headline */}
      <div className="space-y-1">
        <p className="text-xs text-muted-foreground font-[family-name:var(--font-jetbrains-mono)]">
          Surface: <span className="text-foreground">{result.surface_name}</span>
        </p>
        <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-muted-foreground">
          {buildRootHeadline(result)}
        </p>
        <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-foreground">
          {buildMassSummary(result)}
        </p>
      </div>

      {/* Warnings */}
      {result.g_limit_fallback && (
        <div
          className="flex items-start gap-1 rounded bg-yellow-900/20 px-2 py-1 text-xs text-yellow-400"
          data-testid="g-limit-fallback-warning"
        >
          <AlertTriangle size={12} className="mt-0.5 shrink-0" />
          <span>g_limit = {result.g_limit} (default — no design assumption set)</span>
        </div>
      )}
      {result.tc_fallback_warning && (
        <div
          className="flex items-start gap-1 rounded bg-yellow-900/20 px-2 py-1 text-xs text-yellow-400"
          data-testid="tc-fallback-warning"
        >
          <AlertTriangle size={12} className="mt-0.5 shrink-0" />
          <span>{result.tc_fallback_warning}</span>
        </div>
      )}

      {/* Per-station table */}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[480px] border-collapse text-left">
          <thead>
            <tr className="border-b border-border/50 text-[11px] text-muted-foreground font-[family-name:var(--font-jetbrains-mono)]">
              <th className="px-2 py-1">y (m)</th>
              <th className="px-2 py-1">chord (mm)</th>
              <th className="px-2 py-1">outer (mm)</th>
              <th className="px-2 py-1">req. W (mm³)</th>
              <th className="px-2 py-1">{solvedLabel}</th>
              <th className="px-2 py-1">status</th>
            </tr>
          </thead>
          <tbody>
            {[...result.stations]
              .sort((a, b) => a.y_m - b.y_m) // root first (ascending y)
              .map((st, idx) => (
                <StationRow key={idx} station={st} solvedLabel={solvedLabel} />
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---- Main Component --------------------------------------------------------

/** Exported for unit testing (pure display layer). */
export function SparSizingPanel({
  sizingResults,
  isRunning,
  error,
  onCompute,
  gLimit,
  gLimitFallback = false,
}: SparSizingPanelProps) {
  const [open, setOpen] = useState(false);
  const [inputs, setInputs] = useState<SparSizingInputs>({
    materialId: null,
    shape: "tube",
    sigmaAllowOverride: "",
    safetyFactorJ: "1.5",
    packingFactor: "0.80",
    capWidthMm: "",
  });

  // Only material components with allowable_bending_stress_mpa
  const { components } = useComponents("material");
  const structuralMaterials = filterStructuralMaterials(components);

  const handleMaterialChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const id = parseInt(e.target.value, 10);
      if (!Number.isFinite(id)) {
        setInputs((prev) => ({ ...prev, materialId: null, sigmaAllowOverride: "" }));
        return;
      }
      const mat = structuralMaterials.find((m) => m.id === id) ?? null;
      const sigma = mat ? (getSigmaAllow(mat) ?? "") : "";
      setInputs((prev) => ({
        ...prev,
        materialId: id,
        sigmaAllowOverride: sigma !== "" ? String(sigma) : "",
      }));
    },
    [structuralMaterials],
  );

  const handleShapeChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    setInputs((prev) => ({
      ...prev,
      shape: e.target.value as SparShape,
      capWidthMm: "",
    }));
  }, []);

  const handleCompute = useCallback(() => {
    onCompute(inputs);
  }, [inputs, onCompute]);

  const inputClass =
    "h-7 rounded border border-border bg-background px-2 py-1 text-[12px] font-[family-name:var(--font-jetbrains-mono)] text-foreground focus:outline-none focus:ring-1 focus:ring-[#FF8400]/60";
  const labelClass =
    "block text-[11px] font-[family-name:var(--font-jetbrains-mono)] text-muted-foreground mb-0.5";

  return (
    <div className="rounded border border-border/40 bg-card" data-testid="spar-sizing-panel">
      {/* Collapsible header */}
      <button
        className="flex w-full items-center gap-2 px-4 py-2 text-left text-[13px] font-[family-name:var(--font-jetbrains-mono)] text-foreground hover:bg-card-muted/50"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        data-testid="spar-sizing-toggle"
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <span>Spar Sizing</span>
        {sizingResults && sizingResults.length > 0 && (
          <span className="ml-auto text-[11px] text-muted-foreground">
            {sizingResults.length} surface{sizingResults.length !== 1 ? "s" : ""}
          </span>
        )}
      </button>

      {open && (
        <div className="border-t border-border/30 px-4 py-3 space-y-4">
          {/* Inputs */}
          <div className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3 lg:grid-cols-4">
            {/* Material */}
            <div className="col-span-2 sm:col-span-1 lg:col-span-1">
              <label className={labelClass}>Material</label>
              <select
                className={`${inputClass} w-full`}
                value={inputs.materialId ?? ""}
                onChange={handleMaterialChange}
                data-testid="spar-material-select"
              >
                <option value="">— select —</option>
                {structuralMaterials.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Shape */}
            <div>
              <label className={labelClass}>Spar shape</label>
              <select
                className={`${inputClass} w-full`}
                value={inputs.shape}
                onChange={handleShapeChange}
                data-testid="spar-shape-select"
              >
                <option value="tube">Tube</option>
                <option value="rod">Rod</option>
                <option value="rectangular">Rectangular spar</option>
                <option value="capped">Capped spar</option>
              </select>
            </div>

            {/* σ_allow */}
            <div>
              <label className={labelClass}>σ_allow (MPa)</label>
              <input
                type="number"
                className={`${inputClass} w-full`}
                value={inputs.sigmaAllowOverride}
                onChange={(e) =>
                  setInputs((prev) => ({ ...prev, sigmaAllowOverride: e.target.value }))
                }
                placeholder="from material"
                min={0}
                step={1}
                data-testid="spar-sigma-input"
              />
            </div>

            {/* g_limit (read-only) */}
            <div>
              <label className={labelClass}>
                n (limit){gLimitFallback && <span className="ml-1 text-yellow-400">⚠</span>}
              </label>
              <input
                type="text"
                className={`${inputClass} w-full cursor-not-allowed opacity-60`}
                value={gLimit != null ? gLimit.toFixed(1) : "3.0 (default)"}
                readOnly
                data-testid="spar-glimit-display"
              />
            </div>

            {/* Safety factor j */}
            <div>
              <label className={labelClass}>Safety factor j</label>
              <input
                type="number"
                className={`${inputClass} w-full`}
                value={inputs.safetyFactorJ}
                onChange={(e) =>
                  setInputs((prev) => ({ ...prev, safetyFactorJ: e.target.value }))
                }
                min={1}
                step={0.1}
                data-testid="spar-j-input"
              />
            </div>

            {/* Packing factor */}
            <div>
              <label className={labelClass}>Packing factor</label>
              <input
                type="number"
                className={`${inputClass} w-full`}
                value={inputs.packingFactor}
                onChange={(e) =>
                  setInputs((prev) => ({ ...prev, packingFactor: e.target.value }))
                }
                min={0.01}
                max={1.0}
                step={0.01}
                data-testid="spar-packing-input"
              />
            </div>

            {/* Cap width — only for capped */}
            {inputs.shape === "capped" && (
              <div>
                <label className={labelClass}>Cap width b (mm)</label>
                <input
                  type="number"
                  className={`${inputClass} w-full`}
                  value={inputs.capWidthMm}
                  onChange={(e) =>
                    setInputs((prev) => ({ ...prev, capWidthMm: e.target.value }))
                  }
                  min={1}
                  step={1}
                  placeholder="required"
                  data-testid="spar-capwidth-input"
                />
              </div>
            )}
          </div>

          {/* Compute button */}
          <button
            className="rounded bg-[#FF8400] px-3 py-1.5 text-[12px] font-[family-name:var(--font-jetbrains-mono)] text-black hover:bg-[#FF8400]/80 disabled:opacity-50"
            onClick={handleCompute}
            disabled={isRunning || inputs.materialId == null}
            data-testid="spar-compute-button"
          >
            {isRunning ? "Computing…" : "Compute Spar Sizing"}
          </button>

          {/* Error */}
          {error && (
            <p
              className="rounded bg-red-900/30 px-2 py-1 text-[12px] text-red-400 font-[family-name:var(--font-jetbrains-mono)]"
              data-testid="spar-error"
            >
              {error}
            </p>
          )}

          {/* Results */}
          {sizingResults && sizingResults.length > 0 && (
            <div className="space-y-3" data-testid="spar-results">
              {sizingResults.map((r, i) => (
                <SizingResultCard key={i} result={r} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default SparSizingPanel;

// ---- Utility for external use (avoids prop-drilling) -----------------------

/**
 * Convert SparSizingInputs to the query params required by useSparSizing.run().
 * Returns null when required fields are missing (materialId).
 */
export function toSizingParams(inputs: SparSizingInputs): import("@/hooks/useSparSizing").SparSizingParams | null {
  if (inputs.materialId == null) return null;
  return {
    material_id: inputs.materialId,
    shape: inputs.shape,
    safety_factor_j: parsePositiveFloat(inputs.safetyFactorJ, 1.5),
    packing_factor: parsePositiveFloat(inputs.packingFactor, 0.8),
    sigma_allow_mpa_override:
      inputs.sigmaAllowOverride !== ""
        ? parsePositiveFloat(inputs.sigmaAllowOverride, 0) || undefined
        : undefined,
    cap_width_mm:
      inputs.shape === "capped" && inputs.capWidthMm !== ""
        ? parsePositiveFloat(inputs.capWidthMm, 0) || undefined
        : undefined,
  };
}
