"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";

export type AxisName =
  | "stall_safety"
  | "glide"
  | "climb"
  | "cruise"
  | "maneuver"
  | "wing_loading"
  | "field_friendliness";

export interface MissionPreset {
  id: string;
  label: string;
  description: string;
  target_polygon: Record<AxisName, number>;
  axis_ranges: Record<AxisName, [number, number]>;
  suggested_estimates: {
    g_limit: number;
    target_static_margin: number;
    cl_max: number;
    power_to_weight: number;
    prop_efficiency: number;
  };
}

export function useMissionPresets() {
  return useSWR<MissionPreset[] | null>("/mission-presets", fetcher);
}
