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
  alpha: number[];
  [key: string]: unknown;
}

/**
 * Extract CL/CD/alpha from the nested API response.
 * API returns: { analysis: { coefficients: { CL, CD }, flight_condition: { alpha } } }
 * We flatten to: { CL, CD, alpha }
 */
function extractResult(data: Record<string, unknown>): AnalysisResult {
  const analysis = data.analysis as Record<string, unknown> | undefined;
  const coefficients = analysis?.coefficients as Record<string, number[]> | undefined;
  const flightCondition = analysis?.flight_condition as Record<string, number[]> | undefined;

  return {
    CL: coefficients?.CL ?? [],
    CD: coefficients?.CD ?? [],
    alpha: flightCondition?.alpha ?? [],
  };
}

export function useAnalysis(aeroplaneId: string | null) {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runAlphaSweep = useCallback(
    async (params: AlphaSweepParams) => {
      if (!aeroplaneId) return;
      setIsRunning(true);
      setError(null);

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
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setIsRunning(false);
      }
    },
    [aeroplaneId],
  );

  return { result, isRunning, error, runAlphaSweep };
}
