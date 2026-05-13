"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";

// ---------------------------------------------------------------------------
// Types matching backend MatchingChartResponse schema (gh-492)
// ---------------------------------------------------------------------------

export type AircraftMode =
  | "rc_runway"
  | "rc_hand_launch"
  | "uav_runway"
  | "uav_belly_land";

export interface ConstraintLine {
  name: string;
  /** T/W values at each W/S sample point (line constraints); null for vertical constraints */
  t_w_points: number[] | null;
  /** Maximum allowable W/S [N/m²] (vertical line); null for line constraints */
  ws_max: number | null;
  /** Hex color for the constraint line */
  color: string;
  /** True when the design point is near this constraint (actively limiting) */
  binding: boolean;
  /** Short formula / reference for hover tooltip */
  hover_text: string | null;
}

export interface DesignPoint {
  /** Wing loading [N/m²] */
  ws_n_m2: number;
  /** T/W = T_static_SL / W_MTOW (dimensionless) */
  t_w: number;
}

export type Feasibility = "feasible" | "infeasible_below_constraints";

export interface MatchingChartData {
  /** W/S sweep [N/m²] — X-axis of the chart */
  ws_range_n_m2: number[];
  /** Constraint lines */
  constraints: ConstraintLine[];
  /** Aircraft design point */
  design_point: DesignPoint;
  feasibility: Feasibility;
  warnings: string[];
}

// ---------------------------------------------------------------------------
// Hook options
// ---------------------------------------------------------------------------

export interface UseMatchingChartOptions {
  mode?: AircraftMode;
  sRunway?: number | null;
  vSTarget?: number | null;
  gammaClimbDeg?: number | null;
  vCruiseMps?: number | null;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useMatchingChart(
  aeroplaneId: string | null,
  {
    mode = "rc_runway",
    sRunway,
    vSTarget,
    gammaClimbDeg,
    vCruiseMps,
  }: UseMatchingChartOptions = {}
) {
  const params = new URLSearchParams();
  params.set("mode", mode);
  if (sRunway != null) params.set("s_runway", String(sRunway));
  if (vSTarget != null) params.set("v_s_target", String(vSTarget));
  if (gammaClimbDeg != null) params.set("gamma_climb_deg", String(gammaClimbDeg));
  if (vCruiseMps != null) params.set("v_cruise_mps", String(vCruiseMps));

  const url = aeroplaneId
    ? `/aeroplanes/${encodeURIComponent(aeroplaneId)}/matching-chart?${params}`
    : null;

  const { data, error, isLoading, mutate } = useSWR<MatchingChartData>(
    url,
    fetcher,
    {
      revalidateOnFocus: false,
    }
  );

  return { data, error, isLoading, mutate };
}
