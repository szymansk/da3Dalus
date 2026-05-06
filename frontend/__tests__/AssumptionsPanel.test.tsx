/**
 * Unit tests for AssumptionsPanel and AssumptionRow components (gh-424).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import type { Assumption, AssumptionsSummary } from "@/hooks/useDesignAssumptions";

// ── Mocks ─────────────────────────────────────────────────────────

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    AlertTriangle: icon,
    ArrowLeftRight: icon,
    Loader2: icon,
    Plus: icon,
  };
});

const mockSeedDefaults = vi.fn();
const mockUpdateEstimate = vi.fn();
const mockSwitchSource = vi.fn();
const mockMutate = vi.fn();

let hookReturn: {
  data: AssumptionsSummary | null;
  isLoading: boolean;
  error: Error | null;
  seedDefaults: typeof mockSeedDefaults;
  updateEstimate: typeof mockUpdateEstimate;
  switchSource: typeof mockSwitchSource;
  mutate: typeof mockMutate;
};

vi.mock("@/hooks/useDesignAssumptions", () => ({
  useDesignAssumptions: () => hookReturn,
}));

import { AssumptionsPanel } from "@/components/workbench/AssumptionsPanel";

// ── Test data ─────────────────────────────────────────────────────

function makeAssumption(overrides: Partial<Assumption> = {}): Assumption {
  return {
    id: 1,
    parameter_name: "mass",
    estimate_value: 2.5,
    calculated_value: 2.7,
    calculated_source: "weight_buildup",
    active_source: "ESTIMATE",
    effective_value: 2.5,
    divergence_pct: 8.0,
    divergence_level: "info",
    unit: "kg",
    is_design_choice: false,
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

// ── Tests ─────────────────────────────────────────────────────────

describe("AssumptionsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    hookReturn = {
      data: null,
      isLoading: false,
      error: null,
      seedDefaults: mockSeedDefaults,
      updateEstimate: mockUpdateEstimate,
      switchSource: mockSwitchSource,
      mutate: mockMutate,
    };
  });

  it("shows loading state", () => {
    hookReturn.isLoading = true;

    render(<AssumptionsPanel aeroplaneId="aero-1" />);

    expect(screen.getByText("Loading assumptions...")).toBeDefined();
  });

  it("shows error state", () => {
    hookReturn.error = new Error("Network error");

    render(<AssumptionsPanel aeroplaneId="aero-1" />);

    expect(screen.getByText("Failed to load assumptions")).toBeDefined();
  });

  it("shows seed defaults button when no assumptions exist", () => {
    hookReturn.data = { assumptions: [], warnings_count: 0 };

    render(<AssumptionsPanel aeroplaneId="aero-1" />);

    expect(screen.getByText("No design assumptions yet")).toBeDefined();
    expect(screen.getByTestId("seed-defaults-button")).toBeDefined();
  });

  it("calls seedDefaults when button is clicked", async () => {
    hookReturn.data = { assumptions: [], warnings_count: 0 };
    const user = userEvent.setup();

    render(<AssumptionsPanel aeroplaneId="aero-1" />);

    await user.click(screen.getByTestId("seed-defaults-button"));

    expect(mockSeedDefaults).toHaveBeenCalledOnce();
  });

  it("renders assumption rows when data exists", () => {
    hookReturn.data = {
      assumptions: [
        makeAssumption({ id: 1, parameter_name: "mass" }),
        makeAssumption({ id: 2, parameter_name: "cd0", unit: "-", effective_value: 0.02 }),
      ],
      warnings_count: 0,
    };

    render(<AssumptionsPanel aeroplaneId="aero-1" />);

    expect(screen.getByText("Total Mass")).toBeDefined();
    expect(screen.getByText("Zero-Lift Drag (CD₀)")).toBeDefined();
  });

  it("shows warnings badge when warnings_count > 0", () => {
    hookReturn.data = {
      assumptions: [makeAssumption()],
      warnings_count: 3,
    };

    render(<AssumptionsPanel aeroplaneId="aero-1" />);

    expect(screen.getByTestId("warnings-badge")).toBeDefined();
    expect(screen.getByText("3")).toBeDefined();
  });

  it("does not show warnings badge when warnings_count is 0", () => {
    hookReturn.data = {
      assumptions: [makeAssumption()],
      warnings_count: 0,
    };

    render(<AssumptionsPanel aeroplaneId="aero-1" />);

    expect(screen.queryByTestId("warnings-badge")).toBeNull();
  });
});

describe("AssumptionRow (via AssumptionsPanel)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows design choice badge for design_choice assumptions", () => {
    hookReturn = {
      data: {
        assumptions: [
          makeAssumption({ is_design_choice: true, parameter_name: "target_static_margin" }),
        ],
        warnings_count: 0,
      },
      isLoading: false,
      error: null,
      seedDefaults: mockSeedDefaults,
      updateEstimate: mockUpdateEstimate,
      switchSource: mockSwitchSource,
      mutate: mockMutate,
    };

    render(<AssumptionsPanel aeroplaneId="aero-1" />);

    expect(screen.getByText("design choice")).toBeDefined();
  });

  it("shows calculated badge when active_source is CALCULATED", () => {
    hookReturn = {
      data: {
        assumptions: [
          makeAssumption({ active_source: "CALCULATED" }),
        ],
        warnings_count: 0,
      },
      isLoading: false,
      error: null,
      seedDefaults: mockSeedDefaults,
      updateEstimate: mockUpdateEstimate,
      switchSource: mockSwitchSource,
      mutate: mockMutate,
    };

    render(<AssumptionsPanel aeroplaneId="aero-1" />);

    // The checkmark + calculated text
    expect(screen.getByText(/calculated/)).toBeDefined();
  });

  it("shows estimate badge when active_source is ESTIMATE and not design choice", () => {
    hookReturn = {
      data: {
        assumptions: [
          makeAssumption({ active_source: "ESTIMATE", is_design_choice: false }),
        ],
        warnings_count: 0,
      },
      isLoading: false,
      error: null,
      seedDefaults: mockSeedDefaults,
      updateEstimate: mockUpdateEstimate,
      switchSource: mockSwitchSource,
      mutate: mockMutate,
    };

    render(<AssumptionsPanel aeroplaneId="aero-1" />);

    expect(screen.getByText(/estimate/)).toBeDefined();
  });

  it("shows source toggle button when calculated_value exists and not design_choice", () => {
    hookReturn = {
      data: {
        assumptions: [
          makeAssumption({ calculated_value: 2.7, is_design_choice: false }),
        ],
        warnings_count: 0,
      },
      isLoading: false,
      error: null,
      seedDefaults: mockSeedDefaults,
      updateEstimate: mockUpdateEstimate,
      switchSource: mockSwitchSource,
      mutate: mockMutate,
    };

    render(<AssumptionsPanel aeroplaneId="aero-1" />);

    expect(screen.getByTestId("toggle-source-mass")).toBeDefined();
  });

  it("hides source toggle button when no calculated_value", () => {
    hookReturn = {
      data: {
        assumptions: [
          makeAssumption({ calculated_value: null, is_design_choice: false }),
        ],
        warnings_count: 0,
      },
      isLoading: false,
      error: null,
      seedDefaults: mockSeedDefaults,
      updateEstimate: mockUpdateEstimate,
      switchSource: mockSwitchSource,
      mutate: mockMutate,
    };

    render(<AssumptionsPanel aeroplaneId="aero-1" />);

    expect(screen.queryByTestId("toggle-source-mass")).toBeNull();
  });

  it("hides source toggle button for design choices", () => {
    hookReturn = {
      data: {
        assumptions: [
          makeAssumption({ calculated_value: 2.7, is_design_choice: true }),
        ],
        warnings_count: 0,
      },
      isLoading: false,
      error: null,
      seedDefaults: mockSeedDefaults,
      updateEstimate: mockUpdateEstimate,
      switchSource: mockSwitchSource,
      mutate: mockMutate,
    };

    render(<AssumptionsPanel aeroplaneId="aero-1" />);

    expect(screen.queryByTestId("toggle-source-mass")).toBeNull();
  });

  it("calls switchSource when toggle is clicked", async () => {
    hookReturn = {
      data: {
        assumptions: [
          makeAssumption({
            active_source: "ESTIMATE",
            calculated_value: 2.7,
            is_design_choice: false,
          }),
        ],
        warnings_count: 0,
      },
      isLoading: false,
      error: null,
      seedDefaults: mockSeedDefaults,
      updateEstimate: mockUpdateEstimate,
      switchSource: mockSwitchSource,
      mutate: mockMutate,
    };
    const user = userEvent.setup();

    render(<AssumptionsPanel aeroplaneId="aero-1" />);

    await user.click(screen.getByTestId("toggle-source-mass"));

    expect(mockSwitchSource).toHaveBeenCalledWith("mass", "CALCULATED");
  });

  it("shows divergence info text for info level", () => {
    hookReturn = {
      data: {
        assumptions: [
          makeAssumption({ divergence_level: "info", divergence_pct: 8.0 }),
        ],
        warnings_count: 0,
      },
      isLoading: false,
      error: null,
      seedDefaults: mockSeedDefaults,
      updateEstimate: mockUpdateEstimate,
      switchSource: mockSwitchSource,
      mutate: mockMutate,
    };

    render(<AssumptionsPanel aeroplaneId="aero-1" />);

    expect(screen.getByText("8.0% divergence")).toBeDefined();
  });

  it("shows divergence warning text for warning level", () => {
    hookReturn = {
      data: {
        assumptions: [
          makeAssumption({ divergence_level: "warning", divergence_pct: 15.0 }),
        ],
        warnings_count: 1,
      },
      isLoading: false,
      error: null,
      seedDefaults: mockSeedDefaults,
      updateEstimate: mockUpdateEstimate,
      switchSource: mockSwitchSource,
      mutate: mockMutate,
    };

    render(<AssumptionsPanel aeroplaneId="aero-1" />);

    expect(screen.getByText(/15\.0% divergence — review recommended/)).toBeDefined();
  });

  it("shows divergence alert text for alert level", () => {
    hookReturn = {
      data: {
        assumptions: [
          makeAssumption({ divergence_level: "alert", divergence_pct: 30.0 }),
        ],
        warnings_count: 1,
      },
      isLoading: false,
      error: null,
      seedDefaults: mockSeedDefaults,
      updateEstimate: mockUpdateEstimate,
      switchSource: mockSwitchSource,
      mutate: mockMutate,
    };

    render(<AssumptionsPanel aeroplaneId="aero-1" />);

    expect(screen.getByText(/30\.0% divergence — significant!/)).toBeDefined();
  });

  it("does not show divergence for none level", () => {
    hookReturn = {
      data: {
        assumptions: [
          makeAssumption({ divergence_level: "none", divergence_pct: null }),
        ],
        warnings_count: 0,
      },
      isLoading: false,
      error: null,
      seedDefaults: mockSeedDefaults,
      updateEstimate: mockUpdateEstimate,
      switchSource: mockSwitchSource,
      mutate: mockMutate,
    };

    render(<AssumptionsPanel aeroplaneId="aero-1" />);

    expect(screen.queryByText(/divergence/)).toBeNull();
  });

  it("opens inline editor on click and submits on Enter", async () => {
    hookReturn = {
      data: {
        assumptions: [makeAssumption({ estimate_value: 2.5 })],
        warnings_count: 0,
      },
      isLoading: false,
      error: null,
      seedDefaults: mockSeedDefaults,
      updateEstimate: mockUpdateEstimate,
      switchSource: mockSwitchSource,
      mutate: mockMutate,
    };
    const user = userEvent.setup();

    render(<AssumptionsPanel aeroplaneId="aero-1" />);

    // Click the estimate display to open editor
    await user.click(screen.getByTestId("estimate-display-mass"));

    // Input should appear
    const input = screen.getByTestId("estimate-input-mass") as HTMLInputElement;
    expect(input).toBeDefined();

    // Clear and type new value
    await user.clear(input);
    await user.type(input, "3.0");
    await user.keyboard("{Enter}");

    expect(mockUpdateEstimate).toHaveBeenCalledWith("mass", 3.0);
  });
});
