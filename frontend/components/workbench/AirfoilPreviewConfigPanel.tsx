"use client";

import { useState } from "react";
import { Info } from "lucide-react";
import { AirfoilSelector } from "./AirfoilSelector";

interface AirfoilPreviewConfigPanelProps {
  rootAirfoil: string;
  tipAirfoil: string;
  onRootAirfoilChange: (name: string) => void;
  onTipAirfoilChange: (name: string) => void;
  onRunAnalysis: () => void;
  onClearResults: () => void;
  isRunning: boolean;
  segmentLabel: string;
  segmentProps: {
    length?: number;
    sweep?: number;
    dihedral?: number;
    incidence?: number;
  };
  velocity: number;
  onVelocityChange: (v: number) => void;
  rootRe: number;
  tipRe: number;
  onRootReChange: (re: number) => void;
  onTipReChange: (re: number) => void;
  rootChordMm: number;
  tipChordMm: number;
}

function ReadOnlyField({
  label,
  value,
  suffix,
}: {
  label: string;
  value: number | string | undefined;
  suffix?: string;
}) {
  const display = value != null ? `${value}` : "\u2014";
  return (
    <div className="flex flex-1 flex-col gap-1">
      <label className="text-[11px] text-muted-foreground">{label}</label>
      <div className="flex items-center gap-2 rounded-[--radius-s] border border-border bg-input px-3 py-2">
        <span className="text-[13px] text-foreground">{display}</span>
        {suffix && (
          <span className="flex-shrink-0 text-[11px] text-muted-foreground">
            {suffix}
          </span>
        )}
      </div>
    </div>
  );
}

function ReynoldsField({
  label,
  re,
  onReChange,
  chordMm,
  color,
}: {
  label: string;
  re: number;
  onReChange: (re: number) => void;
  chordMm: number;
  color?: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <span
        className="w-8 font-[family-name:var(--font-jetbrains-mono)] text-[11px]"
        style={color ? { color } : undefined}
      >
        {label}
      </span>
      <input
        type="number"
        value={re}
        onChange={(e) => {
          const v = parseInt(e.target.value, 10);
          if (!isNaN(v) && v > 0) onReChange(v);
        }}
        className="w-24 rounded-[--radius-s] border border-border bg-input px-2 py-1.5 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
      />
      <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
        c={chordMm}mm
      </span>
    </div>
  );
}

const RE_INFO_TEXT =
  "Re = V \u00D7 c / \u03BD\n\n" +
  "V = Fluggeschwindigkeit [m/s]\n" +
  "c = Profiltiefe (Chord) [m]\n" +
  "\u03BD = kinematische Viskosit\u00E4t der Luft\n" +
  "    (1.46\u00D710\u207B\u2075 m\u00B2/s bei 15\u00B0C)\n\n" +
  "Die Reynolds-Zahl bestimmt, ob die Grenzschicht\n" +
  "laminar oder turbulent ist. Modellflugzeuge\n" +
  "operieren typisch bei Re 50k\u2013500k (Low-Re-Regime).\n" +
  "\u00C4nderung der Geschwindigkeit berechnet Re f\u00FCr\n" +
  "Root und Tip automatisch neu aus dem jeweiligen Chord.";

export function AirfoilPreviewConfigPanel({
  rootAirfoil,
  tipAirfoil,
  onRootAirfoilChange,
  onTipAirfoilChange,
  onRunAnalysis,
  onClearResults,
  isRunning,
  segmentLabel,
  segmentProps,
  velocity,
  onVelocityChange,
  rootRe,
  tipRe,
  onRootReChange,
  onTipReChange,
  rootChordMm,
  tipChordMm,
}: AirfoilPreviewConfigPanelProps) {
  const [showReInfo, setShowReInfo] = useState(false);
  const hasTip = tipAirfoil !== rootAirfoil;

  return (
    <div className="flex h-full flex-col gap-4 overflow-hidden p-4">
      {/* Action Row */}
      <div className="flex gap-2">
        <button
          onClick={onRunAnalysis}
          disabled={isRunning}
          className="rounded-[--radius-pill] bg-primary px-4 py-2 text-[13px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
        >
          {isRunning ? "Running\u2026" : "Run Analysis"}
        </button>
        <button
          onClick={onClearResults}
          disabled={isRunning}
          className="rounded-[--radius-pill] border border-border-strong bg-background px-3.5 py-2 text-[13px] text-foreground hover:bg-sidebar-accent disabled:opacity-50"
        >
          Clear Results
        </button>
      </div>

      {/* Section header */}
      <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
        {segmentLabel} {"\u00B7"} Properties
      </span>

      {/* Form Card */}
      <div className="flex flex-1 flex-col gap-3 overflow-y-auto rounded-[--radius-m] border border-border bg-card p-4">
        {/* Velocity + Re info header */}
        <div className="flex items-center gap-2">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
            V
          </span>
          <input
            type="number"
            step="0.5"
            value={velocity}
            onChange={(e) => {
              const v = parseFloat(e.target.value);
              if (!isNaN(v) && v > 0) onVelocityChange(v);
            }}
            className="w-16 rounded-[--radius-s] border border-border bg-input px-2 py-1.5 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
          />
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
            m/s
          </span>
          <span className="flex-1" />
          <button
            onClick={() => setShowReInfo((s) => !s)}
            className="flex size-5 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
            title="Reynolds-Zahl Berechnung"
          >
            <Info size={12} />
          </button>
        </div>

        {/* Re info tooltip */}
        {showReInfo && (
          <div className="rounded-[--radius-s] border border-border bg-card-muted p-3">
            <pre className="whitespace-pre-wrap font-[family-name:var(--font-jetbrains-mono)] text-[10px] leading-relaxed text-muted-foreground">
              {RE_INFO_TEXT}
            </pre>
          </div>
        )}

        {/* Divider */}
        <div className="border-t border-border" />

        {/* root_airfoil */}
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-primary">
          root_airfoil
        </span>
        <AirfoilSelector
          label=""
          value={rootAirfoil}
          onChange={onRootAirfoilChange}
        />
        <ReynoldsField
          label="Re"
          re={rootRe}
          onReChange={onRootReChange}
          chordMm={rootChordMm}
          color="#FF8400"
        />

        {/* Divider */}
        <div className="border-t border-border" />

        {/* tip_airfoil */}
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
          tip_airfoil
        </span>
        <AirfoilSelector
          label=""
          value={tipAirfoil}
          onChange={onTipAirfoilChange}
        />
        {hasTip && (
          <ReynoldsField
            label="Re"
            re={tipRe}
            onReChange={onTipReChange}
            chordMm={tipChordMm}
            color="#22D3EE"
          />
        )}

        {/* Divider */}
        <div className="border-t border-border" />

        {/* Read-only segment properties */}
        <div className="opacity-50">
          <div className="flex gap-3">
            <ReadOnlyField label="length" value={segmentProps.length} suffix="mm" />
            <ReadOnlyField label="sweep" value={segmentProps.sweep} suffix="mm" />
          </div>
          <div className="mt-3 flex gap-3">
            <ReadOnlyField label="dihedral" value={segmentProps.dihedral} suffix={"\u00B0"} />
            <ReadOnlyField label="incidence" value={segmentProps.incidence} suffix={"\u00B0"} />
          </div>
        </div>
      </div>
    </div>
  );
}
