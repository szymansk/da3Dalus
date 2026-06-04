/**
 * Unit tests for AirfoilPreviewViewerPanel suitability enhancements (gh-822).
 * Verifies:
 * - Operating-point marker trace on the L/D polar at operating CL/α
 * - Tip-Re < root-Re warning banner (red, AlertTriangle, role='alert')
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

// Mock lucide-react
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
import type { SuitabilityItem } from "../hooks/useAirfoilSuitability";

const baseSuitabilityItem: SuitabilityItem = {
  airfoil_name: "naca0012",
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
  caveat: "Nur relative Rangfolge.",
};

const mockGeometry: AirfoilGeometry = {
  upper: [[0, 0], [0.5, 0.08], [1, 0]],
  lower: [[0, 0], [0.5, -0.04], [1, 0]],
  maxThicknessPct: 12,
  maxCamberPct: 4,
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
  tipAirfoilName: null,
  rootGeometry: mockGeometry,
  tipGeometry: null,
  geometryLoading: false,
  rootAnalysisResult: mockAnalysis,
  tipAnalysisResult: null,
  rootRe: 200000,
  tipRe: null,
  ma: 0,
  onMaChange: vi.fn(),
};

describe("AirfoilPreviewViewerPanel — suitability enhancements", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does NOT show tip-Re banner when tipRe is null (no tip)", () => {
    render(<AirfoilPreviewViewerPanel {...baseProps} />);
    // No alert banner should appear
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("does NOT show tip-Re banner when tipRe equals rootRe", () => {
    render(
      <AirfoilPreviewViewerPanel
        {...baseProps}
        tipAirfoilName="naca0012"
        tipRe={200000}
        rootRe={200000}
      />,
    );
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("does NOT show tip-Re banner when tipRe > rootRe", () => {
    render(
      <AirfoilPreviewViewerPanel
        {...baseProps}
        tipAirfoilName="naca0012"
        tipRe={300000}
        rootRe={200000}
      />,
    );
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shows tip-Re warning banner (role=alert) when tipRe < rootRe", () => {
    render(
      <AirfoilPreviewViewerPanel
        {...baseProps}
        tipAirfoilName="naca0012"
        tipRe={100000}
        rootRe={200000}
      />,
    );
    const alert = screen.getByRole("alert");
    expect(alert).toBeDefined();
  });

  it("tip-Re banner shows AlertTriangle icon", () => {
    render(
      <AirfoilPreviewViewerPanel
        {...baseProps}
        tipAirfoilName="naca0012"
        tipRe={100000}
        rootRe={200000}
      />,
    );
    expect(screen.getByTestId("alert-triangle")).toBeDefined();
  });

  it("renders operating point marker when operatingAlphaDeg is provided", () => {
    render(
      <AirfoilPreviewViewerPanel
        {...baseProps}
        operatingAlphaDeg={5}
      />,
    );
    // The marker should appear as a circle element in the SVG polar chart
    // We look for an SVG circle with the operating point data-testid
    const marker = screen.queryByTestId("operating-point-marker");
    expect(marker).not.toBeNull();
  });

  it("does NOT render operating point marker when operatingAlphaDeg is not provided", () => {
    render(<AirfoilPreviewViewerPanel {...baseProps} />);
    expect(screen.queryByTestId("operating-point-marker")).toBeNull();
  });

  it("does NOT render operating point marker when alphaDeg array is empty (empty-array guard)", () => {
    // Regression guard for the unguarded alphas[0] access: an empty alphaDeg array
    // must not produce a NaN coordinate that renders an invisible/misplaced marker.
    const emptyAlphaAnalysis: AirfoilAnalysisResult = {
      ...mockAnalysis,
      alphaDeg: [],
      cl: [],
      cd: [],
      cm: [],
      clOverCd: [],
    };
    render(
      <AirfoilPreviewViewerPanel
        {...baseProps}
        rootAnalysisResult={emptyAlphaAnalysis}
        operatingAlphaDeg={5}
      />,
    );
    // The component must not crash, and the marker must be absent (no valid coords)
    expect(screen.queryByTestId("operating-point-marker")).toBeNull();
  });

  it("banner text mentions tip Re reduction", () => {
    render(
      <AirfoilPreviewViewerPanel
        {...baseProps}
        tipAirfoilName="naca0012"
        tipRe={100000}
        rootRe={200000}
      />,
    );
    const alert = screen.getByRole("alert");
    // Should mention tip or Re in some form
    expect(alert.textContent).toMatch(/tip|Re|Tip/i);
  });

  // tip_re_flag is the AUTHORITATIVE trigger when a suitability item is available.
  // The arithmetic fallback (tipRe < rootRe) is only used when no item is present.

  it("shows tip-Re banner when tipSuitabilityItem.tip_re_flag is true, even if tipRe > rootRe", () => {
    // Authoritative path: backend flag set → show banner regardless of arithmetic
    render(
      <AirfoilPreviewViewerPanel
        {...baseProps}
        tipAirfoilName="naca0012"
        tipRe={300000}
        rootRe={200000}
        tipSuitabilityItem={{ ...baseSuitabilityItem, tip_re_flag: true }}
      />,
    );
    expect(screen.getByRole("alert")).toBeDefined();
  });

  it("does NOT show tip-Re banner when tipSuitabilityItem.tip_re_flag is false, even if tipRe < rootRe", () => {
    // Authoritative path: backend flag clear → no banner even when arithmetic says tipRe < rootRe
    render(
      <AirfoilPreviewViewerPanel
        {...baseProps}
        tipAirfoilName="naca0012"
        tipRe={100000}
        rootRe={200000}
        tipSuitabilityItem={{ ...baseSuitabilityItem, tip_re_flag: false }}
      />,
    );
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("falls back to arithmetic (tipRe < rootRe) when no tipSuitabilityItem is provided", () => {
    // Fallback path: no suitability data, use arithmetic check
    render(
      <AirfoilPreviewViewerPanel
        {...baseProps}
        tipAirfoilName="naca0012"
        tipRe={100000}
        rootRe={200000}
        // tipSuitabilityItem intentionally omitted
      />,
    );
    expect(screen.getByRole("alert")).toBeDefined();
  });
});
