/**
 * Unit tests for AirfoilPreviewConfigPanel suitability wiring (gh-822).
 * Verifies: AirfoilSuitabilityCard rendered under each AirfoilSelector +
 * ReynoldsField (root open, tip collapsed).
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// Mock lucide-react
vi.mock("lucide-react", () => ({
  Info: (p: Record<string, unknown>) => <svg data-testid="info" {...p} />,
  ArrowLeft: (p: Record<string, unknown>) => <svg data-testid="arrow-left" {...p} />,
  Save: (p: Record<string, unknown>) => <svg data-testid="save" {...p} />,
  Loader2: (p: Record<string, unknown>) => <svg data-testid="loader2" {...p} />,
  ChevronLeft: (p: Record<string, unknown>) => <svg data-testid="chevron-left" {...p} />,
  ChevronRight: (p: Record<string, unknown>) => <svg data-testid="chevron-right" {...p} />,
  ChevronDown: (p: Record<string, unknown>) => <svg data-testid="chevron-down" {...p} />,
  ChevronUp: (p: Record<string, unknown>) => <svg data-testid="chevron-up" {...p} />,
  Search: (p: Record<string, unknown>) => <svg data-testid="search" {...p} />,
  Check: (p: Record<string, unknown>) => <svg data-testid="check" {...p} />,
  Undo2: (p: Record<string, unknown>) => <svg data-testid="undo2" {...p} />,
  AlertTriangle: (p: Record<string, unknown>) => <svg data-testid="alert-triangle" {...p} />,
}));

// Mock SWR for AirfoilSelector airfoil list
vi.mock("swr", () => ({
  default: vi.fn(() => ({
    data: {
      count: 1,
      airfoils: [{ airfoil_name: "e423", file_name: "e423.dat" }],
    },
    error: null,
    isLoading: false,
  })),
}));

import { AirfoilPreviewConfigPanel } from "../components/workbench/AirfoilPreviewConfigPanel";
import type { SuitabilityItem } from "../hooks/useAirfoilSuitability";

const rootSuitabilityItem: SuitabilityItem = {
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
  tags: [],
};

const tipSuitabilityItem: SuitabilityItem = {
  airfoil_name: "naca0015",
  family: "symmetric",
  re_agnostic: 0.65,
  mission: null,
  target_cl_cruise: null,
  target_cl_best_glide: null,
  target_cl_min_sink: null,
  stall_gentleness: null,
  cl_max_margin: null,
  min_analysis_confidence: 0.88,
  tip_re_flag: false,
  caveat: "Keine Missionsdaten.",
  tags: [],
};

const baseProps = {
  rootAirfoil: "e423",
  tipAirfoil: "naca0015",
  onRootAirfoilChange: vi.fn(),
  onTipAirfoilChange: vi.fn(),
  isRunning: false,
  segmentIndex: 0,
  segmentCount: 1,
  onSegmentChange: vi.fn(),
  segmentProps: {},
  velocity: 14,
  onVelocityChange: vi.fn(),
  rootRe: 200000,
  tipRe: 150000,
  onRootReChange: vi.fn(),
  onTipReChange: vi.fn(),
  rootChordMm: 200,
  tipChordMm: 150,
  isDirty: false,
  isSaving: false,
  onSave: vi.fn(),
  onRevert: vi.fn(),
  onBack: vi.fn(),
};

describe("AirfoilPreviewConfigPanel — suitability card wiring", () => {
  it("renders AirfoilSuitabilityCard for root airfoil (open by default) when rootSuitabilityItem provided", () => {
    render(
      <AirfoilPreviewConfigPanel
        {...baseProps}
        rootSuitabilityItem={rootSuitabilityItem}
      />,
    );
    // Root card should be open — Re-agnostisch bar visible
    expect(screen.getByText(/Re-agnostisch/i)).toBeDefined();
  });

  it("renders AirfoilSuitabilityCard for tip airfoil (collapsed by default) when tipSuitabilityItem provided", () => {
    render(
      <AirfoilPreviewConfigPanel
        {...baseProps}
        rootSuitabilityItem={rootSuitabilityItem}
        tipSuitabilityItem={tipSuitabilityItem}
      />,
    );
    // Root card is open - Re-agnostisch visible
    expect(screen.getByText(/Re-agnostisch/i)).toBeDefined();
    // Tip card is collapsed by default — its Re-agnostisch bar is hidden
    // (both cards show "Re-agnostisch" only when open; with tip collapsed
    // there should be exactly one "Re-agnostisch" label)
    const reAgnosticLabels = screen.getAllByText(/Re-agnostisch/i);
    expect(reAgnosticLabels).toHaveLength(1); // only root card open
  });

  it("does NOT render AirfoilSuitabilityCard when no suitability item provided", () => {
    render(<AirfoilPreviewConfigPanel {...baseProps} />);
    // No suitability card content
    expect(screen.queryByText(/Re-agnostisch/i)).toBeNull();
  });

  // ── Issue #3: No-data placeholder ─────────────────────────────
  it("renders no-data placeholder for root when rootSuitabilityNotFound is true", () => {
    render(
      <AirfoilPreviewConfigPanel
        {...baseProps}
        rootSuitabilityNotFound
      />,
    );
    expect(screen.getByTestId("suitability-no-data")).toBeDefined();
    expect(screen.getByText(/Keine Low-Re-Eignungsdaten/i)).toBeDefined();
  });

  it("does NOT render no-data placeholder when rootSuitabilityNotFound is false", () => {
    render(
      <AirfoilPreviewConfigPanel
        {...baseProps}
        rootSuitabilityNotFound={false}
      />,
    );
    expect(screen.queryByTestId("suitability-no-data")).toBeNull();
  });

  it("renders no-data placeholder for tip when tipSuitabilityNotFound is true", () => {
    render(
      <AirfoilPreviewConfigPanel
        {...baseProps}
        tipSuitabilityNotFound
      />,
    );
    expect(screen.getByTestId("suitability-no-data")).toBeDefined();
  });

  it("passes stats to root AirfoilSelector and score badge appears in dropdown", async () => {
    // Strengthened from a no-crash check: opens the dropdown and asserts the
    // score badge text is visible for the airfoil in the rootScoreMap.
    const user = userEvent.setup();
    const rootScoreMap: Record<string, string> = { "e423": "0.82" };
    render(
      <AirfoilPreviewConfigPanel
        {...baseProps}
        rootScoreMap={rootScoreMap}
      />,
    );
    // The root_airfoil label is visible before opening
    expect(screen.getByText("root_airfoil")).toBeDefined();

    // Open the root AirfoilSelector dropdown (first trigger button in the form)
    // The root selector trigger shows the current value "e423"
    const triggers = screen.getAllByRole("button");
    // Find the button that shows the current root airfoil value "e423" as its text
    const rootTrigger = triggers.find((btn) => btn.textContent?.includes("e423"));
    expect(rootTrigger).toBeDefined();
    await user.click(rootTrigger!);

    // The score badge "0.82" should now be visible in the dropdown row for e423
    expect(screen.getByText("0.82")).toBeDefined();
  });
});
