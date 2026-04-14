"use client";

import { useState, useCallback } from "react";
import { API_BASE } from "@/lib/fetcher";

interface StreamlinesState {
  figure: Record<string, unknown> | null;
  isComputing: boolean;
  error: string | null;
}

export interface StreamlinesParams {
  velocity: number;
  alpha: number;
  beta: number;
  altitude: number;
}

export function useStreamlines(aeroplaneId: string | null) {
  const [state, setState] = useState<StreamlinesState>({
    figure: null,
    isComputing: false,
    error: null,
  });

  const computeStreamlines = useCallback(
    async (params: StreamlinesParams) => {
      if (!aeroplaneId) return;
      setState({ figure: null, isComputing: true, error: null });

      try {
        const res = await fetch(
          `${API_BASE}/aeroplanes/${aeroplaneId}/streamlines`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              velocity: params.velocity,
              alpha: params.alpha,
              beta: params.beta,
              altitude: params.altitude,
            }),
          },
        );
        if (!res.ok) {
          const body = await res.text();
          throw new Error(`Streamlines failed: ${res.status} ${body}`);
        }
        const figure = await res.json();
        setState({ figure, isComputing: false, error: null });
      } catch (err) {
        setState({
          figure: null,
          isComputing: false,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    },
    [aeroplaneId],
  );

  return { ...state, computeStreamlines };
}
