"use client";

import useSWR from "swr";
import { fetcher, API_BASE } from "@/lib/fetcher";

// ---------------------------------------------------------------------------
// Types matching backend PowertrainModalParamsResponse (gh-197)
// ---------------------------------------------------------------------------

export interface MotorSuggestion {
  id: number;
  name: string;
  manufacturer: string | null;
  mass_g: number | null;
  efficiency_pct: number;
  kv: number | null;
  max_power_w: number | null;
  description: string | null;
}

export interface PowertrainModalParamsResponse {
  altitude_m: number;
  cd0: number;
  s_ref_m2: number;
  eta_prop: number;
  eta_motor: number;
  motors: MotorSuggestion[];
  warnings: string[];
}

// ---------------------------------------------------------------------------
// Hook: fetch pre-filled modal params
// ---------------------------------------------------------------------------

export function usePowertrainModalParams(aeroplaneId: string | null) {
  const url = aeroplaneId
    ? `/aeroplanes/${encodeURIComponent(aeroplaneId)}/powertrain/sizing-modal-params`
    : null;

  const { data, error, isLoading, mutate } = useSWR<PowertrainModalParamsResponse>(
    url,
    fetcher,
    { revalidateOnFocus: false }
  );

  return { data, error, isLoading, mutate };
}

// ---------------------------------------------------------------------------
// Types for the powertrain sizing POST request/response (gh-490)
// ---------------------------------------------------------------------------

export interface PowertrainSizingRequest {
  airframe_mass_kg: number;
  target_cruise_speed_ms: number;
  target_top_speed_ms: number;
  target_flight_time_min: number;
  altitude_m?: number;
  cd0?: number;
  s_ref_m2?: number;
  eta_prop?: number;
  eta_motor?: number;
  eta_esc?: number;
}

export interface PowertrainCandidate {
  motor_id: number | null;
  motor_name: string | null;
  esc_id: number | null;
  esc_name: string | null;
  battery_id: number | null;
  battery_name: string | null;
  propeller: string | null;
  estimated_flight_time_min: number;
  estimated_cruise_power_w: number;
  estimated_top_speed_ms: number;
  confidence: number;
}

export interface PowertrainSizingResponse {
  recommendations: PowertrainCandidate[];
  warnings: string[];
}

// ---------------------------------------------------------------------------
// Imperative sizing POST (called on "Run" button)
// ---------------------------------------------------------------------------

export async function runPowertrainSizing(
  aeroplaneId: string,
  body: PowertrainSizingRequest
): Promise<PowertrainSizingResponse> {
  const res = await fetch(
    `${API_BASE}/aeroplanes/${encodeURIComponent(aeroplaneId)}/powertrain/sizing`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }
  );
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Powertrain sizing failed: ${res.status} ${res.statusText}: ${text}`);
  }
  return res.json();
}
