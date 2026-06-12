"use client";

/**
 * Side-by-side version compare panel (gh-907).
 *
 * Given two `CompareOut` nodes, renders the key metrics columns in
 * two columns — Speed, Geometry, Quality, Tail, Powertrain — and
 * visually flags rows where the values differ between the two variants.
 *
 * The compare panel is a focused sibling to the MetricsDashboard.
 * It reuses the same adapter functions (toSpeedData, toGeometryItems, …)
 * and the BulletGauge / MetricCard primitives. It does NOT replicate the
 * full band — it renders a more compact two-column comparison table.
 *
 * Props:
 *   compareOut  — the full CompareOut payload from GET /aeroplanes/compare
 *   onClose     — called when the user closes the compare panel
 *   isLoading   — true while the request is in flight
 *   error       — error message string, or null
 */

import React from "react";
import { X, ArrowLeftRight } from "lucide-react";
import type { CompareOut, VersionNode } from "@/types/versioning";
import type { ComputationContext } from "@/hooks/useComputationContext";
import {
  toSpeedData,
  toGeometryItems,
  toBalanceData,
  toQualityGauges,
  toTail,
} from "@/lib/metricsAdapters";
import { renderSymbol } from "@/components/workbench/renderSymbol";
import { isAgentAuthor, authorLabel } from "@/lib/versionProvenance";
import type { GaugeData, MetricItem } from "@/components/workbench/metrics-dashboard/metricsTypes";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Cast the opaque metrics dict to ComputationContext for the adapters.
 *
 * The backend returns `assumption_computation_context` as a nested field, OR
 * the dict IS the context directly (flat). Either way we only treat it as a
 * real context when it carries the geometry the metric adapters require
 * (`mac_m`); a sparse/empty dict returns null so the adapters render "–" and
 * the disclosure line warns, instead of crashing on a missing field.
 */
function toCtx(metrics: Record<string, unknown> | null): ComputationContext | null {
  if (metrics == null) return null;
  const nested = metrics["assumption_computation_context"];
  const candidate =
    nested != null && typeof nested === "object"
      ? (nested as Record<string, unknown>)
      : metrics;
  if (typeof candidate["mac_m"] === "number") {
    return candidate as unknown as ComputationContext;
  }
  return null;
}

function nodeLabel(node: VersionNode): string {
  return node.version_label ?? node.name;
}

// ---------------------------------------------------------------------------
// Speed compare row
// ---------------------------------------------------------------------------

interface SpeedRowProps {
  readonly labelA: string;
  readonly labelB: string;
  readonly ctxA: ComputationContext | null;
  readonly ctxB: ComputationContext | null;
}

function formatSpeed(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return "–";
  return `${v.toFixed(1)} m/s`;
}

function SpeedCompareRow({ labelA, labelB, ctxA, ctxB }: SpeedRowProps) {
  const speedA = toSpeedData(ctxA);
  const speedB = toSpeedData(ctxB);

  const symbols = ["V_stall", "V_cruise", "V_max", "V_md"] as const;

  return (
    <CompareSection title="Speed">
      {symbols.map((sym) => {
        const mA = speedA?.markers.find((m) => m.symbol === sym);
        const mB = speedB?.markers.find((m) => m.symbol === sym);
        const valA = mA?.value;
        const valB = mB?.value;
        const differs = valA != null && valB != null && Math.abs(valA - valB) > 0.05;
        return (
          <MetricRow
            key={sym}
            symbol={sym}
            valA={formatSpeed(valA)}
            valB={formatSpeed(valB)}
            labelA={labelA}
            labelB={labelB}
            differs={differs}
          />
        );
      })}
    </CompareSection>
  );
}

// ---------------------------------------------------------------------------
// Geometry compare rows
// ---------------------------------------------------------------------------

interface GeometryRowsProps {
  readonly labelA: string;
  readonly labelB: string;
  readonly ctxA: ComputationContext | null;
  readonly ctxB: ComputationContext | null;
}

function GeometryCompareRows({ labelA, labelB, ctxA, ctxB }: GeometryRowsProps) {
  const itemsA = toGeometryItems(ctxA);
  const itemsB = toGeometryItems(ctxB);

  const symbols = ["S_ref", "MAC", "B_ref", "AR"] as const;

  return (
    <CompareSection title="Geometry">
      {symbols.map((sym) => {
        const iA = itemsA.find((i: MetricItem) => i.symbol === sym);
        const iB = itemsB.find((i: MetricItem) => i.symbol === sym);
        const differs = !!iA && !!iB && iA.value !== iB.value;
        const fmtItem = (i: MetricItem | undefined) => {
          if (i == null) return "–";
          return i.unit != null ? `${i.value} ${i.unit}` : i.value;
        };
        return (
          <MetricRow
            key={sym}
            symbol={sym}
            valA={fmtItem(iA)}
            valB={fmtItem(iB)}
            labelA={labelA}
            labelB={labelB}
            differs={differs}
          />
        );
      })}
      {/* Static margin */}
      {(() => {
        const balA = toBalanceData(ctxA);
        const balB = toBalanceData(ctxB);
        const smA = balA != null ? `${balA.smPercent.toFixed(1)}%` : "–";
        const smB = balB != null ? `${balB.smPercent.toFixed(1)}%` : "–";
        const differs = balA != null && balB != null &&
          Math.abs(balA.smPercent - balB.smPercent) > 0.1;
        return (
          <MetricRow
            symbol="SM"
            valA={smA}
            valB={smB}
            labelA={labelA}
            labelB={labelB}
            differs={differs}
          />
        );
      })()}
    </CompareSection>
  );
}

// ---------------------------------------------------------------------------
// Quality gauge compare rows
// ---------------------------------------------------------------------------

interface QualityRowsProps {
  readonly labelA: string;
  readonly labelB: string;
  readonly ctxA: ComputationContext | null;
  readonly ctxB: ComputationContext | null;
}

function QualityCompareRows({ labelA, labelB, ctxA, ctxB }: QualityRowsProps) {
  const gaugesA = toQualityGauges(ctxA);
  const gaugesB = toQualityGauges(ctxB);

  // Collect symbols present in either
  const allSymbols = Array.from(
    new Set([...gaugesA.map((g: GaugeData) => g.symbol), ...gaugesB.map((g: GaugeData) => g.symbol)]),
  );

  if (allSymbols.length === 0) return null;

  return (
    <CompareSection title="Quality">
      {allSymbols.map((sym) => {
        const gA = gaugesA.find((g: GaugeData) => g.symbol === sym);
        const gB = gaugesB.find((g: GaugeData) => g.symbol === sym);
        const fmt = gA?.format ?? gB?.format;
        const fmtVal = (g: GaugeData | undefined) => {
          if (g == null) return "–";
          return fmt ? fmt(g.value) : g.value.toFixed(2);
        };
        const differs = !!gA && !!gB && Math.abs(gA.value - gB.value) > 0.01;
        return (
          <MetricRow
            key={sym}
            symbol={sym}
            valA={fmtVal(gA)}
            valB={fmtVal(gB)}
            labelA={labelA}
            labelB={labelB}
            differs={differs}
          />
        );
      })}
    </CompareSection>
  );
}

// ---------------------------------------------------------------------------
// Tail + Powertrain compare rows
// ---------------------------------------------------------------------------

interface TailRowsProps {
  readonly labelA: string;
  readonly labelB: string;
  readonly ctxA: ComputationContext | null;
  readonly ctxB: ComputationContext | null;
}

function TailCompareRows({ labelA, labelB, ctxA, ctxB }: TailRowsProps) {
  const tailA = toTail(null, ctxA);
  const tailB = toTail(null, ctxB);

  if (tailA == null && tailB == null) return null;

  const vhA = tailA?.gauge.value;
  const vhB = tailB?.gauge.value;
  const differs = vhA != null && vhB != null && Math.abs(vhA - vhB) > 0.01;

  return (
    <CompareSection title="Tail">
      <MetricRow
        symbol="V_H"
        valA={vhA != null ? vhA.toFixed(2) : "–"}
        valB={vhB != null ? vhB.toFixed(2) : "–"}
        labelA={labelA}
        labelB={labelB}
        differs={differs}
      />
    </CompareSection>
  );
}

// Powertrain data comes from endurance, which the compare endpoint does not
// include separately. Rendering is deferred until the compare API exposes it.
// The component is retained as a placeholder for future expansion.

// ---------------------------------------------------------------------------
// Layout primitives
// ---------------------------------------------------------------------------

interface CompareSectionProps {
  readonly title: string;
  readonly children: React.ReactNode;
}

function CompareSection({ title, children }: CompareSectionProps) {
  const validChildren = React.Children.toArray(children).filter(Boolean);
  if (validChildren.length === 0) return null;
  return (
    <div className="mb-4">
      <div className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-subtle-foreground">
        {title}
      </div>
      <div className="flex flex-col gap-1">{children}</div>
    </div>
  );
}

interface MetricRowProps {
  readonly symbol: string;
  readonly valA: string;
  readonly valB: string;
  readonly labelA: string;
  readonly labelB: string;
  readonly differs: boolean;
}

function MetricRow({ symbol, valA, valB, labelA, labelB, differs }: MetricRowProps) {
  return (
    <div
      className={`grid grid-cols-[1fr_auto_1fr] items-center gap-2 rounded px-2 py-1 font-[family-name:var(--font-geist-mono)] text-[11px] ${
        differs ? "bg-amber-500/10" : ""
      }`}
      data-testid={`compare-row-${symbol}`}
      data-differs={differs ? "true" : undefined}
    >
      {/* A value */}
      <span
        aria-label={`${labelA}: ${valA}`}
        className={`text-right ${differs ? "font-semibold text-foreground" : "text-muted-foreground"}`}
      >
        {valA}
      </span>
      {/* Symbol */}
      <span className="min-w-[56px] text-center text-subtle-foreground">
        {renderSymbol(symbol)}
      </span>
      {/* B value */}
      <span
        aria-label={`${labelB}: ${valB}`}
        className={`text-left ${differs ? "font-semibold text-foreground" : "text-muted-foreground"}`}
      >
        {valB}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Analysis-context disclosure line (gh-963)
// ---------------------------------------------------------------------------

interface AnalysisContextLineProps {
  readonly metrics: Record<string, unknown> | null;
  readonly side: "A" | "B";
}

/**
 * Small muted line disclosing the computation assumptions behind the metrics
 * column. Sourced from metrics.total_mass_kg and
 * metrics.assumption_computation_context.
 *
 * If assumption_computation_context is absent or empty, renders an amber
 * warning instead so the reviewer knows the values may not be comparable.
 */
function AnalysisContextLine({ metrics, side }: AnalysisContextLineProps) {
  const testId = `compare-analysis-context-${side}`;

  // Use the same extraction as the metric rows (incl. the flat-payload
  // fallback) so the disclosure line and the numbers below it never disagree.
  const ctx = toCtx(metrics);

  // Aero operating-point fields are the real "analysis context". Each is
  // type-guarded because `ctx` is an unchecked cast — a malformed payload must
  // not crash the column.
  const aeroParts: string[] = [];
  if (ctx != null && typeof ctx.reynolds === "number") {
    aeroParts.push(`Re≈${Math.round(ctx.reynolds).toLocaleString("en-GB")}`);
  }
  if (ctx != null && typeof ctx.v_cruise_mps === "number") {
    aeroParts.push(`v_cruise ${ctx.v_cruise_mps.toFixed(1)} m/s`);
  }
  if (ctx != null && typeof ctx.computed_at === "string" && ctx.computed_at) {
    const d = new Date(ctx.computed_at);
    aeroParts.push(
      Number.isNaN(d.getTime())
        ? ctx.computed_at
        : d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }),
    );
  }

  // No usable operating point → warn, rather than render a blank/misleading
  // line or mass alone (metrics aren't comparable without the conditions).
  if (aeroParts.length === 0) {
    return (
      <div data-testid={testId} className="pl-6 mt-1 text-[9px] text-amber-400">
        <span aria-hidden="true">⚠</span> no analysis context — values may not be comparable
      </div>
    );
  }

  const massKg =
    metrics != null && typeof metrics["total_mass_kg"] === "number"
      ? (metrics["total_mass_kg"] as number)
      : null;
  const parts = massKg != null ? [`${massKg} kg`, ...aeroParts] : aeroParts;

  return (
    <div data-testid={testId} className="pl-6 mt-1 text-[9px] text-subtle-foreground">
      {parts.join(" · ")}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Node identity header (gh-961) — disambiguates even when version_label is
// shared between both sides.
// ---------------------------------------------------------------------------

/**
 * Format an ISO timestamp string to a short locale date + time string.
 * Uses "en-GB" for unambiguous day/month order (e.g. "1 Jan 2026, 08:00").
 */
function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-GB", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}


interface NodeIdentityHeaderProps {
  readonly node: VersionNode;
  readonly side: "A" | "B";
  readonly branchNameMap?: ReadonlyMap<number, string>;
  readonly metrics: Record<string, unknown> | null;
}

/**
 * Rich header for one compare column.
 *
 * Always shows (making both sides unambiguous even when `version_label` is
 * identical):
 *   - A/B marker chip (orange for A, violet for B)
 *   - `version_label ?? name` title
 *   - snapshot / HEAD tag
 *   - node id pill (#<id>)
 *   - branch pill (branch <branch_id> | legacy)
 *   - author chip (created_by)
 *   - timestamp (created_at, formatted)
 */
function NodeIdentityHeader({ node, side, branchNameMap, metrics }: NodeIdentityHeaderProps) {
  const isAi = isAgentAuthor(node.created_by);
  const sideColor =
    side === "A"
      ? { chip: "bg-primary/20 text-primary", dot: "bg-primary" }
      : { chip: "bg-violet-500/20 text-violet-400", dot: "bg-violet-400" };

  return (
    <div className="flex flex-col gap-1 px-2">
      {/* Title row: A/B marker + label + snapshot/HEAD tag */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <span
          className={`inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[9px] font-bold ${sideColor.chip}`}
          data-testid={`compare-side-marker-${side}`}
        >
          {side}
        </span>
        {/* Lane colour dot */}
        <span
          className={`inline-block h-2 w-2 shrink-0 rounded-full ${sideColor.dot}`}
          aria-hidden="true"
        />
        <span className="truncate font-[family-name:var(--font-jetbrains-mono)] text-[12px] font-semibold text-foreground">
          {nodeLabel(node)}
        </span>
        {node.is_immutable ? (
          <span className="rounded-full bg-amber-500/15 px-1 py-0.5 text-[9px] font-medium text-amber-400">
            snapshot
          </span>
        ) : (
          // VersionNode has no is_head, so we can't claim "HEAD" here — only
          // that the node is editable (non-immutable).
          <span className="rounded-full bg-emerald-500/15 px-1 py-0.5 text-[9px] font-medium text-emerald-400">
            editable
          </span>
        )}
        {isAi && (
          <span className="rounded-full bg-violet-500/15 px-1 py-0.5 text-[9px] font-medium text-violet-400">
            ai
          </span>
        )}
      </div>

      {/* Identity row: node id + branch + author */}
      <div className="flex items-center gap-1.5 flex-wrap pl-6">
        {/* Node id */}
        <span className="rounded bg-muted/60 px-1 py-0.5 font-[family-name:var(--font-geist-mono)] text-[9px] text-muted-foreground">
          #{node.id}
        </span>
        {/* Branch — show name from map when available, raw id as tooltip */}
        {node.branch_id != null ? (
          <span
            data-testid={`compare-branch-pill-${side}`}
            title={`branch id: ${node.branch_id}`}
            className="rounded bg-muted/60 px-1 py-0.5 font-[family-name:var(--font-geist-mono)] text-[9px] text-muted-foreground"
          >
            {branchNameMap?.get(node.branch_id) ?? `branch ${node.branch_id}`}
          </span>
        ) : (
          <span
            data-testid={`compare-branch-pill-${side}`}
            className="rounded bg-muted/60 px-1 py-0.5 font-[family-name:var(--font-geist-mono)] text-[9px] text-muted-foreground"
          >
            legacy
          </span>
        )}
        {/* Author */}
        <span className="rounded bg-muted/60 px-1 py-0.5 font-[family-name:var(--font-geist-mono)] text-[9px] text-muted-foreground">
          {authorLabel(node.created_by)}
        </span>
      </div>

      {/* Timestamp row */}
      <div className="pl-6">
        <time
          dateTime={node.created_at}
          className="font-[family-name:var(--font-geist-mono)] text-[9px] text-subtle-foreground"
        >
          {formatTimestamp(node.created_at)}
        </time>
      </div>

      {/* Optional version note */}
      {node.version_note && (
        <p className="pl-6 text-[10px] text-muted-foreground line-clamp-1">
          {node.version_note}
        </p>
      )}

      {/* Analysis-context disclosure line */}
      <AnalysisContextLine metrics={metrics} side={side} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export interface VersionCompareViewProps {
  readonly compareOut: CompareOut | null;
  readonly isLoading: boolean;
  readonly error: string | null;
  readonly onClose: () => void;
  /** Map from branch id → branch name, used to display human-readable branch names. */
  readonly branchNameMap?: ReadonlyMap<number, string>;
}

export function VersionCompareView({
  compareOut,
  isLoading,
  error,
  onClose,
  branchNameMap,
}: VersionCompareViewProps) {
  return (
    <div
      aria-label="Version compare"
      data-testid="version-compare-view"
      className="flex flex-col border-l border-border bg-card"
    >
      {/* Header */}
      <div className="flex shrink-0 items-center gap-2 border-b border-border px-4 py-3">
        <ArrowLeftRight size={15} className="text-muted-foreground" />
        <span className="flex-1 text-[13px] font-semibold text-foreground">
          Compare variants
        </span>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close compare panel"
          className="flex h-6 w-6 items-center justify-center rounded hover:bg-sidebar-accent"
        >
          <X size={13} />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {isLoading && (
          <p className="text-[12px] text-muted-foreground">Loading comparison…</p>
        )}

        {error != null && !isLoading && (
          <div role="alert" className="rounded border border-destructive/30 bg-destructive/10 p-3 text-[11px] text-destructive">
            {error}
          </div>
        )}

        {compareOut != null && !isLoading && (
          <>
            {/* Column headers */}
            <div className="mb-4 grid grid-cols-[1fr_auto_1fr] items-center gap-2">
              <NodeIdentityHeader
                node={compareOut.node_a}
                side="A"
                branchNameMap={branchNameMap}
                metrics={compareOut.metrics_a}
              />
              <div className="flex h-6 w-6 items-center justify-center text-muted-foreground/40">
                <ArrowLeftRight size={11} />
              </div>
              <NodeIdentityHeader
                node={compareOut.node_b}
                side="B"
                branchNameMap={branchNameMap}
                metrics={compareOut.metrics_b}
              />
            </div>

            {/* Column label row */}
            <div
              className="mb-2 grid grid-cols-[1fr_auto_1fr] gap-2 px-2 text-[10px] font-medium text-subtle-foreground"
              aria-hidden="true"
            >
              <span className="text-right">{nodeLabel(compareOut.node_a)}</span>
              <span className="min-w-[56px] text-center">metric</span>
              <span className="text-left">{nodeLabel(compareOut.node_b)}</span>
            </div>

            {/* Metric rows */}
            {(() => {
              const ctxA = toCtx(compareOut.metrics_a);
              const ctxB = toCtx(compareOut.metrics_b);
              const labelA = nodeLabel(compareOut.node_a);
              const labelB = nodeLabel(compareOut.node_b);
              return (
                <>
                  <SpeedCompareRow ctxA={ctxA} ctxB={ctxB} labelA={labelA} labelB={labelB} />
                  <GeometryCompareRows ctxA={ctxA} ctxB={ctxB} labelA={labelA} labelB={labelB} />
                  <QualityCompareRows ctxA={ctxA} ctxB={ctxB} labelA={labelA} labelB={labelB} />
                  <TailCompareRows ctxA={ctxA} ctxB={ctxB} labelA={labelA} labelB={labelB} />
                </>
              );
            })()}

            {/* Legend */}
            <div className="mt-4 flex items-center gap-2 border-t border-border pt-3 text-[10px] text-muted-foreground">
              <span className="inline-block h-2 w-3 rounded bg-amber-500/30" />
              Values that differ between the two variants are highlighted
            </div>
          </>
        )}

        {compareOut == null && !isLoading && error == null && (
          <p className="text-[12px] text-muted-foreground">No comparison data.</p>
        )}
      </div>
    </div>
  );
}
