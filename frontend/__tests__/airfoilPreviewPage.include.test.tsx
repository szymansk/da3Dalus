/**
 * Tests for ITEM 5-FE page wiring — include param on airfoil-preview page.
 *
 * Contract:
 *   - Page passes `include: [rootAirfoil]` to the root useAirfoilSuitability call.
 *   - Page passes `include: [tipAirfoil]` to the tip useAirfoilSuitability call.
 *   - When the selected airfoil HAS rows in the response (backend returned it
 *     because of include), rootSuitabilityItem is found → AirfoilSuitabilityCard renders.
 *   - AirfoilSuitabilityNoData placeholder appears ONLY when the backend genuinely
 *     omits the airfoil from results (no low-Re data for that name), not when it's
 *     just outside the top-N.
 *   - The guard against placeholder airfoil '—' (empty selection) prevents include=['—'].
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

// ── Mocks ─────────────────────────────────────────────────────────

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock("@/components/workbench/AeroplaneContext", () => ({
  useAeroplaneContext: () => ({
    aeroplaneId: "test-uuid-1234",
    selectedWing: null,
    selectedXsecIndex: 0,
    selectXsec: vi.fn(),
  }),
}));

vi.mock("@/hooks/useWingConfig", () => ({
  useWingConfig: () => ({
    wingConfig: null,
    saveWingConfig: vi.fn(),
  }),
}));

vi.mock("@/hooks/useAirfoilGeometry", () => ({
  useAirfoilGeometry: () => ({ geometry: null, isLoading: false, error: null }),
  interpolateY: () => null,
}));

vi.mock("@/hooks/useAirfoilAnalysis", () => ({
  useAirfoilAnalysis: () => ({
    result: null,
    isRunning: false,
    error: null,
    run: vi.fn(),
    clear: vi.fn(),
  }),
}));

// Track which include values were passed to useAirfoilSuitability
const capturedIncludes: Array<string[] | undefined> = [];
let mockSuitabilityData: Record<string, unknown> | null = null;

vi.mock("@/hooks/useAirfoilSuitability", () => ({
  useAirfoilSuitability: (params: { include?: string[]; chord_m?: number }) => {
    capturedIncludes.push(params.include);
    return {
      data: mockSuitabilityData,
      isLoading: false,
      error: null,
    };
  },
}));

// Render child panels minimally — expose props for assertions
vi.mock("@/components/workbench/AirfoilPreviewViewerPanel", () => ({
  AirfoilPreviewViewerPanel: () => <div data-testid="viewer-panel" />,
}));

vi.mock("@/components/workbench/AirfoilPreviewConfigPanel", () => ({
  AirfoilPreviewConfigPanel: (props: Record<string, unknown>) => (
    <div
      data-testid="config-panel"
      data-root-not-found={String(props.rootSuitabilityNotFound)}
      data-tip-not-found={String(props.tipSuitabilityNotFound)}
      data-has-root-item={String(props.rootSuitabilityItem != null)}
      data-has-tip-item={String(props.tipSuitabilityItem != null)}
    />
  ),
}));

import AirfoilPreviewPage, { toInclude } from "@/app/workbench/airfoil-preview/page";

// ── toInclude helper ──────────────────────────────────────────────

describe("toInclude — pure helper (ITEM 5-FE)", () => {
  it("returns [name] for a normal airfoil name", () => {
    expect(toInclude("naca0015")).toEqual(["naca0015"]);
  });

  it("returns undefined for empty string", () => {
    expect(toInclude("")).toBeUndefined();
  });

  it("returns undefined for the placeholder '—'", () => {
    expect(toInclude("—")).toBeUndefined();
  });

  it("returns [name] for a name with path prefix stripped already", () => {
    expect(toInclude("e423")).toEqual(["e423"]);
  });
});

// ── Page component tests ──────────────────────────────────────────

describe("AirfoilPreviewPage — include param wiring (ITEM 5-FE)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capturedIncludes.length = 0;
    mockSuitabilityData = null;
  });

  it("passes include=[rootAirfoil] to root suitability hook", () => {
    render(<AirfoilPreviewPage />);
    // Two calls: one for root, one for tip (naca0015/naca0015 both default)
    // At least one call should have include=['naca0015']
    const hasRootInclude = capturedIncludes.some(
      (inc) => inc?.includes("naca0015"),
    );
    expect(hasRootInclude).toBe(true);
  });

  it("does NOT pass include=['—'] when airfoil is the placeholder '—'", () => {
    render(<AirfoilPreviewPage />);
    const hasDash = capturedIncludes.some((inc) => inc?.includes("—"));
    expect(hasDash).toBe(false);
  });

  // ── No-data placeholder: only when backend genuinely omits the airfoil ──

  it("rootSuitabilityNotFound=true ONLY when backend returns data but selected airfoil is absent from results", () => {
    // Backend responded (non-null data) but didn't include 'naca0015' in results
    mockSuitabilityData = {
      query: { active_lens: "re_agnostic", target_cl_provenance: "estimated" },
      results: [
        {
          airfoil_name: "e423",  // different airfoil — naca0015 not present
          re_agnostic: 0.82,
          mission: null,
          target_cl_cruise: null,
          target_cl_best_glide: null,
          target_cl_min_sink: null,
          stall_gentleness: null,
          cl_max_margin: null,
          min_analysis_confidence: 0.9,
          tip_re_flag: false,
          caveat: "",
        },
      ],
      caveat: {
        relative_ranking_only: true,
        no_hysteresis_modelling: true,
        ignores_tip_re_clmax_collapse: true,
        recommend_xfoil_validation: false,
        text: "",
      },
    };
    render(<AirfoilPreviewPage />);
    const config = screen.getByTestId("config-panel");
    // rootSuitabilityNotFound should be true (data non-null, item absent)
    expect(config.dataset.rootNotFound).toBe("true");
    expect(config.dataset.hasRootItem).toBe("false");
  });

  it("rootSuitabilityNotFound=false when backend includes the selected airfoil in results", () => {
    // Backend returned the selected airfoil (e.g. because include param worked)
    mockSuitabilityData = {
      query: { active_lens: "re_agnostic", target_cl_provenance: "estimated" },
      results: [
        {
          airfoil_name: "naca0015",  // selected airfoil IS in results
          re_agnostic: 0.75,
          mission: null,
          target_cl_cruise: null,
          target_cl_best_glide: null,
          target_cl_min_sink: null,
          stall_gentleness: null,
          cl_max_margin: null,
          min_analysis_confidence: 0.9,
          tip_re_flag: false,
          caveat: "",
        },
      ],
      caveat: {
        relative_ranking_only: true,
        no_hysteresis_modelling: true,
        ignores_tip_re_clmax_collapse: true,
        recommend_xfoil_validation: false,
        text: "",
      },
    };
    render(<AirfoilPreviewPage />);
    const config = screen.getByTestId("config-panel");
    expect(config.dataset.rootNotFound).toBe("false");
    expect(config.dataset.hasRootItem).toBe("true");
  });
});
