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

function numericFieldChanged(a: unknown, b: unknown): boolean {
  if (typeof a === "number" && typeof b === "number") {
    if (!Number.isFinite(a) || !Number.isFinite(b)) return a !== b;
    return Math.abs(a - b) > NUMERIC_TOLERANCE;
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

function sparFieldDiff(
  sparA: Record<string, unknown>,
  sparB: Record<string, unknown>,
  sparIndex: number,
  showAll: boolean,
): ParamChange[] {
  const n = sparIndex + 1;
  const fields: Array<{ key: string; aVal: unknown; bVal: unknown; unit?: "mm" }> = [
    { key: `spar ${n} position`, aVal: sparA["spare_position_factor"], bVal: sparB["spare_position_factor"] },
    { key: `spar ${n} width`, aVal: sparA["spare_support_dimension_width"], bVal: sparB["spare_support_dimension_width"], unit: "mm" },
    { key: `spar ${n} height`, aVal: sparA["spare_support_dimension_height"], bVal: sparB["spare_support_dimension_height"], unit: "mm" },
    { key: `spar ${n} start`, aVal: sparA["spare_start"], bVal: sparB["spare_start"], unit: "mm" },
    { key: `spar ${n} length`, aVal: sparA["spare_length"], bVal: sparB["spare_length"], unit: "mm" },
    { key: `spar ${n} mode`, aVal: sparA["spare_mode"], bVal: sparB["spare_mode"] },
  ];

  const result: ParamChange[] = [];
  for (const f of fields) {
    const changed = numericFieldChanged(f.aVal, f.bVal);
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
    // Count unchanged; still check fields to see if any changed
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

  if (!showAll && !labelChanged && !bothPresent) return null;

  if (!showAll && !labelChanged && !bothPresent) return null;

  const fields: ParamChange[] = bothPresent
    ? tedFieldDiff(tedA as Record<string, unknown>, tedB as Record<string, unknown>, showAll)
    : [];

  // In changes-only mode: if label is same AND no field changes → skip
  if (!showAll && !labelChanged && fields.length === 0) return null;

  return {
    key: "control_surface",
    kind: "changed",
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

  const fields: ParamChange[] = bothPresent
    ? turbulatorFieldDiff(turbA as Record<string, unknown>, turbB as Record<string, unknown>, showAll)
    : [];

  if (!showAll && !labelChanged && fields.length === 0) return null;

  return {
    key: "turbulator",
    kind: "changed",
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

// --- Wing diff --------------------------------------------------------------

interface WingDiffResult {
  diff: WingDiff;
  sectionsChanged: number;
  sectionsAdded: number;
  sectionsRemoved: number;
  changed: boolean;
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

  for (let i = 0; i < aligned.length; i++) {
    const [segA, segB] = aligned[i];

    if (segA && segB) {
      const changed = sectionHasRealChange(segA, segB);
      if (changed) sectionsChanged++;
      if (showAll || changed) {
        sections.push(diffPresentSection(i, totalSections, segA, segB, showAll));
      }
    } else if (segB && !segA) {
      sectionsAdded++;
      sections.push({
        index: i,
        kind: "added",
        label: sectionLabel(i, totalSections),
        params: [],
        flags: [],
      });
    } else if (segA && !segB) {
      sectionsRemoved++;
      sections.push({
        index: i,
        kind: "removed",
        label: sectionLabel(i, totalSections),
        params: [],
        flags: [],
      });
    }
  }

  const changed =
    sectionsChanged > 0 || sectionsAdded > 0 || sectionsRemoved > 0;

  return {
    diff: { name, kind: "changed", sections },
    sectionsChanged,
    sectionsAdded,
    sectionsRemoved,
    changed,
  };
}

function sectionHasRealChange(
  a: WingConfigSegment,
  b: WingConfigSegment,
): boolean {
  const paramsA = coreParams(a);
  const paramsB = coreParams(b);
  const paramChange = paramsA.some((pa, i) => paramChanged(pa, paramsB[i]));
  if (paramChange) return true;

  // Count-level changes
  const sparCountChange = (a.spare_list?.length ?? 0) !== (b.spare_list?.length ?? 0);
  const tedLabelChange = tedName(a.trailing_edge_device) !== tedName(b.trailing_edge_device);
  const turbLabelChange = turbulatorLabel(a.turbulator) !== turbulatorLabel(b.turbulator);
  if (sparCountChange || tedLabelChange || turbLabelChange) return true;

  // Field-level changes in spars
  const listA = (a.spare_list ?? []) as Record<string, unknown>[];
  const listB = (b.spare_list ?? []) as Record<string, unknown>[];
  for (let i = 0; i < Math.min(listA.length, listB.length); i++) {
    const f = sparFieldDiff(listA[i] ?? {}, listB[i] ?? {}, i, false);
    if (f.length > 0) return true;
  }

  // Field-level changes in TED (when both present and label same)
  if (a.trailing_edge_device != null && b.trailing_edge_device != null) {
    const f = tedFieldDiff(
      a.trailing_edge_device as Record<string, unknown>,
      b.trailing_edge_device as Record<string, unknown>,
      false,
    );
    if (f.length > 0) return true;
  }

  // Field-level changes in turbulator (when both present and label same)
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

export function computeGeometryDiff(
  wingsA: DiffWingInput[],
  wingsB: DiffWingInput[],
  opts: GeometryDiffOptions = {},
): GeometryDiff {
  const showAll = opts.showAll ?? false;

  const byNameA = new Map(wingsA.map((w) => [w.name, w]));
  const byNameB = new Map(wingsB.map((w) => [w.name, w]));

  const wings: WingDiff[] = [];
  let sectionsChanged = 0;
  let sectionsAdded = 0;
  let sectionsRemoved = 0;
  let hasAnyChange = false;

  for (const name of orderedWingNames(wingsA, wingsB)) {
    const a = byNameA.get(name);
    const b = byNameB.get(name);

    if (a && b) {
      const res = diffWing(name, a.config, b.config, showAll);
      sectionsChanged += res.sectionsChanged;
      sectionsAdded += res.sectionsAdded;
      sectionsRemoved += res.sectionsRemoved;
      if (res.changed) hasAnyChange = true;
      if (showAll || res.changed) {
        wings.push(res.diff);
      }
    } else if (b && !a) {
      hasAnyChange = true;
      sectionsAdded += b.config.segments?.length ?? 0;
      wings.push(presenceWing(name, "added", b.config));
    } else if (a && !b) {
      hasAnyChange = true;
      sectionsRemoved += a.config.segments?.length ?? 0;
      wings.push(presenceWing(name, "removed", a.config));
    }
  }

  return {
    wings,
    counts: { sectionsChanged, sectionsAdded, sectionsRemoved },
    hasAnyChange,
  };
}

// --- GH #973: Plain-language geometry hints ---------------------------------

/**
 * Parse a display value like "200 mm" → 200, or "2 deg" → 2.
 * Returns null if not parseable.
 */
function parseDisplayNum(display: string | null): number | null {
  if (display == null || display === "—") return null;
  const n = parseFloat(display);
  return Number.isFinite(n) ? n : null;
}

/**
 * Find a param by key across all sections of all wings in the diff.
 * Returns all matched ParamChange entries.
 */
function allParams(diff: GeometryDiff, key: string): Array<{ a: string | null; b: string | null }> {
  const result: Array<{ a: string | null; b: string | null }> = [];
  for (const wing of diff.wings) {
    for (const section of wing.sections) {
      for (const p of section.params) {
        if (p.key === key) result.push(p);
      }
    }
  }
  return result;
}

/**
 * Returns a small set of conservative, geometric hints derived from the diff.
 * NOT aerodynamic predictions — only geometric observations.
 * At most 5 hints. Only emits when clearly true from the diff data.
 */
export function geometryDiffHints(diff: GeometryDiff): string[] {
  const hints: string[] = [];

  // Rule 1: tip chord decreased while root chord roughly unchanged → more taper
  const rootChords = allParams(diff, "root chord");
  const tipChords = allParams(diff, "tip chord");
  const rootUnchanged = rootChords.every((p) => {
    const a = parseDisplayNum(p.a);
    const b = parseDisplayNum(p.b);
    if (a == null || b == null) return false;
    return Math.abs(a - b) <= NUMERIC_TOLERANCE * 10; // allow ~0.5 mm
  });
  const tipDecreased = tipChords.some((p) => {
    const a = parseDisplayNum(p.a);
    const b = parseDisplayNum(p.b);
    if (a == null || b == null) return false;
    return b < a - NUMERIC_TOLERANCE;
  });
  if (rootChords.length > 0 && rootUnchanged && tipDecreased) {
    hints.push("More taper (tip chord ↓)");
  }

  if (hints.length >= 5) return hints;

  // Rule 2: tip incidence decreased / more negative than root → washout
  const tipIncidences = allParams(diff, "tip incidence");
  const tipIncDecreased = tipIncidences.some((p) => {
    const a = parseDisplayNum(p.a);
    const b = parseDisplayNum(p.b);
    if (a == null || b == null) return false;
    return b < a - NUMERIC_TOLERANCE;
  });
  if (tipIncDecreased) {
    hints.push("More washout at the tip");
  }

  if (hints.length >= 5) return hints;

  // Rule 3: section added at the last position → longer span
  for (const wing of diff.wings) {
    const sections = wing.sections;
    if (sections.length === 0) continue;
    const last = sections[sections.length - 1];
    if (last.kind === "added") {
      hints.push("Longer span (tip section added)");
      break;
    }
  }

  if (hints.length >= 5) return hints;

  // Rule 4: dihedral increased
  const dihedrals = allParams(diff, "root dihedral");
  const dihedralIncreased = dihedrals.some((p) => {
    const a = parseDisplayNum(p.a);
    const b = parseDisplayNum(p.b);
    if (a == null || b == null) return false;
    return b > a + NUMERIC_TOLERANCE;
  });
  if (dihedralIncreased) {
    hints.push("More dihedral");
  }

  if (hints.length >= 5) return hints;

  // Rule 5: any airfoil changed → re-run polar
  const rootAirfoils = allParams(diff, "root airfoil");
  const tipAirfoils = allParams(diff, "tip airfoil");
  const anyAirfoilChanged = [...rootAirfoils, ...tipAirfoils].some(
    (p) => p.a !== p.b && p.a != null && p.b != null,
  );
  if (anyAirfoilChanged) {
    hints.push("Airfoil changed — re-run the polar");
  }

  return hints;
}
