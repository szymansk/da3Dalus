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
});
