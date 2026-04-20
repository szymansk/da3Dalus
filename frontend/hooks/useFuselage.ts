"use client";

import useSWR from "swr";
import { fetcher, API_BASE } from "@/lib/fetcher";

export interface FuselageXSec {
  xyz: number[];
  a: number;
  b: number;
  n: number;
}

export interface Fuselage {
  name: string;
  x_secs: FuselageXSec[];
}

/**
 * Load full Fuselage data for ALL fuselage names in parallel.
 */
export function useAllFuselageData(aeroplaneId: string | null, fuselageNames: string[]) {
  const key = aeroplaneId && fuselageNames.length > 0
    ? `all-fuselages:${aeroplaneId}:${fuselageNames.join(",")}`
    : null;

  const { data, error, isLoading, mutate } = useSWR<Fuselage[]>(
    key,
    async () => {
      const results = await Promise.all(
        fuselageNames.map(async (name) => {
          const res = await fetch(
            `${API_BASE}/aeroplanes/${aeroplaneId}/fuselages/${encodeURIComponent(name)}`,
          );
          if (!res.ok) return null;
          return res.json() as Promise<Fuselage>;
        }),
      );
      return results.filter((f): f is Fuselage => f !== null);
    },
  );

  return { fuselages: data ?? [], error, isLoading, mutate };
}

export function useFuselage(aeroplaneId: string | null, fuselageName: string | null) {
  const { data, error, isLoading, mutate } = useSWR<Fuselage>(
    aeroplaneId && fuselageName
      ? `/aeroplanes/${aeroplaneId}/fuselages/${encodeURIComponent(fuselageName)}`
      : null,
    fetcher,
  );

  async function updateXSec(index: number, xsec: FuselageXSec): Promise<void> {
    if (!aeroplaneId || !fuselageName) return;
    const res = await fetch(
      `${API_BASE}/aeroplanes/${aeroplaneId}/fuselages/${encodeURIComponent(fuselageName)}/cross_sections/${index}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(xsec),
      },
    );
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Update xsec failed: ${res.status} ${body}`);
    }
    mutate();
  }

  return {
    fuselage: data ?? null,
    error,
    isLoading,
    mutate,
    updateXSec,
  };
}
