/**
 * Regression test for gh-868: Airfoil-Preview charts must be vertically
 * scrollable.
 *
 * IMPORTANT (the real bug): the panel root expands to full content height, so
 * it never overflows *itself* — putting `overflow-y-auto` on the panel root
 * (the first, ineffective fix) produced no scrollbar. The actual scroll
 * container is the bounded-height page wrapper in
 * `app/workbench/airfoil-preview/page.tsx` (`flex-1 overflow-y-auto`,
 * data-testid="airfoil-preview-scroll").
 *
 * jsdom has no layout engine, so real scrollability is verified in a browser
 * (Playwright) — see the PR. This unit test only guards against re-introducing
 * the wrong fix: the panel root must NOT try to own vertical overflow (neither
 * clip with overflow-hidden nor scroll with overflow-y-auto); it must grow and
 * let the page wrapper scroll.
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
  it("panel root grows and does NOT own vertical overflow (page wrapper scrolls)", () => {
    const { getByTestId } = render(<AirfoilPreviewViewerPanel {...baseProps} />);
    const container = getByTestId("airfoil-preview-charts");
    const classes = container.className;
    // Must be a growing flex column...
    expect(classes).toContain("flex-col");
    expect(classes).toContain("flex-1");
    // ...but must NOT clip (the original bug) NOR try to scroll itself (the
    // ineffective first fix). Real scrolling lives on the page wrapper.
    expect(classes).not.toContain("overflow-hidden");
    expect(classes).not.toContain("overflow-y-auto");
  });
});
