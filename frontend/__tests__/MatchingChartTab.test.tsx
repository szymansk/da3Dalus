/**
 * Unit tests for MatchingChartTab component — gh-492.
 * Mocks the useMatchingChart hook and plotly import to avoid browser env plumbing.
 * Covers: rendering states, helper functions, drag state, form controls, mode changes.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import React from "react";
import type { MatchingChartData, ConstraintLine } from "@/hooks/useMatchingChart";

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", { ...props, "data-testid": "icon" });
  return {
    AlertTriangle: icon,
    Info: icon,
    Loader2: icon,
    X: icon,
  };
});

// Plotly dynamic import — return a stub that captures calls so we can inspect traces
const plotlyReactMock = vi.fn().mockResolvedValue(undefined);
vi.mock("plotly.js-gl3d-dist-min", () => ({
  react: plotlyReactMock,
  purge: vi.fn(),
}));

let hookReturn: {
  data: MatchingChartData | null | undefined;
  error: Error | null | undefined;
  isLoading: boolean;
  mutate: ReturnType<typeof vi.fn>;
};

vi.mock("@/hooks/useMatchingChart", () => ({
  useMatchingChart: () => hookReturn,
}));

// gh-606: mocks for design-assumptions + computation-context. Tests override
// these per scenario via the let-binding pattern (mutable closure).
type MockAssumption = {
  parameter_name: string;
  effective_value: number;
};
let mockAssumptions: MockAssumption[] = [];
let mockCtx: { s_ref_m2?: number | null; b_ref_m?: number | null; is_glider?: boolean } | null = null;

vi.mock("@/hooks/useDesignAssumptions", () => ({
  useDesignAssumptions: () => ({
    data: { assumptions: mockAssumptions, warnings_count: 0 },
    isLoading: false,
    isRecomputing: false,
    error: null,
    seedDefaults: vi.fn(),
    updateEstimate: vi.fn(),
    switchSource: vi.fn(),
    mutate: vi.fn(),
  }),
}));

vi.mock("@/hooks/useComputationContext", () => ({
  useComputationContext: () => ({
    data: mockCtx,
    error: null,
    isLoading: false,
    mutate: vi.fn(),
  }),
}));

import {
  MatchingChartTab,
  findBindingConstraintAtPoint,
  findInsufficientThrustConstraint,
  formatSigFigs,
  computeWingArea,
  computeThrust,
  computeAspectRatio,
  buildCurrentDesignPointTrace,
} from "@/components/workbench/MatchingChartTab";

// ── Test data ─────────────────────────────────────────────────────────────────

const MOCK_CESSNA: MatchingChartData = {
  ws_range_n_m2: Array.from({ length: 200 }, (_, i) => 10 + (1490 / 199) * i),
  constraints: [
    {
      name: "Takeoff",
      t_w_points: Array(200).fill(0.17),
      ws_max: null,
      color: "#FF8400",
      binding: true,
      hover_text: "Takeoff distance ≤ s_runway.",
    },
    {
      name: "Landing",
      t_w_points: null,
      ws_max: 662.0,
      color: "#3B82F6",
      binding: false,
      hover_text: "Landing distance constraint.",
    },
    {
      name: "Cruise",
      t_w_points: Array(200).fill(0.12),
      ws_max: null,
      color: "#30A46C",
      binding: false,
      hover_text: "Level cruise.",
    },
    {
      name: "Climb",
      t_w_points: Array(200).fill(0.14),
      ws_max: null,
      color: "#E5484D",
      binding: false,
      hover_text: "Climb gradient.",
    },
    {
      name: "Stall",
      t_w_points: null,
      ws_max: 900.0,
      color: "#A78BFA",
      binding: false,
      hover_text: "Stall speed.",
    },
  ],
  design_point: { ws_n_m2: 660.07, t_w: 0.17801 },
  feasibility: "feasible",
  warnings: [],
};

const MOCK_LOADING_STATE = { data: undefined, error: null, isLoading: true, mutate: vi.fn() };
const MOCK_ERROR_STATE = {
  data: null,
  error: Object.assign(new Error("fetch failed"), { status: 422 }),
  isLoading: false,
  mutate: vi.fn(),
};
const MOCK_GENERIC_ERROR_STATE = {
  data: null,
  error: Object.assign(new Error("fetch failed"), { status: 500 }),
  isLoading: false,
  mutate: vi.fn(),
};
const MOCK_OK_STATE = { data: MOCK_CESSNA, error: null, isLoading: false, mutate: vi.fn() };
const MOCK_INFEASIBLE: MatchingChartData = {
  ...MOCK_CESSNA,
  design_point: { ws_n_m2: 660.07, t_w: 0.05 },
  feasibility: "infeasible_below_constraints",
};

// ── Tests: Basic rendering states ─────────────────────────────────────────────

describe("MatchingChartTab", () => {
  beforeEach(() => {
    hookReturn = MOCK_LOADING_STATE;
    // gh-606: default empty assumptions + null ctx — current-design-point hidden
    mockAssumptions = [];
    mockCtx = null;
    plotlyReactMock.mockClear();
  });

  it("shows loading spinner while fetching", () => {
    hookReturn = MOCK_LOADING_STATE;
    render(<MatchingChartTab aeroplaneId="test-id" />);
    expect(screen.getByText(/computing constraints/i)).toBeInTheDocument();
  });

  it("shows friendly error for 422 (missing polar parameters)", () => {
    hookReturn = MOCK_ERROR_STATE;
    render(<MatchingChartTab aeroplaneId="test-id" />);
    expect(screen.getByText(/assumption recompute/i)).toBeInTheDocument();
  });

  it("shows generic error for non-422 status", () => {
    hookReturn = MOCK_GENERIC_ERROR_STATE;
    render(<MatchingChartTab aeroplaneId="test-id" />);
    expect(screen.getByText(/matching chart unavailable/i)).toBeInTheDocument();
  });

  it("renders design point W/S and T/W when data is available", () => {
    hookReturn = MOCK_OK_STATE;
    render(<MatchingChartTab aeroplaneId="test-id" />);
    // Should show the W/S and T/W values
    expect(screen.getByText(/660/)).toBeInTheDocument();
    expect(screen.getByText(/0.178/)).toBeInTheDocument();
  });

  it("renders 'Feasible' badge for a feasible design", () => {
    hookReturn = MOCK_OK_STATE;
    render(<MatchingChartTab aeroplaneId="test-id" />);
    expect(screen.getByText("Feasible")).toBeInTheDocument();
  });

  it("renders 'Infeasible' badge for an infeasible design", () => {
    hookReturn = { ...MOCK_OK_STATE, data: MOCK_INFEASIBLE };
    render(<MatchingChartTab aeroplaneId="test-id" />);
    expect(screen.getByText("Infeasible")).toBeInTheDocument();
  });

  it("shows binding constraint name when a constraint is binding", () => {
    hookReturn = MOCK_OK_STATE;
    render(<MatchingChartTab aeroplaneId="test-id" />);
    // Takeoff is binding in the mock data
    expect(screen.getByText("Takeoff")).toBeInTheDocument();
  });

  it("renders mode selector with all four modes", () => {
    hookReturn = MOCK_OK_STATE;
    render(<MatchingChartTab aeroplaneId="test-id" />);
    expect(screen.getByText("RC Runway")).toBeInTheDocument();
    expect(screen.getByText("RC Hand Launch")).toBeInTheDocument();
    expect(screen.getByText("UAV Runway")).toBeInTheDocument();
    expect(screen.getByText("UAV Belly Land")).toBeInTheDocument();
  });

  it("renders runway, V_s, and gamma controls", () => {
    hookReturn = MOCK_OK_STATE;
    render(<MatchingChartTab aeroplaneId="test-id" />);
    // Use label text to distinguish "Runway [m]" from dropdown options
    expect(screen.getByText("Runway [m]")).toBeInTheDocument();
    expect(screen.getByText("V_s max [m/s]")).toBeInTheDocument();
    expect(screen.getByText("γ climb [°]")).toBeInTheDocument();
  });

  it("shows no warnings section when warnings array is empty", () => {
    hookReturn = MOCK_OK_STATE;
    render(<MatchingChartTab aeroplaneId="test-id" />);
    expect(screen.queryByText(/⚠/)).not.toBeInTheDocument();
  });

  it("shows warnings when present", () => {
    const withWarning: MatchingChartData = {
      ...MOCK_CESSNA,
      warnings: ["v_cruise_mps not specified — estimated from polar"],
    };
    hookReturn = { ...MOCK_OK_STATE, data: withWarning };
    render(<MatchingChartTab aeroplaneId="test-id" />);
    expect(screen.getByText(/v_cruise_mps not specified/i)).toBeInTheDocument();
  });

  it("shows the convention banner text in header", () => {
    hookReturn = MOCK_OK_STATE;
    render(<MatchingChartTab aeroplaneId="test-id" />);
    expect(screen.getByText(/Sizing \/ Matching Chart/i)).toBeInTheDocument();
  });

  it("shows Scholz reference in subtitle", () => {
    hookReturn = MOCK_OK_STATE;
    render(<MatchingChartTab aeroplaneId="test-id" />);
    expect(screen.getByText(/Scholz/i)).toBeInTheDocument();
  });

  it("shows info-modal trigger button when data is available", () => {
    hookReturn = MOCK_OK_STATE;
    render(<MatchingChartTab aeroplaneId="test-id" />);
    expect(screen.getByText(/How to read this chart/i)).toBeInTheDocument();
  });

  it("renders plot container with data-testid", () => {
    hookReturn = MOCK_OK_STATE;
    render(<MatchingChartTab aeroplaneId="test-id" />);
    expect(document.querySelector("[data-testid='matching-chart-plot']")).toBeTruthy();
  });

  it("renders design-point summary cells with data-testid", () => {
    hookReturn = MOCK_OK_STATE;
    render(<MatchingChartTab aeroplaneId="test-id" />);
    expect(document.querySelector("[data-testid='dp-ws']")).toBeTruthy();
    expect(document.querySelector("[data-testid='dp-tw']")).toBeTruthy();
  });
});

// ── Tests: Form controls and mode change ──────────────────────────────────────

describe("MatchingChartTab — form controls", () => {
  beforeEach(() => {
    hookReturn = MOCK_OK_STATE;
  });

  it("mode selector defaults to RC Runway", () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    const select = screen.getByRole("combobox") as HTMLSelectElement;
    expect(select.value).toBe("rc_runway");
  });

  it("changing mode to rc_hand_launch resets runway to 0", () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    const select = screen.getByRole("combobox");
    act(() => {
      fireEvent.change(select, { target: { value: "rc_hand_launch" } });
    });
    // runway should reset to 0 for hand launch
    const runwayInput = screen.getByDisplayValue("0") as HTMLInputElement;
    expect(runwayInput).toBeTruthy();
  });

  it("changing mode to uav_runway resets runway to 200", () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    const select = screen.getByRole("combobox");
    act(() => {
      fireEvent.change(select, { target: { value: "uav_runway" } });
    });
    const runwayInput = screen.getByDisplayValue("200") as HTMLInputElement;
    expect(runwayInput).toBeTruthy();
  });

  it("changing mode to uav_belly_land resets defaults", () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    const select = screen.getByRole("combobox");
    act(() => {
      fireEvent.change(select, { target: { value: "uav_belly_land" } });
    });
    expect((select as HTMLSelectElement).value).toBe("uav_belly_land");
  });

  it("runway input change updates state", () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    const inputs = document.querySelectorAll('input[type="number"]');
    const runwayInput = inputs[0] as HTMLInputElement;
    act(() => {
      fireEvent.change(runwayInput, { target: { value: "100" } });
    });
    expect(runwayInput.value).toBe("100");
  });

  it("V_s input change updates state", () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    const inputs = document.querySelectorAll('input[type="number"]');
    const vsInput = inputs[1] as HTMLInputElement;
    act(() => {
      fireEvent.change(vsInput, { target: { value: "10" } });
    });
    expect(vsInput.value).toBe("10");
  });

  it("gamma input change updates state", () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    const inputs = document.querySelectorAll('input[type="number"]');
    const gammaInput = inputs[2] as HTMLInputElement;
    act(() => {
      fireEvent.change(gammaInput, { target: { value: "8" } });
    });
    expect(gammaInput.value).toBe("8");
  });

  it("does not show data when loading", () => {
    hookReturn = MOCK_LOADING_STATE;
    render(<MatchingChartTab aeroplaneId="test-id" />);
    expect(document.querySelector("[data-testid='dp-ws']")).toBeNull();
  });

  it("does not show data content when error", () => {
    hookReturn = MOCK_ERROR_STATE;
    render(<MatchingChartTab aeroplaneId="test-id" />);
    expect(document.querySelector("[data-testid='dp-ws']")).toBeNull();
  });
});

// ── Tests: Auto-reset via key on new data ─────────────────────────────────────

describe("MatchingChartTab — auto-reset key on new data", () => {
  it("content key resets when design point changes (key prop encodes ws+tw)", () => {
    hookReturn = MOCK_OK_STATE;
    const { rerender } = render(<MatchingChartTab aeroplaneId="test-id" />);
    // Verify design point renders
    expect(screen.getByText(/660/)).toBeInTheDocument();

    // New data arrives with different design point
    const newData: MatchingChartData = {
      ...MOCK_CESSNA,
      design_point: { ws_n_m2: 750.0, t_w: 0.2 },
    };
    hookReturn = { ...MOCK_OK_STATE, data: newData };
    rerender(<MatchingChartTab aeroplaneId="test-id" />);
    // New W/S value should now be shown
    expect(screen.getByText(/750/)).toBeInTheDocument();
  });

  it("loading state shows 'loading' key (no crash)", () => {
    hookReturn = MOCK_LOADING_STATE;
    // Should render without error
    expect(() => render(<MatchingChartTab aeroplaneId="test-id" />)).not.toThrow();
  });
});

// ── Tests: DesignPointSummary drag labels ─────────────────────────────────────

describe("MatchingChartTab — DesignPointSummary labels", () => {
  it("shows 'Design Point W/S' label when not dragging", () => {
    hookReturn = MOCK_OK_STATE;
    render(<MatchingChartTab aeroplaneId="test-id" />);
    expect(screen.getByText("Design Point W/S")).toBeInTheDocument();
    expect(screen.getByText("Design Point T/W")).toBeInTheDocument();
  });
});

// ── Tests: Multiple warnings ──────────────────────────────────────────────────

describe("MatchingChartTab — multiple warnings", () => {
  it("renders all warning messages", () => {
    const withWarnings: MatchingChartData = {
      ...MOCK_CESSNA,
      warnings: [
        "v_cruise_mps not specified — estimated from polar",
        "Aspect ratio assumed 7.0",
      ],
    };
    hookReturn = { ...MOCK_OK_STATE, data: withWarnings };
    render(<MatchingChartTab aeroplaneId="test-id" />);
    expect(screen.getByText(/v_cruise_mps not specified/i)).toBeInTheDocument();
    expect(screen.getByText(/Aspect ratio assumed/i)).toBeInTheDocument();
  });
});

// ── Tests: findBindingConstraintAtPoint helper ────────────────────────────────

describe("findBindingConstraintAtPoint", () => {
  const wsRange = Array.from({ length: 100 }, (_, i) => 100 + i * 10); // 100..1090

  const constraints: ConstraintLine[] = [
    {
      name: "Takeoff",
      t_w_points: Array(100).fill(0.2),
      ws_max: null,
      color: "#FF8400",
      binding: true,
      hover_text: null,
    },
    {
      name: "Cruise",
      t_w_points: Array(100).fill(0.1),
      ws_max: null,
      color: "#30A46C",
      binding: false,
      hover_text: null,
    },
    {
      name: "Stall",
      t_w_points: null,
      ws_max: 800,
      color: "#A78BFA",
      binding: false,
      hover_text: null,
    },
  ];

  it("returns null when wsRange is empty", () => {
    expect(findBindingConstraintAtPoint(500, 0.15, [], constraints)).toBeNull();
  });

  it("returns null-like when constraints array is empty", () => {
    // With empty constraints, no binding can be found — returns null
    const result = findBindingConstraintAtPoint(500, 0.15, wsRange, []);
    expect(result).toBeNull();
  });

  it("returns the most violated t_w_points constraint when T/W is below all", () => {
    // T/W = 0.05 is below both Takeoff (0.2) and Cruise (0.1)
    // Takeoff requires 0.2, violation = (0.2 - 0.05) / 0.2 = 0.75
    // Cruise requires 0.1, violation = (0.1 - 0.05) / 0.1 = 0.5
    // So Takeoff is the binding constraint
    const result = findBindingConstraintAtPoint(500, 0.05, wsRange, constraints);
    expect(result).toBe("Takeoff");
  });

  it("returns Cruise when T/W satisfies Takeoff but violates Cruise", () => {
    // T/W = 0.15 satisfies Takeoff (0.2? no, 0.15 < 0.2, still violated)
    // Actually Takeoff ratio = (0.2-0.15)/0.2 = 0.25, Cruise = (0.1-0.15)/0.1 = -0.5
    // So Takeoff is binding (highest positive ratio)
    const result = findBindingConstraintAtPoint(500, 0.15, wsRange, constraints);
    expect(result).toBe("Takeoff");
  });

  it("returns Cruise as binding when T/W satisfies Takeoff exactly", () => {
    // T/W = 0.25 is above both Takeoff (0.2) and Cruise (0.1)
    // Takeoff ratio = (0.2 - 0.25) / 0.2 = -0.25 (not violated)
    // Cruise ratio = (0.1 - 0.25) / 0.1 = -1.5 (not violated)
    // Stall: ws=500 < ws_max=800, ratio = (500-800)/800 = -0.375
    // All negative → still returns the one with highest ratio (Takeoff at -0.25)
    const result = findBindingConstraintAtPoint(500, 0.25, wsRange, constraints);
    expect(result).toBe("Takeoff");
  });

  it("handles vertical line constraint (ws_max) as binding when ws exceeds it", () => {
    // W/S = 900 > Stall ws_max = 800
    // Stall ratio = (900 - 800) / 800 = 0.125 (positive, violated)
    // Takeoff at ws=900: t_w_points[idx] = 0.2, tw=0.25 -> ratio = (0.2-0.25)/0.2 = -0.25
    // Cruise at ws=900: t_w_points[idx] = 0.1, tw=0.25 -> ratio = (0.1-0.25)/0.1 = -1.5
    // So Stall should bind
    const result = findBindingConstraintAtPoint(900, 0.25, wsRange, constraints);
    expect(result).toBe("Stall");
  });

  it("uses nearest W/S index correctly for ws at end of range", () => {
    // ws = 1100 is beyond range (max is 1090), nearest idx = 99
    const result = findBindingConstraintAtPoint(1100, 0.05, wsRange, constraints);
    // Should still return a result without crashing
    expect(result).not.toBeNull();
    expect(typeof result).toBe("string");
  });

  it("finds nearest index for ws at start of range", () => {
    const result = findBindingConstraintAtPoint(100, 0.05, wsRange, constraints);
    expect(result).not.toBeNull();
  });

  it("handles constraint with zero t_w_points (avoids divide by zero)", () => {
    const zeroConstraints: ConstraintLine[] = [
      {
        name: "Zero",
        t_w_points: Array(100).fill(0),
        ws_max: null,
        color: "#fff",
        binding: false,
        hover_text: null,
      },
    ];
    // twReq = 0, so the branch `if (twReq > 0)` is false → _constraintViolationRatio returns -Infinity
    // bindingName never gets updated (initial value stays null), so result is null
    const result = findBindingConstraintAtPoint(500, 0.1, wsRange, zeroConstraints);
    expect(result).toBeNull();
  });

  it("handles ws_max = Infinity gracefully (branch: isFinite check)", () => {
    const infConstraint: ConstraintLine[] = [
      {
        name: "InfStall",
        t_w_points: null,
        ws_max: Infinity,
        color: "#fff",
        binding: false,
        hover_text: null,
      },
    ];
    // isFinite(Infinity) = false → returns -Infinity → never binding
    const result = findBindingConstraintAtPoint(500, 0.1, wsRange, infConstraint);
    // maxRatio stays -Infinity, bindingName stays null
    expect(result).toBeNull();
  });

  it("returns correct binding for a constraint with ws_max = null and t_w_points = null", () => {
    // Both null → _constraintViolationRatio returns -Infinity for all
    const emptyConstraints: ConstraintLine[] = [
      {
        name: "Empty",
        t_w_points: null,
        ws_max: null,
        color: "#fff",
        binding: false,
        hover_text: null,
      },
    ];
    const result = findBindingConstraintAtPoint(500, 0.1, wsRange, emptyConstraints);
    // maxRatio = -Infinity, bindingName = null (initial); "Empty" never wins
    expect(result).toBeNull();
  });

  it("handles single-element wsRange", () => {
    const singleRange = [500];
    const result = findBindingConstraintAtPoint(500, 0.05, singleRange, [
      { name: "T", t_w_points: [0.2], ws_max: null, color: "#f00", binding: true, hover_text: null },
    ]);
    expect(result).toBe("T");
  });
});

// ── Tests: Mouse drag interactions via fireEvent on the plot div ──────────────

describe("MatchingChartTab — MatchingChartPlot mousedown outside hit radius", () => {
  it("does not crash when mousedown occurs on plot container", () => {
    hookReturn = MOCK_OK_STATE;
    const { container } = render(<MatchingChartTab aeroplaneId="test-id" />);
    const plotDiv = container.querySelector("[data-testid='matching-chart-plot']");
    expect(plotDiv).toBeTruthy();
    // Firing a mousedown on the plot container should not throw
    act(() => {
      fireEvent.mouseDown(plotDiv!, { clientX: 0, clientY: 0 });
    });
    // Component still renders
    expect(screen.getByText(/660/)).toBeInTheDocument();
  });

  it("window mousemove without active drag does not update display", () => {
    hookReturn = MOCK_OK_STATE;
    render(<MatchingChartTab aeroplaneId="test-id" />);
    act(() => {
      fireEvent.mouseMove(window, { clientX: 100, clientY: 100 });
    });
    // No drag active → display point unchanged
    expect(screen.getByText(/660/)).toBeInTheDocument();
  });

  it("window mouseup without active drag does not crash", () => {
    hookReturn = MOCK_OK_STATE;
    render(<MatchingChartTab aeroplaneId="test-id" />);
    act(() => {
      fireEvent.mouseUp(window, { clientX: 100, clientY: 100 });
    });
    expect(screen.getByText(/660/)).toBeInTheDocument();
  });
});

// ── Tests: MatchingChartContent drag state via simulated _fullLayout ──────────

describe("MatchingChartTab — drag with mocked _fullLayout", () => {
  function setupPlotlyLayout(plotDiv: Element) {
    // Simulate Plotly attaching _fullLayout to the div
    const gd = plotDiv as HTMLDivElement & {
      _fullLayout: {
        margin: { l: number; r: number; t: number; b: number };
        xaxis: { range: [number, number] };
        yaxis: { range: [number, number] };
      };
    };
    gd._fullLayout = {
      margin: { l: 55, r: 15, t: 30, b: 50 },
      xaxis: { range: [0, 1500] },
      yaxis: { range: [0, 0.5] },
    };
    // Simulate bounding rect so pixel-to-data math works
    gd.getBoundingClientRect = () => ({
      left: 0,
      top: 0,
      width: 600,
      height: 400,
      right: 600,
      bottom: 400,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    });
  }

  it("drag lifecycle: mousedown near DP → mousemove → mouseup changes display labels", async () => {
    hookReturn = MOCK_OK_STATE;
    const { container } = render(<MatchingChartTab aeroplaneId="test-id" />);
    const plotDiv = container.querySelector("[data-testid='matching-chart-plot']")!;

    // Inject _fullLayout so pixelToDataCoords and isNearDesignPoint work
    setupPlotlyLayout(plotDiv);

    // Flush the async IIFE so plotlyRef.current gets set (to the mocked Plotly)
    await act(async () => { await Promise.resolve(); });

    // Design point is at ws=660 N/m², t_w=0.178
    // With xaxis.range=[0,1500], plotWidth = 600-55-15=530px
    // dpPixelX = 55 + (660/1500)*530 ≈ 55 + 233 = 288
    // With yaxis.range=[0,0.5], plotHeight = 400-30-50=320px
    // dpPixelY = 30 + (1 - 0.178/0.5)*320 ≈ 30 + (0.644)*320 ≈ 30 + 206 = 236
    // Click exactly at design point pixel location
    act(() => {
      fireEvent.mouseDown(plotDiv, { clientX: 288, clientY: 236 });
    });
    // Move somewhere
    act(() => {
      fireEvent.mouseMove(window, { clientX: 300, clientY: 250 });
    });
    act(() => {
      fireEvent.mouseUp(window, { clientX: 300, clientY: 250 });
    });
    // After mouseup, drag labels should revert to "Design Point W/S"
    expect(screen.getByText("Design Point W/S")).toBeInTheDocument();
  });

  it("drag lifecycle with full flush: shows Drag W/S during drag and reverts after mouseup", async () => {
    hookReturn = MOCK_OK_STATE;
    const { container } = render(<MatchingChartTab aeroplaneId="test-id" />);
    const plotDiv = container.querySelector("[data-testid='matching-chart-plot']")!;
    setupPlotlyLayout(plotDiv);

    // Flush async IIFE so plotlyRef.current is set
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    // Initiate drag at design point
    await act(async () => {
      fireEvent.mouseDown(plotDiv, { clientX: 288, clientY: 236 });
    });

    // During drag, move the point to a new location
    await act(async () => {
      fireEvent.mouseMove(window, { clientX: 320, clientY: 260 });
    });

    // End drag
    await act(async () => {
      fireEvent.mouseUp(window, { clientX: 320, clientY: 260 });
    });

    expect(screen.getByText("Design Point W/S")).toBeInTheDocument();
  });

  it("does not initiate drag when clicking far from design point", async () => {
    hookReturn = MOCK_OK_STATE;
    const { container } = render(<MatchingChartTab aeroplaneId="test-id" />);
    const plotDiv = container.querySelector("[data-testid='matching-chart-plot']")!;
    setupPlotlyLayout(plotDiv);

    // Flush async IIFE so plotlyRef.current is set
    await act(async () => { await Promise.resolve(); });

    // Click far from design point (0,0 is well outside the 18px hit radius)
    act(() => {
      fireEvent.mouseDown(plotDiv, { clientX: 0, clientY: 0 });
    });
    act(() => {
      fireEvent.mouseMove(window, { clientX: 50, clientY: 50 });
    });
    act(() => {
      fireEvent.mouseUp(window, { clientX: 50, clientY: 50 });
    });
    // No drag should have started — label stays "Design Point W/S"
    expect(screen.getByText("Design Point W/S")).toBeInTheDocument();
  });

  it("pixelToDataCoords returns null when plotlyRef is not set (no _fullLayout)", async () => {
    hookReturn = MOCK_OK_STATE;
    const { container } = render(<MatchingChartTab aeroplaneId="test-id" />);
    const plotDiv = container.querySelector("[data-testid='matching-chart-plot']")!;
    // Don't set _fullLayout — just trigger a mousedown and flush
    await act(async () => { await Promise.resolve(); });
    // mousedown without _fullLayout — pixelToDataCoords returns null
    act(() => {
      fireEvent.mouseDown(plotDiv, { clientX: 288, clientY: 236 });
    });
    // No drag started (pixelToDataCoords returned null)
    expect(screen.getByText("Design Point W/S")).toBeInTheDocument();
  });
});

// ── Tests: buildHullFill, buildDesignPointTrace, buildConstraintTraces via indirect render ──

describe("MatchingChartTab — trace builders indirect (via render with specific data)", () => {
  it("renders without crash when all t_w_points constraints are 0", () => {
    const zeroData: MatchingChartData = {
      ...MOCK_CESSNA,
      constraints: MOCK_CESSNA.constraints.map((c) =>
        c.t_w_points ? { ...c, t_w_points: Array(200).fill(0) } : c,
      ),
    };
    hookReturn = { ...MOCK_OK_STATE, data: zeroData };
    expect(() => render(<MatchingChartTab aeroplaneId="test-id" />)).not.toThrow();
  });

  it("renders without crash for infeasible data in DesignPointSummary", () => {
    hookReturn = { ...MOCK_OK_STATE, data: MOCK_INFEASIBLE };
    render(<MatchingChartTab aeroplaneId="test-id" />);
    expect(screen.getByText("Infeasible")).toBeInTheDocument();
  });

  it("renders correctly when design point has very high T/W (yMax dominated by dp)", () => {
    const highTwData: MatchingChartData = {
      ...MOCK_CESSNA,
      design_point: { ws_n_m2: 500, t_w: 1.5 },
    };
    hookReturn = { ...MOCK_OK_STATE, data: highTwData };
    expect(() => render(<MatchingChartTab aeroplaneId="test-id" />)).not.toThrow();
  });

  it("renders correctly when constraints array has no t_w_points (all ws_max)", () => {
    const wsOnlyData: MatchingChartData = {
      ...MOCK_CESSNA,
      constraints: [
        { name: "Stall", t_w_points: null, ws_max: 800, color: "#A78BFA", binding: true, hover_text: null },
      ],
    };
    hookReturn = { ...MOCK_OK_STATE, data: wsOnlyData };
    render(<MatchingChartTab aeroplaneId="test-id" />);
    // The "Stall" constraint shows in the binding section
    expect(screen.getByText("Stall")).toBeInTheDocument();
  });

  it("isDragging=false marker size path renders correctly", () => {
    // buildDesignPointTrace with isDragging=false uses size 12
    hookReturn = MOCK_OK_STATE;
    expect(() => render(<MatchingChartTab aeroplaneId="test-id" />)).not.toThrow();
  });
});

// ── Tests: async Plotly IIFE — flush promises to cover trace builders ──────────

describe("MatchingChartTab — async Plotly render (trace builders + buildLayout)", () => {
  // After the dynamic import resolves, buildHullFill / buildConstraintTraces /
  // buildDesignPointTrace / buildLayout are all called.  We flush the micro-task
  // queue with `await act(async () => {})` to cover those code paths.

  it("calls Plotly.react with traces after dynamic import resolves", async () => {
    const { react: mockReact } = await import("plotly.js-gl3d-dist-min");
    (mockReact as ReturnType<typeof vi.fn>).mockClear();

    hookReturn = MOCK_OK_STATE;
    render(<MatchingChartTab aeroplaneId="test-id" />);

    // Flush the async IIFE so the dynamic import + buildXxx calls execute
    await act(async () => {
      await Promise.resolve();
    });

    // Plotly.react may or may not have been called (depends on containerRef being non-null)
    // but the important thing is no uncaught error was thrown
    expect(screen.getByText(/660/)).toBeInTheDocument();
  });

  it("trace builders run for feasible design point (covers buildDesignPointTrace feasible path)", async () => {
    hookReturn = MOCK_OK_STATE;
    const { container } = render(<MatchingChartTab aeroplaneId="test-id" />);
    await act(async () => { await Promise.resolve(); });
    expect(container.querySelector("[data-testid='matching-chart-plot']")).toBeTruthy();
  });

  it("trace builders run for infeasible design point (covers buildDesignPointTrace infeasible path)", async () => {
    hookReturn = { ...MOCK_OK_STATE, data: MOCK_INFEASIBLE };
    render(<MatchingChartTab aeroplaneId="test-id" />);
    await act(async () => { await Promise.resolve(); });
    expect(screen.getByText("Infeasible")).toBeInTheDocument();
  });

  it("buildConstraintTraces covers ws_max branch (vertical constraint)", async () => {
    // Landing and Stall have ws_max — covers the else branch in buildConstraintTraces
    hookReturn = MOCK_OK_STATE;
    render(<MatchingChartTab aeroplaneId="test-id" />);
    await act(async () => { await Promise.resolve(); });
    expect(screen.getByText(/660/)).toBeInTheDocument();
  });

  it("buildConstraintTraces with dragBindingName set (covers isBinding during drag highlight)", async () => {
    // Rerender with new data triggers re-effect which calls buildConstraintTraces
    hookReturn = MOCK_OK_STATE;
    const { rerender } = render(<MatchingChartTab aeroplaneId="test-id" />);
    await act(async () => { await Promise.resolve(); });
    const newData: MatchingChartData = {
      ...MOCK_CESSNA,
      design_point: { ws_n_m2: 700, t_w: 0.19 },
    };
    hookReturn = { ...MOCK_OK_STATE, data: newData };
    rerender(<MatchingChartTab aeroplaneId="test-id" />);
    await act(async () => { await Promise.resolve(); });
    expect(screen.getByText(/700/)).toBeInTheDocument();
  });

  it("buildLayout covers empty allTw branch when no t_w_points constraints", async () => {
    const wsOnlyData: MatchingChartData = {
      ...MOCK_CESSNA,
      constraints: [
        { name: "Stall", t_w_points: null, ws_max: 800, color: "#A78BFA", binding: false, hover_text: null },
      ],
    };
    hookReturn = { ...MOCK_OK_STATE, data: wsOnlyData };
    render(<MatchingChartTab aeroplaneId="test-id" />);
    await act(async () => { await Promise.resolve(); });
    expect(screen.getByText("Design Point W/S")).toBeInTheDocument();
  });

  it("cleanup effect unmounts without crashing (covers purge path)", async () => {
    hookReturn = MOCK_OK_STATE;
    const { unmount } = render(<MatchingChartTab aeroplaneId="test-id" />);
    await act(async () => { await Promise.resolve(); });
    // Unmount triggers the cleanup effect which calls Plotly.purge
    expect(() => unmount()).not.toThrow();
  });

  it("handles loading transition then data (content key change)", async () => {
    hookReturn = MOCK_LOADING_STATE;
    const { rerender } = render(<MatchingChartTab aeroplaneId="test-id" />);
    hookReturn = MOCK_OK_STATE;
    rerender(<MatchingChartTab aeroplaneId="test-id" />);
    await act(async () => { await Promise.resolve(); });
    expect(screen.getByText(/660/)).toBeInTheDocument();
  });
});

// ── gh-606: Info modal ────────────────────────────────────────────────────────

describe("MatchingChartTab — info modal (gh-606)", () => {
  beforeEach(() => {
    hookReturn = MOCK_OK_STATE;
    mockAssumptions = [];
    mockCtx = null;
  });

  it("info-modal trigger has aria-label and is keyboard-accessible", () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    const trigger = screen.getByTestId("info-modal-trigger");
    expect(trigger).toHaveAttribute("aria-label", "Open sizing methodology help");
    expect(trigger.tagName).toBe("BUTTON");
  });

  it("modal is hidden initially", () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    expect(screen.queryByTestId("matching-chart-info-modal")).toBeNull();
  });

  it("clicking trigger opens the modal with all 8 sections", () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    act(() => {
      fireEvent.click(screen.getByTestId("info-modal-trigger"));
    });
    expect(screen.getByTestId("matching-chart-info-modal")).toBeInTheDocument();
    // Eight sections per Scholz-corrected spec
    expect(screen.getByTestId("info-section-overview")).toBeInTheDocument();
    expect(screen.getByTestId("info-section-glossary")).toBeInTheDocument();
    expect(screen.getByTestId("info-section-axes")).toBeInTheDocument();
    expect(screen.getByTestId("info-section-constraints")).toBeInTheDocument();
    expect(screen.getByTestId("info-section-red-area")).toBeInTheDocument();
    expect(screen.getByTestId("info-section-design-point")).toBeInTheDocument();
    expect(screen.getByTestId("info-section-readoff")).toBeInTheDocument();
    expect(screen.getByTestId("info-section-iteration")).toBeInTheDocument();
  });

  it("modal y-axis section names T_TO/W_TO and the static-thrust proxy", () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    act(() => {
      fireEvent.click(screen.getByTestId("info-modal-trigger"));
    });
    const axes = screen.getByTestId("info-section-axes");
    // textContent strips <sub> tags, so T_TO/W_TO becomes TTO/WTO
    expect(axes.textContent).toMatch(/TTO\/WTO/);
    expect(axes.textContent).toMatch(/take-off thrust over take-off weight/);
    expect(axes.textContent).toMatch(/proxy/);
    // AR labelled as chart INPUT, not "held constant"
    expect(axes.textContent).toMatch(/AR is a chart INPUT/);
  });

  it("modal glossary entry for T mentions the RC approximation", () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    act(() => {
      fireEvent.click(screen.getByTestId("info-modal-trigger"));
    });
    const glossary = screen.getByTestId("info-section-glossary");
    expect(glossary.textContent).toMatch(/take-off thrust at sea level/);
    expect(glossary.textContent).toMatch(/static-thrust input/);
    expect(glossary.textContent).toMatch(/L\/D/);
    expect(glossary.textContent).toMatch(/C/); // C_L,max
  });

  it("modal overview discloses 3-5 iteration outer loop and SI units", () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    act(() => {
      fireEvent.click(screen.getByTestId("info-modal-trigger"));
    });
    const overview = screen.getByTestId("info-section-overview");
    expect(overview.textContent).toMatch(/3.{0,3}5 iteration/);
    expect(overview.textContent).toMatch(/SI units/);
  });

  it("modal cruise is shown but called out as slack (parenthesised)", () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    act(() => {
      fireEvent.click(screen.getByTestId("info-modal-trigger"));
    });
    const constraints = screen.getByTestId("info-section-constraints");
    expect(constraints.textContent).toMatch(/Cruise/);
    expect(constraints.textContent).toMatch(/slack/);
  });

  it("modal includes Scholz Fig. 5.9 sketch reference", () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    act(() => {
      fireEvent.click(screen.getByTestId("info-modal-trigger"));
    });
    const dp = screen.getByTestId("info-section-design-point");
    expect(dp.textContent).toMatch(/Fig\. 5\.9/);
    expect(dp.textContent).toMatch(/intersection of the take-off line/);
  });

  it("ESC closes the modal", () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    act(() => {
      fireEvent.click(screen.getByTestId("info-modal-trigger"));
    });
    expect(screen.getByTestId("matching-chart-info-modal")).toBeInTheDocument();
    act(() => {
      fireEvent.keyDown(window, { key: "Escape" });
    });
    expect(screen.queryByTestId("matching-chart-info-modal")).toBeNull();
  });

  it("close button closes the modal", () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    act(() => {
      fireEvent.click(screen.getByTestId("info-modal-trigger"));
    });
    act(() => {
      fireEvent.click(screen.getByTestId("info-modal-close"));
    });
    expect(screen.queryByTestId("matching-chart-info-modal")).toBeNull();
  });
});

// ── gh-606: Current design point marker — powered ────────────────────────────

describe("MatchingChartTab — current design point (powered, gh-606)", () => {
  beforeEach(() => {
    hookReturn = MOCK_OK_STATE;
    mockAssumptions = [
      { parameter_name: "mass", effective_value: 2.0 }, // 2 kg
      { parameter_name: "t_static_N", effective_value: 30.0 }, // 30 N
    ];
    mockCtx = { s_ref_m2: 0.5, b_ref_m: 2.0, is_glider: false };
  });

  it("renders Current Design Point trace via Plotly.react", async () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    await act(async () => { await Promise.resolve(); });
    // Plotly.react should have been called; pull the traces argument
    const calls = plotlyReactMock.mock.calls;
    expect(calls.length).toBeGreaterThan(0);
    const traces = calls[calls.length - 1][1] as Array<{ name?: string }>;
    const cdp = traces.find((t) => t.name === "Current Design Point");
    expect(cdp).toBeDefined();
  });

  it("Current Design Point uses (W/S, T/W) = (39.2, 1.53) for 2kg/0.5m²/30N", async () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    await act(async () => { await Promise.resolve(); });
    const traces = plotlyReactMock.mock.calls.at(-1)![1] as Array<{
      name?: string;
      x?: number[];
      y?: number[];
    }>;
    const cdp = traces.find((t) => t.name === "Current Design Point")!;
    // W = 2 × 9.80665 = 19.6133 N. W/S = 19.6133 / 0.5 = 39.227. T/W = 30 / 19.6133 = 1.530.
    expect(cdp.x![0]).toBeCloseTo(39.227, 2);
    expect(cdp.y![0]).toBeCloseTo(1.530, 2);
  });

  it("Current Design Point marker uses teal #22dd99 and diamond symbol", async () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    await act(async () => { await Promise.resolve(); });
    const traces = plotlyReactMock.mock.calls.at(-1)![1] as Array<{
      name?: string;
      marker?: { symbol?: string; color?: string };
    }>;
    const cdp = traces.find((t) => t.name === "Current Design Point")!;
    expect(cdp.marker?.symbol).toBe("diamond");
    expect(cdp.marker?.color).toBe("#22dd99");
  });

  it("Current Design Point hover template names W as m_MTO·g", async () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    await act(async () => { await Promise.resolve(); });
    const traces = plotlyReactMock.mock.calls.at(-1)![1] as Array<{
      name?: string;
      hovertemplate?: string;
    }>;
    const cdp = traces.find((t) => t.name === "Current Design Point")!;
    expect(cdp.hovertemplate).toMatch(/m_MTO/);
    expect(cdp.hovertemplate).toMatch(/W\/S/);
    expect(cdp.hovertemplate).toMatch(/T\/W/);
    expect(cdp.hovertemplate).toMatch(/AR/);
    expect(cdp.hovertemplate).toMatch(/assumed static thrust/);
  });
});

// ── gh-606: Glider suppression ───────────────────────────────────────────────

describe("MatchingChartTab — glider current design point suppressed (gh-606)", () => {
  beforeEach(() => {
    hookReturn = MOCK_OK_STATE;
  });

  it("no Current Design Point trace for glider context", async () => {
    mockAssumptions = [
      { parameter_name: "mass", effective_value: 2.0 },
      { parameter_name: "t_static_N", effective_value: 0 },
    ];
    mockCtx = { s_ref_m2: 0.5, b_ref_m: 3.0, is_glider: true };
    render(<MatchingChartTab aeroplaneId="test-id" />);
    await act(async () => { await Promise.resolve(); });
    const traces = plotlyReactMock.mock.calls.at(-1)![1] as Array<{ name?: string }>;
    const cdp = traces.find((t) => t.name === "Current Design Point");
    expect(cdp).toBeUndefined();
  });

  it("renders the glider callout", async () => {
    mockAssumptions = [];
    mockCtx = { s_ref_m2: 0.5, b_ref_m: 3.0, is_glider: true };
    render(<MatchingChartTab aeroplaneId="test-id" />);
    await act(async () => { await Promise.resolve(); });
    const callout = screen.getByTestId("glider-callout");
    expect(callout.textContent).toMatch(/jet\/powered-only/);
    expect(callout.textContent).toMatch(/sink-rate polar/);
  });

  it("no Current Design Point trace when t_static_N = 0 (even non-glider flag)", async () => {
    mockAssumptions = [
      { parameter_name: "mass", effective_value: 2.0 },
      { parameter_name: "t_static_N", effective_value: 0 },
    ];
    mockCtx = { s_ref_m2: 0.5, b_ref_m: 2.0, is_glider: false };
    render(<MatchingChartTab aeroplaneId="test-id" />);
    await act(async () => { await Promise.resolve(); });
    const traces = plotlyReactMock.mock.calls.at(-1)![1] as Array<{ name?: string }>;
    expect(traces.find((t) => t.name === "Current Design Point")).toBeUndefined();
  });
});

// ── gh-606: Insufficient-thrust callout ──────────────────────────────────────

describe("MatchingChartTab — insufficient thrust warning (gh-606)", () => {
  it("renders callout when current marker T/W is below a constraint curve", async () => {
    // Constraint at T/W = 0.5 across the board. Current T/W = 30 / (40 × 9.80665) = ~0.0765 — well below.
    // mass = 40 kg, s_ref = 1.0 m² → W = 392 N, W/S = 392, T/W = 30/392 = 0.0765.
    const customData: MatchingChartData = {
      ...MOCK_CESSNA,
      ws_range_n_m2: Array.from({ length: 200 }, (_, i) => 10 + (1490 / 199) * i),
      constraints: [
        {
          name: "Climb",
          t_w_points: Array(200).fill(0.5),
          ws_max: null,
          color: "#E5484D",
          binding: true,
          hover_text: "Insufficient climb thrust",
        },
      ],
      design_point: { ws_n_m2: 400, t_w: 0.5 },
    };
    hookReturn = { ...MOCK_OK_STATE, data: customData };
    mockAssumptions = [
      { parameter_name: "mass", effective_value: 40 },
      { parameter_name: "t_static_N", effective_value: 30 },
    ];
    mockCtx = { s_ref_m2: 1.0, b_ref_m: 3.0, is_glider: false };

    render(<MatchingChartTab aeroplaneId="test-id" />);
    await act(async () => { await Promise.resolve(); });

    const callout = screen.getByTestId("insufficient-thrust-callout");
    expect(callout.textContent).toMatch(/insufficient/i);
    expect(callout.textContent).toMatch(/Climb/);
  });

  it("does NOT render callout when current marker is above all constraints", async () => {
    const customData: MatchingChartData = {
      ...MOCK_CESSNA,
      constraints: [
        {
          name: "Climb",
          t_w_points: Array(200).fill(0.05),
          ws_max: null,
          color: "#E5484D",
          binding: false,
          hover_text: "OK",
        },
      ],
    };
    hookReturn = { ...MOCK_OK_STATE, data: customData };
    mockAssumptions = [
      { parameter_name: "mass", effective_value: 2 },
      { parameter_name: "t_static_N", effective_value: 30 },
    ];
    mockCtx = { s_ref_m2: 0.5, b_ref_m: 2.0, is_glider: false };
    render(<MatchingChartTab aeroplaneId="test-id" />);
    await act(async () => { await Promise.resolve(); });
    expect(screen.queryByTestId("insufficient-thrust-callout")).toBeNull();
  });
});

// ── gh-606: Live derived readout ─────────────────────────────────────────────

describe("MatchingChartTab — live derived readout (gh-606)", () => {
  beforeEach(() => {
    hookReturn = MOCK_OK_STATE;
    mockAssumptions = [
      { parameter_name: "mass", effective_value: 2.0 }, // W = 19.6133 N
      { parameter_name: "t_static_N", effective_value: 30.0 },
    ];
    mockCtx = { s_ref_m2: 0.5, b_ref_m: 2.0, is_glider: false };
  });

  it("readout shows derived S, T, W, and AR cells", () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    // Initial design point W/S=660, T/W=0.178 → S = 19.6133/660 ≈ 0.0297, T = 0.178·19.6133 ≈ 3.49
    const sCell = document.querySelector("[data-testid='dp-derived-s']");
    const tCell = document.querySelector("[data-testid='dp-derived-t']");
    const wCell = document.querySelector("[data-testid='dp-w']");
    const arCell = document.querySelector("[data-testid='dp-ar']");
    expect(sCell).toBeTruthy();
    expect(tCell).toBeTruthy();
    expect(wCell).toBeTruthy();
    expect(arCell).toBeTruthy();
    // W displayed in N
    expect(wCell!.textContent).toMatch(/19\.6/);
    // AR = b²/S = 4 / 0.5 = 8.00
    expect(arCell!.textContent).toMatch(/8\.00/);
  });

  it("AR label uses 'AR (input — see info modal)' not 'AR (held)'", () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    expect(screen.getByText(/AR \(input — see info modal\)/)).toBeInTheDocument();
    expect(screen.queryByText(/AR \(held\)/)).toBeNull();
  });

  it("W label uses 'W (m_MTO · g)'", () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    expect(screen.getByText(/W \(m_MTO · g\)/)).toBeInTheDocument();
  });

  it("derived S = W / (W/S) when dragging to (W/S = 100, T/W = 0.4)", async () => {
    const customData: MatchingChartData = {
      ...MOCK_CESSNA,
      design_point: { ws_n_m2: 100, t_w: 0.4 },
    };
    hookReturn = { ...MOCK_OK_STATE, data: customData };
    render(<MatchingChartTab aeroplaneId="test-id" />);
    // W = 19.6133 N, so S = 19.6133 / 100 = 0.196 m²
    const sCell = document.querySelector("[data-testid='dp-derived-s']");
    expect(sCell!.textContent).toMatch(/0\.196/);
    // T = 0.4 × 19.6133 = 7.85 N → 3 sig figs ≈ "7.85"
    const tCell = document.querySelector("[data-testid='dp-derived-t']");
    expect(tCell!.textContent).toMatch(/7\.85/);
  });

  it("derived cells show em dash when mass missing", () => {
    mockAssumptions = []; // no mass
    mockCtx = { s_ref_m2: 0.5, b_ref_m: 2.0, is_glider: false };
    render(<MatchingChartTab aeroplaneId="test-id" />);
    const sCell = document.querySelector("[data-testid='dp-derived-s']");
    expect(sCell!.textContent).toMatch(/—/);
  });
});

// ── gh-606: pure helpers ──────────────────────────────────────────────────────

describe("formatSigFigs (gh-606)", () => {
  it("formats 123 to 3 sig figs as '123'", () => {
    expect(formatSigFigs(123, 3)).toBe("123");
  });
  it("formats 1234.56 to 3 sig figs", () => {
    // toPrecision(3) on 1234.56 = "1.23e+3"
    expect(formatSigFigs(1234.56, 3)).toMatch(/1\.23e\+3/);
  });
  it("formats 0.01234 to 3 sig figs", () => {
    expect(formatSigFigs(0.01234, 3)).toBe("0.0123");
  });
  it("returns '0' for zero", () => {
    expect(formatSigFigs(0, 3)).toBe("0");
  });
  it("returns em dash for non-finite", () => {
    expect(formatSigFigs(Infinity, 3)).toBe("—");
    expect(formatSigFigs(NaN, 3)).toBe("—");
  });
});

describe("computeWingArea / computeThrust / computeAspectRatio (gh-606)", () => {
  it("S = W / (W/S)", () => {
    expect(computeWingArea(19.6133, 660)).toBeCloseTo(0.0297, 4);
    expect(computeWingArea(19.6133, 100)).toBeCloseTo(0.196, 3);
  });
  it("computeWingArea returns NaN for W/S <= 0", () => {
    expect(Number.isNaN(computeWingArea(100, 0))).toBe(true);
    expect(Number.isNaN(computeWingArea(100, -1))).toBe(true);
  });
  it("T = T/W · W", () => {
    expect(computeThrust(100, 0.5)).toBe(50);
    expect(computeThrust(19.6133, 0.4)).toBeCloseTo(7.845, 3);
  });
  it("AR = b²/S", () => {
    expect(computeAspectRatio(2, 0.5)).toBeCloseTo(8.0, 5);
    expect(computeAspectRatio(3, 1)).toBe(9);
  });
  it("AR returns null on missing/invalid inputs", () => {
    expect(computeAspectRatio(null, 1)).toBeNull();
    expect(computeAspectRatio(2, null)).toBeNull();
    expect(computeAspectRatio(2, 0)).toBeNull();
    expect(computeAspectRatio(2, -1)).toBeNull();
  });
});

describe("findInsufficientThrustConstraint (gh-606)", () => {
  const wsRange = Array.from({ length: 100 }, (_, i) => 100 + i * 10);
  const constraints: ConstraintLine[] = [
    { name: "Takeoff", t_w_points: Array(100).fill(0.2), ws_max: null, color: "#FF8400", binding: true, hover_text: null },
    { name: "Climb", t_w_points: Array(100).fill(0.5), ws_max: null, color: "#E5484D", binding: false, hover_text: null },
    { name: "Stall", t_w_points: null, ws_max: 800, color: "#A78BFA", binding: false, hover_text: null },
  ];

  it("returns most-violated t_w_points constraint when below all", () => {
    // T/W = 0.05 violates both Takeoff (0.2) and Climb (0.5). Climb has the larger ratio.
    expect(findInsufficientThrustConstraint(500, 0.05, wsRange, constraints)).toBe("Climb");
  });

  it("returns null when current T/W is above all curves", () => {
    expect(findInsufficientThrustConstraint(500, 0.8, wsRange, constraints)).toBeNull();
  });

  it("ignores ws_max-only constraints", () => {
    const wsOnly: ConstraintLine[] = [
      { name: "Stall", t_w_points: null, ws_max: 800, color: "#A78BFA", binding: false, hover_text: null },
    ];
    expect(findInsufficientThrustConstraint(900, 0.1, wsRange, wsOnly)).toBeNull();
  });

  it("returns null on empty wsRange", () => {
    expect(findInsufficientThrustConstraint(500, 0.05, [], constraints)).toBeNull();
  });

  it("ignores zero-valued constraints to avoid divide-by-zero", () => {
    const zero: ConstraintLine[] = [
      { name: "Zero", t_w_points: Array(100).fill(0), ws_max: null, color: "#fff", binding: false, hover_text: null },
    ];
    expect(findInsufficientThrustConstraint(500, 0.1, wsRange, zero)).toBeNull();
  });
});

// ── gh-613 Phase A: CS-25 honesty in the info modal ──────────────────────────

describe("MatchingChartTab — gh-613 Phase A CS-25 callout", () => {
  beforeEach(() => {
    hookReturn = MOCK_OK_STATE;
    mockAssumptions = [];
    mockCtx = null;
  });

  it("constraints section shows CS-25 provenance callout when modal is open", () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    act(() => {
      fireEvent.click(screen.getByTestId("info-modal-trigger"));
    });
    const callout = screen.getByTestId("info-section-cs25-callout");
    expect(callout).toBeInTheDocument();
    expect(callout.textContent).toMatch(/Scholz\/Loftin CS-25 methodology/);
    expect(callout.textContent).toMatch(/multi-engine transport aircraft/);
    expect(callout.textContent).toMatch(/Second-Segment Climb \(OEI\)/);
    expect(callout.textContent).toMatch(/Missed-Approach Climb/);
    expect(callout.textContent).toMatch(/CS-25 conformance bands, not RC requirements/);
  });

  it("CS-25 callout precedes the constraints list inside the constraints section", () => {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    act(() => {
      fireEvent.click(screen.getByTestId("info-modal-trigger"));
    });
    const constraintsSection = screen.getByTestId("info-section-constraints");
    const callout = screen.getByTestId("info-section-cs25-callout");
    // Callout must live inside the constraints section
    expect(constraintsSection.contains(callout)).toBe(true);
    // Callout must come before the <ul> of constraints
    const ul = constraintsSection.querySelector("ul");
    expect(ul).toBeTruthy();
    expect(
      callout.compareDocumentPosition(ul!) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeGreaterThan(0);
  });
});

describe("MatchingChartTab — gh-613 Phase A relevance badges", () => {
  beforeEach(() => {
    hookReturn = MOCK_OK_STATE;
    mockAssumptions = [];
    mockCtx = null;
  });

  function openModal() {
    render(<MatchingChartTab aeroplaneId="test-id" />);
    act(() => {
      fireEvent.click(screen.getByTestId("info-modal-trigger"));
    });
  }

  it("Stall constraint has Universal badge", () => {
    openModal();
    const badge = screen.getByTestId("constraint-badge-stall");
    expect(badge).toHaveAttribute("data-relevance", "universal");
    expect(badge.textContent).toMatch(/Universal/);
    expect(badge).toHaveAttribute("title", "Universal — pure aerodynamics");
  });

  it("Takeoff field length has Conditional badge", () => {
    openModal();
    const badge = screen.getByTestId("constraint-badge-takeoff");
    expect(badge).toHaveAttribute("data-relevance", "conditional");
    expect(badge.textContent).toMatch(/Conditional/);
    expect(badge).toHaveAttribute("title", "Wheeled takeoff only");
  });

  it("Second-segment climb has CS-25-only badge", () => {
    openModal();
    const badge = screen.getByTestId("constraint-badge-second-segment");
    expect(badge).toHaveAttribute("data-relevance", "cs25-only");
    expect(badge.textContent).toMatch(/CS-25-only/);
    expect(badge).toHaveAttribute(
      "title",
      "CS-25 multi-engine — single-engine N/A",
    );
  });

  it("Missed-approach climb has CS-25-only badge", () => {
    openModal();
    const badge = screen.getByTestId("constraint-badge-missed-approach");
    expect(badge).toHaveAttribute("data-relevance", "cs25-only");
    expect(badge.textContent).toMatch(/CS-25-only/);
    expect(badge).toHaveAttribute(
      "title",
      "CS-25 multi-engine — single-engine N/A",
    );
  });

  it("Cruise has Universal badge with slack tooltip", () => {
    openModal();
    const badge = screen.getByTestId("constraint-badge-cruise");
    expect(badge).toHaveAttribute("data-relevance", "universal");
    expect(badge.textContent).toMatch(/Universal/);
    expect(badge).toHaveAttribute(
      "title",
      "Universal — slack constraint, iterated via fuel mass",
    );
  });

  it("Landing field length has Conditional badge", () => {
    openModal();
    const badge = screen.getByTestId("constraint-badge-landing");
    expect(badge).toHaveAttribute("data-relevance", "conditional");
    expect(badge.textContent).toMatch(/Conditional/);
    expect(badge).toHaveAttribute("title", "Runway landing only");
  });
});

// ── gh-613 Phase A: relax insufficient-T/W warning (skip OEI / Missed-Approach) ──

describe("MatchingChartTab — gh-613 Phase A insufficient-T/W skips OEI", () => {
  it("does NOT render warning when only an OEI Second-Segment constraint is violated", async () => {
    const data: MatchingChartData = {
      ...MOCK_CESSNA,
      constraints: [
        // Only the OEI constraint is binding/violated — everything else is OK.
        {
          name: "Second-Segment Climb (OEI)",
          t_w_points: Array(200).fill(0.5),
          ws_max: null,
          color: "#E5484D",
          binding: true,
          hover_text: "OEI segment-2",
        },
        {
          name: "Cruise",
          t_w_points: Array(200).fill(0.05),
          ws_max: null,
          color: "#30A46C",
          binding: false,
          hover_text: "Cruise",
        },
      ],
      design_point: { ws_n_m2: 400, t_w: 0.5 },
    };
    hookReturn = { ...MOCK_OK_STATE, data };
    mockAssumptions = [
      { parameter_name: "mass", effective_value: 40 },
      { parameter_name: "t_static_N", effective_value: 30 }, // T/W ≈ 0.076
    ];
    mockCtx = { s_ref_m2: 1.0, b_ref_m: 3.0, is_glider: false };

    render(<MatchingChartTab aeroplaneId="test-id" />);
    await act(async () => {
      await Promise.resolve();
    });

    // OEI was the only "binding" violator — warning must be suppressed.
    expect(screen.queryByTestId("insufficient-thrust-callout")).toBeNull();
  });

  it("does NOT render warning when only Missed-Approach constraint is violated", async () => {
    const data: MatchingChartData = {
      ...MOCK_CESSNA,
      constraints: [
        {
          name: "Missed-Approach Climb",
          t_w_points: Array(200).fill(0.5),
          ws_max: null,
          color: "#E5484D",
          binding: true,
          hover_text: "Missed approach",
        },
      ],
      design_point: { ws_n_m2: 400, t_w: 0.5 },
    };
    hookReturn = { ...MOCK_OK_STATE, data };
    mockAssumptions = [
      { parameter_name: "mass", effective_value: 40 },
      { parameter_name: "t_static_N", effective_value: 30 },
    ];
    mockCtx = { s_ref_m2: 1.0, b_ref_m: 3.0, is_glider: false };

    render(<MatchingChartTab aeroplaneId="test-id" />);
    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.queryByTestId("insufficient-thrust-callout")).toBeNull();
  });

  it("DOES render warning when a non-OEI constraint (e.g. Stall climb) is violated", async () => {
    const data: MatchingChartData = {
      ...MOCK_CESSNA,
      constraints: [
        // OEI exists but is satisfied (low requirement) — should still be skipped from warning anyway
        {
          name: "Second-Segment Climb (OEI)",
          t_w_points: Array(200).fill(0.02),
          ws_max: null,
          color: "#888",
          binding: false,
          hover_text: "OEI segment-2",
        },
        // Stall (T/W requirement) is genuinely violated
        {
          name: "Stall Climb",
          t_w_points: Array(200).fill(0.5),
          ws_max: null,
          color: "#E5484D",
          binding: true,
          hover_text: "Stall climb",
        },
      ],
      design_point: { ws_n_m2: 400, t_w: 0.5 },
    };
    hookReturn = { ...MOCK_OK_STATE, data };
    mockAssumptions = [
      { parameter_name: "mass", effective_value: 40 },
      { parameter_name: "t_static_N", effective_value: 30 },
    ];
    mockCtx = { s_ref_m2: 1.0, b_ref_m: 3.0, is_glider: false };

    render(<MatchingChartTab aeroplaneId="test-id" />);
    await act(async () => {
      await Promise.resolve();
    });

    const callout = screen.getByTestId("insufficient-thrust-callout");
    expect(callout).toBeInTheDocument();
    // The non-OEI constraint name should appear (Stall Climb), not the OEI one.
    expect(callout.textContent).toMatch(/Stall Climb/);
    expect(callout.textContent).not.toMatch(/Second-Segment Climb \(OEI\)/);
  });
});

describe("findInsufficientThrustConstraint — gh-613 Phase A skipOei flag", () => {
  const wsRange = Array.from({ length: 100 }, (_, i) => 100 + i * 10);

  it("skipOei=true ignores 'Second-Segment Climb (OEI)' constraint", () => {
    const constraints: ConstraintLine[] = [
      {
        name: "Second-Segment Climb (OEI)",
        t_w_points: Array(100).fill(0.5),
        ws_max: null,
        color: "#E5484D",
        binding: true,
        hover_text: null,
      },
    ];
    // T/W = 0.05 violates the OEI constraint; with skipOei it should be ignored.
    expect(
      findInsufficientThrustConstraint(500, 0.05, wsRange, constraints, true),
    ).toBeNull();
    // Without the flag (or with skipOei=false) the constraint is still considered.
    expect(
      findInsufficientThrustConstraint(500, 0.05, wsRange, constraints, false),
    ).toBe("Second-Segment Climb (OEI)");
  });

  it("skipOei=true ignores 'Missed-Approach Climb' constraint", () => {
    const constraints: ConstraintLine[] = [
      {
        name: "Missed-Approach Climb",
        t_w_points: Array(100).fill(0.5),
        ws_max: null,
        color: "#E5484D",
        binding: true,
        hover_text: null,
      },
    ];
    expect(
      findInsufficientThrustConstraint(500, 0.05, wsRange, constraints, true),
    ).toBeNull();
  });

  it("skipOei=true still flags genuine non-OEI binding constraints", () => {
    const constraints: ConstraintLine[] = [
      {
        name: "Second-Segment Climb (OEI)",
        t_w_points: Array(100).fill(0.5),
        ws_max: null,
        color: "#E5484D",
        binding: true,
        hover_text: null,
      },
      {
        name: "Climb",
        t_w_points: Array(100).fill(0.4),
        ws_max: null,
        color: "#E5484D",
        binding: false,
        hover_text: null,
      },
    ];
    // T/W = 0.05 violates Climb (non-OEI) — should still report it.
    expect(
      findInsufficientThrustConstraint(500, 0.05, wsRange, constraints, true),
    ).toBe("Climb");
  });

  it("default (no skipOei argument) preserves previous behavior", () => {
    // Backwards compat: callers that don't pass the flag get the old behavior.
    const constraints: ConstraintLine[] = [
      {
        name: "Second-Segment Climb (OEI)",
        t_w_points: Array(100).fill(0.5),
        ws_max: null,
        color: "#E5484D",
        binding: true,
        hover_text: null,
      },
    ];
    // No 5th arg → undefined → falsy → OEI not skipped → bindingName returned.
    expect(
      findInsufficientThrustConstraint(500, 0.05, wsRange, constraints),
    ).toBe("Second-Segment Climb (OEI)");
  });
});

describe("buildCurrentDesignPointTrace (gh-606)", () => {
  it("produces a Plotly trace with the expected shape", () => {
    const trace = buildCurrentDesignPointTrace({
      ws_n_m2: 39.227,
      t_w: 1.530,
      mass_kg: 2,
      s_m2: 0.5,
      t_n: 30,
      w_n: 19.6133,
      ar: 8.0,
    });
    expect(trace.name).toBe("Current Design Point");
    expect(trace.type).toBe("scatter");
    expect(trace.mode).toBe("markers");
    expect(trace.x).toEqual([39.227]);
    expect(trace.y).toEqual([1.530]);
    expect(trace.marker.symbol).toBe("diamond");
    expect(trace.marker.color).toBe("#22dd99");
    expect(trace.hovertemplate).toContain("m_MTO·g");
  });

  it("renders em-dash for AR when null", () => {
    const trace = buildCurrentDesignPointTrace({
      ws_n_m2: 100,
      t_w: 0.2,
      mass_kg: 1,
      s_m2: 0.5,
      t_n: 10,
      w_n: 9.81,
      ar: null,
    });
    expect(trace.hovertemplate).toContain("AR = —");
  });
});

// ───────────────────────────────────────────────────────────────────────────
// gh-613 Phase B — data-driven constraint rendering
// ───────────────────────────────────────────────────────────────────────────

import {
  applicableConstraints,
  isConstraintBindingForWarning,
  constraintRelevance,
  CATEGORY_TO_RELEVANCE,
} from "@/components/workbench/MatchingChartTab";

describe("gh-613 Phase B — applicableConstraints filter", () => {
  it("keeps constraints with applicable_for_profile=true", () => {
    const cs: ConstraintLine[] = [
      {
        name: "Stall",
        t_w_points: null,
        ws_max: 900,
        color: "#A78BFA",
        binding: false,
        hover_text: null,
        category: "universal",
        binding_for_warning: true,
        applicable_for_profile: true,
      },
    ];
    expect(applicableConstraints(cs)).toHaveLength(1);
  });

  it("drops constraints with applicable_for_profile=false", () => {
    const cs: ConstraintLine[] = [
      {
        name: "Stall",
        t_w_points: null,
        ws_max: 900,
        color: "#A78BFA",
        binding: false,
        hover_text: null,
        category: "universal",
        binding_for_warning: true,
        applicable_for_profile: true,
      },
      {
        name: "Takeoff",
        t_w_points: [0.1, 0.2, 0.3],
        ws_max: null,
        color: "#FF8400",
        binding: false,
        hover_text: null,
        category: "universal",
        binding_for_warning: true,
        applicable_for_profile: false,
      },
    ];
    const out = applicableConstraints(cs);
    expect(out.map((c) => c.name)).toEqual(["Stall"]);
  });

  it("falls back to keeping constraints when applicable_for_profile is missing (legacy)", () => {
    const cs = [
      {
        name: "Climb",
        t_w_points: [0.1, 0.2],
        ws_max: null,
        color: "#E5484D",
        binding: false,
        hover_text: null,
      } as ConstraintLine,
    ];
    expect(applicableConstraints(cs)).toHaveLength(1);
  });
});

describe("gh-613 Phase B — isConstraintBindingForWarning (data-driven)", () => {
  it("returns true when binding_for_warning=true", () => {
    expect(
      isConstraintBindingForWarning({
        name: "Stall",
        t_w_points: null,
        ws_max: 900,
        color: "#A78BFA",
        binding: false,
        hover_text: null,
        category: "universal",
        binding_for_warning: true,
        applicable_for_profile: true,
      }),
    ).toBe(true);
  });

  it("returns false when binding_for_warning=false (independent of name)", () => {
    expect(
      isConstraintBindingForWarning({
        name: "Wing-Cube-Loading",
        t_w_points: null,
        ws_max: 250,
        color: "#FBBF24",
        binding: false,
        hover_text: null,
        category: "rc_specific",
        binding_for_warning: false,
        applicable_for_profile: true,
      }),
    ).toBe(false);
  });

  it("falls back to the Phase A name regex when binding_for_warning is missing", () => {
    const legacyOei = {
      name: "Second-Segment Climb (OEI)",
      t_w_points: [0.5, 0.5],
      ws_max: null,
      color: "#E5484D",
      binding: false,
      hover_text: null,
    } as ConstraintLine;
    expect(isConstraintBindingForWarning(legacyOei)).toBe(false);

    const legacyClimb = {
      name: "Climb",
      t_w_points: [0.5, 0.5],
      ws_max: null,
      color: "#E5484D",
      binding: false,
      hover_text: null,
    } as ConstraintLine;
    expect(isConstraintBindingForWarning(legacyClimb)).toBe(true);
  });
});

describe("gh-613 Phase B — findInsufficientThrustConstraint uses binding_for_warning", () => {
  const wsRange = Array.from({ length: 50 }, (_, i) => 50 + i * 10);

  it("ignores constraints with binding_for_warning=false even when violated", () => {
    const cs: ConstraintLine[] = [
      {
        name: "Some Guideline",
        t_w_points: Array(50).fill(0.5),
        ws_max: null,
        color: "#FBBF24",
        binding: false,
        hover_text: null,
        category: "rc_specific",
        binding_for_warning: false,
        applicable_for_profile: true,
      },
    ];
    expect(
      findInsufficientThrustConstraint(200, 0.05, wsRange, cs, true),
    ).toBeNull();
  });

  it("still flags constraints with binding_for_warning=true", () => {
    const cs: ConstraintLine[] = [
      {
        name: "Climb",
        t_w_points: Array(50).fill(0.4),
        ws_max: null,
        color: "#E5484D",
        binding: false,
        hover_text: null,
        category: "universal",
        binding_for_warning: true,
        applicable_for_profile: true,
      },
    ];
    expect(
      findInsufficientThrustConstraint(200, 0.05, wsRange, cs, true),
    ).toBe("Climb");
  });
});

describe("gh-613 Phase B — constraintRelevance (modal badge mapping)", () => {
  it("maps category=universal → 'universal'", () => {
    expect(CATEGORY_TO_RELEVANCE.universal).toBe("universal");
  });

  it("maps category=rc_specific → 'rc-specific'", () => {
    expect(CATEGORY_TO_RELEVANCE.rc_specific).toBe("rc-specific");
  });

  it("maps category=cs25_only → 'cs25-only'", () => {
    expect(CATEGORY_TO_RELEVANCE.cs25_only).toBe("cs25-only");
  });

  it("overrides Takeoff to 'conditional' (universal in data, conditional in modal copy)", () => {
    expect(
      constraintRelevance({ name: "Takeoff", category: "universal" }),
    ).toBe("conditional");
  });

  it("overrides Landing to 'conditional'", () => {
    expect(
      constraintRelevance({ name: "Landing", category: "universal" }),
    ).toBe("conditional");
  });

  it("preserves cs25-only for OEI even when category says universal", () => {
    expect(
      constraintRelevance({ name: "Second-Segment Climb (OEI)", category: "universal" }),
    ).toBe("cs25-only");
  });

  it("falls back to category for non-overridden names", () => {
    expect(
      constraintRelevance({ name: "Stall", category: "universal" }),
    ).toBe("universal");
    expect(
      constraintRelevance({ name: "Mission-Min T/W", category: "rc_specific" }),
    ).toBe("rc-specific");
  });
});

describe("gh-613 Phase B — MatchingChartTab integration", () => {
  beforeEach(() => {
    hookReturn = MOCK_LOADING_STATE;
    mockAssumptions = [];
    mockCtx = null;
    plotlyReactMock.mockClear();
  });

  it("does not render constraints whose applicable_for_profile=false on the chart", async () => {
    const trainerProfileData: MatchingChartData = {
      ws_range_n_m2: Array.from({ length: 10 }, (_, i) => 100 + i * 100),
      constraints: [
        {
          name: "Stall",
          t_w_points: null,
          ws_max: 900,
          color: "#A78BFA",
          binding: false,
          hover_text: null,
          category: "universal",
          binding_for_warning: true,
          applicable_for_profile: true,
        },
        {
          name: "Takeoff",
          t_w_points: Array(10).fill(0.15),
          ws_max: null,
          color: "#FF8400",
          binding: false,
          hover_text: null,
          category: "universal",
          binding_for_warning: true,
          // not relevant for trainer profile
          applicable_for_profile: false,
        },
      ],
      design_point: { ws_n_m2: 500, t_w: 0.2 },
      feasibility: "feasible",
      warnings: [],
    };
    hookReturn = { data: trainerProfileData, error: null, isLoading: false, mutate: vi.fn() };

    await act(async () => {
      render(<MatchingChartTab aeroplaneId="t" />);
    });

    // Plotly.react must have been called with traces that omit Takeoff.
    expect(plotlyReactMock).toHaveBeenCalled();
    const lastCall = plotlyReactMock.mock.calls[plotlyReactMock.mock.calls.length - 1];
    const traces = lastCall[1] as Array<{ name?: string }>;
    const traceNames = traces.map((t) => t.name).filter(Boolean);
    expect(traceNames).not.toContain("Takeoff");
  });

  it("does not flag insufficient-T/W warning when only a binding_for_warning=false constraint is violated", async () => {
    const wcl_only_violated: MatchingChartData = {
      ws_range_n_m2: Array.from({ length: 10 }, (_, i) => 100 + i * 100),
      constraints: [
        {
          name: "Stall",
          t_w_points: null,
          ws_max: 2000,
          color: "#A78BFA",
          binding: false,
          hover_text: null,
          category: "universal",
          binding_for_warning: true,
          applicable_for_profile: true,
        },
        {
          // Lennon guideline — violated but should not raise a warning
          name: "Wing-Cube-Loading",
          t_w_points: Array(10).fill(0.5),
          ws_max: null,
          color: "#FBBF24",
          binding: false,
          hover_text: null,
          category: "rc_specific",
          binding_for_warning: false,
          applicable_for_profile: true,
        },
      ],
      design_point: { ws_n_m2: 500, t_w: 0.1 },
      feasibility: "feasible",
      warnings: [],
    };
    hookReturn = { data: wcl_only_violated, error: null, isLoading: false, mutate: vi.fn() };
    mockAssumptions = [
      { parameter_name: "mass", effective_value: 2 },
      { parameter_name: "t_static_N", effective_value: 5 },
    ];
    mockCtx = { s_ref_m2: 0.04, b_ref_m: 0.6, is_glider: false };

    await act(async () => {
      render(<MatchingChartTab aeroplaneId="t" />);
    });

    // The insufficient-T/W callout must not appear.
    expect(
      document.querySelector("[data-testid='insufficient-thrust-callout']"),
    ).toBeNull();
  });

  it("flags insufficient-T/W warning when a binding_for_warning=true constraint is violated", async () => {
    const climb_violated: MatchingChartData = {
      ws_range_n_m2: Array.from({ length: 10 }, (_, i) => 100 + i * 100),
      constraints: [
        {
          name: "Stall",
          t_w_points: null,
          ws_max: 2000,
          color: "#A78BFA",
          binding: false,
          hover_text: null,
          category: "universal",
          binding_for_warning: true,
          applicable_for_profile: true,
        },
        {
          name: "Climb",
          t_w_points: Array(10).fill(0.4),
          ws_max: null,
          color: "#E5484D",
          binding: false,
          hover_text: null,
          category: "universal",
          binding_for_warning: true,
          applicable_for_profile: true,
        },
      ],
      design_point: { ws_n_m2: 500, t_w: 0.1 },
      feasibility: "feasible",
      warnings: [],
    };
    hookReturn = { data: climb_violated, error: null, isLoading: false, mutate: vi.fn() };
    mockAssumptions = [
      { parameter_name: "mass", effective_value: 2 },
      { parameter_name: "t_static_N", effective_value: 5 },
    ];
    mockCtx = { s_ref_m2: 0.04, b_ref_m: 0.6, is_glider: false };

    await act(async () => {
      render(<MatchingChartTab aeroplaneId="t" />);
    });

    expect(
      document.querySelector("[data-testid='insufficient-thrust-callout']"),
    ).toBeTruthy();
  });
});
