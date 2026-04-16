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
  // Extended fields surfaced by the backend — optional because the list
  // response and the property panel both use the same type.
  construction_part_id?: number | null;
  shape_key?: string | null;
  shape_hash?: string | null;
  volume_mm3?: number | null;
  area_mm2?: number | null;
  pos_x?: number;
  pos_y?: number;
  pos_z?: number;
  rot_x?: number;
  rot_y?: number;
  rot_z?: number;
  material_id?: number | null;
  print_type?: string | null;
  scale_factor?: number;
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
  node: {
    parent_id?: number | null;
    node_type: string;
    name: string;
    component_id?: number;
    quantity?: number;
    construction_part_id?: number;
  },
): Promise<ComponentTreeNode> {
  const res = await fetch(`${API_BASE}/aeroplanes/${aeroplaneId}/component-tree`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(node),
  });
  if (!res.ok) throw new Error(`Add node failed: ${res.status}`);
  return res.json();
}

/**
 * Fields accepted by `PUT /component-tree/{id}`. Mirrors the backend's
 * ComponentTreeNodeWrite schema; callers pass the full node shape (the
 * backend overwrites every field on update).
 */
export interface ComponentTreeNodeUpdate {
  parent_id?: number | null;
  sort_index?: number;
  node_type: string;
  name: string;
  shape_key?: string | null;
  shape_hash?: string | null;
  volume_mm3?: number | null;
  area_mm2?: number | null;
  component_id?: number | null;
  quantity?: number;
  construction_part_id?: number | null;
  pos_x?: number;
  pos_y?: number;
  pos_z?: number;
  rot_x?: number;
  rot_y?: number;
  rot_z?: number;
  material_id?: number | null;
  weight_override_g?: number | null;
  print_type?: string | null;
  scale_factor?: number;
}

export async function updateTreeNode(
  aeroplaneId: string,
  nodeId: number,
  body: ComponentTreeNodeUpdate,
): Promise<ComponentTreeNode> {
  const res = await fetch(
    `${API_BASE}/aeroplanes/${aeroplaneId}/component-tree/${nodeId}`,
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
