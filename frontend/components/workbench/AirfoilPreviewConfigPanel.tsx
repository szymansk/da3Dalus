"use client";

import { AirfoilSelector } from "./AirfoilSelector";
import type { AirfoilAnalysisResult } from "@/hooks/useAirfoilAnalysis";

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
}: AirfoilPreviewConfigPanelProps) {
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
        {segmentLabel} &middot; Properties
      </span>

      {/* Form Card */}
      <div className="flex flex-1 flex-col gap-3 overflow-y-auto rounded-[--radius-m] border border-border bg-card p-4">
        {/* root_airfoil */}
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-primary">
          root_airfoil
        </span>
        <AirfoilSelector
          label=""
          value={rootAirfoil}
          onChange={onRootAirfoilChange}
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

        {/* Divider */}
        <div className="border-t border-border" />

        {/* Read-only segment properties */}
        <div className="opacity-50">
          <div className="flex gap-3">
            <ReadOnlyField
              label="length"
              value={segmentProps.length}
              suffix="mm"
            />
            <ReadOnlyField
              label="sweep"
              value={segmentProps.sweep}
              suffix="mm"
            />
          </div>
          <div className="mt-3 flex gap-3">
            <ReadOnlyField
              label="dihedral"
              value={segmentProps.dihedral}
              suffix="\u00B0"
            />
            <ReadOnlyField
              label="incidence"
              value={segmentProps.incidence}
              suffix="\u00B0"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
