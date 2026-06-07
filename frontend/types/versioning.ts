/**
 * TypeScript types mirroring the backend versioning schemas (gh-907).
 *
 * Source: app/schemas/versioning.py
 */

// ---------------------------------------------------------------------------
// Request bodies
// ---------------------------------------------------------------------------

export interface SnapshotRequest {
  label: string;
  note?: string | null;
  provenance_message_id?: number | null;
}

export interface BranchRequest {
  name: string;
  created_by?: string | null;
}

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

/** A single node in the version lineage graph. Returned by snapshot/restore. */
export interface VersionNode {
  id: number;
  uuid: string;
  name: string;
  branch_id: number | null;
  predecessor_id: number | null;
  root_id: number | null;
  is_immutable: boolean;
  version_label: string | null;
  version_note: string | null;
  created_by: string | null;
  provenance_message_id: number | null;
  /** Base64-encoded PNG thumbnail. Present on detail; omitted from tree listing. */
  preview_png: string | null;
  created_at: string;
  updated_at: string;
}

/** Branch metadata returned by create_branch and adopt_branch. */
export interface BranchOut {
  id: number;
  root_id: number;
  head_id: number;
  name: string;
  is_main: boolean;
  created_by: string | null;
  created_at: string;
}

/** One node in the lineage tree (compact — no preview_png). */
export interface TreeNodeOut {
  id: number;
  uuid: string;
  name: string;
  branch_id: number | null;
  predecessor_id: number | null;
  root_id: number | null;
  is_immutable: boolean;
  /** True if this node is the head of any branch. */
  is_head: boolean;
  version_label: string | null;
  version_note: string | null;
  created_by: string | null;
  created_at: string;
}

/** Version lineage graph for a root aeroplane. */
export interface TreeOut {
  root_id: number;
  nodes: TreeNodeOut[];
  branches: BranchOut[];
}

/** Side-by-side metrics payload for two aeroplane nodes. */
export interface CompareOut {
  node_a: VersionNode;
  node_b: VersionNode;
  metrics_a: Record<string, unknown> | null;
  metrics_b: Record<string, unknown> | null;
}
