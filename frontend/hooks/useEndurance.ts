"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";

/**
 * Electric endurance / range response from GET /aeroplanes/{id}/endurance.
 * Matches app/schemas/endurance.py EnduranceResponse.
 */
export interface EnduranceData {
  t_endurance_max_s: number | null;
  range_max_m: number | null;
  p_req_at_v_md_w: number | null;
  p_req_at_v_min_sink_w: number | null;
  p_margin: number | null;
  p_margin_class: string | null;
  battery_mass_g_predicted: number | null;
  confidence: "computed" | "estimated";
  warnings: string[];
}

export function useEndurance(aeroplaneId: string | null) {
  const path = aeroplaneId
    ? `/aeroplanes/${encodeURIComponent(aeroplaneId)}/endurance`
    : null;

  const { data, error, isLoading, mutate } = useSWR<EnduranceData | null>(
    path,
    fetcher,
  );

  return { data, error, isLoading, mutate };
}
