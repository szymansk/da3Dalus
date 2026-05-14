"use client";

import { useState, useCallback, useEffect } from "react";
import { API_BASE } from "@/lib/fetcher";

export interface VnPoint {
  velocity_mps: number;
  load_factor: number;
}

export interface GustCriticalWarning {
  velocity_mps: number;
  /** Peak gust load factor (1 + Δn) at this speed */
  n_gust: number;
  /** Maneuver g-limit the gust load exceeds */
  g_limit: number;
  message: string;
}

/** Warning emitted when μ_g is outside the Pratt-Walker validity range [3, 200] (gh-497). */
export interface GustValidityWarning {
  mu_g_value: number;
  validity_min: number;
  validity_max: number;
  message: string;
}

/** Discriminated union of all gust warning types */
export type AnyGustWarning = GustCriticalWarning | GustValidityWarning;

/** Type guard: check if a warning is a GustValidityWarning */
export function isGustValidityWarning(
  w: AnyGustWarning,
): w is GustValidityWarning {
  return "mu_g_value" in w;
}

/** Type guard: check if a warning is a GustCriticalWarning */
export function isGustCriticalWarning(
  w: AnyGustWarning,
): w is GustCriticalWarning {
  return "velocity_mps" in w && "n_gust" in w;
}

export interface VnCurve {
  positive: VnPoint[];
  negative: VnPoint[];
  dive_speed_mps: number;
  stall_speed_mps: number;
  /** Positive gust load-factor line (1 + Δn) — Pratt-Walker, CS-VLA.333. Optional: matches backend's default_factory=list */
  gust_lines_positive?: VnPoint[];
  /** Negative gust load-factor line (1 − Δn). Optional: matches backend's default_factory=list */
  gust_lines_negative?: VnPoint[];
  /** Gust warnings: GustCriticalWarning and/or GustValidityWarning (gh-487, gh-497). Optional: matches backend's default_factory=list */
  gust_warnings?: AnyGustWarning[];
}

export interface PerformanceKPI {
  label: string;
  display_name: string;
  value: number;
  unit: string;
  source_op_id: number | null;
  /**
   * - `trimmed`: from a TRIMMED operating point
   * - `computed`: polar/physics-derived from cached assumptions (gh-475)
   * - `estimated`: heuristic shortcut (e.g. 1.4·V_s)
   * - `limit`: boundary or user-supplied limit
   */
  confidence: "trimmed" | "computed" | "estimated" | "limit";
}

export interface VnMarker {
  op_id: number;
  name: string;
  velocity_mps: number;
  load_factor: number;
  status: string;
  label: string;
}

export interface FlightEnvelopeData {
  id: number;
  aeroplane_id: number;
  vn_curve: VnCurve;
  kpis: PerformanceKPI[];
  operating_points: VnMarker[];
  assumptions_snapshot: Record<string, number>;
  computed_at: string;
  /** Top-level gust warnings (mirrors vn_curve.gust_warnings): includes GustCriticalWarning and/or GustValidityWarning */
  gust_warnings: AnyGustWarning[];
}

export interface UseFlightEnvelopeReturn {
  data: FlightEnvelopeData | null;
  isLoading: boolean;
  isComputing: boolean;
  error: string | null;
  compute: () => Promise<void>;
  refresh: () => Promise<void>;
}

export function useFlightEnvelope(
  aeroplaneId: string | null,
): UseFlightEnvelopeReturn {
  const [data, setData] = useState<FlightEnvelopeData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isComputing, setIsComputing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!aeroplaneId) return;
    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/flight-envelope`,
      );
      if (res.status === 404) {
        setData(null);
        return;
      }
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`Failed to fetch envelope: ${res.status} ${body}`);
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
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/flight-envelope/compute`,
        { method: "POST" },
      );
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`Compute failed: ${res.status} ${body}`);
      }
      const json = await res.json();
      setData(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsComputing(false);
    }
  }, [aeroplaneId]);

  useEffect(() => {
    if (aeroplaneId) {
      refresh();
    } else {
      setData(null);
    }
  }, [aeroplaneId, refresh]);

  return { data, isLoading, isComputing, error, compute, refresh };
}
