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
    expect(screen.getByText("Elevator (°)")).toBeTruthy();
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

  it("sorting every column (mixed surfaces, unknown roles, null aero, both directions)", async () => {
    const user = userEvent.setup();
    // A second OP with a known + two unknown-role surfaces and NO aero — exercises
    // the role-rank fallback, the absent-surface / null-coefficient (?? 0) branches,
    // and the asc↔desc toggle for every column.
    const mixed = makeOp({
      id: 8,
      name: "mixed",
      alpha: 7 * RAD,
      trim_enrichment: {
        analysis_goal: "Mixed",
        result_summary: "",
        trim_method: "opti",
        trim_score: 0.04,
        trim_residuals: {},
        deflection_reserves: {
          "[aileron]Aileron": {
            deflection_deg: 6.0,
            max_pos_deg: 20,
            max_neg_deg: 20,
            usage_fraction: 0.3,
          },
          "[winglet]Winglet": {
            deflection_deg: 1.0,
            max_pos_deg: 10,
            max_neg_deg: 10,
            usage_fraction: 0.1,
          },
          "[spoiler]Spoiler": {
            deflection_deg: 2.0,
            max_pos_deg: 15,
            max_neg_deg: 15,
            usage_fraction: 0.13,
          },
        },
        design_warnings: [],
        effectiveness: {},
        stability_classification: null,
        mixer_values: {},
        aero_coefficients: {}, // null CL/CD/LD → "—" + ?? 0 sort branches
      },
    });
    render(<OpComparisonTable points={[POINTS[0], mixed]} />);
    // role-ordered: known roles first (Elevator, Aileron), unknown last alpha-sorted (Spoiler, Winglet)
    for (const label of [
      "OP",
      "Elevator (°)",
      "Aileron (°)",
      "Spoiler (°)",
      "Winglet (°)",
      "CL",
      "CD",
      "L/D",
      "Reserve",
      "α (°)",
    ]) {
      await user.click(screen.getByText(label)); // desc
      await user.click(screen.getByText(label)); // asc (toggle)
      expect(screen.getAllByTestId(/^op-row-/)).toHaveLength(2);
    }
  });

  it("shows — for missing coefficients and absent surfaces", () => {
    const partial = makeOp({
      id: 7,
      name: "partial",
      alpha: 4 * RAD,
      trim_enrichment: {
        analysis_goal: "Partial",
        result_summary: "",
        trim_method: "opti",
        trim_score: 0.03,
        trim_residuals: {},
        // only a rudder reserve; no elevator, and no aero_coefficients
        deflection_reserves: {
          "[rudder]Rudder": {
            deflection_deg: 5.0,
            max_pos_deg: 30,
            max_neg_deg: 30,
            usage_fraction: 0.17,
          },
        },
        design_warnings: [],
        effectiveness: {},
        stability_classification: null,
        mixer_values: {},
        aero_coefficients: {},
      },
    });
    // POINTS[0] has elevator → union columns are Elevator + Rudder.
    render(<OpComparisonTable points={[POINTS[0], partial]} />);
    // partial row: Elevator absent → "—"; CL/CD/LD absent → "—" (multiple dashes)
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(3);
  });

  it("renders a column for EVERY control surface, not just elevator (gh-863)", () => {
    const op = makeOp({
      id: 9,
      name: "turn",
      alpha: 6 * RAD,
      trim_enrichment: {
        analysis_goal: "Turn",
        result_summary: "",
        trim_method: "opti",
        trim_score: 0.02,
        trim_residuals: {},
        deflection_reserves: {
          "[elevator]Elevator": {
            deflection_deg: -3.0,
            max_pos_deg: 25,
            max_neg_deg: 25,
            usage_fraction: 0.12,
          },
          "[aileron]Aileron": {
            deflection_deg: 8.0,
            max_pos_deg: 20,
            max_neg_deg: 20,
            usage_fraction: 0.4,
          },
          "[rudder]Rudder": {
            deflection_deg: 4.0,
            max_pos_deg: 30,
            max_neg_deg: 30,
            usage_fraction: 0.133,
          },
        },
        design_warnings: [],
        effectiveness: {},
        stability_classification: null,
        mixer_values: {},
        aero_coefficients: { CL: 0.6, CD: 0.04 },
      },
    });
    render(<OpComparisonTable points={[op]} />);

    // a header per surface (display names, role-ordered elevator→aileron→rudder)
    expect(screen.getByText("Elevator (°)")).toBeTruthy();
    expect(screen.getByText("Aileron (°)")).toBeTruthy();
    expect(screen.getByText("Rudder (°)")).toBeTruthy();
    // and their deflection values are shown
    expect(screen.getByText("-3.0")).toBeTruthy();
    expect(screen.getByText("8.0")).toBeTruthy();
    expect(screen.getByText("4.0")).toBeTruthy();
    // Reserve is the binding (max) authority used across surfaces → aileron 40%
    expect(screen.getByText("40%")).toBeTruthy();
  });

  it("renders greyed placeholder rows for COMPUTING points (gh-865)", () => {
    const computing = makeOp({
      id: -1,
      name: "max_range",
      status: "COMPUTING",
      trim_enrichment: null,
    });
    render(<OpComparisonTable points={[POINTS[0], computing]} />);
    // the solved row is shown normally
    expect(screen.getByTestId("op-row-1")).toBeTruthy();
    // the computing target appears as a greyed placeholder with a live label
    const placeholder = screen.getByTestId("op-computing-max_range");
    expect(placeholder).toBeTruthy();
    expect(placeholder.className).toContain("animate-pulse");
    expect(screen.getByText("rechnet…")).toBeTruthy();
  });

  it("renders the table when ONLY computing placeholders exist (gh-865)", () => {
    // No trimmed rows yet — but the table must still appear so the user sees
    // the greyed rows immediately at the start of a streaming generation.
    const computing = [
      makeOp({ id: -1, name: "cruise", status: "COMPUTING", trim_enrichment: null }),
      makeOp({ id: -2, name: "loiter", status: "COMPUTING", trim_enrichment: null }),
    ];
    render(<OpComparisonTable points={computing} />);
    expect(screen.getByText("OP Comparison")).toBeTruthy();
    expect(screen.getByTestId("op-computing-cruise")).toBeTruthy();
    expect(screen.getByTestId("op-computing-loiter")).toBeTruthy();
    // no solved data rows
    expect(screen.queryAllByTestId(/^op-row-/)).toHaveLength(0);
  });
});
