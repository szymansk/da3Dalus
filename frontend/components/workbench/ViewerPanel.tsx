"use client";

import { useState, lazy, Suspense } from "react";
import { Box, Loader, RefreshCw } from "lucide-react";
import { useAeroplaneContext } from "./AeroplaneContext";
import { useTessellation } from "@/hooks/useTessellation";

// lazy() instead of next/dynamic — avoids Turbopack prefetching
// the massive three-cad-viewer bundle on initial page load.
// The chunk is only fetched when CadViewer actually renders.
const CadViewer = lazy(() => import("./CadViewer").then((m) => ({ default: m.CadViewer })));

const STAGES = ["Bare Aero", "+TEDs", "+Spars", "Final Print"] as const;
type Stage = (typeof STAGES)[number];

export function ViewerPanel() {
  const [activeStage, setActiveStage] = useState<Stage>("Bare Aero");
  const { aeroplaneId, selectedWing } = useAeroplaneContext();
  const {
    data,
    isTessellating,
    progress,
    error,
    isStale,
    hasCachedData,
    triggerTessellation,
  } = useTessellation(aeroplaneId);

  return (
    <div className="flex flex-1 flex-col overflow-hidden rounded-[--radius-m] border border-border">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-border bg-card px-4 py-3">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
          CAD Viewer
        </span>
        {isStale && !isTessellating && (
          <span className="rounded-[--radius-pill] bg-sidebar-accent px-2 py-0.5 text-[10px] text-muted-foreground">
            Updating…
          </span>
        )}
        {hasCachedData && !isTessellating && (
          <button
            onClick={() => selectedWing && triggerTessellation(selectedWing)}
            className="flex items-center gap-1 rounded-[--radius-s] border border-border bg-card-muted px-2 py-1 text-[11px] text-muted-foreground hover:text-foreground"
            title="Re-tessellate"
          >
            <RefreshCw size={11} />
            Refresh
          </button>
        )}
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
        {data ? (
          <Suspense fallback={
            <div className="flex flex-1 items-center justify-center">
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
                Loading 3D viewer…
              </span>
            </div>
          }>
            <CadViewer data={data as unknown as Record<string, unknown>} />
          </Suspense>
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center gap-4 p-6">
            <Box size={72} className="text-subtle-foreground" />
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-muted-foreground">
              {selectedWing
                ? `Click "Preview" to render ${selectedWing}`
                : "Select a wing to preview"}
            </span>
            {selectedWing && (
              <button
                onClick={() => triggerTessellation(selectedWing)}
                disabled={isTessellating}
                className="rounded-[--radius-pill] bg-primary px-4 py-2.5 text-[13px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
              >
                {isTessellating ? "Tessellating…" : "Preview 3D"}
              </button>
            )}
            {error && (
              <span className="max-w-md text-center text-[12px] text-destructive">{error}</span>
            )}
          </div>
        )}
      </div>

      {/* Task Toast */}
      {isTessellating && (
        <div className="flex items-center gap-3 border-t border-border bg-card px-4 py-3">
          <Loader size={14} className="animate-spin text-primary" />
          <span className="font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground">
            {progress}
          </span>
        </div>
      )}
    </div>
  );
}
