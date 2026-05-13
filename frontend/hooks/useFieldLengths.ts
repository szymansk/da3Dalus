"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";

// ---------------------------------------------------------------------------
// Types (matching backend FieldLengthRead schema)
// ---------------------------------------------------------------------------

export type TakeoffMode = "runway" | "hand_launch" | "bungee" | "catapult";
export type LandingMode = "runway" | "belly_land";

export interface FieldLengthResult {
  s_to_ground_m: number;
  s_to_50ft_m: number;
  s_ldg_ground_m: number;
  s_ldg_50ft_m: number;
  vto_obstacle_mps: number;
  vapp_mps: number;
  mode_takeoff: TakeoffMode;
  mode_landing: LandingMode;
  warnings: string[];
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

interface UseFieldLengthsOptions {
  takeoffMode?: TakeoffMode;
  landingMode?: LandingMode;
  vThrowMps?: number | null;
  vReleaseMps?: number | null;
  bungeeForceN?: number | null;
  stretchM?: number | null;
}

export function useFieldLengths(
  aeroplaneId: string | null,
  {
    takeoffMode = "runway",
    landingMode = "runway",
    vThrowMps,
    vReleaseMps,
    bungeeForceN,
    stretchM,
  }: UseFieldLengthsOptions = {}
) {
  const params = new URLSearchParams();
  params.set("takeoff_mode", takeoffMode);
  params.set("landing_mode", landingMode);
  if (vThrowMps != null) params.set("v_throw_mps", String(vThrowMps));
  if (vReleaseMps != null) params.set("v_release_mps", String(vReleaseMps));
  if (bungeeForceN != null) params.set("bungee_force_N", String(bungeeForceN));
  if (stretchM != null) params.set("stretch_m", String(stretchM));

  const url = aeroplaneId
    ? `/aeroplanes/${aeroplaneId}/field-lengths?${params}`
    : null;

  return useSWR<FieldLengthResult>(url, fetcher, {
    revalidateOnFocus: false,
    // Field lengths depend on design assumptions; revalidate when they change
    // by using a focused SWR key. Callers should call mutate() when assumptions change.
  });
}
