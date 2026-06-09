"use client";

/**
 * useCopilotProposal (gh-939)
 *
 * Detects a pending "copilot proposal" branch for the current aeroplane:
 * a branch in the lineage tree with `created_by === "copilot"` and
 * `is_main === false`.
 *
 * Reuses `useLineageTree` and `useVersionActions` from the shipped #907
 * versioning hooks — no new API endpoints.
 *
 * The hook is disabled (returns null) when:
 * - no aeroplane is selected
 * - the lineage tree is not yet available (legacy pre-versioning aeroplane)
 * - no copilot branch exists in the tree
 */

import { useMemo } from "react";
import { useAeroplanes } from "@/hooks/useAeroplanes";
import { useLineageTree, useVersionActions } from "@/hooks/useVersioning";
import type { BranchOut } from "@/types/versioning";

// ---------------------------------------------------------------------------
// Return type
// ---------------------------------------------------------------------------

export interface CopilotProposal {
  /** The copilot branch. */
  branch: BranchOut;
  /** Adopt the proposal (promotes it to is_main). */
  adopt: () => Promise<void>;
  /** Discard the proposal (deletes the branch). */
  discard: () => Promise<void>;
  /** True while an adopt/discard action is in flight. */
  busy: boolean;
}

export interface UseCopilotProposalResult {
  /** Non-null when a pending copilot proposal branch exists. */
  proposal: CopilotProposal | null;
  /** True while the lineage tree is loading. */
  isLoading: boolean;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * @param aeroplaneId  UUID string from AeroplaneContext (or null).
 * @param onAdoptComplete  Optional callback fired after a successful adopt.
 * @param onDiscardComplete  Optional callback fired after a successful discard.
 */
export function useCopilotProposal(
  aeroplaneId: string | null,
  onAdoptComplete?: () => void,
  onDiscardComplete?: () => void,
): UseCopilotProposalResult {
  const { aeroplanes } = useAeroplanes();

  // Resolve the current aeroplane's integer root_id from the aeroplanes list.
  const currentAeroplane = useMemo(
    () => aeroplanes.find((a) => a.id === aeroplaneId) ?? null,
    [aeroplanes, aeroplaneId],
  );

  const intId = currentAeroplane?.int_id ?? null;
  const rootId = currentAeroplane?.root_id ?? null;

  const { tree, isLoading } = useLineageTree(rootId);

  // Find the first non-main branch created by "copilot".
  const proposalBranch = useMemo<BranchOut | null>(() => {
    if (!tree) return null;
    return (
      tree.branches.find(
        (b) => b.created_by === "copilot" && !b.is_main,
      ) ?? null
    );
  }, [tree]);

  // Version actions (adopt/discard) — revalidates tree + aeroplanes list.
  const actions = useVersionActions(intId, rootId);

  // Stable proposal object — only changes when the branch identity changes.
  const proposal = useMemo<CopilotProposal | null>(() => {
    if (!proposalBranch) return null;

    const branchId = proposalBranch.id;

    return {
      branch: proposalBranch,
      busy: false, // caller can track busy locally; actions throw on error
      adopt: async () => {
        await actions.adoptBranch(branchId);
        onAdoptComplete?.();
      },
      discard: async () => {
        await actions.discardBranch(branchId);
        onDiscardComplete?.();
      },
    };
  }, [proposalBranch, actions, onAdoptComplete, onDiscardComplete]);

  if (!aeroplaneId) {
    return { proposal: null, isLoading: false };
  }

  return { proposal, isLoading };
}
