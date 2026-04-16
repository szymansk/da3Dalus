/**
 * Integration tests for the Component Tree drag-and-drop wiring (gh#57-wak).
 *
 * The pure drop-resolution logic is exhaustively covered in `treeDnd.test.ts`.
 * Here we verify the React glue: the row exposes draggable attributes, and
 * the exported `handleDragEnd` callback wires through to `moveTreeNode` /
 * `mutate()` with optimistic-rollback semantics.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    Plus: icon, Trash2: icon, X: icon, Check: icon,
    ChevronDown: icon, ChevronRight: icon,
    FolderPlus: icon, Package: icon, Box: icon,
    Search: icon, Loader2: icon, GripVertical: icon, Pencil: icon, Scale: icon,
  };
});

const mockMoveTreeNode = vi.fn().mockResolvedValue({});
const mockMutate = vi.fn();

vi.mock("@/hooks/useComponentTree", () => ({
  useComponentTree: () => ({
    tree: [
      {
        id: 10, aeroplane_id: "a", parent_id: null, sort_index: 0,
        node_type: "group", name: "eHawk",
        component_id: null, quantity: 1, weight_override_g: null,
        children: [
          {
            id: 20, aeroplane_id: "a", parent_id: 10, sort_index: 0,
            node_type: "group", name: "main_wing",
            component_id: null, quantity: 1, weight_override_g: null,
            children: [],
          },
        ],
      },
    ],
    totalNodes: 2,
    isLoading: false,
    error: null,
    mutate: mockMutate,
  }),
  addTreeNode: vi.fn().mockResolvedValue({}),
  deleteTreeNode: vi.fn().mockResolvedValue(undefined),
  moveTreeNode: (...args: unknown[]) => mockMoveTreeNode(...args),
}));

vi.mock("@/hooks/useComponents", () => ({
  useComponents: () => ({ components: [], total: 0, isLoading: false, error: null, mutate: vi.fn() }),
  useComponentTypes: () => ["generic"],
}));

vi.mock("@/components/workbench/AeroplaneContext", () => ({
  useAeroplaneContext: () => ({
    aeroplaneId: "a",
    selectedWing: null, selectedXsecIndex: null,
    selectedFuselage: null, selectedFuselageXsecIndex: null,
    treeMode: "wingconfig",
    setAeroplaneId: vi.fn(), selectWing: vi.fn(), selectXsec: vi.fn(),
    selectFuselage: vi.fn(), selectFuselageXsec: vi.fn(), setTreeMode: vi.fn(),
  }),
}));

vi.mock("@/lib/fetcher", () => ({ API_BASE: "http://x", fetcher: vi.fn() }));

import { ComponentTree } from "@/components/workbench/ComponentTree";
import { handleDragEnd } from "@/components/workbench/ComponentTree";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ComponentTree — drag-and-drop wiring", () => {
  it("renders without crashing under a DndContext-equipped tree", () => {
    render(<ComponentTree />);
    expect(screen.getByText("eHawk")).toBeDefined();
  });

  it("rows expose a draggable attribute (data-dnd-handle or aria-roledescription)", () => {
    const { container } = render(<ComponentTree />);
    const draggables = container.querySelectorAll(
      '[aria-roledescription="sortable"], [data-dnd-handle="true"]',
    );
    expect(draggables.length).toBeGreaterThan(0);
  });
});

// --------------------------------------------------------------------------- //
// Pure handleDragEnd unit tests
// --------------------------------------------------------------------------- //

const treeFixture = [
  {
    id: 10, aeroplane_id: "a", parent_id: null, sort_index: 0,
    node_type: "group" as const, name: "eHawk",
    component_id: null, quantity: 1, weight_override_g: null,
    children: [
      {
        id: 20, aeroplane_id: "a", parent_id: 10, sort_index: 0,
        node_type: "group" as const, name: "main_wing",
        component_id: null, quantity: 1, weight_override_g: null,
        children: [
          {
            id: 100, aeroplane_id: "a", parent_id: 20, sort_index: 0,
            node_type: "cots" as const, name: "servo",
            component_id: 7, quantity: 1, weight_override_g: null,
            children: [],
          },
        ],
      },
      {
        id: 30, aeroplane_id: "a", parent_id: 10, sort_index: 1,
        node_type: "group" as const, name: "v_tail",
        component_id: null, quantity: 1, weight_override_g: null,
        children: [],
      },
    ],
  },
];

describe("handleDragEnd", () => {
  it("calls moveTreeNode + mutate when the drop is valid", async () => {
    await handleDragEnd({
      activeId: 100,
      overId: 30,
      tree: treeFixture,
      aeroplaneId: "a",
      moveFn: mockMoveTreeNode,
      mutateFn: mockMutate,
    });
    expect(mockMoveTreeNode).toHaveBeenCalledWith(
      "a",
      100,
      { new_parent_id: 30, sort_index: 0 },
    );
    expect(mockMutate).toHaveBeenCalled();
  });

  it("does not call moveTreeNode when activeId == overId (drop on self)", async () => {
    await handleDragEnd({
      activeId: 20, overId: 20, tree: treeFixture,
      aeroplaneId: "a", moveFn: mockMoveTreeNode, mutateFn: mockMutate,
    });
    expect(mockMoveTreeNode).not.toHaveBeenCalled();
  });

  it("does not call moveTreeNode when target is a descendant of source (cycle)", async () => {
    await handleDragEnd({
      activeId: 10, overId: 100, tree: treeFixture,
      aeroplaneId: "a", moveFn: mockMoveTreeNode, mutateFn: mockMutate,
    });
    expect(mockMoveTreeNode).not.toHaveBeenCalled();
  });

  it("does not call moveTreeNode when overId is null (drop outside)", async () => {
    await handleDragEnd({
      activeId: 100, overId: null, tree: treeFixture,
      aeroplaneId: "a", moveFn: mockMoveTreeNode, mutateFn: mockMutate,
    });
    expect(mockMoveTreeNode).not.toHaveBeenCalled();
  });

  it("triggers mutate even when the move API rejects (rollback)", async () => {
    const reject = vi.fn().mockRejectedValue(new Error("network"));
    await handleDragEnd({
      activeId: 100, overId: 30, tree: treeFixture,
      aeroplaneId: "a", moveFn: reject, mutateFn: mockMutate,
    }).catch(() => undefined);
    // mutate is called BEFORE the API call (optimistic) AND after error to
    // trigger a rollback refetch.
    expect(mockMutate).toHaveBeenCalled();
  });

  it("drops on a leaf (cots) do nothing — leaves are not 'into' targets", async () => {
    await handleDragEnd({
      activeId: 30, overId: 100, tree: treeFixture,
      aeroplaneId: "a", moveFn: mockMoveTreeNode, mutateFn: mockMutate,
    });
    expect(mockMoveTreeNode).not.toHaveBeenCalled();
  });
});
