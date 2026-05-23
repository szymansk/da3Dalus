import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
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
    RefreshCw: icon,
    Square: icon,
    ArrowLeftRight: icon,
    // gh-581: TaillessBanner uses Info icon when ctx.is_tailless is true.
    Info: icon,
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
    // gh-563: V_max chip (formerly relabeled V_NE for gliders) hidden for gliders.
    expect(screen.queryByRole("group", { name: /V NE/ })).toBeNull();
    expect(screen.queryByRole("group", { name: /^V max:/ })).toBeNull();
    // gh-573: V_dive (heuristic 1.4 × V_max) hidden for gliders since V_max is hidden too.
    expect(screen.queryByRole("group", { name: /V dive/ })).toBeNull();
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

  // gh-626: chip row splits into FOUR thematic rows
  // (speeds / geometry / polar / stability).
  it("splits chips into four thematic rows: speeds / geometry / polar / stability", async () => {
    (useComputationContext as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        v_cruise_mps: 18.0,
        v_stall_mps: 8.0,
        v_min_sink_mps: 13.2,
        v_md_mps: 14.0,
        v_x_mps: 12.0,
        v_y_mps: 15.5,
        v_a_mps: 17.5,
        v_max_mps: 25.0,
        v_dive_mps: 30.0,
        reynolds: 230000,
        mac_m: 0.21,
        s_ref_m2: 0.42,
        b_ref_m: 2.0,
        aspect_ratio: 10.0,
        cd0: 0.02,
        e_oswald: 0.8,
        e_oswald_quality: "high",
        e_oswald_fallback_used: false,
        polar_by_config: { clean: { cl_max: 1.4 } },
        x_np_m: 0.085,
        target_static_margin: 0.12,
        cg_agg_m: 0.092,
        is_glider: false,
      },
      isLoading: false,
      error: null,
      mutate: vi.fn(),
    });

    const { InfoChipRow } = await import("@/components/workbench/InfoChipRow");
    render(<InfoChipRow aeroplaneId="42" cgAero={0.073} />);

    const speedsRow = screen.getByTestId("chip-row-speeds");
    const geometryRow = screen.getByTestId("chip-row-geometry");
    const polarRow = screen.getByTestId("chip-row-polar");
    const stabilityRow = screen.getByTestId("chip-row-stability");

    // Envelope speeds in row 1.
    expect(speedsRow).toContainElement(screen.getByRole("group", { name: /^V stall:/ }));
    expect(speedsRow).toContainElement(screen.getByRole("group", { name: /^V max:/ }));

    // Geometry row (gh-626: AR added here, Re moved to polar row).
    expect(geometryRow).toContainElement(screen.getByRole("group", { name: /^S ref:/ }));
    expect(geometryRow).toContainElement(screen.getByRole("group", { name: /^MAC:/ }));
    expect(geometryRow).toContainElement(screen.getByRole("group", { name: /^B ref:/ }));
    expect(geometryRow).toContainElement(screen.getByRole("group", { name: /^AR:/ }));

    // Polar row (gh-626 NEW: Re, C_D0, e, k, C_L,md, C_L,max, (L/D)_max, ρ).
    expect(polarRow).toContainElement(screen.getByRole("group", { name: /^Re:/ }));
    expect(polarRow).toContainElement(screen.getByRole("group", { name: /^C D0:/ }));
    expect(polarRow).toContainElement(screen.getByRole("group", { name: /^e:/ }));
    expect(polarRow).toContainElement(screen.getByRole("group", { name: /^ρ:/ }));

    // Stability row.
    expect(stabilityRow).toContainElement(screen.getByRole("group", { name: /^CG:/ }));
    expect(stabilityRow).toContainElement(screen.getByRole("group", { name: /^NP:/ }));

    // No chip is placed in the wrong row.
    expect(geometryRow).not.toContainElement(screen.getByRole("group", { name: /^V stall:/ }));
    expect(speedsRow).not.toContainElement(screen.getByRole("group", { name: /^Re:/ }));
    expect(geometryRow).not.toContainElement(screen.getByRole("group", { name: /^Re:/ }));
    expect(polarRow).not.toContainElement(screen.getByRole("group", { name: /^CG:/ }));
  });

  // gh-593: S_ref chip renders with the formatted area value (3 decimals + " m²").
  it("renders S_ref chip with the s_ref_m2 value formatted as area", async () => {
    (useComputationContext as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        reynolds: 230000,
        mac_m: 0.21,
        s_ref_m2: 0.42,
        b_ref_m: 2.0,
        x_np_m: 0.085,
        target_static_margin: 0.12,
        cg_agg_m: 0.092,
      },
      isLoading: false,
      error: null,
    });

    const { InfoChipRow } = await import("@/components/workbench/InfoChipRow");
    render(<InfoChipRow aeroplaneId="42" cgAero={0.073} />);

    const sRefChip = screen.getByRole("group", { name: /^S ref:/ });
    expect(sRefChip).toBeInTheDocument();
    expect(sRefChip.textContent).toMatch(/0\.420 m²/);
    // Tooltip explains the coefficient formula (drag/lift non-dim).
    expect(sRefChip.getAttribute("aria-label")).toMatch(/Reference area/);
    expect(sRefChip.getAttribute("aria-label")).toMatch(/C_L = L \/ \(q · S_ref\)/);
  });

  // gh-593: B_ref chip renders with the formatted span value (2 decimals + " m").
  it("renders B_ref chip with the b_ref_m value formatted as length", async () => {
    (useComputationContext as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        reynolds: 230000,
        mac_m: 0.21,
        s_ref_m2: 0.42,
        b_ref_m: 2.0,
        x_np_m: 0.085,
        target_static_margin: 0.12,
        cg_agg_m: 0.092,
      },
      isLoading: false,
      error: null,
    });

    const { InfoChipRow } = await import("@/components/workbench/InfoChipRow");
    render(<InfoChipRow aeroplaneId="42" cgAero={0.073} />);

    const bRefChip = screen.getByRole("group", { name: /^B ref:/ });
    expect(bRefChip).toBeInTheDocument();
    expect(bRefChip.textContent).toMatch(/2\.00 m/);
    // Tooltip explains the moment-coefficient formula (roll/yaw non-dim).
    expect(bRefChip.getAttribute("aria-label")).toMatch(/Reference span/);
    expect(bRefChip.getAttribute("aria-label")).toMatch(
      /C_l = M_roll \/ \(q · S_ref · B_ref\)/,
    );
  });

  // gh-593: MAC tooltip explicitly calls out the C_ref alias used in AVL / ASB.
  it("MAC chip description mentions C_ref alias", async () => {
    (useComputationContext as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        reynolds: 230000,
        mac_m: 0.21,
        s_ref_m2: 0.42,
        b_ref_m: 2.0,
        x_np_m: 0.085,
        target_static_margin: 0.12,
        cg_agg_m: 0.092,
      },
      isLoading: false,
      error: null,
    });

    const { InfoChipRow } = await import("@/components/workbench/InfoChipRow");
    render(<InfoChipRow aeroplaneId="42" cgAero={0.073} />);

    const macChip = screen.getByRole("group", { name: /^MAC:/ });
    expect(macChip.getAttribute("aria-label")).toMatch(/C_ref/);
    // The tooltip should also still contain the pitching-moment formula.
    expect(macChip.getAttribute("aria-label")).toMatch(
      /C_m = M_pitch \/ \(q · S_ref · C_ref\)/,
    );
  });

  // gh-593: when s_ref_m2 / b_ref_m are missing, chips render dash placeholders.
  it("renders dashes for S_ref / B_ref when values are missing from context", async () => {
    (useComputationContext as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        reynolds: 230000,
        mac_m: 0.21,
        // s_ref_m2 / b_ref_m intentionally absent
        x_np_m: 0.085,
        target_static_margin: 0.12,
        cg_agg_m: 0.092,
      },
      isLoading: false,
      error: null,
    });

    const { InfoChipRow } = await import("@/components/workbench/InfoChipRow");
    render(<InfoChipRow aeroplaneId="42" cgAero={0.073} />);

    const sRefChip = screen.getByRole("group", { name: /^S ref:/ });
    const bRefChip = screen.getByRole("group", { name: /^B ref:/ });
    expect(sRefChip.textContent).toMatch(/=\s*–/);
    expect(bRefChip.textContent).toMatch(/=\s*–/);
  });

  // gh-687: refresh button must force a recompute (POST /recompute),
  // not just re-fetch the cached context. Previously it only called
  // mutate() on the SWR key, which made the button feel like a no-op
  // because the backend cached context never changed.
  it("renders a force-recompute button that POSTs to /recompute and revalidates", async () => {
    const mutate = vi.fn().mockResolvedValue(undefined);
    (useComputationContext as ReturnType<typeof vi.fn>).mockReturnValue({
      data: { v_cruise_mps: 18.0, reynolds: 230000, mac_m: 0.21, x_np_m: 0.085, target_static_margin: 0.12, cg_agg_m: 0.092 },
      isLoading: false,
      error: null,
      mutate,
    });

    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null, { status: 202 }));

    try {
      const { InfoChipRow } = await import("@/components/workbench/InfoChipRow");
      render(<InfoChipRow aeroplaneId="42" cgAero={0.073} />);

      const button = screen.getByRole("button", { name: /force recompute/i });
      expect(button).toBeInTheDocument();
      expect(button).not.toBeDisabled();

      fireEvent.click(button);
      // Wait for the awaited fetch + mutate chain to settle.
      await Promise.resolve();
      await Promise.resolve();

      expect(fetchMock).toHaveBeenCalledTimes(1);
      const [url, init] = fetchMock.mock.calls[0];
      expect(String(url)).toMatch(/\/aeroplanes\/42\/recompute$/);
      expect(init?.method).toBe("POST");
      expect(mutate).toHaveBeenCalledTimes(1);
    } finally {
      fetchMock.mockRestore();
    }
  });

  // gh-575/gh-687: button is disabled (and does not POST) while a
  // recompute is already in flight.
  it("disables force-recompute button while isRecomputing is true", async () => {
    const mutate = vi.fn();
    (useComputationContext as ReturnType<typeof vi.fn>).mockReturnValue({
      data: { v_cruise_mps: 18.0, reynolds: 230000, mac_m: 0.21, x_np_m: 0.085, target_static_margin: 0.12, cg_agg_m: 0.092 },
      isLoading: false,
      error: null,
      mutate,
    });

    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, { status: 202 }),
    );

    try {
      const { InfoChipRow } = await import("@/components/workbench/InfoChipRow");
      render(<InfoChipRow aeroplaneId="42" cgAero={0.073} isRecomputing />);

      const button = screen.getByRole("button", { name: /force recompute/i });
      expect(button).toBeDisabled();

      fireEvent.click(button);
      expect(fetchMock).not.toHaveBeenCalled();
      expect(mutate).not.toHaveBeenCalled();
    } finally {
      fetchMock.mockRestore();
    }
  });

  // gh-579: SM chip must render for tailless aircraft.
  // Anderson + Apogee + Scholz + Lennon converge on SM = 5–10% MAC for tailless;
  // backend now returns target_static_margin = 0.075 for tailless configurations
  // (formerly returned status="not_applicable", which suppressed the chip target).
  // Tailless and glider often co-occur for unpowered flying wings, so we
  // verify the chip renders correctly with both flags set.
  it("renders SM chip for tailless glider with target_static_margin=0.075", async () => {
    (useComputationContext as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        is_glider: true,
        v_min_sink_mps: 13.2,
        reynolds: 230000,
        mac_m: 0.21,
        x_np_m: 0.085,
        target_static_margin: 0.075, // 7.5% MAC — tailless recommendation
        cg_agg_m: 0.078,
      },
      isLoading: false,
      error: null,
    });

    const { InfoChipRow } = await import("@/components/workbench/InfoChipRow");
    render(<InfoChipRow aeroplaneId="42" cgAero={0.078} />);

    const smChip = screen.getByRole("group", { name: /^SM:/ });
    expect(smChip).toBeInTheDocument();
    // 0.075 → 8% (rounds to 0 decimals via .toFixed(0))
    expect(smChip.textContent).toMatch(/8%/);
  });

  // gh-581: Tailless UX banner surfaces when backend reports is_tailless=true.
  // Banner explains tail-volume sizing is N/A, SM corridor is tighter, and that
  // trim comes from sweep + washout + reflex (hybrid preferred per Apogee).
  it("renders the TaillessBanner when ctx.is_tailless is true", async () => {
    (useComputationContext as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        is_tailless: true,
        v_cruise_mps: 18.0,
        reynolds: 230000,
        mac_m: 0.21,
        x_np_m: 0.085,
        target_static_margin: 0.075,
        cg_agg_m: 0.078,
      },
      isLoading: false,
      error: null,
    });

    const { InfoChipRow } = await import("@/components/workbench/InfoChipRow");
    render(<InfoChipRow aeroplaneId="42" cgAero={0.078} />);

    expect(screen.getByTestId("tailless-banner")).toBeInTheDocument();
    expect(screen.getByText(/Tailless configuration/i)).toBeInTheDocument();
  });

  // gh-581: Conventional aircraft must NOT see the tailless banner.
  it("does not render the TaillessBanner when ctx.is_tailless is false or missing", async () => {
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

    expect(screen.queryByTestId("tailless-banner")).not.toBeInTheDocument();
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
