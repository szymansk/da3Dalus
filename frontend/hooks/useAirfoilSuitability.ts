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
  | "target_cl_cruise";

/**
 * Lenses that drive the ranked sort order in the UI.
 * Glide points (target_cl_best_glide, target_cl_min_sink) are display-only —
 * they add score columns but never re-rank the list.
 * ActiveLens is already the ranking set (no loiter/glide points),
 * so RankingLens is kept as a distinct union for semantic clarity in imports.
 */
// eslint-disable-next-line sonarjs/redundant-type-aliases
export type RankingLens = ActiveLens;

/**
 * Provenance of the target CL values.
 * 'calculated' — all inputs from automated design assumptions (v_cruise_auto etc.)
 * 'estimated'  — all inputs from manual user estimates
 * 'mixed'      — some calculated, some estimated
 */
export type TargetClProvenance = "estimated" | "calculated" | "mixed";

export interface SuitabilityItem {
  airfoil_name: string;
  family: AirfoilFamily;
  re_agnostic: number;
  mission: number | null;
  target_cl_cruise: number | null;
  /** NEW gh-825 — target CL at best-glide (engine-off / glide) */
  target_cl_best_glide: number | null;
  /** RENAMED from target_cl_loiter — target CL at min-sink */
  target_cl_min_sink: number | null;
  /**
   * NEW gh-825 — raw dCL/dα past peak (≈0 gentle, negative = abrupt stall).
   * NOT a 0..1 score — raw engineering value.
   */
  stall_gentleness: number | null;
  /**
   * NEW gh-825 — signed CL margin = cl_max − max(target CLs present).
   * Negative means the target exceeds the section CL_max.
   */
  cl_max_margin: number | null;
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
  /** NEW gh-825 — resolved best-glide target CL */
  target_cl_best_glide: number | null;
  /** RENAMED from target_cl_loiter */
  target_cl_min_sink: number | null;
  /** NEW gh-825 — provenance of the target CL values */
  target_cl_provenance: TargetClProvenance;
  active_lens: ActiveLens;
}

export interface SuitabilityCaveat {
  relative_ranking_only: boolean;
  no_hysteresis_modelling: boolean;
  /** NEW gh-825 — always true; score is section-CL == wing-CL ideal (elliptical, untwisted) */
  ignores_tip_re_clmax_collapse: boolean;
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
  /** RENAMED from target_cl_loiter */
  target_cl_min_sink?: number;
  /** NEW gh-825 — best-glide target CL */
  target_cl_best_glide?: number;
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
    target_cl_min_sink,
    target_cl_best_glide,
    limit,
    tip_chord_m,
  } = params;

  // Only build a key when required params are present
  const key =
    chord_m != null && speed_ms != null
      ? buildKey(chord_m, speed_ms, aeroplane_id ?? null, {
          mission_type,
          target_cl_cruise,
          target_cl_min_sink,
          target_cl_best_glide,
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
    target_cl_min_sink?: number;
    target_cl_best_glide?: number;
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
  if (optional.target_cl_min_sink != null) {
    params.set("target_cl_min_sink", String(optional.target_cl_min_sink));
  }
  if (optional.target_cl_best_glide != null) {
    params.set("target_cl_best_glide", String(optional.target_cl_best_glide));
  }
  if (optional.limit != null) {
    params.set("limit", String(optional.limit));
  }
  if (optional.tip_chord_m != null) {
    params.set("tip_chord_m", String(optional.tip_chord_m));
  }
  return `/airfoils/db/suitability?${params.toString()}`;
}
