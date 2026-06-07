"use client";

/**
 * SWR hooks for the aircraft versioning system (gh-907).
 *
 * - useLineageTree(rootId)   — GET /lineages/{rootId}/tree, with mutate
 * - useVersionActions(aeroplaneId) — mutations: snapshot/branch/adopt/restore/discard
 *   Each mutation revalidates the lineage tree and the aeroplanes list.
 */

import { useCallback } from "react";
import useSWR, { useSWRConfig } from "swr";
import { fetcher } from "@/lib/fetcher";
import * as api from "@/lib/versioning-api";
import type { BranchOut, BranchRequest, CompareOut, SnapshotRequest, TreeOut, VersionNode } from "@/types/versioning";

// ---------------------------------------------------------------------------
// useLineageTree
// ---------------------------------------------------------------------------

export interface UseLineageTreeResult {
  tree: TreeOut | undefined;
  isLoading: boolean;
  error: Error | undefined;
  mutate: () => Promise<TreeOut | undefined>;
}

/**
 * Fetch and subscribe to the full version lineage graph for a root aeroplane.
 *
 * Pass `rootId=null` to disable (e.g. while the root ID is being resolved).
 */
export function useLineageTree(rootId: number | null): UseLineageTreeResult {
  const path = rootId !== null ? `/lineages/${rootId}/tree` : null;

  const { data, error, isLoading, mutate } = useSWR<TreeOut>(path, fetcher);

  return {
    tree: data,
    isLoading,
    error: error as Error | undefined,
    mutate: mutate as () => Promise<TreeOut | undefined>,
  };
}

// ---------------------------------------------------------------------------
// useVersionActions
// ---------------------------------------------------------------------------

export interface UseVersionActionsResult {
  /**
   * Create an immutable snapshot of the current head.
   * Revalidates the lineage tree and the aeroplanes list.
   */
  snapshot: (body: SnapshotRequest) => Promise<VersionNode>;

  /**
   * Fork a new editable branch from the current aeroplane node.
   * Revalidates the lineage tree and the aeroplanes list.
   */
  createBranch: (body: BranchRequest) => Promise<BranchOut>;

  /**
   * Promote a branch to is_main=true.
   * Revalidates the lineage tree and the aeroplanes list.
   */
  adoptBranch: (branchId: number) => Promise<BranchOut>;

  /**
   * Fork an editable branch from an immutable snapshot (rollback).
   * Revalidates the lineage tree and the aeroplanes list.
   */
  restore: (snapshotId: number, body: BranchRequest) => Promise<BranchOut>;

  /**
   * Discard a branch and all of its exclusively-owned aeroplane nodes.
   * Revalidates the lineage tree and the aeroplanes list.
   */
  discardBranch: (branchId: number) => Promise<void>;
}

/**
 * Expose all versioning mutations for the given aeroplane.
 *
 * Each mutation automatically revalidates:
 * - `/lineages/<rootId>/tree` — to keep the history panel in sync
 * - `/aeroplanes`             — because branch heads appear in the picker
 *
 * The root ID needed to revalidate the tree is derived from the lineage tree
 * response (tree.root_id).  While the tree is not yet loaded, tree-key
 * revalidation is a no-op (mutate of a null key is safe in SWR).
 *
 * `aeroplaneId` is the integer PK of the **current head node** being edited.
 * Pass `null` when the ID is not yet known.
 */
export function useVersionActions(
  aeroplaneId: number | null,
  rootId: number | null = null,
): UseVersionActionsResult {
  const { mutate: globalMutate } = useSWRConfig();

  /** Invalidate both the tree and the aeroplanes list after every mutation. */
  const revalidateAll = useCallback(async () => {
    const treeKey = rootId !== null ? `/lineages/${rootId}/tree` : null;
    await Promise.all([
      globalMutate("/aeroplanes"),
      ...(treeKey ? [globalMutate(treeKey)] : []),
    ]);
  }, [globalMutate, rootId]);

  const snapshotAction = useCallback(
    async (body: SnapshotRequest): Promise<VersionNode> => {
      if (aeroplaneId === null) throw new Error("aeroplaneId is required");
      const node = await api.snapshot(aeroplaneId, body);
      await revalidateAll();
      return node;
    },
    [aeroplaneId, revalidateAll],
  );

  const createBranchAction = useCallback(
    async (body: BranchRequest): Promise<BranchOut> => {
      if (aeroplaneId === null) throw new Error("aeroplaneId is required");
      const branch = await api.createBranch(aeroplaneId, body);
      await revalidateAll();
      return branch;
    },
    [aeroplaneId, revalidateAll],
  );

  const adoptBranchAction = useCallback(
    async (branchId: number): Promise<BranchOut> => {
      const branch = await api.adoptBranch(branchId);
      await revalidateAll();
      return branch;
    },
    [revalidateAll],
  );

  const restoreAction = useCallback(
    async (snapshotId: number, body: BranchRequest): Promise<BranchOut> => {
      const branch = await api.restore(snapshotId, body);
      await revalidateAll();
      return branch;
    },
    [revalidateAll],
  );

  const discardBranchAction = useCallback(
    async (branchId: number): Promise<void> => {
      await api.discardBranch(branchId);
      await revalidateAll();
    },
    [revalidateAll],
  );

  return {
    snapshot: snapshotAction,
    createBranch: createBranchAction,
    adoptBranch: adoptBranchAction,
    restore: restoreAction,
    discardBranch: discardBranchAction,
  };
}

// ---------------------------------------------------------------------------
// Re-export types so consumers can import from a single place
// ---------------------------------------------------------------------------
export type { BranchOut, BranchRequest, CompareOut, SnapshotRequest, TreeOut, VersionNode };
