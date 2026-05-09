import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DesignWarningBadges } from "@/components/workbench/trim-interpretation/DesignWarningBadges";
import type { TrimEnrichment } from "@/hooks/useOperatingPoints";

const MOCK_ENRICHMENT: TrimEnrichment = {
  analysis_goal: "Test",
  result_summary: "",
  trim_method: "opti",
  trim_score: null,
  trim_residuals: {},
  deflection_reserves: {},
  design_warnings: [
    {
      level: "critical",
      category: "authority",
      surface: "[elevator]Elevator",
      message: "Elevator near mechanical limit (96% used)",
    },
    {
      level: "warning",
      category: "authority",
      surface: "[aileron]Left Aileron",
      message: "75% authority used — surface may be undersized",
    },
    {
      level: "info",
      category: "stability",
      surface: null,
      message: "Large static margin — nose-heavy tendency",
    },
  ],
  effectiveness: {},
  stability_classification: null,
  mixer_values: {},
  aero_coefficients: {},
};

describe("DesignWarningBadges", () => {
  it("renders all warning messages", () => {
    render(<DesignWarningBadges enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByText(/Elevator near mechanical limit/)).toBeTruthy();
    expect(screen.getByText(/75% authority used/)).toBeTruthy();
    expect(screen.getByText(/Large static margin/)).toBeTruthy();
  });

  it("expands badge on click to show details", async () => {
    const user = userEvent.setup();
    render(<DesignWarningBadges enrichment={MOCK_ENRICHMENT} />);
    const badge = screen.getByText(/Elevator near mechanical limit/);
    await user.click(badge);
    expect(screen.getByTestId("warning-detail-0")).toBeTruthy();
  });

  it("collapses expanded badge on second click", async () => {
    const user = userEvent.setup();
    render(<DesignWarningBadges enrichment={MOCK_ENRICHMENT} />);
    const badge = screen.getByText(/Elevator near mechanical limit/);
    await user.click(badge);
    expect(screen.getByTestId("warning-detail-0")).toBeTruthy();
    await user.click(badge);
    expect(screen.queryByTestId("warning-detail-0")).toBeNull();
  });

  it("renders nothing when no warnings", () => {
    const empty = { ...MOCK_ENRICHMENT, design_warnings: [] };
    const { container } = render(<DesignWarningBadges enrichment={empty} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when enrichment is null", () => {
    const { container } = render(<DesignWarningBadges enrichment={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("applies correct color for each severity level", () => {
    render(<DesignWarningBadges enrichment={MOCK_ENRICHMENT} />);
    const buttons = screen.getAllByRole("button");
    expect(buttons[0].className).toContain("red");
    expect(buttons[1].className).toContain("yellow");
    expect(buttons[2].className).toContain("blue");
  });
});
