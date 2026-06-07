"use client";

// Click-dummy (#881, v2) — compact metrics BAND: five columns inside a fixed
// ~20vh-tall strip. All columns are equal compact tiles by default; activating
// one makes it full width (others shrink to narrow vertical tabs). The band
// height never changes — content scrolls inside a column if needed.

import { useState } from "react";
import { Wind, Gauge, Ruler, BatteryCharging, ChevronUp, ChevronDown } from "lucide-react";
import { renderSymbol } from "@/components/workbench/renderSymbol";
import { MetricColumn, type ColumnMode } from "./MetricColumn";
import { EnvelopeAxis, BulletGauge, MetricCard, Tip } from "./primitives";
import { PlanformDiagram } from "./PlanformDiagram";
import {
  antriebDetailMock, antriebMock, balanceMock, geometryMock,
  gueteMock, gueteRawMock, speedMock, tailBandsNote, tailItems, tailMission, tailVhGauge, type MetricItem,
} from "./metricsMock";

type Id = "speed" | "geometry" | "guete" | "antrieb";
const IDS: Id[] = ["speed", "geometry", "guete", "antrieb"];
const QCOL = { good: "text-success", caution: "text-amber-400", bad: "text-destructive" } as const;

// tiny key/value used in compact tiles
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

export function MetricsDashboard() {
  const [active, setActive] = useState<Id | null>(null);
  const [open, setOpen] = useState(true);
  function modeOf(id: Id): ColumnMode {
    if (active === null) return "tile";
    return active === id ? "large" : "tab";
  }

  const smInTarget = balanceMock.smPercent >= balanceMock.targetSmMin && balanceMock.smPercent <= balanceMock.targetSmMax;
  // CG/NP as a fraction of MAC (LE → TE) for placement on the planform centreline
  const cgFrac = (balanceMock.cg - balanceMock.macStart) / balanceMock.macLength;
  const npFrac = (balanceMock.np - balanceMock.macStart) / balanceMock.macLength;
  const smStr = `${balanceMock.smPercent.toFixed(1)}%`;

  const cols: Record<Id, { title: string; icon: typeof Wind; headline: string; tile: React.ReactNode; large: React.ReactNode }> = {
    speed: {
      title: "Speed", icon: Wind, headline: "V_stall 8.2 · V_cruise 14.0 · V_max 22.0",
      tile: (
        <div>
          <EnvelopeAxis markers={speedMock.markers} />
          <div className="mt-1 flex justify-between font-[family-name:var(--font-geist-mono)] text-[10px] text-muted-foreground">
            <span className="group/m relative" tabIndex={0}>stall <span className="text-foreground">8.2</span><Tip>Stall speed — slowest controllable speed (1g).</Tip></span>
            <span className="group/m relative" tabIndex={0}>cruise <span className="text-foreground">14.0</span><Tip>Design cruise speed.</Tip></span>
            <span className="group/m relative" tabIndex={0}>max <span className="text-foreground">22.0</span><Tip>Max operating speed.</Tip></span>
          </div>
        </div>
      ),
      large: <EnvelopeAxis markers={speedMock.markers} large />,
    },
    guete: {
      title: "Güte", icon: Gauge, headline: "(L/D) 21.0 · ρ 0.70 ⚠",
      tile: (
        <div className="flex flex-col gap-1 pt-0.5">
          {gueteMock.slice(0, 3).map((g) => <BulletGauge key={g.symbol} g={g} />)}
        </div>
      ),
      large: (
        <div>
          <div className="grid grid-cols-3 gap-x-5 gap-y-2.5 md:grid-cols-6">
            {gueteMock.map((g) => <BulletGauge key={g.symbol} g={g} />)}
          </div>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 border-t border-border pt-1.5">
            {gueteRawMock.map((r) => (
              <span key={r.symbol} className="group/m relative font-[family-name:var(--font-geist-mono)] text-[10px] text-muted-foreground" tabIndex={0}>
                {renderSymbol(r.symbol)} <span className="text-foreground">{r.value}</span>
                <Tip>{r.label} — {r.description}</Tip>
              </span>
            ))}
          </div>
        </div>
      ),
    },
    geometry: {
      title: "Geometry", icon: Ruler, headline: "AR 11.3 · SM 8.1% · V_H 0.58",
      tile: (
        <div className="grid h-full grid-cols-3 content-center gap-x-3 gap-y-2 pt-0.5 font-[family-name:var(--font-geist-mono)]">
          {geometryMock.map((m) => (
            <div key={m.symbol} className="group/m relative min-w-0" tabIndex={0}>
              <div className="truncate text-[10px] uppercase tracking-wide text-subtle-foreground">{renderSymbol(m.symbol)}</div>
              <div className="truncate text-[13px] font-semibold text-foreground">{m.value}{m.unit && <span className="ml-0.5 text-[9px] font-normal text-muted-foreground">{m.unit}</span>}</div>
              <Tip>{m.label} — {m.description}</Tip>
            </div>
          ))}
          <div className="group/m relative" tabIndex={0}>
            <div className="text-[10px] uppercase tracking-wide text-subtle-foreground">SM</div>
            <div className={`text-[13px] font-bold ${smInTarget ? "text-success" : "text-amber-400"}`}>{balanceMock.smPercent.toFixed(1)}%</div>
            <Tip>Static margin — longitudinal stability as % of MAC (CG ahead of neutral point). Target {balanceMock.targetSmMin}–{balanceMock.targetSmMax}%.</Tip>
          </div>
          <div className="group/m relative" tabIndex={0}>
            <div className="text-[10px] uppercase tracking-wide text-subtle-foreground">{renderSymbol("V_H")}</div>
            <div className={`text-[13px] font-bold ${QCOL[tailVhGauge.quality]}`}>{tailVhGauge.value.toFixed(2)}</div>
            <Tip>{tailVhGauge.label} — {tailVhGauge.description}</Tip>
          </div>
        </div>
      ),
      large: (
        <div className="flex h-full items-stretch gap-4 pt-1">
          <div className="flex h-full min-h-0 flex-[2] items-center justify-center">
            <PlanformDiagram bRef="1.50" mac="0.135" sRef="0.200" ar="11.3" annotate cgFrac={cgFrac} npFrac={npFrac} sm={smStr} smOk={smInTarget} />
          </div>
          <div className="flex flex-1 flex-col justify-center gap-1.5 font-[family-name:var(--font-geist-mono)] text-[11px]">
            <div className="text-[9px] uppercase tracking-wide text-subtle-foreground">Balance</div>
            <div className="group/m relative" tabIndex={0}>
              SM <span className={smInTarget ? "text-success" : "text-amber-400"}>{smStr}</span> · CG {balanceMock.cg.toFixed(3)} m · NP {balanceMock.np.toFixed(3)} m
              <Tip>Static margin = (NP − CG) / MAC. CG must sit ahead of the neutral point. Target {balanceMock.targetSmMin}–{balanceMock.targetSmMax}% MAC.</Tip>
            </div>
            <p className="text-[10px] text-subtle-foreground">Component CG {balanceMock.cgComponent?.toFixed(3)} m · target SM {balanceMock.targetSmMin}–{balanceMock.targetSmMax}% MAC</p>
          </div>
          <div className="flex flex-1 flex-col justify-center gap-1.5">
            <div className="group/m relative inline-block text-[9px] uppercase tracking-wide text-subtle-foreground" tabIndex={0}>
              Tail · <span className="text-muted-foreground">{tailMission}</span> · RC rule of thumb
              <Tip>{tailBandsNote}</Tip>
            </div>
            <BulletGauge g={tailVhGauge} />
            <div className="flex flex-wrap gap-x-3 gap-y-0.5 font-[family-name:var(--font-geist-mono)]">
              {tailItems.map((t) => (
                <span key={t.symbol} className="group/m relative text-[10px] text-muted-foreground" tabIndex={0}>
                  {renderSymbol(t.symbol)} <span className="text-foreground">{t.value}{t.unit ? ` ${t.unit}` : ""}</span>
                  <Tip>{t.label} — {t.description}</Tip>
                </span>
              ))}
            </div>
          </div>
        </div>
      ),
    },
    antrieb: {
      title: "Antrieb", icon: BatteryCharging, headline: "Endurance 42 min · P/W 4.1",
      tile: <div className="pt-1"><MiniKV items={antriebMock} /></div>,
      large: (
        <div>
          <div className="flex flex-wrap gap-2 pt-1">{antriebMock.map((m) => <MetricCard key={m.symbol} item={m} large />)}</div>
          <p className="mt-2 border-t border-border pt-1.5 text-[10px] text-muted-foreground">
            P_req @V_md {antriebDetailMock.pReqVmd} W · reserve <span className="text-amber-400">{antriebDetailMock.pMarginClass}</span> · battery ~{antriebDetailMock.batteryMassPredicted} g · <span className="text-amber-400">{antriebDetailMock.confidence}</span>
          </p>
        </div>
      ),
    },
  };

  // condensed summary chips shown on the handle when the band is collapsed
  const collapsedItems: { sym: string; val: string }[] = [
    { sym: "V_cruise", val: `${speedMock.markers.find((m) => m.symbol === "V_cruise")?.value.toFixed(0)}` },
    { sym: "AR", val: `${geometryMock.find((m) => m.symbol === "AR")?.value}` },
    { sym: "(L/D)_max", val: gueteMock[0].value.toFixed(0) },
    { sym: "SM", val: `${balanceMock.smPercent.toFixed(0)}%` },
    { sym: "Endurance", val: `${antriebMock[1].value} ${antriebMock[1].unit}` },
  ];

  return (
    <div className="w-full" data-testid="metrics-band">
      {/* persistent handle — sits ABOVE the band; toggles it open/closed */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label={open ? "Collapse metrics" : "Expand metrics"}
        className="flex h-8 w-full shrink-0 items-center gap-3 rounded-t-xl border border-border bg-sidebar px-4 text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-foreground"
      >
        {open ? <ChevronDown size={15} /> : <ChevronUp size={15} />}
        <span className="text-[12px] font-medium">Metrics</span>
        {!open && (
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

      {/* sliding band — collapses to 0 height via the grid-rows trick */}
      <div className={`grid transition-[grid-template-rows] duration-300 ease-out ${open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"}`}>
        <div className="min-h-0 overflow-hidden">
          <div className="h-[15vh] min-h-[118px] w-full pt-2" data-testid="metrics-band-body">
            <div className="flex h-full w-full gap-2">
              {IDS.map((id) => (
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
