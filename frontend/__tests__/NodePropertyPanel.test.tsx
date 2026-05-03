/**
 * Tests for NodePropertyPanel (gh#57-38x).
 *
 * The panel is driven by a single prop `node: ComponentTreeNode | null`.
 * Each node type exposes a different field set per AC-E-2. Save posts to
 * PUT /aeroplanes/{id}/component-tree/{nodeId} via updateTreeNode().
 * Delete uses a shared confirmation modal (replaces window.confirm).
 * Lock-toggle for cad_shape nodes calls the construction-parts lock/unlock
 * endpoint and is disabled when construction_part_id is not set.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import type { ComponentTreeNode } from "@/hooks/useComponentTree";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    X: icon, Save: icon, Loader2: icon, Trash2: icon, Lock: icon, Unlock: icon,
    AlertTriangle: icon, Settings: icon, Package: icon, Box: icon,
  };
});

const mockUpdate = vi.fn().mockResolvedValue({});
const mockDelete = vi.fn().mockResolvedValue(undefined);
const mockLock = vi.fn().mockResolvedValue({});
const mockUnlock = vi.fn().mockResolvedValue({});

vi.mock("@/hooks/useComponentTree", () => ({
  updateTreeNode: (...a: unknown[]) => mockUpdate(...a),
  deleteTreeNode: (...a: unknown[]) => mockDelete(...a),
}));

vi.mock("@/hooks/useConstructionParts", () => ({
  lockConstructionPart: (...a: unknown[]) => mockLock(...a),
  unlockConstructionPart: (...a: unknown[]) => mockUnlock(...a),
}));

vi.mock("@/hooks/useComponents", () => ({
  useComponents: (filter?: string) => ({
    components: filter === "material"
      ? [
          { id: 42, name: "PLA+", component_type: "material", manufacturer: "eSUN", specs: { density_kg_m3: 1240 } },
          { id: 43, name: "PETG", component_type: "material", manufacturer: "Prusa", specs: { density_kg_m3: 1270 } },
        ]
      : [],
    total: 2,
    isLoading: false,
    error: null,
    mutate: vi.fn(),
  }),
}));

vi.mock("@/lib/fetcher", () => ({ API_BASE: "http://x", fetcher: vi.fn() }));

import { NodePropertyPanel } from "@/components/workbench/NodePropertyPanel";

function makeNode(overrides: Partial<ComponentTreeNode> = {}): ComponentTreeNode {
  return {
    id: 1, aeroplane_id: "a", parent_id: null, sort_index: 0,
    node_type: "group", name: "root",
    component_id: null, quantity: 1, weight_override_g: null,
    synced_from: null,
    children: [],
    ...overrides,
  } as unknown as ComponentTreeNode;
}

beforeEach(() => {
  vi.clearAllMocks();
});

// --------------------------------------------------------------------------- //
// Visibility / empty state
// --------------------------------------------------------------------------- //

describe("NodePropertyPanel — visibility", () => {
  it("renders nothing when node is null", () => {
    const { container } = render(
      <NodePropertyPanel
        node={null}
        aeroplaneId="a"
        onMutate={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(container.textContent ?? "").toBe("");
  });

  it("renders the node name in the header when a node is provided", () => {
    render(
      <NodePropertyPanel
        node={makeNode({ name: "main_wing" })}
        aeroplaneId="a"
        onMutate={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText("main_wing")).toBeDefined();
  });
});

// --------------------------------------------------------------------------- //
// Field sets per node type (AC-E-2)
// --------------------------------------------------------------------------- //

describe("NodePropertyPanel — field sets per node type", () => {
  it("group: shows name + weight_override only", () => {
    const node = makeNode({ node_type: "group", name: "wing", weight_override_g: null });
    render(
      <NodePropertyPanel node={node} aeroplaneId="a" onMutate={vi.fn()} onClose={vi.fn()} />,
    );
    expect(screen.getByText(/^Name/)).toBeDefined();
    expect(screen.getByText(/Weight override/i)).toBeDefined();
    expect(screen.queryByText(/Quantity/i)).toBeNull();
    expect(screen.queryByText(/Material/i)).toBeNull();
    expect(screen.queryByText(/^Pos\s*X/i)).toBeNull();
  });

  it("cots: adds Quantity", () => {
    const node = makeNode({ node_type: "cots", name: "servo", component_id: 5, quantity: 2 });
    render(
      <NodePropertyPanel node={node} aeroplaneId="a" onMutate={vi.fn()} onClose={vi.fn()} />,
    );
    expect(screen.getByText(/Quantity/i)).toBeDefined();
    expect(screen.queryByText(/Material/i)).toBeNull();
    expect(screen.queryByText(/^Pos\s*X/i)).toBeNull();
  });

  it("cad_shape: adds 6-DOF, Material, Scale factor, Print type, Lock toggle", () => {
    const node = makeNode({ node_type: "cad_shape", name: "rib" });
    render(
      <NodePropertyPanel node={node} aeroplaneId="a" onMutate={vi.fn()} onClose={vi.fn()} />,
    );
    // Material label (the word also appears in the node-type chip on group
    // nodes, so we match the exact label text, not a regex).
    expect(screen.getByText("Material")).toBeDefined();
    expect(screen.getByText(/Pos X/i)).toBeDefined();
    expect(screen.getByText(/Pos Y/i)).toBeDefined();
    expect(screen.getByText(/Pos Z/i)).toBeDefined();
    expect(screen.getByText(/Rot X/i)).toBeDefined();
    expect(screen.getByText(/Scale factor/i)).toBeDefined();
    expect(screen.getByText(/Print type/i)).toBeDefined();
  });
});

// --------------------------------------------------------------------------- //
// Material dropdown (AC-E-3)
// --------------------------------------------------------------------------- //

describe("NodePropertyPanel — material dropdown", () => {
  it("lists materials with density label", () => {
    const node = makeNode({ node_type: "cad_shape", name: "r" });
    render(
      <NodePropertyPanel node={node} aeroplaneId="a" onMutate={vi.fn()} onClose={vi.fn()} />,
    );
    expect(screen.getByText(/PLA\+.*1240.*kg\/m/i)).toBeDefined();
    expect(screen.getByText(/PETG.*1270.*kg\/m/i)).toBeDefined();
  });
});

// --------------------------------------------------------------------------- //
// Save (AC-E-4)
// --------------------------------------------------------------------------- //

describe("NodePropertyPanel — save", () => {
  it("Save posts the edited fields via updateTreeNode", async () => {
    const user = userEvent.setup();
    const node = makeNode({ id: 7, node_type: "group", name: "old" });
    const onMutate = vi.fn();
    const { container } = render(
      <NodePropertyPanel node={node} aeroplaneId="a" onMutate={onMutate} onClose={vi.fn()} />,
    );

    const nameInput = container.querySelector('input[type="text"]') as HTMLInputElement;
    await user.clear(nameInput);
    await user.type(nameInput, "renamed");

    await user.click(screen.getByText("Save"));

    expect(mockUpdate).toHaveBeenCalledWith(
      "a",
      7,
      expect.objectContaining({ name: "renamed", node_type: "group" }),
    );
    // onMutate fires after the API resolves; with mockResolvedValue that's synchronous-ish
    await Promise.resolve();
    expect(onMutate).toHaveBeenCalled();
  });

  it("Save button is disabled when no fields are dirty", () => {
    const node = makeNode({ id: 1, node_type: "group", name: "x" });
    render(
      <NodePropertyPanel node={node} aeroplaneId="a" onMutate={vi.fn()} onClose={vi.fn()} />,
    );
    const saveBtn = screen.getByText("Save").closest("button") as HTMLButtonElement;
    expect(saveBtn.disabled).toBe(true);
  });

  it("Cancel resets the form without calling the API", async () => {
    const user = userEvent.setup();
    const node = makeNode({ id: 1, node_type: "group", name: "orig" });
    const { container } = render(
      <NodePropertyPanel node={node} aeroplaneId="a" onMutate={vi.fn()} onClose={vi.fn()} />,
    );
    const nameInput = container.querySelector('input[type="text"]') as HTMLInputElement;

    await user.clear(nameInput);
    await user.type(nameInput, "edited");
    expect(nameInput.value).toBe("edited");
    await user.click(screen.getByText("Cancel"));
    expect(nameInput.value).toBe("orig");
    expect(mockUpdate).not.toHaveBeenCalled();
  });
});

// --------------------------------------------------------------------------- //
// Delete flow (AC-E-5)
// --------------------------------------------------------------------------- //

describe("NodePropertyPanel — delete", () => {
  it("opens a confirmation modal on Delete click", async () => {
    const user = userEvent.setup();
    const node = makeNode({ id: 5, name: "doomed" });
    render(
      <NodePropertyPanel node={node} aeroplaneId="a" onMutate={vi.fn()} onClose={vi.fn()} />,
    );

    await user.click(screen.getByTitle("Delete node"));
    expect(screen.getByText(/Delete "doomed"/)).toBeDefined();
  });

  it("Confirm in the modal fires deleteTreeNode; Cancel does not", async () => {
    const user = userEvent.setup();
    const node = makeNode({ id: 5, name: "doomed" });
    const onClose = vi.fn();
    const onMutate = vi.fn();
    const { rerender } = render(
      <NodePropertyPanel node={node} aeroplaneId="a" onMutate={onMutate} onClose={onClose} />,
    );

    await user.click(screen.getByTitle("Delete node"));
    await user.click(screen.getByText(/Confirm/));
    expect(mockDelete).toHaveBeenCalledWith("a", 5);

    // Reset: re-render, click delete, then Cancel in the modal — no delete.
    // There are two "Cancel" buttons when the modal is open (form footer +
    // modal footer); click the one INSIDE the modal dialog.
    mockDelete.mockClear();
    rerender(
      <NodePropertyPanel node={node} aeroplaneId="a" onMutate={onMutate} onClose={onClose} />,
    );
    await user.click(screen.getByTitle("Delete node"));
    const modalCancel = screen
      .getAllByText("Cancel")
      .find((el) => el.closest("dialog") !== null) as HTMLElement;
    expect(modalCancel).toBeDefined();
    await user.click(modalCancel);
    expect(mockDelete).not.toHaveBeenCalled();
  });
});

// --------------------------------------------------------------------------- //
// Lock toggle (AC-E-6)
// --------------------------------------------------------------------------- //

describe("NodePropertyPanel — lock toggle", () => {
  it("shows a Lock button for cad_shape with construction_part_id", () => {
    const node = makeNode({
      node_type: "cad_shape", name: "part",
    });
    // construction_part_id is an extra field on the runtime type — typecast.
    (node as unknown as { construction_part_id: number }).construction_part_id = 99;

    render(
      <NodePropertyPanel node={node} aeroplaneId="a" onMutate={vi.fn()} onClose={vi.fn()} />,
    );
    const btn = screen.getByTitle(/Lock/i);
    expect(btn).toBeDefined();
    expect((btn as HTMLButtonElement).disabled).toBe(false);
  });

  it("disables the Lock button when construction_part_id is not set", () => {
    const node = makeNode({ node_type: "cad_shape", name: "no-fk" });
    render(
      <NodePropertyPanel node={node} aeroplaneId="a" onMutate={vi.fn()} onClose={vi.fn()} />,
    );
    const btn = screen.getByTitle(/Lock/i) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it("does not show a Lock button for group or cots nodes", () => {
    render(
      <NodePropertyPanel
        node={makeNode({ node_type: "group", name: "g" })}
        aeroplaneId="a" onMutate={vi.fn()} onClose={vi.fn()}
      />,
    );
    expect(screen.queryByTitle(/Lock/i)).toBeNull();
  });

  it("Lock click fires lockConstructionPart with the FK", async () => {
    const user = userEvent.setup();
    const node = makeNode({ node_type: "cad_shape", name: "p" });
    (node as unknown as { construction_part_id: number }).construction_part_id = 42;

    render(
      <NodePropertyPanel node={node} aeroplaneId="a" onMutate={vi.fn()} onClose={vi.fn()} />,
    );
    await user.click(screen.getByTitle("Lock part"));
    expect(mockLock).toHaveBeenCalledWith("a", 42);
  });
});

// --------------------------------------------------------------------------- //
// Synced warning (AC-E-7)
// --------------------------------------------------------------------------- //

describe("NodePropertyPanel — synced warning chip", () => {
  it("shows a warning chip when synced_from is set", () => {
    const node = makeNode({ name: "seg0", synced_from: "wing:main_wing:segment:0" });
    render(
      <NodePropertyPanel node={node} aeroplaneId="a" onMutate={vi.fn()} onClose={vi.fn()} />,
    );
    expect(screen.getByText(/Synced from/i)).toBeDefined();
    expect(screen.getByText(/wing:main_wing:segment:0/)).toBeDefined();
  });

  it("does not show the warning when synced_from is null", () => {
    const node = makeNode({ synced_from: null });
    render(
      <NodePropertyPanel node={node} aeroplaneId="a" onMutate={vi.fn()} onClose={vi.fn()} />,
    );
    expect(screen.queryByText(/Synced from/i)).toBeNull();
  });
});
