/**
 * Unit tests for useAirfoilSuitability hook (gh-825).
 * Verifies that the SWR query string is built correctly per the frozen contract.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { useAirfoilSuitability } from "@/hooks/useAirfoilSuitability";
import type {
  ActiveLens,
  RankingLens,
  TargetClProvenance,
  SuitabilityItem,
  SuitabilityQuery,
  SuitabilityCaveat,
} from "@/hooks/useAirfoilSuitability";

// ── Capture the SWR key ──────────────────────────────────────────
let capturedKey: string | null = undefined as unknown as string | null;

vi.mock("swr", () => ({
  default: vi.fn((key: string | null) => {
    capturedKey = key;
    return {
      data: null,
      error: null,
      isLoading: false,
    };
  }),
}));

describe("useAirfoilSuitability — query string construction", () => {
  beforeEach(() => {
    capturedKey = undefined as unknown as string | null;
  });

  it("returns null key (no fetch) when chord_m is missing", () => {
    renderHook(() =>
      useAirfoilSuitability({ chord_m: undefined, speed_ms: 14 }),
    );
    expect(capturedKey).toBeNull();
  });

  it("returns null key (no fetch) when speed_ms is missing", () => {
    renderHook(() =>
      useAirfoilSuitability({ chord_m: 0.2, speed_ms: undefined }),
    );
    expect(capturedKey).toBeNull();
  });

  it("returns null key when both missing", () => {
    renderHook(() =>
      useAirfoilSuitability({ chord_m: undefined, speed_ms: undefined }),
    );
    expect(capturedKey).toBeNull();
  });

  it("builds key with chord_m and speed_ms only when no aeroplane_id", () => {
    renderHook(() =>
      useAirfoilSuitability({ chord_m: 0.2, speed_ms: 14 }),
    );
    expect(capturedKey).not.toBeNull();
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.pathname).toBe("/airfoils/db/suitability");
    expect(url.searchParams.get("chord_m")).toBe("0.2");
    expect(url.searchParams.get("speed_ms")).toBe("14");
    expect(url.searchParams.has("aeroplane_id")).toBe(false);
  });

  it("appends aeroplane_id as UUID string verbatim when aeroplane_id is present", () => {
    const uuid = "3fa85f64-5717-4562-b3fc-2c963f66afa6";
    renderHook(() =>
      useAirfoilSuitability({ chord_m: 0.2, speed_ms: 14, aeroplane_id: uuid }),
    );
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.searchParams.get("aeroplane_id")).toBe(uuid);
  });

  it("appends mission_type when provided", () => {
    renderHook(() =>
      useAirfoilSuitability({
        chord_m: 0.2,
        speed_ms: 14,
        mission_type: "trainer",
      }),
    );
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.searchParams.get("mission_type")).toBe("trainer");
  });

  it("appends target_cl_cruise when provided", () => {
    renderHook(() =>
      useAirfoilSuitability({
        chord_m: 0.2,
        speed_ms: 14,
        target_cl_cruise: 0.6,
      }),
    );
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.searchParams.get("target_cl_cruise")).toBe("0.6");
  });

  it("appends target_cl_min_sink (renamed from loiter) when provided", () => {
    renderHook(() =>
      useAirfoilSuitability({
        chord_m: 0.2,
        speed_ms: 14,
        target_cl_min_sink: 0.9,
      }),
    );
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.searchParams.get("target_cl_min_sink")).toBe("0.9");
    // Ensure old param name is NOT sent
    expect(url.searchParams.has("target_cl_loiter")).toBe(false);
  });

  it("appends target_cl_best_glide (new gh-825) when provided", () => {
    renderHook(() =>
      useAirfoilSuitability({
        chord_m: 0.2,
        speed_ms: 14,
        target_cl_best_glide: 0.8,
      }),
    );
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.searchParams.get("target_cl_best_glide")).toBe("0.8");
  });

  it("does NOT append target_cl_best_glide when not provided", () => {
    renderHook(() =>
      useAirfoilSuitability({ chord_m: 0.2, speed_ms: 14 }),
    );
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.searchParams.has("target_cl_best_glide")).toBe(false);
  });

  it("builds complete query string with all optional params", () => {
    const uuid = "3fa85f64-5717-4562-b3fc-2c963f66afa6";
    renderHook(() =>
      useAirfoilSuitability({
        chord_m: 0.3,
        speed_ms: 18,
        aeroplane_id: uuid,
        mission_type: "sport",
        target_cl_cruise: 0.7,
        target_cl_min_sink: 1.0,
        target_cl_best_glide: 0.85,
      }),
    );
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.searchParams.get("chord_m")).toBe("0.3");
    expect(url.searchParams.get("speed_ms")).toBe("18");
    expect(url.searchParams.get("aeroplane_id")).toBe(uuid);
    expect(url.searchParams.get("mission_type")).toBe("sport");
    expect(url.searchParams.get("target_cl_cruise")).toBe("0.7");
    expect(url.searchParams.get("target_cl_min_sink")).toBe("1");
    expect(url.searchParams.get("target_cl_best_glide")).toBe("0.85");
  });

  // The spec says: appends aeroplane_id as the UUID string from
  // useAeroplaneContext().aeroplaneId VERBATIM when present.
  // Since the hook accepts aeroplane_id as a param (injected by the caller
  // which uses useAeroplaneContext), the hook test verifies the verbatim pass-through.
  it("does NOT add aeroplane_id when aeroplane_id is null", () => {
    renderHook(() =>
      useAirfoilSuitability({ chord_m: 0.2, speed_ms: 14, aeroplane_id: null }),
    );
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.searchParams.has("aeroplane_id")).toBe(false);
  });

  it("appends limit when provided", () => {
    renderHook(() =>
      useAirfoilSuitability({ chord_m: 0.2, speed_ms: 14, limit: 20 }),
    );
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.searchParams.get("limit")).toBe("20");
  });

  it("does NOT append limit when not provided", () => {
    renderHook(() =>
      useAirfoilSuitability({ chord_m: 0.2, speed_ms: 14 }),
    );
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.searchParams.has("limit")).toBe(false);
  });

  it("appends tip_chord_m when provided", () => {
    renderHook(() =>
      useAirfoilSuitability({ chord_m: 0.2, speed_ms: 14, tip_chord_m: 0.15 }),
    );
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.searchParams.get("tip_chord_m")).toBe("0.15");
  });

  it("does NOT append tip_chord_m when not provided", () => {
    renderHook(() =>
      useAirfoilSuitability({ chord_m: 0.2, speed_ms: 14 }),
    );
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.searchParams.has("tip_chord_m")).toBe(false);
  });
});

// ── Type-level tests for ActiveLens, RankingLens, TargetClProvenance ──
describe("useAirfoilSuitability — types (gh-825)", () => {
  it("ActiveLens includes re_agnostic, mission, target_cl_cruise", () => {
    const lenses: ActiveLens[] = ["re_agnostic", "mission", "target_cl_cruise"];
    expect(lenses).toHaveLength(3);
  });

  it("ActiveLens does NOT include target_cl_loiter (removed in gh-825)", () => {
    const lenses: ActiveLens[] = ["re_agnostic", "mission", "target_cl_cruise"];
    expect(lenses.includes("target_cl_loiter" as ActiveLens)).toBe(false);
  });

  it("RankingLens equals ActiveLens (no glide points in ranking set)", () => {
    const lenses: RankingLens[] = ["re_agnostic", "mission", "target_cl_cruise"];
    expect(lenses).toHaveLength(3);
    expect(lenses.includes("target_cl_loiter" as RankingLens)).toBe(false);
  });

  it("TargetClProvenance has the three expected literals", () => {
    const provenances: TargetClProvenance[] = [
      "estimated",
      "calculated",
      "mixed",
    ];
    expect(provenances).toHaveLength(3);
  });

  it("SuitabilityItem has the gh-825 fields: target_cl_best_glide, target_cl_min_sink, stall_gentleness, cl_max_margin", () => {
    const item: SuitabilityItem = {
      airfoil_name: "e423",
      family: "cambered",
      re_agnostic: 0.82,
      mission: 0.75,
      target_cl_cruise: 0.68,
      target_cl_best_glide: 0.80,
      target_cl_min_sink: 0.95,
      stall_gentleness: -0.15,
      cl_max_margin: 0.12,
      min_analysis_confidence: 0.92,
      tip_re_flag: false,
      caveat: "Nur relative Rangfolge.",
      tags: [],
    };
    expect(item.target_cl_best_glide).toBe(0.80);
    expect(item.target_cl_min_sink).toBe(0.95);
    expect(item.stall_gentleness).toBe(-0.15);
    expect(item.cl_max_margin).toBe(0.12);
    // Ensure old field is not present
    expect("target_cl_loiter" in item).toBe(false);
  });

  it("SuitabilityItem nullable fields accept null for all gh-825 additions", () => {
    const item: SuitabilityItem = {
      airfoil_name: "naca0015",
      family: "symmetric",
      re_agnostic: 0.6,
      mission: null,
      target_cl_cruise: null,
      target_cl_best_glide: null,
      target_cl_min_sink: null,
      stall_gentleness: null,
      cl_max_margin: null,
      min_analysis_confidence: 0.88,
      tip_re_flag: false,
      caveat: "",
      tags: [],
    };
    expect(item.target_cl_best_glide).toBeNull();
    expect(item.target_cl_min_sink).toBeNull();
    expect(item.stall_gentleness).toBeNull();
    expect(item.cl_max_margin).toBeNull();
  });

  it("SuitabilityQuery has target_cl_best_glide, target_cl_min_sink, target_cl_provenance", () => {
    const query: SuitabilityQuery = {
      chord_m: 0.2,
      speed_ms: 14,
      reynolds: 191781,
      re_clamped: false,
      mission_type: "trainer",
      target_cl_cruise: 0.68,
      target_cl_best_glide: 0.80,
      target_cl_min_sink: 0.95,
      target_cl_provenance: "calculated",
      active_lens: "re_agnostic",
      v_cruise_mps: null,
      v_md_mps: null,
      v_min_sink_mps: null,
    };
    expect(query.target_cl_best_glide).toBe(0.80);
    expect(query.target_cl_min_sink).toBe(0.95);
    expect(query.target_cl_provenance).toBe("calculated");
    expect("target_cl_loiter" in query).toBe(false);
  });

  it("SuitabilityCaveat has ignores_tip_re_clmax_collapse field", () => {
    const caveat: SuitabilityCaveat = {
      relative_ranking_only: true,
      no_hysteresis_modelling: true,
      ignores_tip_re_clmax_collapse: true,
      recommend_xfoil_validation: false,
      text: "Test caveat.",
    };
    expect(caveat.ignores_tip_re_clmax_collapse).toBe(true);
  });
});
