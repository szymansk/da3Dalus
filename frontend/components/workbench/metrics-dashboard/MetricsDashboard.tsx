"use client";

// Click-dummy (#881, v2) — compact metrics BAND: five columns inside a fixed
// ~20vh-tall strip. All columns are equal compact tiles by default; activating
// one makes it full width (others shrink to narrow vertical tabs). The band
// height never changes — content scrolls inside a column if needed.

import { useState } from "react";
import { Wind, Gauge, Ruler, BatteryCharging } from "lucide-react";
import { renderSymbol } from "@/components/workbench/renderSymbol";
import { MetricColumn, type ColumnMode } from "./MetricColumn";
import { EnvelopeAxis, BulletGauge, MetricCard, Tip } from "./primitives";
import { PlanformDiagram } from "./PlanformDiagram";
import {
  antriebDetailMock, antriebMock, balanceMock, geometryMock,
  gueteMock, gueteRawMock, speedMock, type MetricItem,
} from "./metricsMock";

type Id = "speed" | "geometry" | "guete" | "antrieb";
const IDS: Id[] = ["speed", "geometry", "guete", "antrieb"];

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
        <div className="flex flex-col gap-2 pt-1">
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
      title: "Geometry", icon: Ruler, headline: "AR 11.3 · S_ref 0.200 m² · SM 8.1%",
      tile: (
        <div className="flex h-full flex-col gap-1 pt-1">
          <div className="flex min-h-0 flex-1 items-center justify-center">
            <PlanformDiagram bRef="1.50" mac="0.135" sRef="0.200" ar="11.3" cgFrac={cgFrac} npFrac={npFrac} sm={smStr} smOk={smInTarget} />
          </div>
          <div className="flex items-end justify-between gap-2">
            <div className="min-w-0 flex-1"><MiniKV items={geometryMock} /></div>
            <div className="group/m relative shrink-0 text-right font-[family-name:var(--font-geist-mono)]" tabIndex={0}>
              <div className={`text-[16px] font-bold leading-none ${smInTarget ? "text-success" : "text-amber-400"}`}>{balanceMock.smPercent.toFixed(1)}%</div>
              <div className="text-[9px] uppercase tracking-wide text-subtle-foreground">SM</div>
              <Tip>Static margin — longitudinal stability as % of MAC (CG ahead of neutral point). Target {balanceMock.targetSmMin}–{balanceMock.targetSmMax}%.</Tip>
            </div>
          </div>
        </div>
      ),
      large: (
        <div className="flex h-full items-stretch gap-4 pt-1">
          <div className="flex h-full min-h-0 flex-[3] items-center justify-center">
            <PlanformDiagram bRef="1.50" mac="0.135" sRef="0.200" ar="11.3" annotate cgFrac={cgFrac} npFrac={npFrac} sm={smStr} smOk={smInTarget} />
          </div>
          <div className="flex flex-1 flex-col justify-center gap-1.5 font-[family-name:var(--font-geist-mono)] text-[11px]">
            <div className="group/m relative" tabIndex={0}>
              SM <span className={smInTarget ? "text-success" : "text-amber-400"}>{smStr}</span> · CG {balanceMock.cg.toFixed(3)} m · NP {balanceMock.np.toFixed(3)} m
              <Tip>Static margin = (NP − CG) / MAC. CG must sit ahead of the neutral point. Target {balanceMock.targetSmMin}–{balanceMock.targetSmMax}% MAC.</Tip>
            </div>
            <p className="text-[10px] text-subtle-foreground">Component CG {balanceMock.cgComponent?.toFixed(3)} m · target SM {balanceMock.targetSmMin}–{balanceMock.targetSmMax}% MAC</p>
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

  return (
    <div className="h-[20vh] min-h-[140px] w-full" data-testid="metrics-band">
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
  );
}
