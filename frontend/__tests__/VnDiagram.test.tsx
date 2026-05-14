/**
 * Unit tests for VnDiagram gust warning banners (gh-497).
 *
 * Validates that the validity-warning (μ_g out of [3, 200]) banner
 * renders with amber styling and is distinct from the gust-critical
 * (n_gust > g_limit) banner with sky-blue styling.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { VnDiagram } from "@/components/workbench/VnDiagram";
import type { VnCurve, AnyGustWarning } from "@/hooks/useFlightEnvelope";

vi.mock("plotly.js-gl3d-dist-min", () => ({
  default: { newPlot: vi.fn(), react: vi.fn(), purge: vi.fn() },
  newPlot: vi.fn(),
  react: vi.fn(),
  purge: vi.fn(),
}));

const BASE_CURVE: VnCurve = {
  positive: [
    { velocity_mps: 10, load_factor: 1.0 },
    { velocity_mps: 30, load_factor: 3.8 },
  ],
  negative: [
    { velocity_mps: 10, load_factor: -1.0 },
    { velocity_mps: 30, load_factor: -1.5 },
  ],
  dive_speed_mps: 45,
  stall_speed_mps: 12,
  gust_warnings: [],
};

describe("VnDiagram gust warning banners (gh-497)", () => {
  it("renders amber validity banner when μ_g warning present", () => {
    const validity: AnyGustWarning = {
      mu_g_value: 1.5,
      validity_min: 3.0,
      validity_max: 200.0,
      message: "μ_g = 1.50 outside Pratt-Walker validity range [3, 200]",
    };
    render(
      <VnDiagram
        vnCurve={BASE_CURVE}
        operatingPoints={[]}
        gustWarnings={[validity]}
      />,
    );
    const banner = screen.getByText(
      /Pratt-Walker validity: gust loads may be optimistic/,
    );
    expect(banner).toBeDefined();
    expect(
      screen.getByText(
        /μ_g = 1.50 outside Pratt-Walker validity range \[3, 200\]/,
      ),
    ).toBeDefined();
  });

  it("renders sky-blue critical banner when n_gust > g_limit", () => {
    const critical: AnyGustWarning = {
      velocity_mps: 50,
      n_gust: 4.5,
      g_limit: 3.8,
      message: "Gust-critical: structure sized by gust loads, not maneuver",
    };
    render(
      <VnDiagram
        vnCurve={BASE_CURVE}
        operatingPoints={[]}
        gustWarnings={[critical]}
      />,
    );
    expect(
      screen.getByText(
        /Gust-critical: structure sized by gust loads, not maneuver/,
      ),
    ).toBeDefined();
  });

  it("renders no banner when warnings list is empty", () => {
    render(
      <VnDiagram
        vnCurve={BASE_CURVE}
        operatingPoints={[]}
        gustWarnings={[]}
      />,
    );
    expect(
      screen.queryByText(/Pratt-Walker validity/),
    ).toBeNull();
    expect(
      screen.queryByText(/Gust-critical/),
    ).toBeNull();
  });
});
