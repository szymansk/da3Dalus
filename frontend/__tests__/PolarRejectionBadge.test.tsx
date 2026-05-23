import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => ({
  AlertTriangle: (props: Record<string, unknown>) => (
    <svg data-testid="warn-icon" {...props} />
  ),
}));

import { PolarRejectionBadge } from "../components/workbench/PolarRejectionBadge";
import type { PolarRejection } from "../hooks/useComputationContext";

const designRejection: PolarRejection = {
  gate: "negative_slope_k",
  category: "design",
  fitted_value: -0.001,
  threshold: "k > 0",
  hint: "Polare zeigt mit steigendem Auftrieb fallenden Widerstand.",
};

const sweepRejection: PolarRejection = {
  gate: "insufficient_points",
  category: "sweep",
  fitted_value: 5,
  threshold: ">= 6 points",
  hint: "Zu wenig Punkte.",
};

const dataRejection: PolarRejection = {
  ...sweepRejection,
  gate: "non_monotonic_polar",
  category: "data",
};

const consistencyRejection: PolarRejection = {
  ...sweepRejection,
  gate: "cd0_stability_mismatch",
  category: "consistency",
};

describe("PolarRejectionBadge", () => {
  it("renders the hint when category is design", () => {
    const { container } = render(<PolarRejectionBadge rejection={designRejection} />);
    expect(screen.getByText(designRejection.hint)).toBeDefined();
    expect(screen.getByTestId("warn-icon")).toBeDefined();
    expect(container.firstChild).not.toBeNull();
  });

  it("renders nothing when rejection is null", () => {
    const { container } = render(<PolarRejectionBadge rejection={null} />);
    expect(container.firstChild).toBeNull();
  });

  it.each([
    ["sweep", sweepRejection],
    ["data", dataRejection],
    ["consistency", consistencyRejection],
  ] as const)("renders nothing when category is %s", (_label, rej) => {
    const { container } = render(<PolarRejectionBadge rejection={rej} />);
    expect(container.firstChild).toBeNull();
  });

  it("exposes role=alert for accessibility on design rejection", () => {
    render(<PolarRejectionBadge rejection={designRejection} />);
    expect(screen.getByRole("alert")).toBeDefined();
  });
});
