"use client";

import useSWR from "swr";
import { fetcher, putJson } from "@/lib/fetcher";

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
}

export function useMissionObjectives(aeroplaneId: string | null) {
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
    return updated;
  };

  return { data, error, isLoading, update, mutate };
}
