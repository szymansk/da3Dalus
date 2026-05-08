"use client";

import { useState, useCallback } from "react";
import { API_BASE } from "@/lib/fetcher";

export interface MassSweepPoint {
  mass_kg: number;
  wing_loading_pa: number;
  stall_speed_ms: number;
  required_cl: number;
  cl_margin: number;
}

export interface MassSweepData {
  s_ref: number;
  cl_max: number;
  velocity: number;
  altitude: number;
  points: MassSweepPoint[];
}

export interface ComputeOptions {
  velocity?: number;
  altitude?: number;
  masses?: number[];
}

function defaultMasses(): number[] {
  const masses: number[] = [];
  for (let m = 0.5; m <= 10; m += 0.5) {
    masses.push(m);
  }
  return masses;
}

export function useMassSweep(aeroplaneId: string | null) {
  const [data, setData] = useState<MassSweepData | null>(null);
  const [isComputing, setIsComputing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const compute = useCallback(
    async (opts: ComputeOptions = {}) => {
      if (!aeroplaneId) return;
      setIsComputing(true);
      setError(null);

      try {
        const res = await fetch(
          `${API_BASE}/aeroplanes/${aeroplaneId}/mass_sweep`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              masses_kg: opts.masses ?? defaultMasses(),
              velocity: opts.velocity ?? 15.0,
              altitude: opts.altitude ?? 0.0,
            }),
          },
        );
        if (!res.ok) {
          const body = await res.text();
          throw new Error(`Compute failed: ${res.status} ${body}`);
        }
        const json: MassSweepData = await res.json();
        setData(json);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setIsComputing(false);
      }
    },
    [aeroplaneId],
  );

  return { data, isComputing, error, compute };
}
