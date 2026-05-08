"use client";

import { useState, useCallback, useEffect } from "react";
import { API_BASE } from "@/lib/fetcher";

export type OperatingPointStatus = "TRIMMED" | "NOT_TRIMMED" | "LIMIT_REACHED";

export interface StoredOperatingPoint {
  id: number;
  name: string;
  description: string;
  aircraft_id: number | null;
  config: string;
  status: OperatingPointStatus;
  warnings: string[];
  controls: Record<string, number>;
  velocity: number;
  alpha: number;
  beta: number;
  p: number;
  q: number;
  r: number;
  xyz_ref: number[];
  altitude: number;
  control_deflections: Record<string, number> | null;
}

export interface AVLTrimResult {
  converged: boolean;
  trimmed_deflections: Record<string, number>;
  trimmed_state: Record<string, number>;
  aero_coefficients: Record<string, number>;
  forces_and_moments: Record<string, number>;
  stability_derivatives: Record<string, number>;
  raw_results: Record<string, number>;
}

export interface AeroBuildupTrimResult {
  converged: boolean;
  trim_variable: string;
  trimmed_deflection: number;
  target_coefficient: string;
  achieved_value: number | null;
  aero_coefficients: Record<string, number>;
  stability_derivatives: Record<string, number>;
}

export interface TrimConstraint {
  variable: string;
  target: string;
  value: number;
}

export interface UseOperatingPointsReturn {
  points: StoredOperatingPoint[];
  isLoading: boolean;
  isGenerating: boolean;
  isTrimming: boolean;
  error: string | null;
  generate: (replaceExisting?: boolean) => Promise<void>;
  refresh: () => Promise<void>;
  trimWithAvl: (
    point: StoredOperatingPoint,
    constraints: TrimConstraint[],
  ) => Promise<AVLTrimResult | null>;
  trimWithAerobuildup: (
    point: StoredOperatingPoint,
    trimVariable: string,
    targetCoefficient: string,
    targetValue: number,
  ) => Promise<AeroBuildupTrimResult | null>;
}

function toTrimPayload(point: StoredOperatingPoint) {
  return {
    velocity: point.velocity,
    alpha: point.alpha,
    beta: point.beta,
    p: point.p,
    q: point.q,
    r: point.r,
    xyz_ref: point.xyz_ref,
    altitude: point.altitude,
    control_deflections: point.control_deflections,
  };
}

export function useOperatingPoints(
  aeroplaneId: string | null,
): UseOperatingPointsReturn {
  const [points, setPoints] = useState<StoredOperatingPoint[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isTrimming, setIsTrimming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!aeroplaneId) return;
    setIsLoading(true);
    setError(null);
    try {
      const url = new URL(`${API_BASE}/operating_points`);
      url.searchParams.set("aircraft_id", aeroplaneId);
      const res = await fetch(url);
      if (res.status === 404) {
        setPoints([]);
        return;
      }
      if (!res.ok) {
        const body = await res.text();
        throw new Error(
          `Failed to fetch operating points: ${res.status} ${body}`,
        );
      }
      const json = await res.json();
      setPoints(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  }, [aeroplaneId]);

  const generate = useCallback(
    async (replaceExisting?: boolean) => {
      if (!aeroplaneId) return;
      setIsGenerating(true);
      setError(null);
      try {
        const res = await fetch(
          `${API_BASE}/aeroplanes/${encodeURIComponent(aeroplaneId)}/operating-pointsets/generate-default`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ replace_existing: replaceExisting ?? false }),
          },
        );
        if (!res.ok) {
          const body = await res.text();
          throw new Error(`Generate failed: ${res.status} ${body}`);
        }
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setIsGenerating(false);
      }
    },
    [aeroplaneId, refresh],
  );

  const trimWithAvl = useCallback(
    async (
      point: StoredOperatingPoint,
      constraints: TrimConstraint[],
    ): Promise<AVLTrimResult | null> => {
      if (!aeroplaneId) return null;
      setIsTrimming(true);
      setError(null);
      try {
        const res = await fetch(
          `${API_BASE}/aeroplanes/${encodeURIComponent(aeroplaneId)}/operating-points/avl-trim`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              operating_point: toTrimPayload(point),
              trim_constraints: constraints,
            }),
          },
        );
        if (!res.ok) {
          const body = await res.text();
          throw new Error(`AVL trim failed: ${res.status} ${body}`);
        }
        const result: AVLTrimResult = await res.json();
        await refresh();
        return result;
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        return null;
      } finally {
        setIsTrimming(false);
      }
    },
    [aeroplaneId, refresh],
  );

  const trimWithAerobuildup = useCallback(
    async (
      point: StoredOperatingPoint,
      trimVariable: string,
      targetCoefficient: string,
      targetValue: number,
    ): Promise<AeroBuildupTrimResult | null> => {
      if (!aeroplaneId) return null;
      setIsTrimming(true);
      setError(null);
      try {
        const res = await fetch(
          `${API_BASE}/aeroplanes/${encodeURIComponent(aeroplaneId)}/operating-points/aerobuildup-trim`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              operating_point: toTrimPayload(point),
              trim_variable: trimVariable,
              target_coefficient: targetCoefficient,
              target_value: targetValue,
            }),
          },
        );
        if (!res.ok) {
          const body = await res.text();
          throw new Error(`Aerobuildup trim failed: ${res.status} ${body}`);
        }
        const result: AeroBuildupTrimResult = await res.json();
        await refresh();
        return result;
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        return null;
      } finally {
        setIsTrimming(false);
      }
    },
    [aeroplaneId, refresh],
  );

  useEffect(() => {
    if (aeroplaneId) {
      refresh();
    } else {
      setPoints([]);
    }
  }, [aeroplaneId, refresh]);

  return {
    points,
    isLoading,
    isGenerating,
    isTrimming,
    error,
    generate,
    refresh,
    trimWithAvl,
    trimWithAerobuildup,
  };
}
