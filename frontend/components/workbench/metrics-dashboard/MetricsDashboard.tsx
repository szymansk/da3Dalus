"use client";

// Click-dummy (#881, v2) — compact metrics BAND: five columns inside a fixed
// ~20vh-tall strip. All columns are equal compact tiles by default; activating
// one makes it full width (others shrink to narrow vertical tabs). The band
// height never changes — content scrolls inside a column if needed.

import { useState } from "react";
import { Wind, Scale, Gauge, Ruler, BatteryCharging } from "lucide-react";
import { MetricColumn, type ColumnMode } from "./MetricColumn";
import { EnvelopeAxis, BulletGauge, MetricCard, MacCgDiagram } from "./primitives";
import {
  antriebDetailMock, antriebMock, balanceMock, geometryMock,
  gueteMock, gueteRawMock, speedMock, type MetricItem,
} from "./metricsMock";

type Id = "speed" | "balance" | "guete" | "geometry" | "antrieb";
const IDS: Id[] = ["speed", "balance", "guete", "geometry", "antrieb"];

// tiny key/value used in compact tiles
function MiniKV({ items }: { readonly items: readonly MetricItem[] }) {
  return (
    <div className="grid grid-cols-2 gap-x-2 gap-y-1.5">
      {items.map((m) => (
        <div key={m.symbol} className="group/m relative min-w-0" tabIndex={0}>
          <div className="truncate font-[family-name:var(--font-geist-mono)] text-[9px] uppercase tracking-wide text-subtle-foreground">{m.symbol}</div>
          <div className="truncate font-[family-name:var(--font-geist-mono)] text-[12px] font-semibold text-foreground">
            {m.value}{m.unit && <span className="ml-0.5 text-[9px] font-normal text-muted-foreground">{m.unit}</span>}
          </div>
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

  const cols: Record<Id, { title: string; icon: typeof Wind; headline: string; tile: React.ReactNode; large: React.ReactNode }> = {
    speed: {
      title: "Speed", icon: Wind, headline: "V_stall 8.2 · V_cruise 14.0 · V_max 22.0",
      tile: (
        <div>
          <EnvelopeAxis markers={speedMock.markers} />
          <div className="mt-1 flex justify-between font-[family-name:var(--font-geist-mono)] text-[10px] text-muted-foreground">
            <span>stall <span className="text-foreground">8.2</span></span>
            <span>cruise <span className="text-foreground">14.0</span></span>
            <span>max <span className="text-foreground">22.0</span></span>
          </div>
        </div>
      ),
      large: <EnvelopeAxis markers={speedMock.markers} large />,
    },
    balance: {
      title: "Balance", icon: Scale, headline: `SM ${balanceMock.smPercent.toFixed(1)}%`,
      tile: (
        <div className="pt-1">
          <div className="font-[family-name:var(--font-geist-mono)] text-[18px] font-bold leading-none">
            <span className={smInTarget ? "text-success" : "text-amber-400"}>{balanceMock.smPercent.toFixed(1)}%</span>
            <span className="ml-1 text-[10px] font-normal text-subtle-foreground">SM</span>
          </div>
          <MacCgDiagram {...balanceMock} inTarget={smInTarget} />
        </div>
      ),
      large: (
        <div>
          <MacCgDiagram {...balanceMock} inTarget={smInTarget} large />
          <p className="mt-1 text-[10px] text-subtle-foreground">Component CG {balanceMock.cgComponent?.toFixed(3)} m · target SM {balanceMock.targetSmMin}–{balanceMock.targetSmMax}% MAC</p>
        </div>
      ),
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
              <span key={r.symbol} className="font-[family-name:var(--font-geist-mono)] text-[10px] text-muted-foreground">{r.symbol} <span className="text-foreground">{r.value}</span></span>
            ))}
          </div>
        </div>
      ),
    },
    geometry: {
      title: "Geometry", icon: Ruler, headline: "AR 11.3 · S_ref 0.200 m²",
      tile: <div className="pt-1"><MiniKV items={geometryMock} /></div>,
      large: <div className="flex flex-wrap gap-2 pt-1">{geometryMock.map((m) => <MetricCard key={m.symbol} item={m} large />)}</div>,
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
