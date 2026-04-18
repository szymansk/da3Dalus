"use client";

import useSWR from "swr";
import { fetcher, API_BASE } from "@/lib/fetcher";

export interface PlanSummary {
  id: number;
  name: string;
  description: string | null;
  step_count: number;
  created_at: string;
}

export interface PlanRead {
  id: number;
  name: string;
  description: string | null;
  tree_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ExecutionResult {
  status: "success" | "error";
  shape_keys: string[];
  export_paths: string[];
  error: string | null;
  duration_ms: number;
}

export function useConstructionPlans() {
  const { data, error, isLoading, mutate } = useSWR<PlanSummary[]>(
    "/construction-plans",
    fetcher,
  );

  return {
    plans: data ?? [],
    error,
    isLoading,
    mutate,
  };
}

export function useConstructionPlan(id: number | null) {
  const { data, error, isLoading, mutate } = useSWR<PlanRead>(
    id != null ? `/construction-plans/${id}` : null,
    fetcher,
  );

  return {
    plan: data ?? null,
    error,
    isLoading,
    mutate,
  };
}

export async function createPlan(
  body: { name: string; description?: string; tree_json: Record<string, unknown> },
): Promise<PlanRead> {
  const res = await fetch(`${API_BASE}/construction-plans`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Create plan failed: ${res.status} ${detail}`);
  }
  return res.json();
}

export async function updatePlan(
  id: number,
  body: { name: string; description?: string; tree_json: Record<string, unknown> },
): Promise<PlanRead> {
  const res = await fetch(`${API_BASE}/construction-plans/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Update plan failed: ${res.status} ${detail}`);
  }
  return res.json();
}

export async function deletePlan(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/construction-plans/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Delete plan failed: ${res.status} ${detail}`);
  }
}

export async function executePlan(
  id: number,
  aeroplaneId: string,
): Promise<ExecutionResult> {
  const res = await fetch(`${API_BASE}/construction-plans/${id}/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ aeroplane_id: aeroplaneId }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Execute plan failed: ${res.status} ${detail}`);
  }
  return res.json();
}
