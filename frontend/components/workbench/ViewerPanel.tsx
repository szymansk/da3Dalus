"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Box, Loader, RefreshCw } from "lucide-react";
import { useAeroplaneContext } from "./AeroplaneContext";
import { useTessellation } from "@/hooks/useTessellation";

const STAGES = ["Bare Aero", "+TEDs", "+Spars", "Final Print"] as const;
type Stage = (typeof STAGES)[number];

/**
 * Resolve ocp_tessellate instance refs ({ref: N}) to inline geometry.
 * three-cad-viewer expects inline shape data, not references.
 */
function resolveRefs(
  node: Record<string, unknown>,
  instances: Record<string, unknown>[],
) {
  if (node.shape && typeof node.shape === "object") {
    const s = node.shape as Record<string, unknown>;
    if ("ref" in s && typeof s.ref === "number") {
      node.shape = instances[s.ref as number];
    }
  }
  if (Array.isArray(node.parts)) {
    for (const part of node.parts) {
      if (part && typeof part === "object") {
        resolveRefs(part as Record<string, unknown>, instances);
      }
    }
  }
}

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

  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<unknown>(null);
  const [viewerError, setViewerError] = useState<string | null>(null);
  const [viewerLoading, setViewerLoading] = useState(false);

  // Render three-cad-viewer when data changes.
  // The import("three-cad-viewer") only fires when data is non-null,
  // so Turbopack never prefetches the chunk on initial page load.
  useEffect(() => {
    if (!containerRef.current || !data) return;
    let disposed = false;

    async function init() {
      try {
        setViewerLoading(true);
        setViewerError(null);

        /* eslint-disable @typescript-eslint/no-explicit-any */
        const { Display, Viewer } = await import("three-cad-viewer");
        if (disposed || !containerRef.current) return;

        const container = containerRef.current;

        // Cleanup previous
        if (viewerRef.current) {
          try { (viewerRef.current as any).dispose?.(); } catch { /* ok */ }
        }
        container.innerHTML = "";

        const w = container.clientWidth || 800;
        const h = container.clientHeight || 500;

        const display = new Display(container, {
          cadWidth: w,
          height: h,
          treeWidth: 0,
          theme: "dark",
          glass: false,
          tools: false,
        } as any);

        const viewerOptions = { target: [0, 0, 0], up: "Z" };
        const viewer = new Viewer(display, viewerOptions as any, () => {});
        viewerRef.current = viewer;

        const tessData = data as {
          data?: { shapes?: Record<string, unknown>; instances?: Record<string, unknown>[] };
        };
        const shapes = tessData?.data?.shapes;
        const instances = tessData?.data?.instances;
        if (!shapes) throw new Error("No shape data in tessellation result");

        if (instances && Array.isArray(instances)) {
          resolveRefs(shapes, instances);
        }

        viewer.render(
          shapes as any,
          {
            ambientIntensity: 1.0,
            directIntensity: 1.1,
            metalness: 0.3,
            roughness: 0.65,
            edgeColor: 0x707070,
            defaultOpacity: 1.0,
          } as any,
          viewerOptions as any,
        );
        /* eslint-enable @typescript-eslint/no-explicit-any */

        setViewerLoading(false);
      } catch (err) {
        console.error("[ViewerPanel] Viewer error:", err);
        if (!disposed) {
          setViewerError(err instanceof Error ? err.message : String(err));
          setViewerLoading(false);
        }
      }
    }

    init();

    return () => {
      disposed = true;
      if (viewerRef.current) {
        try { (viewerRef.current as { dispose?: () => void }).dispose?.(); } catch { /* ok */ }
        viewerRef.current = null;
      }
      if (containerRef.current) {
        containerRef.current.innerHTML = "";
      }
    };
  }, [data]);

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
          <div className="relative h-full w-full">
            {viewerLoading && (
              <div className="absolute inset-0 z-10 flex items-center justify-center bg-card-muted/80">
                <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
                  Loading 3D viewer…
                </span>
              </div>
            )}
            {viewerError && (
              <div className="flex h-full items-center justify-center p-6">
                <div className="flex flex-col items-center gap-2">
                  <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-destructive">
                    Viewer Error
                  </span>
                  <span className="max-w-md text-center text-[12px] text-muted-foreground">{viewerError}</span>
                </div>
              </div>
            )}
            <div ref={containerRef} className="h-full w-full" />
          </div>
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
