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
    // gh-1075: non-tube intermediate joint (solid rod, rectangular, capped —
    // shapes without a bore cannot telescope, so the solver emits 'joiner').
    case "joiner":
      return "Joiner";
    default:
      return joint;
  }
}

/**
 * One-line dimension summary for a buildable piece, branching on shape:
 *
 * - `tube` → "OD 28.8 × ID 24.0 (wall 2.4) mm"  (byte-identical to the
 *   pre-gh-1075 label — regression guard for the common case).
 * - `rod`  → "Ø 8.0 mm"  (no ID / wall — a solid rod has no bore, so both
 *   inner_d=0 and wall=d/2 are meaningless to a builder; gh-1075).
 * - anything else → graceful "Ø <od> mm" fallback (rectangular / capped /
 *   unknown — their b×h fields are deferred to #1080 and must not be faked).
 *
 * Wall is computed from OD/ID when the piece's `wall` field is absent.
 */
export function pieceDimsLabel(piece: SparPieceOut): string {
  const od = mToMm(piece.outer_d);

  if (piece.shape === "tube") {
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

  // rod and all other shapes: show outer diameter only.
  // rectangular / capped labels (b×h, cap_width) are deferred to #1080 — the
  // SparPieceOut schema carries no width/height fields yet, so we must not
  // invent numbers from outer_d.
  return `Ø ${od} mm`;
}

// ---- Built-spar spanwise extent + telescoping joint (gh-1060) ---------------

/**
 * The piece's spanwise extent in mm (root=0): "span 0 → 750 mm". Uses the
 * gh-1057 y_start/y_end fields. Extents are rounded to whole mm.
 */
export function pieceExtentLabel(piece: SparPieceOut): string {
  return `span ${mToMm(piece.y_start, 0)} → ${mToMm(piece.y_end, 0)} mm`;
}

/**
 * The joint label for a built piece. For an intermediate piece, the joint
 * position is the NEXT piece's y_start (the telescoping overlap region begins
 * there): e.g. "Telescoping @ 700 mm". The last piece (no next) runs to the
 * tip with no joint → "to tip — no joint".
 */
export function pieceJointLabel(
  piece: SparPieceOut,
  next: SparPieceOut | null | undefined,
): string {
  if (next == null) return "to tip — no joint";
  return `${jointLabel(piece.joint_to_next)} @ ${mToMm(next.y_start, 0)} mm`;
}

// ---- Built-spar chordwise position (% chord) (gh-1072) ----------------------

/**
 * Format a chordwise fraction (x/c, 0..1) as a whole-percent chord label,
 * e.g. 0.30 → "30% c". Rounded to the nearest percent (a sub-percent
 * difference between stations is not meaningful for placement display).
 */
export function formatXOverChord(xOverChord: number): string {
  return `${Math.round(xOverChord * 100)}% c`;
}

/**
 * Per-piece chordwise-position label, e.g. "@ 30% c". Used when the x/c
 * varies between pieces of a spar so each row carries its own position.
 */
export function pieceXcLabel(piece: SparPieceOut): string {
  return `@ ${formatXOverChord(piece.x_over_chord)}`;
}

/**
 * Group-level chordwise suffix appended to the spar group label when every
 * piece in the group shares the same (rounded) chordwise position, e.g.
 * " · @ 30% c". Returns null when the group is empty or the position varies
 * between pieces — in that case the per-piece {@link pieceXcLabel} is shown.
 */
export function groupXcSuffix(pieces: SparPieceOut[]): string | null {
  if (pieces.length === 0) return null;
  const first = Math.round(pieces[0].x_over_chord * 100);
  const constant = pieces.every(
    (p) => Math.round(p.x_over_chord * 100) === first,
  );
  if (!constant) return null;
  return ` · @ ${formatXOverChord(pieces[0].x_over_chord)}`;
}

// ---- Insert-preview: segment split + snapshot notes (gh-1060) ---------------

/**
 * A note describing the planned main-spar segment split, or null when there is
 * no split. A split exists only when the host segment is divided into >1
 * sub-segment (the main spar telescopes). Lengths are shown in mm and the note
 * mentions the auto-snapshot the commit takes.
 */
export function splitNote(
  plannedSegmentLengths: number[] | null | undefined,
): string | null {
  if (plannedSegmentLengths == null) return null;
  const n = plannedSegmentLengths.length;
  if (n <= 1) return null;
  const lengths = plannedSegmentLengths.map((l) => mToMm(l, 0)).join(", ");
  return (
    `Main spar telescopes → the segment will be split into ${n} sub-segments ` +
    `(lengths ${lengths} mm); a snapshot will be taken so you can revert.`
  );
}

/**
 * "Snapshot #N created" for a committed insert, or null when there is no
 * snapshot id (dry-run, or a non-destructive commit that took none).
 */
export function snapshotNote(
  snapshotId: number | null | undefined,
): string | null {
  if (snapshotId == null) return null;
  return `Snapshot #${snapshotId} created`;
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
