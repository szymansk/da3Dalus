/**
 * Unit tests for the spar-plan pure helpers (gh-1050).
 */
import { describe, it, expect } from "vitest";
import {
  buildMomentsFromLoads,
  mToMm,
  sparGroupLabel,
  jointLabel,
  pieceDimsLabel,
  noSparRegionLabel,
  touchedSegments,
  replaceWarning,
  pieceExtentLabel,
  pieceJointLabel,
  splitNote,
  snapshotNote,
  formatXOverChord,
  pieceXcLabel,
  groupXcSuffix,
} from "@/lib/sparPlanHelpers";
import type { SpanwiseLoadsResult } from "@/hooks/useSpanwiseLoads";
import type { PlannedSpareOut, SparPieceOut } from "@/hooks/useSparPlan";

function loads(): SpanwiseLoadsResult {
  return {
    alpha: 2,
    beta: 0,
    velocity_mps: 30,
    altitude_m: 0,
    dynamic_pressure_Pa: 551,
    surfaces: [
      {
        surface_name: "Main Wing",
        starboard: [
          { y_m: 0.0, chord_m: 0.3, shear_N: 100, bending_moment_Nm: 200 },
          { y_m: 0.5, chord_m: 0.25, shear_N: 50, bending_moment_Nm: 80 },
          { y_m: 1.0, chord_m: 0.2, shear_N: 0, bending_moment_Nm: 0 },
        ],
        port: [],
        root_shear_N_starboard: 100,
        root_shear_N_port: 100,
        root_bending_moment_Nm_starboard: 200,
        root_bending_moment_Nm_port: 200,
      },
    ],
  };
}

describe("buildMomentsFromLoads", () => {
  it("normalises y to a 0..1 span fraction and uses |M|", () => {
    const m = buildMomentsFromLoads(loads());
    expect(m).not.toBeNull();
    expect(m!).toHaveLength(3);
    expect(m![0]).toEqual({ y_span: 0, bending_moment_Nm: 200 });
    expect(m![1]).toEqual({ y_span: 0.5, bending_moment_Nm: 80 });
    expect(m![2]).toEqual({ y_span: 1, bending_moment_Nm: 0 });
  });

  it("returns null when there are no surfaces", () => {
    expect(buildMomentsFromLoads(null)).toBeNull();
    expect(buildMomentsFromLoads({ ...loads(), surfaces: [] })).toBeNull();
  });

  it("returns null when the span is degenerate (all y=0)", () => {
    const l = loads();
    l.surfaces[0].starboard = [
      { y_m: 0, chord_m: 0.3, shear_N: 0, bending_moment_Nm: 10 },
    ];
    expect(buildMomentsFromLoads(l)).toBeNull();
  });
});

describe("formatting helpers", () => {
  it("mToMm converts metres to millimetres", () => {
    expect(mToMm(0.0288)).toBe("28.8");
    expect(mToMm(0.75, 0)).toBe("750");
  });

  it("sparGroupLabel marks the front as main spar index 0", () => {
    expect(sparGroupLabel("front")).toContain("main spar");
    expect(sparGroupLabel("front")).toContain("0");
    expect(sparGroupLabel("rear")).toContain("Rear");
    expect(sparGroupLabel("reinforcement")).toContain("reinforcement");
  });

  it("jointLabel maps tokens to readable phrases", () => {
    expect(jointLabel(null)).toBe("Continuous");
    expect(jointLabel("telescoping")).toBe("Telescoping");
    expect(jointLabel("bent-pin")).toBe("Bent-pin");
    expect(jointLabel("reinforcement+joiner")).toBe("Reinforcement + joiner");
    expect(jointLabel("weird")).toBe("weird");
  });

  it("pieceDimsLabel shows OD, ID and computed wall in mm", () => {
    const piece: SparPieceOut = {
      role: "front",
      spare_origin: [0, 0, 0],
      spare_vector: [0, 1, 0],
      outer_d: 0.0288,
      inner_d: 0.024,
      wall: 0.0024,
      shape: "tube",
      governing_y: 0,
      x_over_chord: 0.3,
      y_start: 0,
      y_end: 0.75,
      utilisation: 0.5,
      joint_to_next: null,
      feasible: true,
      infeasibility_reason: null,
    };
    const label = pieceDimsLabel(piece);
    expect(label).toContain("OD 28.8");
    expect(label).toContain("ID 24.0");
    expect(label).toContain("wall 2.4");
  });

  it("pieceDimsLabel computes wall from OD/ID when wall missing", () => {
    const piece = {
      role: "front",
      spare_origin: [0, 0, 0],
      spare_vector: [0, 1, 0],
      outer_d: 0.02,
      inner_d: 0.01,
      shape: "tube",
      governing_y: 0,
      utilisation: 0.5,
      joint_to_next: null,
      feasible: true,
      infeasibility_reason: null,
    } as unknown as SparPieceOut;
    expect(pieceDimsLabel(piece)).toContain("wall 5.0");
  });
});

// gh-1060: spanwise extent + telescoping joint + split / snapshot notes -------

function gh1060Piece(over: Partial<SparPieceOut>): SparPieceOut {
  return {
    role: "front",
    spare_origin: [0, 0, 0],
    spare_vector: [0, 1, 0],
    outer_d: 0.0288,
    inner_d: 0.024,
    wall: 0.0024,
    shape: "tube",
    governing_y: 0,
    x_over_chord: 0.3,
    utilisation: 0.5,
    joint_to_next: null,
    feasible: true,
    infeasibility_reason: null,
    y_start: 0,
    y_end: 0.75,
    ...over,
  } as SparPieceOut;
}

describe("pieceExtentLabel (gh-1060)", () => {
  const p = gh1060Piece;

  it("shows the spanwise extent in mm (root=0)", () => {
    expect(pieceExtentLabel(p({ y_start: 0, y_end: 0.75 }))).toBe(
      "span 0 → 750 mm",
    );
  });

  it("rounds extents to whole mm", () => {
    expect(pieceExtentLabel(p({ y_start: 0.75, y_end: 1.2 }))).toBe(
      "span 750 → 1200 mm",
    );
  });
});

describe("pieceJointLabel (gh-1060)", () => {
  const p = gh1060Piece;

  it("shows the telescoping joint position from the next piece's y_start", () => {
    const piece = p({ joint_to_next: "telescoping", y_end: 0.75 });
    const next = p({ y_start: 0.7 }); // overlap rootward → joint = next.y_start
    expect(pieceJointLabel(piece, next)).toBe("Telescoping @ 700 mm");
  });

  it("falls back to the readable joint label when there is a next piece but no telescoping", () => {
    const piece = p({ joint_to_next: "bent-pin" });
    const next = p({ y_start: 0.9 });
    expect(pieceJointLabel(piece, next)).toBe("Bent-pin @ 900 mm");
  });

  it("shows 'to tip — no joint' for the last piece", () => {
    const piece = p({ joint_to_next: null });
    expect(pieceJointLabel(piece, undefined)).toBe("to tip — no joint");
  });
});

describe("splitNote (gh-1060)", () => {
  it("returns null when there is no split (single-piece front spar)", () => {
    expect(splitNote(null)).toBeNull();
    expect(splitNote([])).toBeNull();
    expect(splitNote([0.75])).toBeNull(); // single sub-segment = no split
  });

  it("describes the split with sub-segment count + lengths in mm", () => {
    const note = splitNote([0.75, 0.45]);
    expect(note).toContain("Main spar telescopes");
    expect(note).toContain("split into 2 sub-segments");
    expect(note).toContain("750");
    expect(note).toContain("450");
    expect(note).toContain("snapshot");
  });
});

describe("snapshotNote (gh-1060)", () => {
  it("returns null when there is no snapshot id", () => {
    expect(snapshotNote(null)).toBeNull();
    expect(snapshotNote(undefined)).toBeNull();
  });

  it("formats the snapshot id", () => {
    expect(snapshotNote(42)).toBe("Snapshot #42 created");
  });
});

// gh-1072: chordwise position (% chord) of each spar -------------------------

describe("formatXOverChord (gh-1072)", () => {
  it("renders a 0..1 fraction as a whole-percent chord", () => {
    expect(formatXOverChord(0.3)).toBe("30% c");
    expect(formatXOverChord(0.62)).toBe("62% c");
  });

  it("rounds to a whole percent", () => {
    expect(formatXOverChord(0.305)).toBe("31% c");
    expect(formatXOverChord(0.624)).toBe("62% c");
  });
});

describe("pieceXcLabel (gh-1072)", () => {
  const p = gh1060Piece;

  it("shows the piece's chordwise position as a percent", () => {
    expect(pieceXcLabel(p({ x_over_chord: 0.3 }))).toBe("@ 30% c");
    expect(pieceXcLabel(p({ x_over_chord: 0.62 }))).toBe("@ 62% c");
  });
});

describe("groupXcSuffix (gh-1072)", () => {
  const p = gh1060Piece;

  it("returns a single suffix when every piece shares the same x/c", () => {
    const pieces = [p({ x_over_chord: 0.3 }), p({ x_over_chord: 0.3 })];
    expect(groupXcSuffix(pieces)).toBe(" · @ 30% c");
  });

  it("returns null when the x/c varies between pieces (shown per piece)", () => {
    const pieces = [p({ x_over_chord: 0.3 }), p({ x_over_chord: 0.4 })];
    expect(groupXcSuffix(pieces)).toBeNull();
  });

  it("returns null for an empty group", () => {
    expect(groupXcSuffix([])).toBeNull();
  });
});

// gh-1075: shape-aware pieceDimsLabel + joiner joint label -----------------

describe("pieceDimsLabel — shape-aware (gh-1075)", () => {
  function makePiece(overrides: Partial<SparPieceOut>): SparPieceOut {
    return {
      role: "front",
      spare_origin: [0, 0, 0],
      spare_vector: [0, 1, 0],
      outer_d: 0.0288,
      inner_d: 0.024,
      wall: 0.0024,
      shape: "tube",
      governing_y: 0,
      x_over_chord: 0.3,
      y_start: 0,
      y_end: 0.75,
      utilisation: 0.5,
      joint_to_next: null,
      feasible: true,
      infeasibility_reason: null,
      ...overrides,
    };
  }

  it("tube — byte-identical to previous label (regression guard)", () => {
    const piece = makePiece({ shape: "tube", outer_d: 0.0288, inner_d: 0.024, wall: 0.0024 });
    expect(pieceDimsLabel(piece)).toBe("OD 28.8 × ID 24.0 (wall 2.4) mm");
  });

  it("rod — shows only Ø <d> mm, no ID, no wall fragment", () => {
    const piece = makePiece({ shape: "rod", outer_d: 0.008, inner_d: 0, wall: 0.004 });
    expect(pieceDimsLabel(piece)).toBe("Ø 8.0 mm");
    expect(pieceDimsLabel(piece)).not.toContain("ID");
    expect(pieceDimsLabel(piece)).not.toContain("wall");
  });

  it("rod — 'ID 0' must never appear", () => {
    const piece = makePiece({ shape: "rod", outer_d: 0.012, inner_d: 0, wall: 0 });
    expect(pieceDimsLabel(piece)).not.toContain("ID 0");
    expect(pieceDimsLabel(piece)).not.toContain("wall 0");
  });

  it("unknown shape — graceful fallback: exact Ø label, never blank or crash", () => {
    // 'hexagonal' is genuinely unrecognised — not a known deferred shape.
    // Must produce "Ø 15.0 mm" (outer_d only), never blank.
    const piece = makePiece({ shape: "hexagonal", outer_d: 0.015, inner_d: 0, wall: 0 });
    expect(pieceDimsLabel(piece)).toBe("Ø 15.0 mm");
  });

  it("capped shape (deferred to #1080) — falls back to Ø form, no b×h invented", () => {
    // rectangular/capped lack width/height fields in SparPieceOut; must not
    // fabricate b×h from outer_d. Graceful Ø fallback is correct for B2.
    const piece = makePiece({ shape: "capped", outer_d: 0.015, inner_d: 0.010, wall: 0.0025 });
    expect(pieceDimsLabel(piece)).toBe("Ø 15.0 mm");
    expect(pieceDimsLabel(piece)).not.toContain("ID");
  });
});

describe("jointLabel — joiner token (gh-1075)", () => {
  it("maps 'joiner' to 'Joiner'", () => {
    expect(jointLabel("joiner")).toBe("Joiner");
  });

  it("'telescoping' still maps to 'Telescoping' (switch-order regression guard)", () => {
    expect(jointLabel("telescoping")).toBe("Telescoping");
  });

  it("falling-back unknown token returns the token itself", () => {
    expect(jointLabel("weird-token")).toBe("weird-token");
  });
});

describe("touchedSegments + replaceWarning", () => {
  function planned(seg: number): PlannedSpareOut {
    return {
      segment_index: seg,
      spar_index: 0,
      role: "front",
      spare_support_dimension_width: 0.02,
      spare_support_dimension_height: 0.02,
      spare_length: 0.5,
      outer_d: 0.02,
      inner_d: 0.0,
      spare_origin: [0, 0, 0],
      spare_vector: [0, 1, 0],
      joint_note: null,
      feasible: true,
    };
  }

  it("returns sorted unique segment indices", () => {
    expect(touchedSegments([planned(2), planned(0), planned(2), planned(1)])).toEqual([
      0, 1, 2,
    ]);
  });

  it("replaceWarning lists touched segments (plural)", () => {
    expect(replaceWarning([planned(0), planned(1)])).toBe(
      "This replaces existing spars in segments 0, 1.",
    );
  });

  it("replaceWarning is singular for one segment", () => {
    expect(replaceWarning([planned(3)])).toBe(
      "This replaces existing spars in segment 3.",
    );
  });

  it("replaceWarning is null when nothing is touched", () => {
    expect(replaceWarning([])).toBeNull();
    expect(touchedSegments([])).toEqual([]);
  });
});

// gh-1080: rectangular/capped dims in pieceDimsLabel + SparPieceOut fields ----

describe("pieceDimsLabel — rectangular/capped (gh-1080)", () => {
  function makePiece(overrides: Partial<SparPieceOut>): SparPieceOut {
    return {
      role: "front",
      spare_origin: [0, 0, 0],
      spare_vector: [0, 1, 0],
      outer_d: 0.015,
      inner_d: 0,
      wall: 0,
      shape: "rectangular",
      governing_y: 0,
      x_over_chord: 0.3,
      y_start: 0,
      y_end: 0.5,
      utilisation: 0.6,
      joint_to_next: null,
      feasible: true,
      infeasibility_reason: null,
      ...overrides,
    };
  }

  it("rectangular — shows b × h when width + height are present", () => {
    const piece = makePiece({
      shape: "rectangular",
      width: 0.005,
      height: 0.012,
    });
    const label = pieceDimsLabel(piece);
    // 5.0 × 12.0 mm
    expect(label).toBe("5.0 × 12.0 mm");
    expect(label).not.toContain("OD");
    expect(label).not.toContain("ID");
  });

  it("rectangular — falls back to Ø when width/height are absent (solver not yet populating)", () => {
    // The current solver does not populate width/height — this is the live state.
    const piece = makePiece({ shape: "rectangular", outer_d: 0.015 });
    expect(pieceDimsLabel(piece)).toBe("Ø 15.0 mm");
    expect(pieceDimsLabel(piece)).not.toContain("×");
  });

  it("rectangular — falls back to Ø when only width is present (height missing)", () => {
    const piece = makePiece({ shape: "rectangular", width: 0.005 });
    expect(pieceDimsLabel(piece)).toBe("Ø 15.0 mm");
  });

  it("capped — shows cap + H when cap_width + height are present", () => {
    const piece = makePiece({
      shape: "capped",
      cap_width: 0.008,
      height: 0.015,
    });
    const label = pieceDimsLabel(piece);
    expect(label).toContain("8.0");
    expect(label).toContain("15.0");
    expect(label).not.toContain("OD");
    expect(label).not.toContain("ID");
  });

  it("capped — falls back to Ø when cap_width/height are absent", () => {
    const piece = makePiece({ shape: "capped", outer_d: 0.015 });
    expect(pieceDimsLabel(piece)).toBe("Ø 15.0 mm");
  });

  it("tube regression — still byte-identical after rectangular/capped additions", () => {
    const piece = makePiece({
      shape: "tube",
      outer_d: 0.0288,
      inner_d: 0.024,
      wall: 0.0024,
    });
    expect(pieceDimsLabel(piece)).toBe("OD 28.8 × ID 24.0 (wall 2.4) mm");
  });

  it("rod regression — still Ø only after rectangular/capped additions", () => {
    const piece = makePiece({ shape: "rod", outer_d: 0.008, inner_d: 0, wall: 0 });
    expect(pieceDimsLabel(piece)).toBe("Ø 8.0 mm");
  });
});

// gh-1076: pieceDimsLabel — thin-wall tube must never show "wall 0" ----------
// Reuses gh1060Piece (defined above) to avoid a duplicate factory.

describe("pieceDimsLabel — thin-wall tube (gh-1076)", () => {
  const p = gh1060Piece;

  it("tube with sub-0.1 mm wall (OD>0) never shows 'wall 0' or 'wall 0.0'", () => {
    // OD 10 mm, ID 9.96 mm → wall = 0.02 mm → rounds to 0.0 at 1 decimal → must NOT show "wall 0.0"
    const piece = p({ outer_d: 0.010, inner_d: 0.00996, wall: 0.00002 });
    const label = pieceDimsLabel(piece);
    expect(label).not.toContain("wall 0.0");
    expect(label).not.toContain("wall 0)");
    // Must use the sub-precision marker instead
    expect(label).toContain("<0.1");
  });

  it("tube with wall that rounds to 0.0 (from OD/ID fallback) uses <0.1 marker", () => {
    // wall field absent; computed from OD/ID: (0.010 - 0.00996)/2 = 0.00002 m = 0.02 mm → rounds to 0.0
    const piece = {
      role: "front",
      spare_origin: [0, 0, 0],
      spare_vector: [0, 1, 0],
      outer_d: 0.010,
      inner_d: 0.00996,
      shape: "tube",
      governing_y: 0,
      x_over_chord: 0.3,
      y_start: 0,
      y_end: 0.5,
      utilisation: 0.5,
      joint_to_next: null,
      feasible: true,
      infeasibility_reason: null,
    } as unknown as SparPieceOut;
    const label = pieceDimsLabel(piece);
    expect(label).not.toContain("wall 0.0");
    expect(label).toContain("<0.1");
  });

  it("normal tube (OD 28.8 × ID 24.0, wall 2.4 mm) is byte-identical to before (regression)", () => {
    const piece = p({ outer_d: 0.0288, inner_d: 0.024, wall: 0.0024 });
    expect(pieceDimsLabel(piece)).toBe("OD 28.8 × ID 24.0 (wall 2.4) mm");
  });

  it("tube with wall exactly 0.1 mm renders '0.1' (boundary — not <0.1)", () => {
    // wall = 0.0001 m = 0.1 mm — rounds to "0.1", NOT sub-precision
    const piece = p({ outer_d: 0.010, inner_d: 0.0098, wall: 0.0001 });
    const label = pieceDimsLabel(piece);
    expect(label).toContain("wall 0.1");
    expect(label).not.toContain("<0.1");
  });
});

// gh-1076: noSparRegionLabel ---------------------------------------------------

describe("noSparRegionLabel (gh-1076)", () => {
  it("returns null when fromY is null (spar runs all the way to the tip)", () => {
    expect(noSparRegionLabel(null, false)).toBeNull();
    expect(noSparRegionLabel(null, true)).toBeNull();
  });

  it("returns 'loads negligible' message when the whole span is negligible (piecesEmpty=true)", () => {
    const label = noSparRegionLabel(0, true);
    expect(label).not.toBeNull();
    expect(label).toContain("No spar required");
    expect(label).toContain("negligible");
  });

  it("returns span-position message when there is a normal no-spar tip region (piecesEmpty=false)", () => {
    // fromY = 0.75 m → 750 mm; spar runs to 750 mm then tip region is negligible
    const label = noSparRegionLabel(0.75, false);
    expect(label).not.toBeNull();
    expect(label).toContain("No spar required");
    expect(label).toContain("negligible");
    expect(label).toContain("750");
    expect(label).toContain("mm");
    expect(label).toContain("tip");
  });

  it("span position uses the same mToMm rounding as pieceExtentLabel (0 decimals for extents)", () => {
    // fromY = 0.7777 m → pieceExtentLabel uses mToMm(y, 0) → "778 mm"; we match that style
    const label = noSparRegionLabel(0.7777, false);
    expect(label).toContain("778");
  });

  it("piecesEmpty=false with fromY=0 (root=0 but not whole-span) renders the span position", () => {
    // This case doesn't happen in practice, but the contract is: piecesEmpty drives the message,
    // not fromY===0. With piecesEmpty=false, always show the span label.
    const label = noSparRegionLabel(0, false);
    expect(label).not.toBeNull();
    expect(label).toContain("0");
    expect(label).toContain("mm");
  });
});
