"use client";

import { useState } from "react";
import {
  Box,
  ZoomIn,
  Maximize2,
  Square,
  LayoutGrid,
  Folder,
  Eye,
  Trash2,
  Loader,
} from "lucide-react";

const STAGES = ["Bare Aero", "+TEDs", "+Spars", "Final Print"] as const;
type Stage = (typeof STAGES)[number];

const TOOLBAR_ICONS = [
  ZoomIn,
  Maximize2,
  Square,
  Box,
  LayoutGrid,
  Folder,
  Eye,
  Trash2,
] as const;

export function ViewerPanel() {
  const [activeStage, setActiveStage] = useState<Stage>("Bare Aero");

  return (
    <div className="flex flex-1 flex-col overflow-hidden rounded-[--radius-m] border border-border">
      {/* ── Viewer Header ── */}
      <div className="flex items-center gap-2 border-b border-border bg-card px-4 py-3">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
          OCP CAD Viewer
        </span>
        <div className="flex-1" />
        <div className="flex items-center gap-1">
          {STAGES.map((stage) => (
            <button
              key={stage}
              onClick={() => setActiveStage(stage)}
              className={`rounded-[--radius-pill] px-3 py-1.5 font-[family-name:var(--font-geist-sans)] text-[12px] transition-colors ${
                stage === activeStage
                  ? "bg-primary text-primary-foreground"
                  : "bg-card-muted text-muted-foreground hover:bg-sidebar-accent"
              }`}
            >
              {stage}
            </button>
          ))}
        </div>
      </div>

      {/* ── Viewer Body ── */}
      <div className="flex flex-1 flex-col items-center justify-center gap-4 bg-card-muted p-6">
        <Box size={72} className="text-subtle-foreground" />
        <h2 className="font-[family-name:var(--font-jetbrains-mono)] text-[16px] text-muted-foreground">
          3D CAD Viewer — eHawk main_wing
        </h2>
        <p className="font-[family-name:var(--font-geist-sans)] text-[12px] italic text-subtle-foreground">
          Embedded OCP CAD Viewer &middot; display() command active
        </p>

        {/* Toolbar */}
        <div className="flex items-center gap-2 pt-6">
          {TOOLBAR_ICONS.map((Icon, i) => (
            <button
              key={i}
              className="flex h-7 w-7 items-center justify-center rounded-[--radius-s] border border-border bg-card hover:bg-sidebar-accent"
            >
              <Icon size={14} className="text-muted-foreground" />
            </button>
          ))}
        </div>
      </div>

      {/* ── Task Toast ── */}
      <div className="flex items-center gap-3 border-t border-border bg-card px-4 py-3">
        <Loader size={14} className="animate-spin text-primary" />
        <span className="font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground">
          Generating wing_loft/stl&hellip;
        </span>
        <div className="flex-1" />
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-primary">
          32 %
        </span>
        <div className="h-1.5 w-[120px] rounded-sm bg-input">
          <div className="h-1.5 w-[38px] rounded-sm bg-primary" />
        </div>
      </div>
    </div>
  );
}
