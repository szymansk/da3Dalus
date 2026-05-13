/**
 * Unit tests for MatchingChartTab component — gh-492.
 * Mocks the useMatchingChart hook and plotly import to avoid browser env plumbing.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import type { MatchingChartData } from "@/hooks/useMatchingChart";

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

import { MatchingChartTab } from "@/components/workbench/MatchingChartTab";

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
const MOCK_OK_STATE = { data: MOCK_CESSNA, error: null, isLoading: false, mutate: vi.fn() };
const MOCK_INFEASIBLE: MatchingChartData = {
  ...MOCK_CESSNA,
  design_point: { ws_n_m2: 660.07, t_w: 0.05 },
  feasibility: "infeasible_below_constraints",
};

// ── Tests ─────────────────────────────────────────────────────────────────────

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
});
