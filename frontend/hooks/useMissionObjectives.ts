"use client";

import useSWR, { useSWRConfig } from "swr";
import { fetcher, putJson } from "@/lib/fetcher";

// gh-477: backend ``LandingSurface`` literal — keep in lock-step with
// ``app/schemas/mission_objective.py``. The mission page uses these
// values verbatim in the dropdown.
export type LandingSurface =
  | "grass_short"
  | "grass_long"
  | "hard_paved"
  | "soft_soil"
  | "belly_grass"
  | "net_recovery";

export interface MissionObjective {
  mission_type: string;
  target_cruise_mps: number;
  target_stall_safety: number;
  target_maneuver_n: number;
  target_glide_ld: number;
  target_climb_energy: number;
  target_wing_loading_n_m2: number;
  target_field_length_m: number;
  available_runway_m: number;
  runway_type: "grass" | "asphalt" | "belly";
  t_static_N: number;
  takeoff_mode: "runway" | "hand_launch" | "bungee" | "catapult";
  // gh-477: landing-field-length inputs. All optional — the service
  // falls back to grass-short / safety=1.5 / no length check when absent.
  landing_surface?: LandingSurface | null;
  landing_safety_factor?: number | null;
  available_field_length_m?: number | null;
}

export function useMissionObjectives(aeroplaneId: string | null) {
  const { mutate: globalMutate } = useSWRConfig();
  const path = aeroplaneId
    ? `/aeroplanes/${encodeURIComponent(aeroplaneId)}/mission-objectives`
    : null;
  const { data, error, isLoading, mutate } = useSWR<MissionObjective | null>(
    path,
    fetcher,
  );

  const update = async (
    payload: MissionObjective,
  ): Promise<MissionObjective | null> => {
    if (!aeroplaneId || !path) return null;
    const updated = await putJson<MissionObjective>(path, payload);
    await mutate(updated, { revalidate: false });
    // gh-770: the spider chart's Soll polygon (and Ist) is computed server-side
    // in /mission-kpis from the persisted objective (since gh-767). Revalidate
    // every mission-kpis cache entry for this aeroplane so the radar refreshes
    // live instead of only after a page reload. Prefix match because the key
    // carries a `?missions=…` query that varies with the active/comparison set.
    const kpiPrefix = `/aeroplanes/${encodeURIComponent(aeroplaneId)}/mission-kpis`;
    await globalMutate(
      (key) => typeof key === "string" && key.startsWith(kpiPrefix),
    );
    return updated;
  };

  return { data, error, isLoading, update, mutate };
}
