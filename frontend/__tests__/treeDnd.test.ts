/**
 * Pure-logic tests for the tree drag-and-drop helpers (gh#57-wak).
 *
 * The interactive @dnd-kit wiring lives in <ComponentTree>; these helpers
 * compute the API call (or null) given a drop event description. Keeping the
 * pure logic separate means we can cover all corner cases (cycles, root
 * drops, sibling reorder) without simulating mouse events.
 */
import { describe, it, expect } from "vitest";
import type { ComponentTreeNode } from "@/hooks/useComponentTree";
import {
  findNode,
  isDescendantOf,
  computeMoveResult,
  type DropPosition,
} from "@/lib/treeDnd";

const fixture = (): ComponentTreeNode[] => [
  {
    id: 1, aeroplane_id: "a", parent_id: null, sort_index: 0,
    node_type: "group", name: "eHawk",
    component_id: null, quantity: 1, weight_override_g: null,
    children: [
      {
        id: 10, aeroplane_id: "a", parent_id: 1, sort_index: 0,
        node_type: "group", name: "main_wing",
        component_id: null, quantity: 1, weight_override_g: null,
        children: [
          {
            id: 100, aeroplane_id: "a", parent_id: 10, sort_index: 0,
            node_type: "cots", name: "servo",
            component_id: 7, quantity: 1, weight_override_g: null,
            children: [],
          },
          {
            id: 101, aeroplane_id: "a", parent_id: 10, sort_index: 1,
            node_type: "cad_shape", name: "rib",
            component_id: null, quantity: 1, weight_override_g: null,
            children: [],
          },
        ],
      },
      {
        id: 20, aeroplane_id: "a", parent_id: 1, sort_index: 1,
        node_type: "group", name: "v_tail",
        component_id: null, quantity: 1, weight_override_g: null,
        children: [],
      },
    ],
  },
];

describe("findNode", () => {
  it("returns the node at root", () => {
    expect(findNode(fixture(), 1)?.name).toBe("eHawk");
  });
  it("returns a deeply nested node", () => {
    expect(findNode(fixture(), 100)?.name).toBe("servo");
  });
  it("returns null for an unknown ID", () => {
    expect(findNode(fixture(), 999)).toBeNull();
  });
});

describe("isDescendantOf", () => {
  it("identifies a direct child", () => {
    expect(isDescendantOf(fixture(), 1, 10)).toBe(true);
  });
  it("identifies a deep grandchild", () => {
    expect(isDescendantOf(fixture(), 1, 100)).toBe(true);
  });
  it("returns false for a sibling", () => {
    expect(isDescendantOf(fixture(), 10, 20)).toBe(false);
  });
  it("returns false for an ancestor", () => {
    expect(isDescendantOf(fixture(), 100, 1)).toBe(false);
  });
  it("returns false for the same node", () => {
    expect(isDescendantOf(fixture(), 10, 10)).toBe(false);
  });
});

describe("computeMoveResult", () => {
  it("'into' a group makes the source a child of that group", () => {
    const result = computeMoveResult(fixture(), 100, 20, "into" as DropPosition);
    expect(result).toEqual({ newParentId: 20, sortIndex: 0 });
  });

  it("'into' an empty group → sortIndex = 0", () => {
    const result = computeMoveResult(fixture(), 100, 20, "into" as DropPosition);
    expect(result?.sortIndex).toBe(0);
  });

  it("'into' a group with existing children → sortIndex = end of children", () => {
    const result = computeMoveResult(fixture(), 100, 10, "into" as DropPosition);
    // moving 100 into group 10 (its current parent, but treat as fresh):
    // group 10 has children [100, 101]; moving "into" appends → sortIndex = 2
    expect(result?.sortIndex).toBe(2);
  });

  it("'before' a sibling reorders within the same parent", () => {
    // move 101 before 100 within group 10
    const result = computeMoveResult(fixture(), 101, 100, "before" as DropPosition);
    expect(result).toEqual({ newParentId: 10, sortIndex: 0 });
  });

  it("'after' a sibling reorders within the same parent", () => {
    // move 100 after 101 within group 10
    const result = computeMoveResult(fixture(), 100, 101, "after" as DropPosition);
    expect(result).toEqual({ newParentId: 10, sortIndex: 2 });
  });

  it("'before' a node in a different parent moves AND reorders", () => {
    // move 100 (in group 10) before 20 (in root group 1)
    const result = computeMoveResult(fixture(), 100, 20, "before" as DropPosition);
    expect(result).toEqual({ newParentId: 1, sortIndex: 1 });
  });

  it("returns null when dropping a node onto itself ('into')", () => {
    expect(computeMoveResult(fixture(), 10, 10, "into" as DropPosition)).toBeNull();
  });

  it("returns null when dropping a node onto its descendant", () => {
    // can't move 1 into 100 (cycle)
    expect(computeMoveResult(fixture(), 1, 100, "into" as DropPosition)).toBeNull();
    // can't drop 1 before 100 either
    expect(computeMoveResult(fixture(), 1, 100, "before" as DropPosition)).toBeNull();
  });

  it("returns null when source or target is unknown", () => {
    expect(computeMoveResult(fixture(), 999, 10, "into" as DropPosition)).toBeNull();
    expect(computeMoveResult(fixture(), 10, 999, "into" as DropPosition)).toBeNull();
  });

  it("'into' a leaf node is rejected (only groups accept 'into')", () => {
    // 100 is a cots leaf; cannot drop INTO a leaf
    expect(computeMoveResult(fixture(), 101, 100, "into" as DropPosition)).toBeNull();
  });

  it("dropping a node where it already lives is a no-op (returns null)", () => {
    // 100 is already child[0] of 10; "before" 100 with self → null
    expect(computeMoveResult(fixture(), 100, 100, "before" as DropPosition)).toBeNull();
  });
});
