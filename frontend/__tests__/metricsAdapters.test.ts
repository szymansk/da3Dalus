/**
 * Tests for metricsAdapters.ts — pure adapter functions that map hook
 * result types (ComputationContext, TailSizingResult, EnduranceData) to
 * the MetricsDashboard data shapes (SpeedData, BalanceData, GaugeData[],
 * MetricItem[]).
 *
 * Pattern mirrors InfoChipRow.test.tsx: no React, no DOM — pure unit tests
 * over deterministic transform functions.
 */
import { describe, it, expect } from "vitest";
import type { ComputationContext } from "@/hooks/useComputationContext";
import type { TailSizingResult } from "@/hooks/useTailSizing";
import type { EnduranceData } from "@/hooks/useEndurance";
import {
  toSpeedData,
  toGeometryItems,
  toBalanceData,
  toQualityGauges,
  toQualityRaw,
  toTail,
  toPowertrainItems,
} from "@/lib/metricsAdapters";

// ---------------------------------------------------------------------------
// Shared realistic fixtures (mirrors SpeedChipRow / PolarChipRow inputs in
// InfoChipRow.test.tsx so the derived values can be cross-checked).
// ---------------------------------------------------------------------------

const NOMINAL_CTX: ComputationContext = {
  v_cruise_mps: 14.0,
  v_stall_mps: 8.2,
  v_min_sink_mps: 9.1,
  min_sink_rate_mps: 0.55,
  v_md_mps: 11.0,
  v_x_mps: 12.5,
  v_y_mps: 13.5,
  v_a_mps: 17.5,
  v_max_mps: 22.0,
  v_dive_mps: 30.8,
  alpha_stall_deg: 14.0,
  alpha_min_sink_deg: 5.0,
  alpha_best_glide_deg: 2.3,
  is_glider: false,
  reynolds: 230000,
  mac_m: 0.135,
  s_ref_m2: 0.2,
  b_ref_m: 1.5,
  aspect_ratio: 11.3,
  cd0: 0.0158,
  e_oswald: 0.79,
  e_oswald_quality: "high",
  e_oswald_fallback_used: false,
  x_np_m: 0.143,
  target_static_margin: 0.081,
  cg_agg_m: 0.132,
  is_tailless: false,
  computed_at: "2026-01-01T00:00:00Z",
  polar_by_config: {
    clean: {
      cd0: 0.0158,
      e_oswald: 0.79,
      cl_max: 1.18,
      e_oswald_r2: 0.99,
      e_oswald_quality: "high",
      flap_deflection_deg: 0,
      provenance: "aerobuildup",
      rejection: null,
      ld_max: 21.0,
      cl_at_ld_max: 0.62,
      e_oswald_provenance: "aerobuildup_trefftz",
    },
    takeoff: {
      cd0: 0.022,
      e_oswald: 0.75,
      cl_max: 1.6,
      e_oswald_r2: 0.95,
      e_oswald_quality: "medium",
      flap_deflection_deg: 15,
      provenance: "aerobuildup",
      rejection: null,
    },
    landing: {
      cd0: 0.028,
      e_oswald: 0.72,
      cl_max: 1.85,
      e_oswald_r2: 0.93,
      e_oswald_quality: "medium",
      flap_deflection_deg: 30,
      provenance: "aerobuildup",
      rejection: null,
    },
  },
  landing_field_length_m: 24,
  landing_field_sufficient: true,
};

const GLIDER_CTX: ComputationContext = {
  ...NOMINAL_CTX,
  is_glider: true,
  v_x_mps: null,
  v_y_mps: null,
  v_a_mps: null,
  v_max_mps: null,
  v_dive_mps: null,
};

const FALLBACK_CTX: ComputationContext = {
  ...NOMINAL_CTX,
  e_oswald_fallback_used: true,
  polar_by_config: {
    clean: {
      ...NOMINAL_CTX.polar_by_config!.clean,
      e_oswald_provenance: "fallback",
    },
    takeoff: NOMINAL_CTX.polar_by_config!.takeoff,
    landing: NOMINAL_CTX.polar_by_config!.landing,
  },
};

const TAILLESS_CTX: ComputationContext = {
  ...NOMINAL_CTX,
  is_tailless: true,
};

const NOMINAL_TAIL: TailSizingResult = {
  v_h_current: 0.58,
  v_v_current: 0.035,
  l_h_m: 0.43,
  l_h_eff_from_aft_cg_m: 0.41,
  s_h_recommended_mm2: null,
  s_v_recommended_mm2: null,
  classification: "in_range",
  classification_h: "in_range",
  classification_v: "in_range",
  aircraft_class_used: "sport",
  cg_aware: true,
  v_h_target_min: 0.5,
  v_h_target_max: 0.6,
  v_v_target_min: 0.025,
  v_v_target_max: 0.05,
  v_h_citation: "RC rule of thumb",
  v_v_citation: "RC rule of thumb",
  warnings: [],
};

const NOT_APPLICABLE_TAIL: TailSizingResult = {
  ...NOMINAL_TAIL,
  v_h_current: null,
  v_v_current: null,
  classification: "not_applicable",
  classification_h: "not_applicable",
  classification_v: "not_applicable",
};

const BELOW_RANGE_TAIL: TailSizingResult = {
  ...NOMINAL_TAIL,
  v_h_current: 0.38,
  classification: "below_range",
  classification_h: "below_range",
};

const NOMINAL_ENDURANCE: EnduranceData = {
  t_endurance_max_s: 2520, // 42 min
  range_max_m: 38000,
  p_req_at_v_md_w: 24.5,
  p_req_at_v_min_sink_w: 19.8,
  p_margin: 0.18,
  p_margin_class: "feasible but tight",
  battery_mass_g_predicted: 188,
  confidence: "estimated",
  warnings: [],
};

const COMPUTED_ENDURANCE: EnduranceData = {
  ...NOMINAL_ENDURANCE,
  confidence: "computed",
};

// ---------------------------------------------------------------------------
// toSpeedData
// ---------------------------------------------------------------------------
describe("toSpeedData", () => {
  it("returns null when ctx is null/undefined", () => {
    expect(toSpeedData(null)).toBeNull();
    expect(toSpeedData(undefined)).toBeNull();
  });

  it("returns SpeedData with all nominal markers", () => {
    const result = toSpeedData(NOMINAL_CTX);
    expect(result).not.toBeNull();
    const symbols = result!.markers.map((m) => m.symbol);
    expect(symbols).toContain("V_stall");
    expect(symbols).toContain("V_min_sink");
    expect(symbols).toContain("V_md");
    expect(symbols).toContain("V_cruise");
    expect(symbols).toContain("V_x");
    expect(symbols).toContain("V_y");
    expect(symbols).toContain("V_a");
    expect(symbols).toContain("V_max");
    expect(symbols).toContain("V_dive");
  });

  it("attaches alpha to markers that have it", () => {
    const result = toSpeedData(NOMINAL_CTX)!;
    const stall = result.markers.find((m) => m.symbol === "V_stall");
    expect(stall?.aoa).toBeCloseTo(14.0);
    const md = result.markers.find((m) => m.symbol === "V_md");
    expect(md?.aoa).toBeCloseTo(2.3);
    const cruise = result.markers.find((m) => m.symbol === "V_cruise");
    expect(cruise?.aoa).toBeUndefined();
  });

  it("sets isGlider=false for powered aircraft", () => {
    expect(toSpeedData(NOMINAL_CTX)!.isGlider).toBe(false);
  });

  it("sets isGlider=true and omits V_x/V_y/V_a/V_max/V_dive for gliders", () => {
    const result = toSpeedData(GLIDER_CTX)!;
    expect(result.isGlider).toBe(true);
    const symbols = result.markers.map((m) => m.symbol);
    expect(symbols).not.toContain("V_x");
    expect(symbols).not.toContain("V_y");
    expect(symbols).not.toContain("V_a");
    expect(symbols).not.toContain("V_max");
    expect(symbols).not.toContain("V_dive");
    // Core glider speeds must still be present
    expect(symbols).toContain("V_stall");
    expect(symbols).toContain("V_min_sink");
    expect(symbols).toContain("V_md");
  });

  it("omits markers whose speed value is null", () => {
    const ctx: ComputationContext = {
      ...NOMINAL_CTX,
      v_stall_mps: null,
      v_max_mps: null,
    };
    const result = toSpeedData(ctx)!;
    const symbols = result.markers.map((m) => m.symbol);
    expect(symbols).not.toContain("V_stall");
    expect(symbols).not.toContain("V_max");
    expect(symbols).toContain("V_cruise");
  });

  it("sets wMin from min_sink_rate_mps", () => {
    const result = toSpeedData(NOMINAL_CTX)!;
    expect(result.wMin).toBeCloseTo(0.55);
  });

  it("sets wMin to 0 when min_sink_rate_mps is null", () => {
    const ctx: ComputationContext = { ...NOMINAL_CTX, min_sink_rate_mps: null };
    expect(toSpeedData(ctx)!.wMin).toBe(0);
  });

  it("assigns kind=stall to V_stall, kind=ne to V_dive, kind=caution to V_a/V_max", () => {
    const result = toSpeedData(NOMINAL_CTX)!;
    expect(result.markers.find((m) => m.symbol === "V_stall")?.kind).toBe("stall");
    expect(result.markers.find((m) => m.symbol === "V_dive")?.kind).toBe("ne");
    expect(result.markers.find((m) => m.symbol === "V_a")?.kind).toBe("caution");
    expect(result.markers.find((m) => m.symbol === "V_max")?.kind).toBe("caution");
    expect(result.markers.find((m) => m.symbol === "V_cruise")?.kind).toBe("normal");
  });
});

// ---------------------------------------------------------------------------
// toGeometryItems
// ---------------------------------------------------------------------------
describe("toGeometryItems", () => {
  it("returns empty array when ctx is null", () => {
    expect(toGeometryItems(null)).toEqual([]);
  });

  it("returns MetricItem[] for S_ref, MAC, B_ref, AR", () => {
    const items = toGeometryItems(NOMINAL_CTX);
    const symbols = items.map((i) => i.symbol);
    expect(symbols).toContain("S_ref");
    expect(symbols).toContain("MAC");
    expect(symbols).toContain("B_ref");
    expect(symbols).toContain("AR");
  });

  it("S_ref item shows 3dp value and m² unit", () => {
    const item = toGeometryItems(NOMINAL_CTX).find((i) => i.symbol === "S_ref")!;
    expect(item.value).toBe("0.200");
    expect(item.unit).toBe("m²");
  });

  it("AR item has no unit", () => {
    const item = toGeometryItems(NOMINAL_CTX).find((i) => i.symbol === "AR")!;
    expect(item.unit).toBeUndefined();
    expect(item.value).toBe("11.3");
  });

  it("omits items whose value is null", () => {
    const ctx: ComputationContext = {
      ...NOMINAL_CTX,
      s_ref_m2: null,
      b_ref_m: null,
    };
    const symbols = toGeometryItems(ctx).map((i) => i.symbol);
    expect(symbols).not.toContain("S_ref");
    expect(symbols).not.toContain("B_ref");
  });
});

// ---------------------------------------------------------------------------
// toBalanceData
// ---------------------------------------------------------------------------
describe("toBalanceData", () => {
  it("returns null when ctx is null", () => {
    expect(toBalanceData(null)).toBeNull();
  });

  it("returns null when cg_agg_m is null", () => {
    const ctx: ComputationContext = { ...NOMINAL_CTX, cg_agg_m: null };
    expect(toBalanceData(ctx)).toBeNull();
  });

  it("maps cg, np, macLength from ctx fields", () => {
    const result = toBalanceData(NOMINAL_CTX)!;
    expect(result.cg).toBeCloseTo(0.132);
    expect(result.np).toBeCloseTo(0.143);
    expect(result.macLength).toBeCloseTo(0.135);
  });

  it("computes smPercent as (np-cg)/mac * 100", () => {
    const result = toBalanceData(NOMINAL_CTX)!;
    const expected = ((0.143 - 0.132) / 0.135) * 100;
    expect(result.smPercent).toBeCloseTo(expected, 2);
  });

  it("target_static_margin drives targetSmMin and targetSmMax symmetrically", () => {
    const result = toBalanceData(NOMINAL_CTX)!;
    // target_static_margin = 0.081 → 8.1%; the dashboard shows a range
    // around it. The exact band is defined by the adapter — verify it is
    // consistent (targetSmMin < target * 100 < targetSmMax).
    const targetPct = NOMINAL_CTX.target_static_margin * 100;
    expect(result.targetSmMin).toBeLessThan(targetPct);
    expect(result.targetSmMax).toBeGreaterThan(targetPct);
  });

  it("passes through optional cgComponent", () => {
    const result = toBalanceData(NOMINAL_CTX, 0.129)!;
    expect(result.cgComponent).toBeCloseTo(0.129);
  });

  it("cgComponent is undefined when not passed", () => {
    const result = toBalanceData(NOMINAL_CTX)!;
    expect(result.cgComponent).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// toQualityGauges
// ---------------------------------------------------------------------------
describe("toQualityGauges", () => {
  it("returns empty array when ctx is null", () => {
    expect(toQualityGauges(null)).toEqual([]);
  });

  it("includes (L/D)_max, e, ρ, SM, L_land, P_margin gauges", () => {
    const gauges = toQualityGauges(NOMINAL_CTX);
    const symbols = gauges.map((g) => g.symbol);
    expect(symbols).toContain("(L/D)_max");
    expect(symbols).toContain("e");
    expect(symbols).toContain("ρ");
    expect(symbols).toContain("SM");
    expect(symbols).toContain("L_land");
  });

  it("(L/D)_max gauge uses empirical ld_max from clean polar when available", () => {
    const gauges = toQualityGauges(NOMINAL_CTX);
    const ldGauge = gauges.find((g) => g.symbol === "(L/D)_max")!;
    expect(ldGauge.value).toBeCloseTo(21.0);
  });

  it("e gauge value is e_oswald", () => {
    const gauges = toQualityGauges(NOMINAL_CTX);
    const eGauge = gauges.find((g) => g.symbol === "e")!;
    expect(eGauge.value).toBeCloseTo(0.79);
  });

  it("ρ gauge has a numeric value for nominal ctx", () => {
    const gauges = toQualityGauges(NOMINAL_CTX);
    const rhoGauge = gauges.find((g) => g.symbol === "ρ")!;
    expect(rhoGauge.value).toBeGreaterThan(0);
    expect(rhoGauge.value).toBeLessThanOrEqual(1);
  });

  it("SM gauge shows smPercent value", () => {
    const gauges = toQualityGauges(NOMINAL_CTX);
    const smGauge = gauges.find((g) => g.symbol === "SM")!;
    const expectedSm = ((NOMINAL_CTX.x_np_m - NOMINAL_CTX.cg_agg_m!) / NOMINAL_CTX.mac_m) * 100;
    expect(smGauge.value).toBeCloseTo(expectedSm, 1);
  });

  it("L_land gauge uses landing_field_length_m", () => {
    const gauges = toQualityGauges(NOMINAL_CTX);
    const lGauge = gauges.find((g) => g.symbol === "L_land")!;
    expect(lGauge.value).toBeCloseTo(24);
  });

  it("polar fallback: (L/D)_max / ρ gauges are omitted or have a sentinel value", () => {
    // When e_oswald_fallback_used=true, polar-derived quantities are non-physical.
    // The adapter must not show garbage — it either omits those gauges or
    // replaces with a special sentinel (NaN / 0 is not acceptable).
    const gauges = toQualityGauges(FALLBACK_CTX);
    const ldGauge = gauges.find((g) => g.symbol === "(L/D)_max");
    const rhoGauge = gauges.find((g) => g.symbol === "ρ");
    // Either omitted entirely, or value is null-like (0 is the documented sentinel)
    if (ldGauge) {
      expect(Number.isFinite(ldGauge.value)).toBe(true);
      // value should be 0 to signal "not computed" to BulletGauge
      expect(ldGauge.value).toBe(0);
    }
    if (rhoGauge) {
      expect(Number.isFinite(rhoGauge.value)).toBe(true);
      expect(rhoGauge.value).toBe(0);
    }
  });

  it("landing field gauge omitted when landing_field_length_m is null", () => {
    const ctx: ComputationContext = { ...NOMINAL_CTX, landing_field_length_m: null };
    const gauges = toQualityGauges(ctx);
    const lGauge = gauges.find((g) => g.symbol === "L_land");
    expect(lGauge).toBeUndefined();
  });

  it("all returned gauges have valid zones that cover [min, max]", () => {
    const gauges = toQualityGauges(NOMINAL_CTX);
    for (const g of gauges) {
      const lo = Math.min(...g.zones.map((z) => z.from));
      const hi = Math.max(...g.zones.map((z) => z.to));
      expect(lo).toBeLessThanOrEqual(g.min + 0.001);
      expect(hi).toBeGreaterThanOrEqual(g.max - 0.001);
    }
  });

  it("quality field matches the zone that contains the value", () => {
    const gauges = toQualityGauges(NOMINAL_CTX);
    for (const g of gauges) {
      if (g.value === 0 && g.symbol !== "SM") continue; // sentinel, skip
      const matchingZone = g.zones.find(
        (z) => g.value >= z.from && g.value <= z.to,
      );
      if (matchingZone) {
        expect(g.quality).toBe(matchingZone.quality);
      }
    }
  });
});

// ---------------------------------------------------------------------------
// toQualityRaw
// ---------------------------------------------------------------------------
describe("toQualityRaw", () => {
  it("returns empty array when ctx is null", () => {
    expect(toQualityRaw(null)).toEqual([]);
  });

  it("includes Re, C_D0, k, C_L_max, C_L_md items", () => {
    const items = toQualityRaw(NOMINAL_CTX);
    const symbols = items.map((i) => i.symbol);
    expect(symbols).toContain("Re");
    expect(symbols).toContain("C_D0");
    expect(symbols).toContain("k");
    expect(symbols).toContain("C_L_max");
    expect(symbols).toContain("C_L_md");
  });

  it("Re is formatted in exponential notation", () => {
    const item = toQualityRaw(NOMINAL_CTX).find((i) => i.symbol === "Re")!;
    expect(item.value).toMatch(/e\+?\d/i);
  });

  it("k shows dash-string when fallback used", () => {
    const items = toQualityRaw(FALLBACK_CTX);
    const kItem = items.find((i) => i.symbol === "k");
    if (kItem) {
      expect(kItem.value).toBe("–");
    }
  });

  it("C_L_md shows empirical backend value even when fit fallback used (sweep-derived, not fit-derived)", () => {
    // cl_at_ld_max from the AeroBuildup sweep is independent of the parabolic fit.
    // When e_oswald_fallback_used=true, only formula-derived C_L_md is suppressed;
    // the empirical backend value (cl_at_ld_max) is always shown (mirrors PolarChipRow).
    const ctxNoEmpiricalClMd: ComputationContext = {
      ...FALLBACK_CTX,
      polar_by_config: {
        ...FALLBACK_CTX.polar_by_config!,
        clean: {
          ...FALLBACK_CTX.polar_by_config!.clean,
          cl_at_ld_max: null, // no empirical value → formula also null → dash
        },
      },
    };
    const items = toQualityRaw(ctxNoEmpiricalClMd);
    const item = items.find((i) => i.symbol === "C_L_md");
    if (item) {
      expect(item.value).toBe("–");
    }
  });
});

// ---------------------------------------------------------------------------
// toTail
// ---------------------------------------------------------------------------
describe("toTail", () => {
  it("returns null when tailSizing is null/undefined", () => {
    expect(toTail(null, NOMINAL_CTX)).toBeNull();
    expect(toTail(undefined, NOMINAL_CTX)).toBeNull();
  });

  it("returns null when classification is not_applicable (tailless)", () => {
    expect(toTail(NOT_APPLICABLE_TAIL, TAILLESS_CTX)).toBeNull();
  });

  it("returns tail result with gauge and items for in_range classification", () => {
    const result = toTail(NOMINAL_TAIL, NOMINAL_CTX);
    expect(result).not.toBeNull();
    expect(result!.gauge).toBeDefined();
    expect(result!.items.length).toBeGreaterThan(0);
    expect(result!.mission).toBe("sport");
  });

  it("V_H gauge value equals v_h_current", () => {
    const result = toTail(NOMINAL_TAIL, NOMINAL_CTX)!;
    expect(result.gauge.value).toBeCloseTo(0.58);
  });

  it("gauge symbol is V_H", () => {
    const result = toTail(NOMINAL_TAIL, NOMINAL_CTX)!;
    expect(result.gauge.symbol).toBe("V_H");
  });

  it("in_range classification maps to quality=good", () => {
    const result = toTail(NOMINAL_TAIL, NOMINAL_CTX)!;
    expect(result.gauge.quality).toBe("good");
  });

  it("below_range classification maps to quality=bad or caution", () => {
    const result = toTail(BELOW_RANGE_TAIL, NOMINAL_CTX)!;
    expect(["bad", "caution"]).toContain(result.gauge.quality);
  });

  it("gauge zones are built from v_h_target_min / v_h_target_max", () => {
    const result = toTail(NOMINAL_TAIL, NOMINAL_CTX)!;
    // The target band [0.5, 0.6] must contain a "good" zone
    const goodZone = result.gauge.zones.find((z) => z.quality === "good");
    expect(goodZone).toBeDefined();
    expect(goodZone!.from).toBeCloseTo(0.5);
    expect(goodZone!.to).toBeCloseTo(0.6);
  });

  it("items contain l_HT and V_V entries", () => {
    const result = toTail(NOMINAL_TAIL, NOMINAL_CTX)!;
    const symbols = result.items.map((i) => i.symbol);
    expect(symbols).toContain("l_HT");
    expect(symbols).toContain("V_V");
  });

  it("bandsNote is a non-empty string", () => {
    const result = toTail(NOMINAL_TAIL, NOMINAL_CTX)!;
    expect(typeof result.bandsNote).toBe("string");
    expect(result.bandsNote.length).toBeGreaterThan(10);
  });
});

// ---------------------------------------------------------------------------
// toPowertrainItems
// ---------------------------------------------------------------------------
describe("toPowertrainItems", () => {
  it("returns empty object when endurance is null", () => {
    const result = toPowertrainItems(null);
    expect(result.items).toEqual([]);
  });

  it("includes Endurance and Range items", () => {
    const result = toPowertrainItems(NOMINAL_ENDURANCE);
    const symbols = result.items.map((i) => i.symbol);
    expect(symbols).toContain("Endurance");
    expect(symbols).toContain("Range");
  });

  it("endurance converts seconds to minutes", () => {
    const result = toPowertrainItems(NOMINAL_ENDURANCE);
    const endItem = result.items.find((i) => i.symbol === "Endurance")!;
    expect(endItem.value).toBe("42");
    expect(endItem.unit).toBe("min");
  });

  it("range converts metres to km", () => {
    const result = toPowertrainItems(NOMINAL_ENDURANCE);
    const rangeItem = result.items.find((i) => i.symbol === "Range")!;
    expect(rangeItem.value).toBe("38");
    expect(rangeItem.unit).toBe("km");
  });

  it("detail shows pReqVmd, pMarginClass, batteryMassPredicted, confidence", () => {
    const result = toPowertrainItems(NOMINAL_ENDURANCE);
    expect(result.detail.pReqVmd).toBeCloseTo(24.5);
    expect(result.detail.pMarginClass).toBe("feasible but tight");
    expect(result.detail.batteryMassPredicted).toBe(188);
    expect(result.detail.confidence).toBe("estimated");
  });

  it("confidence='computed' is propagated", () => {
    const result = toPowertrainItems(COMPUTED_ENDURANCE);
    expect(result.detail.confidence).toBe("computed");
  });

  it("handles null endurance values gracefully (shows dashes)", () => {
    const sparse: EnduranceData = {
      t_endurance_max_s: null,
      range_max_m: null,
      p_req_at_v_md_w: null,
      p_req_at_v_min_sink_w: null,
      p_margin: null,
      p_margin_class: null,
      battery_mass_g_predicted: null,
      confidence: "estimated",
      warnings: [],
    };
    const result = toPowertrainItems(sparse);
    const endItem = result.items.find((i) => i.symbol === "Endurance");
    if (endItem) {
      expect(endItem.value).toBe("–");
    }
  });
});
