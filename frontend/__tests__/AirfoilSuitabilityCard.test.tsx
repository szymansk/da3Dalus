/**
 * Unit tests for AirfoilSuitabilityCard (gh-822).
 * Verifies: three lens bars, null handling, confidence chip, caveat callout,
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
import type { SuitabilityItem } from "../hooks/useAirfoilSuitability";

const baseItem: SuitabilityItem = {
  airfoil_name: "e423",
  family: "cambered",
  re_agnostic: 0.82,
  mission: 0.75,
  target_cl_cruise: 0.68,
  target_cl_loiter: 0.55,
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
  target_cl_loiter: null,
};

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

  it("renders Ziel-CL Cruise bar", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.getByText(/Cruise/i)).toBeDefined();
  });

  it("renders Ziel-CL Loiter bar", () => {
    render(<AirfoilSuitabilityCard item={baseItem} defaultOpen />);
    expect(screen.getByText(/Loiter/i)).toBeDefined();
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

  it("hides Loiter bar or shows n/a when target_cl_loiter score is null", () => {
    render(<AirfoilSuitabilityCard item={nullMissionItem} defaultOpen />);
    const loiterBars = screen.queryAllByText(/Loiter/i);
    if (loiterBars.length > 0) {
      const naElements = screen.queryAllByText(/n\/a/i);
      expect(naElements.length).toBeGreaterThan(0);
    }
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
      target_cl_loiter: 0.51,
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
      target_cl_loiter: 0.1,
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
    const note = screen.getByRole("note");
    expect(note.textContent).not.toMatch(/Geringe Modell-Konfidenz/i);
  });
});
