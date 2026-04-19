"use client";

import useSWR from "swr";
import { fetcher, API_BASE } from "@/lib/fetcher";

export interface PlanSummary {
  id: number;
  name: string;
  description: string | null;
  step_count: number;
  plan_type: string;
  aeroplane_id: string | null;
  created_at: string;
}

export interface PlanRead {
  id: number;
  name: string;
  description: string | null;
  tree_json: Record<string, unknown>;
  plan_type: string;
  aeroplane_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExecutionResult {
  status: "success" | "error";
  shape_keys: string[];
  export_paths: string[];
  error: string | null;
  duration_ms: number;
  tessellation: Record<string, unknown> | null;
}

export function useConstructionPlans(planType?: string) {
  const path = planType
    ? `/construction-plans?plan_type=${planType}`
    : "/construction-plans";
  const { data, error, isLoading, mutate } = useSWR<PlanSummary[]>(
    path,
    fetcher,
  );

  return {
    plans: data ?? [],
    error,
    isLoading,
    mutate,
  };
}

export function useAeroplanePlans(aeroplaneId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<PlanSummary[]>(
    aeroplaneId ? `/aeroplanes/${aeroplaneId}/construction-plans` : null,
    fetcher,
  );
  return { plans: data ?? [], error, isLoading, mutate };
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
  body: { name: string; description?: string; tree_json: Record<string, unknown>; plan_type?: string; aeroplane_id?: string },
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
  aeroplaneId: string,
  planId: number,
): Promise<ExecutionResult> {
  const res = await fetch(`${API_BASE}/aeroplanes/${aeroplaneId}/construction-plans/${planId}/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Execute plan failed: ${res.status} ${detail}`);
  }
  return res.json();
}

export async function instantiateTemplate(
  aeroplaneId: string,
  templateId: number,
  name?: string,
): Promise<PlanRead> {
  const res = await fetch(
    `${API_BASE}/aeroplanes/${aeroplaneId}/construction-plans/from-template/${templateId}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: name ? JSON.stringify({ name }) : "{}",
    },
  );
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Instantiate failed: ${res.status} ${detail}`);
  }
  return res.json();
}

export async function toTemplate(
  aeroplaneId: string,
  planId: number,
  name?: string,
): Promise<PlanRead> {
  const res = await fetch(
    `${API_BASE}/aeroplanes/${aeroplaneId}/construction-plans/${planId}/to-template`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: name ? JSON.stringify({ name }) : "{}",
    },
  );
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`To template failed: ${res.status} ${detail}`);
  }
  return res.json();
}
