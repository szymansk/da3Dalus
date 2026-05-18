"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useComputationContext } from "@/hooks/useComputationContext";
import type { PlotlyTrace } from "@/hooks/useOverlayRegistry";
import { buildStabilityTraces } from "./buildStabilityTraces";

const STORAGE_KEY = "stabilityOverlayEnabled";

interface Props {
  aeroplaneId: string | null;
  /** Stable setter from useOverlayRegistry — pass register('stability'). */
  register: (next: PlotlyTrace[]) => void;
}

/**
 * Self-contained overlay component that publishes Plotly traces for the
 * stability visualisation (NP, CG SOLL, CG IST, SM band, delta link)
 * into the parent overlay registry, and renders its own toggle button.
 *
 * Mount inside the workbench preview's overlay bar. Composes alongside
 * <WingOutlineViewer extraTraces={registry.traces} />.
 */
export function StabilityOverlay({ aeroplaneId, register }: Readonly<Props>) {
  const { data: ctx } = useComputationContext(aeroplaneId);

  const [enabled, setEnabled] = useState<boolean>(() => {
    if (typeof window === "undefined") return true;
    return localStorage.getItem(STORAGE_KEY) !== "false";
  });

  const toggle = useCallback(() => {
    setEnabled((prev) => {
      const next = !prev;
      if (typeof window !== "undefined") {
        localStorage.setItem(STORAGE_KEY, String(next));
      }
      return next;
    });
  }, []);

  const traces = useMemo<PlotlyTrace[]>(() => {
    if (!enabled || !ctx) return [];
    return buildStabilityTraces({
      x_np_m: ctx.x_np_m,
      mac_m: ctx.mac_m,
      cg_agg_m: ctx.cg_agg_m,
      target_static_margin: ctx.target_static_margin,
    });
  }, [enabled, ctx]);

  useEffect(() => {
    register(traces);
    // Cleanup fires on every traces change AND on unmount.
    // Intentional: registry must always reflect the current overlay state.
    // React 18+ batches the cleanup + new register call into a single commit,
    // so consumers see one state update per change, not two.
    return () => {
      register([]);
    };
  }, [register, traces]);

  const hasData = ctx?.x_np_m != null;
  const buttonTitle = hasData
    ? "Toggle stability markers"
    : "No aero data — run analysis first";
  const activeClasses =
    enabled && hasData
      ? "border-primary bg-primary/20 text-primary"
      : "border-border bg-card/80 text-muted-foreground hover:text-foreground";

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={!hasData}
      aria-pressed={enabled}
      title={buttonTitle}
      className={`rounded-lg border px-2 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[10px] backdrop-blur-sm disabled:opacity-50 ${activeClasses}`}
    >
      Stability
    </button>
  );
}
