import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";

// ── Mocks ─────────────────────────────────────────────────────────

vi.mock("lucide-react", async () => {
  const actual = await vi.importActual<Record<string, unknown>>("lucide-react");
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  // Replace every named export with our stub so that adding new lucide
  // icons in production code never breaks this mock.
  return Object.fromEntries(Object.keys(actual).map((k) => [k, icon]));
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

const mockMutateAeroplanePlans = vi.fn();
const mockInstantiateTemplate = vi.fn().mockResolvedValue({ id: 10, name: "Instantiated" });
const mockToTemplate = vi.fn().mockResolvedValue({ id: 11, name: "Saved Template" });
const mockExecuteStreamUrl = vi.fn(
  (aeroplaneId: string, planId: number) =>
    `http://localhost:8000/aeroplanes/${aeroplaneId}/construction-plans/${planId}/execute-stream`,
);

vi.mock("@/hooks/useConstructionPlans", () => ({
  useConstructionPlans: () => ({
    plans: [
      { id: 1, name: "eHawk Wing", description: null, step_count: 3, plan_type: "template", aeroplane_id: null, created_at: "2026-01-01" },
    ],
    error: null,
    isLoading: false,
    mutate: mockMutatePlans,
  }),
  useAeroplanePlans: () => ({
    plans: [
      { id: 2, name: "eHawk Build", description: null, step_count: 2, plan_type: "plan", aeroplane_id: "aero-1", created_at: "2026-01-01" },
    ],
    error: null,
    isLoading: false,
    mutate: mockMutateAeroplanePlans,
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
            loglevel: 50,
            successors: {
              VaseModeWingCreator: {
                $TYPE: "ConstructionStepNode",
                creator_id: "VaseModeWingCreator",
                loglevel: 50,
                creator: { $TYPE: "VaseModeWingCreator", creator_id: "VaseModeWingCreator", wing_index: "main_wing", loglevel: 50 },
                successors: {},
              },
            },
          },
          plan_type: "template",
          aeroplane_id: null,
          created_at: "2026-01-01",
          updated_at: "2026-01-01",
        }
      : id === 2
      ? {
          id: 2,
          name: "eHawk Build",
          description: null,
          tree_json: {
            $TYPE: "ConstructionRootNode",
            creator_id: "root",
            loglevel: 50,
            successors: {
              VaseModeWingCreator: {
                $TYPE: "ConstructionStepNode",
                creator_id: "VaseModeWingCreator",
                loglevel: 50,
                creator: { $TYPE: "VaseModeWingCreator", creator_id: "VaseModeWingCreator", wing_index: "main_wing", loglevel: 50 },
                successors: {},
              },
            },
          },
          plan_type: "plan",
          aeroplane_id: "aero-1",
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
  instantiateTemplate: (...args: unknown[]) => mockInstantiateTemplate(...args),
  toTemplate: (...args: unknown[]) => mockToTemplate(...args),
  // Artifact-browser surface (gh-320, gh-339) — stubbed to keep the page renderable.
  usePlanArtifacts: () => ({ executions: [], error: null, isLoading: false, mutate: vi.fn() }),
  useArtifactFiles: () => ({ files: [], error: null, isLoading: false, mutate: vi.fn() }),
  deleteArtifactFile: vi.fn().mockResolvedValue(undefined),
  deleteExecution: vi.fn().mockResolvedValue(undefined),
  artifactDownloadUrl: (planId: number, execId: string, filename: string) =>
    `http://localhost:8000/construction-plans/${planId}/artifacts/${execId}/${filename}`,
  executionZipUrl: (planId: number, execId: string) =>
    `http://localhost:8000/construction-plans/${planId}/artifacts/${execId}/zip`,
  executeStreamUrl: (...args: [string, number]) => mockExecuteStreamUrl(...args),
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

// jsdom does not implement EventSource. Stub it so that ExecutionResultDialog
// can mount with a streamUrl prop without throwing.
class FakeEventSource {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSED = 2;
  readyState = FakeEventSource.CONNECTING;
  url: string;
  constructor(url: string) {
    this.url = url;
  }
  addEventListener() {}
  removeEventListener() {}
  close() {
    this.readyState = FakeEventSource.CLOSED;
  }
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(window, "prompt").mockReturnValue("Test Plan");
  vi.spyOn(window, "confirm").mockReturnValue(true);
  vi.stubGlobal("EventSource", FakeEventSource);
});

// Tests target the post-gh-323 UI: TemplateModePanel + TemplateSelector
// (rich combobox) and PlanTreeSection (per-plan icon-button toolbar).
// User-journey style — render the page, drive interactions, assert visible
// elements via labels/titles.
describe("ConstructionPlansPage", () => {
  it("renders the template/plans toggle", () => {
    render(<ConstructionPlansPage />);
    expect(screen.getByText("Templates")).toBeDefined();
    expect(screen.getByText("Plans")).toBeDefined();
  });

  it("defaults to plans mode and shows the aeroplane's plan", async () => {
    render(<ConstructionPlansPage />);
    // Plans mode is the default. The PlanTreeSection renders the plan
    // name via InlineEditableName as a <span>, plus a "(2)" step counter.
    await waitFor(() => {
      expect(screen.getByText("eHawk Build")).toBeDefined();
    });
    // Step counter rendered next to the name (gh-323 PlanTreeSection)
    expect(screen.getByText("(2)")).toBeDefined();
  });

  it("shows the plan tree when the auto-selected plan is loaded", async () => {
    render(<ConstructionPlansPage />);
    // The first plan is auto-expanded via useEffect (page.tsx). Once
    // the active plan detail is loaded, renderCreatorTree displays
    // each step's creator_id as the row label. The same identifier
    // also appears as a parameter label inside the row's add/edit
    // tooltips, so multiple matches are expected.
    await waitFor(() => {
      const matches = screen.getAllByText("VaseModeWingCreator");
      // Renders at least twice: once as the row label in renderCreatorTree
      // and once as the parameter description in the row's add/edit tooltip.
      // Catches a regression where the tooltip parameter label disappears.
      expect(matches.length).toBeGreaterThanOrEqual(2);
    });
  });

  it("shows template-specific actions after selecting a template in template mode", async () => {
    render(<ConstructionPlansPage />);
    fireEvent.click(screen.getByText("Templates"));
    // Open the TemplateSelector dropdown and click "eHawk Wing"
    fireEvent.click(screen.getByRole("combobox"));
    fireEvent.click(screen.getByText("eHawk Wing"));
    // After selection, the TemplateModePanel renders the template-specific
    // toolbar: "Execute template against an aeroplane" (Play),
    // "Delete eHawk Wing" (Trash), and "Add step to eHawk Wing" (Plus).
    await waitFor(() => {
      expect(screen.getByTitle("Execute template against an aeroplane")).toBeDefined();
    });
    expect(screen.getByTitle("Add step to eHawk Wing")).toBeDefined();
    // The plan-mode-only "Execute eHawk Build" button must not appear
    // in template mode (the plan list is hidden).
    expect(screen.queryByTitle("Execute eHawk Build")).toBeNull();
  });

  it("shows the Execute action for each plan in plans mode", async () => {
    render(<ConstructionPlansPage />);
    // Default mode is plans — first plan auto-expands. PlanTreeSection
    // renders an icon Play button with title="Execute eHawk Build" and
    // the TreeCard renders a header-level "Execute all plans" button.
    await waitFor(() => {
      expect(screen.getByTitle("Execute eHawk Build")).toBeDefined();
    });
    expect(screen.getByTitle("Execute all plans")).toBeDefined();
  });

  it("creates a new plan via NewPlanDialog when '+' is clicked in plans mode", async () => {
    render(<ConstructionPlansPage />);
    // The TreeCard "+" header button (title="Create new plan") opens
    // NewPlanDialog. The dialog offers an "Empty plan" choice that
    // delegates to handleCreateEmptyPlan → createPlan({plan_type: "plan"}).
    fireEvent.click(screen.getByTitle("Create new plan"));
    // Dialog renders with aria-label="Create new plan"
    const dialog = await screen.findByRole("dialog", { name: "Create new plan" });
    expect(dialog).toBeDefined();
    fireEvent.click(screen.getByText("Empty plan"));
    await waitFor(() => {
      expect(mockCreatePlan).toHaveBeenCalledWith(
        expect.objectContaining({ plan_type: "plan", aeroplane_id: "aero-1" }),
      );
    });
  });

  it("opens AeroplanePickerDialog when executing a template", async () => {
    render(<ConstructionPlansPage />);
    fireEvent.click(screen.getByText("Templates"));
    fireEvent.click(screen.getByRole("combobox"));
    fireEvent.click(screen.getByText("eHawk Wing"));
    // Click "Execute template against an aeroplane" — opens
    // AeroplanePickerDialog (gh-323).
    fireEvent.click(
      await screen.findByTitle("Execute template against an aeroplane"),
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Select aeroplane to execute against",
    });
    expect(dialog).toBeDefined();
    // Aeroplane list is rendered inside the dialog
    expect(screen.getByText("eHawk")).toBeDefined();
  });

  it("shows creator catalog on the right panel", () => {
    render(<ConstructionPlansPage />);
    expect(screen.getByText("Creator Catalog")).toBeDefined();
  });

  it("shows Save-as-template action for each plan in plans mode", async () => {
    render(<ConstructionPlansPage />);
    // Plans mode is the default. Each plan row in PlanTreeSection
    // renders a BookTemplate icon button with
    // title="Save <plan-name> as template" that calls toTemplate(...).
    await waitFor(() => {
      expect(screen.getByTitle("Save eHawk Build as template")).toBeDefined();
    });
  });

  it("starts streaming execution when Execute is clicked in plans mode", async () => {
    render(<ConstructionPlansPage />);
    // Plans mode is the default. Clicking the per-plan Play icon
    // (title="Execute <plan-name>") triggers handleExecutePlan which
    // builds a streaming URL via executeStreamUrl(aeroplaneId, planId)
    // and opens the ExecutionResultDialog with that streamUrl.
    const executeButton = await screen.findByTitle("Execute eHawk Build");
    fireEvent.click(executeButton);

    // The contract: the page asks for the streaming URL with the
    // active aeroplane id and the clicked plan id.
    await waitFor(() => {
      expect(mockExecuteStreamUrl).toHaveBeenCalledWith("aero-1", 2);
    });
  });
});
