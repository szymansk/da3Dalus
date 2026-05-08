import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  AnalysisGoalBanner,
  ControlAuthorityChart,
  DesignWarningBadges,
} from "@/components/workbench/OperatingPointsPanel";
import type { TrimEnrichment } from "@/hooks/useOperatingPoints";

const MOCK_ENRICHMENT: TrimEnrichment = {
  analysis_goal: "Can the aircraft trim near stall?",
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
};

describe("AnalysisGoalBanner", () => {
  it("renders analysis goal text", () => {
    render(<AnalysisGoalBanner enrichment={MOCK_ENRICHMENT} />);
    expect(
      screen.getByText("Can the aircraft trim near stall?"),
    ).toBeTruthy();
  });

  it("renders nothing when enrichment is null", () => {
    const { container } = render(<AnalysisGoalBanner enrichment={null} />);
    expect(container.firstChild).toBeNull();
  });
});

describe("ControlAuthorityChart", () => {
  it("renders a bar for each surface", () => {
    render(<ControlAuthorityChart enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByText(/Elevator/)).toBeTruthy();
    expect(screen.getByText(/Left Aileron/)).toBeTruthy();
  });

  it("shows percentage for each surface", () => {
    render(<ControlAuthorityChart enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByText("20%")).toBeTruthy();
    expect(screen.getByText("15%")).toBeTruthy();
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
