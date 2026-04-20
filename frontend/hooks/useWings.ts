"use client";

import useSWR from "swr";
import { fetcher, API_BASE } from "@/lib/fetcher";

export interface XSec {
  xyz_le: number[];
  chord: number;
  twist: number;
  airfoil: string;
  x_sec_type?: string;
  tip_type?: string;
  number_interpolation_points?: number;
  spare_list?: unknown[];
  trailing_edge_device?: Record<string, unknown> | null;
  control_surface?: Record<string, unknown> | null;
}

export interface Wing {
  name: string;
  symmetric: boolean;
  x_secs: XSec[];
}

export function useWings(aeroplaneId: string | null) {
  const { data: wingNames, error, isLoading, mutate } = useSWR<string[]>(
    aeroplaneId ? `/aeroplanes/${aeroplaneId}/wings` : null,
    fetcher,
  );

  return {
    wingNames: wingNames ?? [],
    error,
    isLoading,
    mutate,
  };
}

/**
 * Load full Wing data for ALL wing names in parallel.
 * Unlike individual useWing() calls, this scales to any number of wings.
 */
export function useAllWingData(aeroplaneId: string | null, wingNames: string[]) {
  const key = aeroplaneId && wingNames.length > 0
    ? `all-wings:${aeroplaneId}:${wingNames.join(",")}`
    : null;

  const { data, error, isLoading, mutate } = useSWR<Wing[]>(
    key,
    async () => {
      const results = await Promise.all(
        wingNames.map(async (name) => {
          const res = await fetch(
            `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${encodeURIComponent(name)}`,
          );
          if (!res.ok) return null;
          return res.json() as Promise<Wing>;
        }),
      );
      return results.filter((w): w is Wing => w !== null);
    },
  );

  return { wings: data ?? [], error, isLoading, mutate };
}

export function useWing(aeroplaneId: string | null, wingName: string | null) {
  const { data, error, isLoading, mutate } = useSWR<Wing>(
    aeroplaneId && wingName
      ? `/aeroplanes/${aeroplaneId}/wings/${wingName}`
      : null,
    fetcher,
  );

  async function updateXSec(
    xsecIndex: number,
    payload: Partial<XSec>,
  ): Promise<void> {
    if (!aeroplaneId || !wingName) return;
    const res = await fetch(
      `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${wingName}/cross_sections/${xsecIndex}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
    if (!res.ok) throw new Error(`Failed to update x_sec: ${res.status}`);
    mutate();
  }

  return {
    wing: data ?? null,
    error,
    isLoading,
    mutate,
    updateXSec,
  };
}
