import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) => React.createElement("span", props);
  return {
    Wind: icon,
    SlidersHorizontal: icon,
    Activity: icon,
    Ruler: icon,
    Target: icon,
    Navigation: icon,
    Settings: icon,
    Gauge: icon,
    AlertTriangle: icon,
    Loader2: icon,
    Plane: icon,
    TrendingUp: icon,
    Zap: icon,
  };
});

vi.mock("@/hooks/useComputationContext", () => ({
  useComputationContext: vi.fn(),
}));

import { useComputationContext } from "@/hooks/useComputationContext";

describe("Info Chip Row", () => {
  it("shows dynamic values when context is available", async () => {
    (useComputationContext as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        v_cruise_mps: 18.0,
        reynolds: 230000,
        mac_m: 0.21,
        x_np_m: 0.085,
        target_static_margin: 0.12,
        cg_agg_m: 0.092,
      },
      isLoading: false,
      error: null,
    });

    const { InfoChipRow } = await import("@/components/workbench/InfoChipRow");
    render(<InfoChipRow aeroplaneId="42" cgAero={0.073} />);

    expect(screen.getByText(/18\.0 m\/s/)).toBeInTheDocument();
    expect(screen.getByText(/2\.3e\+?5/i)).toBeInTheDocument();
    expect(screen.getByText(/0\.21 m/)).toBeInTheDocument();
    expect(screen.getByText(/0\.085 m/)).toBeInTheDocument();
  });

  it("shows dashes when no context", async () => {
    (useComputationContext as ReturnType<typeof vi.fn>).mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    const { InfoChipRow } = await import("@/components/workbench/InfoChipRow");
    render(<InfoChipRow aeroplaneId="42" cgAero={null} />);

    const dashes = screen.getAllByText("–");
    expect(dashes.length).toBeGreaterThanOrEqual(4);
  });

  // gh-476: extended V-speed chips
  it("renders V_min_sink, V_x, V_y, V_a, V_dive when available", async () => {
    (useComputationContext as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        v_cruise_mps: 18.0,
        v_min_sink_mps: 13.2,
        v_x_mps: 12.0,
        v_y_mps: 15.5,
        v_a_mps: 17.5,
        v_dive_mps: 30.0,
        reynolds: 230000,
        mac_m: 0.21,
        x_np_m: 0.085,
        target_static_margin: 0.12,
        cg_agg_m: 0.092,
      },
      isLoading: false,
      error: null,
    });

    const { InfoChipRow } = await import("@/components/workbench/InfoChipRow");
    render(<InfoChipRow aeroplaneId="42" cgAero={0.073} />);

    // Chips are addressable by their humanized accessible name ("V min sink: …").
    expect(screen.getByRole("group", { name: /V min sink/ })).toBeInTheDocument();
    expect(screen.getByText(/13\.2 m\/s/)).toBeInTheDocument();
    expect(screen.getByRole("group", { name: /^V x:/ })).toBeInTheDocument();
    expect(screen.getByText(/12\.0 m\/s/)).toBeInTheDocument();
    expect(screen.getByRole("group", { name: /^V y:/ })).toBeInTheDocument();
    expect(screen.getByText(/15\.5 m\/s/)).toBeInTheDocument();
    expect(screen.getByRole("group", { name: /^V a:/ })).toBeInTheDocument();
    expect(screen.getByText(/17\.5 m\/s/)).toBeInTheDocument();
    expect(screen.getByRole("group", { name: /V dive/ })).toBeInTheDocument();
    expect(screen.getByText(/30\.0 m\/s/)).toBeInTheDocument();
  });

  // gh-476: V_a hidden for gliders (no manoeuvring placard in CS-22).
  it("hides V_a chip when is_glider is true", async () => {
    (useComputationContext as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        v_cruise_mps: 30.0,
        v_min_sink_mps: 22.0,
        v_a_mps: 25.0,
        v_dive_mps: 60.0,
        is_glider: true,
        reynolds: 800000,
        mac_m: 0.42,
        x_np_m: 0.15,
        target_static_margin: 0.12,
        cg_agg_m: 0.13,
      },
      isLoading: false,
      error: null,
    });

    const { InfoChipRow } = await import("@/components/workbench/InfoChipRow");
    render(<InfoChipRow aeroplaneId="42" cgAero={0.13} />);

    expect(screen.queryByRole("group", { name: /^V a:/ })).toBeNull();
    expect(screen.getByRole("group", { name: /V NE/ })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: /V min sink/ })).toBeInTheDocument();
  });

  // gh-540: each chip exposes a hover description and is keyboard-focusable.
  it("renders hover-description tooltip and is keyboard focusable", async () => {
    (useComputationContext as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        v_min_sink_mps: 13.2,
        v_x_mps: 12.0,
        v_a_mps: 17.5,
        mac_m: 0.21,
      },
      isLoading: false,
      error: null,
    });

    const { InfoChipRow } = await import("@/components/workbench/InfoChipRow");
    render(<InfoChipRow aeroplaneId="42" cgAero={0.073} />);

    const chip = screen.getByRole("group", { name: /V min sink.*minimum sink/i });
    expect(chip).toBeInTheDocument();
    // WCAG 2.1 SC 1.4.13: hover-only tooltips must also reveal on focus.
    expect(chip).toHaveAttribute("tabindex", "0");

    // Tooltip text is inside the chip subtree. It is aria-hidden because
    // the parent chip already carries the description via aria-label.
    expect(chip.textContent).toMatch(/minimum sink/i);
    const tooltip = chip.querySelector('[aria-hidden="true"]');
    expect(tooltip).not.toBeNull();
    expect(tooltip!.textContent).toMatch(/minimum sink/i);
  });

  // gh-540: symbol underscores render as subscript groups.
  it("renders V_min_sink with min,sink in a <sub> element", async () => {
    (useComputationContext as ReturnType<typeof vi.fn>).mockReturnValue({
      data: { v_min_sink_mps: 13.2, mac_m: 0.21 },
      isLoading: false,
      error: null,
    });

    const { InfoChipRow } = await import("@/components/workbench/InfoChipRow");
    const { container } = render(<InfoChipRow aeroplaneId="42" cgAero={null} />);

    const subs = container.querySelectorAll("sub");
    const subTexts = Array.from(subs).map((s) => s.textContent);
    expect(subTexts).toContain("min,sink");
    expect(subTexts).toContain("x");
    expect(subTexts).toContain("dive");
  });

  // gh-540: aria-label is humanized (no literal underscores spoken).
  it("humanizes underscores in aria-label for screen readers", async () => {
    (useComputationContext as ReturnType<typeof vi.fn>).mockReturnValue({
      data: { v_min_sink_mps: 13.2 },
      isLoading: false,
      error: null,
    });

    const { InfoChipRow } = await import("@/components/workbench/InfoChipRow");
    render(<InfoChipRow aeroplaneId="42" cgAero={null} />);

    const chip = screen.getByRole("group", { name: /^V min sink:/ });
    expect(chip.getAttribute("aria-label")).not.toMatch(/_/);
  });
});
