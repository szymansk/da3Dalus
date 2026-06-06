/**
 * Regression test for gh-868: Airfoil-Preview chart column must be
 * vertically scrollable (overflow-y-auto), not clipped (overflow-hidden).
 *
 * The right-hand config panel already uses overflow-y-auto; the chart column
 * must follow the same pattern so lower charts are reachable by scrolling.
 */
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
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

describe("AirfoilPreviewViewerPanel — scroll (gh-868)", () => {
  it("chart column container has overflow-y-auto and does NOT have overflow-hidden", () => {
    const { getByTestId } = render(<AirfoilPreviewViewerPanel {...baseProps} />);
    const container = getByTestId("airfoil-preview-charts");
    const classes = container.className;
    expect(classes).toContain("overflow-y-auto");
    expect(classes).not.toContain("overflow-hidden");
  });
});
