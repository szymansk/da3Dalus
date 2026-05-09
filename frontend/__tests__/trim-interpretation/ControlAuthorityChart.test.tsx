import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ControlAuthorityChart } from "@/components/workbench/trim-interpretation/ControlAuthorityChart";
import type { TrimEnrichment } from "@/hooks/useOperatingPoints";

vi.mock("plotly.js-gl3d-dist-min", () => ({
  default: { react: vi.fn(), purge: vi.fn() },
  react: vi.fn(),
  purge: vi.fn(),
}));

const MOCK_ENRICHMENT: TrimEnrichment = {
  analysis_goal: "Test",
  result_summary: "",
  trim_method: "opti",
  trim_score: 0.01,
  trim_residuals: {},
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
  design_warnings: [],
  effectiveness: {},
  stability_classification: null,
  mixer_values: {},
  aero_coefficients: {},
};

describe("ControlAuthorityChart", () => {
  it("renders chart container with correct heading", () => {
    render(<ControlAuthorityChart enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByText("Control Authority")).toBeTruthy();
  });

  it("renders a chart container div", () => {
    render(<ControlAuthorityChart enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByTestId("authority-chart-container")).toBeTruthy();
  });

  it("renders nothing when enrichment is null", () => {
    const { container } = render(<ControlAuthorityChart enrichment={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when no deflection reserves", () => {
    const empty = { ...MOCK_ENRICHMENT, deflection_reserves: {} };
    const { container } = render(<ControlAuthorityChart enrichment={empty} />);
    expect(container.firstChild).toBeNull();
  });
});
