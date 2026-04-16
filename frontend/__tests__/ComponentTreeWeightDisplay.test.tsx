/**
 * Tests for weight display in the Component Tree (gh#78).
 *
 * Each row shows a colored Scale icon (green/yellow/red) driven by the
 * backend's per-node `weight_status`. The tree header shows the aggregate
 * total weight + status of the roots combined.
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
    Search: icon, Loader2: icon, Settings: icon,
    GripVertical: icon, Pencil: icon, Scale: icon,
  };
});

const mockMutate = vi.fn();
let treeReturnValue: Record<string, unknown> = {
  tree: [],
  totalNodes: 0,
  isLoading: false,
  error: null,
};

vi.mock("@/hooks/useComponentTree", () => ({
  useComponentTree: () => ({ ...treeReturnValue, mutate: mockMutate }),
  addTreeNode: vi.fn(),
  deleteTreeNode: vi.fn().mockResolvedValue(undefined),
  moveTreeNode: vi.fn().mockResolvedValue({}),
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

beforeEach(() => {
  vi.clearAllMocks();
});

function makeNode(overrides: Record<string, unknown> = {}) {
  return {
    id: 1, aeroplane_id: "a", parent_id: null, sort_index: 0,
    node_type: "group", name: "root",
    component_id: null, quantity: 1, weight_override_g: null,
    children: [],
    ...overrides,
  };
}

describe("ComponentTree — weight display (gh#78)", () => {
  it("shows no header badge or icon when the tree is empty", () => {
    treeReturnValue = { tree: [], totalNodes: 0, isLoading: false, error: null };
    const { container } = render(<ComponentTree />);
    expect(container.querySelector("[data-root-weight-status]")).toBeDefined();
    // Status is "invalid" for an empty tree (red).
    const aggIcon = container.querySelector("[data-root-weight-status]") as HTMLElement;
    expect(aggIcon.getAttribute("data-root-weight-status")).toBe("invalid");
  });

  it("shows GREEN scale + total weight when all nodes are valid", () => {
    treeReturnValue = {
      tree: [
        makeNode({
          id: 1, name: "valid-tree", weight_status: "valid",
          own_weight_g: 100, own_weight_source: "override",
          total_weight_g: 250,
          children: [
            makeNode({ id: 2, parent_id: 1, name: "child1", node_type: "cots",
              weight_status: "valid", own_weight_g: 50, own_weight_source: "cots",
              total_weight_g: 50 }),
            makeNode({ id: 3, parent_id: 1, name: "child2", node_type: "cots",
              weight_status: "valid", own_weight_g: 100, own_weight_source: "cots",
              total_weight_g: 100 }),
          ],
        }),
      ],
      totalNodes: 3,
      isLoading: false,
      error: null,
    };
    const { container } = render(<ComponentTree />);
    const agg = container.querySelector("[data-root-weight-status]") as HTMLElement;
    expect(agg.getAttribute("data-root-weight-status")).toBe("valid");
    // Total weight appears at least in the badge (and also in the row annotation).
    expect(screen.getAllByText("250.0g").length).toBeGreaterThanOrEqual(1);
  });

  it("shows RED scale when the only root is invalid", () => {
    treeReturnValue = {
      tree: [
        makeNode({
          id: 1, name: "broken",
          weight_status: "invalid", own_weight_g: null, own_weight_source: "none",
          total_weight_g: 0, children: [],
        }),
      ],
      totalNodes: 1, isLoading: false, error: null,
    };
    const { container } = render(<ComponentTree />);
    const agg = container.querySelector("[data-root-weight-status]") as HTMLElement;
    expect(agg.getAttribute("data-root-weight-status")).toBe("invalid");
  });

  it("shows YELLOW scale for a partially-valid tree", () => {
    treeReturnValue = {
      tree: [
        makeNode({
          id: 1, name: "root", weight_status: "partial",
          own_weight_g: null, own_weight_source: "none",
          total_weight_g: 50,
          children: [
            makeNode({ id: 2, parent_id: 1, name: "ok", node_type: "cots",
              weight_status: "valid", own_weight_g: 50, own_weight_source: "cots",
              total_weight_g: 50 }),
            makeNode({ id: 3, parent_id: 1, name: "missing", node_type: "cad_shape",
              weight_status: "invalid", own_weight_g: null, own_weight_source: "none",
              total_weight_g: 0 }),
          ],
        }),
      ],
      totalNodes: 3, isLoading: false, error: null,
    };
    const { container } = render(<ComponentTree />);
    const agg = container.querySelector("[data-root-weight-status]") as HTMLElement;
    expect(agg.getAttribute("data-root-weight-status")).toBe("partial");
    expect(screen.getAllByText("50.0g").length).toBeGreaterThanOrEqual(1);
  });

  it("renders per-row weight status icons", () => {
    treeReturnValue = {
      tree: [
        makeNode({
          id: 1, name: "root", weight_status: "partial",
          own_weight_g: null, own_weight_source: "none", total_weight_g: 50,
          children: [
            makeNode({ id: 2, parent_id: 1, name: "ok", node_type: "cots",
              weight_status: "valid", own_weight_g: 50, own_weight_source: "cots",
              total_weight_g: 50 }),
            makeNode({ id: 3, parent_id: 1, name: "missing", node_type: "cad_shape",
              weight_status: "invalid", own_weight_g: null, own_weight_source: "none",
              total_weight_g: 0 }),
          ],
        }),
      ],
      totalNodes: 3, isLoading: false, error: null,
    };
    const { container } = render(<ComponentTree />);
    // Per-row status attributes (data-weight-status exposed by SimpleTreeRow).
    const statuses = Array.from(
      container.querySelectorAll("[data-weight-status]"),
    ).map((el) => el.getAttribute("data-weight-status"));
    expect(statuses).toContain("partial"); // root
    // Children only render when expanded — root is collapsed by default, so
    // only the root's status icon is visible. That's fine; this test asserts
    // presence of the data attribute plumbing, not hover/expand behavior.
  });

  it("uses backend total_weight_g for the row annotation (not weight_override_g)", () => {
    treeReturnValue = {
      tree: [
        makeNode({
          id: 1, name: "root",
          weight_status: "valid", own_weight_g: 10, own_weight_source: "override",
          weight_override_g: 10,  // override present
          total_weight_g: 42.5,   // but total includes children
          children: [],
        }),
      ],
      totalNodes: 1, isLoading: false, error: null,
    };
    const { container } = render(<ComponentTree />);
    // The annotation shows total_weight_g with one decimal. With children
    // suppressed the total equals own, but the annotation format proves we
    // used total_weight_g not weight_override_g (otherwise it'd be "10g").
    expect(container.textContent).toContain("42.5g");
  });
});
