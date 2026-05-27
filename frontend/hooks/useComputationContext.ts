"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";
import type { EQuality } from "@/lib/polar";

export type PolarRejectionGate =
  | "insufficient_points"
  | "non_monotonic_polar"
  | "negative_slope_k"
  | "non_positive_cd0"
  | "unphysical_e_oswald"
  | "cd0_stability_mismatch";

export type PolarRejectionCategory = "sweep" | "data" | "design" | "consistency";

export interface PolarRejection {
  gate: PolarRejectionGate;
  category: PolarRejectionCategory;
  fitted_value: number | null;
  threshold: string;
  hint: string;
}

export type PolarConfigName = "clean" | "takeoff" | "landing";

export type EOswaldProvenance =
  | "aerobuildup_trefftz"
  | "fit"
  | "fallback";

export interface ParabolicPolar {
  cd0: number | null;
  e_oswald: number | null;
  cl_max: number;
  e_oswald_r2: number | null;
  e_oswald_quality: "high" | "medium" | "low" | "unknown";
  flap_deflection_deg: number;
  provenance: "aerobuildup" | "no_flap_geometry" | "aerobuildup_failed";
  rejection: PolarRejection | null;
  // gh-636: empirical (L/D)max + CL_at_(L/D)max from the AeroBuildup sweep;
  // provenance of e (vlm-trefftz / fit / fallback).
  ld_max?: number | null;
  cl_at_ld_max?: number | null;
  e_oswald_provenance?: EOswaldProvenance;
}

export type PolarByConfig = Record<PolarConfigName, ParabolicPolar>;

export interface ComputationContext {
  v_cruise_mps: number;
  v_cruise_auto?: boolean;
  v_max_mps?: number | null;
  v_stall_mps?: number | null;
  v_md_mps?: number | null;
  // gh-476: extended V-speed set surfaced on the chip row.
  v_min_sink_mps?: number | null;
  // gh-692: vertical speed at V_min_sink — minimum sink rate the polar can deliver.
  // Glider/Motorsegler chip; powered aircraft also receive it for completeness.
  min_sink_rate_mps?: number | null;
  v_a_mps?: number | null;
  v_dive_mps?: number | null;
  v_x_mps?: number | null;
  v_y_mps?: number | null;
  is_glider?: boolean;
  reynolds: number;
  mac_m: number;
  s_ref_m2?: number | null;
  // gh-593: reference span (main wing), surfaced as the B_ref chip alongside
  // S_ref and MAC for coefficient non-dimensionalisation.
  b_ref_m?: number | null;
  aspect_ratio?: number | null;
  // gh-626: polar metrics surfaced in PolarChipRow.
  cd0?: number | null;
  e_oswald?: number | null;
  e_oswald_quality?: EQuality;
  e_oswald_fallback_used?: boolean;
  x_np_m: number;
  target_static_margin: number;
  cg_agg_m: number | null;
  // gh-581: tailless configuration flag — derived backend-side from geometry
  // (no horizontal-tail wing). Used to surface the tailless UX banner and to
  // gate tail-volume-related UI off when true.
  is_tailless?: boolean;
  computed_at: string;
  // gh-630 + gh-636: per-config polars + empirical L/D max + e provenance.
  polar_by_config?: PolarByConfig;
  // gh-477: required landing field length from physics + mission surface.
  // ``landing_field_length_m`` is null when CL_max_landing, mass, or S_ref
  // is not yet known. ``landing_field_sufficient`` compares against the
  // mission's ``available_field_length_m``; null when one of the two is
  // absent (chip renders neutral).
  landing_field_length_m?: number | null;
  landing_surface_used?: string | null;
  landing_field_sufficient?: boolean | null;
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
