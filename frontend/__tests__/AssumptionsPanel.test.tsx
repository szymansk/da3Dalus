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
    Info: icon,
    Loader2: icon,
    Plus: icon,
  };
});

vi.mock("@/components/workbench/CGComparisonBanner", () => ({
  CGComparisonBanner: ({ aeroplaneId }: { aeroplaneId: string }) =>
    React.createElement("div", { "data-testid": "cg-comparison-banner-mock", "data-aeroplane-id": aeroplaneId }),
}));

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

// gh-603: ctx.is_glider drives whether powertrain groups render.
let ctxReturn: { data: { is_glider?: boolean } | null };

vi.mock("@/hooks/useDesignAssumptions", () => ({
  useDesignAssumptions: () => hookReturn,
}));

vi.mock("@/hooks/useComputationContext", () => ({
  useComputationContext: () => ctxReturn,
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
    // Default: not a glider (all groups visible).
    ctxReturn = { data: { is_glider: false } };
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

  it("renders CGComparisonBanner when assumptions exist", () => {
    hookReturn.data = {
      assumptions: [makeAssumption()],
      warnings_count: 0,
    };

    render(<AssumptionsPanel aeroplaneId="aero-1" />);

    const banner = screen.getByTestId("cg-comparison-banner-mock");
    expect(banner).toBeDefined();
    expect(banner.getAttribute("data-aeroplane-id")).toBe("aero-1");
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
    ctxReturn = { data: { is_glider: false } };
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

// ── gh-603: thematic grouping & glider hiding ─────────────────────

import { ASSUMPTION_GROUPS } from "@/components/workbench/AssumptionsPanel";

const ALL_PARAM_NAMES: Assumption["parameter_name"][] = [
  "mass",
  "cg_x",
  "target_static_margin",
  "g_limit",
  "cl_max",
  "cd0",
  "power_to_weight",
  "prop_efficiency",
  "propulsion_eta_motor",
  "propulsion_eta_esc",
  "motor_continuous_power_w",
  "battery_capacity_wh",
  "battery_specific_energy_wh_per_kg",
  "t_static_N",
];

function makeAllAssumptions(): Assumption[] {
  return ALL_PARAM_NAMES.map((name, idx) =>
    makeAssumption({
      id: idx + 1,
      parameter_name: name,
      // CL_max needs unit "-" so it doesn't get treated as percent.
      unit: name === "target_static_margin" ? "% MAC" : "-",
      effective_value: 0.1,
      estimate_value: 0.1,
    }),
  );
}

describe("AssumptionsPanel — thematic grouping (gh-603)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    ctxReturn = { data: { is_glider: false } };
  });

  it("renders all 6 groups for a non-glider", () => {
    hookReturn = {
      data: { assumptions: makeAllAssumptions(), warnings_count: 0 },
      isLoading: false,
      error: null,
      seedDefaults: mockSeedDefaults,
      updateEstimate: mockUpdateEstimate,
      switchSource: mockSwitchSource,
      mutate: mockMutate,
    };

    const { container } = render(<AssumptionsPanel aeroplaneId="aero-1" />);

    for (const id of [
      "mass_balance",
      "stability",
      "aerodynamics",
      "propulsion",
      "energy",
      "takeoff",
    ]) {
      expect(
        container.querySelector(`[data-testid="assumption-group-${id}"]`),
      ).not.toBeNull();
    }
  });

  it("hides propulsion/energy/takeoff groups when is_glider is true", () => {
    hookReturn = {
      data: { assumptions: makeAllAssumptions(), warnings_count: 0 },
      isLoading: false,
      error: null,
      seedDefaults: mockSeedDefaults,
      updateEstimate: mockUpdateEstimate,
      switchSource: mockSwitchSource,
      mutate: mockMutate,
    };
    ctxReturn = { data: { is_glider: true } };

    const { container } = render(<AssumptionsPanel aeroplaneId="aero-1" />);

    // Always-on groups present.
    expect(
      container.querySelector('[data-testid="assumption-group-mass_balance"]'),
    ).not.toBeNull();
    expect(
      container.querySelector('[data-testid="assumption-group-stability"]'),
    ).not.toBeNull();
    expect(
      container.querySelector('[data-testid="assumption-group-aerodynamics"]'),
    ).not.toBeNull();
    // Powertrain groups hidden.
    expect(
      container.querySelector('[data-testid="assumption-group-propulsion"]'),
    ).toBeNull();
    expect(
      container.querySelector('[data-testid="assumption-group-energy"]'),
    ).toBeNull();
    expect(
      container.querySelector('[data-testid="assumption-group-takeoff"]'),
    ).toBeNull();
  });

  it("renders all 6 groups when ctx.is_glider is undefined (defensive)", () => {
    hookReturn = {
      data: { assumptions: makeAllAssumptions(), warnings_count: 0 },
      isLoading: false,
      error: null,
      seedDefaults: mockSeedDefaults,
      updateEstimate: mockUpdateEstimate,
      switchSource: mockSwitchSource,
      mutate: mockMutate,
    };
    // ctx not yet loaded.
    ctxReturn = { data: null };

    const { container } = render(<AssumptionsPanel aeroplaneId="aero-1" />);

    expect(
      container.querySelector('[data-testid="assumption-group-propulsion"]'),
    ).not.toBeNull();
    expect(
      container.querySelector('[data-testid="assumption-group-energy"]'),
    ).not.toBeNull();
    expect(
      container.querySelector('[data-testid="assumption-group-takeoff"]'),
    ).not.toBeNull();
  });

  it("renders groups in the expected order", () => {
    hookReturn = {
      data: { assumptions: makeAllAssumptions(), warnings_count: 0 },
      isLoading: false,
      error: null,
      seedDefaults: mockSeedDefaults,
      updateEstimate: mockUpdateEstimate,
      switchSource: mockSwitchSource,
      mutate: mockMutate,
    };

    const { container } = render(<AssumptionsPanel aeroplaneId="aero-1" />);

    const ids = Array.from(
      container.querySelectorAll('[data-testid^="assumption-group-"]'),
    ).map((el) => el.getAttribute("data-testid"));

    expect(ids).toEqual([
      "assumption-group-mass_balance",
      "assumption-group-stability",
      "assumption-group-aerodynamics",
      "assumption-group-propulsion",
      "assumption-group-energy",
      "assumption-group-takeoff",
    ]);
  });

  it("skips empty groups (no matching parameters in data)", () => {
    // Provide only mass and cg_x -> only mass_balance should render.
    hookReturn = {
      data: {
        assumptions: [
          makeAssumption({ id: 1, parameter_name: "mass" }),
          makeAssumption({ id: 2, parameter_name: "cg_x", unit: "m" }),
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

    const { container } = render(<AssumptionsPanel aeroplaneId="aero-1" />);

    expect(
      container.querySelector('[data-testid="assumption-group-mass_balance"]'),
    ).not.toBeNull();
    // Other groups have no data → not rendered.
    expect(
      container.querySelector('[data-testid="assumption-group-stability"]'),
    ).toBeNull();
    expect(
      container.querySelector('[data-testid="assumption-group-aerodynamics"]'),
    ).toBeNull();
    expect(
      container.querySelector('[data-testid="assumption-group-propulsion"]'),
    ).toBeNull();
  });

  it("renders group section headers (labels)", () => {
    hookReturn = {
      data: { assumptions: makeAllAssumptions(), warnings_count: 0 },
      isLoading: false,
      error: null,
      seedDefaults: mockSeedDefaults,
      updateEstimate: mockUpdateEstimate,
      switchSource: mockSwitchSource,
      mutate: mockMutate,
    };

    render(<AssumptionsPanel aeroplaneId="aero-1" />);

    expect(screen.getByText("Mass & Balance")).toBeDefined();
    expect(screen.getByText("Stability")).toBeDefined();
    expect(screen.getByText("Aerodynamics")).toBeDefined();
    expect(screen.getByText("Propulsion")).toBeDefined();
    expect(screen.getByText("Energy")).toBeDefined();
    expect(screen.getByText("Takeoff")).toBeDefined();
  });
});

describe("ASSUMPTION_GROUPS table (gh-603)", () => {
  it("contains exactly the 6 expected group ids in order", () => {
    expect(ASSUMPTION_GROUPS.map((g) => g.id)).toEqual([
      "mass_balance",
      "stability",
      "aerodynamics",
      "propulsion",
      "energy",
      "takeoff",
    ]);
  });

  it("covers every VALID_PARAMETERS member exactly once", () => {
    const flat = ASSUMPTION_GROUPS.flatMap((g) => g.params);
    // No duplicates.
    expect(new Set(flat).size).toBe(flat.length);
    // Same set as the backend VALID_PARAMETERS contract.
    expect(new Set(flat)).toEqual(new Set(ALL_PARAM_NAMES));
  });

  it("flags only propulsion/energy/takeoff as hideForGlider", () => {
    const hidden = ASSUMPTION_GROUPS.filter((g) => g.hideForGlider).map(
      (g) => g.id,
    );
    expect(new Set(hidden)).toEqual(
      new Set(["propulsion", "energy", "takeoff"]),
    );
  });
});
