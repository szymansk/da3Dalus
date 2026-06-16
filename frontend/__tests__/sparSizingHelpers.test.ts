// frontend/__tests__/sparSizingHelpers.test.ts
// gh-1008: Unit tests for pure spar-sizing helper functions.
// No DOM, no network — pure TypeScript logic.

import { describe, it, expect } from "vitest";

import {
  filterStructuralMaterials,
  getSigmaAllow,
  getDensity,
  solvedDimLabel,
  feasibilityLabel,
  allStationsFeasible,
  buildRootHeadline,
  buildMassSummary,
  buildSizingAnnotationText,
} from "@/lib/sparSizingHelpers";
import type { Component } from "@/hooks/useComponents";
import type { SparSizingResult, SparSizingStation } from "@/hooks/useSparSizing";

// ---- Fixtures --------------------------------------------------------------

function makeMaterial(
  id: number,
  name: string,
  specs: Record<string, unknown> = {},
): Component {
  return {
    id,
    name,
    component_type: "material",
    manufacturer: null,
    description: null,
    mass_g: null,
    bbox_x_mm: null,
    bbox_y_mm: null,
    bbox_z_mm: null,
    model_ref: null,
    specs,
    created_at: "2025-01-01T00:00:00",
    updated_at: "2025-01-01T00:00:00",
  };
}

function makeStation(overrides: Partial<SparSizingStation> = {}): SparSizingStation {
  return {
    y_m: 0.0,
    chord_m: 0.4,
    profile_thickness_mm: 48.0,
    outer_mm: 38.4,
    tc_ratio: 0.12,
    tc_fallback: false,
    m_design_Nm: 4500.0,
    required_W_mm3: 9000.0,
    solved_mm: 2.5,
    feasible: true,
    infeasibility_reason: null,
    cross_section_area_mm2: 120.0,
    ...overrides,
  };
}

function makeResult(overrides: Partial<SparSizingResult> = {}): SparSizingResult {
  const st = makeStation();
  return {
    surface_name: "main_wing",
    shape: "tube",
    material_name: "Carbon Fiber (structural)",
    sigma_allow_mpa: 500.0,
    density_kg_m3: 1600.0,
    g_limit: 4.0,
    g_limit_fallback: false,
    safety_factor_j: 1.5,
    packing_factor: 0.8,
    stations: [st],
    root_station: st,
    spar_mass_half_kg: 0.045,
    spar_mass_full_kg: 0.09,
    tc_fallback_warning: null,
    ...overrides,
  };
}

// ---- filterStructuralMaterials ---------------------------------------------

describe("filterStructuralMaterials", () => {
  it("returns only material components with allowable_bending_stress_mpa > 0", () => {
    const components: Component[] = [
      makeMaterial(1, "Carbon Fiber", {
        density_kg_m3: 1600,
        allowable_bending_stress_mpa: 500,
      }),
      makeMaterial(2, "PLA (3D print)", { density_kg_m3: 1240 }), // no σ_allow
      makeMaterial(3, "Pine", {
        density_kg_m3: 500,
        allowable_bending_stress_mpa: 39,
      }),
      makeMaterial(4, "Servo", { torque_kg_cm: 5 }), // wrong type in specs (but type filter should catch it)
    ];
    // Override component_type for the servo
    components[3].component_type = "servo";

    const result = filterStructuralMaterials(components);
    expect(result.map((c) => c.id)).toEqual([1, 3]);
  });

  it("excludes materials with allowable_bending_stress_mpa = 0", () => {
    const comps = [
      makeMaterial(1, "Bad", { density_kg_m3: 100, allowable_bending_stress_mpa: 0 }),
    ];
    expect(filterStructuralMaterials(comps)).toHaveLength(0);
  });

  it("returns empty array when no structural materials present", () => {
    expect(filterStructuralMaterials([])).toHaveLength(0);
    expect(
      filterStructuralMaterials([makeMaterial(1, "PLA", { density_kg_m3: 1240 })]),
    ).toHaveLength(0);
  });
});

// ---- getSigmaAllow ---------------------------------------------------------

describe("getSigmaAllow", () => {
  it("returns the numeric value", () => {
    const mat = makeMaterial(1, "CF", { allowable_bending_stress_mpa: 500 });
    expect(getSigmaAllow(mat)).toBe(500);
  });

  it("returns null when field is missing", () => {
    const mat = makeMaterial(1, "PLA", { density_kg_m3: 1240 });
    expect(getSigmaAllow(mat)).toBeNull();
  });

  it("returns null when field is a string", () => {
    const mat = makeMaterial(1, "Bad", { allowable_bending_stress_mpa: "500" });
    expect(getSigmaAllow(mat)).toBeNull();
  });
});

// ---- getDensity ------------------------------------------------------------

describe("getDensity", () => {
  it("returns numeric density", () => {
    const mat = makeMaterial(1, "CF", { density_kg_m3: 1600 });
    expect(getDensity(mat)).toBe(1600);
  });

  it("returns null when missing", () => {
    expect(getDensity(makeMaterial(1, "x", {}))).toBeNull();
  });
});

// ---- solvedDimLabel --------------------------------------------------------

describe("solvedDimLabel", () => {
  it.each([
    ["tube", "Wall t (mm)"],
    ["rod", "d (mm)"],
    ["rectangular", "Width b (mm)"],
    ["capped", "Gurt t (mm)"],
  ] as const)("shape=%s → %s", (shape, expected) => {
    expect(solvedDimLabel(shape)).toBe(expected);
  });
});

// ---- feasibilityLabel ------------------------------------------------------

describe("feasibilityLabel", () => {
  it("returns 'OK' when feasible", () => {
    expect(feasibilityLabel(makeStation({ feasible: true }))).toBe("OK");
  });

  it("returns infeasibility_reason when infeasible", () => {
    const st = makeStation({ feasible: false, infeasibility_reason: "rod too big — d=42 mm" });
    expect(feasibilityLabel(st)).toBe("rod too big — d=42 mm");
  });

  it("returns 'infeasible' fallback when no reason provided", () => {
    const st = makeStation({ feasible: false, infeasibility_reason: null });
    expect(feasibilityLabel(st)).toBe("infeasible");
  });
});

// ---- allStationsFeasible ---------------------------------------------------

describe("allStationsFeasible", () => {
  it("returns true when all stations feasible", () => {
    const result = makeResult({ stations: [makeStation(), makeStation()] });
    expect(allStationsFeasible(result)).toBe(true);
  });

  it("returns false when any station infeasible", () => {
    const result = makeResult({
      stations: [makeStation(), makeStation({ feasible: false })],
    });
    expect(allStationsFeasible(result)).toBe(false);
  });
});

// ---- buildRootHeadline -----------------------------------------------------

describe("buildRootHeadline", () => {
  it("contains M_design, required W, outer, and solved dim", () => {
    const result = makeResult();
    const text = buildRootHeadline(result);
    expect(text).toContain("M_design");
    expect(text).toContain("4500");
    expect(text).toContain("Required W");
    expect(text).toContain("9000");
    expect(text).toContain("Outer");
    expect(text).toContain("38.4");
    expect(text).toContain("Wall t (mm)"); // shape=tube
    expect(text).toContain("2.50"); // solved_mm
  });

  it("shows — for null solved_mm", () => {
    const result = makeResult({
      root_station: makeStation({ solved_mm: null, feasible: false }),
    });
    expect(buildRootHeadline(result)).toContain("—");
  });
});

// ---- buildMassSummary ------------------------------------------------------

describe("buildMassSummary", () => {
  it("contains half and full mass", () => {
    const result = makeResult({ spar_mass_half_kg: 0.045, spar_mass_full_kg: 0.09 });
    const text = buildMassSummary(result);
    expect(text).toContain("0.045");
    expect(text).toContain("0.090");
    expect(text.toLowerCase()).toContain("half");
    expect(text.toLowerCase()).toContain("full");
  });
});

// ---- buildSizingAnnotationText --------------------------------------------

describe("buildSizingAnnotationText", () => {
  it("contains material, shape, sigma, n, j, packing", () => {
    const result = makeResult();
    const text = buildSizingAnnotationText(result);
    expect(text).toContain("Carbon Fiber");
    expect(text).toContain("tube");
    expect(text).toContain("500");
    expect(text).toContain("1600");
    expect(text).toContain("4.0"); // g_limit (toFixed(1) → "4.0")
    expect(text).toContain("1.5"); // j
    expect(text).toContain("0.8"); // packing
  });

  it("marks fallback g_limit with (default)", () => {
    const result = makeResult({ g_limit: 3.0, g_limit_fallback: true });
    expect(buildSizingAnnotationText(result)).toContain("(default)");
  });
});
