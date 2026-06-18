// frontend/lib/sparPlanHelpers.ts
// gh-1050: Pure helpers for the buildable-spar plan display + insert preview.
// Side-effect-free and DOM-free so they can be unit-tested directly.

import type { SpanwiseLoadsResult } from "@/hooks/useSpanwiseLoads";
import type {
  MomentSample,
  PlannedSpareOut,
  SparPieceOut,
} from "@/hooks/useSparPlan";

// ---- Moments distribution from spanwise loads ------------------------------

/**
 * Build the spanwise bending-moment distribution (root→tip) the spar-plan
 * endpoint expects, from the already-computed spanwise-loads result.
 *
 * The loads result exposes M(y) per strip on the starboard half of each
 * surface as { y_m, bending_moment_Nm }. The spar-plan request wants
 * y_span as a 0..1 span fraction, so we normalise y_m by the outermost
 * (max) y_m of the chosen surface. Magnitudes are used (|M|) because the
 * spar is sized on the bending-moment magnitude.
 *
 * Returns null when there is no usable distribution (no surfaces / strips /
 * zero span), so the caller can keep the plan disabled.
 */
export function buildMomentsFromLoads(
  loads: SpanwiseLoadsResult | null | undefined,
  surfaceIndex = 0,
): MomentSample[] | null {
  const surf = loads?.surfaces?.[surfaceIndex];
  if (!surf || surf.starboard.length === 0) return null;

  const entries = [...surf.starboard].sort((a, b) => a.y_m - b.y_m);
  const maxY = Math.max(...entries.map((e) => Math.abs(e.y_m)));
  if (!Number.isFinite(maxY) || maxY <= 0) return null;

  return entries.map((e) => ({
    y_span: Math.min(1, Math.max(0, Math.abs(e.y_m) / maxY)),
    bending_moment_Nm: Math.abs(e.bending_moment_Nm),
  }));
}

// ---- Built-spar piece formatting -------------------------------------------

/** Metres → millimetres, rounded for display. */
export function mToMm(m: number, digits = 1): string {
  return (m * 1000).toFixed(digits);
}

/**
 * Human label for a spar group. The FRONT spar is the structural main spar
 * (spar_index 0); call this out explicitly.
 */
export function sparGroupLabel(
  group: "front" | "rear" | "reinforcement",
): string {
  switch (group) {
    case "front":
      return "Front (main spar · index 0)";
    case "rear":
      return "Rear (torsion spar · index 1)";
    case "reinforcement":
      return "Root reinforcement";
  }
}

/**
 * Human label for a joint type between/at spar pieces.
 * Maps the backend's terse tokens to a readable phrase, falling back to the
 * raw token for anything unknown.
 */
export function jointLabel(joint: string | null | undefined): string {
  if (joint == null || joint === "") return "Continuous";
  switch (joint) {
    case "continuous":
      return "Continuous";
    case "telescoping":
      return "Telescoping";
    case "bent-pin":
      return "Bent-pin";
    case "reinforcement+joiner":
      return "Reinforcement + joiner";
    default:
      return joint;
  }
}

/**
 * One-line dimension summary for a buildable piece:
 * "OD 28.8 × ID 24.0 (wall 2.4) × L 750 mm".
 * Wall is computed from OD/ID when the piece's wall is absent.
 */
export function pieceDimsLabel(piece: SparPieceOut): string {
  const od = mToMm(piece.outer_d);
  const id = mToMm(piece.inner_d);
  const wall =
    piece.wall != null && Number.isFinite(piece.wall)
      ? piece.wall
      : (piece.outer_d - piece.inner_d) / 2;
  const wallStr = mToMm(wall);
  // length is the run-length along spare_vector; not on the piece schema, so
  // pieces show OD/ID/wall only (length lives on the planned-spare preview).
  return `OD ${od} × ID ${id} (wall ${wallStr}) mm`;
}

// ---- Insert-preview: REPLACE warning ---------------------------------------

/**
 * The set of target segment indices a planned insert touches, sorted.
 * Committing REPLACES every existing spar in these segments, so the preview
 * must warn the user about exactly these segments.
 */
export function touchedSegments(planned: PlannedSpareOut[]): number[] {
  const set = new Set<number>();
  for (const p of planned) set.add(p.segment_index);
  return [...set].sort((a, b) => a - b);
}

/**
 * The REPLACE warning sentence for the preview, or null when nothing is
 * touched. English UI per project convention.
 */
export function replaceWarning(planned: PlannedSpareOut[]): string | null {
  const segs = touchedSegments(planned);
  if (segs.length === 0) return null;
  const list = segs.join(", ");
  const noun = segs.length === 1 ? "segment" : "segments";
  return `This replaces existing spars in ${noun} ${list}.`;
}
