"use client";

import { useState, useCallback } from "react";
import { API_BASE } from "@/lib/fetcher";

export interface AlphaSweepParams {
  alpha_start: number;
  alpha_end: number;
  alpha_num: number;
  velocity: number;
  beta: number;
  altitude: number;
  xyz_ref: number[];
  /** Extra masses [kg] for speed-polar comparison curves (base mass always included). */
  masses_kg?: number[];
}

export interface AnalysisResult {
  // Coefficients may contain null where the backend sanitized a non-finite
  // (NaN/Inf) solver value for a degenerate sweep (gh-815). alpha is the swept
  // input, always finite.
  CL: (number | null)[];
  CD: (number | null)[];
  Cm: (number | null)[];
  alpha: number[];
  [key: string]: unknown;
}

export interface SpeedPolarCurve {
  mass_kg: number;
  is_base: boolean;
  V: number[];
  w: number[];
  cl: number[];
  cd: number[];
  v_stall: number | null;
  v_min_sink: number | null;
  w_min: number | null;
  v_best_glide: number | null;
  ld_max: number | null;
}

export interface SpeedPolar {
  base_mass_kg: number;
  s_ref: number;
  rho: number;
  altitude: number;
  curves: SpeedPolarCurve[];
  /** Recommended X-axis lower limit [m/s] = 0.7 × min V_stall over curves */
  v_axis_min?: number | null;
  /** Recommended X-axis upper limit [m/s] = 1.3 × V_dive or max sweep V */
  v_axis_max?: number | null;
}

/**
 * Extract CL/CD/Cm/alpha from the nested API response.
 * API returns: { analysis: { coefficients: { CL, CD, Cm }, flight_condition: { alpha } } }
 */
function extractResult(data: Record<string, unknown>): AnalysisResult {
  const analysis = data.analysis as Record<string, unknown> | undefined;
  const coefficients = analysis?.coefficients as Record<string, number[]> | undefined;
  const flightCondition = analysis?.flight_condition as Record<string, number[]> | undefined;

  return {
    CL: coefficients?.CL ?? [],
    CD: coefficients?.CD ?? [],
    Cm: coefficients?.Cm ?? [],
    alpha: flightCondition?.alpha ?? [],
  };
}

export interface UseAnalysisReturn {
  result: AnalysisResult | null;
  speedPolar: SpeedPolar | null;
  isRunning: boolean;
  error: string | null;
  lastRunTime: Date | null;
  lastRunDurationMs: number | null;
  runAlphaSweep: (params: AlphaSweepParams) => Promise<void>;
}

export function useAnalysis(aeroplaneId: string | null): UseAnalysisReturn {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [speedPolar, setSpeedPolar] = useState<SpeedPolar | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRunTime, setLastRunTime] = useState<Date | null>(null);
  const [lastRunDurationMs, setLastRunDurationMs] = useState<number | null>(null);

  const runAlphaSweep = useCallback(
    async (params: AlphaSweepParams) => {
      if (!aeroplaneId) return;
      setIsRunning(true);
      setError(null);
      const t0 = Date.now();

      try {
        const res = await fetch(
          `${API_BASE}/aeroplanes/${aeroplaneId}/alpha_sweep`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(params),
          },
        );
        if (!res.ok) {
          const body = await res.text();
          throw new Error(`Analysis failed: ${res.status} ${body}`);
        }
        const data = await res.json();
        setResult(extractResult(data));
        setSpeedPolar((data.speed_polar as SpeedPolar | undefined) ?? null);
        setLastRunTime(new Date());
        setLastRunDurationMs(Date.now() - t0);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setIsRunning(false);
      }
    },
    [aeroplaneId],
  );

  return { result, speedPolar, isRunning, error, lastRunTime, lastRunDurationMs, runAlphaSweep };
}
