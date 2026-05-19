"use client";

import { useState, useCallback } from "react";
import { API_BASE } from "@/lib/fetcher";
import { parseApiError } from "@/lib/parseApiError";

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
  /**
   * Moment-reference point for the run. Defaults to [0,0,0] on the
   * backend if omitted, but callers should pass the design CG so the
   * streamline visualisation is consistent with the rest of the system.
   */
  xyz_ref?: number[];
  /**
   * gh-577: bind the run to a stored, trimmed OperatingPoint. When set
   * the backend resolves alpha (rad→deg), xyz_ref, velocity, altitude,
   * body rates and all control-surface deflections from that record so
   * the Trefftz plane / streamlines reflect a trim-consistent state.
   */
  operating_point_id?: number | null;
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
        const body: Record<string, unknown> = {
          velocity: params.velocity,
          alpha: params.alpha,
          beta: params.beta,
          altitude: params.altitude,
          xyz_ref: params.xyz_ref ?? [0, 0, 0],
        };
        if (params.operating_point_id != null) {
          body.operating_point_id = params.operating_point_id;
        }
        const res = await fetch(
          `${API_BASE}/aeroplanes/${aeroplaneId}/streamlines`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          },
        );
        if (!res.ok) {
          throw new Error(await parseApiError(res, "Streamlines"));
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
