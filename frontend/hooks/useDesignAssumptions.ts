"use client";

import useSWR, { mutate as globalMutate } from "swr";
import { useCallback, useState } from "react";
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
  const [isRecomputing, setIsRecomputing] = useState(false);

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

      // Recompute-triggering parameters re-derive cl_max/cd0/cg_x and
      // V_stall via the backend debounced job. Recompute time varies
      // wildly (debounce 2s + ASB sweep — anything from 3s to 15s
      // depending on geometry complexity). Poll a few times to catch
      // whenever it settles, and surface an isRecomputing flag so the UI
      // can show a spinner.
      // Must mirror app/services/invalidation_service._RECOMPUTE_TRIGGERING_PARAMS.
      const RECOMPUTE_TRIGGERS = new Set(["target_static_margin", "mass"]);
      if (RECOMPUTE_TRIGGERS.has(paramName)) {
        setIsRecomputing(true);
        const ctxPath = `/aeroplanes/${aeroplaneId}/assumptions/computation-context`;
        const revalidate = () => {
          mutate();
          globalMutate(ctxPath);
        };
        // Idempotent revalidations at staggered intervals — covers
        // recompute times anywhere from 3s to 12s. Cleanup is not needed:
        // mutate() / globalMutate() are idempotent if the component
        // unmounts in the meantime.
        setTimeout(revalidate, 2500);
        setTimeout(revalidate, 5000);
        setTimeout(revalidate, 8000);
        setTimeout(() => {
          revalidate();
          setIsRecomputing(false);
        }, 12000);
      }
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
    isRecomputing,
    error: error ?? null,
    seedDefaults,
    updateEstimate,
    switchSource,
    mutate,
  };
}
