/**
 * Coverage tests for AirfoilPreviewViewerPanel additional branches (gh-822).
 *
 * Covers:
 * - Ma input onChange (lines 601-602)
 * - maximizedChart toggle (lines 762-769)
 * - geometry loading state
 * - no rootGeometry state ("No airfoil selected")
 * - hasTip geometry stats
 * - no rootAnalysisResult ("Run Analysis" placeholder)
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

vi.mock("lucide-react", () => ({
  Maximize2: (p: Record<string, unknown>) => <svg data-testid="maximize" {...p} />,
  Minimize2: (p: Record<string, unknown>) => <svg data-testid="minimize" {...p} />,
  AlertTriangle: (p: Record<string, unknown>) => (
    <svg data-testid="alert-triangle" {...p} />
  ),
}));

import { AirfoilPreviewViewerPanel } from "../components/workbench/AirfoilPreviewViewerPanel";
import type { AirfoilAnalysisResult } from "../hooks/useAirfoilAnalysis";
import type { AirfoilGeometry } from "../hooks/useAirfoilGeometry";

const mockGeometry: AirfoilGeometry = {
  upper: [[0, 0], [0.5, 0.08], [1, 0]],
  lower: [[0, 0], [0.5, -0.04], [1, 0]],
  maxThicknessPct: 12,
  maxCamberPct: 4,
  maxThicknessX: 0.3,
};

const tipGeometry: AirfoilGeometry = {
  upper: [[0, 0], [0.5, 0.06], [1, 0]],
  lower: [[0, 0], [0.5, -0.03], [1, 0]],
  maxThicknessPct: 9,
  maxCamberPct: 3,
  maxThicknessX: 0.3,
};

const mockAnalysis: AirfoilAnalysisResult = {
  airfoilName: "e423",
  alphaDeg: [-5, 0, 5, 10, 15],
  cl: [-0.2, 0.1, 0.5, 0.9, 1.2],
  cd: [0.015, 0.01, 0.012, 0.02, 0.04],
  cm: [-0.02, -0.01, -0.01, -0.02, -0.03],
  clOverCd: [-13.3, 10, 41.7, 45, 30],
  clMax: 1.2,
  alphaAtClMax: 15,
  ldMax: 45,
  alphaAtLdMax: 10,
};

const baseProps = {
  rootAirfoilName: "e423",
  tipAirfoilName: null as string | null,
  rootGeometry: mockGeometry,
  tipGeometry: null as AirfoilGeometry | null,
  geometryLoading: false,
  rootAnalysisResult: mockAnalysis,
  tipAnalysisResult: null as AirfoilAnalysisResult | null,
  rootRe: 200000,
  tipRe: null as number | null,
  ma: 0,
  onMaChange: vi.fn(),
};

describe("AirfoilPreviewViewerPanel — coverage (gh-822)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("Ma input fires onMaChange with parsed float", async () => {
    const onMaChange = vi.fn();
    render(<AirfoilPreviewViewerPanel {...baseProps} onMaChange={onMaChange} />);
    const maInput = screen.getByDisplayValue("0") as HTMLInputElement;
    fireEvent.change(maInput, { target: { value: "0.3" } });
    expect(onMaChange).toHaveBeenCalledWith(0.3);
  });

  it("Ma input does NOT fire onMaChange for NaN input", async () => {
    const onMaChange = vi.fn();
    render(<AirfoilPreviewViewerPanel {...baseProps} onMaChange={onMaChange} />);
    const maInput = screen.getByDisplayValue("0") as HTMLInputElement;
    fireEvent.change(maInput, { target: { value: "abc" } });
    expect(onMaChange).not.toHaveBeenCalled();
  });

  it("shows 'Loading…' text when geometryLoading is true", () => {
    render(
      <AirfoilPreviewViewerPanel
        {...baseProps}
        rootGeometry={null}
        geometryLoading
      />,
    );
    expect(screen.getByText(/Loading/)).toBeDefined();
  });

  it("shows 'No airfoil selected' when geometry not loaded and not loading", () => {
    render(
      <AirfoilPreviewViewerPanel
        {...baseProps}
        rootGeometry={null}
        geometryLoading={false}
      />,
    );
    expect(screen.getByText(/No airfoil selected/)).toBeDefined();
  });

  it("shows 'Run Analysis to see polars' placeholder when no analysis result", () => {
    render(
      <AirfoilPreviewViewerPanel {...baseProps} rootAnalysisResult={null} />,
    );
    expect(screen.getByText(/Run Analysis to see polars/i)).toBeDefined();
  });

  it("renders chart titles when analysis result is provided", () => {
    render(<AirfoilPreviewViewerPanel {...baseProps} />);
    // The SVG charts have text elements with titles (multiple charts, so getAllBy)
    expect(screen.getAllByText(/C_L vs/i).length).toBeGreaterThan(0);
  });

  it("maximize button toggles chart to maximized mode", async () => {
    const user = userEvent.setup();
    render(<AirfoilPreviewViewerPanel {...baseProps} />);
    // Hover to reveal maximize button (group-hover:opacity-100 — jsdom ignores hover)
    // Force click the first maximize button by querying all
    const maxBtns = screen.getAllByTitle("Maximize");
    expect(maxBtns.length).toBeGreaterThan(0);
    await user.click(maxBtns[0]);
    // After maximizing, we should see "Restore" button
    expect(screen.getByTitle("Restore")).toBeDefined();
    // And the Minimize icon
    expect(screen.getByTestId("minimize")).toBeDefined();
  });

  it("clicking Restore collapses back from maximized view", async () => {
    const user = userEvent.setup();
    render(<AirfoilPreviewViewerPanel {...baseProps} />);
    const maxBtns = screen.getAllByTitle("Maximize");
    // Maximize first chart
    await user.click(maxBtns[0]);
    // Now restore
    const restoreBtn = screen.getByTitle("Restore");
    await user.click(restoreBtn);
    // Should be back to normal multi-chart view
    expect(screen.getAllByTitle("Maximize").length).toBeGreaterThan(0);
  });

  it("hasTip=true: shows tip airfoil name and tip Re", () => {
    render(
      <AirfoilPreviewViewerPanel
        {...baseProps}
        tipAirfoilName="naca0015"
        tipRe={150000}
      />,
    );
    // Tip name shown
    expect(screen.getAllByText("naca0015").length).toBeGreaterThan(0);
    // Tip Re shown ("150k") — may appear in multiple text nodes
    expect(screen.getAllByText(/150k/).length).toBeGreaterThan(0);
  });

  it("hasTip=true with tipGeometry: geo stats include tip info", () => {
    render(
      <AirfoilPreviewViewerPanel
        {...baseProps}
        tipAirfoilName="naca0015"
        tipRe={150000}
        tipGeometry={tipGeometry}
      />,
    );
    // The stats string includes "tip: t/c = ..."
    expect(screen.getByText(/tip:/)).toBeDefined();
  });

  it("hasTip=true with null tipGeometry: geo stats only show root", () => {
    render(
      <AirfoilPreviewViewerPanel
        {...baseProps}
        tipAirfoilName="naca0015"
        tipRe={150000}
        tipGeometry={null}
      />,
    );
    // Only root geo stats visible (no "tip:" prefix)
    expect(screen.queryByText(/tip: t\/c/)).toBeNull();
  });

  it("hasTip=true: shows secondary data trace (dashed line) for tip analysis", () => {
    render(
      <AirfoilPreviewViewerPanel
        {...baseProps}
        tipAirfoilName="naca0015"
        tipRe={150000}
        tipAnalysisResult={mockAnalysis}
      />,
    );
    // With tip data, legend should appear (label + label2)
    // The SVG text for "root" label appears in the legend
    const rootLabels = screen.getAllByText("root");
    expect(rootLabels.length).toBeGreaterThan(0);
  });

  it("operating point marker absent when alphaDeg has valid entries but operatingAlphaDeg not provided", () => {
    render(<AirfoilPreviewViewerPanel {...baseProps} />);
    expect(screen.queryByTestId("operating-point-marker")).toBeNull();
  });

  it("displays clMax annotation when clMax and alphaAtClMax are non-null", () => {
    render(<AirfoilPreviewViewerPanel {...baseProps} />);
    // annotation text: "C_L,max ≈ 1.20 @ 15°"
    expect(screen.getByText(/C_L,max/)).toBeDefined();
  });

  it("does NOT show clMax annotation when analysis has null clMax", () => {
    const analysisNoClmax = { ...mockAnalysis, clMax: null, alphaAtClMax: null };
    render(
      <AirfoilPreviewViewerPanel {...baseProps} rootAnalysisResult={analysisNoClmax} />,
    );
    expect(screen.queryByText(/C_L,max/)).toBeNull();
  });

  it("shows L/D max annotation when ldMax and alphaAtLdMax are non-null", () => {
    render(<AirfoilPreviewViewerPanel {...baseProps} />);
    expect(screen.getByText(/L\/D,max/)).toBeDefined();
  });
});
