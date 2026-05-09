import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AnalysisGoalCard } from "@/components/workbench/trim-interpretation/AnalysisGoalCard";
import type { TrimEnrichment } from "@/hooks/useOperatingPoints";

const MOCK_ENRICHMENT: TrimEnrichment = {
  analysis_goal: "Can the aircraft trim near stall?",
  result_summary: "Trimmed at α=12.3° with 82% elevator reserve",
  trim_method: "opti",
  trim_score: 0.02,
  trim_residuals: { cm: 0.001 },
  deflection_reserves: {
    "[elevator]Elevator": {
      deflection_deg: -5.0,
      max_pos_deg: 25.0,
      max_neg_deg: 25.0,
      usage_fraction: 0.18,
    },
  },
  design_warnings: [],
  effectiveness: {},
  stability_classification: null,
  mixer_values: {},
  aero_coefficients: { CL: 1.2, CD: 0.06 },
};

describe("AnalysisGoalCard", () => {
  it("renders analysis goal and result summary", () => {
    render(<AnalysisGoalCard enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByText("Can the aircraft trim near stall?")).toBeTruthy();
    expect(screen.getByText("Trimmed at α=12.3° with 82% elevator reserve")).toBeTruthy();
  });

  it("shows green badge when all reserves below 60%", () => {
    render(<AnalysisGoalCard enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByTestId("status-badge")).toHaveClass("bg-emerald-500");
  });

  it("shows amber badge when any reserve between 60-80%", () => {
    const amber = {
      ...MOCK_ENRICHMENT,
      deflection_reserves: {
        "[elevator]Elevator": {
          deflection_deg: -17.0,
          max_pos_deg: 25.0,
          max_neg_deg: 25.0,
          usage_fraction: 0.68,
        },
      },
    };
    render(<AnalysisGoalCard enrichment={amber} />);
    expect(screen.getByTestId("status-badge")).toHaveClass("bg-amber-500");
  });

  it("shows red badge when any reserve above 80%", () => {
    const red = {
      ...MOCK_ENRICHMENT,
      deflection_reserves: {
        "[elevator]Elevator": {
          deflection_deg: -22.0,
          max_pos_deg: 25.0,
          max_neg_deg: 25.0,
          usage_fraction: 0.88,
        },
      },
    };
    render(<AnalysisGoalCard enrichment={red} />);
    expect(screen.getByTestId("status-badge")).toHaveClass("bg-red-500");
  });

  it("shows red badge when design_warnings contain critical level", () => {
    const critical = {
      ...MOCK_ENRICHMENT,
      design_warnings: [
        { level: "critical" as const, category: "authority", surface: null, message: "Near limit" },
      ],
    };
    render(<AnalysisGoalCard enrichment={critical} />);
    expect(screen.getByTestId("status-badge")).toHaveClass("bg-red-500");
  });

  it("renders nothing when enrichment is null", () => {
    const { container } = render(<AnalysisGoalCard enrichment={null} />);
    expect(container.firstChild).toBeNull();
  });
});
