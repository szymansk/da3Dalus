"use client";

import { useState, useCallback } from "react";
import { API_BASE } from "@/lib/fetcher";

export interface AlphaSweepParams {
  analysis_tool: string;
  velocity_m_s: number;
  alpha_start_deg: number;
  alpha_end_deg: number;
  alpha_step_deg: number;
  beta_deg: number;
  xyz_ref_m: number[];
}

export interface AnalysisResult {
  CL: number[];
  CD: number[];
  Cm: number[];
  alpha: number[];
  [key: string]: unknown;
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
  isRunning: boolean;
  error: string | null;
  lastRunTime: Date | null;
  lastRunDurationMs: number | null;
  runAlphaSweep: (params: AlphaSweepParams) => Promise<void>;
}

export function useAnalysis(aeroplaneId: string | null): UseAnalysisReturn {
  const [result, setResult] = useState<AnalysisResult | null>(null);
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

  return { result, isRunning, error, lastRunTime, lastRunDurationMs, runAlphaSweep };
}
