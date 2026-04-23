"use client";

import { useState, useCallback } from "react";
import { API_BASE } from "@/lib/fetcher";

export interface AirfoilAnalysisResult {
  airfoilName: string;
  alphaDeg: number[];
  cl: (number | null)[];
  cd: (number | null)[];
  cm: (number | null)[];
  clOverCd: (number | null)[];
  clMax: number | null;
  alphaAtClMax: number | null;
  ldMax: number | null;
  alphaAtLdMax: number | null;
}

export function useAirfoilAnalysis() {
  const [result, setResult] = useState<AirfoilAnalysisResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(
    async (airfoilName: string, re: number, ma: number) => {
      setIsRunning(true);
      setError(null);
      try {
        const res = await fetch(
          `${API_BASE}/airfoils/${encodeURIComponent(airfoilName)}/neuralfoil/analysis`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              reynolds_numbers: [re],
              mach: ma,
              alpha_start_deg: -10,
              alpha_end_deg: 16,
              alpha_step_deg: 1,
            }),
          },
        );
        if (!res.ok) throw new Error(`Analysis failed: ${res.status}`);
        const data = await res.json();

        // Extract first Reynolds result
        const rr = data.reynolds_results?.[0];
        if (!rr) throw new Error("No results");

        // Find L/D max
        const clOverCd: (number | null)[] = rr.cl_over_cd ?? [];
        let ldMax: number | null = null;
        let alphaAtLdMax: number | null = null;
        for (let i = 0; i < clOverCd.length; i++) {
          const v = clOverCd[i];
          if (v != null && (ldMax == null || v > ldMax)) {
            ldMax = v;
            alphaAtLdMax = data.alpha_deg?.[i] ?? null;
          }
        }

        setResult({
          airfoilName,
          alphaDeg: data.alpha_deg ?? [],
          cl: rr.cl ?? [],
          cd: rr.cd ?? [],
          cm: rr.cm ?? [],
          clOverCd,
          clMax: rr.cl_max ?? null,
          alphaAtClMax: rr.alpha_at_cl_max_deg ?? null,
          ldMax: ldMax == null ? null : Math.round(ldMax * 10) / 10,
          alphaAtLdMax,
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setIsRunning(false);
      }
    },
    [],
  );

  const clear = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { result, isRunning, error, run, clear };
}
