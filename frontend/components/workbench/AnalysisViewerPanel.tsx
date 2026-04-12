"use client";

import { useState, useMemo } from "react";
import { Wind, SlidersHorizontal, Activity } from "lucide-react";
import type { AnalysisResult } from "@/hooks/useAnalysis";

const TABS = ["Polar", "Three-View", "Streamlines", "Diagrams"] as const;
type Tab = (typeof TABS)[number];

const BAR_HEIGHTS = [
  14, 20, 30, 42, 56, 72, 88, 104, 120, 138, 156, 168, 176, 180, 182, 182,
];

const MAX_BAR_HEIGHT = 180;

interface Props {
  result: AnalysisResult | null;
}

export function AnalysisViewerPanel({ result }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>("Polar");

  const chartData = useMemo(() => {
    if (!result || !result.CL || result.CL.length === 0) return null;

    const { CL, alpha } = result;
    const minCL = Math.min(...CL);
    const maxCL = Math.max(...CL);
    const range = maxCL - minCL;

    const barHeights = CL.map((cl) =>
      range > 0
        ? ((cl - minCL) / range) * MAX_BAR_HEIGHT
        : MAX_BAR_HEIGHT / 2
    );

    // Find stall index: last index where CL starts to drop
    let stallIndex = -1;
    for (let i = 1; i < CL.length; i++) {
      if (CL[i] < CL[i - 1]) {
        stallIndex = i;
        break;
      }
    }

    // CL_max is at the index just before stall (or the peak)
    const clMaxIndex = stallIndex > 0 ? stallIndex - 1 : CL.indexOf(maxCL);
    const clMax = CL[clMaxIndex];
    const alphaStall = alpha[clMaxIndex];

    // X-axis labels: first, quarter, middle, three-quarter, last
    const first = alpha[0];
    const last = alpha[alpha.length - 1];
    const mid = alpha[Math.floor(alpha.length / 2)];
    const q1 = alpha[Math.floor(alpha.length / 4)];
    const q3 = alpha[Math.floor((3 * alpha.length) / 4)];

    return {
      barHeights,
      stallIndex,
      clMax,
      alphaStall,
      xLabels: [first, q1, mid, q3, last],
    };
  }, [result]);

  const bars = chartData ? chartData.barHeights : BAR_HEIGHTS;
  const stallIdx = chartData ? chartData.stallIndex : -1;

  const titleAnnotation = chartData
    ? `\u03B1_stall \u2248 ${chartData.alphaStall.toFixed(0)}\u00B0 \u00B7 C_L,max \u2248 ${chartData.clMax.toFixed(2)}`
    : "\u03B1_stall \u2248 12\u00B0 \u00B7 C_L,max \u2248 1.1";

  const xLabels = chartData
    ? chartData.xLabels.map((v) => `${v.toFixed(0)}\u00B0`)
    : ["-5\u00B0", "0\u00B0", "5\u00B0", "10\u00B0", "15\u00B0"];

  return (
    <div className="flex flex-1 flex-col overflow-hidden rounded-[--radius-m] border border-border">
      {/* ── Header ── */}
      <div className="flex items-center gap-2 border-b border-border bg-card px-4 py-3">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
          Aerodynamic Analysis
        </span>
        <div className="flex-1" />
        <div className="flex items-center gap-1">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`rounded-[--radius-pill] px-3 py-1.5 font-[family-name:var(--font-geist-sans)] text-[12px] transition-colors ${
                tab === activeTab
                  ? "bg-primary text-primary-foreground"
                  : "bg-card-muted text-muted-foreground hover:bg-sidebar-accent"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* ── Chart Body ── */}
      <div className="flex flex-1 flex-col gap-3 border border-border bg-card-muted p-8">
        {/* Title row */}
        <div className="flex items-center">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-foreground">
            C_L vs &alpha;
          </span>
          <div className="flex-1" />
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
            {titleAnnotation}
          </span>
        </div>

        {/* Chart area */}
        <div className="flex flex-1 items-end gap-1.5 rounded-[--radius-s] border border-border bg-card p-4">
          {bars.map((h, i) => (
            <div
              key={i}
              className={`flex-1 rounded-sm ${
                stallIdx >= 0 && i >= stallIdx ? "bg-destructive" : "bg-primary"
              }`}
              style={{ height: `${h}px` }}
            />
          ))}
          {/* Stall line marker (only when there is no dynamic stall detection) */}
          {stallIdx < 0 && <div className="h-full w-0.5 bg-destructive" />}
        </div>

        {/* X-axis labels */}
        <div className="flex justify-between pt-2">
          {xLabels.map((label, i) => (
            <span
              key={i}
              className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground"
            >
              {label}
            </span>
          ))}
        </div>

        {/* X-axis title */}
        <div className="text-center">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground">
            &alpha; [&deg;]
          </span>
        </div>
      </div>

      {/* ── Info Chip Row ── */}
      <div className="flex items-center gap-2 border-t border-border bg-card px-4 py-3">
        <div className="flex items-center gap-1.5 rounded-[--radius-pill] bg-card-muted px-3 py-1.5">
          <Wind size={12} className="text-muted-foreground" />
          <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-foreground">
            Flight profile: cruise
          </span>
        </div>
        <div className="flex items-center gap-1.5 rounded-[--radius-pill] bg-card-muted px-3 py-1.5">
          <SlidersHorizontal size={12} className="text-muted-foreground" />
          <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-foreground">
            Trim: elevator &minus;2.1&deg;
          </span>
        </div>
        <div className="flex items-center gap-1.5 rounded-[--radius-pill] bg-card-muted px-3 py-1.5">
          <Activity size={12} className="text-muted-foreground" />
          <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-foreground">
            Re &asymp; 4.2e5
          </span>
        </div>
        <div className="flex-1" />
        <span className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
          Last run: 11:42 &middot; 820 ms
        </span>
      </div>
    </div>
  );
}
