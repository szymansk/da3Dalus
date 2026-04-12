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
    const res = await fetch(`${API_BASE}/aeroplanes/${id}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error(`Failed to delete aeroplane: ${res.status}`);
    mutate();
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
