"use client";

import useSWR from "swr";
import { fetcher, API_BASE } from "@/lib/fetcher";

export interface Component {
  id: number;
  name: string;
  component_type: string;
  manufacturer: string | null;
  description: string | null;
  mass_g: number | null;
  bbox_x_mm: number | null;
  bbox_y_mm: number | null;
  bbox_z_mm: number | null;
  model_ref: string | null;
  specs: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

interface ComponentList {
  items: Component[];
  total: number;
}

export function useComponents(componentType?: string, search?: string) {
  const params = new URLSearchParams();
  if (componentType) params.set("component_type", componentType);
  if (search) params.set("q", search);
  const query = params.toString();
  const url = `/components${query ? `?${query}` : ""}`;

  const { data, error, isLoading, mutate } = useSWR<ComponentList>(url, fetcher);

  return {
    components: data?.items ?? [],
    total: data?.total ?? 0,
    error,
    isLoading,
    mutate,
  };
}

export function useComponentTypes() {
  const { data } = useSWR<{ types: string[] }>("/components/types", fetcher);
  return data?.types ?? [];
}

export async function createComponent(comp: Omit<Component, "id" | "created_at" | "updated_at">): Promise<Component> {
  const res = await fetch(`${API_BASE}/components`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(comp),
  });
  if (!res.ok) throw new Error(`Create failed: ${res.status}`);
  return res.json();
}

export async function updateComponent(id: number, comp: Omit<Component, "id" | "created_at" | "updated_at">): Promise<Component> {
  const res = await fetch(`${API_BASE}/components/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(comp),
  });
  if (!res.ok) throw new Error(`Update failed: ${res.status}`);
  return res.json();
}

export async function deleteComponent(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/components/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
}
