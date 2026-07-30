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
import { ChevronDown, ChevronRight, AlertTriangle, Loader2 } from "lucide-react";

import type { SparShape, SparSizingResult, SparSizingStation } from "@/hooks/useSparSizing";
import type {
  SparPlanResult,
  SparPieceOut,
  SparInsertResult,
} from "@/hooks/useSparPlan";
import { useComponents } from "@/hooks/useComponents";
import {
  filterStructuralMaterials,
  getSigmaAllow,
  solvedDimLabel,
  feasibilityLabel,
  buildRootHeadline,
  buildMassSummary,
} from "@/lib/sparSizingHelpers";
import {
  sparGroupLabel,
  jointLabel,
  pieceDimsLabel,
  noSparRegionLabel,
  pieceExtentLabel,
  pieceJointLabel,
  splitNote,
  snapshotNote,
  mToMm,
  replaceWarning,
  pieceXcLabel,
  groupXcSuffix,
} from "@/lib/sparPlanHelpers";

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
  /** gh-1050: buildable spar plan (front/rear/reinforcement), or null. */
  plan?: SparPlanResult | null;
  /**
   * gh-1050: insert the plan into the wing. dry_run=true → preview,
   * dry_run=false → commit. When omitted, the "Add spar to wing" UI is hidden.
   */
  onInsert?: (dryRun: boolean) => Promise<SparInsertResult>;
  /** gh-1050: called after a successful commit so the parent can refresh the tree. */
  onSparInserted?: () => void;
  /**
   * gh-1060: revert a destructive commit by restoring its pre-insert snapshot.
   * When omitted, the Revert affordance is hidden.
   */
  onRevert?: (snapshotId: number) => Promise<void>;
}

// ---- Helpers ---------------------------------------------------------------

function parsePositiveFloat(s: string, fallback: number): number {
  const v = parseFloat(s);
  return Number.isFinite(v) && v > 0 ? v : fallback;
}

function StationRow({
  station,
}: {
  station: SparSizingStation;
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
                <StationRow key={idx} station={st} />
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---- Built-spar display (gh-1050) ------------------------------------------

/**
 * One buildable piece row: dims (OD×ID×wall), spanwise extent, joint,
 * feasibility. gh-1060: the joint position for a telescoping piece is the
 * NEXT piece's y_start; the last piece (no next) reads "to tip — no joint".
 */
function BuiltSparPieceRow({
  piece,
  next,
  index,
  showXc,
}: {
  piece: SparPieceOut;
  next: SparPieceOut | null;
  index: number;
  /** gh-1072: show this piece's % chord inline (the group's x/c varies). */
  showXc: boolean;
}) {
  return (
    <div
      className="flex flex-wrap items-center gap-x-3 gap-y-0.5 border-b border-border/20 px-2 py-1 text-[12px] font-[family-name:var(--font-jetbrains-mono)]"
      data-testid="built-spar-piece"
    >
      <span className="text-muted-foreground">#{index + 1}</span>
      <span className="tabular-nums text-foreground">{pieceDimsLabel(piece)}</span>
      {showXc && (
        <span className="tabular-nums text-muted-foreground">
          {pieceXcLabel(piece)}
        </span>
      )}
      <span className="tabular-nums text-muted-foreground">
        {pieceExtentLabel(piece)}
      </span>
      <span className="text-muted-foreground">
        joint: {pieceJointLabel(piece, next)}
      </span>
      <span className={piece.feasible ? "text-green-400" : "text-yellow-400"}>
        {piece.feasible ? "OK" : (piece.infeasibility_reason ?? "infeasible")}
      </span>
    </div>
  );
}

/** A spar group (front / rear / reinforcement) with its labelled pieces. */
function BuiltSparGroup({
  group,
  pieces,
}: {
  group: "front" | "rear" | "reinforcement";
  pieces: SparPieceOut[];
}) {
  if (pieces.length === 0) return null;
  // gh-1072: when every piece shares the same chordwise position, show it once
  // on the group label; otherwise show it per piece (xcSuffix is null).
  const xcSuffix = groupXcSuffix(pieces);
  return (
    <div className="space-y-0.5" data-testid={`built-spar-group-${group}`}>
      <p
        className={`text-[12px] font-[family-name:var(--font-jetbrains-mono)] ${
          group === "front" ? "text-[#FF8400]" : "text-muted-foreground"
        }`}
      >
        {sparGroupLabel(group)}
        {xcSuffix}
      </p>
      {pieces.map((p, i) => (
        <BuiltSparPieceRow
          key={i}
          piece={p}
          next={pieces[i + 1] ?? null}
          index={i}
          showXc={xcSuffix == null}
        />
      ))}
    </div>
  );
}

/**
 * Buildable-spar display: the two-spar plan grouped Front (main, index 0) /
 * Rear / Reinforcement, each piece as OD × ID (wall) × length in mm, with
 * joint type + feasibility. Exported for direct unit testing.
 */
export function BuiltSparSection({ plan }: { plan: SparPlanResult }) {
  const frontNoSparLabel = noSparRegionLabel(
    plan.front_no_spar_from_y,
    plan.front_pieces.length === 0,
  );
  const rearNoSparLabel = noSparRegionLabel(
    plan.rear_no_spar_from_y,
    plan.rear_pieces.length === 0,
  );
  return (
    <div
      className="rounded border border-border/40 bg-card p-3 text-[13px] space-y-3"
      data-testid="built-spar-section"
    >
      <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-foreground">
        Built spar (buildable pieces)
      </p>
      {!plan.feasible && (
        <div
          className="flex items-start gap-1 rounded bg-yellow-900/20 px-2 py-1 text-xs text-yellow-400"
          data-testid="built-spar-infeasible"
        >
          <AlertTriangle size={12} className="mt-0.5 shrink-0" />
          <span>{plan.infeasibility_reason ?? "Plan is not buildable as-is."}</span>
        </div>
      )}
      <BuiltSparGroup group="front" pieces={plan.front_pieces} />
      {frontNoSparLabel && (
        <p
          className="px-2 py-1 text-[11px] font-[family-name:var(--font-jetbrains-mono)] text-muted-foreground"
          data-testid="front-no-spar-label"
        >
          {frontNoSparLabel}
        </p>
      )}
      <BuiltSparGroup group="rear" pieces={plan.rear_pieces} />
      {rearNoSparLabel && (
        <p
          className="px-2 py-1 text-[11px] font-[family-name:var(--font-jetbrains-mono)] text-muted-foreground"
          data-testid="rear-no-spar-label"
        >
          {rearNoSparLabel}
        </p>
      )}
      <BuiltSparGroup
        group="reinforcement"
        pieces={plan.reinforcement ? [plan.reinforcement] : []}
      />
    </div>
  );
}

// ---- Add-spar-to-wing preview → confirm flow (gh-1050) ---------------------

export interface AddSparToWingFlowProps {
  /** The buildable plan. Button is disabled when the plan is infeasible. */
  plan: SparPlanResult;
  /** dry_run=true → preview; dry_run=false → commit. Returns the result or throws. */
  onInsert: (dryRun: boolean) => Promise<SparInsertResult>;
  /** Called after a successful commit so the parent can refresh the wing/tree. */
  onCommitted?: () => void;
  /**
   * gh-1060: revert a destructive commit by restoring its pre-insert snapshot.
   * Called with the snapshot id surfaced on the commit result; should refresh
   * the wing/construction data on success. Throws on error.
   */
  onRevert?: (snapshotId: number) => Promise<void>;
}

/**
 * "Add spar to wing" button → dry-run preview modal (per planned spare:
 * segment, spar_index, dims, placement, joint) with a REPLACE warning →
 * user confirm → commit. Exported for direct unit testing.
 */
export function AddSparToWingFlow({
  plan,
  onInsert,
  onCommitted,
  onRevert,
}: AddSparToWingFlowProps) {
  const [preview, setPreview] = useState<SparInsertResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [committed, setCommitted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // gh-1060: snapshot id surfaced on a destructive commit, the revert state,
  // and any revert error.
  const [snapshotId, setSnapshotId] = useState<number | null>(null);
  const [reverted, setReverted] = useState(false);
  const [revertError, setRevertError] = useState<string | null>(null);

  const openPreview = useCallback(async () => {
    setBusy(true);
    setError(null);
    setCommitted(false);
    setSnapshotId(null);
    setReverted(false);
    setRevertError(null);
    try {
      const res = await onInsert(true);
      setPreview(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }, [onInsert]);

  const confirm = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await onInsert(false);
      setCommitted(true);
      setSnapshotId(res.snapshot_id ?? null);
      setPreview(null);
      onCommitted?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }, [onInsert, onCommitted]);

  const revert = useCallback(async () => {
    if (snapshotId == null || !onRevert) return;
    setBusy(true);
    setRevertError(null);
    try {
      await onRevert(snapshotId);
      setReverted(true);
    } catch (err) {
      setRevertError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }, [snapshotId, onRevert]);

  const close = useCallback(() => {
    setPreview(null);
    setError(null);
  }, []);

  const warning = preview ? replaceWarning(preview.planned_spares) : null;
  const previewSplit = preview ? splitNote(preview.planned_segment_lengths) : null;
  const committedSnapshot = snapshotNote(snapshotId);

  return (
    <div className="space-y-2">
      <button
        className="rounded border border-[#FF8400] px-3 py-1.5 text-[12px] font-[family-name:var(--font-jetbrains-mono)] text-[#FF8400] hover:bg-[#FF8400]/10 disabled:opacity-40"
        onClick={openPreview}
        disabled={!plan.feasible || busy}
        data-testid="add-spar-to-wing-button"
        title={
          plan.feasible ? undefined : "Plan is infeasible — cannot add to wing"
        }
      >
        {busy && !preview ? "Loading preview…" : "Add spar to wing"}
      </button>

      {committed && (
        <div
          className="rounded bg-green-900/30 px-2 py-1.5 text-[12px] text-green-400 font-[family-name:var(--font-jetbrains-mono)] space-y-1"
          data-testid="add-spar-success"
        >
          <p>
            Spar added to the wing.
            {committedSnapshot && (
              <span className="ml-1 text-foreground">{committedSnapshot}.</span>
            )}
          </p>
          {snapshotId != null && !reverted && (
            <button
              className="rounded border border-border px-2 py-0.5 text-[11px] text-foreground hover:bg-card-muted/50 disabled:opacity-50"
              onClick={revert}
              disabled={busy || !onRevert}
              data-testid="add-spar-revert-button"
            >
              Revert
            </button>
          )}
          {reverted && (
            <p className="text-foreground" data-testid="add-spar-reverted">
              Reverted to the pre-insert snapshot.
            </p>
          )}
          {revertError && (
            <p
              className="text-red-400"
              data-testid="add-spar-revert-error"
            >
              {revertError}
            </p>
          )}
        </div>
      )}

      {error && !preview && (
        <p
          className="rounded bg-red-900/30 px-2 py-1 text-[12px] text-red-400 font-[family-name:var(--font-jetbrains-mono)]"
          data-testid="add-spar-error"
        >
          {error}
        </p>
      )}

      {preview && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          data-testid="add-spar-preview-modal"
        >
          <div className="max-h-[80vh] w-full max-w-2xl overflow-auto rounded-lg border border-border bg-card p-5 space-y-4">
            <h3 className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-foreground">
              Add spar to {preview.wing_name}
            </h3>

            {warning && (
              <div
                className="flex items-start gap-1 rounded bg-yellow-900/20 px-2 py-1.5 text-[12px] text-yellow-400"
                data-testid="add-spar-replace-warning"
              >
                <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                <span>{warning}</span>
              </div>
            )}

            {previewSplit && (
              <div
                className="flex items-start gap-1 rounded bg-[#FF8400]/10 px-2 py-1.5 text-[12px] text-[#FF8400]"
                data-testid="add-spar-split-note"
              >
                <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                <span>{previewSplit}</span>
              </div>
            )}

            {preview.warnings.length > 0 && (
              <ul className="space-y-0.5" data-testid="add-spar-warnings">
                {preview.warnings.map((w, i) => (
                  <li
                    key={i}
                    className="text-[11px] text-yellow-400 font-[family-name:var(--font-jetbrains-mono)]"
                  >
                    • {w}
                  </li>
                ))}
              </ul>
            )}

            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] border-collapse text-left">
                <thead>
                  <tr className="border-b border-border/50 text-[11px] text-muted-foreground font-[family-name:var(--font-jetbrains-mono)]">
                    <th className="px-2 py-1">segment</th>
                    <th className="px-2 py-1">spar_index</th>
                    <th className="px-2 py-1">role</th>
                    <th className="px-2 py-1">OD × ID (mm)</th>
                    <th className="px-2 py-1">length (mm)</th>
                    <th className="px-2 py-1">joint</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.planned_spares.map((sp, i) => (
                    <tr
                      key={i}
                      className="border-b border-border/30 font-[family-name:var(--font-jetbrains-mono)] text-[12px]"
                      data-testid="planned-spare-row"
                    >
                      <td className="px-2 py-1 tabular-nums">{sp.segment_index}</td>
                      <td
                        className={`px-2 py-1 tabular-nums ${
                          sp.spar_index === 0 ? "font-bold text-[#FF8400]" : ""
                        }`}
                      >
                        {sp.spar_index}
                        {sp.spar_index === 0 ? " (main)" : ""}
                      </td>
                      <td className="px-2 py-1">{sp.role}</td>
                      <td className="px-2 py-1 tabular-nums">
                        {mToMm(sp.outer_d)} × {mToMm(sp.inner_d)}
                      </td>
                      <td className="px-2 py-1 tabular-nums">
                        {mToMm(sp.spare_length, 0)}
                      </td>
                      <td className="px-2 py-1">{jointLabel(sp.joint_note)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {error && (
              <p
                className="rounded bg-red-900/30 px-2 py-1 text-[12px] text-red-400 font-[family-name:var(--font-jetbrains-mono)]"
                data-testid="add-spar-preview-error"
              >
                {error}
              </p>
            )}

            <div className="flex items-center justify-end gap-2">
              <button
                className="rounded border border-border px-3 py-1.5 text-[12px] font-[family-name:var(--font-jetbrains-mono)] text-foreground hover:bg-card-muted/50"
                onClick={close}
                disabled={busy}
                data-testid="add-spar-cancel"
              >
                Cancel
              </button>
              <button
                className="flex items-center gap-1.5 rounded bg-[#FF8400] px-3 py-1.5 text-[12px] font-[family-name:var(--font-jetbrains-mono)] text-black hover:bg-[#FF8400]/80 disabled:opacity-50"
                onClick={confirm}
                disabled={busy || !preview.feasible}
                data-testid="add-spar-confirm"
              >
                {busy && <Loader2 size={12} className="animate-spin" />}
                Confirm &amp; add
              </button>
            </div>
          </div>
        </div>
      )}
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
  plan = null,
  onInsert,
  onSparInserted,
  onRevert,
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

          {/* gh-1050: Built spar (buildable pieces) + Add to wing */}
          {plan && (
            <div className="space-y-3" data-testid="built-spar-block">
              <BuiltSparSection plan={plan} />
              {onInsert && (
                <AddSparToWingFlow
                  plan={plan}
                  onInsert={onInsert}
                  onCommitted={onSparInserted}
                  onRevert={onRevert}
                />
              )}
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
