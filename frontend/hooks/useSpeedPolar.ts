"use client";

import useSWR from "swr";

// ---------------------------------------------------------------------------
// Types — mirror backend SpeedPolarResponse / SpeedPolarPoint schemas (gh-841)
// ---------------------------------------------------------------------------

export interface SpeedPolarPoint {
  /** Airspeed [m/s] */
  v_mps: number;
  /** Sink rate [m/s] (positive = downward) */
  sink_mps: number;
  /** Lift coefficient at this point */
  cl: number;
}

export interface AircraftSpeedPolar {
  /** Airspeed sweep [m/s] — ascending */
  v_mps: number[];
  /** Sink rate [m/s] — positive downward */
  sink_mps: number[];
  /** CL sweep — decreasing (paired with v_mps/sink_mps) */
  cl: number[];
  /** (L/D)_max operating point — origin-tangent to the curve */
  best_glide: SpeedPolarPoint;
  /** Minimum sink rate operating point */
  min_sink: SpeedPolarPoint;
  /** Inputs used to produce this polar (for provenance display) */
  inputs: {
    mass_kg: number;
    s_ref_m2: number;
    ar: number;
    e_oswald: number;
    cd0: number;
    rho: number;
  };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * SWR hook for the aircraft speed polar endpoint (gh-841).
 *
 * Fetches GET /aeroplanes/{aeroplaneId}/speed-polar.
 * Returns null data when the aeroplane has insufficient context (HTTP 422).
 * Callers should render an empty-state when data is null.
 */
export function useSpeedPolar(aeroplaneId: string | null) {
  const url = aeroplaneId
    ? `/aeroplanes/${encodeURIComponent(aeroplaneId)}/speed-polar`
    : null;

  const { data, error, isLoading, mutate } = useSWR<AircraftSpeedPolar | null>(
    url,
    async (path: string) => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001"}${path}`,
      );
      if (res.status === 422) {
        // Insufficient context — not an error, just missing inputs
        return null;
      }
      if (!res.ok) {
        const body = await res.text().catch(() => "");
        throw new Error(`${res.status}: ${body}`);
      }
      return res.json() as Promise<AircraftSpeedPolar>;
    },
    { revalidateOnFocus: false },
  );

  return { data: data ?? null, error, isLoading, mutate };
}
