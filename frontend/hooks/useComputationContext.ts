"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";

export interface ComputationContext {
  v_cruise_mps: number;
  v_cruise_auto?: boolean;
  v_max_mps?: number | null;
  v_stall_mps?: number | null;
  v_md_mps?: number | null;
  // gh-476: extended V-speed set surfaced on the chip row.
  v_min_sink_mps?: number | null;
  v_a_mps?: number | null;
  v_dive_mps?: number | null;
  v_x_mps?: number | null;
  v_y_mps?: number | null;
  is_glider?: boolean;
  reynolds: number;
  mac_m: number;
  s_ref_m2?: number | null;
  aspect_ratio?: number | null;
  x_np_m: number;
  target_static_margin: number;
  cg_agg_m: number | null;
  computed_at: string;
}

export function useComputationContext(
  aeroplaneId: string | null,
  options?: { readonly isRecomputing?: boolean },
) {
  const path = aeroplaneId
    ? `/aeroplanes/${encodeURIComponent(aeroplaneId)}/assumptions/computation-context`
    : null;
  // While the assumption compute job is in flight, poll every 1.5s so
  // the chip values update as soon as the backend settles. Polling
  // stops as soon as isRecomputing flips back to false.
  const { data, error, isLoading, mutate } = useSWR<ComputationContext | null>(
    path,
    fetcher,
    options?.isRecomputing ? { refreshInterval: 1500 } : undefined,
  );

  return { data, error, isLoading, mutate };
}
