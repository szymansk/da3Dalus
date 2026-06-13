/**
 * Pure geometry parameter diff for the version-compare view (gh-971).
 *
 * Compares two sets of wing geometries (WingConfig objects, mm + degrees, the
 * shape returned by GET /aeroplanes/{uuid}/wings/{wing}/wingconfig) and reports
 * WHICH design inputs changed — per wing, per section, per core param — plus
 * presence/count flags for sub-elements (spar / control-surface / turbulator).
 *
 * Pure: no React, no network. All diff logic + the numeric tolerance live here
 * so the component/hook stay thin and the rules stay testable.
 *
 * Units follow WingConfig: chord/span in mm, incidence/dihedral in degrees,
 * sweep in mm. Numeric tolerance |Δ| <= 0.05 is treated as unchanged to
 * avoid float noise; airfoil compares by string equality.
 *
 * Section alignment is performed by SIGNATURE (root_chord|length|root_airfoil)
 * using an LCS (Longest Common Subsequence) algorithm so that inserting a
 * section in the middle does NOT cascade false "changed" on downstream sections.
 *
 * gh-402: spar dimensional fields (width/height/start/length) come from the API
 * in METRES (the API converts mm→m). They are multiplied by 1000 before both
 * display formatting and tolerance comparison so the diff works in mm.
 * spare_position_factor (0–1 fraction) and spare_mode (string) are NOT converted.
 *
 * Hints (gh-973) are computed per-section from RAW numeric values inside
 * computeGeometryDiff, deduped, and stored in GeometryDiff.hints. No
 * string-parsing needed; the old geometryDiffHints() export is removed.
 */

import type { WingConfig, WingConfigSegment } from "@/hooks/useWingConfig";

// --- Public types ----------------------------------------------------------

export type ChangeKind = "changed" | "added" | "removed";

/** A single core-param diff, e.g. key="root chord", a="162 mm", b="158 mm". */
export interface ParamChange {
  key: string;
  a: string | null;
  b: string | null;
}

/** A sub-element presence/count flag (spar / control_surface / turbulator). */
export interface SubElementFlag {
  key: string;
  kind: ChangeKind;
  a: string | null;
  b: string | null;
  /** Field-level detail: changed (or all, in showAll mode) fields of this sub-element. */
  fields?: ParamChange[];
}

export interface SectionDiff {
  index: number;
  kind: ChangeKind;
  label: string;
  params: ParamChange[];
  flags: SubElementFlag[];
}

export interface WingDiff {
  name: string;
  kind: ChangeKind;
  sections: SectionDiff[];
}

export interface GeometryDiff {
  wings: WingDiff[];
  counts: {
    sectionsChanged: number;
    sectionsAdded: number;
    sectionsRemoved: number;
  };
  hasAnyChange: boolean;
  /** Conservative per-section geometric observations. Max 5, deduped. */
  hints: string[];
}

/** One named wing's full geometry, the unit the diff aligns by name. */
export interface DiffWingInput {
  name: string;
  config: WingConfig;
}

export interface GeometryDiffOptions {
  showAll?: boolean;
}

// --- Constants --------------------------------------------------------------

/** |Δ| at or below this (mm or degrees) is float noise, not a change. */
const NUMERIC_TOLERANCE = 0.05;

/** Tight tolerance for spare_position_factor (0–1 fraction, not mm). */
const POSITION_FACTOR_TOLERANCE = 0.005;

// --- Formatting helpers -----------------------------------------------------

/** Strip ".dat" suffix from airfoil file names for display. */
function stripDat(name: string): string {
  return name.endsWith(".dat") ? name.slice(0, -4) : name;
}

/**
 * Format a number for display ("500", "1.5", "12.34").
 * Returns "—" for non-finite values (NaN, ±Infinity).
 */
function formatNumber(value: number): string {
  if (!Number.isFinite(value)) return "—";
  // Round to 2 dp, then drop trailing zeros / dot.
  const rounded = Math.round(value * 100) / 100;
  return String(rounded);
}

function formatMm(value: number): string {
  if (!Number.isFinite(value)) return "—";
  return `${formatNumber(value)} mm`;
}

function formatDeg(value: number): string {
  if (!Number.isFinite(value)) return "—";
  return `${formatNumber(value)} deg`;
}

// --- Core param extraction --------------------------------------------------

interface CoreParam {
  key: string;
  /** Numeric value used for tolerance comparison; null for string params. */
  num: number | null;
  /** Formatted display value. */
  display: string;
}

/**
 * Extract all core params for both root and tip airfoils of a segment.
 * Guards against missing root_airfoil / tip_airfoil with ?? {}.
 */
function coreParams(seg: WingConfigSegment): CoreParam[] {
  const af = seg.root_airfoil ?? {};
  const rootChord = (af as { chord?: number }).chord ?? 0;
  const rootIncidence = (af as { incidence?: number }).incidence ?? 0;
  const rootDihedral = (af as { dihedral_as_rotation_in_degrees?: number }).dihedral_as_rotation_in_degrees ?? 0;
  const rootAirfoil = stripDat((af as { airfoil?: string }).airfoil ?? "");

  const taf = seg.tip_airfoil ?? {};
  const tipChord = (taf as { chord?: number }).chord ?? 0;
  const tipIncidence = (taf as { incidence?: number }).incidence ?? 0;
  const tipDihedral = (taf as { dihedral_as_rotation_in_degrees?: number }).dihedral_as_rotation_in_degrees ?? 0;
  const tipAirfoil = stripDat((taf as { airfoil?: string }).airfoil ?? "");

  const span = seg.length ?? 0;
  const sweep = seg.sweep ?? 0;

  return [
    { key: "root chord", num: rootChord, display: formatMm(rootChord) },
    { key: "root incidence", num: rootIncidence, display: formatDeg(rootIncidence) },
    { key: "root dihedral", num: rootDihedral, display: formatDeg(rootDihedral) },
    { key: "root airfoil", num: null, display: rootAirfoil },
    { key: "tip chord", num: tipChord, display: formatMm(tipChord) },
    { key: "tip incidence", num: tipIncidence, display: formatDeg(tipIncidence) },
    { key: "tip dihedral", num: tipDihedral, display: formatDeg(tipDihedral) },
    { key: "tip airfoil", num: null, display: tipAirfoil },
    { key: "span", num: span, display: formatMm(span) },
    { key: "sweep", num: sweep, display: formatMm(sweep) },
  ];
}

function paramChanged(a: CoreParam, b: CoreParam): boolean {
  if (a.num !== null && b.num !== null) {
    const aFin = Number.isFinite(a.num);
    const bFin = Number.isFinite(b.num);
    // One finite, one not → changed
    if (aFin !== bFin) return true;
    // Both non-finite → unchanged (treat as same)
    if (!aFin && !bFin) return false;
    // Both finite → numeric tolerance comparison
    return Math.abs(a.num - b.num) > NUMERIC_TOLERANCE;
  }
  // string param (airfoil): exact equality
  return a.display !== b.display;
}

// --- Section signature for LCS alignment ------------------------------------

/**
 * Compute a stable signature for a segment for use in LCS alignment.
 * Uses root chord (rounded to nearest integer mm), length (rounded to
 * nearest integer mm), and the root airfoil name. Rounding to integers
 * tolerates minor float noise (e.g. 500 vs 500.04 both → 500) while
 * still distinguishing meaningfully different sections.
 */
function sectionSignature(seg: WingConfigSegment): string {
  const af = seg.root_airfoil ?? {};
  const chord = Math.round((af as { chord?: number }).chord ?? 0);
  const length = Math.round(seg.length ?? 0);
  const airfoil = stripDat((af as { airfoil?: string }).airfoil ?? "");
  return `${chord}|${length}|${airfoil}`;
}

/**
 * LCS-align segsA and segsB by signature.
 *
 * Returns an array of pairs where each entry is either:
 *   [segA, segB]  — matched pair (both defined)
 *   [segA, null]  — removed (only in A)
 *   [null, segB]  — added (only in B)
 *
 * The LCS is computed over signature strings. Matched pairs preserve the
 * original segment data for detailed diffing.
 */
function lcsAlign(
  segsA: WingConfigSegment[],
  segsB: WingConfigSegment[],
): Array<[WingConfigSegment | null, WingConfigSegment | null]> {
  const sigsA = segsA.map(sectionSignature);
  const sigsB = segsB.map(sectionSignature);
  const m = sigsA.length;
  const n = sigsB.length;

  // Build LCS table
  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (sigsA[i - 1] === sigsB[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  // Trace back to build aligned pairs
  const result: Array<[WingConfigSegment | null, WingConfigSegment | null]> = [];
  let i = m;
  let j = n;
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && sigsA[i - 1] === sigsB[j - 1]) {
      result.unshift([segsA[i - 1], segsB[j - 1]]);
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      result.unshift([null, segsB[j - 1]]);
      j--;
    } else {
      result.unshift([segsA[i - 1], null]);
      i--;
    }
  }

  return result;
}

// --- Sub-element flag extraction --------------------------------------------

function sparLabel(count: number): string {
  return `${count} ${count === 1 ? "spar" : "spars"}`;
}

function tedName(ted: Record<string, unknown> | null | undefined): string {
  if (ted == null) return "—";
  const name = ted["name"];
  if (typeof name === "string" && name.trim() !== "") return name;
  return "on";
}

function turbulatorLabel(
  turb: Record<string, unknown> | null | undefined,
): string {
  return turb == null ? "—" : "on";
}

// --- Field-level helpers for numeric tolerance comparison -------------------

function numericFieldChanged(a: unknown, b: unknown, tol: number = NUMERIC_TOLERANCE): boolean {
  if (typeof a === "number" && typeof b === "number") {
    if (!Number.isFinite(a) || !Number.isFinite(b)) return a !== b;
    return Math.abs(a - b) > tol;
  }
  return String(a ?? "") !== String(b ?? "");
}

function formatFieldValue(value: unknown, unit?: "mm"): string {
  if (value == null) return "—";
  if (typeof value === "number") {
    if (!Number.isFinite(value)) return "—";
    const rounded = Math.round(value * 100) / 100;
    const s = String(rounded);
    return unit === "mm" ? `${s} mm` : s;
  }
  return String(value);
}

// --- Spar field-level diff --------------------------------------------------

/**
 * gh-402: spar dimensional fields arrive from the API in metres (mm stored in
 * DB but converted to m by the API layer). Multiply by 1000 before display and
 * tolerance comparison so everything is in mm. spare_position_factor (0–1) and
 * spare_mode (string) are NOT converted.
 */
function sparFieldDiff(
  sparA: Record<string, unknown>,
  sparB: Record<string, unknown>,
  sparIndex: number,
  showAll: boolean,
): ParamChange[] {
  const n = sparIndex + 1;

  // Dimensional fields: metres → mm conversion factor
  const M_TO_MM = 1000;

  const widthA = typeof sparA["spare_support_dimension_width"] === "number"
    ? sparA["spare_support_dimension_width"] * M_TO_MM
    : sparA["spare_support_dimension_width"];
  const widthB = typeof sparB["spare_support_dimension_width"] === "number"
    ? sparB["spare_support_dimension_width"] * M_TO_MM
    : sparB["spare_support_dimension_width"];

  const heightA = typeof sparA["spare_support_dimension_height"] === "number"
    ? sparA["spare_support_dimension_height"] * M_TO_MM
    : sparA["spare_support_dimension_height"];
  const heightB = typeof sparB["spare_support_dimension_height"] === "number"
    ? sparB["spare_support_dimension_height"] * M_TO_MM
    : sparB["spare_support_dimension_height"];

  const startA = typeof sparA["spare_start"] === "number"
    ? sparA["spare_start"] * M_TO_MM
    : sparA["spare_start"];
  const startB = typeof sparB["spare_start"] === "number"
    ? sparB["spare_start"] * M_TO_MM
    : sparB["spare_start"];

  const lengthA = typeof sparA["spare_length"] === "number"
    ? sparA["spare_length"] * M_TO_MM
    : sparA["spare_length"];
  const lengthB = typeof sparB["spare_length"] === "number"
    ? sparB["spare_length"] * M_TO_MM
    : sparB["spare_length"];

  const fields: Array<{ key: string; aVal: unknown; bVal: unknown; unit?: "mm"; tol?: number }> = [
    {
      key: `spar ${n} position`,
      aVal: sparA["spare_position_factor"],
      bVal: sparB["spare_position_factor"],
      tol: POSITION_FACTOR_TOLERANCE,
    },
    { key: `spar ${n} width`, aVal: widthA, bVal: widthB, unit: "mm" },
    { key: `spar ${n} height`, aVal: heightA, bVal: heightB, unit: "mm" },
    { key: `spar ${n} start`, aVal: startA, bVal: startB, unit: "mm" },
    { key: `spar ${n} length`, aVal: lengthA, bVal: lengthB, unit: "mm" },
    { key: `spar ${n} mode`, aVal: sparA["spare_mode"], bVal: sparB["spare_mode"] },
  ];

  const result: ParamChange[] = [];
  for (const f of fields) {
    const changed = numericFieldChanged(f.aVal, f.bVal, f.tol ?? NUMERIC_TOLERANCE);
    if (showAll || changed) {
      result.push({
        key: f.key,
        a: formatFieldValue(f.aVal, f.unit),
        b: formatFieldValue(f.bVal, f.unit),
      });
    }
  }
  return result;
}

function sparFlags(
  a: WingConfigSegment,
  b: WingConfigSegment,
  showAll: boolean,
): SubElementFlag | null {
  const listA = (a.spare_list ?? []) as Record<string, unknown>[];
  const listB = (b.spare_list ?? []) as Record<string, unknown>[];
  const countA = listA.length;
  const countB = listB.length;
  const labelA = sparLabel(countA);
  const labelB = sparLabel(countB);

  // Determine overall kind
  let kind: ChangeKind = "changed";
  if (countA === 0 && countB > 0) kind = "added";
  else if (countA > 0 && countB === 0) kind = "removed";

  if (!showAll && labelA === labelB) {
    // Count unchanged; still check fields to see if any changed.
    // Only emit field diffs when counts are equal (index alignment is safe).
    if (countA !== countB) {
      // Counts differ but labels happen to be equal — shouldn't happen with
      // sparLabel, but guard anyway.
      return { key: "spar", kind, a: labelA, b: labelB };
    }
    const fields: ParamChange[] = [];
    const sharedCount = Math.min(countA, countB);
    for (let i = 0; i < sharedCount; i++) {
      const sparA = listA[i] ?? {};
      const sparB = listB[i] ?? {};
      fields.push(...sparFieldDiff(sparA, sparB, i, false));
    }
    if (fields.length === 0) return null;
    return { key: "spar", kind, a: labelA, b: labelB, fields };
  }

  // showAll=true OR label changed (count changed).
  // When counts differ, do NOT emit positional field sub-rows — pairing by
  // index is unsafe (an insert at position k would corrupt every spar after k).
  if (countA !== countB) {
    return {
      key: "spar",
      kind,
      a: labelA,
      b: labelB,
      // fields deliberately empty/undefined — count mismatch makes positional
      // field-pairing meaningless.
    };
  }

  // Counts equal — safe to pair by index.
  const fields: ParamChange[] = [];
  const sharedCount = Math.min(countA, countB);
  for (let i = 0; i < sharedCount; i++) {
    const sparA = listA[i] ?? {};
    const sparB = listB[i] ?? {};
    fields.push(...sparFieldDiff(sparA, sparB, i, showAll));
  }

  return {
    key: "spar",
    kind,
    a: labelA,
    b: labelB,
    fields: fields.length > 0 ? fields : undefined,
  };
}

// --- TED field-level diff ---------------------------------------------------

const TED_FIELDS: Array<{ key: string; prop: string }> = [
  { key: "control surface name", prop: "name" },
  { key: "control surface role", prop: "role" },
  { key: "control surface rel_chord_root", prop: "rel_chord_root" },
  { key: "control surface rel_chord_tip", prop: "rel_chord_tip" },
  { key: "control surface positive_deflection_deg", prop: "positive_deflection_deg" },
  { key: "control surface negative_deflection_deg", prop: "negative_deflection_deg" },
  { key: "control surface hinge_type", prop: "hinge_type" },
  { key: "control surface servo_placement", prop: "servo_placement" },
  { key: "control surface servo_index", prop: "servo_index" },
];

function tedFieldDiff(
  tedA: Record<string, unknown>,
  tedB: Record<string, unknown>,
  showAll: boolean,
): ParamChange[] {
  const result: ParamChange[] = [];
  for (const f of TED_FIELDS) {
    const aVal = tedA[f.prop];
    const bVal = tedB[f.prop];
    const changed = numericFieldChanged(aVal, bVal);
    if (showAll || changed) {
      result.push({
        key: f.key,
        a: formatFieldValue(aVal),
        b: formatFieldValue(bVal),
      });
    }
  }
  return result;
}

function tedFlag(
  a: WingConfigSegment,
  b: WingConfigSegment,
  showAll: boolean,
): SubElementFlag | null {
  const tedA = a.trailing_edge_device;
  const tedB = b.trailing_edge_device;
  const labelA = tedName(tedA);
  const labelB = tedName(tedB);

  const bothPresent = tedA != null && tedB != null;
  const labelChanged = labelA !== labelB;

  // Determine kind from presence
  let kind: ChangeKind = "changed";
  if (tedA == null && tedB != null) kind = "added";
  else if (tedA != null && tedB == null) kind = "removed";

  if (!showAll && !labelChanged && !bothPresent) return null;

  const fields: ParamChange[] = bothPresent
    ? tedFieldDiff(tedA as Record<string, unknown>, tedB as Record<string, unknown>, showAll)
    : [];

  // In changes-only mode: if label is same AND no field changes → skip
  if (!showAll && !labelChanged && fields.length === 0) return null;

  return {
    key: "control_surface",
    kind,
    a: labelA,
    b: labelB,
    fields: fields.length > 0 ? fields : undefined,
  };
}

// --- Turbulator field-level diff --------------------------------------------

const TURBULATOR_FIELDS: Array<{ key: string; prop: string }> = [
  { key: "turbulator form", prop: "form" },
  { key: "turbulator height_mm", prop: "height_mm" },
  { key: "turbulator position_root", prop: "position_root" },
  { key: "turbulator position_tip", prop: "position_tip" },
  { key: "turbulator enabled", prop: "enabled" },
];

function turbulatorFieldDiff(
  turbA: Record<string, unknown>,
  turbB: Record<string, unknown>,
  showAll: boolean,
): ParamChange[] {
  const result: ParamChange[] = [];
  for (const f of TURBULATOR_FIELDS) {
    const aVal = turbA[f.prop];
    const bVal = turbB[f.prop];
    const changed = numericFieldChanged(aVal, bVal);
    if (showAll || changed) {
      result.push({
        key: f.key,
        a: formatFieldValue(aVal),
        b: formatFieldValue(bVal),
      });
    }
  }
  return result;
}

function turbulatorFlag(
  a: WingConfigSegment,
  b: WingConfigSegment,
  showAll: boolean,
): SubElementFlag | null {
  const turbA = a.turbulator;
  const turbB = b.turbulator;
  const labelA = turbulatorLabel(turbA);
  const labelB = turbulatorLabel(turbB);
  const labelChanged = labelA !== labelB;
  const bothPresent = turbA != null && turbB != null;

  // Determine kind from presence
  let kind: ChangeKind = "changed";
  if (turbA == null && turbB != null) kind = "added";
  else if (turbA != null && turbB == null) kind = "removed";

  const fields: ParamChange[] = bothPresent
    ? turbulatorFieldDiff(turbA as Record<string, unknown>, turbB as Record<string, unknown>, showAll)
    : [];

  if (!showAll && !labelChanged && fields.length === 0) return null;

  return {
    key: "turbulator",
    kind,
    a: labelA,
    b: labelB,
    fields: fields.length > 0 ? fields : undefined,
  };
}

function subElementFlags(
  a: WingConfigSegment,
  b: WingConfigSegment,
  showAll: boolean,
): SubElementFlag[] {
  const flags: SubElementFlag[] = [];

  const spar = sparFlags(a, b, showAll);
  if (spar != null) flags.push(spar);

  const ted = tedFlag(a, b, showAll);
  if (ted != null) flags.push(ted);

  const turb = turbulatorFlag(a, b, showAll);
  if (turb != null) flags.push(turb);

  return flags;
}

// --- Section diff -----------------------------------------------------------

/**
 * Generate a label for a section with its position role.
 * Index 0 → "Section 1 · root", last index (totalSections-1) → "Section N · tip",
 * middle → "Section k · mid".
 */
function sectionLabel(index: number, totalSections: number): string {
  const num = index + 1;
  if (totalSections === 1) return `Section ${num} · root`;
  if (index === 0) return `Section ${num} · root`;
  if (index === totalSections - 1) return `Section ${num} · tip`;
  return `Section ${num} · mid`;
}

function diffPresentSection(
  index: number,
  totalSections: number,
  a: WingConfigSegment,
  b: WingConfigSegment,
  showAll: boolean,
): SectionDiff {
  const paramsA = coreParams(a);
  const paramsB = coreParams(b);

  const params: ParamChange[] = [];
  for (let i = 0; i < paramsA.length; i++) {
    const pa = paramsA[i];
    const pb = paramsB[i];
    const changed = paramChanged(pa, pb);
    if (showAll || changed) {
      params.push({ key: pa.key, a: pa.display, b: pb.display });
    }
  }

  const flags = subElementFlags(a, b, showAll);

  return {
    index,
    kind: "changed",
    label: sectionLabel(index, totalSections),
    params,
    flags,
  };
}

// --- Per-section hint accumulation (gh-973) ---------------------------------

/**
 * Accumulate geometric hints from a matched section pair using raw numeric
 * values. Called during section alignment inside diffWing so hints are based
 * on the same data used for the diff — not re-parsed from formatted strings.
 *
 * Rules (conservative, per-section):
 *   - taper: tip chord decreased while root chord ~unchanged (≤5 mm shift)
 *   - dihedral: a section's dihedral increased
 *   - airfoil changed: any airfoil changed → "re-run the polar"
 *
 * Washout and span are evaluated at the wing level (after alignment), not here.
 */
function accumulateSectionHints(
  a: WingConfigSegment,
  b: WingConfigSegment,
  hints: Set<string>,
): void {
  if (hints.size >= 5) return;

  const afA = a.root_airfoil ?? {};
  const afB = b.root_airfoil ?? {};
  const tafA = a.tip_airfoil ?? {};
  const tafB = b.tip_airfoil ?? {};

  const rootChordA = (afA as { chord?: number }).chord ?? 0;
  const rootChordB = (afB as { chord?: number }).chord ?? 0;
  const tipChordA = (tafA as { chord?: number }).chord ?? 0;
  const tipChordB = (tafB as { chord?: number }).chord ?? 0;

  // Taper: tip chord decreased while root chord roughly unchanged (≤5 mm)
  const rootUnchanged = Math.abs(rootChordA - rootChordB) <= NUMERIC_TOLERANCE * 100; // 5 mm
  const tipDecreased = tipChordB < tipChordA - NUMERIC_TOLERANCE;
  if (rootUnchanged && tipDecreased) {
    hints.add("More taper (tip chord ↓)");
  }

  if (hints.size >= 5) return;

  // Dihedral increased
  const dihA = (afA as { dihedral_as_rotation_in_degrees?: number }).dihedral_as_rotation_in_degrees ?? 0;
  const dihB = (afB as { dihedral_as_rotation_in_degrees?: number }).dihedral_as_rotation_in_degrees ?? 0;
  if (dihB > dihA + NUMERIC_TOLERANCE) {
    hints.add("More dihedral");
  }

  if (hints.size >= 5) return;

  // Airfoil changed (root or tip)
  const rootAirfoilA = stripDat((afA as { airfoil?: string }).airfoil ?? "");
  const rootAirfoilB = stripDat((afB as { airfoil?: string }).airfoil ?? "");
  const tipAirfoilA = stripDat((tafA as { airfoil?: string }).airfoil ?? "");
  const tipAirfoilB = stripDat((tafB as { airfoil?: string }).airfoil ?? "");
  if (
    (rootAirfoilA !== rootAirfoilB && rootAirfoilA !== "" && rootAirfoilB !== "") ||
    (tipAirfoilA !== tipAirfoilB && tipAirfoilA !== "" && tipAirfoilB !== "")
  ) {
    hints.add("Airfoil changed — re-run the polar");
  }
}

// --- Wing diff --------------------------------------------------------------

interface WingDiffResult {
  diff: WingDiff;
  sectionsChanged: number;
  sectionsAdded: number;
  sectionsRemoved: number;
  changed: boolean;
  hints: Set<string>;
}

/** Check whether any spar, TED, or turbulator field-level diff exists. */
function subElementHasFieldChange(
  a: WingConfigSegment,
  b: WingConfigSegment,
): boolean {
  // Field-level changes in spars (only when counts match — safe to pair by index)
  const listA = (a.spare_list ?? []) as Record<string, unknown>[];
  const listB = (b.spare_list ?? []) as Record<string, unknown>[];
  if (listA.length === listB.length) {
    for (let i = 0; i < listA.length; i++) {
      const f = sparFieldDiff(listA[i] ?? {}, listB[i] ?? {}, i, false);
      if (f.length > 0) return true;
    }
  }
  // Field-level changes in TED
  if (a.trailing_edge_device != null && b.trailing_edge_device != null) {
    const f = tedFieldDiff(
      a.trailing_edge_device as Record<string, unknown>,
      b.trailing_edge_device as Record<string, unknown>,
      false,
    );
    if (f.length > 0) return true;
  }
  // Field-level changes in turbulator
  if (a.turbulator != null && b.turbulator != null) {
    const f = turbulatorFieldDiff(
      a.turbulator as Record<string, unknown>,
      b.turbulator as Record<string, unknown>,
      false,
    );
    if (f.length > 0) return true;
  }
  return false;
}

function sectionHasRealChange(
  a: WingConfigSegment,
  b: WingConfigSegment,
): boolean {
  const paramsA = coreParams(a);
  const paramsB = coreParams(b);
  if (paramsA.some((pa, i) => paramChanged(pa, paramsB[i]))) return true;

  // Count-level changes
  const sparCountChange = (a.spare_list?.length ?? 0) !== (b.spare_list?.length ?? 0);
  const tedLabelChange = tedName(a.trailing_edge_device) !== tedName(b.trailing_edge_device);
  const turbLabelChange = turbulatorLabel(a.turbulator) !== turbulatorLabel(b.turbulator);
  if (sparCountChange || tedLabelChange || turbLabelChange) return true;

  return subElementHasFieldChange(a, b);
}

/** Accumulate wing-level hints (washout from outermost section, span from tip addition). */
function accumulateWingHints(
  aligned: Array<[WingConfigSegment | null, WingConfigSegment | null]>,
  hints: Set<string>,
): void {
  // Washout: ONLY the outermost (last) matched section's tip incidence decreased.
  const matchedPairs: Array<[WingConfigSegment, WingConfigSegment]> = [];
  for (const [segA, segB] of aligned) {
    if (segA && segB) matchedPairs.push([segA, segB]);
  }
  if (matchedPairs.length > 0 && hints.size < 5) {
    const [lastA, lastB] = matchedPairs[matchedPairs.length - 1];
    const tafA = lastA.tip_airfoil ?? {};
    const tafB = lastB.tip_airfoil ?? {};
    const tipIncA = (tafA as { incidence?: number }).incidence ?? 0;
    const tipIncB = (tafB as { incidence?: number }).incidence ?? 0;
    if (tipIncB < tipIncA - NUMERIC_TOLERANCE) {
      hints.add("More washout at the tip");
    }
  }
  // Span: last section in the aligned list was added at the tip.
  if (aligned.length > 0 && hints.size < 5) {
    const [lastA, lastB] = aligned[aligned.length - 1];
    if (!lastA && lastB) {
      hints.add("Longer span (tip section added)");
    }
  }
}

function diffWing(
  name: string,
  a: WingConfig,
  b: WingConfig,
  showAll: boolean,
): WingDiffResult {
  const segsA = a.segments ?? [];
  const segsB = b.segments ?? [];

  // LCS-align sections by signature (not by index)
  const aligned = lcsAlign(segsA, segsB);
  const totalSections = aligned.length;

  const sections: SectionDiff[] = [];
  let sectionsChanged = 0;
  let sectionsAdded = 0;
  let sectionsRemoved = 0;
  const hints = new Set<string>();

  for (let i = 0; i < aligned.length; i++) {
    const [segA, segB] = aligned[i];
    if (segA && segB) {
      const changed = sectionHasRealChange(segA, segB);
      if (changed) {
        sectionsChanged++;
        accumulateSectionHints(segA, segB, hints);
      }
      if (showAll || changed) {
        sections.push(diffPresentSection(i, totalSections, segA, segB, showAll));
      }
    } else if (segB) {
      sectionsAdded++;
      sections.push({ index: i, kind: "added", label: sectionLabel(i, totalSections), params: [], flags: [] });
    } else if (segA) {
      sectionsRemoved++;
      sections.push({ index: i, kind: "removed", label: sectionLabel(i, totalSections), params: [], flags: [] });
    }
  }

  accumulateWingHints(aligned, hints);

  const changed = sectionsChanged > 0 || sectionsAdded > 0 || sectionsRemoved > 0;
  return {
    diff: { name, kind: "changed", sections },
    sectionsChanged,
    sectionsAdded,
    sectionsRemoved,
    changed,
    hints,
  };
}

// --- Top-level diff ---------------------------------------------------------

/** Stable name order: A's wings first (in order), then B-only wings. */
function orderedWingNames(
  wingsA: DiffWingInput[],
  wingsB: DiffWingInput[],
): string[] {
  const names: string[] = [];
  const seen = new Set<string>();
  for (const w of [...wingsA, ...wingsB]) {
    if (!seen.has(w.name)) {
      names.push(w.name);
      seen.add(w.name);
    }
  }
  return names;
}

/** Build a wing diff for a wing present on only one side (added/removed). */
function presenceWing(
  name: string,
  kind: "added" | "removed",
  config: WingConfig,
): WingDiff {
  const segs = config.segments ?? [];
  const totalSections = segs.length;
  return {
    name,
    kind,
    sections: segs.map((_, i) => ({
      index: i,
      kind,
      label: sectionLabel(i, totalSections),
      params: [],
      flags: [],
    })),
  };
}

interface DiffAccumulator {
  wings: WingDiff[];
  sectionsChanged: number;
  sectionsAdded: number;
  sectionsRemoved: number;
  hasAnyChange: boolean;
  allHints: Set<string>;
}

function processMatchedWing(
  name: string,
  a: DiffWingInput,
  b: DiffWingInput,
  showAll: boolean,
  acc: DiffAccumulator,
): void {
  const res = diffWing(name, a.config, b.config, showAll);
  acc.sectionsChanged += res.sectionsChanged;
  acc.sectionsAdded += res.sectionsAdded;
  acc.sectionsRemoved += res.sectionsRemoved;
  if (res.changed) acc.hasAnyChange = true;
  if (showAll || res.changed) acc.wings.push(res.diff);
  for (const h of res.hints) {
    if (acc.allHints.size < 5) acc.allHints.add(h);
  }
}

export function computeGeometryDiff(
  wingsA: DiffWingInput[],
  wingsB: DiffWingInput[],
  opts: GeometryDiffOptions = {},
): GeometryDiff {
  const showAll = opts.showAll ?? false;

  const byNameA = new Map(wingsA.map((w) => [w.name, w]));
  const byNameB = new Map(wingsB.map((w) => [w.name, w]));

  const acc: DiffAccumulator = {
    wings: [],
    sectionsChanged: 0,
    sectionsAdded: 0,
    sectionsRemoved: 0,
    hasAnyChange: false,
    allHints: new Set<string>(),
  };

  for (const name of orderedWingNames(wingsA, wingsB)) {
    const a = byNameA.get(name);
    const b = byNameB.get(name);

    if (a && b) {
      processMatchedWing(name, a, b, showAll, acc);
    } else if (b) {
      acc.hasAnyChange = true;
      acc.sectionsAdded += b.config.segments?.length ?? 0;
      acc.wings.push(presenceWing(name, "added", b.config));
    } else if (a) {
      acc.hasAnyChange = true;
      acc.sectionsRemoved += a.config.segments?.length ?? 0;
      acc.wings.push(presenceWing(name, "removed", a.config));
    }
  }

  return {
    wings: acc.wings,
    counts: { sectionsChanged: acc.sectionsChanged, sectionsAdded: acc.sectionsAdded, sectionsRemoved: acc.sectionsRemoved },
    hasAnyChange: acc.hasAnyChange,
    hints: Array.from(acc.allHints),
  };
}
