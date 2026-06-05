/**
 * Unit tests for AirfoilProxyChart component (gh-841).
 *
 * Tests verify:
 * - Empty state when no analysis result
 * - Chart renders with cl/cd and cl^1.5/cd curves
 * - Disclaimer badge present (clearly labelled as 2D proxy)
 * - Peak markers rendered
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AirfoilProxyChart } from "@/components/workbench/AirfoilProxyChart";
import type { AirfoilAnalysisResult } from "@/hooks/useAirfoilAnalysis";

// ---------------------------------------------------------------------------
// Test fixture — representative NACA 2412 polar values
// ---------------------------------------------------------------------------

const MOCK_ANALYSIS: AirfoilAnalysisResult = {
  airfoilName: "naca2412",
  alphaDeg: [-4, -2, 0, 2, 4, 6, 8, 10, 12],
  cl: [-0.2, 0.1, 0.35, 0.55, 0.75, 0.95, 1.1, 1.2, 1.3],
  cd: [0.012, 0.010, 0.009, 0.009, 0.010, 0.012, 0.015, 0.020, 0.027],
  cm: [-0.05, -0.04, -0.04, -0.04, -0.04, -0.04, -0.04, -0.04, -0.04],
  clOverCd: [-16.7, 10.0, 38.9, 61.1, 75.0, 79.2, 73.3, 60.0, 48.1],
  clMax: 1.3,
  alphaAtClMax: 12,
  ldMax: 79.2,
  alphaAtLdMax: 6,
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("AirfoilProxyChart", () => {
  it("renders empty state when no analysis result", () => {
    render(<AirfoilProxyChart analysisResult={null} />);
    expect(screen.getByTestId("airfoil-proxy-chart-empty")).toBeDefined();
  });

  it("renders chart when analysis result is provided", () => {
    render(<AirfoilProxyChart analysisResult={MOCK_ANALYSIS} />);
    expect(screen.getByTestId("airfoil-proxy-chart")).toBeDefined();
  });

  it("renders cl/cd line", () => {
    render(<AirfoilProxyChart analysisResult={MOCK_ANALYSIS} />);
    expect(screen.getByTestId("airfoil-proxy-clovercd-line")).toBeDefined();
  });

  it("renders cl^1.5/cd line", () => {
    render(<AirfoilProxyChart analysisResult={MOCK_ANALYSIS} />);
    expect(screen.getByTestId("airfoil-proxy-cl15-line")).toBeDefined();
  });

  it("renders peak cl/cd marker", () => {
    render(<AirfoilProxyChart analysisResult={MOCK_ANALYSIS} />);
    expect(screen.getByTestId("airfoil-proxy-peak-clovercd")).toBeDefined();
  });

  it("renders peak cl^1.5/cd marker", () => {
    render(<AirfoilProxyChart analysisResult={MOCK_ANALYSIS} />);
    expect(screen.getByTestId("airfoil-proxy-peak-cl15overcd")).toBeDefined();
  });

  it("shows disclaimer badge labelling chart as 2D proxy", () => {
    render(<AirfoilProxyChart analysisResult={MOCK_ANALYSIS} />);
    expect(screen.getByTestId("airfoil-proxy-disclaimer")).toBeDefined();
  });

  it("shows title Profil-Indikator (2D)", () => {
    render(<AirfoilProxyChart analysisResult={MOCK_ANALYSIS} />);
    // The title span contains "Profil-Indikator (2D)" — at least one element matches
    const matches = screen.getAllByText(/Profil-Indikator/);
    expect(matches.length).toBeGreaterThan(0);
  });

  it("empty state when all cl values are non-positive", () => {
    const noPositiveCl: AirfoilAnalysisResult = {
      ...MOCK_ANALYSIS,
      cl: [-0.5, -0.2, 0.0],
      cd: [0.01, 0.01, 0.01],
    };
    render(<AirfoilProxyChart analysisResult={noPositiveCl} />);
    expect(screen.getByTestId("airfoil-proxy-chart-empty")).toBeDefined();
  });
});
