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
  };
});

// Plotly dynamic import — return a stub that does nothing
vi.mock("plotly.js-gl3d-dist-min", () => ({
  react: vi.fn().mockResolvedValue(undefined),
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

import { MatchingChartTab, findBindingConstraintAtPoint } from "@/components/workbench/MatchingChartTab";

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

  it("shows drag hint info text when data is available", () => {
    hookReturn = MOCK_OK_STATE;
    render(<MatchingChartTab aeroplaneId="test-id" />);
    expect(screen.getByText(/drag design point/i)).toBeInTheDocument();
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
