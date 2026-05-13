import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";

// Mock SWR and hooks before component import
vi.mock("@/hooks/useLoadingScenarios", async () => {
  const actual = await vi.importActual("@/hooks/useLoadingScenarios");
  return {
    ...actual,
    useLoadingScenarios: vi.fn(),
    useCgEnvelope: vi.fn(),
    useLoadingScenarioTemplates: vi.fn(),
  };
});

import { LoadingScenariosCard } from "@/components/workbench/LoadingScenariosCard";
import {
  useLoadingScenarios,
  useCgEnvelope,
  useLoadingScenarioTemplates,
} from "@/hooks/useLoadingScenarios";

const MOCK_SCENARIO = {
  id: 1,
  aeroplane_id: 42,
  name: "Battery Forward",
  aircraft_class: "rc_trainer" as const,
  component_overrides: {
    toggles: [],
    mass_overrides: [],
    position_overrides: [],
    adhoc_items: [
      {
        name: "Battery",
        mass_kg: 0.2,
        x_m: 0.05,
        y_m: 0,
        z_m: 0,
        category: "payload" as const,
      },
    ],
  },
  is_default: false,
};

const MOCK_ENVELOPE_OK = {
  cg_loading_fwd_m: 0.13,
  cg_loading_aft_m: 0.17,
  cg_stability_fwd_m: 0.10,
  cg_stability_aft_m: 0.22,
  sm_at_fwd: 0.10,
  sm_at_aft: 0.06,
  classification: "ok" as const,
  warnings: [],
};

const MOCK_ENVELOPE_WARN = {
  ...MOCK_ENVELOPE_OK,
  sm_at_fwd: 0.03,
  sm_at_aft: 0.01,
  classification: "warn" as const,
  warnings: ["CG exceeds aft stability limit by 15 mm."],
};

const MOCK_ENVELOPE_ERROR = {
  ...MOCK_ENVELOPE_OK,
  sm_at_fwd: 0.01,
  sm_at_aft: -0.01,
  classification: "error" as const,
  warnings: ["SM at aft CG = -1.0% — outside safe operating range."],
};

function setupMocks(opts: {
  scenarios?: typeof MOCK_SCENARIO[];
  envelope?: typeof MOCK_ENVELOPE_OK | typeof MOCK_ENVELOPE_WARN | typeof MOCK_ENVELOPE_ERROR | null;
  templates?: { name: string; component_overrides: (typeof MOCK_SCENARIO)["component_overrides"]; is_default: boolean }[];
}) {
  const createScenario = vi.fn();
  const deleteScenario = vi.fn();

  (useLoadingScenarios as ReturnType<typeof vi.fn>).mockReturnValue({
    scenarios: opts.scenarios ?? [],
    isLoading: false,
    error: null,
    mutate: vi.fn(),
    createScenario,
    updateScenario: vi.fn(),
    deleteScenario,
  });

  (useCgEnvelope as ReturnType<typeof vi.fn>).mockReturnValue({
    envelope: opts.envelope ?? null,
    isLoading: false,
    error: null,
    mutate: vi.fn(),
  });

  (useLoadingScenarioTemplates as ReturnType<typeof vi.fn>).mockReturnValue({
    templates: opts.templates ?? [
      {
        name: "Empty",
        component_overrides: { toggles: [], mass_overrides: [], position_overrides: [], adhoc_items: [] },
        is_default: true,
      },
    ],
    isLoading: false,
    error: null,
  });

  return { createScenario, deleteScenario };
}

describe("LoadingScenariosCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders card header with scenario count", () => {
    setupMocks({ scenarios: [MOCK_SCENARIO] });
    render(<LoadingScenariosCard aeroplaneId="test-id" />);

    expect(screen.getByTestId("loading-scenarios-card")).toBeInTheDocument();
    expect(screen.getByText(/1 scenario/i)).toBeInTheDocument();
  });

  it("shows CG envelope chip with SM values when envelope is available", () => {
    setupMocks({ envelope: MOCK_ENVELOPE_OK });
    render(<LoadingScenariosCard aeroplaneId="test-id" />);

    const chip = screen.getByTestId("cg-envelope-chip");
    expect(chip).toBeInTheDocument();
    // SM = 10.0% (fwd) ... 6.0% (aft)
    expect(chip).toHaveTextContent(/10\.0%.*fwd/i);
    expect(chip).toHaveTextContent(/6\.0%.*aft/i);
  });

  it("applies green colour for OK classification", () => {
    setupMocks({ envelope: MOCK_ENVELOPE_OK });
    render(<LoadingScenariosCard aeroplaneId="test-id" />);
    const chip = screen.getByTestId("cg-envelope-chip");
    expect(chip.className).toContain("green");
  });

  it("applies orange colour for WARN classification", () => {
    setupMocks({ envelope: MOCK_ENVELOPE_WARN });
    render(<LoadingScenariosCard aeroplaneId="test-id" />);
    const chip = screen.getByTestId("cg-envelope-chip");
    expect(chip.className).toContain("orange");
  });

  it("applies red colour for ERROR classification", () => {
    setupMocks({ envelope: MOCK_ENVELOPE_ERROR });
    render(<LoadingScenariosCard aeroplaneId="test-id" />);
    const chip = screen.getByTestId("cg-envelope-chip");
    expect(chip.className).toContain("red");
  });

  it("shows validation warnings when present", () => {
    setupMocks({ envelope: MOCK_ENVELOPE_WARN });
    render(<LoadingScenariosCard aeroplaneId="test-id" />);
    expect(
      screen.getByText(/exceeds aft stability limit/i),
    ).toBeInTheDocument();
  });

  it("does not show warnings when envelope is OK", () => {
    setupMocks({ envelope: MOCK_ENVELOPE_OK });
    render(<LoadingScenariosCard aeroplaneId="test-id" />);
    expect(screen.queryByText(/exceeds/i)).not.toBeInTheDocument();
  });

  it("expands to show scenarios on header click", () => {
    setupMocks({ scenarios: [MOCK_SCENARIO] });
    render(<LoadingScenariosCard aeroplaneId="test-id" />);

    fireEvent.click(screen.getByTestId("loading-scenarios-header"));

    expect(screen.getByTestId("scenario-row")).toBeInTheDocument();
    expect(screen.getByText("Battery Forward")).toBeInTheDocument();
  });

  it("shows adhoc item count on scenario row", () => {
    setupMocks({ scenarios: [MOCK_SCENARIO] });
    render(<LoadingScenariosCard aeroplaneId="test-id" />);
    fireEvent.click(screen.getByTestId("loading-scenarios-header"));

    expect(screen.getByText(/1 adhoc item/i)).toBeInTheDocument();
  });

  it("marks default scenario with badge", () => {
    const defaultScenario = { ...MOCK_SCENARIO, is_default: true };
    setupMocks({ scenarios: [defaultScenario] });
    render(<LoadingScenariosCard aeroplaneId="test-id" />);
    fireEvent.click(screen.getByTestId("loading-scenarios-header"));

    expect(screen.getByText("default")).toBeInTheDocument();
  });

  it("calls deleteScenario when delete button is clicked", async () => {
    const { deleteScenario } = setupMocks({ scenarios: [MOCK_SCENARIO] });
    render(<LoadingScenariosCard aeroplaneId="test-id" />);
    fireEvent.click(screen.getByTestId("loading-scenarios-header"));

    const deleteBtn = screen.getByTestId("delete-scenario-button");
    fireEvent.click(deleteBtn);

    await waitFor(() => {
      expect(deleteScenario).toHaveBeenCalledWith(MOCK_SCENARIO.id);
    });
  });

  it("shows Add scenario button when expanded", () => {
    setupMocks({});
    render(<LoadingScenariosCard aeroplaneId="test-id" />);
    fireEvent.click(screen.getByTestId("loading-scenarios-header"));

    expect(screen.getByTestId("add-scenario-button")).toBeInTheDocument();
  });

  it("shows add form with template picker on Add click", () => {
    setupMocks({});
    render(<LoadingScenariosCard aeroplaneId="test-id" />);
    fireEvent.click(screen.getByTestId("loading-scenarios-header"));
    fireEvent.click(screen.getByTestId("add-scenario-button"));

    expect(screen.getByTestId("scenario-name-input")).toBeInTheDocument();
    expect(screen.getByText("Empty")).toBeInTheDocument(); // template button
  });

  it("calls createScenario with template data on template click", async () => {
    const { createScenario } = setupMocks({});
    render(<LoadingScenariosCard aeroplaneId="test-id" />);
    fireEvent.click(screen.getByTestId("loading-scenarios-header"));
    fireEvent.click(screen.getByTestId("add-scenario-button"));

    // Click the "Empty" template button
    fireEvent.click(screen.getByText("Empty"));

    await waitFor(() => {
      expect(createScenario).toHaveBeenCalledWith(
        expect.objectContaining({ name: "Empty" }),
      );
    });
  });

  it("shows aircraft class selector when expanded", () => {
    setupMocks({});
    render(<LoadingScenariosCard aeroplaneId="test-id" />);
    fireEvent.click(screen.getByTestId("loading-scenarios-header"));

    expect(screen.getByTestId("aircraft-class-select")).toBeInTheDocument();
  });

  it("shows empty state message when no scenarios", () => {
    setupMocks({ scenarios: [] });
    render(<LoadingScenariosCard aeroplaneId="test-id" />);
    fireEvent.click(screen.getByTestId("loading-scenarios-header"));

    expect(
      screen.getByText(/no scenarios yet/i),
    ).toBeInTheDocument();
  });
});
