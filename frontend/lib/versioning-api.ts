/**
 * API client functions for the aircraft versioning system (gh-907).
 *
 * All functions use the project-standard fetcher / API_BASE so that
 * NEXT_PUBLIC_API_URL is respected and error handling is uniform.
 */

import { API_BASE } from "@/lib/fetcher";
import type {
  BranchOut,
  BranchRequest,
  CompareOut,
  SnapshotRequest,
  TreeOut,
  VersionNode,
} from "@/types/versioning";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`POST ${path} failed: ${res.status} ${res.statusText}: ${text}`);
  }
  return res.json() as Promise<T>;
}

async function postNoBody<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { method: "POST" });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`POST ${path} failed: ${res.status} ${res.statusText}: ${text}`);
  }
  return res.json() as Promise<T>;
}

async function deleteReq(path: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, { method: "DELETE" });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`DELETE ${path} failed: ${res.status} ${res.statusText}: ${text}`);
  }
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`GET ${path} failed: ${res.status} ${res.statusText}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// API client functions
// ---------------------------------------------------------------------------

/**
 * POST /aeroplanes/{id}/snapshot
 * Create an immutable snapshot of the current head.
 */
export async function snapshot(
  aeroplaneId: number,
  body: SnapshotRequest,
): Promise<VersionNode> {
  return postJson<VersionNode>(`/aeroplanes/${aeroplaneId}/snapshot`, body);
}

/**
 * POST /aeroplanes/{nodeId}/branch
 * Fork a new editable branch from a specific node (mutable head or snapshot).
 */
export async function createBranch(
  nodeId: number,
  body: BranchRequest,
): Promise<BranchOut> {
  return postJson<BranchOut>(`/aeroplanes/${nodeId}/branch`, body);
}

/**
 * POST /branches/{id}/adopt
 * Promote a branch to is_main=true. The backend takes no request body.
 */
export async function adoptBranch(branchId: number): Promise<BranchOut> {
  return postNoBody<BranchOut>(`/branches/${branchId}/adopt`);
}

/**
 * POST /aeroplanes/{snapshot_id}/restore
 * Fork an editable branch from an immutable snapshot.
 */
export async function restore(
  snapshotId: number,
  body: BranchRequest,
): Promise<BranchOut> {
  return postJson<BranchOut>(`/aeroplanes/${snapshotId}/restore`, body);
}

/**
 * DELETE /branches/{id}
 * Discard a branch and all of its exclusively-owned aeroplane nodes.
 */
export async function discardBranch(branchId: number): Promise<void> {
  return deleteReq(`/branches/${branchId}`);
}

/**
 * GET /lineages/{root_id}/tree
 * Return the full version lineage graph.
 */
export async function getLineageTree(rootId: number): Promise<TreeOut> {
  return getJson<TreeOut>(`/lineages/${rootId}/tree`);
}

/**
 * GET /aeroplanes/compare?a={a}&b={b}
 * Return the metrics payloads for two aeroplane nodes side by side.
 */
export async function compareNodes(a: number, b: number): Promise<CompareOut> {
  return getJson<CompareOut>(`/aeroplanes/compare?a=${a}&b=${b}`);
}

/**
 * PATCH /branches/{id}
 * Rename a branch. Returns the updated BranchOut.
 * 404 — unknown branch; 409 — duplicate name in lineage; 422 — empty name.
 */
export async function renameBranch(
  branchId: number,
  name: string,
): Promise<BranchOut> {
  const res = await fetch(`${API_BASE}/branches/${branchId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`PATCH /branches/${branchId} failed: ${res.status} ${res.statusText}: ${text}`);
  }
  return res.json() as Promise<BranchOut>;
}
