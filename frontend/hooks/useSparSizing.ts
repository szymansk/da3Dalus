// frontend/hooks/useSparSizing.ts
// gh-1008: Spar sizing from spanwise loads.
// Calls POST /aeroplanes/{id}/spanwise_loads_with_sizing

"use client";

import { useState, useCallback } from "react";
import { API_BASE } from "@/lib/fetcher";
import { parseApiError } from "@/lib/parseApiError";
import type { SpanwiseLoadsParams } from "@/hooks/useSpanwiseLoads";

// ---- Types (mirrors app/schemas/spar_sizing.py) ----------------------------

export type SparShape = "tube" | "rod" | "rectangular" | "capped";

export interface SparSizingStation {
  y_m: number;
  chord_m: number;
  profile_thickness_mm: number;
  outer_mm: number;
  tc_ratio: number;
  tc_fallback: boolean;
  m_design_Nm: number;
  required_W_mm3: number;
  solved_mm: number | null;
  feasible: boolean;
  infeasibility_reason: string | null;
  cross_section_area_mm2: number | null;
}

export interface SparSizingResult {
  surface_name: string;
  shape: SparShape;
  material_name: string;
  sigma_allow_mpa: number;
  density_kg_m3: number;
  g_limit: number;
  g_limit_fallback: boolean;
  safety_factor_j: number;
  packing_factor: number;
  stations: SparSizingStation[];
  root_station: SparSizingStation;
  spar_mass_half_kg: number;
  spar_mass_full_kg: number;
  tc_fallback_warning: string | null;
}

export interface SpanwiseLoadsWithSizingResult {
  alpha: number;
  velocity_mps: number;
  altitude_m: number;
  dynamic_pressure_Pa: number;
  surfaces: unknown[];
  spar_sizing: SparSizingResult[] | null;
}

// ---- Spar sizing parameters ------------------------------------------------

export interface SparSizingParams {
  material_id: number;
  shape: SparShape;
  sigma_allow_mpa_override?: number | null;
  safety_factor_j?: number;
  packing_factor?: number;
  cap_width_mm?: number | null;
}

// ---- Hook ------------------------------------------------------------------

export function useSparSizing(aeroplaneId: string | null) {
  const [result, setResult] = useState<SpanwiseLoadsWithSizingResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(
    async (
      opParams: SpanwiseLoadsParams,
      sizingParams: SparSizingParams,
    ) => {
      if (!aeroplaneId) return;
      setIsRunning(true);
      setError(null);
      setResult(null);

      try {
        // Build query string for sizing params
        const qs = new URLSearchParams();
        qs.set("material_id", String(sizingParams.material_id));
        qs.set("shape", sizingParams.shape);
        if (sizingParams.safety_factor_j != null)
          qs.set("safety_factor_j", String(sizingParams.safety_factor_j));
        if (sizingParams.packing_factor != null)
          qs.set("packing_factor", String(sizingParams.packing_factor));
        if (sizingParams.sigma_allow_mpa_override != null)
          qs.set("sigma_allow_mpa_override", String(sizingParams.sigma_allow_mpa_override));
        if (sizingParams.cap_width_mm != null)
          qs.set("cap_width_mm", String(sizingParams.cap_width_mm));

        const requestBody: Record<string, unknown> = {
          velocity: opParams.velocity,
          alpha: opParams.alpha,
          beta: opParams.beta,
          altitude: opParams.altitude,
          xyz_ref: opParams.xyz_ref,
        };
        if (opParams.operating_point_id != null) {
          requestBody.operating_point_id = opParams.operating_point_id;
        }

        const res = await fetch(
          `${API_BASE}/aeroplanes/${aeroplaneId}/spanwise_loads_with_sizing?${qs}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(requestBody),
          },
        );
        if (!res.ok) {
          throw new Error(await parseApiError(res, "Spar sizing"));
        }
        const data: SpanwiseLoadsWithSizingResult = await res.json();
        setResult(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setIsRunning(false);
      }
    },
    [aeroplaneId],
  );

  return { result, isRunning, error, run };
}
