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

import { AirfoilSuitabilityCard } from "../components/workbench/AirfoilSuitabilityCard";
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
});
