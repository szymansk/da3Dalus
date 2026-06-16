// frontend/hooks/useSpanwiseLoads.ts
"use client";

// gh-1002: Spanwise shear + bending-moment distribution hook.
// Calls POST /aeroplanes/{id}/spanwise_loads — pure post-processing over
// strip forces, so the same operating-point parameters as useStripForces apply.

import { useState, useCallback } from "react";
import { API_BASE } from "@/lib/fetcher";
import { parseApiError } from "@/lib/parseApiError";

export interface SpanwiseLoadEntry {
  y_m: number;
  chord_m: number;
  shear_N: number;
  bending_moment_Nm: number;
}

export interface SurfaceSpanwiseLoads {
  surface_name: string;
  starboard: SpanwiseLoadEntry[];
  port: SpanwiseLoadEntry[];
  root_shear_N_starboard: number;
  root_shear_N_port: number;
  root_bending_moment_Nm_starboard: number;
  root_bending_moment_Nm_port: number;
}

export interface SpanwiseLoadsResult {
  alpha: number;
  velocity_mps: number;
  altitude_m: number;
  dynamic_pressure_Pa: number;
  surfaces: SurfaceSpanwiseLoads[];
}

export interface SpanwiseLoadsParams {
  velocity: number;
  alpha: number;
  beta: number;
  altitude: number;
  xyz_ref: number[];
  operating_point_id?: number | null;
}

export function useSpanwiseLoads(aeroplaneId: string | null) {
  const [result, setResult] = useState<SpanwiseLoadsResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(
    async (params: SpanwiseLoadsParams) => {
      if (!aeroplaneId) return;
      setIsRunning(true);
      setError(null);
      setResult(null);

      try {
        const requestBody: Record<string, unknown> = {
          velocity: params.velocity,
          alpha: params.alpha,
          beta: params.beta,
          altitude: params.altitude,
          xyz_ref: params.xyz_ref,
        };
        if (params.operating_point_id != null) {
          requestBody.operating_point_id = params.operating_point_id;
        }

        const res = await fetch(
          `${API_BASE}/aeroplanes/${aeroplaneId}/spanwise_loads`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(requestBody),
          },
        );
        if (!res.ok) {
          throw new Error(await parseApiError(res, "Spanwise loads"));
        }
        const data: SpanwiseLoadsResult = await res.json();
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
