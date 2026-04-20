// frontend/hooks/useStripForces.ts
"use client";

import { useState, useCallback } from "react";
import { API_BASE } from "@/lib/fetcher";

export interface StripForceEntry {
  j: number;
  Xle: number;
  Yle: number;
  Zle: number;
  Chord: number;
  Area: number;
  c_cl: number;
  ai: number;
  cl_norm: number;
  cl: number;
  cd: number;
  cdv: number;
  "cm_c/4": number;
  cm_LE: number;
  "C.P.x/c": number;
}

export interface SurfaceStripForces {
  surface_name: string;
  surface_number: number;
  n_chordwise: number;
  n_spanwise: number;
  surface_area: number;
  strips: StripForceEntry[];
}

export interface StripForcesResult {
  alpha: number;
  mach: number;
  sref: number;
  cref: number;
  bref: number;
  surfaces: SurfaceStripForces[];
}

export interface StripForcesParams {
  wing_name: string;
  velocity: number;
  alpha: number;
  beta: number;
  altitude: number;
  xyz_ref: number[];
}

export function useStripForces(aeroplaneId: string | null) {
  const [result, setResult] = useState<StripForcesResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(
    async (params: StripForcesParams) => {
      if (!aeroplaneId) return;
      setIsRunning(true);
      setError(null);

      try {
        const res = await fetch(
          `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${encodeURIComponent(params.wing_name)}/strip_forces`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              velocity: params.velocity,
              alpha: params.alpha,
              beta: params.beta,
              altitude: params.altitude,
              xyz_ref: params.xyz_ref,
            }),
          },
        );
        if (!res.ok) {
          const body = await res.text();
          throw new Error(`Strip forces failed: ${res.status} ${body}`);
        }
        const data: StripForcesResult = await res.json();
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
