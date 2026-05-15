"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";
import type { AxisName } from "./useMissionPresets";

export type Provenance = "computed" | "estimated" | "missing";

export interface MissionAxisKpi {
  axis: AxisName;
  value: number | null;
  unit: string | null;
  score_0_1: number | null;
  range_min: number;
  range_max: number;
  provenance: Provenance;
  formula: string;
  warning: string | null;
}

export interface MissionTargetPolygon {
  mission_id: string;
  label: string;
  scores_0_1: Partial<Record<AxisName, number>>;
}

export interface MissionKpiSet {
  aeroplane_uuid: string;
  ist_polygon: Record<AxisName, MissionAxisKpi>;
  target_polygons: MissionTargetPolygon[];
  active_mission_id: string;
  computed_at: string;
  context_hash: string;
}

export function useMissionKpis(
  aeroplaneId: string | null,
  missions: string[],
  options?: { readonly isRecomputing?: boolean },
) {
  const query = missions
    .map((m) => `missions=${encodeURIComponent(m)}`)
    .join("&");
  const params = query ? `?${query}` : "";
  const path = aeroplaneId
    ? `/aeroplanes/${encodeURIComponent(aeroplaneId)}/mission-kpis${params}`
    : null;
  return useSWR<MissionKpiSet | null>(
    path,
    fetcher,
    options?.isRecomputing ? { refreshInterval: 1500 } : undefined,
  );
}
