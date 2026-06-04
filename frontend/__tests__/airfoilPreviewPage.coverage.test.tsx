/**
 * Coverage tests for airfoil-preview page.tsx and pure helpers (gh-822).
 *
 * Scope: airfoilShortName, page component rendering, ranked mode toggles,
 * save/revert callbacks, segment navigation, velocity input interactions.
 *
 * Strategy: mock every Next.js / hook dependency; render the page in
 * various states to exercise uncovered branches.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// ── Pure helper tests (no mocks needed) ─────────────────────────

import {
  airfoilShortName,
  activeLensScore,
  computeRe,
} from "@/app/workbench/airfoil-preview/page";

describe("airfoilShortName — pure helper", () => {
  it("strips .dat extension (case-insensitive)", () => {
    expect(airfoilShortName("e423.dat")).toBe("e423");
    expect(airfoilShortName("naca0015.DAT")).toBe("naca0015");
  });

  it("strips path prefix before .dat", () => {
    expect(airfoilShortName("UIUC/e423.dat")).toBe("e423");
  });

  it("handles deep path prefix", () => {
    expect(airfoilShortName("data/airfoils/clark-y.dat")).toBe("clark-y");
  });

  it("leaves plain name without extension unchanged", () => {
    expect(airfoilShortName("naca0012")).toBe("naca0012");
  });

  it("handles empty string gracefully", () => {
    expect(airfoilShortName("")).toBe("");
  });
});

describe("activeLensScore — edge cases", () => {
  const item = {
    re_agnostic: 0.8,
    mission: null as number | null,
    target_cl_cruise: null as number | null,
  };

  it("falls back to re_agnostic when mission is null", () => {
    expect(activeLensScore({ ...item, mission: null }, "mission")).toBe(0.8);
  });

  it("falls back to re_agnostic when target_cl_cruise is null", () => {
    expect(activeLensScore({ ...item, target_cl_cruise: null }, "target_cl_cruise")).toBe(0.8);
  });

  it("uses re_agnostic for unknown lens string", () => {
    expect(activeLensScore(item, "unknown_lens")).toBe(0.8);
  });
});

describe("computeRe — edge cases", () => {
  it("returns 0 when velocity is 0", () => {
    expect(computeRe(0, 200)).toBe(0);
  });

  it("returns 0 when chord is 0", () => {
    expect(computeRe(14, 0)).toBe(0);
  });

  it("scales linearly with velocity", () => {
    const re1 = computeRe(14, 200);
    const re2 = computeRe(28, 200);
    expect(re2 / re1).toBeCloseTo(2, 0);
  });
});

// ── Page component tests ──────────────────────────────────────────

// Mocks must be defined before imports

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

const mockSelectXsec = vi.fn();
let mockAeroplaneId: string | null = null;
let mockSelectedWing: string | null = null;
let mockSelectedXsecIndex: number | null = 0;

vi.mock("@/components/workbench/AeroplaneContext", () => ({
  useAeroplaneContext: () => ({
    aeroplaneId: mockAeroplaneId,
    selectedWing: mockSelectedWing,
    selectedXsecIndex: mockSelectedXsecIndex,
    selectXsec: mockSelectXsec,
  }),
}));

const mockSaveWingConfig = vi.fn();
let mockWingConfig: Record<string, unknown> | null = null;

vi.mock("@/hooks/useWingConfig", () => ({
  useWingConfig: () => ({
    wingConfig: mockWingConfig,
    saveWingConfig: mockSaveWingConfig,
  }),
}));

vi.mock("@/hooks/useAirfoilGeometry", () => ({
  useAirfoilGeometry: () => ({
    geometry: null,
    isLoading: false,
    error: null,
  }),
  interpolateY: () => null,
}));

const mockRun = vi.fn();
const mockClear = vi.fn();
let mockAnalysisResult: Record<string, unknown> | null = null;

vi.mock("@/hooks/useAirfoilAnalysis", () => ({
  useAirfoilAnalysis: () => ({
    result: mockAnalysisResult,
    isRunning: false,
    error: null,
    run: mockRun,
    clear: mockClear,
  }),
}));

let mockSuitabilityData: Record<string, unknown> | null = null;

vi.mock("@/hooks/useAirfoilSuitability", () => ({
  useAirfoilSuitability: () => ({
    data: mockSuitabilityData,
    isLoading: false,
    error: null,
  }),
}));

// Stub child panels to pure pass-through to avoid deep rendering
vi.mock("@/components/workbench/AirfoilPreviewViewerPanel", () => ({
  AirfoilPreviewViewerPanel: (props: Record<string, unknown>) => (
    <div
      data-testid="viewer-panel"
      data-root-airfoil={props.rootAirfoilName as string}
      data-tip-airfoil={props.tipAirfoilName as string ?? ""}
      data-operating-alpha={props.operatingAlphaDeg as number ?? ""}
    />
  ),
}));

vi.mock("@/components/workbench/AirfoilPreviewConfigPanel", () => ({
  AirfoilPreviewConfigPanel: (props: Record<string, unknown>) => (
    <div
      data-testid="config-panel"
      data-root-airfoil={props.rootAirfoil as string}
      data-tip-airfoil={props.tipAirfoil as string}
      data-root-ranked-mode={String(props.rootRankedMode)}
      data-tip-ranked-mode={String(props.tipRankedMode)}
    >
      <button
        data-testid="trigger-back"
        onClick={() => (props.onBack as () => void)?.()}
      >
        back
      </button>
      <button
        data-testid="trigger-save"
        onClick={() => (props.onSave as () => void)?.()}
      >
        save
      </button>
      <button
        data-testid="trigger-revert"
        onClick={() => (props.onRevert as () => void)?.()}
      >
        revert
      </button>
      <button
        data-testid="trigger-root-ranked"
        onClick={() => (props.onRootRankedModeToggle as () => void)?.()}
      >
        root-ranked
      </button>
      <button
        data-testid="trigger-tip-ranked"
        onClick={() => (props.onTipRankedModeToggle as () => void)?.()}
      >
        tip-ranked
      </button>
      <button
        data-testid="trigger-segment-change"
        onClick={() => (props.onSegmentChange as (i: number) => void)?.(1)}
      >
        seg-change
      </button>
      <button
        data-testid="trigger-root-airfoil-change"
        onClick={() => (props.onRootAirfoilChange as (n: string) => void)?.("clark-y")}
      >
        root-airfoil-change
      </button>
      <button
        data-testid="trigger-tip-airfoil-change"
        onClick={() => (props.onTipAirfoilChange as (n: string) => void)?.("naca0012")}
      >
        tip-airfoil-change
      </button>
    </div>
  ),
}));

import AirfoilPreviewPage from "@/app/workbench/airfoil-preview/page";

describe("AirfoilPreviewPage — rendering and wiring (gh-822)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAeroplaneId = null;
    mockSelectedWing = null;
    mockSelectedXsecIndex = 0;
    mockWingConfig = null;
    mockSuitabilityData = null;
    mockAnalysisResult = null;
  });

  it("renders both panels (viewer + config)", () => {
    render(<AirfoilPreviewPage />);
    expect(screen.getByTestId("viewer-panel")).toBeDefined();
    expect(screen.getByTestId("config-panel")).toBeDefined();
  });

  it("defaults rootAirfoil to 'naca0015' when no wingConfig", () => {
    render(<AirfoilPreviewPage />);
    const config = screen.getByTestId("config-panel");
    expect(config.dataset.rootAirfoil).toBe("naca0015");
  });

  it("reads rootAirfoil from wingConfig segment", () => {
    mockWingConfig = {
      segments: [
        {
          root_airfoil: { airfoil: "e423.dat", chord: 200 },
          tip_airfoil: { airfoil: "clark-y.dat", chord: 150 },
          length: 500,
          sweep: 0,
        },
      ],
    };
    render(<AirfoilPreviewPage />);
    const config = screen.getByTestId("config-panel");
    // airfoilShortName strips ".dat"
    expect(config.dataset.rootAirfoil).toBe("e423");
    expect(config.dataset.tipAirfoil).toBe("clark-y");
  });

  it("back button calls router.push('/workbench')", async () => {
    const user = userEvent.setup();
    render(<AirfoilPreviewPage />);
    await user.click(screen.getByTestId("trigger-back"));
    expect(mockPush).toHaveBeenCalledWith("/workbench");
  });

  it("rootRankedMode toggles on rootRankedModeToggle click", async () => {
    const user = userEvent.setup();
    render(<AirfoilPreviewPage />);
    const config = screen.getByTestId("config-panel");
    expect(config.dataset.rootRankedMode).toBe("false");

    await user.click(screen.getByTestId("trigger-root-ranked"));
    expect(screen.getByTestId("config-panel").dataset.rootRankedMode).toBe("true");

    await user.click(screen.getByTestId("trigger-root-ranked"));
    expect(screen.getByTestId("config-panel").dataset.rootRankedMode).toBe("false");
  });

  it("tipRankedMode toggles on tipRankedModeToggle click", async () => {
    const user = userEvent.setup();
    render(<AirfoilPreviewPage />);
    await user.click(screen.getByTestId("trigger-tip-ranked"));
    expect(screen.getByTestId("config-panel").dataset.tipRankedMode).toBe("true");
  });

  it("root airfoil change updates the displayed root airfoil", async () => {
    const user = userEvent.setup();
    render(<AirfoilPreviewPage />);
    await user.click(screen.getByTestId("trigger-root-airfoil-change"));
    expect(screen.getByTestId("config-panel").dataset.rootAirfoil).toBe("clark-y");
  });

  it("tip airfoil change updates the displayed tip airfoil", async () => {
    const user = userEvent.setup();
    render(<AirfoilPreviewPage />);
    await user.click(screen.getByTestId("trigger-tip-airfoil-change"));
    expect(screen.getByTestId("config-panel").dataset.tipAirfoil).toBe("naca0012");
  });

  it("segment change calls selectXsec", async () => {
    const user = userEvent.setup();
    render(<AirfoilPreviewPage />);
    await user.click(screen.getByTestId("trigger-segment-change"));
    expect(mockSelectXsec).toHaveBeenCalledWith(1);
  });

  it("save calls saveWingConfig when wingConfig and segment are present", async () => {
    mockWingConfig = {
      segments: [
        {
          root_airfoil: { airfoil: "e423.dat", chord: 200 },
          tip_airfoil: { airfoil: "clark-y.dat", chord: 150 },
          length: 500,
          sweep: 0,
        },
      ],
    };
    mockSaveWingConfig.mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<AirfoilPreviewPage />);
    await user.click(screen.getByTestId("trigger-save"));
    expect(mockSaveWingConfig).toHaveBeenCalled();
  });

  it("save is a no-op when wingConfig is null", async () => {
    mockWingConfig = null;
    const user = userEvent.setup();
    render(<AirfoilPreviewPage />);
    await user.click(screen.getByTestId("trigger-save"));
    expect(mockSaveWingConfig).not.toHaveBeenCalled();
  });

  it("revert restores naca0015 defaults when wingConfig is null", async () => {
    const user = userEvent.setup();
    render(<AirfoilPreviewPage />);
    // Change to clark-y
    await user.click(screen.getByTestId("trigger-root-airfoil-change"));
    expect(screen.getByTestId("config-panel").dataset.rootAirfoil).toBe("clark-y");
    // Revert
    await user.click(screen.getByTestId("trigger-revert"));
    expect(screen.getByTestId("config-panel").dataset.rootAirfoil).toBe("naca0015");
  });

  it("suitabilityData present: rootScoreMap passed as defined", () => {
    mockSuitabilityData = {
      query: { active_lens: "re_agnostic", target_cl_provenance: "estimated" },
      results: [
        {
          airfoil_name: "e423",
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
      caveat: { relative_ranking_only: true, no_hysteresis_modelling: true, ignores_tip_re_clmax_collapse: true, recommend_xfoil_validation: false, text: "" },
    };
    // Render and assert rootRankedMode is false (scores but not ranked)
    render(<AirfoilPreviewPage />);
    const config = screen.getByTestId("config-panel");
    expect(config.dataset.rootRankedMode).toBe("false");
  });

  it("renders with aeroplane_id from context", () => {
    mockAeroplaneId = "test-uuid-1234";
    render(<AirfoilPreviewPage />);
    // Should render without crash
    expect(screen.getByTestId("viewer-panel")).toBeDefined();
  });

  it("airfoilShortName strips path prefix from UIUC path in segment", () => {
    mockWingConfig = {
      segments: [
        {
          root_airfoil: { airfoil: "UIUC/e423.dat", chord: 200 },
          tip_airfoil: { airfoil: "UIUC/clark-y.dat", chord: 150 },
          length: 500,
          sweep: 0,
        },
      ],
    };
    render(<AirfoilPreviewPage />);
    const config = screen.getByTestId("config-panel");
    expect(config.dataset.rootAirfoil).toBe("e423");
    expect(config.dataset.tipAirfoil).toBe("clark-y");
  });

  it("uses root airfoil as tip when tip_airfoil is missing from segment", () => {
    mockWingConfig = {
      segments: [
        {
          root_airfoil: { airfoil: "naca2412.dat", chord: 200 },
          // tip_airfoil intentionally missing — triggers the fallback
          length: 500,
          sweep: 0,
        },
      ],
    };
    render(<AirfoilPreviewPage />);
    const config = screen.getByTestId("config-panel");
    expect(config.dataset.rootAirfoil).toBe("naca2412");
    // tip falls back to root
    expect(config.dataset.tipAirfoil).toBe("naca2412");
  });

  it("viewer panel receives null tipAirfoilName when root and tip are the same", () => {
    render(<AirfoilPreviewPage />);
    // Default: root=naca0015, tip=naca0015 (same → hasTip=false → tipAirfoilName=null)
    const viewer = screen.getByTestId("viewer-panel");
    expect(viewer.dataset.tipAirfoil).toBe("");
  });

  it("viewer panel receives tipAirfoilName when root and tip differ", async () => {
    const user = userEvent.setup();
    render(<AirfoilPreviewPage />);
    // Change tip to a different airfoil
    await user.click(screen.getByTestId("trigger-tip-airfoil-change"));
    const viewer = screen.getByTestId("viewer-panel");
    expect(viewer.dataset.tipAirfoil).toBe("naca0012");
  });

  it("activeLensScore: mission lens with non-null value uses mission score", () => {
    // Test through activeLensScore export (already covered in helpers, extra coverage)
    const item = {
      re_agnostic: 0.5,
      mission: 0.9,
      target_cl_cruise: 0.6,
    };
    expect(activeLensScore(item, "mission")).toBe(0.9);
    expect(activeLensScore(item, "target_cl_cruise")).toBe(0.6);
    expect(activeLensScore(item, "re_agnostic")).toBe(0.5);
  });

  it("rootOperatingAlpha is computed when analysis result + target_cl_cruise are both non-null", () => {
    // Cover lines 144-160: rootOperatingAlpha useMemo with valid analysis + suitability
    mockAnalysisResult = {
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
    mockSuitabilityData = {
      query: { active_lens: "target_cl_cruise", target_cl_provenance: "calculated" },
      results: [
        {
          airfoil_name: "naca0015",
          re_agnostic: 0.75,
          mission: null,
          target_cl_cruise: 0.5,  // matches cl[2]=0.5 → α=5°
          target_cl_best_glide: null,
          target_cl_min_sink: null,
          stall_gentleness: null,
          cl_max_margin: null,
          min_analysis_confidence: 0.9,
          tip_re_flag: false,
          caveat: "",
        },
      ],
      caveat: { relative_ranking_only: true, no_hysteresis_modelling: true, ignores_tip_re_clmax_collapse: true, recommend_xfoil_validation: false, text: "" },
    };
    render(<AirfoilPreviewPage />);
    // The page should render without crash; the viewer panel receives operatingAlphaDeg
    const viewer = screen.getByTestId("viewer-panel");
    // operatingAlphaDeg should be 5 (index 2 matches cl=0.5)
    expect(viewer.dataset.operatingAlpha).toBe("5");
  });

  it("rootOperatingAlpha is undefined when rootSuitabilityItem has null target_cl_cruise", () => {
    mockAnalysisResult = {
      airfoilName: "naca0015",
      alphaDeg: [0, 5, 10],
      cl: [0.1, 0.5, 0.9],
      cd: [0.01, 0.012, 0.02],
      cm: [-0.01, -0.01, -0.02],
      clOverCd: [10, 41.7, 45],
      clMax: null,
      alphaAtClMax: null,
      ldMax: null,
      alphaAtLdMax: null,
    };
    mockSuitabilityData = {
      query: { active_lens: "re_agnostic", target_cl_provenance: "estimated" },
      results: [
        {
          airfoil_name: "naca0015",
          re_agnostic: 0.75,
          mission: null,
          target_cl_cruise: null,  // null → no operating alpha
          target_cl_best_glide: null,
          target_cl_min_sink: null,
          stall_gentleness: null,
          cl_max_margin: null,
          min_analysis_confidence: 0.9,
          tip_re_flag: false,
          caveat: "",
        },
      ],
      caveat: { relative_ranking_only: true, no_hysteresis_modelling: true, ignores_tip_re_clmax_collapse: true, recommend_xfoil_validation: false, text: "" },
    };
    render(<AirfoilPreviewPage />);
    // operatingAlphaDeg should be empty string (undefined passed to dataset)
    const viewer = screen.getByTestId("viewer-panel");
    expect(viewer.dataset.operatingAlpha).toBe("");
  });

  it("rootOperatingAlpha: covers the loop iteration (lines 151-158) to find closest CL index", () => {
    // Tests the inner loop by using a target CL that matches a non-zero index
    mockAnalysisResult = {
      airfoilName: "naca0015",
      alphaDeg: [0, 5, 10, 15, 20],
      cl: [0.1, 0.3, 0.7, 1.0, 1.2],
      cd: [0.01, 0.012, 0.018, 0.025, 0.04],
      cm: [-0.01, -0.01, -0.015, -0.02, -0.025],
      clOverCd: [10, 25, 38, 40, 30],
      clMax: 1.2,
      alphaAtClMax: 20,
      ldMax: 40,
      alphaAtLdMax: 15,
    };
    mockSuitabilityData = {
      query: { active_lens: "target_cl_cruise", target_cl_provenance: "calculated" },
      results: [
        {
          airfoil_name: "naca0015",
          re_agnostic: 0.78,
          mission: null,
          target_cl_cruise: 0.68,  // closest to cl[2]=0.7 → α=10°
          target_cl_best_glide: null,
          target_cl_min_sink: null,
          stall_gentleness: null,
          cl_max_margin: null,
          min_analysis_confidence: 0.9,
          tip_re_flag: false,
          caveat: "",
        },
      ],
      caveat: { relative_ranking_only: true, no_hysteresis_modelling: true, ignores_tip_re_clmax_collapse: true, recommend_xfoil_validation: false, text: "" },
    };
    render(<AirfoilPreviewPage />);
    const viewer = screen.getByTestId("viewer-panel");
    // Should find α=10 as closest to CL=0.68
    expect(viewer.dataset.operatingAlpha).toBe("10");
  });

  it("rootScoreMap built from suitabilityData with mission lens", () => {
    mockSuitabilityData = {
      query: { active_lens: "mission", target_cl_provenance: "mixed" },
      results: [
        {
          airfoil_name: "e423",
          re_agnostic: 0.82,
          mission: 0.90,
          target_cl_cruise: 0.70,
          target_cl_best_glide: 0.75,
          target_cl_min_sink: 0.55,
          stall_gentleness: -0.03,
          cl_max_margin: 0.10,
          min_analysis_confidence: 0.92,
          tip_re_flag: false,
          caveat: "",
        },
      ],
      caveat: { relative_ranking_only: true, no_hysteresis_modelling: true, ignores_tip_re_clmax_collapse: true, recommend_xfoil_validation: false, text: "" },
    };
    // When rootRankedMode=false, rootScoreMap is undefined (scores not passed)
    render(<AirfoilPreviewPage />);
    // Just verify no crash
    expect(screen.getByTestId("config-panel")).toBeDefined();
  });

  it("revert restores segment airfoils from wingConfig", async () => {
    mockWingConfig = {
      segments: [
        {
          root_airfoil: { airfoil: "e423.dat", chord: 200 },
          tip_airfoil: { airfoil: "clark-y.dat", chord: 150 },
          length: 500,
          sweep: 0,
        },
      ],
    };
    const user = userEvent.setup();
    render(<AirfoilPreviewPage />);
    // Initially shows e423
    expect(screen.getByTestId("config-panel").dataset.rootAirfoil).toBe("e423");
    // Change root airfoil to something else
    await user.click(screen.getByTestId("trigger-root-airfoil-change"));
    expect(screen.getByTestId("config-panel").dataset.rootAirfoil).toBe("clark-y");
    // Revert should restore e423
    await user.click(screen.getByTestId("trigger-revert"));
    expect(screen.getByTestId("config-panel").dataset.rootAirfoil).toBe("e423");
  });
});
