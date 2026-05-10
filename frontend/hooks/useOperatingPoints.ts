"use client";

import { useState, useCallback, useEffect } from "react";
import { API_BASE } from "@/lib/fetcher";
import type { Wing } from "@/hooks/useWings";

export type OperatingPointStatus = "TRIMMED" | "NOT_TRIMMED" | "LIMIT_REACHED" | "DIRTY" | "COMPUTING";

export interface ControlSurface {
  name: string;
  deflection_deg: number;
}

function isValidControlDevice(
  ted: Record<string, unknown> | null | undefined,
): ted is Record<string, unknown> & { name: string } {
  return ted != null && typeof ted === "object" && typeof ted.name === "string";
}

export function extractControlSurfaces(wings: Wing[]): ControlSurface[] {
  const seen = new Map<string, number>();
  const allXSecs = wings.flatMap((w) => w.x_secs);
  for (const xsec of allXSecs) {
    const ted = xsec.trailing_edge_device ?? xsec.control_surface;
    if (!isValidControlDevice(ted)) continue;
    if (seen.has(ted.name)) continue;
    const deflection =
      typeof ted.deflection_deg === "number" ? ted.deflection_deg : 0;
    seen.set(ted.name, deflection);
  }
  return Array.from(seen.entries()).map(([name, deflection_deg]) => ({
    name,
    deflection_deg,
  }));
}

export interface DeflectionReserve {
  deflection_deg: number;
  max_pos_deg: number;
  max_neg_deg: number;
  usage_fraction: number;
}

export interface DesignWarning {
  level: "info" | "warning" | "critical";
  category: string;
  surface: string | null;
  message: string;
}

export interface ControlEffectiveness {
  derivative: number;
  coefficient: string;
  surface: string;
}

export interface StabilityClassification {
  is_statically_stable: boolean;
  is_directionally_stable: boolean;
  is_laterally_stable: boolean;
  static_margin: number | null;
  overall_class: "stable" | "neutral" | "unstable";
}

export interface MixerValues {
  symmetric_offset: number;
  differential_throw: number;
  role: "elevon" | "flaperon" | "ruddervator";
}

export interface TrimEnrichment {
  analysis_goal: string;
  result_summary: string;
  trim_method: string;
  trim_score: number | null;
  trim_residuals: Record<string, number>;
  deflection_reserves: Record<string, DeflectionReserve>;
  design_warnings: DesignWarning[];
  effectiveness: Record<string, ControlEffectiveness>;
  stability_classification: StabilityClassification | null;
  mixer_values: Record<string, MixerValues>;
  aero_coefficients: Record<string, number>;
}

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
  trim_enrichment: TrimEnrichment | null;
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
  updateDeflections: (
    opId: number,
    deflections: Record<string, number> | null,
  ) => Promise<void>;
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
            // Default to replace_existing=true so 'Generate Default OPs'
            // replaces the previous default set instead of appending —
            // prevents duplicate cruise / loiter / max_range rows when the
            // user re-generates after geometry / mass / SM changes.
            body: JSON.stringify({ replace_existing: replaceExisting ?? true }),
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

  const updateDeflections = useCallback(
    async (
      opId: number,
      deflections: Record<string, number> | null,
    ): Promise<void> => {
      setError(null);
      try {
        const res = await fetch(
          `${API_BASE}/operating_points/${opId}/deflections`,
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ control_deflections: deflections }),
          },
        );
        if (!res.ok) {
          const body = await res.text();
          throw new Error(
            `Failed to update deflections: ${res.status} ${body}`,
          );
        }
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    },
    [refresh],
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
    updateDeflections,
  };
}
