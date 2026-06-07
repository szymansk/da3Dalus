"use client";

// Click-dummy (#881, v2) — compact metrics BAND: five columns inside a fixed
// ~20vh-tall strip. All columns are equal compact tiles by default; activating
// one makes it full width (others shrink to narrow vertical tabs). The band
// height never changes — content scrolls inside a column if needed.
//
// This component is DATA-DRIVEN: all computed values are passed via props
// from MetricsDashboardContainer. No mock data is imported at runtime.

import { useState } from "react";
import { Wind, Gauge, Ruler, BatteryCharging, ChevronUp, ChevronDown } from "lucide-react";
import { renderSymbol } from "@/components/workbench/renderSymbol";
import { MetricColumn, type ColumnMode } from "./MetricColumn";
import { EnvelopeAxis, BulletGauge, MetricCard, Tip } from "./primitives";
import { PlanformDiagram } from "./PlanformDiagram";
import type {
  SpeedData,
  BalanceData,
  GaugeData,
  MetricItem,
} from "./metricsTypes";
import type { TailAdapterResult, PowertrainAdapterResult } from "@/lib/metricsAdapters";

// ---------------------------------------------------------------------------
// Props interface
// ---------------------------------------------------------------------------

export interface MetricsDashboardProps {
  /** Speed envelope data for the Speed column. null = loading/unavailable. */
  readonly speed: SpeedData | null;
  /** Flat geometry MetricItem[] for the Geometry column tile. */
  readonly geometryItems: readonly MetricItem[];
  /** Balance data for the Geometry column large view. null = not yet computed. */
  readonly balance: BalanceData | null;
  /** Quality gauge array for the Quality column. */
  readonly qualityGauges: readonly GaugeData[];
  /** Raw polar numbers (Re, C_D0, k, C_L_max, C_L_md) shown in large state. */
  readonly qualityRaw: readonly MetricItem[];
  /** Tail sizing adapter result — null for tailless or unavailable. */
  readonly tail: TailAdapterResult | null;
  /** Powertrain adapter result. */
  readonly powertrain: PowertrainAdapterResult;
  /** True while any of the backing hooks are still loading. */
  readonly loading?: boolean;
  /** True when no aeroplane is selected. */
  readonly empty?: boolean;
}

// ---------------------------------------------------------------------------
// Tiny helpers
// ---------------------------------------------------------------------------

const QCOL = { good: "text-success", caution: "text-amber-400", bad: "text-destructive" } as const;

function smInTargetClass(smInTarget: boolean) {
  return smInTarget ? "text-success" : "text-amber-400";
}

function Placeholder({ loading }: { readonly loading: boolean }) {
  return (
    <div className="flex h-full items-center justify-center text-[11px] text-muted-foreground">
      {loading ? "Loading…" : "–"}
    </div>
  );
}

function MiniKV({ items }: { readonly items: readonly MetricItem[] }) {
  return (
    <div className="grid grid-cols-2 gap-x-2 gap-y-1.5">
      {items.map((m) => (
        <div key={m.symbol} className="group/m relative min-w-0" tabIndex={0}>
          <div className="truncate font-[family-name:var(--font-geist-mono)] text-[10px] uppercase tracking-wide text-subtle-foreground">{renderSymbol(m.symbol)}</div>
          <div className="truncate font-[family-name:var(--font-geist-mono)] text-[12px] font-semibold text-foreground">
            {m.value}{m.unit && <span className="ml-0.5 text-[9px] font-normal text-muted-foreground">{m.unit}</span>}
          </div>
          <Tip>{m.label} — {m.description}</Tip>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Speed column
// ---------------------------------------------------------------------------

function SpeedTile({ speed, loading }: { readonly speed: SpeedData | null; readonly loading: boolean }) {
  if (speed == null) return <Placeholder loading={loading} />;
  const vStall = speed.markers.find((m) => m.symbol === "V_stall");
  const vCruise = speed.markers.find((m) => m.symbol === "V_cruise");
  const vMax = speed.markers.find((m) => m.symbol === "V_max") ?? speed.markers.find((m) => m.symbol === "V_md");
  return (
    <div>
      <EnvelopeAxis markers={speed.markers} />
      <div className="mt-1 flex justify-between font-[family-name:var(--font-geist-mono)] text-[10px] text-muted-foreground">
        {vStall && (
          <span className="group/m relative" tabIndex={0}>
            stall <span className="text-foreground">{vStall.value.toFixed(1)}</span>
            <Tip>Stall speed — slowest controllable speed (1g).</Tip>
          </span>
        )}
        {vCruise && (
          <span className="group/m relative" tabIndex={0}>
            cruise <span className="text-foreground">{vCruise.value.toFixed(1)}</span>
            <Tip>Design cruise speed.</Tip>
          </span>
        )}
        {vMax && (
          <span className="group/m relative" tabIndex={0}>
            max <span className="text-foreground">{vMax.value.toFixed(1)}</span>
            <Tip>Max operating speed.</Tip>
          </span>
        )}
      </div>
    </div>
  );
}

function SpeedLarge({ speed, loading }: { readonly speed: SpeedData | null; readonly loading: boolean }) {
  if (speed == null) {
    return (
      <div className="flex h-full items-center justify-center text-[11px] text-muted-foreground">
        {loading ? "Loading…" : "No speed data"}
      </div>
    );
  }
  return <EnvelopeAxis markers={speed.markers} large />;
}

// ---------------------------------------------------------------------------
// Quality column
// ---------------------------------------------------------------------------

function QualityTile({ qualityGauges, loading }: { readonly qualityGauges: readonly GaugeData[]; readonly loading: boolean }) {
  return (
    <div className="flex flex-col gap-1 pt-0.5">
      {qualityGauges.slice(0, 3).map((g) => <BulletGauge key={g.symbol} g={g} />)}
      {qualityGauges.length === 0 && <Placeholder loading={loading} />}
    </div>
  );
}

function QualityLarge({ qualityGauges, qualityRaw }: { readonly qualityGauges: readonly GaugeData[]; readonly qualityRaw: readonly MetricItem[] }) {
  return (
    <div>
      <div className="grid grid-cols-3 gap-x-5 gap-y-2.5 md:grid-cols-6">
        {qualityGauges.map((g) => <BulletGauge key={g.symbol} g={g} />)}
      </div>
      {qualityRaw.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 border-t border-border pt-1.5">
          {qualityRaw.map((r) => (
            <span key={r.symbol} className="group/m relative font-[family-name:var(--font-geist-mono)] text-[10px] text-muted-foreground" tabIndex={0}>
              {renderSymbol(r.symbol)} <span className="text-foreground">{r.value}</span>
              <Tip>{r.label} — {r.description}</Tip>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Geometry column — balance + tail sub-panels
// ---------------------------------------------------------------------------

function BalancePanel({ balance, loading }: { readonly balance: BalanceData | null; readonly loading: boolean }) {
  if (balance == null) {
    return <p className="text-[10px] text-muted-foreground">{loading ? "Loading…" : "No balance data"}</p>;
  }
  const smInTarget = balance.smPercent >= balance.targetSmMin && balance.smPercent <= balance.targetSmMax;
  const smStr = `${balance.smPercent.toFixed(1)}%`;
  const targetRange = `${balance.targetSmMin.toFixed(0)}–${balance.targetSmMax.toFixed(0)}`;
  return (
    <>
      <div className="group/m relative" tabIndex={0}>
        SM{" "}
        <span className={smInTargetClass(smInTarget)}>{smStr}</span>
        {" · "}CG {balance.cg.toFixed(3)} m{" · "}NP {balance.np.toFixed(3)} m
        <Tip>Static margin = (NP − CG) / MAC. CG must sit ahead of the neutral point. Target {targetRange}% MAC.</Tip>
      </div>
      <p className="text-[10px] text-subtle-foreground">
        {balance.cgComponent != null && `Component CG ${balance.cgComponent.toFixed(3)} m · `}
        target SM {targetRange}% MAC
      </p>
    </>
  );
}

function TailPanel({ tail, loading }: { readonly tail: TailAdapterResult | null; readonly loading: boolean }) {
  if (tail == null) {
    return <p className="text-[10px] text-muted-foreground">{loading ? "Loading…" : "No tail data"}</p>;
  }
  return (
    <>
      <div className="group/m relative inline-block text-[9px] uppercase tracking-wide text-subtle-foreground" tabIndex={0}>
        Tail{" · "}<span className="text-muted-foreground">{tail.mission}</span>{" · "}RC rule of thumb
        <Tip>{tail.bandsNote}</Tip>
      </div>
      <BulletGauge g={tail.gauge} />
      <div className="flex flex-wrap gap-x-3 gap-y-0.5 font-[family-name:var(--font-geist-mono)]">
        {tail.items.map((t) => (
          <span key={t.symbol} className="group/m relative text-[10px] text-muted-foreground" tabIndex={0}>
            {renderSymbol(t.symbol)}{" "}
            <span className="text-foreground">{t.value}{t.unit ? ` ${t.unit}` : ""}</span>
            <Tip>{t.label} — {t.description}</Tip>
          </span>
        ))}
      </div>
    </>
  );
}

interface GeometryColProps {
  readonly geometryItems: readonly MetricItem[];
  readonly balance: BalanceData | null;
  readonly tail: TailAdapterResult | null;
  readonly loading: boolean;
}

function GeometryTile({ geometryItems, balance, tail, loading }: GeometryColProps) {
  const tailGauge = tail?.gauge ?? null;
  const smInTarget = balance != null
    ? balance.smPercent >= balance.targetSmMin && balance.smPercent <= balance.targetSmMax
    : false;
  return (
    <div className="grid h-full grid-cols-3 content-center gap-x-3 gap-y-2 pt-0.5 font-[family-name:var(--font-geist-mono)]">
      {geometryItems.map((m) => (
        <div key={m.symbol} className="group/m relative min-w-0" tabIndex={0}>
          <div className="truncate text-[10px] uppercase tracking-wide text-subtle-foreground">{renderSymbol(m.symbol)}</div>
          <div className="truncate text-[13px] font-semibold text-foreground">
            {m.value}{m.unit && <span className="ml-0.5 text-[9px] font-normal text-muted-foreground">{m.unit}</span>}
          </div>
          <Tip>{m.label} — {m.description}</Tip>
        </div>
      ))}
      {balance != null && (
        <div className="group/m relative" tabIndex={0}>
          <div className="text-[10px] uppercase tracking-wide text-subtle-foreground">SM</div>
          <div className={`text-[13px] font-bold ${smInTargetClass(smInTarget)}`}>{balance.smPercent.toFixed(1)}%</div>
          <Tip>Static margin as % of MAC. Target {balance.targetSmMin.toFixed(0)}–{balance.targetSmMax.toFixed(0)}%.</Tip>
        </div>
      )}
      {tailGauge != null && (
        <div className="group/m relative" tabIndex={0}>
          <div className="text-[10px] uppercase tracking-wide text-subtle-foreground">{renderSymbol("V_H")}</div>
          <div className={`text-[13px] font-bold ${QCOL[tailGauge.quality]}`}>{tailGauge.value.toFixed(2)}</div>
          <Tip>{tailGauge.label} — {tailGauge.description}</Tip>
        </div>
      )}
      {geometryItems.length === 0 && balance == null && (
        <div className="col-span-3"><Placeholder loading={loading} /></div>
      )}
    </div>
  );
}

function GeometryLarge({ geometryItems, balance, tail, loading }: GeometryColProps) {
  const smInTarget = balance != null
    ? balance.smPercent >= balance.targetSmMin && balance.smPercent <= balance.targetSmMax
    : false;
  const cgFrac = balance != null ? (balance.cg - balance.macStart) / balance.macLength : undefined;
  const npFrac = balance != null ? (balance.np - balance.macStart) / balance.macLength : undefined;
  const smStr = balance != null ? `${balance.smPercent.toFixed(1)}%` : undefined;

  return (
    <div className="flex h-full items-stretch gap-4 pt-1">
      <div className="flex h-full min-h-0 flex-[2] items-center justify-center">
        <PlanformDiagram
          bRef={geometryItems.find((m) => m.symbol === "B_ref")?.value ?? "–"}
          mac={geometryItems.find((m) => m.symbol === "MAC")?.value ?? "–"}
          sRef={geometryItems.find((m) => m.symbol === "S_ref")?.value ?? "–"}
          ar={geometryItems.find((m) => m.symbol === "AR")?.value ?? "–"}
          annotate
          cgFrac={cgFrac}
          npFrac={npFrac}
          sm={smStr}
          smOk={smInTarget}
        />
      </div>
      <div className="flex flex-1 flex-col justify-center gap-1.5 font-[family-name:var(--font-geist-mono)] text-[11px]">
        <div className="text-[9px] uppercase tracking-wide text-subtle-foreground">Balance</div>
        <BalancePanel balance={balance} loading={loading} />
      </div>
      <div className="flex flex-1 flex-col justify-center gap-1.5">
        <TailPanel tail={tail} loading={loading} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Powertrain column
// ---------------------------------------------------------------------------

function PowertrainLarge({ powertrain }: { readonly powertrain: PowertrainAdapterResult }) {
  const { detail } = powertrain;
  const pReqStr = detail.pReqVmd != null ? `P_req @V_md ${detail.pReqVmd.toFixed(1)} W` : "P_req @V_md –";
  return (
    <div>
      <div className="flex flex-wrap gap-2 pt-1">
        {powertrain.items.map((m) => <MetricCard key={m.symbol} item={m} large />)}
      </div>
      <p className="mt-2 border-t border-border pt-1.5 text-[10px] text-muted-foreground">
        {pReqStr}
        {detail.pMarginClass != null && (
          <> · reserve <span className="text-amber-400">{detail.pMarginClass}</span></>
        )}
        {detail.batteryMassPredicted != null && <> · battery ~{detail.batteryMassPredicted} g</>}
        {" · "}<span className="text-amber-400">{detail.confidence}</span>
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Collapse handle
// ---------------------------------------------------------------------------

function MetricsHandle({
  open,
  onToggle,
  collapsedItems,
}: {
  readonly open: boolean;
  readonly onToggle: () => void;
  readonly collapsedItems?: readonly { sym: string; val: string }[];
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-expanded={open}
      aria-label={open ? "Collapse metrics" : "Expand metrics"}
      className="flex h-8 w-full shrink-0 items-center gap-3 rounded-t-xl border border-border bg-sidebar px-4 text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-foreground"
    >
      {open ? <ChevronDown size={15} /> : <ChevronUp size={15} />}
      <span className="text-[12px] font-medium">Metrics</span>
      {!open && collapsedItems && (
        <span className="flex min-w-0 items-center gap-2 truncate font-[family-name:var(--font-geist-mono)] text-[11px] text-subtle-foreground">
          {collapsedItems.map((c, i) => (
            <span key={c.sym} className="whitespace-nowrap">
              {i > 0 && <span className="mr-2 text-border">·</span>}
              {renderSymbol(c.sym)} <span className="text-muted-foreground">{c.val}</span>
            </span>
          ))}
        </span>
      )}
      <span className="flex-1" />
      <span className="text-[10px] text-subtle-foreground">{open ? "hide" : "show"}</span>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Headline builders (pure functions, not components)
// ---------------------------------------------------------------------------

function buildSpeedHeadline(speed: SpeedData | null): string {
  if (speed == null) return "No data";
  const parts: string[] = [];
  const vStall = speed.markers.find((m) => m.symbol === "V_stall");
  const vCruise = speed.markers.find((m) => m.symbol === "V_cruise");
  const vMax = speed.markers.find((m) => m.symbol === "V_max") ?? speed.markers.find((m) => m.symbol === "V_md");
  if (vStall) parts.push(`V_stall ${vStall.value.toFixed(1)}`);
  if (vCruise) parts.push(`V_cruise ${vCruise.value.toFixed(1)}`);
  if (vMax) parts.push(`V_max ${vMax.value.toFixed(1)}`);
  return parts.join(" · ") || "No data";
}

function buildQualityHeadline(gauges: readonly GaugeData[]): string {
  const parts: string[] = [];
  const ld = gauges.find((g) => g.symbol === "(L/D)_max");
  const rho = gauges.find((g) => g.symbol === "ρ");
  if (ld) parts.push(`(L/D) ${ld.value.toFixed(1)}`);
  if (rho) parts.push(`ρ ${rho.value.toFixed(2)}`);
  return parts.join(" · ") || "No data";
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

type ColId = "speed" | "geometry" | "guete" | "antrieb";
const COL_IDS: ColId[] = ["speed", "geometry", "guete", "antrieb"];

export function MetricsDashboard({
  speed,
  geometryItems,
  balance,
  qualityGauges,
  qualityRaw,
  tail,
  powertrain,
  loading = false,
  empty = false,
}: MetricsDashboardProps) {
  const [active, setActive] = useState<ColId | null>(null);
  const [open, setOpen] = useState(true);

  const modeOf = (id: ColId): ColumnMode => {
    if (active === null) return "tile";
    return active === id ? "large" : "tab";
  };

  const vCruise = speed?.markers.find((m) => m.symbol === "V_cruise");
  const ldGauge = qualityGauges.find((g) => g.symbol === "(L/D)_max");
  const arItem = geometryItems.find((m) => m.symbol === "AR");
  const enduranceItem = powertrain.items.find((m) => m.symbol === "Endurance");
  const tailGauge = tail?.gauge ?? null;
  const smPct = balance?.smPercent ?? null;

  const smLabel = smPct != null ? `SM ${smPct.toFixed(1)}%` : "SM –";
  const vhLabel = tailGauge != null ? `V_H ${tailGauge.value.toFixed(2)}` : "V_H –";
  const geometryHeadline = [arItem ? `AR ${arItem.value}` : null, smLabel, vhLabel]
    .filter(Boolean).join(" · ");

  const powertrainHeadline = enduranceItem
    ? `Endurance ${enduranceItem.value} ${enduranceItem.unit ?? ""}`.trimEnd()
    : "No data";

  const collapsedItems = [
    { sym: "V_cruise", val: vCruise != null ? vCruise.value.toFixed(0) : "–" },
    { sym: "AR", val: arItem?.value ?? "–" },
    { sym: "(L/D)_max", val: ldGauge != null ? ldGauge.value.toFixed(0) : "–" },
    { sym: "SM", val: smPct != null ? `${smPct.toFixed(0)}%` : "–" },
    {
      sym: "Endurance",
      val: enduranceItem != null ? `${enduranceItem.value} ${enduranceItem.unit ?? ""}`.trimEnd() : "–",
    },
  ] as const;

  const cols: Record<ColId, { title: string; icon: typeof Wind; headline: string; tile: React.ReactNode; large: React.ReactNode }> = {
    speed: {
      title: "Speed", icon: Wind,
      headline: buildSpeedHeadline(speed),
      tile: <SpeedTile speed={speed} loading={loading} />,
      large: <SpeedLarge speed={speed} loading={loading} />,
    },
    guete: {
      title: "Quality", icon: Gauge,
      headline: buildQualityHeadline(qualityGauges),
      tile: <QualityTile qualityGauges={qualityGauges} loading={loading} />,
      large: <QualityLarge qualityGauges={qualityGauges} qualityRaw={qualityRaw} />,
    },
    geometry: {
      title: "Geometry", icon: Ruler,
      headline: geometryHeadline,
      tile: <GeometryTile geometryItems={geometryItems} balance={balance} tail={tail} loading={loading} />,
      large: <GeometryLarge geometryItems={geometryItems} balance={balance} tail={tail} loading={loading} />,
    },
    antrieb: {
      title: "Powertrain", icon: BatteryCharging,
      headline: powertrainHeadline,
      tile: <div className="pt-1"><MiniKV items={powertrain.items} /></div>,
      large: <PowertrainLarge powertrain={powertrain} />,
    },
  };

  // Empty state (no aeroplane selected)
  if (empty) {
    return (
      <div className="w-full" data-testid="metrics-band">
        <MetricsHandle open={open} onToggle={() => setOpen((v) => !v)} />
        <div className={`grid transition-[grid-template-rows] duration-300 ease-out ${open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"}`}>
          <div className="min-h-0 overflow-hidden">
            <div className="h-[15vh] min-h-[118px] w-full pt-2" data-testid="metrics-band-body">
              <div className="flex h-full w-full items-center justify-center rounded-b-lg border border-border bg-card">
                <span className="text-[13px] text-muted-foreground">Select an aeroplane to view metrics</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full" data-testid="metrics-band">
      {/* persistent handle — sits ABOVE the band; toggles it open/closed */}
      <MetricsHandle
        open={open}
        onToggle={() => setOpen((v) => !v)}
        collapsedItems={collapsedItems}
      />
      {/* sliding band — collapses to 0 height via the grid-rows trick */}
      <div className={`grid transition-[grid-template-rows] duration-300 ease-out ${open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"}`}>
        <div className="min-h-0 overflow-hidden">
          <div className="h-[15vh] min-h-[118px] w-full pt-2" data-testid="metrics-band-body">
            <div className="flex h-full w-full gap-2">
              {COL_IDS.map((id) => (
                <MetricColumn
                  key={id}
                  title={cols[id].title}
                  icon={cols[id].icon}
                  mode={modeOf(id)}
                  onActivate={() => setActive(id)}
                  onCollapse={() => setActive(null)}
                  headline={cols[id].headline}
                  tile={cols[id].tile}
                  large={cols[id].large}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
