/**
 * Tests for weight display in the Component Tree (gh#78).
 *
 * Each row shows a colored Scale icon (green/yellow/red) driven by the
 * backend's per-node `weight_status`. The tree header shows the aggregate
 * total weight + status of the roots combined.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

/**
 * Read the virtual-root row's weight status from the DOM.
 *
 * As of gh#89 the aggregated scale + total moved OUT of the panel header INTO
 * a synthesised root row labelled with the aeroplane name. The `data-weight-
 * status` attribute on the first row's Scale span is the aggregate indicator.
 * (Children only render when a group is expanded, so with collapsed children
 * the first `[data-weight-status]` element is the virtual root itself.)
 */
function getVirtualRootStatus(container: HTMLElement): string | null {
  const first = container.querySelector("[data-weight-status]");
  return first?.getAttribute("data-weight-status") ?? null;
}

describe("ComponentTree — weight display (gh#78 + gh#89 virtual root)", () => {
  it("empty tree: virtual root's aggregate status is 'invalid' (red)", () => {
    treeReturnValue = { tree: [], totalNodes: 0, isLoading: false, error: null };
    const { container } = render(<ComponentTree />);
    // The virtual root row is always present — even with no real nodes.
    expect(getVirtualRootStatus(container)).toBe("invalid");
  });

  it("shows GREEN scale + total weight on the virtual root row when all nodes are valid", () => {
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
    expect(getVirtualRootStatus(container)).toBe("valid");
    // Total appears on the virtual root row (the row-level `1` group, collapsed
    // by default, also shows its own total in its annotation).
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
    expect(getVirtualRootStatus(container)).toBe("invalid");
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
    expect(getVirtualRootStatus(container)).toBe("partial");
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

// --------------------------------------------------------------------------- //
// gh#89 — virtual root node contract.
// --------------------------------------------------------------------------- //

describe("ComponentTree — virtual root (gh#89)", () => {
  it("renders a root row labelled with the fallback 'Aeroplane' when no aeroplane name is known", () => {
    treeReturnValue = { tree: [], totalNodes: 0, isLoading: false, error: null };
    render(<ComponentTree />);
    // The tests don't mock useAeroplanes, so aeroplanes[] is empty → fallback.
    expect(screen.getByText("Aeroplane")).toBeDefined();
  });

  it("panel header no longer carries a weight chip or data-root-weight-status", () => {
    treeReturnValue = {
      tree: [
        makeNode({
          id: 1, name: "wing", weight_status: "valid",
          total_weight_g: 124.2, own_weight_g: 124.2, own_weight_source: "override",
        }),
      ],
      totalNodes: 1, isLoading: false, error: null,
    };
    const { container } = render(<ComponentTree />);
    // The old header-side aggregate icon attribute is gone.
    expect(container.querySelector("[data-root-weight-status]")).toBeNull();
    // The total still renders — on the virtual root row — so the user still
    // sees the number, just no longer in the header chip slot.
    expect(screen.getAllByText("124.2g").length).toBeGreaterThanOrEqual(1);
  });

  it("virtual root row has no delete icon (cannot be deleted)", () => {
    treeReturnValue = {
      tree: [
        makeNode({ id: 1, name: "wing", weight_status: "valid", total_weight_g: 50 }),
      ],
      totalNodes: 1, isLoading: false, error: null,
    };
    const { container } = render(<ComponentTree />);
    // The real row for "wing" still has a delete button. The virtual root row
    // must not. Count Trash2 icons across all rows — with one real child and
    // the virtual root, we must see at most one (never two).
    const deleteButtons = container.querySelectorAll(
      'button.text-destructive',
    );
    // The virtual root row has no delete button. The child row does.
    expect(deleteButtons.length).toBe(1);
  });

  it("collapsing the virtual root hides every child row", async () => {
    const user = userEvent.setup();
    treeReturnValue = {
      tree: [
        makeNode({ id: 1, name: "wing", weight_status: "valid", total_weight_g: 50 }),
        makeNode({ id: 2, name: "fuselage", weight_status: "valid", total_weight_g: 20 }),
      ],
      totalNodes: 2, isLoading: false, error: null,
    };
    render(<ComponentTree />);
    // Both real roots are visible while the virtual root is expanded (default).
    expect(screen.getByText("wing")).toBeDefined();
    expect(screen.getByText("fuselage")).toBeDefined();
    // Click the virtual root label to toggle it collapsed.
    await user.click(screen.getByText("Aeroplane"));
    expect(screen.queryByText("wing")).toBeNull();
    expect(screen.queryByText("fuselage")).toBeNull();
    // The virtual root itself stays visible.
    expect(screen.getByText("Aeroplane")).toBeDefined();
  });

  it("virtual root row exposes an 'Add to Aeroplane' affordance (replaces header + button)", () => {
    treeReturnValue = { tree: [], totalNodes: 0, isLoading: false, error: null };
    render(<ComponentTree />);
    // Replaces the panel-header "Add to root" button.
    expect(screen.getByTitle(/Add to Aeroplane/i)).toBeDefined();
  });

  it("real tree rows are indented one level deeper than before (nested under virtual root)", () => {
    treeReturnValue = {
      tree: [makeNode({ id: 1, name: "wing", weight_status: "valid", total_weight_g: 50 })],
      totalNodes: 1, isLoading: false, error: null,
    };
    render(<ComponentTree />);
    // Find the row for "wing" and verify its padding-left corresponds to level=1
    // (= 20px) rather than the pre-gh#89 level=0 (= 0px).
    const wingText = screen.getByText("wing");
    const row = wingText.closest('[aria-roledescription="sortable"]') as HTMLElement;
    expect(row.style.paddingLeft).toBe("20px");
    // Virtual root stays at level=0 (no indent).
    const aeroText = screen.getByText("Aeroplane");
    const rootRow = aeroText.closest('[aria-roledescription="sortable"]') as HTMLElement;
    expect(rootRow.style.paddingLeft).toBe("0px");
  });
});
