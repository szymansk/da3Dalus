"use client";

import { useState } from "react";
import { Wind, SlidersHorizontal, Activity } from "lucide-react";

const TABS = ["Polar", "Three-View", "Streamlines", "Diagrams"] as const;
type Tab = (typeof TABS)[number];

const BAR_HEIGHTS = [
  14, 20, 30, 42, 56, 72, 88, 104, 120, 138, 156, 168, 176, 180, 182, 182,
];

export function AnalysisViewerPanel() {
  const [activeTab, setActiveTab] = useState<Tab>("Polar");

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
            &alpha;_stall &asymp; 12&deg; &middot; C_L,max &asymp; 1.1
          </span>
        </div>

        {/* Chart area */}
        <div className="flex flex-1 items-end gap-1.5 rounded-[--radius-s] border border-border bg-card p-4">
          {BAR_HEIGHTS.map((h, i) => (
            <div
              key={i}
              className="flex-1 rounded-sm bg-primary"
              style={{ height: `${h}px` }}
            />
          ))}
          {/* Stall line marker */}
          <div className="h-full w-0.5 bg-destructive" />
        </div>

        {/* X-axis labels */}
        <div className="flex justify-between pt-2">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
            -5&deg;
          </span>
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
            0&deg;
          </span>
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
            5&deg;
          </span>
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
            10&deg;
          </span>
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
            15&deg;
          </span>
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
