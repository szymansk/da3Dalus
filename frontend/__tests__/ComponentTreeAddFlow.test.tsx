/**
 * Integration tests for the Component Tree's new add-flow (gh#57-40g):
 *   - per-group (+) button
 *   - inline input for creating sub-groups (replaces window.prompt())
 *   - COTS picker wiring — clicking a component creates a cots tree node
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
    Search: icon, Loader2: icon, Settings: icon,
  };
});

const mockAddTreeNode = vi.fn().mockResolvedValue({});
const mockMutate = vi.fn();
let treeReturnValue: Record<string, unknown> = {
  tree: [
    {
      id: 10,
      aeroplane_id: "aero-1",
      parent_id: null,
      node_type: "group",
      name: "eHawk",
      children: [
        {
          id: 11,
          aeroplane_id: "aero-1",
          parent_id: 10,
          node_type: "group",
          name: "main_wing",
          children: [],
        },
      ],
    },
  ],
  totalNodes: 2,
  isLoading: false,
  error: null,
};

vi.mock("@/hooks/useComponentTree", () => ({
  useComponentTree: () => ({ ...treeReturnValue, mutate: mockMutate }),
  addTreeNode: (...args: unknown[]) => mockAddTreeNode(...args),
  deleteTreeNode: vi.fn().mockResolvedValue(undefined),
}));

let componentsList: Array<Record<string, unknown>> = [
  { id: 77, name: "KST X08", component_type: "servo", manufacturer: "KST", mass_g: 7, specs: {} },
];
vi.mock("@/hooks/useComponents", () => ({
  useComponents: () => ({
    components: componentsList,
    total: componentsList.length,
    error: null,
    isLoading: false,
    mutate: vi.fn(),
  }),
  useComponentTypes: () => ["generic", "servo", "battery"],
}));

vi.mock("@/components/workbench/AeroplaneContext", () => ({
  useAeroplaneContext: () => ({
    aeroplaneId: "aero-1",
    selectedWing: null,
    selectedXsecIndex: null,
    selectedFuselage: null,
    selectedFuselageXsecIndex: null,
    treeMode: "wingconfig",
    setAeroplaneId: vi.fn(),
    selectWing: vi.fn(),
    selectXsec: vi.fn(),
    selectFuselage: vi.fn(),
    selectFuselageXsec: vi.fn(),
    setTreeMode: vi.fn(),
  }),
}));

vi.mock("@/lib/fetcher", () => ({
  API_BASE: "http://localhost:8000",
  fetcher: vi.fn(),
}));

import { ComponentTree } from "@/components/workbench/ComponentTree";

beforeEach(() => {
  vi.clearAllMocks();
  componentsList = [
    { id: 77, name: "KST X08", component_type: "servo", manufacturer: "KST", mass_g: 7, specs: {} },
  ];
  treeReturnValue = {
    tree: [
      {
        id: 10,
        aeroplane_id: "aero-1",
        parent_id: null,
        node_type: "group",
        name: "eHawk",
        children: [
          {
            id: 11,
            aeroplane_id: "aero-1",
            parent_id: 10,
            node_type: "group",
            name: "main_wing",
            children: [],
          },
        ],
      },
    ],
    totalNodes: 2,
    isLoading: false,
    error: null,
  };
});

describe("ComponentTree — per-group add flow", () => {
  it("renders an add button for each group node (root + nested)", () => {
    const { container } = render(<ComponentTree />);
    // Expand the root group so the nested group is visible.
    fireEvent.click(screen.getByText("eHawk"));

    // Expect one add button per group row; root (tree header) + 2 groups = 3 '+' affordances.
    // We query by title since buttons use an empty <span> icon.
    const addButtons = container.querySelectorAll('[title^="Add to"]');
    expect(addButtons.length).toBeGreaterThanOrEqual(2);
  });

  it("opens the popover when a group's (+) is clicked", () => {
    render(<ComponentTree />);
    // Click the (+) on the root group eHawk.
    const rootAddBtn = screen.getByTitle("Add to eHawk");
    fireEvent.click(rootAddBtn);

    expect(screen.getByText("New Group")).toBeDefined();
    expect(screen.getByText("Assign COTS Component")).toBeDefined();
  });

  it("opens an inline input for 'New Group' and submits to create a sub-group", async () => {
    render(<ComponentTree />);
    fireEvent.click(screen.getByTitle("Add to eHawk"));
    fireEvent.click(screen.getByText("New Group"));

    // Inline input appears — we look for a text input placeholder
    const input = screen.getByPlaceholderText(/group name/i) as HTMLInputElement;
    expect(input).toBeDefined();
    fireEvent.change(input, { target: { value: "electronics" } });

    // Submit by pressing Enter
    fireEvent.keyDown(input, { key: "Enter", code: "Enter" });

    expect(mockAddTreeNode).toHaveBeenCalledWith(
      "aero-1",
      expect.objectContaining({
        parent_id: 10,
        node_type: "group",
        name: "electronics",
      }),
    );
  });

  it("cancels the inline input on Escape without calling the API", () => {
    render(<ComponentTree />);
    fireEvent.click(screen.getByTitle("Add to eHawk"));
    fireEvent.click(screen.getByText("New Group"));

    const input = screen.getByPlaceholderText(/group name/i) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "not-saved" } });
    fireEvent.keyDown(input, { key: "Escape", code: "Escape" });

    expect(mockAddTreeNode).not.toHaveBeenCalled();
    expect(screen.queryByPlaceholderText(/group name/i)).toBeNull();
  });

  it("does not submit an empty group name", () => {
    render(<ComponentTree />);
    fireEvent.click(screen.getByTitle("Add to eHawk"));
    fireEvent.click(screen.getByText("New Group"));

    const input = screen.getByPlaceholderText(/group name/i) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "   " } });
    fireEvent.keyDown(input, { key: "Enter", code: "Enter" });

    expect(mockAddTreeNode).not.toHaveBeenCalled();
  });

  it("opens the COTS picker and creates a cots node on selection", async () => {
    render(<ComponentTree />);
    fireEvent.click(screen.getByTitle("Add to eHawk"));
    fireEvent.click(screen.getByText("Assign COTS Component"));

    // The picker dialog is open, library component is listed
    const pickRow = screen.getByText("KST X08");
    fireEvent.click(pickRow);

    expect(mockAddTreeNode).toHaveBeenCalledWith(
      "aero-1",
      expect.objectContaining({
        parent_id: 10,
        node_type: "cots",
        component_id: 77,
        name: "KST X08",
      }),
    );
  });
});
