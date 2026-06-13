/**
 * Unit tests for PowertrainTab + usePowertrainSolutionSpace hook (gh-976, gh-977).
 * Mocks: SWR hook, plotly.js-gl3d-dist-min, lucide-react.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import type {
  PowertrainSolutionSpaceResponse,
  SolutionSpaceAssumptions,
} from "@/hooks/usePowertrainSolutionSpace";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", { ...props, "data-testid": "icon" });
  return {
    AlertTriangle: icon,
    Loader2: icon,
  };
});

// Plotly dynamic import — stub that records calls
const plotlyReactMock = vi.fn().mockResolvedValue(undefined);
vi.mock("plotly.js-gl3d-dist-min", () => ({
  react: plotlyReactMock,
  purge: vi.fn(),
}));

// SWR hook mock — mutable via the let-binding pattern
let hookReturn: {
  data: PowertrainSolutionSpaceResponse | null | undefined;
  error: unknown;
  isLoading: boolean;
  mutate: ReturnType<typeof vi.fn>;
};

vi.mock("@/hooks/usePowertrainSolutionSpace", async (importActual) => {
  const actual = await importActual<typeof import("@/hooks/usePowertrainSolutionSpace")>();
  return {
    ...actual,
    usePowertrainSolutionSpace: () => hookReturn,
  };
});

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

function mkRow(
  cell_count: number,
  overrides: Partial<PowertrainSolutionSpaceResponse["rows"][number]> = {}
): PowertrainSolutionSpaceResponse["rows"][number] {
  return {
    cell_count,
    v_nom_v: cell_count * 3.7,
    v_sag_v: cell_count * 3.5,
    p_cruise_w: 100,
    p_top_w: 300,
    p_cruise_lo_w: 90,
    p_cruise_hi_w: 110,
    p_top_lo_w: 270,
    p_top_hi_w: 330,
    energy_wh: 20,
    capacity_mah_min: 2000 / cell_count,
    capacity_mah_min_lo: 1800 / cell_count,
    capacity_mah_min_hi: 2200 / cell_count,
    i_peak_a: 40 / cell_count,
    i_peak_lo_a: 36 / cell_count,
    i_peak_hi_a: 44 / cell_count,
    c_min: 8 / cell_count,
    c_min_lo: 7 / cell_count,
    c_min_hi: 9 / cell_count,
    esc_min_a: 56 / cell_count,
    esc_min_lo_a: 50 / cell_count,
    esc_min_hi_a: 62 / cell_count,
    motor_peak_w: 300,
    motor_cont_w: 100,
    kv_approx: 1200 / cell_count,
    has_motor_match: false,
    has_battery_match: false,
    has_esc_match: false,
    ...overrides,
  };
}

function mkRegion(cell_count: number): PowertrainSolutionSpaceResponse["feasible_regions"][number] {
  return {
    cell_count,
    capacity_floor_mah: 1500 / cell_count,
    i_peak_a: 40 / cell_count,
    capacity_curve_mah: [500, 1000, 2000, 4000],
    c_rate_curve: [20, 10, 5, 2.5],
  };
}

function mkSpec(cell_count: number): PowertrainSolutionSpaceResponse["shopping_specs"][number] {
  return {
    cell_count,
    battery_min_mah: 2000 / cell_count,
    battery_min_c: 8 / cell_count,
    battery_v_nom: cell_count * 3.7,
    esc_min_a: 56 / cell_count,
    motor_min_peak_w: 300,
    motor_cont_w: 100,
    kv_approx: 1200 / cell_count,
  };
}

const MOCK_DATA: PowertrainSolutionSpaceResponse = {
  rows: [mkRow(2), mkRow(3), mkRow(4), mkRow(6)],
  feasible_regions: [mkRegion(2), mkRegion(3), mkRegion(4), mkRegion(6)],
  shopping_specs: [mkSpec(2), mkSpec(3), mkSpec(4), mkSpec(6)],
  p_aero_cruise_w: 80,
  p_aero_top_w: 250,
  energy_wh: 18.5,
  v_cruise_mps: 14.0,
  v_top_mps: 22.0,
  t_target_min: 15,
  assumptions_used: {},
  warnings: [],
};

const MOCK_OK = { data: MOCK_DATA, error: null, isLoading: false, mutate: vi.fn() };
const MOCK_LOADING = { data: undefined, error: null, isLoading: true, mutate: vi.fn() };
const MOCK_ERROR_422 = {
  data: null,
  error: Object.assign(new Error("422"), { status: 422 }),
  isLoading: false,
  mutate: vi.fn(),
};
const MOCK_ERROR_500 = {
  data: null,
  error: Object.assign(new Error("500"), { status: 500 }),
  isLoading: false,
  mutate: vi.fn(),
};

// ---------------------------------------------------------------------------
// Import component after mocks are set up
// ---------------------------------------------------------------------------

import {
  PowertrainTab,
  conservativeSpec,
  conservativeMotorW,
} from "@/components/workbench/PowertrainTab";

// ---------------------------------------------------------------------------
// Hook query-string tests (import the real hook function, bypass SWR)
// ---------------------------------------------------------------------------

// Import the exported URL builder directly for pure unit tests (no hooks needed)
import { buildSolutionSpaceUrl } from "@/hooks/usePowertrainSolutionSpace";

describe("usePowertrainSolutionSpace — URL construction (buildSolutionSpaceUrl)", () => {
  it("builds URL with cell_counts as repeated params", () => {
    const assumptions: SolutionSpaceAssumptions = {
      cell_counts: [2, 4, 6],
      eta_prop_lo: 0.65,
      eta_prop_hi: 0.78,
      dod: 0.8,
    };
    const url = buildSolutionSpaceUrl("test-id", assumptions);

    expect(url).not.toBeNull();
    expect(url).toContain("cell_counts=2");
    expect(url).toContain("cell_counts=4");
    expect(url).toContain("cell_counts=6");
    expect(url).toContain("eta_prop_lo=0.65");
    expect(url).toContain("eta_prop_hi=0.78");
    expect(url).toContain("dod=0.8");

    // Verify all three cell counts present (repeated param pattern)
    const qs = url!.split("?")[1];
    const allParams = new URLSearchParams(qs);
    expect(allParams.getAll("cell_counts")).toEqual(["2", "4", "6"]);

    // Unused assumptions must not appear
    expect(url).not.toContain("rho=");
    expect(url).not.toContain("g=");
  });

  it("returns null when aeroplaneId is null", () => {
    const url = buildSolutionSpaceUrl(null, { cell_counts: [3] });
    expect(url).toBeNull();
  });

  it("encodes aeroplaneId correctly", () => {
    const url = buildSolutionSpaceUrl("abc-123", {});
    expect(url).toBe("/aeroplanes/abc-123/powertrain/solution-space");
  });

  it("omits query string when no assumptions are set", () => {
    const url = buildSolutionSpaceUrl("my-plane", {});
    expect(url).not.toContain("?");
  });
});

// ---------------------------------------------------------------------------
// PowertrainTab rendering tests
// ---------------------------------------------------------------------------

describe("PowertrainTab", () => {
  beforeEach(() => {
    hookReturn = MOCK_LOADING;
    plotlyReactMock.mockClear();
  });

  it("shows loading spinner", () => {
    hookReturn = MOCK_LOADING;
    render(<PowertrainTab aeroplaneId="test-id" />);
    expect(screen.getByText(/computing powertrain solution space/i)).toBeInTheDocument();
  });

  it("shows 422 error with recompute hint", () => {
    hookReturn = MOCK_ERROR_422;
    render(<PowertrainTab aeroplaneId="test-id" />);
    expect(screen.getByText(/assumption recompute first/i)).toBeInTheDocument();
  });

  it("shows generic error for 500", () => {
    hookReturn = MOCK_ERROR_500;
    render(<PowertrainTab aeroplaneId="test-id" />);
    expect(screen.getByText(/powertrain solution space unavailable/i)).toBeInTheDocument();
  });

  it("renders all cell-count rows from mock data", () => {
    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);
    expect(screen.getByTestId("solution-row-2")).toBeInTheDocument();
    expect(screen.getByTestId("solution-row-3")).toBeInTheDocument();
    expect(screen.getByTestId("solution-row-4")).toBeInTheDocument();
    expect(screen.getByTestId("solution-row-6")).toBeInTheDocument();
  });

  it("column Peak-A filter reduces visible rows (conservative i_peak_hi_a)", () => {
    // Filters compare against the CONSERVATIVE worst-case Peak A = i_peak_hi_a.
    // 2S: 44/2 = 22A; 3S ≈ 14.67A; 4S = 11A; 6S ≈ 7.33A
    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);

    const filterInput = screen.getByTestId("filter-peak-a");
    // Filter to Peak A ≤ 15 → hides 2S (22A) but keeps 3S (~14.67A), 4S, 6S
    fireEvent.change(filterInput, { target: { value: "15" } });

    expect(screen.queryByTestId("solution-row-2")).not.toBeInTheDocument();
    expect(screen.getByTestId("solution-row-3")).toBeInTheDocument();
    expect(screen.getByTestId("solution-row-4")).toBeInTheDocument();
    expect(screen.getByTestId("solution-row-6")).toBeInTheDocument();
  });

  it("mAh filter reduces visible rows (conservative ceil(capacity_mah_min_hi))", () => {
    // Conservative mAh min = ceil(capacity_mah_min_hi = 2200/cell):
    // 2S = 1100; 3S = ceil(733.3) = 734; 4S = 550; 6S = ceil(366.7) = 367
    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);

    const filterInput = screen.getByTestId("filter-mah");
    // Filter mAh ≤ 400 → show only 6S (367); hide 2S/3S/4S
    fireEvent.change(filterInput, { target: { value: "400" } });

    expect(screen.queryByTestId("solution-row-2")).not.toBeInTheDocument();
    expect(screen.queryByTestId("solution-row-3")).not.toBeInTheDocument();
    expect(screen.queryByTestId("solution-row-4")).not.toBeInTheDocument();
    expect(screen.getByTestId("solution-row-6")).toBeInTheDocument();
  });

  it("catalog-only toggle hides rows with no matches", () => {
    // All rows in MOCK_DATA have has_motor_match/battery/esc = false
    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);

    const toggle = screen.getByTestId("filter-catalog-only");
    fireEvent.click(toggle);

    // All rows should be hidden — empty message appears
    expect(screen.getByTestId("solution-table-empty")).toBeInTheDocument();
    expect(screen.queryByTestId("solution-row-2")).not.toBeInTheDocument();
  });

  it("catalog-only toggle keeps rows with at least one match", () => {
    const dataWithMatch: PowertrainSolutionSpaceResponse = {
      ...MOCK_DATA,
      rows: [
        mkRow(3, { has_motor_match: true }),
        mkRow(4, { has_battery_match: false, has_motor_match: false, has_esc_match: false }),
      ],
      shopping_specs: [mkSpec(3), mkSpec(4)],
      feasible_regions: [mkRegion(3), mkRegion(4)],
    };
    hookReturn = { data: dataWithMatch, error: null, isLoading: false, mutate: vi.fn() };
    render(<PowertrainTab aeroplaneId="test-id" />);

    const toggle = screen.getByTestId("filter-catalog-only");
    fireEvent.click(toggle);

    expect(screen.getByTestId("solution-row-3")).toBeInTheDocument();
    expect(screen.queryByTestId("solution-row-4")).not.toBeInTheDocument();
  });

  it("clicking a row selects it and updates shopping spec", () => {
    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);

    // Initially, 2S is auto-selected (first row)
    const specLine2S = screen.getByTestId("shopping-spec-line");
    expect(specLine2S).toHaveTextContent("2S");

    // Click the 4S row
    fireEvent.click(screen.getByTestId("solution-row-4"));

    // Shopping spec should now show 4S
    const specLine4S = screen.getByTestId("shopping-spec-line");
    expect(specLine4S).toHaveTextContent("4S");
  });

  it("shopping spec shows CONSERVATIVE rounded-up values for selected row", () => {
    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);

    // First row is 2S, auto-selected. Conservative (worst-case, rounded-up):
    //   ESC   = ceil(esc_min_hi_a = 62/2 = 31)            = 31 A
    //   mAh   = ceil(capacity_mah_min_hi = 2200/2 = 1100) = 1100 mAh
    //   C     = ceil(c_min_hi = 9/2 = 4.5)                = 5 C
    //   Motor = ceil(p_aero_top_w / eta_prop_lo = 250/0.65) = 385 W
    //   V_nom = 7.4 V, KV = 600 (from shopping spec)
    const spec = screen.getByTestId("shopping-spec-line");
    expect(spec).toHaveTextContent("ESC ≥ 31 A");
    expect(spec).toHaveTextContent("1100 mAh");
    expect(spec).toHaveTextContent("≥5C");
    expect(spec).toHaveTextContent("385 W");
    expect(spec).toHaveTextContent("7.4");
    expect(spec).toHaveTextContent("600");
  });

  it("shows warnings banner when warnings are present", () => {
    const dataWithWarnings: PowertrainSolutionSpaceResponse = {
      ...MOCK_DATA,
      warnings: ["Mission speed not set — using defaults.", "No polar data found."],
    };
    hookReturn = { data: dataWithWarnings, error: null, isLoading: false, mutate: vi.fn() };
    render(<PowertrainTab aeroplaneId="test-id" />);

    const banner = screen.getByTestId("powertrain-warnings");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent("Mission speed not set");
    expect(banner).toHaveTextContent("No polar data found");
  });

  it("does not show warnings banner when warnings array is empty", () => {
    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);
    expect(screen.queryByTestId("powertrain-warnings")).not.toBeInTheDocument();
  });

  it("renders the feasible-region plot container", () => {
    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);
    expect(screen.getByTestId("powertrain-feasible-region-plot")).toBeInTheDocument();
  });

  it("renders assumption controls", () => {
    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);
    expect(screen.getByTestId("assumption-controls")).toBeInTheDocument();
  });

  it("renders mission invariants when data is loaded", () => {
    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);
    // V_cruise, V_top, t_target from MOCK_DATA
    expect(screen.getByText("14.0 m/s")).toBeInTheDocument();
    expect(screen.getByText("22.0 m/s")).toBeInTheDocument();
    expect(screen.getByText("15 min")).toBeInTheDocument();
    expect(screen.getByText("80 W")).toBeInTheDocument(); // p_aero_cruise_w
  });
});

// ---------------------------------------------------------------------------
// FeasibleRegionPlot: Plotly trace construction (structural test)
// ---------------------------------------------------------------------------

describe("FeasibleRegionPlot — Plotly call structure", () => {
  beforeEach(() => {
    plotlyReactMock.mockClear();
  });

  it("calls Plotly.react with traces for each region", async () => {
    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);

    // Wait for async Plotly import in useEffect
    await new Promise((r) => setTimeout(r, 50));

    // plotlyReactMock is called once by FeasibleRegionPlot
    expect(plotlyReactMock).toHaveBeenCalled();

    const [, traces] = plotlyReactMock.mock.calls[0];
    // Should have traces for 4 regions: floor curve + vertical line + marker = 3 per region
    expect(traces.length).toBeGreaterThanOrEqual(4 * 3);

    // Verify marker traces have customdata (cell_count) for click selection
    const markerTraces = traces.filter(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (t: any) => t.mode === "markers+text" && t.customdata != null
    );
    expect(markerTraces.length).toBe(4);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const cellCounts = markerTraces.map((t: any) => t.customdata[0]);
    expect(cellCounts).toContain(2);
    expect(cellCounts).toContain(3);
    expect(cellCounts).toContain(4);
    expect(cellCounts).toContain(6);

    // Markers must sit at the CONSERVATIVE worst-case point
    // (ceil(capacity_mah_min_hi), ceil(c_min_hi)). For 2S:
    //   x = ceil(2200/2) = 1100, y = ceil(9/2 = 4.5) = 5
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const marker2S = markerTraces.find((t: any) => t.customdata[0] === 2);
    expect(marker2S.x[0]).toBe(1100);
    expect(marker2S.y[0]).toBe(5);
  });

  it("highlights the auto-selected (first) cell count with star marker on initial render", async () => {
    // On initial render, first row (2S) is auto-selected.
    // Plotly should render the 2S marker as star and others as circle.
    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);
    await new Promise((r) => setTimeout(r, 50));

    expect(plotlyReactMock).toHaveBeenCalled();
    const [, traces] = plotlyReactMock.mock.calls[0];

    // 2S marker → selected → star
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const markerFor2S = traces.find((t: any) => t.customdata?.[0] === 2);
    expect(markerFor2S?.marker?.symbol).toBe("star");

    // 4S marker → not selected → circle
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const markerFor4S = traces.find((t: any) => t.customdata?.[0] === 4);
    expect(markerFor4S?.marker?.symbol).toBe("circle");
  });

  it("layout annotation contains mission metadata inside figure", async () => {
    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);
    await new Promise((r) => setTimeout(r, 50));

    const [, , layout] = plotlyReactMock.mock.calls[0];
    // Per project convention: mission params go INSIDE the figure (annotation)
    const annotations = layout.annotations ?? [];
    const missionAnnotation = annotations.find(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (a: any) => typeof a.text === "string" && a.text.includes("V_cruise")
    );
    expect(missionAnnotation).toBeDefined();
    expect(missionAnnotation.text).toContain("V_top");
    expect(missionAnnotation.text).toContain("14.0 m/s"); // v_cruise_mps from MOCK_DATA
  });

  it("reserves bottom margin so the metadata annotation is not clipped", async () => {
    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);
    await new Promise((r) => setTimeout(r, 50));

    const [, , layout] = plotlyReactMock.mock.calls[0];
    // Bottom annotation sits at y:-0.13; margin.b must be generous (>= 65)
    // to keep it fully visible.
    expect(layout.margin.b).toBeGreaterThanOrEqual(65);
  });
});

// ---------------------------------------------------------------------------
// plotly_click listener: bind once, clean up on unmount (no accumulation)
// ---------------------------------------------------------------------------

describe("FeasibleRegionPlot — plotly_click listener lifecycle", () => {
  beforeEach(() => {
    plotlyReactMock.mockClear();
  });

  it("binds the click listener once and removes it on cleanup", async () => {
    // Patch the jsdom container so it exposes Plotly's `.on()` / `.removeAllListeners()`.
    const onSpy = vi.fn();
    const removeAllSpy = vi.fn();
    const origCreate = document.createElement.bind(document);
    const createSpy = vi
      .spyOn(document, "createElement")
      .mockImplementation((tag: string, opts?: ElementCreationOptions) => {
        const el = origCreate(tag, opts);
        if (tag === "div") {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (el as any).on = onSpy;
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (el as any).removeAllListeners = removeAllSpy;
        }
        return el;
      });

    hookReturn = MOCK_OK;
    const { unmount } = render(<PowertrainTab aeroplaneId="test-id" />);
    await new Promise((r) => setTimeout(r, 50));

    // The click handler is bound exactly once for plotly_click.
    const clickBinds = onSpy.mock.calls.filter((c) => c[0] === "plotly_click");
    expect(clickBinds.length).toBe(1);

    unmount();
    expect(removeAllSpy).toHaveBeenCalledWith("plotly_click");

    createSpy.mockRestore();
  });

  it("does not re-bind the click listener when the selection changes", async () => {
    const onSpy = vi.fn();
    const removeAllSpy = vi.fn();
    const origCreate = document.createElement.bind(document);
    const createSpy = vi
      .spyOn(document, "createElement")
      .mockImplementation((tag: string, opts?: ElementCreationOptions) => {
        const el = origCreate(tag, opts);
        if (tag === "div") {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (el as any).on = onSpy;
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (el as any).removeAllListeners = removeAllSpy;
        }
        return el;
      });

    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);
    await new Promise((r) => setTimeout(r, 50));

    const bindsBefore = onSpy.mock.calls.filter((c) => c[0] === "plotly_click").length;
    expect(bindsBefore).toBe(1);

    // Change the selection by clicking a different table row.
    fireEvent.click(screen.getByTestId("solution-row-4"));
    await new Promise((r) => setTimeout(r, 50));

    // Selection change re-draws the figure (marker re-style) but must NOT
    // re-bind the click listener — the effect that binds it does not depend
    // on selectedCellCount.
    const bindsAfter = onSpy.mock.calls.filter((c) => c[0] === "plotly_click").length;
    expect(bindsAfter).toBe(1);

    createSpy.mockRestore();
  });
});

// ---------------------------------------------------------------------------
// Orphaned-selection reset + NaN-guarded numeric inputs
// ---------------------------------------------------------------------------

describe("PowertrainTab — selection + input edge cases", () => {
  beforeEach(() => {
    plotlyReactMock.mockClear();
  });

  it("resets the selection when the selected cell-count disappears from new data", () => {
    hookReturn = MOCK_OK;
    const { rerender } = render(<PowertrainTab aeroplaneId="test-id" />);

    // Select 6S explicitly.
    fireEvent.click(screen.getByTestId("solution-row-6"));
    expect(screen.getByTestId("shopping-spec-line")).toHaveTextContent("6S");

    // New data no longer contains 6S → selection must fall back to first row (3S).
    const dataWithout6S: PowertrainSolutionSpaceResponse = {
      ...MOCK_DATA,
      rows: [mkRow(3), mkRow(4)],
      feasible_regions: [mkRegion(3), mkRegion(4)],
      shopping_specs: [mkSpec(3), mkSpec(4)],
    };
    hookReturn = { data: dataWithout6S, error: null, isLoading: false, mutate: vi.fn() };
    rerender(<PowertrainTab aeroplaneId="test-id" />);

    // Shopping spec now reflects the first available row (3S), not the orphaned 6S.
    expect(screen.getByTestId("shopping-spec-line")).toHaveTextContent("3S");
    expect(screen.queryByTestId("solution-row-6")).not.toBeInTheDocument();
  });

  it("clearing a numeric assumption input omits it (no NaN serialized)", () => {
    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);

    const tTarget = screen.getByTestId("t-target-input") as HTMLInputElement;
    // Clearing the field must NOT throw and must not leave a NaN; the value
    // becomes undefined and the input falls back to its default on re-render
    // (undefined → `assumptions.t_target_min ?? 15`).
    fireEvent.change(tTarget, { target: { value: "" } });

    expect((screen.getByTestId("t-target-input") as HTMLInputElement).value).toBe("15");
  });
});

// ---------------------------------------------------------------------------
// Conservative (worst-case, rounded-up) minimum specs — pure functions
// ---------------------------------------------------------------------------

describe("conservativeSpec / conservativeMotorW", () => {
  it("uses the worst-case _hi band and rounds UP so a part bought at the value is sufficient", () => {
    // 2S mock row (real field names): i_peak_hi_a=22, esc_min_hi_a=31,
    // c_min_hi=4.5, capacity_mah_min_hi=1100
    const row = mkRow(2);
    const spec = conservativeSpec(row, 250, 0.65);
    expect(spec.peakA).toBe(22); // i_peak_hi_a, not the mid i_peak_a (=20)
    expect(spec.escMinA).toBe(31); // ceil(esc_min_hi_a = 31)
    expect(spec.minC).toBe(5); // ceil(c_min_hi = 4.5)
    expect(spec.mahMin).toBe(1100); // ceil(capacity_mah_min_hi = 1100)
    expect(spec.motorW).toBe(385); // ceil(250 / 0.65)
  });

  it("does NOT divide mAh by DoD (DoD already in energy_wh upstream)", () => {
    // capacity_mah_min_hi is already the rated pack capacity; ceil only.
    const row = mkRow(4); // capacity_mah_min_hi = 2200/4 = 550
    const spec = conservativeSpec(row, 250, 0.65);
    expect(spec.mahMin).toBe(550);
  });

  it("rounds a fractional ceil example up (5.46A → 6A) like the real UAT data", () => {
    const row = mkRow(2, { esc_min_hi_a: 5.46 });
    const spec = conservativeSpec(row, 250, 0.65);
    expect(spec.escMinA).toBe(6);
  });

  it("conservativeMotorW = ceil(pAeroTop / etaPropLo); degrades gracefully at eta<=0", () => {
    expect(conservativeMotorW(250, 0.65)).toBe(385);
    expect(conservativeMotorW(250, 0)).toBe(250); // no divide-by-zero
  });

  it("falls back to the mid value when the _hi band field is absent (contract drift)", () => {
    // Simulate a backend that dropped the band fields: only mid values present.
    // Strip the band keys via an unknown cast (object-literal @ts-expect-error
    // can't target individual properties).
    const base = mkRow(2) as unknown as Record<string, unknown>;
    delete base.i_peak_hi_a;
    delete base.esc_min_hi_a;
    delete base.c_min_hi;
    delete base.capacity_mah_min_hi;
    const row = base as unknown as PowertrainSolutionSpaceResponse["rows"][number];
    const spec = conservativeSpec(row, 250, 0.65);
    // Falls back to mid: i_peak_a=20, esc_min_a=28→28, c_min=4→4, cap=1000→1000
    expect(spec.peakA).toBe(20);
    expect(spec.escMinA).toBe(28);
    expect(spec.minC).toBe(4);
    expect(spec.mahMin).toBe(1000);
  });

  it("returns null (renders '—') when neither band nor mid value is usable", () => {
    const base = mkRow(2) as unknown as Record<string, unknown>;
    delete base.i_peak_hi_a;
    delete base.i_peak_a;
    const row = base as unknown as PowertrainSolutionSpaceResponse["rows"][number];
    const spec = conservativeSpec(row, 250, 0.65);
    expect(spec.peakA).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Table renders the conservative values (not the mid band)
// ---------------------------------------------------------------------------

describe("SolutionTable — conservative cell values", () => {
  beforeEach(() => {
    plotlyReactMock.mockClear();
  });

  it("shows conservative ESC / mAh / Min C-rating / Peak A / Motor in the 2S row", () => {
    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);

    const row2S = screen.getByTestId("solution-row-2");
    // Conservative 2S: Peak 22.0, ESC 31, mAh 1100, Min C 5, Motor 385.
    expect(row2S).toHaveTextContent("22.0");
    expect(row2S).toHaveTextContent("31");
    expect(row2S).toHaveTextContent("1100");
    expect(row2S).toHaveTextContent("5");
    expect(row2S).toHaveTextContent("385");
  });

  it("renames the C-min header to 'Min C-rating' with a guidance tooltip", () => {
    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);
    const header = screen.getByText("Min C-rating");
    expect(header).toBeInTheDocument();
    expect(header).toHaveAttribute("title", "minimum battery C-rating you need");
  });
});

// ---------------------------------------------------------------------------
// Hobbyist labels / guidance + Scholz scope note
// ---------------------------------------------------------------------------

describe("PowertrainTab — labels, guidance, scope note", () => {
  beforeEach(() => {
    plotlyReactMock.mockClear();
  });

  it("renders the Phase-1 scope disclaimer", () => {
    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);
    const note = screen.getByTestId("powertrain-scope-note");
    expect(note).toHaveTextContent(/Phase 1/i);
    expect(note).toHaveTextContent(/static-thrust/i);
    expect(note).toHaveTextContent(/Phase 2/i);
  });

  it("renders the hobbyist how-to callout above the table", () => {
    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);
    const callout = screen.getByTestId("powertrain-table-callout");
    expect(callout).toHaveTextContent(/Pick a cell count, then shop/i);
    expect(callout).toHaveTextContent(/ESC ≥ ESC min/i);
  });

  it("labels the assumption controls for hobbyists (Prop efficiency, DoD tooltip)", () => {
    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);
    expect(screen.getByText("Prop efficiency [lo / hi]")).toBeInTheDocument();
    const dod = screen.getByText("DoD");
    expect(dod).toHaveAttribute("title", "Depth of discharge — usable battery %");
  });

  it("marks the invariants row as 'Computed from mission'", () => {
    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);
    expect(screen.getByTestId("invariants-source-label")).toHaveTextContent(
      /Computed from mission/i
    );
  });

  it("shows the V_top '(from Mission)' hint when v_top is auto-derived", () => {
    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);
    // assumptions start with no v_top_mps → auto-derived.
    expect(screen.getByTestId("v-top-from-mission")).toBeInTheDocument();

    // Setting V_top removes the hint.
    fireEvent.change(screen.getByTestId("v-top-input"), { target: { value: "25" } });
    expect(screen.queryByTestId("v-top-from-mission")).not.toBeInTheDocument();
  });

  it("adds the 'on/above the curve' feasibility annotation to the plot", async () => {
    hookReturn = MOCK_OK;
    render(<PowertrainTab aeroplaneId="test-id" />);
    await new Promise((r) => setTimeout(r, 50));

    const [, , layout] = plotlyReactMock.mock.calls[0];
    const annotations = layout.annotations ?? [];
    const feasNote = annotations.find(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (a: any) => typeof a.text === "string" && a.text.includes("on/above the curve")
    );
    expect(feasNote).toBeDefined();
  });
});
