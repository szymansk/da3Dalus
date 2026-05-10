"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";

export interface ComputationContext {
  v_cruise_mps: number;
  reynolds: number;
  mac_m: number;
  x_np_m: number;
  target_static_margin: number;
  cg_agg_m: number | null;
  computed_at: string;
}

export function useComputationContext(aeroplaneId: string | null) {
  const path = aeroplaneId
    ? `/aeroplanes/${encodeURIComponent(aeroplaneId)}/assumptions/computation-context`
    : null;
  const { data, error, isLoading, mutate } = useSWR<ComputationContext | null>(
    path,
    fetcher,
  );

  return { data, error, isLoading, mutate };
}
