"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";

// ---------------------------------------------------------------------------
// Types matching backend PowertrainSolutionSpaceResponse (gh-976)
// ---------------------------------------------------------------------------

export interface SolutionRow {
  cell_count: number;
  v_nom_v: number;
  v_sag_v: number;
  p_cruise_w: number;
  p_top_w: number;
  p_cruise_lo_w: number;
  p_cruise_hi_w: number;
  p_top_lo_w: number;
  p_top_hi_w: number;
  energy_wh: number;
  capacity_mah_min: number;
  capacity_mah_min_lo: number;
  capacity_mah_min_hi: number;
  i_peak_a: number;
  i_peak_lo_a: number;
  i_peak_hi_a: number;
  c_min: number;
  c_min_lo: number;
  c_min_hi: number;
  esc_min_a: number;
  esc_min_lo_a: number;
  esc_min_hi_a: number;
  motor_peak_w: number;
  motor_cont_w: number;
  kv_approx: number | null;
  has_motor_match: boolean;
  has_battery_match: boolean;
  has_esc_match: boolean;
}

export interface FeasibleRegion {
  cell_count: number;
  capacity_floor_mah: number;
  i_peak_a: number;
  capacity_curve_mah: number[];
  c_rate_curve: number[];
}

export interface ShoppingSpec {
  cell_count: number;
  battery_min_mah: number;
  battery_min_c: number;
  battery_v_nom: number;
  esc_min_a: number;
  motor_min_peak_w: number;
  motor_cont_w: number;
  kv_approx: number | null;
}

export interface PowertrainSolutionSpaceResponse {
  rows: SolutionRow[];
  feasible_regions: FeasibleRegion[];
  shopping_specs: ShoppingSpec[];
  p_aero_cruise_w: number;
  p_aero_top_w: number;
  energy_wh: number;
  v_cruise_mps: number;
  v_top_mps: number;
  t_target_min: number;
  assumptions_used: SolutionSpaceAssumptions;
  warnings: string[];
}

export interface SolutionSpaceAssumptions {
  cell_counts?: number[];
  eta_prop_lo?: number;
  eta_prop_hi?: number;
  eta_motor?: number;
  eta_esc?: number;
  dod?: number;
  esc_margin?: number;
  c_margin?: number;
  load_rpm_factor?: number;
  prop_pd?: number;
  t_target_min?: number;
  v_top_mps?: number;
  rho?: number;
  g?: number;
}

// ---------------------------------------------------------------------------
// URL builder (extracted to keep hook's cognitive complexity ≤ 15)
// ---------------------------------------------------------------------------

function setIfDefined(
  params: URLSearchParams,
  key: string,
  value: number | undefined | null
): void {
  if (value != null) params.set(key, String(value));
}

export function buildSolutionSpaceUrl(
  aeroplaneId: string | null,
  assumptions: SolutionSpaceAssumptions
): string | null {
  if (!aeroplaneId) return null;

  const params = new URLSearchParams();

  if (assumptions.cell_counts && assumptions.cell_counts.length > 0) {
    for (const s of assumptions.cell_counts) {
      params.append("cell_counts", String(s));
    }
  }
  setIfDefined(params, "eta_prop_lo", assumptions.eta_prop_lo);
  setIfDefined(params, "eta_prop_hi", assumptions.eta_prop_hi);
  setIfDefined(params, "eta_motor", assumptions.eta_motor);
  setIfDefined(params, "eta_esc", assumptions.eta_esc);
  setIfDefined(params, "dod", assumptions.dod);
  setIfDefined(params, "esc_margin", assumptions.esc_margin);
  setIfDefined(params, "c_margin", assumptions.c_margin);
  setIfDefined(params, "load_rpm_factor", assumptions.load_rpm_factor);
  setIfDefined(params, "prop_pd", assumptions.prop_pd);
  setIfDefined(params, "t_target_min", assumptions.t_target_min);
  setIfDefined(params, "v_top_mps", assumptions.v_top_mps);
  setIfDefined(params, "rho", assumptions.rho);
  setIfDefined(params, "g", assumptions.g);

  const base = `/aeroplanes/${encodeURIComponent(aeroplaneId)}/powertrain/solution-space`;
  const qs = params.toString();
  return qs ? `${base}?${qs}` : base;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function usePowertrainSolutionSpace(
  aeroplaneId: string | null,
  assumptions: SolutionSpaceAssumptions = {}
) {
  const url = buildSolutionSpaceUrl(aeroplaneId, assumptions);

  const { data, error, isLoading, mutate } = useSWR<PowertrainSolutionSpaceResponse>(
    url,
    fetcher,
    { revalidateOnFocus: false }
  );

  return { data, error, isLoading, mutate };
}
