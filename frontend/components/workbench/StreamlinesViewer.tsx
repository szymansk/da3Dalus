"use client";

import { useState, useEffect, useRef } from "react";
import { Loader2 } from "lucide-react";
import { useStreamlines, type StreamlinesParams } from "@/hooks/useStreamlines";

// DO NOT import react-plotly.js or plotly.js at top level — it is 1.5 MB.
// We load it dynamically inside useEffect when figure data arrives.

export function StreamlinesViewer({ aeroplaneId }: Readonly<{ aeroplaneId: string | null }>) {
  const { figure, isComputing, error, computeStreamlines } = useStreamlines(aeroplaneId);
  const [params, setParams] = useState<StreamlinesParams>({
    velocity: 20,
    alpha: 5,
    beta: 0,
    altitude: 0,
  });
  const plotContainerRef = useRef<HTMLDivElement>(null);

  // Render Plotly when figure data arrives
  useEffect(() => {
    const node = plotContainerRef.current;
    if (!figure || !node) return;
    let disposed = false;

    (async () => {
      const Plotly = await import("plotly.js-gl3d-dist-min");
      if (disposed || !node) return;

      const figData = figure as { data?: unknown[]; layout?: Record<string, unknown> };
      const sceneFromLayout = (figData.layout?.scene as Record<string, unknown>) ?? {};

      // Dark theme overrides
      const layout = {
        ...figData.layout,
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "#1a1a2e",
        font: { color: "#e0e0e0" },
        scene: {
          ...sceneFromLayout,
          bgcolor: "#1a1a2e",
        },
      };

      Plotly.default.react(node, figData.data || [], layout, {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ["toImage", "sendDataToCloud"],
      });
    })();

    return () => {
      disposed = true;
      if (node) {
        import("plotly.js-gl3d-dist-min").then((P) => P.default.purge(node)).catch(() => { /* cleanup — safe to ignore */ });
      }
    };
  }, [figure]);

  return (
    <div className="flex flex-1 flex-col bg-card-muted">
      {/* Form + Button row */}
      <div className="flex items-end gap-3 border-b border-border bg-card px-4 py-3">
        <div className="flex flex-col gap-1">
          <label htmlFor="streamlines-velocity" className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
            Velocity (m/s)
          </label>
          <input
            id="streamlines-velocity"
            type="number"
            value={params.velocity}
            onChange={(e) => setParams((p) => ({ ...p, velocity: Number.parseFloat(e.target.value) || 0 }))}
            className="w-24 rounded-xl border border-border bg-input px-2 py-1.5 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="streamlines-alpha" className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
            Alpha (&deg;)
          </label>
          <input
            id="streamlines-alpha"
            type="number"
            value={params.alpha}
            onChange={(e) => setParams((p) => ({ ...p, alpha: Number.parseFloat(e.target.value) || 0 }))}
            className="w-20 rounded-xl border border-border bg-input px-2 py-1.5 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="streamlines-beta" className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
            Beta (&deg;)
          </label>
          <input
            id="streamlines-beta"
            type="number"
            value={params.beta}
            onChange={(e) => setParams((p) => ({ ...p, beta: Number.parseFloat(e.target.value) || 0 }))}
            className="w-20 rounded-xl border border-border bg-input px-2 py-1.5 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="streamlines-altitude" className="font-[family-name:var(--font-geist-sans)] text-[11px] text-muted-foreground">
            Altitude (m)
          </label>
          <input
            id="streamlines-altitude"
            type="number"
            value={params.altitude}
            onChange={(e) => setParams((p) => ({ ...p, altitude: Number.parseFloat(e.target.value) || 0 }))}
            className="w-24 rounded-xl border border-border bg-input px-2 py-1.5 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground"
          />
        </div>
        <button
          onClick={() => computeStreamlines(params)}
          disabled={isComputing || !aeroplaneId}
          className="flex items-center gap-1.5 rounded-full bg-primary px-4 py-2 font-[family-name:var(--font-geist-sans)] text-[13px] text-primary-foreground hover:opacity-90 disabled:opacity-50"
        >
          {isComputing ? <Loader2 size={14} className="animate-spin" /> : null}
          {isComputing ? "Computing\u2026" : "Compute"}
        </button>
      </div>

      {/* Plot area */}
      <div className="flex flex-1 items-center justify-center">
        {error && (
          <span className="font-[family-name:var(--font-geist-sans)] text-[13px] text-destructive">
            {error}
          </span>
        )}
        {!figure && !isComputing && !error && (
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
            Set parameters and click Compute
          </span>
        )}
        {isComputing && (
          <div className="flex items-center gap-2">
            <Loader2 size={16} className="animate-spin text-primary" />
            <span className="font-[family-name:var(--font-geist-sans)] text-[13px] text-muted-foreground">
              Computing streamlines&hellip;
            </span>
          </div>
        )}
        <div
          ref={plotContainerRef}
          className={`h-full w-full ${figure ? "" : "hidden"}`}
        />
      </div>
    </div>
  );
}
