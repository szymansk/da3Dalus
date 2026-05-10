"use client";

import { useState, useCallback, useEffect } from "react";
import { API_BASE } from "@/lib/fetcher";

export interface StabilityData {
  id: number;
  aeroplane_id: number;
  solver: string;
  neutral_point_x: number | null;
  mac: number | null;
  cg_x_used: number | null;
  static_margin_pct: number | null;
  stability_class: "stable" | "neutral" | "unstable" | null;
  cg_range_forward: number | null;
  cg_range_aft: number | null;
  Cma: number | null;
  Cnb: number | null;
  Clb: number | null;
  is_statically_stable: boolean;
  is_directionally_stable: boolean;
  is_laterally_stable: boolean;
  trim_alpha_deg: number | null;
  trim_elevator_deg: number | null;
  computed_at: string;
  status: "CURRENT" | "DIRTY";
  geometry_hash: string | null;
}

export interface UseStabilityReturn {
  data: StabilityData | null;
  isLoading: boolean;
  isComputing: boolean;
  error: string | null;
  compute: () => Promise<void>;
  refresh: () => Promise<void>;
}

export function useStability(aeroplaneId: string | null): UseStabilityReturn {
  const [data, setData] = useState<StabilityData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isComputing, setIsComputing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!aeroplaneId) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/aeroplanes/${aeroplaneId}/stability`);
      if (res.status === 404) {
        setData(null);
        return;
      }
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`Failed to fetch stability: ${res.status} ${body}`);
      }
      const json = await res.json();
      setData(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  }, [aeroplaneId]);

  const compute = useCallback(async () => {
    if (!aeroplaneId) return;
    setIsComputing(true);
    setError(null);
    try {
      // Use the design CG (cg_x effective from assumptions) as the
      // moment reference point for the stability run. Without this
      // the backend defaults xyz_ref to [0,0,0] and the static margin
      // is computed against an origin CG, not the real design point.
      let cgX = 0;
      try {
        const aRes = await fetch(`${API_BASE}/aeroplanes/${aeroplaneId}/assumptions`);
        if (aRes.ok) {
          const aBody = await aRes.json();
          const cgRow = aBody.assumptions?.find(
            (a: { parameter_name: string }) => a.parameter_name === "cg_x",
          );
          if (cgRow && typeof cgRow.effective_value === "number") {
            cgX = cgRow.effective_value;
          }
        }
      } catch {
        // Fall through with cgX=0; better than failing the stability run.
      }

      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/stability_summary/aerobuildup`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            velocity: 20,
            alpha: 2,
            beta: 0,
            altitude: 0,
            xyz_ref: [cgX, 0, 0],
          }),
        },
      );
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`Compute failed: ${res.status} ${body}`);
      }
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsComputing(false);
    }
  }, [aeroplaneId, refresh]);

  useEffect(() => {
    if (aeroplaneId) {
      refresh();
    } else {
      setData(null);
    }
  }, [aeroplaneId, refresh]);

  return { data, isLoading, isComputing, error, compute, refresh };
}
