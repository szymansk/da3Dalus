"use client";

import useSWR from "swr";
import { useCallback } from "react";
import { API_BASE, fetcher } from "@/lib/fetcher";

// ---------------------------------------------------------------------------
// Types (matching TailSizingResponse backend schema — gh-491)
// ---------------------------------------------------------------------------

export type TailClassification =
  | "in_range"
  | "below_range"
  | "above_range"
  | "out_of_physical_range"
  | "not_applicable";

export interface TailSizingResult {
  v_h_current: number | null;
  v_v_current: number | null;
  l_h_m: number | null;
  l_h_eff_from_aft_cg_m: number | null;
  s_h_recommended_mm2: number | null;
  s_v_recommended_mm2: number | null;
  classification: TailClassification;
  classification_h: TailClassification;
  classification_v: TailClassification;
  aircraft_class_used: string;
  cg_aware: boolean;
  v_h_target_min: number | null;
  v_h_target_max: number | null;
  v_v_target_min: number | null;
  v_v_target_max: number | null;
  v_h_citation: string;
  v_v_citation: string;
  warnings: string[];
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useTailSizing(aeroplaneId: string | null) {
  const path = aeroplaneId
    ? `/aeroplanes/${encodeURIComponent(aeroplaneId)}/tail-sizing`
    : null;

  const { data, error, isLoading, mutate } = useSWR<TailSizingResult>(
    path,
    fetcher,
  );

  /**
   * Trigger a single recompute of assumptions and then refresh tail sizing.
   * This is the pencil-action: one recompute, no cascade.
   */
  const recomputeOnce = useCallback(async (): Promise<void> => {
    if (!aeroplaneId) return;
    const res = await fetch(
      `${API_BASE}/aeroplanes/${aeroplaneId}/recompute`,
      { method: "POST" },
    );
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(`Recompute failed: ${res.status} ${body}`);
    }
    await mutate();
  }, [aeroplaneId, mutate]);

  return { data, error, isLoading, mutate, recomputeOnce };
}
