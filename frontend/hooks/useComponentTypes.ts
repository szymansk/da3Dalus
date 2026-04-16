"use client";

import useSWR from "swr";
import { fetcher, API_BASE } from "@/lib/fetcher";

export type PropertyType = "number" | "string" | "boolean" | "enum";

export interface PropertyDefinition {
  name: string;
  label: string;
  type: PropertyType;
  unit?: string | null;
  required?: boolean;
  description?: string | null;
  min?: number | null;
  max?: number | null;
  options?: string[] | null;
  default?: unknown;
}

export interface ComponentType {
  id: number;
  name: string;
  label: string;
  description: string | null;
  schema: PropertyDefinition[];
  deletable: boolean;
  reference_count: number;
  created_at: string;
  updated_at: string;
}

export function useComponentTypes() {
  const { data, error, isLoading, mutate } = useSWR<ComponentType[]>(
    "/component-types",
    fetcher,
  );
  return {
    types: data ?? [],
    isLoading,
    error,
    mutate,
  };
}

export async function createComponentType(
  body: Omit<ComponentType, "id" | "deletable" | "reference_count" | "created_at" | "updated_at">,
): Promise<ComponentType> {
  const res = await fetch(`${API_BASE}/component-types`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Create type failed: ${res.status} ${detail}`);
  }
  return res.json();
}

export async function updateComponentType(
  id: number,
  body: Omit<ComponentType, "id" | "deletable" | "reference_count" | "created_at" | "updated_at">,
): Promise<ComponentType> {
  const res = await fetch(`${API_BASE}/component-types/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Update type failed: ${res.status} ${detail}`);
  }
  return res.json();
}

export async function deleteComponentType(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/component-types/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Delete type failed: ${res.status} ${detail}`);
  }
}
