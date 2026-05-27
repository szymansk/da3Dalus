"use client";

import useSWR from "swr";
import { fetcher, API_BASE } from "@/lib/fetcher";

export interface Aeroplane {
  id: string;
  name: string;
  total_mass_kg: number | null;
  created_at: string;
  updated_at: string;
}

interface AeroplanesResponse {
  aeroplanes: Aeroplane[];
}

export function useAeroplanes() {
  const { data, error, isLoading, mutate } = useSWR<AeroplanesResponse>(
    "/aeroplanes",
    fetcher,
  );

  async function createAeroplane(name: string): Promise<{ id: string }> {
    const res = await fetch(
      `${API_BASE}/aeroplanes?name=${encodeURIComponent(name)}`,
      { method: "POST" },
    );
    if (!res.ok) throw new Error(`Failed to create aeroplane: ${res.status}`);
    const created = await res.json();
    mutate();
    return created;
  }

  async function deleteAeroplane(id: string): Promise<void> {
    // gh-751: optimistic update. The pre-fix flow was DELETE → wait
    // for the request to settle → mutate() to revalidate; users saw
    // the deleted row linger in the list until the refetch finished.
    // SWR's optimistic-update contract removes the row from the cache
    // synchronously, runs the DELETE in the background, and reverts
    // on error.
    const filterOut = (current: AeroplanesResponse | undefined): AeroplanesResponse => ({
      aeroplanes: (current?.aeroplanes ?? []).filter((a: Aeroplane) => a.id !== id),
    });
    await mutate(
      async (current: AeroplanesResponse | undefined) => {
        const res = await fetch(`${API_BASE}/aeroplanes/${id}`, {
          method: "DELETE",
        });
        if (!res.ok)
          throw new Error(`Failed to delete aeroplane: ${res.status}`);
        return filterOut(current);
      },
      {
        optimisticData: filterOut,
        rollbackOnError: true,
        revalidate: false,
      },
    );
  }

  return {
    aeroplanes: data?.aeroplanes ?? [],
    error,
    isLoading,
    mutate,
    createAeroplane,
    deleteAeroplane,
  };
}
