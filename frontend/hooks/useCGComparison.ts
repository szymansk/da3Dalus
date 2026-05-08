"use client";

import useSWR from "swr";
import { useCallback } from "react";
import { API_BASE, fetcher } from "@/lib/fetcher";

export interface CGComparison {
  design_cg_x: number;
  component_cg_x: number | null;
  component_cg_y: number | null;
  component_cg_z: number | null;
  component_total_mass_kg: number | null;
  delta_x: number | null;
  within_tolerance: boolean | null;
}

export function useCGComparison(aeroplaneId: string | null) {
  const path = aeroplaneId
    ? `/aeroplanes/${aeroplaneId}/cg_comparison`
    : null;
  const { data, error, isLoading, mutate } = useSWR<CGComparison>(
    path,
    fetcher,
  );

  const syncDesignCG = useCallback(
    async (componentCgX: number) => {
      if (!aeroplaneId) return;
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/assumptions/cg_x`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ estimate_value: componentCgX }),
        },
      );
      if (!res.ok) {
        const body = await res.text().catch(() => "");
        throw new Error(`Failed to sync CG: ${res.status} ${body}`);
      }
      mutate();
    },
    [aeroplaneId, mutate],
  );

  return {
    data: data ?? null,
    isLoading,
    error: error ?? null,
    syncDesignCG,
    mutate,
  };
}
