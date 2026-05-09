import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OpComparisonTable } from "@/components/workbench/trim-interpretation/OpComparisonTable";
import type { StoredOperatingPoint } from "@/hooks/useOperatingPoints";

const RAD = Math.PI / 180;

function makeOp(overrides: Partial<StoredOperatingPoint> & { name: string }): StoredOperatingPoint {
  return {
    id: 1,
    description: "",
    aircraft_id: 1,
    config: "clean",
    status: "TRIMMED",
    warnings: [],
    controls: {},
    velocity: 15,
    alpha: 5 * RAD,
    beta: 0,
    p: 0,
    q: 0,
    r: 0,
    xyz_ref: [0, 0, 0],
    altitude: 0,
    control_deflections: null,
    trim_enrichment: null,
    ...overrides,
  };
}

const POINTS: StoredOperatingPoint[] = [
  makeOp({
    id: 1,
    name: "cruise",
    alpha: 3 * RAD,
    trim_enrichment: {
      analysis_goal: "Cruise trim",
      result_summary: "",
      trim_method: "opti",
      trim_score: 0.01,
      trim_residuals: {},
      deflection_reserves: {
        "[elevator]Elevator": {
          deflection_deg: -2.5,
          max_pos_deg: 25,
          max_neg_deg: 25,
          usage_fraction: 0.1,
        },
      },
      design_warnings: [],
      effectiveness: {},
      stability_classification: null,
      mixer_values: {},
      aero_coefficients: { CL: 0.45, CD: 0.032 },
    },
  }),
  makeOp({
    id: 2,
    name: "stall_approach",
    alpha: 12 * RAD,
    trim_enrichment: {
      analysis_goal: "Near stall",
      result_summary: "",
      trim_method: "opti",
      trim_score: 0.05,
      trim_residuals: {},
      deflection_reserves: {
        "[elevator]Elevator": {
          deflection_deg: -20.0,
          max_pos_deg: 25,
          max_neg_deg: 25,
          usage_fraction: 0.8,
        },
      },
      design_warnings: [],
      effectiveness: {},
      stability_classification: null,
      mixer_values: {},
      aero_coefficients: { CL: 1.3, CD: 0.09 },
    },
  }),
  makeOp({
    id: 3,
    name: "untrimmed",
    status: "NOT_TRIMMED",
    trim_enrichment: null,
  }),
];

describe("OpComparisonTable", () => {
  it("renders table headers", () => {
    render(<OpComparisonTable points={POINTS} />);
    expect(screen.getByText("OP")).toBeTruthy();
    expect(screen.getByText("α (°)")).toBeTruthy();
    expect(screen.getByText("Elev (°)")).toBeTruthy();
    expect(screen.getByText("Reserve")).toBeTruthy();
    expect(screen.getByText("CL")).toBeTruthy();
    expect(screen.getByText("CD")).toBeTruthy();
    expect(screen.getByText("L/D")).toBeTruthy();
  });

  it("only renders trimmed OPs with enrichment", () => {
    render(<OpComparisonTable points={POINTS} />);
    expect(screen.getByText("cruise")).toBeTruthy();
    expect(screen.getByText("stall_approach")).toBeTruthy();
    expect(screen.queryByText("untrimmed")).toBeNull();
  });

  it("computes L/D from CL and CD", () => {
    render(<OpComparisonTable points={POINTS} />);
    // cruise: CL=0.45 / CD=0.032 = 14.1
    expect(screen.getByText("14.1")).toBeTruthy();
  });

  it("highlights worst-case row (highest usage_fraction)", () => {
    render(<OpComparisonTable points={POINTS} />);
    const worstRow = screen.getByTestId("op-row-2");
    expect(worstRow.className).toContain("red");
  });

  it("sorts by column on header click", async () => {
    const user = userEvent.setup();
    render(<OpComparisonTable points={POINTS} />);
    const alphaHeader = screen.getByText("α (°)");
    await user.click(alphaHeader);
    const rows = screen.getAllByTestId(/^op-row-/);
    expect(rows).toHaveLength(2);
  });

  it("renders nothing when no trimmed points exist", () => {
    const untrimmed = [makeOp({ name: "x", status: "NOT_TRIMMED" })];
    const { container } = render(<OpComparisonTable points={untrimmed} />);
    expect(container.firstChild).toBeNull();
  });
});
