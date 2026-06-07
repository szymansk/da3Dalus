"use client";

// Click-dummy (#881) — assembles all five zones with hardcoded data and owns
// the section state machine (incl. the "only one large at a time" invariant).

import { useState } from "react";
import { Wind, Scale, Gauge, Ruler, BatteryCharging } from "lucide-react";
import { MetricSection } from "./MetricSection";
import { EnvelopeAxis, BulletGauge, MacCgDiagram, MetricCard } from "./primitives";
import {
  antriebDetailMock,
  antriebMock,
  balanceMock,
  geometryMock,
  gueteMock,
  gueteRawMock,
  speedMock,
  type SectionState,
} from "./metricsMock";

type Id = "speed" | "balance" | "guete" | "geometry" | "antrieb";
const IDS: Id[] = ["speed", "balance", "guete", "geometry", "antrieb"];

// Click-dummy keeps section state in-memory. localStorage persistence across
// reloads is a real-implementation concern, specified in the #881 acceptance
// criteria (use useSyncExternalStore there to stay SSR-safe).

export function MetricsDashboard() {
  const [states, setStates] = useState<Record<Id, SectionState>>(() =>
    Object.fromEntries(IDS.map((id) => [id, "compact"])) as Record<Id, SectionState>,
  );

  function setSection(id: Id, next: SectionState) {
    setStates((prev) => {
      const out: Record<Id, SectionState> = { ...prev, [id]: next };
      // invariant: at most one section "large" — demote the previous large to compact
      if (next === "large") {
        for (const other of IDS) {
          if (other !== id && out[other] === "large") out[other] = "compact";
        }
      }
      return out;
    });
  }

  const smInTarget = balanceMock.smPercent >= balanceMock.targetSmMin && balanceMock.smPercent <= balanceMock.targetSmMax;

  return (
    <div className="flex flex-col gap-2">
      <MetricSection
        title="Speed" icon={Wind} state={states.speed} onSetState={(s) => setSection("speed", s)}
        headline="V_stall 8.2 · V_cruise 14.0 · V_max 22.0 m/s"
        compact={<EnvelopeAxis markers={speedMock.markers} />}
        large={<EnvelopeAxis markers={speedMock.markers} large />}
      />

      <MetricSection
        title="Balance" icon={Scale} state={states.balance} onSetState={(s) => setSection("balance", s)}
        headline={`SM ${balanceMock.smPercent.toFixed(1)}% · CG ${balanceMock.cg.toFixed(3)} m`}
        compact={<MacCgDiagram {...balanceMock} inTarget={smInTarget} />}
        large={
          <div>
            <MacCgDiagram {...balanceMock} inTarget={smInTarget} large />
            <p className="mt-1 text-[10px] text-subtle-foreground">
              Component CG {balanceMock.cgComponent?.toFixed(3)} m · target SM {balanceMock.targetSmMin}–{balanceMock.targetSmMax}% MAC
            </p>
          </div>
        }
      />

      <MetricSection
        title="Güte" icon={Gauge} state={states.guete} onSetState={(s) => setSection("guete", s)}
        headline="(L/D) 21.0 · ρ 0.70 ⚠ · e 0.79"
        compact={
          <div className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
            {gueteMock.slice(0, 3).map((g) => <BulletGauge key={g.symbol} g={g} />)}
          </div>
        }
        large={
          <div>
            <div className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
              {gueteMock.map((g) => <BulletGauge key={g.symbol} g={g} large />)}
            </div>
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-border pt-2">
              {gueteRawMock.map((r) => (
                <span key={r.symbol} className="font-[family-name:var(--font-geist-mono)] text-[11px] text-muted-foreground">
                  {r.symbol} <span className="text-foreground">{r.value}</span>
                </span>
              ))}
            </div>
          </div>
        }
      />

      <MetricSection
        title="Geometry" icon={Ruler} state={states.geometry} onSetState={(s) => setSection("geometry", s)}
        headline="AR 11.3 · S_ref 0.200 m²"
        compact={<div className="flex flex-wrap gap-2">{geometryMock.map((m) => <MetricCard key={m.symbol} item={m} />)}</div>}
        large={<div className="flex flex-wrap gap-2">{geometryMock.map((m) => <MetricCard key={m.symbol} item={m} large />)}</div>}
      />

      <MetricSection
        title="Antrieb" icon={BatteryCharging} state={states.antrieb} onSetState={(s) => setSection("antrieb", s)}
        headline="Endurance 42 min · P/W 4.1 W/N"
        compact={<div className="flex flex-wrap gap-2">{antriebMock.map((m) => <MetricCard key={m.symbol} item={m} />)}</div>}
        large={
          <div>
            <div className="flex flex-wrap gap-2">{antriebMock.map((m) => <MetricCard key={m.symbol} item={m} large />)}</div>
            <div className="mt-3 border-t border-border pt-2 text-[11px] text-muted-foreground">
              <p>P_req @V_md {antriebDetailMock.pReqVmd} W · @V_min_sink {antriebDetailMock.pReqVminSink} W · motor reserve: <span className="text-amber-400">{antriebDetailMock.pMarginClass}</span></p>
              <p className="mt-1">Battery mass (predicted) {antriebDetailMock.batteryMassPredicted} g · confidence: <span className="text-amber-400">{antriebDetailMock.confidence}</span></p>
              {antriebDetailMock.warnings.map((w) => (
                <p key={w} className="mt-1 text-amber-400">⚠ {w}</p>
              ))}
            </div>
          </div>
        }
      />
    </div>
  );
}
