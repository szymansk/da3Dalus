"use client";

import useSWR from "swr";
import { fetcher, API_BASE } from "@/lib/fetcher";

export interface ConstructionPart {
  id: number;
  aeroplane_id: string;
  name: string;
  volume_mm3: number | null;
  area_mm2: number | null;
  bbox_x_mm: number | null;
  bbox_y_mm: number | null;
  bbox_z_mm: number | null;
  material_component_id: number | null;
  locked: boolean;
  thumbnail_url: string | null;
  file_path: string | null;
  file_format: string | null;
  created_at: string;
  updated_at: string;
}

interface ConstructionPartList {
  aeroplane_id: string;
  items: ConstructionPart[];
  total: number;
}

export function useConstructionParts(aeroplaneId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<ConstructionPartList>(
    aeroplaneId ? `/aeroplanes/${aeroplaneId}/construction-parts` : null,
    fetcher,
  );
  return {
    parts: data?.items ?? [],
    total: data?.total ?? 0,
    error,
    isLoading,
    mutate,
  };
}

export async function uploadConstructionPart(
  aeroplaneId: string,
  formData: FormData,
): Promise<ConstructionPart> {
  const res = await fetch(`${API_BASE}/aeroplanes/${aeroplaneId}/construction-parts`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Upload failed: ${res.status} ${detail}`);
  }
  return res.json();
}

export async function deleteConstructionPart(
  aeroplaneId: string,
  partId: number,
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/aeroplanes/${aeroplaneId}/construction-parts/${partId}`,
    { method: "DELETE" },
  );
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Delete failed: ${res.status} ${detail}`);
  }
}

export async function updateConstructionPart(
  aeroplaneId: string,
  partId: number,
  body: { name?: string; material_component_id?: number | null; thumbnail_url?: string | null },
): Promise<ConstructionPart> {
  const res = await fetch(
    `${API_BASE}/aeroplanes/${aeroplaneId}/construction-parts/${partId}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Update failed: ${res.status} ${detail}`);
  }
  return res.json();
}

export async function lockConstructionPart(
  aeroplaneId: string,
  partId: number,
): Promise<ConstructionPart> {
  const res = await fetch(
    `${API_BASE}/aeroplanes/${aeroplaneId}/construction-parts/${partId}/lock`,
    { method: "PUT" },
  );
  if (!res.ok) throw new Error(`Lock failed: ${res.status}`);
  return res.json();
}

export async function unlockConstructionPart(
  aeroplaneId: string,
  partId: number,
): Promise<ConstructionPart> {
  const res = await fetch(
    `${API_BASE}/aeroplanes/${aeroplaneId}/construction-parts/${partId}/unlock`,
    { method: "PUT" },
  );
  if (!res.ok) throw new Error(`Unlock failed: ${res.status}`);
  return res.json();
}
