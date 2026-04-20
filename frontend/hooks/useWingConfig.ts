"use client";

import useSWR from "swr";
import { fetcher, API_BASE } from "@/lib/fetcher";

export interface WingConfigSegment {
  root_airfoil: {
    airfoil: string;
    chord: number;
    dihedral_as_rotation_in_degrees?: number;
    incidence?: number;
    rotation_point_rel_chord?: number;
  };
  tip_airfoil: {
    airfoil: string;
    chord: number;
    dihedral_as_rotation_in_degrees?: number;
    incidence?: number;
    rotation_point_rel_chord?: number;
  };
  length: number;
  sweep: number;
  number_interpolation_points?: number;
  tip_type?: string;
  spare_list?: unknown[];
  trailing_edge_device?: Record<string, unknown> | null;
}

export interface WingConfig {
  segments: WingConfigSegment[];
  nose_pnt: number[];
  symmetric?: boolean;
  parameters?: string;
}

export function useWingConfig(aeroplaneId: string | null, wingName: string | null) {
  const { data, error, isLoading, mutate } = useSWR<WingConfig>(
    aeroplaneId && wingName
      ? `/aeroplanes/${aeroplaneId}/wings/${wingName}/wingconfig`
      : null,
    fetcher,
  );

  async function saveWingConfig(config: WingConfig): Promise<void> {
    if (!aeroplaneId || !wingName) return;
    const res = await fetch(
      `${API_BASE}/aeroplanes/${aeroplaneId}/wings/${wingName}/wingconfig`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      },
    );
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Save wingconfig failed: ${res.status} ${body}`);
    }
    mutate();
  }

  return {
    wingConfig: data ?? null,
    error,
    isLoading,
    mutate,
    saveWingConfig,
  };
}
