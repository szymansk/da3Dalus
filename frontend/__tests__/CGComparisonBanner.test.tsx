/**
 * Unit tests for CGComparisonBanner component (gh-437).
 *
 * Verifies rendering logic for various CG comparison states
 * and sync button interaction.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import type { CGComparison } from "@/hooks/useCGComparison";

// ── Mocks ─────────────────────────────────────────────────────────

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    AlertTriangle: icon,
    RefreshCw: icon,
  };
});

const mockSyncDesignCG = vi.fn();
const mockMutate = vi.fn();

let hookReturn: {
  data: CGComparison | null;
  isLoading: boolean;
  error: Error | null;
  syncDesignCG: typeof mockSyncDesignCG;
  mutate: typeof mockMutate;
};

vi.mock("@/hooks/useCGComparison", () => ({
  useCGComparison: () => hookReturn,
}));

import { CGComparisonBanner } from "@/components/workbench/CGComparisonBanner";

// ── Tests ─────────────────────────────────────────────────────────

describe("CGComparisonBanner", () => {
  const mockOnCGSynced = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    hookReturn = {
      data: null,
      isLoading: false,
      error: null,
      syncDesignCG: mockSyncDesignCG,
      mutate: mockMutate,
    };
  });

  it("renders nothing when loading", () => {
    hookReturn.isLoading = true;

    const { container } = render(
      <CGComparisonBanner aeroplaneId="aero-1" onCGSynced={mockOnCGSynced} />,
    );

    expect(container.innerHTML).toBe("");
  });

  it("renders nothing when no data", () => {
    hookReturn.data = null;

    const { container } = render(
      <CGComparisonBanner aeroplaneId="aero-1" onCGSynced={mockOnCGSynced} />,
    );

    expect(container.innerHTML).toBe("");
  });

  it("renders nothing when within_tolerance is true", () => {
    hookReturn.data = {
      design_cg_x: 0.25,
      component_cg_x: 0.255,
      component_cg_y: null,
      component_cg_z: null,
      component_total_mass_kg: 2.5,
      delta_x: -0.005,
      within_tolerance: true,
    };

    const { container } = render(
      <CGComparisonBanner aeroplaneId="aero-1" onCGSynced={mockOnCGSynced} />,
    );

    expect(container.innerHTML).toBe("");
  });

  it("renders nothing when component_cg_x is null", () => {
    hookReturn.data = {
      design_cg_x: 0.25,
      component_cg_x: null,
      component_cg_y: null,
      component_cg_z: null,
      component_total_mass_kg: null,
      delta_x: null,
      within_tolerance: null,
    };

    const { container } = render(
      <CGComparisonBanner aeroplaneId="aero-1" onCGSynced={mockOnCGSynced} />,
    );

    expect(container.innerHTML).toBe("");
  });

  it("renders orange warning when delta_x <= 5cm and NOT within tolerance", () => {
    hookReturn.data = {
      design_cg_x: 0.25,
      component_cg_x: 0.28,
      component_cg_y: null,
      component_cg_z: null,
      component_total_mass_kg: 2.5,
      delta_x: -0.03,
      within_tolerance: false,
    };

    render(
      <CGComparisonBanner aeroplaneId="aero-1" onCGSynced={mockOnCGSynced} />,
    );

    const banner = screen.getByTestId("cg-comparison-banner");
    expect(banner).toBeDefined();
    expect(banner.className).toContain("border-orange-500/30");
    expect(banner.className).toContain("bg-orange-500/10");
  });

  it("renders red warning when delta_x > 5cm", () => {
    hookReturn.data = {
      design_cg_x: 0.25,
      component_cg_x: 0.32,
      component_cg_y: null,
      component_cg_z: null,
      component_total_mass_kg: 2.5,
      delta_x: -0.07,
      within_tolerance: false,
    };

    render(
      <CGComparisonBanner aeroplaneId="aero-1" onCGSynced={mockOnCGSynced} />,
    );

    const banner = screen.getByTestId("cg-comparison-banner");
    expect(banner).toBeDefined();
    expect(banner.className).toContain("border-red-500/30");
    expect(banner.className).toContain("bg-red-500/10");
  });

  it("displays correct delta in cm", () => {
    hookReturn.data = {
      design_cg_x: 0.25,
      component_cg_x: 0.28,
      component_cg_y: null,
      component_cg_z: null,
      component_total_mass_kg: 2.5,
      delta_x: -0.03,
      within_tolerance: false,
    };

    render(
      <CGComparisonBanner aeroplaneId="aero-1" onCGSynced={mockOnCGSynced} />,
    );

    expect(screen.getByText(/3\.0cm/)).toBeDefined();
  });

  it("displays component and design CG values", () => {
    hookReturn.data = {
      design_cg_x: 0.25,
      component_cg_x: 0.28,
      component_cg_y: null,
      component_cg_z: null,
      component_total_mass_kg: 2.5,
      delta_x: -0.03,
      within_tolerance: false,
    };

    render(
      <CGComparisonBanner aeroplaneId="aero-1" onCGSynced={mockOnCGSynced} />,
    );

    expect(screen.getByText(/0\.280m/)).toBeDefined();
    expect(screen.getByText(/0\.250m/)).toBeDefined();
  });

  it("sync button calls syncDesignCG with component_cg_x and onCGSynced callback", async () => {
    hookReturn.data = {
      design_cg_x: 0.25,
      component_cg_x: 0.28,
      component_cg_y: null,
      component_cg_z: null,
      component_total_mass_kg: 2.5,
      delta_x: -0.03,
      within_tolerance: false,
    };
    mockSyncDesignCG.mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(
      <CGComparisonBanner aeroplaneId="aero-1" onCGSynced={mockOnCGSynced} />,
    );

    await user.click(screen.getByTestId("sync-cg-button"));

    expect(mockSyncDesignCG).toHaveBeenCalledWith(0.28);
    expect(mockOnCGSynced).toHaveBeenCalledOnce();
  });
});
