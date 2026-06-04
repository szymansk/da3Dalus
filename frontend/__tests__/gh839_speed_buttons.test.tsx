/**
 * TDD tests for gh-839-FE:
 * 1. Speed quick-set buttons (Cruise / Best-Glide / Min-Sink) in AirfoilPreviewConfigPanel
 * 2. Operating-point markers on alpha-diagrams in AirfoilPreviewViewerPanel
 *
 * Tests are written RED first; implementation follows.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// ── Mocks ─────────────────────────────────────────────────────────

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
  Maximize2: (p: Record<string, unknown>) => <svg data-testid="maximize" {...p} />,
  Minimize2: (p: Record<string, unknown>) => <svg data-testid="minimize" {...p} />,
}));

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
import { AirfoilPreviewViewerPanel } from "../components/workbench/AirfoilPreviewViewerPanel";
import type { AirfoilAnalysisResult } from "../hooks/useAirfoilAnalysis";
import type { AirfoilGeometry } from "../hooks/useAirfoilGeometry";

// ── Shared fixtures ────────────────────────────────────────────────

const BASE_CONFIG_PROPS = {
  rootAirfoil: "e423",
  tipAirfoil: "e423",
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
  tipRe: 200000,
  onRootReChange: vi.fn(),
  onTipReChange: vi.fn(),
  rootChordMm: 200,
  tipChordMm: 200,
  isDirty: false,
  isSaving: false,
  onSave: vi.fn(),
  onRevert: vi.fn(),
  onBack: vi.fn(),
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

const mockGeometry: AirfoilGeometry = {
  upper: [[0, 0], [0.5, 0.08], [1, 0]],
  lower: [[0, 0], [0.5, -0.04], [1, 0]],
  maxThicknessPct: 12,
  maxCamberPct: 4,
  maxThicknessX: 0.3,
};

const BASE_VIEWER_PROPS = {
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

// ── Tests: Speed Quick-Set Buttons ────────────────────────────────

describe("gh-839-FE: Speed quick-set buttons in AirfoilPreviewConfigPanel", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders Cruise button when v_cruise_mps is provided", () => {
    render(
      <AirfoilPreviewConfigPanel
        {...BASE_CONFIG_PROPS}
        suitabilitySpeedContext={{ v_cruise_mps: 18, v_md_mps: null, v_min_sink_mps: null }}
      />,
    );
    expect(screen.getByTestId("speed-btn-cruise")).toBeDefined();
  });

  it("renders Best-Glide button when v_md_mps is provided", () => {
    render(
      <AirfoilPreviewConfigPanel
        {...BASE_CONFIG_PROPS}
        suitabilitySpeedContext={{ v_cruise_mps: null, v_md_mps: 13, v_min_sink_mps: null }}
      />,
    );
    expect(screen.getByTestId("speed-btn-best-glide")).toBeDefined();
  });

  it("renders Min-Sink button when v_min_sink_mps is provided", () => {
    render(
      <AirfoilPreviewConfigPanel
        {...BASE_CONFIG_PROPS}
        suitabilitySpeedContext={{ v_cruise_mps: null, v_md_mps: null, v_min_sink_mps: 10 }}
      />,
    );
    expect(screen.getByTestId("speed-btn-min-sink")).toBeDefined();
  });

  it("does NOT render speed buttons when suitabilitySpeedContext is not provided", () => {
    render(<AirfoilPreviewConfigPanel {...BASE_CONFIG_PROPS} />);
    expect(screen.queryByTestId("speed-btn-cruise")).toBeNull();
    expect(screen.queryByTestId("speed-btn-best-glide")).toBeNull();
    expect(screen.queryByTestId("speed-btn-min-sink")).toBeNull();
  });

  it("does NOT render Cruise button when v_cruise_mps is null", () => {
    render(
      <AirfoilPreviewConfigPanel
        {...BASE_CONFIG_PROPS}
        suitabilitySpeedContext={{ v_cruise_mps: null, v_md_mps: 13, v_min_sink_mps: 10 }}
      />,
    );
    expect(screen.queryByTestId("speed-btn-cruise")).toBeNull();
    expect(screen.getByTestId("speed-btn-best-glide")).toBeDefined();
    expect(screen.getByTestId("speed-btn-min-sink")).toBeDefined();
  });

  it("clicking Cruise button calls onVelocityChange with v_cruise_mps", async () => {
    const onVelocityChange = vi.fn();
    const user = userEvent.setup();
    render(
      <AirfoilPreviewConfigPanel
        {...BASE_CONFIG_PROPS}
        onVelocityChange={onVelocityChange}
        suitabilitySpeedContext={{ v_cruise_mps: 18, v_md_mps: 13, v_min_sink_mps: 10 }}
      />,
    );
    await user.click(screen.getByTestId("speed-btn-cruise"));
    expect(onVelocityChange).toHaveBeenCalledWith(18);
  });

  it("clicking Best-Glide button calls onVelocityChange with v_md_mps", async () => {
    const onVelocityChange = vi.fn();
    const user = userEvent.setup();
    render(
      <AirfoilPreviewConfigPanel
        {...BASE_CONFIG_PROPS}
        onVelocityChange={onVelocityChange}
        suitabilitySpeedContext={{ v_cruise_mps: 18, v_md_mps: 13, v_min_sink_mps: 10 }}
      />,
    );
    await user.click(screen.getByTestId("speed-btn-best-glide"));
    expect(onVelocityChange).toHaveBeenCalledWith(13);
  });

  it("clicking Min-Sink button calls onVelocityChange with v_min_sink_mps", async () => {
    const onVelocityChange = vi.fn();
    const user = userEvent.setup();
    render(
      <AirfoilPreviewConfigPanel
        {...BASE_CONFIG_PROPS}
        onVelocityChange={onVelocityChange}
        suitabilitySpeedContext={{ v_cruise_mps: 18, v_md_mps: 13, v_min_sink_mps: 10 }}
      />,
    );
    await user.click(screen.getByTestId("speed-btn-min-sink"));
    expect(onVelocityChange).toHaveBeenCalledWith(10);
  });

  it("renders all three buttons when all speeds are provided", () => {
    render(
      <AirfoilPreviewConfigPanel
        {...BASE_CONFIG_PROPS}
        suitabilitySpeedContext={{ v_cruise_mps: 18, v_md_mps: 13, v_min_sink_mps: 10 }}
      />,
    );
    expect(screen.getByTestId("speed-btn-cruise")).toBeDefined();
    expect(screen.getByTestId("speed-btn-best-glide")).toBeDefined();
    expect(screen.getByTestId("speed-btn-min-sink")).toBeDefined();
  });
});

// ── Tests: Diagram markers ─────────────────────────────────────────

describe("gh-839-FE: Key-point markers in AirfoilPreviewViewerPanel", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows CL_max marker when analysis has clMax and alphaAtClMax", () => {
    render(
      <AirfoilPreviewViewerPanel
        {...BASE_VIEWER_PROPS}
        rootAnalysisResult={mockAnalysis}
      />,
    );
    // CL_max and L/D_max markers should be rendered in the SVG diagrams
    const clMaxMarkers = screen.getAllByTestId("clmax-marker");
    expect(clMaxMarkers.length).toBeGreaterThan(0);
  });

  it("shows L/D_max marker when analysis has ldMax and alphaAtLdMax", () => {
    render(
      <AirfoilPreviewViewerPanel
        {...BASE_VIEWER_PROPS}
        rootAnalysisResult={mockAnalysis}
      />,
    );
    const ldMaxMarkers = screen.getAllByTestId("ldmax-marker");
    expect(ldMaxMarkers.length).toBeGreaterThan(0);
  });

  it("shows operating-point markers for cruise/best-glide/min-sink when provided", () => {
    render(
      <AirfoilPreviewViewerPanel
        {...BASE_VIEWER_PROPS}
        rootAnalysisResult={mockAnalysis}
        operatingAlphaDeg={5}
        operatingPoints={{
          cruise: { alpha: 5, label: "Cruise" },
          bestGlide: { alpha: 10, label: "Best-Glide" },
          minSink: { alpha: 12, label: "Min-Sink" },
        }}
      />,
    );
    // All three operating point markers should be present
    expect(screen.getAllByTestId("op-marker-cruise").length).toBeGreaterThan(0);
    expect(screen.getAllByTestId("op-marker-best-glide").length).toBeGreaterThan(0);
    expect(screen.getAllByTestId("op-marker-min-sink").length).toBeGreaterThan(0);
  });

  it("does NOT render operating-point markers when operatingPoints is not provided", () => {
    render(
      <AirfoilPreviewViewerPanel
        {...BASE_VIEWER_PROPS}
        rootAnalysisResult={mockAnalysis}
      />,
    );
    expect(screen.queryAllByTestId("op-marker-cruise")).toHaveLength(0);
    expect(screen.queryAllByTestId("op-marker-best-glide")).toHaveLength(0);
    expect(screen.queryAllByTestId("op-marker-min-sink")).toHaveLength(0);
  });

  it("does NOT render clmax-marker when analysis clMax is null", () => {
    const noClMaxAnalysis: AirfoilAnalysisResult = {
      ...mockAnalysis,
      clMax: null,
      alphaAtClMax: null,
    };
    render(
      <AirfoilPreviewViewerPanel
        {...BASE_VIEWER_PROPS}
        rootAnalysisResult={noClMaxAnalysis}
      />,
    );
    expect(screen.queryAllByTestId("clmax-marker")).toHaveLength(0);
  });

  it("shows a legend with labels when multiple markers are rendered", () => {
    render(
      <AirfoilPreviewViewerPanel
        {...BASE_VIEWER_PROPS}
        rootAnalysisResult={mockAnalysis}
        operatingPoints={{
          cruise: { alpha: 5, label: "Cruise" },
          bestGlide: { alpha: 10, label: "Best-Glide" },
          minSink: { alpha: 12, label: "Min-Sink" },
        }}
      />,
    );
    // Legend labels should be rendered somewhere in the charts
    expect(screen.getByTestId("chart-markers-legend")).toBeDefined();
  });
});
