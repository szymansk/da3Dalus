"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";

// ── Types (snake_case verbatim per frozen contract) ──────────────

export type AirfoilFamily =
  | "flat_bottom"
  | "semi_symmetric"
  | "symmetric"
  | "cambered"
  | "reflexed";

export type MissionType =
  | "trainer"
  | "sport"
  | "aerobatic"
  | "glider"
  | "flying_wing";

export type ActiveLens =
  | "re_agnostic"
  | "mission"
  | "target_cl_cruise"
  | "target_cl_loiter";

/**
 * Lenses that drive the ranked sort order in the UI.
 * 'target_cl_loiter' is display-only — it adds a score column but never
 * re-ranks the list, so it is excluded here.
 */
export type RankingLens = Exclude<ActiveLens, "target_cl_loiter">;

export interface SuitabilityItem {
  airfoil_name: string;
  family: AirfoilFamily;
  re_agnostic: number;
  mission: number | null;
  target_cl_cruise: number | null;
  target_cl_loiter: number | null;
  min_analysis_confidence: number;
  tip_re_flag: boolean;
  /**
   * Pre-formatted human-readable caveat text.
   * This is the `.text` field of the backend `SuitabilityCaveat` object —
   * not the caveat object itself. The backend serialises it as a plain string
   * per item so the UI can render it without further processing.
   */
  caveat: string;
}

export interface SuitabilityQuery {
  chord_m: number;
  speed_ms: number;
  reynolds: number;
  re_clamped: boolean;
  mission_type: string | null;
  target_cl_cruise: number | null;
  target_cl_loiter: number | null;
  active_lens: ActiveLens;
}

export interface SuitabilityCaveat {
  relative_ranking_only: boolean;
  no_hysteresis_modelling: boolean;
  recommend_xfoil_validation: boolean;
  text: string;
}

export interface AirfoilSuitabilityResponse {
  query: SuitabilityQuery;
  caveat: SuitabilityCaveat;
  results: SuitabilityItem[];
}

export interface UseAirfoilSuitabilityParams {
  chord_m: number | undefined;
  speed_ms: number | undefined;
  /**
   * The aeroplane UUID string (from useAeroplaneContext().aeroplaneId).
   * Passed by the caller rather than read from context, to keep the hook
   * free of component-layer imports (dependency-cruiser: no-hooks-import-components).
   */
  aeroplane_id?: string | null;
  mission_type?: MissionType;
  target_cl_cruise?: number;
  target_cl_loiter?: number;
  limit?: number;
  tip_chord_m?: number;
}

// ── Hook ─────────────────────────────────────────────────────────

export function useAirfoilSuitability(params: UseAirfoilSuitabilityParams) {
  const {
    chord_m,
    speed_ms,
    aeroplane_id,
    mission_type,
    target_cl_cruise,
    target_cl_loiter,
    limit,
    tip_chord_m,
  } = params;

  // Only build a key when required params are present
  const key =
    chord_m != null && speed_ms != null
      ? buildKey(chord_m, speed_ms, aeroplane_id ?? null, {
          mission_type,
          target_cl_cruise,
          target_cl_loiter,
          limit,
          tip_chord_m,
        })
      : null;

  const { data, error, isLoading } = useSWR<AirfoilSuitabilityResponse>(
    key,
    fetcher,
    {
      revalidateOnFocus: false,
      dedupingInterval: 30_000,
    },
  );

  return {
    data: data ?? null,
    isLoading,
    error: error ?? null,
  };
}

function buildKey(
  chord_m: number,
  speed_ms: number,
  aeroplaneId: string | null,
  optional: {
    mission_type?: MissionType;
    target_cl_cruise?: number;
    target_cl_loiter?: number;
    limit?: number;
    tip_chord_m?: number;
  },
): string {
  const params = new URLSearchParams();
  params.set("chord_m", String(chord_m));
  params.set("speed_ms", String(speed_ms));
  if (aeroplaneId != null) {
    params.set("aeroplane_id", aeroplaneId);
  }
  if (optional.mission_type != null) {
    params.set("mission_type", optional.mission_type);
  }
  if (optional.target_cl_cruise != null) {
    params.set("target_cl_cruise", String(optional.target_cl_cruise));
  }
  if (optional.target_cl_loiter != null) {
    params.set("target_cl_loiter", String(optional.target_cl_loiter));
  }
  if (optional.limit != null) {
    params.set("limit", String(optional.limit));
  }
  if (optional.tip_chord_m != null) {
    params.set("tip_chord_m", String(optional.tip_chord_m));
  }
  return `/airfoils/db/suitability?${params.toString()}`;
}
