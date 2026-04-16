/**
 * Pure helpers for the Component Tree drag-and-drop flow (gh#57-wak).
 *
 * Kept separate from the React component so the cycle-prevention and
 * sort-index math can be exhaustively unit-tested without simulating mouse
 * events. The component layer wires these into @dnd-kit's onDragEnd.
 */
import type { ComponentTreeNode } from "@/hooks/useComponentTree";

export type DropPosition = "before" | "after" | "into";

export interface MoveResult {
  newParentId: number | null;
  sortIndex: number;
}

/** Recursive lookup. Returns null if the ID is not in the tree. */
export function findNode(
  tree: ComponentTreeNode[],
  id: number,
): ComponentTreeNode | null {
  for (const node of tree) {
    if (node.id === id) return node;
    const inside = findNode(node.children, id);
    if (inside) return inside;
  }
  return null;
}

/**
 * True if `candidateId` is anywhere inside the subtree of `ancestorId`.
 * `ancestorId === candidateId` returns false (a node is not its own descendant).
 */
export function isDescendantOf(
  tree: ComponentTreeNode[],
  ancestorId: number,
  candidateId: number,
): boolean {
  const ancestor = findNode(tree, ancestorId);
  if (!ancestor) return false;
  return findNode(ancestor.children, candidateId) !== null;
}

/** Find the immediate parent + the source list a node lives in. */
function locateParent(
  tree: ComponentTreeNode[],
  childId: number,
): { parent: ComponentTreeNode | null; siblings: ComponentTreeNode[] } | null {
  // Root level
  if (tree.some((n) => n.id === childId)) {
    return { parent: null, siblings: tree };
  }
  for (const node of tree) {
    if (node.children.some((c) => c.id === childId)) {
      return { parent: node, siblings: node.children };
    }
    const recursed = locateParent(node.children, childId);
    if (recursed) return recursed;
  }
  return null;
}

/**
 * Translate an active-over-position drop into a backend move payload.
 *
 * Returns `null` when the drop is invalid:
 *   - source equals target
 *   - source is dropped on a descendant (cycle)
 *   - source/target node IDs are unknown
 *   - "into" is requested on a non-group leaf
 *   - the resulting position is identical to the current position (no-op)
 *
 * Sort-index semantics:
 *   - "before X" → X.sortIndex (X and later siblings shift down by 1 server-side)
 *   - "after X"  → X.sortIndex + 1
 *   - "into G"   → end of G.children (length)
 */
export function computeMoveResult(
  tree: ComponentTreeNode[],
  activeId: number,
  overId: number,
  position: DropPosition,
): MoveResult | null {
  if (activeId === overId) return null;

  const active = findNode(tree, activeId);
  const over = findNode(tree, overId);
  if (!active || !over) return null;

  // Cycle prevention: source cannot be moved under one of its descendants.
  if (isDescendantOf(tree, activeId, overId)) return null;

  if (position === "into") {
    if (over.node_type !== "group") return null;
    return { newParentId: over.id, sortIndex: over.children.length };
  }

  // "before" / "after": determine the parent and sort_index relative to over.
  const overParent = locateParent(tree, overId);
  if (!overParent) return null;

  const newParentId = overParent.parent ? overParent.parent.id : null;
  const sortIndex = position === "before" ? over.sort_index : over.sort_index + 1;

  // No-op detection: if the active is already at exactly that slot, return null.
  const activeParent = locateParent(tree, activeId);
  if (
    activeParent &&
    ((activeParent.parent?.id ?? null) === newParentId) &&
    active.sort_index === sortIndex
  ) {
    return null;
  }

  return { newParentId, sortIndex };
}
