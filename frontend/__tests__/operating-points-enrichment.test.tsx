import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  AnalysisGoalCard,
  ControlAuthorityChart,
  DesignWarningBadges,
} from "@/components/workbench/trim-interpretation";
import type { TrimEnrichment } from "@/hooks/useOperatingPoints";

vi.mock("plotly.js-gl3d-dist-min", () => ({
  default: { react: vi.fn(), purge: vi.fn() },
  react: vi.fn(),
  purge: vi.fn(),
}));

const MOCK_ENRICHMENT: TrimEnrichment = {
  analysis_goal: "Can the aircraft trim near stall?",
  result_summary: "Trimmed at α=12.3° with 80% elevator reserve",
  trim_method: "opti",
  trim_score: 0.02,
  trim_residuals: { cm: 0.001 },
  deflection_reserves: {
    "[elevator]Elevator": {
      deflection_deg: -5.0,
      max_pos_deg: 25.0,
      max_neg_deg: 25.0,
      usage_fraction: 0.2,
    },
    "[aileron]Left Aileron": {
      deflection_deg: 3.0,
      max_pos_deg: 20.0,
      max_neg_deg: 20.0,
      usage_fraction: 0.15,
    },
  },
  design_warnings: [
    {
      level: "warning",
      category: "authority",
      surface: "[elevator]Elevator",
      message: "85% authority used — surface may be undersized",
    },
  ],
  effectiveness: {},
  stability_classification: null,
  mixer_values: {},
  aero_coefficients: { CL: 0.45, CD: 0.032 },
};

describe("AnalysisGoalCard", () => {
  it("renders analysis goal text", () => {
    render(<AnalysisGoalCard enrichment={MOCK_ENRICHMENT} />);
    expect(
      screen.getByText("Can the aircraft trim near stall?"),
    ).toBeTruthy();
  });

  it("renders nothing when enrichment is null", () => {
    const { container } = render(<AnalysisGoalCard enrichment={null} />);
    expect(container.firstChild).toBeNull();
  });
});

describe("ControlAuthorityChart", () => {
  it("renders chart container when enrichment has reserves", () => {
    render(<ControlAuthorityChart enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByText("Control Authority")).toBeTruthy();
    expect(screen.getByTestId("authority-chart-container")).toBeTruthy();
  });

  it("renders nothing when enrichment is null", () => {
    const { container } = render(
      <ControlAuthorityChart enrichment={null} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when no deflection reserves", () => {
    const empty: TrimEnrichment = {
      ...MOCK_ENRICHMENT,
      deflection_reserves: {},
    };
    const { container } = render(
      <ControlAuthorityChart enrichment={empty} />,
    );
    expect(container.firstChild).toBeNull();
  });
});

describe("DesignWarningBadges", () => {
  it("renders warning badges", () => {
    render(<DesignWarningBadges enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByText(/85% authority used/)).toBeTruthy();
  });

  it("renders nothing when no warnings", () => {
    const noWarn: TrimEnrichment = {
      ...MOCK_ENRICHMENT,
      design_warnings: [],
    };
    const { container } = render(
      <DesignWarningBadges enrichment={noWarn} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when enrichment is null", () => {
    const { container } = render(
      <DesignWarningBadges enrichment={null} />,
    );
    expect(container.firstChild).toBeNull();
  });
});
