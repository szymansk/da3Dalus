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
  /** Optional y-coordinate for marker placement (metres).
   *  Use the main wing's root LE y so markers sit on the wing. */
  referenceY?: number;
  /** Optional z-coordinate for marker placement (metres).
   *  Use the main wing's root LE z so markers sit on the wing's chord line. */
  referenceZ?: number;
}

/**
 * Self-contained overlay component that publishes Plotly traces for the
 * stability visualisation (NP, CG SOLL, CG IST, SM band, delta link)
 * into the parent overlay registry, and renders its own toggle button.
 *
 * Mount inside the workbench preview's overlay bar. Composes alongside
 * <WingOutlineViewer extraTraces={registry.traces} />.
 */
export function StabilityOverlay({
  aeroplaneId,
  register,
  referenceY,
  referenceZ,
}: Readonly<Props>) {
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
    return buildStabilityTraces(
      {
        x_np_m: ctx.x_np_m,
        mac_m: ctx.mac_m,
        cg_agg_m: ctx.cg_agg_m,
        target_static_margin: ctx.target_static_margin,
      },
      { referenceY, referenceZ },
    );
  }, [enabled, ctx, referenceY, referenceZ]);

  useEffect(() => {
    register(traces);
    // Cleanup fires on every traces change AND on unmount. Intentional:
    // the registry must always reflect the current overlay state. Note
    // that this re-runs the cleanup `register([])` and the setup
    // `register(traces)` back-to-back — both setState calls are caught
    // by React 18+ automatic batching, so consumers see one render per
    // change. Side effect: this re-inserts the 'stability' key at the
    // end of useOverlayRegistry's insertion order on every change —
    // fine for a single overlay, watch out if cross-overlay z-ordering
    // ever matters.
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
