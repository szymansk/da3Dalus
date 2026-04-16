"use client";

import useSWR from "swr";
import { fetcher, API_BASE } from "@/lib/fetcher";

export interface ComponentTreeNode {
  id: number;
  aeroplane_id: string;
  parent_id: number | null;
  sort_index: number;
  node_type: "group" | "cad_shape" | "cots";
  name: string;
  component_id: number | null;
  quantity: number;
  weight_override_g: number | null;
  synced_from?: string | null;
  children: ComponentTreeNode[];
}

interface ComponentTreeResponse {
  aeroplane_id: string;
  root_nodes: ComponentTreeNode[];
  total_nodes: number;
}

export function useComponentTree(aeroplaneId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<ComponentTreeResponse>(
    aeroplaneId ? `/aeroplanes/${aeroplaneId}/component-tree` : null,
    fetcher,
  );

  return {
    tree: data?.root_nodes ?? [],
    totalNodes: data?.total_nodes ?? 0,
    error,
    isLoading,
    mutate,
  };
}

export async function addTreeNode(
  aeroplaneId: string,
  node: { parent_id?: number | null; node_type: string; name: string; component_id?: number; quantity?: number },
): Promise<ComponentTreeNode> {
  const res = await fetch(`${API_BASE}/aeroplanes/${aeroplaneId}/component-tree`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(node),
  });
  if (!res.ok) throw new Error(`Add node failed: ${res.status}`);
  return res.json();
}

export async function deleteTreeNode(aeroplaneId: string, nodeId: number): Promise<void> {
  const res = await fetch(`${API_BASE}/aeroplanes/${aeroplaneId}/component-tree/${nodeId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Delete failed: ${res.status} ${detail}`);
  }
}

export async function moveTreeNode(
  aeroplaneId: string,
  nodeId: number,
  body: { new_parent_id: number | null; sort_index: number },
): Promise<ComponentTreeNode> {
  const res = await fetch(
    `${API_BASE}/aeroplanes/${aeroplaneId}/component-tree/${nodeId}/move`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Move failed: ${res.status} ${detail}`);
  }
  return res.json();
}
