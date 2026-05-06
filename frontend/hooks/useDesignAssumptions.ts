"use client";

import useSWR from "swr";
import { useCallback } from "react";
import { API_BASE, fetcher } from "@/lib/fetcher";

export interface Assumption {
  id: number;
  parameter_name:
    | "mass"
    | "cg_x"
    | "target_static_margin"
    | "cd0"
    | "cl_max"
    | "g_limit";
  estimate_value: number;
  calculated_value: number | null;
  calculated_source: string | null;
  active_source: "ESTIMATE" | "CALCULATED";
  effective_value: number;
  divergence_pct: number | null;
  divergence_level: "none" | "info" | "warning" | "alert";
  unit: string;
  is_design_choice: boolean;
  updated_at: string;
}

export interface AssumptionsSummary {
  assumptions: Assumption[];
  warnings_count: number;
}

export function useDesignAssumptions(aeroplaneId: string | null) {
  const path = aeroplaneId
    ? `/aeroplanes/${aeroplaneId}/assumptions`
    : null;
  const { data, error, isLoading, mutate } = useSWR<AssumptionsSummary>(
    path,
    fetcher,
  );

  const seedDefaults = useCallback(async () => {
    if (!aeroplaneId) return;
    const res = await fetch(
      `${API_BASE}/aeroplanes/${aeroplaneId}/assumptions`,
      { method: "POST" },
    );
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(`Failed to seed defaults: ${res.status} ${body}`);
    }
    mutate();
  }, [aeroplaneId, mutate]);

  const updateEstimate = useCallback(
    async (paramName: Assumption["parameter_name"], value: number) => {
      if (!aeroplaneId) return;
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/assumptions/${paramName}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ estimate_value: value }),
        },
      );
      if (!res.ok) {
        const body = await res.text().catch(() => "");
        throw new Error(`Failed to update assumption: ${res.status} ${body}`);
      }
      mutate();
    },
    [aeroplaneId, mutate],
  );

  const switchSource = useCallback(
    async (
      paramName: Assumption["parameter_name"],
      source: "ESTIMATE" | "CALCULATED",
    ) => {
      if (!aeroplaneId) return;
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/assumptions/${paramName}/source`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ active_source: source }),
        },
      );
      if (!res.ok) {
        const body = await res.text().catch(() => "");
        throw new Error(`Failed to switch source: ${res.status} ${body}`);
      }
      mutate();
    },
    [aeroplaneId, mutate],
  );

  return {
    data: data ?? null,
    isLoading,
    error: error ?? null,
    seedDefaults,
    updateEstimate,
    switchSource,
    mutate,
  };
}
