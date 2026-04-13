"use client";

import { useState } from "react";
import { Box, Loader } from "lucide-react";
import { CadViewer } from "./CadViewer";

const STAGES = ["Bare Aero", "+TEDs", "+Spars", "Final Print"] as const;
type Stage = (typeof STAGES)[number];

interface ViewerPanelProps {
  visibleParts: Record<string, unknown>[];
  isAnyLoading: boolean;
  loadingWing: string | null;
}

export function ViewerPanel({ visibleParts, isAnyLoading, loadingWing }: ViewerPanelProps) {
  const [activeStage, setActiveStage] = useState<Stage>("Bare Aero");

  return (
    <div className="flex flex-1 flex-col overflow-hidden rounded-[--radius-m] border border-border">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-border bg-card px-4 py-3">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
          CAD Viewer
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

      {/* Viewer Body */}
      <div className="flex flex-1 flex-col bg-card-muted">
        {visibleParts.length > 0 ? (
          <CadViewer parts={visibleParts} />
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center gap-4 p-6">
            <Box size={72} className="text-subtle-foreground" />
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-muted-foreground">
              Toggle the eye icon next to a wing to preview it
            </span>
          </div>
        )}
      </div>

      {/* Loading Toast */}
      {isAnyLoading && (
        <div className="flex items-center gap-3 border-t border-border bg-card px-4 py-3">
          <Loader size={14} className="animate-spin text-primary" />
          <span className="font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground">
            Tessellating {loadingWing}…
          </span>
        </div>
      )}
    </div>
  );
}
