"use client";

// Click-dummy (#881) — reusable visual primitives for the metrics dashboard.
// Pure presentational components driven by props. Exact numbers are always
// available: inline where there is room, otherwise on hover (tooltip).

import { renderSymbol } from "@/components/workbench/renderSymbol";
import type { GaugeData, MetricItem, Quality, SpeedMarker } from "./metricsMock";

const ZONE_COLOR: Record<SpeedMarker["kind"], string> = {
  stall: "bg-destructive",
  normal: "bg-success",
  caution: "bg-amber-400",
  ne: "bg-destructive",
};

const QUALITY_TEXT: Record<Quality, string> = {
  good: "text-success",
  caution: "text-amber-400",
  bad: "text-destructive",
};

const QUALITY_BAR: Record<Quality, string> = {
  good: "bg-success",
  caution: "bg-amber-400",
  bad: "bg-destructive",
};

// ── Hover tooltip (same mechanics as the existing Chip) ─────────
// Parent must be `group/m relative` (and ideally tabIndex={0} for keyboard).
export function Tip({ children }: { readonly children: React.ReactNode }) {
  return (
    <span
      aria-hidden="true"
      className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-1.5 hidden w-max max-w-[240px] -translate-x-1/2 rounded-lg border border-border bg-card px-2.5 py-1.5 text-[10px] font-normal leading-snug text-foreground shadow-lg group-hover/m:block group-focus-within/m:block"
    >
      {children}
    </span>
  );
}

// ── EnvelopeAxis ────────────────────────────────────────────────
export function EnvelopeAxis({
  markers,
  large = false,
}: {
  readonly markers: readonly SpeedMarker[];
  readonly large?: boolean;
}) {
  const max = Math.max(...markers.map((m) => m.value)) * 1.04;
  const pos = (v: number) => `${(v / max) * 100}%`;

  // contiguous colour zones derived from marker kinds
  const sorted = [...markers].sort((a, b) => a.value - b.value);
  const zones: { from: number; to: number; kind: SpeedMarker["kind"] }[] = [];
  let prev = 0;
  for (const m of sorted) {
    zones.push({ from: prev, to: m.value, kind: m.kind });
    prev = m.value;
  }

  return (
    <div className={large ? "pt-10 pb-1" : "py-4"}>
      <div className="relative h-2 w-full rounded-pill bg-card-muted">
        {zones.map((z) => (
          <div
            key={`${z.kind}-${z.to}`}
            className={`absolute top-0 h-2 ${ZONE_COLOR[z.kind]} opacity-25`}
            style={{ left: pos(z.from), width: `${((z.to - z.from) / max) * 100}%` }}
          />
        ))}
        {markers.map((m) => (
          <div
            key={m.symbol}
            className="group/m absolute top-1/2 -translate-x-1/2 -translate-y-1/2"
            style={{ left: pos(m.value) }}
            tabIndex={0}
          >
            <div className={`h-3.5 w-[3px] rounded-full ${ZONE_COLOR[m.kind]}`} />
            {large && (
              // slanted labels ABOVE the axis fan out instead of colliding
              <span className="absolute bottom-2.5 left-1/2 origin-bottom-left -rotate-[20deg] whitespace-nowrap font-[family-name:var(--font-geist-mono)] text-[10px] text-muted-foreground">
                {renderSymbol(m.symbol)}
              </span>
            )}
            {/* hover/focus detail tooltip — below the axis in large (clears the slanted labels), above in compact */}
            <span
              className={`pointer-events-none absolute left-1/2 z-50 hidden -translate-x-1/2 whitespace-nowrap rounded-lg border border-border bg-card px-2 py-1 font-[family-name:var(--font-geist-mono)] text-[10px] leading-snug shadow-lg group-hover/m:block group-focus-within/m:block ${large ? "top-5" : "bottom-5"}`}
            >
              <span className="font-semibold text-foreground">{renderSymbol(m.symbol)}</span>
              <span className="text-subtle-foreground"> · {m.label}</span>
              <br />
              <span className="text-foreground">{m.value.toFixed(1)} m/s{m.aoa != null ? ` @ ${m.aoa.toFixed(1)}°` : ""}</span>
            </span>
          </div>
        ))}
      </div>
      {large && (
        <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1">
          {markers.map((m) => (
            <span key={m.symbol} className="font-[family-name:var(--font-geist-mono)] text-[11px] text-muted-foreground">
              <span className={`mr-1 inline-block h-2 w-2 rounded-full align-middle ${ZONE_COLOR[m.kind]}`} />
              {renderSymbol(m.symbol)} {m.value.toFixed(1)}
              {m.aoa != null && <span className="text-subtle-foreground"> @{m.aoa.toFixed(1)}°</span>}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ── BulletGauge ─────────────────────────────────────────────────
export function BulletGauge({ g, large = false }: { readonly g: GaugeData; readonly large?: boolean }) {
  const span = g.max - g.min;
  const norm = (v: number) => `${((v - g.min) / span) * 100}%`;
  const fmt = g.format ?? ((v: number) => String(v));
  return (
    <div className="group/m relative" tabIndex={0}>
      <div className="mb-0.5 flex items-baseline justify-between gap-2">
        <span className="font-[family-name:var(--font-geist-mono)] text-[11px] text-muted-foreground">{renderSymbol(g.symbol)}</span>
        <span className={`font-[family-name:var(--font-geist-mono)] text-[12px] font-semibold ${QUALITY_TEXT[g.quality]}`}>
          {fmt(g.value)}
        </span>
      </div>
      <div className="relative h-1.5 w-full overflow-hidden rounded-pill bg-card-muted">
        {/* traffic-light scale: red / amber / green zones */}
        {g.zones.map((z) => (
          <div
            key={`${z.from}-${z.to}`}
            className={`absolute top-0 h-1.5 ${QUALITY_BAR[z.quality]} opacity-30`}
            style={{ left: norm(z.from), width: `${((z.to - z.from) / span) * 100}%` }}
          />
        ))}
        {/* value marker */}
        <div
          className={`absolute top-1/2 h-3 w-[3px] -translate-y-1/2 rounded-full ${QUALITY_BAR[g.quality]}`}
          style={{ left: norm(g.value) }}
        />
      </div>
      {large && <p className="mt-1.5 text-[10px] leading-snug text-subtle-foreground">{g.label} — {g.description}</p>}
      {!large && <Tip>{g.label} — {g.description}</Tip>}
    </div>
  );
}

// ── MacCgDiagram ────────────────────────────────────────────────
export function MacCgDiagram({
  cg, np, macStart, macLength, smPercent, inTarget, large = false,
}: {
  readonly cg: number; readonly np: number; readonly macStart: number; readonly macLength: number;
  readonly smPercent: number; readonly inTarget: boolean; readonly large?: boolean;
}) {
  const rel = (x: number) => `${((x - macStart) / macLength) * 100}%`;
  const smColor = inTarget ? "text-success" : "text-amber-400";
  const smBar = inTarget ? "bg-success" : "bg-amber-400";
  const lo = Math.min(cg, np);
  const hi = Math.max(cg, np);
  return (
    <div className={large ? "py-3" : "py-2"}>
      <div className="relative h-7 w-full rounded-md border border-border bg-card-muted">
        {/* MAC fill */}
        <div className="absolute inset-y-0 left-0 w-full rounded-md bg-foreground/[0.03]" />
        {/* SM span */}
        <div className={`absolute top-1/2 h-1 -translate-y-1/2 ${smBar} opacity-40`} style={{ left: rel(lo), width: `${((hi - lo) / macLength) * 100}%` }} />
        {/* CG marker */}
        <div className="group/m absolute top-0 h-full -translate-x-1/2" style={{ left: rel(cg) }} tabIndex={0}>
          <div className="h-full w-[2px] bg-primary" />
          <span className="absolute -top-0.5 left-1/2 -translate-x-1/2 -translate-y-full whitespace-nowrap font-[family-name:var(--font-geist-mono)] text-[9px] text-primary">CG</span>
          <Tip>CG = {cg.toFixed(3)} m</Tip>
        </div>
        {/* NP marker */}
        <div className="group/m absolute top-0 h-full -translate-x-1/2" style={{ left: rel(np) }} tabIndex={0}>
          <div className="h-full w-[2px] bg-muted-foreground" />
          <span className="absolute -bottom-0.5 left-1/2 -translate-x-1/2 translate-y-full whitespace-nowrap font-[family-name:var(--font-geist-mono)] text-[9px] text-muted-foreground">NP</span>
          <Tip>Neutral point = {np.toFixed(3)} m</Tip>
        </div>
        {/* LE / TE labels */}
        <span className="absolute -left-0.5 top-1/2 -translate-x-full -translate-y-1/2 pr-1 text-[9px] text-subtle-foreground">LE</span>
        <span className="absolute -right-0.5 top-1/2 translate-x-full -translate-y-1/2 pl-1 text-[9px] text-subtle-foreground">TE</span>
      </div>
      <div className="mt-2 flex items-baseline gap-3">
        <span className="font-[family-name:var(--font-geist-mono)] text-[12px] font-semibold">
          SM <span className={smColor}>{smPercent.toFixed(1)}%</span>
        </span>
        {large && (
          <span className="font-[family-name:var(--font-geist-mono)] text-[11px] text-muted-foreground">
            CG {cg.toFixed(3)} m · NP {np.toFixed(3)} m
          </span>
        )}
      </div>
    </div>
  );
}

// ── MetricCard ──────────────────────────────────────────────────
export function MetricCard({ item, large = false }: { readonly item: MetricItem; readonly large?: boolean }) {
  return (
    <div className="group/m relative flex min-w-[112px] flex-col rounded-md border border-border bg-card-muted px-3 py-2" tabIndex={0}>
      <span className="font-[family-name:var(--font-geist-mono)] text-[10px] uppercase tracking-wide text-subtle-foreground">{renderSymbol(item.symbol)}</span>
      <span className="font-[family-name:var(--font-geist-mono)] text-[14px] font-semibold text-foreground">
        {item.value}
        {item.unit && <span className="ml-1 text-[11px] font-normal text-muted-foreground">{item.unit}</span>}
      </span>
      {large ? (
        <span className="mt-0.5 text-[10px] leading-snug text-subtle-foreground">{item.label} — {item.description}</span>
      ) : (
        <Tip>{item.label} — {item.description}</Tip>
      )}
    </div>
  );
}
