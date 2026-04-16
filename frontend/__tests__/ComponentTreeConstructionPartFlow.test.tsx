/**
 * End-to-end wiring test for the Construction-Part add flow (gh#57-wvg).
 *
 * Click (+) on a group → click "Assign Construction Part" → picker opens →
 * click a part → addTreeNode fires with node_type='cad_shape' and
 * construction_part_id set (N1 snapshot logic on the backend then fills
 * volume_mm3 / area_mm2 / material_id).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    Plus: icon, Trash2: icon, X: icon, Check: icon,
    ChevronDown: icon, ChevronRight: icon,
    FolderPlus: icon, Package: icon, Box: icon,
    Search: icon, Loader2: icon, Settings: icon, Lock: icon,
    GripVertical: icon, Pencil: icon,
  };
});

const mockAddTreeNode = vi.fn().mockResolvedValue({});
const mockMutate = vi.fn();

vi.mock("@/hooks/useComponentTree", () => ({
  useComponentTree: () => ({
    tree: [
      {
        id: 10, aeroplane_id: "a", parent_id: null, sort_index: 0,
        node_type: "group", name: "main_wing",
        component_id: null, quantity: 1, weight_override_g: null,
        children: [],
      },
    ],
    totalNodes: 1,
    isLoading: false,
    error: null,
    mutate: mockMutate,
  }),
  addTreeNode: (...args: unknown[]) => mockAddTreeNode(...args),
  deleteTreeNode: vi.fn().mockResolvedValue(undefined),
  moveTreeNode: vi.fn().mockResolvedValue({}),
}));

vi.mock("@/hooks/useConstructionParts", () => ({
  useConstructionParts: () => ({
    parts: [
      {
        id: 77, aeroplane_id: "a", name: "Bulkhead-A",
        volume_mm3: 5000, area_mm2: 400,
        bbox_x_mm: 50, bbox_y_mm: 40, bbox_z_mm: 5,
        material_component_id: null, locked: false,
        thumbnail_url: null, file_path: "tmp/x.stl", file_format: "stl",
        created_at: "2026-04-16T00:00:00Z", updated_at: "2026-04-16T00:00:00Z",
      },
    ],
    total: 1,
    isLoading: false,
    error: null,
    mutate: vi.fn(),
  }),
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

describe("ComponentTree — Construction-Part add flow (gh#57-wvg)", () => {
  it("the 'Assign Construction Part' menu item is enabled", () => {
    render(<ComponentTree />);
    fireEvent.click(screen.getByTitle("Add to main_wing"));

    const button = screen.getByText("Assign Construction Part").closest("button");
    expect(button).not.toBeNull();
    expect(button?.hasAttribute("disabled")).toBe(false);
  });

  it("opens the Construction-Part picker on menu click", () => {
    render(<ComponentTree />);
    fireEvent.click(screen.getByTitle("Add to main_wing"));
    fireEvent.click(screen.getByText("Assign Construction Part"));

    expect(screen.getByText(/Assign Construction Part to 'main_wing'/)).toBeDefined();
    expect(screen.getByText("Bulkhead-A")).toBeDefined();
  });

  it("creates a cad_shape tree node with construction_part_id on selection", async () => {
    render(<ComponentTree />);
    fireEvent.click(screen.getByTitle("Add to main_wing"));
    fireEvent.click(screen.getByText("Assign Construction Part"));
    fireEvent.click(screen.getByText("Bulkhead-A"));

    expect(mockAddTreeNode).toHaveBeenCalledWith(
      "a",
      expect.objectContaining({
        parent_id: 10,
        node_type: "cad_shape",
        name: "Bulkhead-A",
        construction_part_id: 77,
      }),
    );
  });
});
