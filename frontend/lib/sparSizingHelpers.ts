// frontend/lib/sparSizingHelpers.ts
// gh-1008: Pure helper functions for the Spar Sizing panel.
// All functions are side-effect-free and testable without a DOM.

import type { SparShape, SparSizingResult, SparSizingStation } from "@/hooks/useSparSizing";
import type { Component } from "@/hooks/useComponents";

// ---- Material filtering ----------------------------------------------------

/**
 * Filter material components to those with allowable_bending_stress_mpa set.
 * A material is eligible for spar sizing when its specs contain a positive
 * allowable_bending_stress_mpa value.
 */
export function filterStructuralMaterials(components: Component[]): Component[] {
  return components.filter((c) => {
    if (c.component_type !== "material") return false;
    const stress = c.specs["allowable_bending_stress_mpa"];
    return typeof stress === "number" && stress > 0;
  });
}

/**
 * Extract σ_allow (MPa) from a material component's specs.
 * Returns null when the material has no allowable_bending_stress_mpa.
 */
export function getSigmaAllow(material: Component): number | null {
  const v = material.specs["allowable_bending_stress_mpa"];
  return typeof v === "number" ? v : null;
}

/**
 * Extract density (kg/m³) from a material component's specs.
 * Returns null when the field is missing.
 */
export function getDensity(material: Component): number | null {
  const v = material.specs["density_kg_m3"];
  return typeof v === "number" ? v : null;
}

// ---- Shape-adaptive column label -------------------------------------------

/**
 * Return the label for the "solved dimension" column, which is shape-dependent.
 *
 * - tube:        "Wall t (mm)"
 * - rod:         "d (mm)"
 * - rectangular: "Width b (mm)"
 * - capped:      "Gurt t (mm)"
 */
export function solvedDimLabel(shape: SparShape): string {
  switch (shape) {
    case "tube":
      return "Wall t (mm)";
    case "rod":
      return "d (mm)";
    case "rectangular":
      return "Width b (mm)";
    case "capped":
      return "Gurt t (mm)";
  }
}

// ---- Feasibility summary ---------------------------------------------------

/**
 * Return a summary string for a station's feasibility status.
 * Used as table cell text and for accessibility.
 */
export function feasibilityLabel(station: SparSizingStation): string {
  if (station.feasible) return "OK";
  return station.infeasibility_reason ?? "infeasible";
}

/**
 * True when all stations in a result are feasible.
 */
export function allStationsFeasible(result: SparSizingResult): boolean {
  return result.stations.every((s) => s.feasible);
}

// ---- Root headline text ----------------------------------------------------

/**
 * Build the root-station headline text shown above the per-station table.
 * Echoes compute inputs inside the text (project Plotly-metadata convention).
 */
export function buildRootHeadline(result: SparSizingResult): string {
  const root = result.root_station;
  const mStr = root.m_design_Nm.toFixed(0);
  const wStr = root.required_W_mm3.toFixed(0);
  const outerStr = root.outer_mm.toFixed(1);
  const solvedStr = root.solved_mm != null ? root.solved_mm.toFixed(2) : "—";
  const dimLabel = solvedDimLabel(result.shape);
  return (
    `M_design = ${mStr} N·m  |  Required W = ${wStr} mm³  |  ` +
    `Outer = ${outerStr} mm  |  ${dimLabel} = ${solvedStr}`
  );
}

// ---- Mass summary text -----------------------------------------------------

export function buildMassSummary(result: SparSizingResult): string {
  const half = result.spar_mass_half_kg.toFixed(3);
  const full = result.spar_mass_full_kg.toFixed(3);
  return `Est. spar mass: ${half} kg (half-span) / ${full} kg (full)`;
}

// ---- Sigma/g_limit display -------------------------------------------------

/**
 * Build parameter echo text for the spar-sizing inputs.
 * Used as the Plotly figure annotation when displaying the result.
 */
export function buildSizingAnnotationText(result: SparSizingResult): string {
  const lines = [
    `Material: ${result.material_name}  |  Shape: ${result.shape}`,
    `σ_allow = ${result.sigma_allow_mpa} MPa  |  ρ = ${result.density_kg_m3} kg/m³`,
    `n_lim = ${result.g_limit.toFixed(1)}${result.g_limit_fallback ? " (default)" : ""}  |  j = ${result.safety_factor_j}  |  packing = ${result.packing_factor}`,
  ];
  return lines.join("<br>");
}
