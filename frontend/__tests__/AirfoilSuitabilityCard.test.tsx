/**
 * Unit tests for AirfoilSuitabilityCard (gh-825).
 * Verifies: three operating-point bars, provenance indicator, stall/CLmax rows,
 * tip-Re CL_max warning, null handling, confidence chip, caveat callout,
 * collapsible behaviour.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// Mock lucide-react icons
vi.mock("lucide-react", () => ({
  ChevronDown: (p: Record<string, unknown>) => (
    <svg data-testid="chevron-down" {...p} />
  ),
  ChevronRight: (p: Record<string, unknown>) => (
    <svg data-testid="chevron-right" {...p} />
  ),
  AlertTriangle: (p: Record<string, unknown>) => (
    <svg data-testid="alert-triangle" {...p} />
  ),
  Info: (p: Record<string, unknown>) => <svg data-testid="info" {...p} />,
  Activity: (p: Record<string, unknown>) => (
    <svg data-testid="activity" {...p} />
  ),
}));

import { AirfoilSuitabilityCard, AirfoilSuitabilityNoData, qualitativeLabel } from "../components/workbench/AirfoilSuitabilityCard";
import type { SuitabilityItem, SuitabilityCaveat } from "../hooks/useAirfoilSuitability";

// ── Base fixtures ──────────────────────────────────────────────────

const baseItem: SuitabilityItem = {
  airfoil_name: "e423",
  family: "cambered",
  re_agnostic: 0.82,
  mission: 0.75,
  target_cl_cruise: 0.68,
  target_cl_best_glide: 0.80,
  target_cl_min_sink: 0.55,
  stall_gentleness: -0.02,
  cl_max_margin: 0.15,
  min_analysis_confidence: 0.92,
  tip_re_flag: false,
  caveat: "Nur relative Rangfolge.",
};

const lowConfidenceItem: SuitabilityItem = {
  ...baseItem,
  min_analysis_confidence: 0.72,
};

const nullMissionItem: SuitabilityItem = {
  ...baseItem,
  mission: null,
  target_cl_min_sink: null,
  target_cl_best_glide: null,
};

const baseCaveat: SuitabilityCaveat = {
  relative_ranking_only: true,
  no_hysteresis_modelling: true,
  ignores_tip_re_clmax_collapse: true,
  recommend_xfoil_validation: false,
  text: "Nur relative Rangfolge. Kein Hysterese-Modell.",
};

// ── F2: Three operating-point bars ───────────────────────────────

describe("AirfoilSuitabilityCard — F2: three operating-point bars", () => {
  it("renders Ziel-CL · Cruise bar", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.getByText(/Cruise/i)).toBeDefined();
  });

  it("renders Ziel-CL · Best-Glide bar with sublabel", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.getByText(/Best-Glide/i)).toBeDefined();
    expect(screen.getByText(/Motorausfall \/ Segelflug/i)).toBeDefined();
  });

  it("renders Ziel-CL · Min-Sink bar", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.getByText(/Min-Sink/i)).toBeDefined();
  });

  it("does NOT render Loiter bar (removed in gh-825)", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.queryByText(/Loiter/i)).toBeNull();
  });

  it("shows n/a for target_cl_best_glide when null", () => {
    render(<AirfoilSuitabilityCard item={nullMissionItem} defaultOpen />);
    const naElements = screen.queryAllByText(/n\/a/i);
    expect(naElements.length).toBeGreaterThan(0);
  });

  it("shows n/a for target_cl_min_sink when null", () => {
    render(<AirfoilSuitabilityCard item={nullMissionItem} defaultOpen />);
    const naElements = screen.queryAllByText(/n\/a/i);
    expect(naElements.length).toBeGreaterThan(0);
  });
});

// ── F3: Provenance indicator ───────────────────────────────────────

describe("AirfoilSuitabilityCard — F3: provenance indicator", () => {
  it("renders provenance indicator when targetClProvenance is provided", () => {
    render(
      <AirfoilSuitabilityCard
        item={baseItem}
        defaultOpen
        targetClProvenance="calculated"
      />,
    );
    expect(screen.getByTestId("provenance-indicator")).toBeDefined();
  });

  it("does NOT render provenance indicator when targetClProvenance is absent", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.queryByTestId("provenance-indicator")).toBeNull();
  });

  it("shows 'bewegliche Referenz' tooltip for calculated provenance", () => {
    render(
      <AirfoilSuitabilityCard
        item={baseItem}
        defaultOpen
        targetClProvenance="calculated"
      />,
    );
    const indicator = screen.getByTestId("provenance-indicator");
    const title = indicator.getAttribute("title");
    expect(title).toMatch(/bewegliche Referenz|calculated/i);
  });

  it("shows 'feste Referenz' tooltip for estimated provenance", () => {
    render(
      <AirfoilSuitabilityCard
        item={baseItem}
        defaultOpen
        targetClProvenance="estimated"
      />,
    );
    const indicator = screen.getByTestId("provenance-indicator");
    const title = indicator.getAttribute("title");
    expect(title).toMatch(/feste Referenz|estimated/i);
  });

  it("shows 'kombinierte Referenz' tooltip for mixed provenance", () => {
    render(
      <AirfoilSuitabilityCard
        item={baseItem}
        defaultOpen
        targetClProvenance="mixed"
      />,
    );
    const indicator = screen.getByTestId("provenance-indicator");
    const title = indicator.getAttribute("title");
    expect(title).toMatch(/kombinierte Referenz|mixed/i);
  });
});

// ── F4: Stall gentleness + CL_max margin ─────────────────────────

describe("AirfoilSuitabilityCard — F4: stall gentleness and CL_max margin", () => {
  it("renders stall_gentleness value when present", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.getByTestId("stall-gentleness-value")).toBeDefined();
    // baseItem stall_gentleness = -0.02
    expect(screen.getByTestId("stall-gentleness-value").textContent).toMatch(/-0\.0[12]\d/);
  });

  it("renders cl_max_margin value when present", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.getByTestId("cl-max-margin-value")).toBeDefined();
    // baseItem cl_max_margin = 0.15
    expect(screen.getByTestId("cl-max-margin-value").textContent).toMatch(/\+0\.1[45]\d/);
  });

  it("shows abrupt-stall warning when stall_gentleness < -0.05", () => {
    const abruptItem: SuitabilityItem = {
      ...baseItem,
      stall_gentleness: -0.18,
    };
    render(<AirfoilSuitabilityCard item={abruptItem} defaultOpen />);
    expect(screen.getByTestId("stall-abrupt-warning")).toBeDefined();
  });

  it("does NOT show abrupt-stall warning when stall_gentleness is gentle (>= -0.05)", () => {
    const gentleItem: SuitabilityItem = {
      ...baseItem,
      stall_gentleness: -0.02,
    };
    render(<AirfoilSuitabilityCard item={gentleItem} defaultOpen />);
    expect(screen.queryByTestId("stall-abrupt-warning")).toBeNull();
  });

  it("shows negative-margin warning (Ziel > CL_max) when cl_max_margin < 0", () => {
    const negMarginItem: SuitabilityItem = {
      ...baseItem,
      cl_max_margin: -0.05,
    };
    render(<AirfoilSuitabilityCard item={negMarginItem} defaultOpen />);
    expect(screen.getByTestId("cl-max-margin-warning")).toBeDefined();
    expect(screen.getByTestId("cl-max-margin-warning").textContent).toMatch(/Ziel.*CL_max/i);
  });

  it("does NOT show negative-margin warning when cl_max_margin >= 0", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.queryByTestId("cl-max-margin-warning")).toBeNull();
  });

  it("does not render stall/CLmax row when both are null", () => {
    const noStallItem: SuitabilityItem = {
      ...baseItem,
      stall_gentleness: null,
      cl_max_margin: null,
    };
    render(<AirfoilSuitabilityCard item={noStallItem} defaultOpen />);
    expect(screen.queryByTestId("stall-gentleness-value")).toBeNull();
    expect(screen.queryByTestId("cl-max-margin-value")).toBeNull();
  });
});

// ── F5: Tip-Re CL_max collapse warning ───────────────────────────

describe("AirfoilSuitabilityCard — F5: tip-Re CL_max collapse warning", () => {
  it("shows tip-Re warning when caveat.ignores_tip_re_clmax_collapse is true", () => {
    render(
      <AirfoilSuitabilityCard
        item={baseItem}
        defaultOpen
        caveatObject={baseCaveat}
      />,
    );
    expect(screen.getByTestId("tip-re-clmax-warning")).toBeDefined();
    expect(screen.getByTestId("tip-re-clmax-warning").textContent).toMatch(
      /Tip-Re.*CL_max|CL_max.*Einbruch|tip.*stall/i,
    );
  });

  it("shows tip-Re warning when item.tip_re_flag is true (even without caveatObject)", () => {
    const tipFlagItem: SuitabilityItem = {
      ...baseItem,
      tip_re_flag: true,
    };
    render(<AirfoilSuitabilityCard item={tipFlagItem} defaultOpen />);
    expect(screen.getByTestId("tip-re-clmax-warning")).toBeDefined();
  });

  it("does NOT show tip-Re warning when both tip_re_flag=false and no caveatObject", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.queryByTestId("tip-re-clmax-warning")).toBeNull();
  });

  it("does NOT show tip-Re warning when caveat.ignores_tip_re_clmax_collapse is false", () => {
    const noCaveat: SuitabilityCaveat = {
      ...baseCaveat,
      ignores_tip_re_clmax_collapse: false,
    };
    render(
      <AirfoilSuitabilityCard
        item={baseItem}
        defaultOpen
        caveatObject={noCaveat}
      />,
    );
    expect(screen.queryByTestId("tip-re-clmax-warning")).toBeNull();
  });
});

// ── General card tests ────────────────────────────────────────────

describe("AirfoilSuitabilityCard", () => {
  it("renders Re-agnostisch bar", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(
      screen.getByText(/Re-agnostisch/i),
    ).toBeDefined();
  });

  it("renders Mission bar with score", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.getByText(/Mission/i)).toBeDefined();
  });

  it("hides Mission bar or shows n/a when mission score is null", () => {
    render(<AirfoilSuitabilityCard item={nullMissionItem} defaultOpen />);
    // When mission is null, it should either not render the bar or show 'n/a'
    const missionBars = screen.queryAllByText(/Mission/i);
    if (missionBars.length > 0) {
      // If the bar label is still there, the value should be n/a (may be multiple)
      const naElements = screen.queryAllByText(/n\/a/i);
      expect(naElements.length).toBeGreaterThan(0);
    }
    // Otherwise it's hidden — both are valid per spec
  });

  it("shows green color class for score >= 0.7", () => {
    const { container } = render(
      <AirfoilSuitabilityCard item={baseItem} defaultOpen />,
    );
    // re_agnostic = 0.82 (green), mission = 0.75 (green)
    // jsdom renders inline styles as rgb(), check for the rgb equivalent of #34D399
    // or the hex value in background-color style
    const html = container.innerHTML;
    // Either hex or rgb(52, 211, 153) for #34D399
    expect(
      html.includes("34D399") || html.includes("rgb(52, 211, 153)")
    ).toBe(true);
  });

  it("shows amber color class for score 0.4-0.7", () => {
    const amberItem: SuitabilityItem = {
      ...baseItem,
      re_agnostic: 0.55,
      mission: 0.45,
    };
    const { container } = render(
      <AirfoilSuitabilityCard item={amberItem} defaultOpen />,
    );
    // #FBBF24 = rgb(251, 191, 36)
    const html = container.innerHTML;
    expect(
      html.includes("FBBF24") || html.includes("rgb(251, 191, 36)")
    ).toBe(true);
  });

  it("shows red color class for score < 0.4", () => {
    const redItem: SuitabilityItem = {
      ...baseItem,
      re_agnostic: 0.25,
    };
    const { container } = render(
      <AirfoilSuitabilityCard item={redItem} defaultOpen />,
    );
    // #F87171 = rgb(248, 113, 113)
    const html = container.innerHTML;
    expect(
      html.includes("F87171") || html.includes("rgb(248, 113, 113)")
    ).toBe(true);
  });

  it("shows confidence chip in normal state when confidence >= 0.85", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    // Should show confidence value (0.92)
    expect(screen.getByText(/0\.9\d/)).toBeDefined();
  });

  it("shows confidence chip amber styling when min_analysis_confidence < 0.85", () => {
    const { container } = render(
      <AirfoilSuitabilityCard item={lowConfidenceItem} defaultOpen />,
    );
    // Amber color should be present in the confidence chip
    // #FBBF24 = rgb(251, 191, 36)
    const html = container.innerHTML;
    expect(
      html.includes("FBBF24") || html.includes("rgb(251, 191, 36)")
    ).toBe(true);
  });

  it("shows caveat callout text", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.getByText(/Nur relative Rangfolge/)).toBeDefined();
  });

  it("is collapsed by default when defaultOpen is false", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen={false} />);
    // When collapsed, the Re-agnostisch bar should NOT be visible
    expect(screen.queryByText(/Re-agnostisch/i)).toBeNull();
  });

  it("shows ChevronRight when collapsed", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen={false} />);
    expect(screen.getByTestId("chevron-right")).toBeDefined();
  });

  it("shows ChevronDown when open", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.getByTestId("chevron-down")).toBeDefined();
  });

  it("expands when toggle is clicked while collapsed", async () => {
    const user = userEvent.setup();
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen={false} />);
    expect(screen.queryByText(/Re-agnostisch/i)).toBeNull();

    const toggle = screen.getByRole("button");
    await user.click(toggle);

    expect(screen.getByText(/Re-agnostisch/i)).toBeDefined();
  });

  it("collapses when toggle is clicked while open", async () => {
    const user = userEvent.setup();
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.getByText(/Re-agnostisch/i)).toBeDefined();

    const toggle = screen.getByRole("button");
    await user.click(toggle);

    expect(screen.queryByText(/Re-agnostisch/i)).toBeNull();
  });

  // ── Issue #1: Confidence chip overflow fix ─────────────────────
  it("confidence chip is rendered inside the button (not overflowing header row)", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    // The chip now lives in its own sub-row (pl-4 wrapper) inside the toggle button.
    // It must still be present and not overflow the 480px panel.
    // We verify the chip text is present at all.
    expect(screen.getByText(/Konfidenz 0\.92/i)).toBeDefined();
  });

  it("confidence chip text contains the confidence value", () => {
    render(<AirfoilSuitabilityCard item={lowConfidenceItem} defaultOpen />);
    expect(screen.getByText(/Konfidenz 0\.72/i)).toBeDefined();
  });

  it("confidence chip has a tooltip (title) explaining the value", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    const chip = screen.getByText(/Konfidenz 0\.92/i);
    const title = chip.getAttribute("title");
    expect(title).toBeTruthy();
    expect(title).toMatch(/Konfidenz|Modell|Re/i);
  });

  // ── Issue #3: No-data placeholder ─────────────────────────────
  it("AirfoilSuitabilityNoData renders placeholder text without airfoilName", () => {
    render(<AirfoilSuitabilityNoData />);
    expect(screen.getByTestId("suitability-no-data")).toBeDefined();
    expect(screen.getByText(/Keine Low-Re-Eignungsdaten/i)).toBeDefined();
  });

  it("AirfoilSuitabilityNoData renders airfoil name when provided", () => {
    render(<AirfoilSuitabilityNoData airfoilName="rae2822" />);
    expect(screen.getByText(/rae2822/i)).toBeDefined();
  });

  // ── Issue #4a: Qualitative labels ─────────────────────────────
  describe("qualitativeLabel (exported)", () => {
    it("returns 'Gut' for score >= 0.75", () => {
      expect(qualitativeLabel(0.75)).toBe("Gut");
      expect(qualitativeLabel(1.0)).toBe("Gut");
      expect(qualitativeLabel(0.85)).toBe("Gut");
    });

    it("returns 'Mäßig' for score >= 0.5 and < 0.75", () => {
      expect(qualitativeLabel(0.5)).toBe("Mäßig");
      expect(qualitativeLabel(0.6)).toBe("Mäßig");
      expect(qualitativeLabel(0.74)).toBe("Mäßig");
    });

    it("returns 'Schwach' for score < 0.5", () => {
      expect(qualitativeLabel(0.49)).toBe("Schwach");
      expect(qualitativeLabel(0.0)).toBe("Schwach");
      expect(qualitativeLabel(0.3)).toBe("Schwach");
    });
  });

  it("renders qualitative label next to each score bar", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    // re_agnostic = 0.82 → "Gut"
    // mission = 0.75 → "Gut"
    const labels = screen.getAllByTestId("qualitative-label");
    expect(labels.length).toBeGreaterThan(0);
    // At least one "Gut" label visible (re_agnostic=0.82)
    const gutLabels = labels.filter((el) => el.textContent === "Gut");
    expect(gutLabels.length).toBeGreaterThan(0);
  });

  it("renders 'Mäßig' qualitative label for mid-range scores", () => {
    const midItem: SuitabilityItem = {
      ...baseItem,
      re_agnostic: 0.6,
      mission: 0.55,
      target_cl_cruise: 0.52,
      target_cl_min_sink: 0.51,
      target_cl_best_glide: 0.51,
    };
    render(<AirfoilSuitabilityCard item={midItem} defaultOpen />);
    const labels = screen.getAllByTestId("qualitative-label");
    const masigLabels = labels.filter((el) => el.textContent === "Mäßig");
    expect(masigLabels.length).toBeGreaterThan(0);
  });

  it("renders 'Schwach' qualitative label for low scores", () => {
    const weakItem: SuitabilityItem = {
      ...baseItem,
      re_agnostic: 0.25,
      mission: 0.3,
      target_cl_cruise: 0.2,
      target_cl_min_sink: 0.1,
      target_cl_best_glide: 0.1,
    };
    render(<AirfoilSuitabilityCard item={weakItem} defaultOpen />);
    const labels = screen.getAllByTestId("qualitative-label");
    const schwachLabels = labels.filter((el) => el.textContent === "Schwach");
    expect(schwachLabels.length).toBeGreaterThan(0);
  });

  // ── Issue #4b: Softer low-confidence caveat ──────────────────
  it("shows softened caveat when confidence is low (<0.85)", () => {
    render(<AirfoilSuitabilityCard item={lowConfidenceItem} defaultOpen />);
    // The CaveatCallout should include the hobbyist-friendly low-confidence prefix
    expect(screen.getByRole("note").textContent).toMatch(/Geringe Modell-Konfidenz|grobe Orientierung/i);
  });

  it("does NOT show low-confidence prefix in caveat when confidence is high (>=0.85)", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    // baseItem confidence = 0.92 (high)
    // When tip_re_flag is false and no caveatObject, there is only one note (the caveat)
    const notes = screen.getAllByRole("note");
    // Find the one that is the caveat (not tip-Re warning)
    const caveatNote = notes.find(
      (n) => n.textContent?.includes("Nur relative Rangfolge"),
    );
    expect(caveatNote).toBeDefined();
    expect(caveatNote?.textContent).not.toMatch(/Geringe Modell-Konfidenz/i);
  });
});
