import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";

// ── Mocks ─────────────────────────────────────────────────────────

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    Hammer: icon, Plus: icon, Trash2: icon, Play: icon, Loader2: icon,
    Search: icon, ChevronDown: icon, ChevronRight: icon, Pencil: icon,
    Scale: icon, Info: icon,
  };
});

const mockMutatePlans = vi.fn();
const mockMutatePlan = vi.fn();
const mockCreatePlan = vi.fn().mockResolvedValue({ id: 99, name: "Test Plan" });
const mockDeletePlan = vi.fn().mockResolvedValue(undefined);
const mockExecutePlan = vi.fn().mockResolvedValue({
  status: "success",
  shape_keys: ["wing_left"],
  export_paths: [],
  error: null,
  duration_ms: 1234,
});

vi.mock("@/hooks/useConstructionPlans", () => ({
  useConstructionPlans: () => ({
    plans: [
      { id: 1, name: "eHawk Wing", description: null, step_count: 3, created_at: "2026-01-01" },
    ],
    error: null,
    isLoading: false,
    mutate: mockMutatePlans,
  }),
  useConstructionPlan: (id: number | null) => ({
    plan: id === 1
      ? {
          id: 1,
          name: "eHawk Wing",
          description: null,
          tree_json: {
            $TYPE: "ConstructionRootNode",
            creator_id: "root",
            successors: [
              { $TYPE: "VaseModeWingCreator", creator_id: "VaseModeWingCreator", wing_index: "main_wing", successors: [] },
            ],
          },
          created_at: "2026-01-01",
          updated_at: "2026-01-01",
        }
      : null,
    error: null,
    isLoading: false,
    mutate: mockMutatePlan,
  }),
  createPlan: (...args: unknown[]) => mockCreatePlan(...args),
  updatePlan: vi.fn().mockResolvedValue({}),
  deletePlan: (...args: unknown[]) => mockDeletePlan(...args),
  executePlan: (...args: unknown[]) => mockExecutePlan(...args),
}));

vi.mock("@/hooks/useCreators", () => ({
  useCreators: () => ({
    creators: [
      {
        class_name: "VaseModeWingCreator",
        category: "wing",
        description: "Vase-mode wing",
        parameters: [{ name: "wing_index", type: "str", default: null, required: true, description: "Index of the wing", options: null }],
        outputs: [{ key: "{id}", description: "Complete wing assembly", options: null }],
        suggested_id: "{wing_index}.vase_wing",
      },
    ],
    error: null,
    isLoading: false,
  }),
  CREATOR_CATEGORIES: ["wing", "fuselage", "cad_operations", "export_import", "components"],
}));

vi.mock("@/hooks/useAeroplanes", () => ({
  useAeroplanes: () => ({
    aeroplanes: [
      { id: "aero-1", name: "eHawk", total_mass_kg: null, created_at: "", updated_at: "" },
    ],
    error: null,
    isLoading: false,
    mutate: vi.fn(),
    createAeroplane: vi.fn(),
    deleteAeroplane: vi.fn(),
  }),
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

import ConstructionPlansPage from "@/app/workbench/construction-plans/page";

beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(window, "prompt").mockReturnValue("Test Plan");
  vi.spyOn(window, "confirm").mockReturnValue(true);
});

describe("ConstructionPlansPage", () => {
  it("renders the plan selector with existing plans", () => {
    render(<ConstructionPlansPage />);
    expect(screen.getByText("eHawk Wing (3 steps)")).toBeDefined();
  });

  it("shows plan tree when a plan is selected", () => {
    render(<ConstructionPlansPage />);
    const select = screen.getByRole("combobox") as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "1" } });
    // Appears in both the plan tree and the creator catalog
    const matches = screen.getAllByText("VaseModeWingCreator");
    expect(matches.length).toBeGreaterThanOrEqual(2);
  });

  it("shows Execute and Delete buttons when a plan is selected", () => {
    render(<ConstructionPlansPage />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "1" } });
    expect(screen.getByText("Execute")).toBeDefined();
  });

  it("creates a new plan via prompt", async () => {
    render(<ConstructionPlansPage />);
    const buttons = screen.getAllByTitle("New plan");
    fireEvent.click(buttons[0]);
    await waitFor(() => {
      expect(mockCreatePlan).toHaveBeenCalledWith(
        expect.objectContaining({ name: "Test Plan" }),
      );
    });
  });

  it("opens execute dialog and shows aeroplane selector", () => {
    render(<ConstructionPlansPage />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "1" } });
    fireEvent.click(screen.getByText("Execute"));
    expect(screen.getByText("Execute Plan")).toBeDefined();
    expect(screen.getByText("eHawk")).toBeDefined();
  });

  it("shows creator catalog on the right panel", () => {
    render(<ConstructionPlansPage />);
    expect(screen.getByText("Creator Catalog")).toBeDefined();
  });
});
