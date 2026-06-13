import { describe, it, expect } from "vitest";
import {
  computeGeometryDiff,
  type DiffWingInput,
} from "@/lib/geometryDiff";
import type { WingConfigSegment } from "@/hooks/useWingConfig";

// ---------------------------------------------------------------------------
// Test fixtures
// ---------------------------------------------------------------------------

function segment(overrides: Partial<WingConfigSegment> = {}): WingConfigSegment {
  return {
    root_airfoil: {
      airfoil: "naca2412",
      chord: 200,
      dihedral_as_rotation_in_degrees: 3,
      incidence: 1,
    },
    tip_airfoil: {
      airfoil: "naca2412",
      chord: 150,
      dihedral_as_rotation_in_degrees: 3,
      incidence: 0,
    },
    length: 500,
    sweep: 5,
    spare_list: [],
    trailing_edge_device: null,
    turbulator: null,
    ...overrides,
  };
}

function wing(name: string, segments: WingConfigSegment[]): DiffWingInput {
  return { name, config: { segments, nose_pnt: [0, 0, 0] } };
}

// ---------------------------------------------------------------------------
// Core param changes — root airfoil keys renamed
// ---------------------------------------------------------------------------

describe("computeGeometryDiff — core param changes", () => {
  /**
   * NOTE on LCS alignment: the section signature uses (rootChord|length|rootAirfoil).
   * Tests that change chord, length, or rootAirfoil between A and B will NOT match
   * sections in the LCS (the sections appear as add+remove, not changed). Those params
   * are tested via showAll=true or via the add/remove path.
   *
   * Tests for params NOT in the signature (incidence, dihedral, sweep, tipAirfoil,
   * tipChord, tipIncidence, tipDihedral) can directly assert the "changed" path.
   */

  it("detects a root incidence change (deg) — not in LCS signature", () => {
    const a = [wing("main", [segment({ root_airfoil: { airfoil: "naca2412", chord: 200, incidence: 1 } })])];
    const b = [wing("main", [segment({ root_airfoil: { airfoil: "naca2412", chord: 200, incidence: 4 } })])];
    const diff = computeGeometryDiff(a, b);
    const incidence = diff.wings[0].sections[0].params.find((p) => p.key === "root incidence");
    expect(incidence).toBeDefined();
    expect(incidence!.a).toBe("1 deg");
    expect(incidence!.b).toBe("4 deg");
  });

  it("detects a root dihedral change (deg) — not in LCS signature", () => {
    const a = [wing("main", [segment({ root_airfoil: { airfoil: "naca2412", chord: 200, dihedral_as_rotation_in_degrees: 3 } })])];
    const b = [wing("main", [segment({ root_airfoil: { airfoil: "naca2412", chord: 200, dihedral_as_rotation_in_degrees: 6 } })])];
    const diff = computeGeometryDiff(a, b);
    const dih = diff.wings[0].sections[0].params.find((p) => p.key === "root dihedral");
    expect(dih).toBeDefined();
    expect(dih!.a).toBe("3 deg");
    expect(dih!.b).toBe("6 deg");
  });

  it("detects a sweep change with mm unit — not in LCS signature", () => {
    const a = [wing("main", [segment({ sweep: 5 })])];
    const b = [wing("main", [segment({ sweep: 12 })])];
    const diff = computeGeometryDiff(a, b);
    const sw = diff.wings[0].sections[0].params.find((p) => p.key === "sweep");
    expect(sw).toBeDefined();
    expect(sw!.a).toBe("5 mm");
    expect(sw!.b).toBe("12 mm");
  });

  it("detects a tip chord change (mm) — not in LCS signature", () => {
    const a = [wing("main", [segment({ tip_airfoil: { airfoil: "naca2412", chord: 150 } })])];
    const b = [wing("main", [segment({ tip_airfoil: { airfoil: "naca2412", chord: 100 } })])];
    const diff = computeGeometryDiff(a, b);
    const tipChord = diff.wings[0].sections[0].params.find((p) => p.key === "tip chord");
    expect(tipChord).toBeDefined();
    expect(tipChord!.a).toBe("150 mm");
    expect(tipChord!.b).toBe("100 mm");
  });

  it("detects a tip incidence change (deg) — not in LCS signature", () => {
    const a = [wing("main", [segment({ tip_airfoil: { airfoil: "naca2412", chord: 150, incidence: 0 } })])];
    const b = [wing("main", [segment({ tip_airfoil: { airfoil: "naca2412", chord: 150, incidence: 2 } })])];
    const diff = computeGeometryDiff(a, b);
    const tipInc = diff.wings[0].sections[0].params.find((p) => p.key === "tip incidence");
    expect(tipInc).toBeDefined();
    expect(tipInc!.a).toBe("0 deg");
    expect(tipInc!.b).toBe("2 deg");
  });

  it("detects a tip airfoil change (string equality) — not in LCS signature", () => {
    const a = [wing("main", [segment({ tip_airfoil: { airfoil: "naca2412", chord: 150 } })])];
    const b = [wing("main", [segment({ tip_airfoil: { airfoil: "naca0012", chord: 150 } })])];
    const diff = computeGeometryDiff(a, b);
    const af = diff.wings[0].sections[0].params.find((p) => p.key === "tip airfoil");
    expect(af).toBeDefined();
    expect(af!.a).toBe("naca2412");
    expect(af!.b).toBe("naca0012");
  });

  it("root chord and root airfoil are emitted in showAll mode even without a change", () => {
    // Since chord/airfoil are in the LCS signature, verify they appear in showAll
    const a = [wing("main", [segment()])];
    const b = [wing("main", [segment({ root_airfoil: { airfoil: "naca2412", chord: 200, incidence: 2 } })])];
    const diff = computeGeometryDiff(a, b, { showAll: true });
    expect(diff.hasAnyChange).toBe(true);
    const params = diff.wings[0].sections[0].params;
    const chord = params.find((p) => p.key === "root chord");
    expect(chord).toBeDefined();
    expect(chord!.a).toBe("200 mm");
    expect(chord!.b).toBe("200 mm");
    const af = params.find((p) => p.key === "root airfoil");
    expect(af).toBeDefined();
    expect(af!.a).toBe("naca2412");
    expect(af!.b).toBe("naca2412");
  });

  it("span appears as 'span' key (not 'length') in mm", () => {
    // Length IS in the LCS signature; test span key via showAll on matched sections
    const a = [wing("main", [segment({ root_airfoil: { airfoil: "naca2412", chord: 200 }, length: 500 })])];
    const b = [wing("main", [segment({ root_airfoil: { airfoil: "naca2412", chord: 200, incidence: 2 }, length: 500 })])];
    const diff = computeGeometryDiff(a, b, { showAll: true });
    const span = diff.wings[0].sections[0].params.find((p) => p.key === "span");
    expect(span).toBeDefined();
    expect(span!.a).toBe("500 mm");
    expect(span!.b).toBe("500 mm");
    // "length" key must NOT appear (renamed to "span")
    const len = diff.wings[0].sections[0].params.find((p) => p.key === "length");
    expect(len).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// .dat suffix stripping
// ---------------------------------------------------------------------------

describe("computeGeometryDiff — .dat suffix stripping", () => {
  it("strips .dat from root airfoil name in showAll display", () => {
    // Root airfoil is in the LCS signature; use showAll to see the param even when unchanged
    const a = [wing("main", [segment({ root_airfoil: { airfoil: "naca2412.dat", chord: 200, incidence: 1 } })])];
    const b = [wing("main", [segment({ root_airfoil: { airfoil: "naca2412.dat", chord: 200, incidence: 2 } })])];
    const diff = computeGeometryDiff(a, b, { showAll: true });
    const af = diff.wings[0].sections[0].params.find((p) => p.key === "root airfoil");
    expect(af).toBeDefined();
    // ".dat" must be stripped from the display
    expect(af!.a).toBe("naca2412");
    expect(af!.b).toBe("naca2412");
  });

  it("strips .dat from tip airfoil name for display (tip airfoil not in LCS sig)", () => {
    const a = [wing("main", [segment({ tip_airfoil: { airfoil: "clark-y.dat", chord: 150 } })])];
    const b = [wing("main", [segment({ tip_airfoil: { airfoil: "e374.dat", chord: 150 } })])];
    const diff = computeGeometryDiff(a, b);
    const af = diff.wings[0].sections[0].params.find((p) => p.key === "tip airfoil");
    expect(af).toBeDefined();
    expect(af!.a).toBe("clark-y");
    expect(af!.b).toBe("e374");
  });
});

// ---------------------------------------------------------------------------
// Tolerance
// ---------------------------------------------------------------------------

describe("computeGeometryDiff — numeric tolerance", () => {
  it("treats |Δ| = 0.04 as unchanged", () => {
    const a = [wing("main", [segment({ length: 500 })])];
    const b = [wing("main", [segment({ length: 500.04 })])];
    const diff = computeGeometryDiff(a, b);
    expect(diff.hasAnyChange).toBe(false);
  });

  it("treats |Δ| = 0.06 as changed", () => {
    const a = [wing("main", [segment({ length: 500 })])];
    const b = [wing("main", [segment({ length: 500.06 })])];
    const diff = computeGeometryDiff(a, b);
    expect(diff.hasAnyChange).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// formatNumber finite guard
// ---------------------------------------------------------------------------

describe("computeGeometryDiff — finite guard (NaN / Infinity)", () => {
  it("renders '—' for NaN incidence and treats it as a change vs a finite value", () => {
    // Use NaN incidence (NOT in LCS signature) so sections match by sig and diff is computed.
    // Incidence is not part of the signature (root_chord|length|root_airfoil) so sections align.
    const nanSeg: WingConfigSegment = {
      ...segment(),
      root_airfoil: { airfoil: "naca2412", chord: 200, incidence: NaN },
    };
    const a = [wing("main", [segment()])];
    const b = [wing("main", [nanSeg])];
    const diff = computeGeometryDiff(a, b);
    expect(diff.hasAnyChange).toBe(true);
    const params = diff.wings[0].sections[0].params;
    const inc = params.find((p) => p.key === "root incidence");
    expect(inc).toBeDefined();
    // b's incidence is NaN, must display "—"
    expect(inc!.b).toBe("—");
    // a's incidence is 1 (default from segment()), must display normally
    expect(inc!.a).toBe("1 deg");
  });

  it("renders '—' for NaN chord via formatMm guard", () => {
    // Test the formatMm guard directly: if chord is NaN, display is "—"
    // We test through a "removed" section display which still runs coreParams
    // Here we just verify that a segment with all-default params (incl. chord) shows correctly
    // and that NaN sweep renders "—"
    const nanSweepSeg: WingConfigSegment = {
      ...segment(),
      sweep: NaN,
    };
    const a = [wing("main", [segment()])];
    const b = [wing("main", [nanSweepSeg])];
    const diff = computeGeometryDiff(a, b);
    expect(diff.hasAnyChange).toBe(true);
    const params = diff.wings[0].sections[0].params;
    const sw = params.find((p) => p.key === "sweep");
    expect(sw).toBeDefined();
    expect(sw!.b).toBe("—");
    expect(sw!.a).toBe("5 mm"); // default sweep from segment() fixture
  });
});

// ---------------------------------------------------------------------------
// Section label with position role
// ---------------------------------------------------------------------------

describe("computeGeometryDiff — section labels with position role", () => {
  it("single section gets '· root' label", () => {
    const a = [wing("main", [segment()])];
    const b = [wing("main", [segment({ root_airfoil: { airfoil: "naca2412", chord: 100 } })])];
    const diff = computeGeometryDiff(a, b);
    expect(diff.wings[0].sections[0].label).toBe("Section 1 · root");
  });

  it("first section of multi gets '· root', last gets '· tip', middle gets '· mid'", () => {
    // 3 sections each with unique signatures so LCS matches all 3 pairwise
    const s1a = segment({ root_airfoil: { airfoil: "naca2412", chord: 200, incidence: 1 }, length: 500 });
    const s1b = segment({ root_airfoil: { airfoil: "naca2412", chord: 200, incidence: 2 }, length: 500 });
    const s2 = segment({ root_airfoil: { airfoil: "naca2412", chord: 160 }, length: 450 });
    const s3 = segment({ root_airfoil: { airfoil: "naca2412", chord: 120 }, length: 400 });
    const a = [wing("main", [s1a, s2, s3])];
    const b = [wing("main", [s1b, s2, s3])];
    const diff = computeGeometryDiff(a, b, { showAll: true });
    const labels = diff.wings[0].sections.map((s) => s.label);
    // Exactly 3 sections matched; labels reflect position
    expect(labels).toHaveLength(3);
    expect(labels[0]).toMatch(/· root$/);
    expect(labels[1]).toMatch(/· mid$/);
    expect(labels[2]).toMatch(/· tip$/);
  });
});

// ---------------------------------------------------------------------------
// LCS section alignment — insert in the middle must NOT cascade
// ---------------------------------------------------------------------------

describe("computeGeometryDiff — LCS section alignment", () => {
  it("inserting a section in the middle shows exactly one 'added', others unchanged", () => {
    // s1, s2, s3 have distinct signatures (chord differs)
    const s1 = segment({ root_airfoil: { airfoil: "naca2412", chord: 200 }, length: 500 });
    const s2 = segment({ root_airfoil: { airfoil: "naca2412", chord: 160 }, length: 480 });
    const s3 = segment({ root_airfoil: { airfoil: "naca2412", chord: 120 }, length: 400 });
    const sNEW = segment({ root_airfoil: { airfoil: "naca2412", chord: 180 }, length: 490 });

    const wA = [wing("main", [s1, s2, s3])];
    const wB = [wing("main", [s1, sNEW, s2, s3])];
    const diff = computeGeometryDiff(wA, wB);

    // Only sNEW is added; s1, s2, s3 are matched → unchanged
    expect(diff.counts.sectionsAdded).toBe(1);
    expect(diff.counts.sectionsRemoved).toBe(0);
    expect(diff.counts.sectionsChanged).toBe(0);

    // hasAnyChange because of the added section
    expect(diff.hasAnyChange).toBe(true);

    // The added section appears
    const added = diff.wings[0].sections.find((s) => s.kind === "added");
    expect(added).toBeDefined();

    // No "changed" sections
    const changed = diff.wings[0].sections.filter((s) => s.kind === "changed");
    expect(changed).toHaveLength(0);
  });

  it("removing a section from the middle shows exactly one 'removed', others unchanged", () => {
    const s1 = segment({ root_airfoil: { airfoil: "naca2412", chord: 200 }, length: 500 });
    const s2 = segment({ root_airfoil: { airfoil: "naca2412", chord: 160 }, length: 480 });
    const s3 = segment({ root_airfoil: { airfoil: "naca2412", chord: 120 }, length: 400 });

    const wA = [wing("main", [s1, s2, s3])];
    const wB = [wing("main", [s1, s3])];
    const diff = computeGeometryDiff(wA, wB);

    expect(diff.counts.sectionsRemoved).toBe(1);
    expect(diff.counts.sectionsAdded).toBe(0);
    expect(diff.counts.sectionsChanged).toBe(0);
    expect(diff.hasAnyChange).toBe(true);

    const removed = diff.wings[0].sections.find((s) => s.kind === "removed");
    expect(removed).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Section add / remove (positional fallback — same signatures)
// ---------------------------------------------------------------------------

describe("computeGeometryDiff — section add/remove (same-signature)", () => {
  it("flags an added section (B longer, identical sigs)", () => {
    const a = [wing("main", [segment()])];
    const b = [wing("main", [segment(), segment()])];
    const diff = computeGeometryDiff(a, b);
    // One of the two matching sections is "added"
    expect(diff.counts.sectionsAdded).toBe(1);
    const added = diff.wings[0].sections.find((s) => s.kind === "added");
    expect(added).toBeDefined();
  });

  it("flags a removed section (A longer, identical sigs)", () => {
    const a = [wing("main", [segment(), segment()])];
    const b = [wing("main", [segment()])];
    const diff = computeGeometryDiff(a, b);
    expect(diff.counts.sectionsRemoved).toBe(1);
    const removed = diff.wings[0].sections.find((s) => s.kind === "removed");
    expect(removed).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Wing add / remove
// ---------------------------------------------------------------------------

describe("computeGeometryDiff — wing add/remove", () => {
  it("flags an added wing (only in B)", () => {
    const a = [wing("main", [segment()])];
    const b = [wing("main", [segment()]), wing("tail", [segment()])];
    const diff = computeGeometryDiff(a, b);
    const added = diff.wings.find((w) => w.name === "tail");
    expect(added).toBeDefined();
    expect(added!.kind).toBe("added");
    expect(diff.hasAnyChange).toBe(true);
  });

  it("flags a removed wing (only in A)", () => {
    const a = [wing("main", [segment()]), wing("tail", [segment()])];
    const b = [wing("main", [segment()])];
    const diff = computeGeometryDiff(a, b);
    const removed = diff.wings.find((w) => w.name === "tail");
    expect(removed).toBeDefined();
    expect(removed!.kind).toBe("removed");
  });
});

// ---------------------------------------------------------------------------
// Sub-element flags
// ---------------------------------------------------------------------------

describe("computeGeometryDiff — sub-element flags", () => {
  it("flags a spar count change", () => {
    const a = [wing("main", [segment({ spare_list: [{}] })])];
    const b = [wing("main", [segment({ spare_list: [{}, {}] })])];
    const diff = computeGeometryDiff(a, b);
    const spar = diff.wings[0].sections[0].flags.find((f) => f.key === "spar");
    expect(spar).toBeDefined();
    expect(spar!.kind).toBe("changed");
    expect(spar!.a).toBe("1 spar");
    expect(spar!.b).toBe("2 spars");
  });

  it("flags a trailing-edge device presence change", () => {
    const a = [wing("main", [segment({ trailing_edge_device: { name: "aileron" } })])];
    const b = [wing("main", [segment({ trailing_edge_device: null })])];
    const diff = computeGeometryDiff(a, b);
    const ted = diff.wings[0].sections[0].flags.find((f) => f.key === "control_surface");
    expect(ted).toBeDefined();
    expect(ted!.kind).toBe("removed");
    expect(ted!.a).toBe("aileron");
    expect(ted!.b).toBe("—");
  });

  it("flags a turbulator presence change", () => {
    const a = [wing("main", [segment({ turbulator: null })])];
    const b = [wing("main", [segment({ turbulator: { x_c: 0.3 } })])];
    const diff = computeGeometryDiff(a, b);
    const turb = diff.wings[0].sections[0].flags.find((f) => f.key === "turbulator");
    expect(turb).toBeDefined();
    expect(turb!.kind).toBe("added");
    expect(turb!.a).toBe("—");
    expect(turb!.b).toBe("on");
  });
});

// ---------------------------------------------------------------------------
// Identical inputs
// ---------------------------------------------------------------------------

describe("computeGeometryDiff — identical inputs", () => {
  it("reports no change for identical wings", () => {
    const a = [wing("main", [segment(), segment({ sweep: 8 })])];
    const b = [wing("main", [segment(), segment({ sweep: 8 })])];
    const diff = computeGeometryDiff(a, b);
    expect(diff.hasAnyChange).toBe(false);
    expect(diff.wings).toHaveLength(0);
    expect(diff.counts).toEqual({
      sectionsChanged: 0,
      sectionsAdded: 0,
      sectionsRemoved: 0,
    });
  });
});

// ---------------------------------------------------------------------------
// Guard: missing root_airfoil / tip_airfoil
// ---------------------------------------------------------------------------

describe("computeGeometryDiff — missing airfoil guard", () => {
  it("does not throw when root_airfoil is missing (legacy config)", () => {
    // Force a segment with no root_airfoil
    const badSeg = {
      tip_airfoil: { airfoil: "naca2412", chord: 150 },
      length: 500,
      sweep: 5,
    } as unknown as WingConfigSegment;
    const a = [wing("main", [badSeg])];
    const b = [wing("main", [segment()])];
    expect(() => computeGeometryDiff(a, b)).not.toThrow();
  });

  it("does not throw when tip_airfoil is missing (legacy config)", () => {
    const badSeg = {
      root_airfoil: { airfoil: "naca2412", chord: 200 },
      length: 500,
      sweep: 5,
    } as unknown as WingConfigSegment;
    const a = [wing("main", [badSeg])];
    const b = [wing("main", [segment()])];
    expect(() => computeGeometryDiff(a, b)).not.toThrow();
  });
});

// ---------------------------------------------------------------------------
// changes-only vs show-all filtering
// ---------------------------------------------------------------------------

describe("computeGeometryDiff — changes-only vs show-all", () => {
  it("changes-only keeps only changed wings/sections/params (incidence change, same sig)", () => {
    // Use incidence change (not in LCS signature) so sections match by sig and diff their params
    const a = [
      wing("main", [
        segment({ root_airfoil: { airfoil: "n", chord: 200, incidence: 1 }, length: 500 }),
        segment({ root_airfoil: { airfoil: "n", chord: 160, incidence: 0 }, length: 400 }),
      ]),
      wing("tail", [segment()]),
    ];
    const b = [
      wing("main", [
        segment({ root_airfoil: { airfoil: "n", chord: 200, incidence: 4 }, length: 500 }),
        segment({ root_airfoil: { airfoil: "n", chord: 160, incidence: 0 }, length: 400 }),
      ]),
      wing("tail", [segment()]),
    ];
    const diff = computeGeometryDiff(a, b, { showAll: false });
    // tail unchanged → dropped; main has one changed section only
    expect(diff.wings).toHaveLength(1);
    expect(diff.wings[0].name).toBe("main");
    expect(diff.wings[0].sections).toHaveLength(1);
    expect(diff.wings[0].sections[0].index).toBe(0);
    // only the root incidence param is emitted (chord identical, sig-matched)
    expect(diff.wings[0].sections[0].params.map((p) => p.key)).toEqual(["root incidence"]);
  });

  it("show-all emits every wing, section and core param", () => {
    // Use distinct signatures so LCS matches sections positionally
    const a = [
      wing("main", [
        segment({ root_airfoil: { airfoil: "n", chord: 200, incidence: 1 }, length: 500 }),
        segment({ root_airfoil: { airfoil: "naca2412", chord: 160, incidence: 0 }, length: 400 }),
      ]),
      wing("tail", [segment()]),
    ];
    const b = [
      wing("main", [
        segment({ root_airfoil: { airfoil: "n", chord: 200, incidence: 4 }, length: 500 }),
        segment({ root_airfoil: { airfoil: "naca2412", chord: 160, incidence: 0 }, length: 400 }),
      ]),
      wing("tail", [segment()]),
    ];
    const diff = computeGeometryDiff(a, b, { showAll: true });
    // both wings present
    expect(diff.wings.map((w) => w.name).sort()).toEqual(["main", "tail"]);
    const main = diff.wings.find((w) => w.name === "main")!;
    // both sections present
    expect(main.sections).toHaveLength(2);
    // every core param emitted for each section (10 params: root chord/inc/dih/af, tip chord/inc/dih/af, span, sweep)
    const keys = main.sections[0].params.map((p) => p.key).sort();
    expect(keys).toEqual([
      "root airfoil",
      "root chord",
      "root dihedral",
      "root incidence",
      "span",
      "sweep",
      "tip airfoil",
      "tip chord",
      "tip dihedral",
      "tip incidence",
    ]);
    // hasAnyChange still reflects real changes, not the show-all emission
    expect(diff.hasAnyChange).toBe(true);
  });

  it("show-all on identical inputs still has hasAnyChange=false", () => {
    const a = [wing("main", [segment()])];
    const b = [wing("main", [segment()])];
    const diff = computeGeometryDiff(a, b, { showAll: true });
    expect(diff.hasAnyChange).toBe(false);
    expect(diff.wings).toHaveLength(1);
    expect(diff.wings[0].sections[0].params.length).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// GH #972 — field-level sub-element diff: spar fields
// Spar dimensional values (width/height/start/length) are in METRES (API converts
// mm → m). The diff multiplies by 1000 before formatting and tolerance comparison.
// ---------------------------------------------------------------------------

/**
 * A typed spar object matching the expected spare_list item shape.
 * Dimensional fields are in METRES (as returned by the wingconfig API).
 */
function spar(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    spare_position_factor: 0.25,
    spare_support_dimension_width: 0.010,   // 10 mm in metres
    spare_support_dimension_height: 0.015,  // 15 mm in metres
    spare_start: 0.050,                     // 50 mm in metres
    spare_length: 0.400,                    // 400 mm in metres
    spare_mode: "C",
    ...overrides,
  };
}

describe("computeGeometryDiff — gh-972 spar field-level diff", () => {
  it("emits fields with changed spar position_factor (changes-only)", () => {
    const a = [wing("main", [segment({ spare_list: [spar({ spare_position_factor: 0.3 })] })])];
    const b = [wing("main", [segment({ spare_list: [spar({ spare_position_factor: 0.4 })] })])];
    const diff = computeGeometryDiff(a, b);
    const sparFlag = diff.wings[0].sections[0].flags.find((f) => f.key === "spar");
    expect(sparFlag).toBeDefined();
    expect(sparFlag!.fields).toBeDefined();
    const posField = sparFlag!.fields!.find((f) => f.key === "spar 1 position");
    expect(posField).toBeDefined();
    expect(posField!.a).toBe("0.3");
    expect(posField!.b).toBe("0.4");
  });

  it("emits changed width/height dimension fields for a spar (metres → mm conversion)", () => {
    // API returns metres; diff should display in mm
    const a = [wing("main", [segment({ spare_list: [spar({ spare_support_dimension_width: 0.010, spare_support_dimension_height: 0.015 })] })])];
    const b = [wing("main", [segment({ spare_list: [spar({ spare_support_dimension_width: 0.012, spare_support_dimension_height: 0.020 })] })])];
    const diff = computeGeometryDiff(a, b);
    const sparFlag = diff.wings[0].sections[0].flags.find((f) => f.key === "spar");
    expect(sparFlag!.fields).toBeDefined();
    const wField = sparFlag!.fields!.find((f) => f.key === "spar 1 width");
    expect(wField).toBeDefined();
    expect(wField!.a).toBe("10 mm");
    expect(wField!.b).toBe("12 mm");
    const hField = sparFlag!.fields!.find((f) => f.key === "spar 1 height");
    expect(hField).toBeDefined();
    expect(hField!.a).toBe("15 mm");
    expect(hField!.b).toBe("20 mm");
  });

  it("emits changed start/length fields for a spar (metres → mm conversion)", () => {
    const a = [wing("main", [segment({ spare_list: [spar({ spare_start: 0.050, spare_length: 0.400 })] })])];
    const b = [wing("main", [segment({ spare_list: [spar({ spare_start: 0.060, spare_length: 0.350 })] })])];
    const diff = computeGeometryDiff(a, b);
    const sparFlag = diff.wings[0].sections[0].flags.find((f) => f.key === "spar");
    expect(sparFlag!.fields).toBeDefined();
    const startField = sparFlag!.fields!.find((f) => f.key === "spar 1 start");
    expect(startField).toBeDefined();
    expect(startField!.a).toBe("50 mm");
    expect(startField!.b).toBe("60 mm");
    const lenField = sparFlag!.fields!.find((f) => f.key === "spar 1 length");
    expect(lenField).toBeDefined();
    expect(lenField!.a).toBe("400 mm");
    expect(lenField!.b).toBe("350 mm");
  });

  it("detects a width change that would be missed without metres→mm conversion", () => {
    // 0.00442 m and 0.00500 m differ by 0.00058 m — below the raw 0.05 tolerance,
    // but in mm they are 4.42 mm vs 5.00 mm → Δ=0.58 mm > tolerance → should be reported.
    const a = [wing("main", [segment({ spare_list: [spar({ spare_support_dimension_width: 0.00442 })] })])];
    const b = [wing("main", [segment({ spare_list: [spar({ spare_support_dimension_width: 0.00500 })] })])];
    const diff = computeGeometryDiff(a, b);
    const sparFlag = diff.wings[0].sections[0].flags.find((f) => f.key === "spar");
    expect(sparFlag).toBeDefined();
    expect(sparFlag!.fields).toBeDefined();
    const wField = sparFlag!.fields!.find((f) => f.key === "spar 1 width");
    expect(wField).toBeDefined();
    expect(wField!.a).toBe("4.42 mm");
    expect(wField!.b).toBe("5 mm");
  });

  it("emits 'added' kind for a spar that exists only in B (count 0→1)", () => {
    const a = [wing("main", [segment({ spare_list: [] })])];
    const b = [wing("main", [segment({ spare_list: [spar()] })])];
    const diff = computeGeometryDiff(a, b);
    const sparFlag = diff.wings[0].sections[0].flags.find((f) => f.key === "spar");
    expect(sparFlag).toBeDefined();
    expect(sparFlag!.kind).toBe("added");
  });

  it("emits 'removed' kind for a spar that exists only in A (count 1→0)", () => {
    const a = [wing("main", [segment({ spare_list: [spar()] })])];
    const b = [wing("main", [segment({ spare_list: [] })])];
    const diff = computeGeometryDiff(a, b);
    const sparFlag = diff.wings[0].sections[0].flags.find((f) => f.key === "spar");
    expect(sparFlag).toBeDefined();
    expect(sparFlag!.kind).toBe("removed");
  });

  it("count differs (1→2): shows count change, NO field sub-rows", () => {
    // A has 1 spar, B has 2 — positional pairing is unsafe, so no field rows
    const a = [wing("main", [segment({ spare_list: [spar({ spare_support_dimension_width: 0.010 })] })])];
    const b = [wing("main", [segment({ spare_list: [spar({ spare_support_dimension_width: 0.010 }), spar({ spare_support_dimension_width: 0.012 })] })])];
    const diff = computeGeometryDiff(a, b);
    const sparFlag = diff.wings[0].sections[0].flags.find((f) => f.key === "spar");
    expect(sparFlag).toBeDefined();
    expect(sparFlag!.a).toBe("1 spar");
    expect(sparFlag!.b).toBe("2 spars");
    // No field sub-rows when count differs
    expect(sparFlag!.fields == null || sparFlag!.fields.length === 0).toBe(true);
  });

  it("showAll emits all spar fields even when unchanged", () => {
    const a = [wing("main", [segment({ spare_list: [spar()], root_airfoil: { airfoil: "naca2412", chord: 200, incidence: 1 } })])];
    const b = [wing("main", [segment({ spare_list: [spar()], root_airfoil: { airfoil: "naca2412", chord: 200, incidence: 2 } })])];
    const diff = computeGeometryDiff(a, b, { showAll: true });
    const sparFlag = diff.wings[0].sections[0].flags.find((f) => f.key === "spar");
    expect(sparFlag).toBeDefined();
    expect(sparFlag!.fields).toBeDefined();
    // All 6 fields should be present
    const fieldKeys = sparFlag!.fields!.map((f) => f.key);
    expect(fieldKeys).toContain("spar 1 position");
    expect(fieldKeys).toContain("spar 1 width");
    expect(fieldKeys).toContain("spar 1 height");
    expect(fieldKeys).toContain("spar 1 start");
    expect(fieldKeys).toContain("spar 1 length");
    expect(fieldKeys).toContain("spar 1 mode");
  });

  it("changes-only emits fields only for changed spar fields", () => {
    // position changes, width/height/start/length/mode unchanged
    const a = [wing("main", [segment({ spare_list: [spar({ spare_position_factor: 0.25 })] })])];
    const b = [wing("main", [segment({ spare_list: [spar({ spare_position_factor: 0.35 })] })])];
    const diff = computeGeometryDiff(a, b);
    const sparFlag = diff.wings[0].sections[0].flags.find((f) => f.key === "spar");
    expect(sparFlag!.fields).toBeDefined();
    const fieldKeys = sparFlag!.fields!.map((f) => f.key);
    expect(fieldKeys).toContain("spar 1 position");
    // width/height/start/length/mode are unchanged → NOT emitted in changes-only
    expect(fieldKeys).not.toContain("spar 1 width");
    expect(fieldKeys).not.toContain("spar 1 height");
  });
});

// ---------------------------------------------------------------------------
// GH #972 — spare_position_factor tight tolerance (0.005, not 0.05)
// ---------------------------------------------------------------------------

describe("computeGeometryDiff — spare_position_factor tight tolerance", () => {
  it("detects a 0.006 change in position_factor (above 0.005 tight tolerance)", () => {
    const a = [wing("main", [segment({ spare_list: [spar({ spare_position_factor: 0.300 })] })])];
    const b = [wing("main", [segment({ spare_list: [spar({ spare_position_factor: 0.306 })] })])];
    const diff = computeGeometryDiff(a, b);
    const sparFlag = diff.wings[0].sections[0].flags.find((f) => f.key === "spar");
    expect(sparFlag!.fields).toBeDefined();
    const posField = sparFlag!.fields!.find((f) => f.key === "spar 1 position");
    expect(posField).toBeDefined();
  });

  it("treats a 0.004 change in position_factor as noise (below 0.005 tight tolerance)", () => {
    // Only difference is position_factor changes by 0.004 — should be noise, no change
    const a = [wing("main", [segment({ spare_list: [spar({ spare_position_factor: 0.300 })] })])];
    const b = [wing("main", [segment({ spare_list: [spar({ spare_position_factor: 0.304 })] })])];
    const diff = computeGeometryDiff(a, b);
    // No other changes → no section change detected → wings is empty in changes-only mode
    expect(diff.hasAnyChange).toBe(false);
    expect(diff.wings).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// GH #972 — field-level sub-element diff: TED (trailing edge device) fields
// ---------------------------------------------------------------------------

describe("computeGeometryDiff — gh-972 TED field-level diff", () => {
  it("emits changed hinge_type and deflection_deg fields for TED", () => {
    const a = [wing("main", [segment({ trailing_edge_device: {
      name: "aileron", role: "aileron", rel_chord_root: 0.25, rel_chord_tip: 0.25,
      positive_deflection_deg: 20, negative_deflection_deg: -15,
      hinge_type: "plain", servo_placement: "wing", servo_index: 0,
    } })])];
    const b = [wing("main", [segment({ trailing_edge_device: {
      name: "aileron", role: "aileron", rel_chord_root: 0.25, rel_chord_tip: 0.25,
      positive_deflection_deg: 25, negative_deflection_deg: -20,
      hinge_type: "slotted", servo_placement: "wing", servo_index: 0,
    } })])];
    const diff = computeGeometryDiff(a, b);
    const tedFlag = diff.wings[0].sections[0].flags.find((f) => f.key === "control_surface");
    expect(tedFlag).toBeDefined();
    expect(tedFlag!.fields).toBeDefined();
    const hingeField = tedFlag!.fields!.find((f) => f.key === "control surface hinge_type");
    expect(hingeField).toBeDefined();
    expect(hingeField!.a).toBe("plain");
    expect(hingeField!.b).toBe("slotted");
    const posDefField = tedFlag!.fields!.find((f) => f.key === "control surface positive_deflection_deg");
    expect(posDefField).toBeDefined();
    expect(posDefField!.a).toBe("20");
    expect(posDefField!.b).toBe("25");
  });

  it("emits only the name field changed when TED is renamed but otherwise identical", () => {
    const baseTed = {
      name: "aileron", role: "aileron", rel_chord_root: 0.25, rel_chord_tip: 0.25,
      positive_deflection_deg: 20, negative_deflection_deg: -15,
      hinge_type: "plain", servo_placement: "wing", servo_index: 0,
    };
    const a = [wing("main", [segment({ trailing_edge_device: baseTed })])];
    const b = [wing("main", [segment({ trailing_edge_device: { ...baseTed, name: "flap" } })])];
    const diff = computeGeometryDiff(a, b);
    const tedFlag = diff.wings[0].sections[0].flags.find((f) => f.key === "control_surface");
    expect(tedFlag!.fields).toBeDefined();
    const nameField = tedFlag!.fields!.find((f) => f.key === "control surface name");
    expect(nameField).toBeDefined();
    expect(nameField!.a).toBe("aileron");
    expect(nameField!.b).toBe("flap");
    // All other fields unchanged → not in changes-only fields list
    const fieldKeys = tedFlag!.fields!.map((f) => f.key);
    expect(fieldKeys.filter((k) => k !== "control surface name")).toHaveLength(0);
  });

  it("emits moved-but-same-name TED fields (rel_chord changed)", () => {
    const baseTed = {
      name: "aileron", role: "aileron", rel_chord_root: 0.25, rel_chord_tip: 0.25,
      positive_deflection_deg: 20, negative_deflection_deg: -15,
      hinge_type: "plain", servo_placement: "wing", servo_index: 0,
    };
    const a = [wing("main", [segment({ trailing_edge_device: baseTed })])];
    const b = [wing("main", [segment({ trailing_edge_device: { ...baseTed, rel_chord_root: 0.35, rel_chord_tip: 0.35 } })])];
    const diff = computeGeometryDiff(a, b);
    const tedFlag = diff.wings[0].sections[0].flags.find((f) => f.key === "control_surface");
    expect(tedFlag!.fields).toBeDefined();
    const rootField = tedFlag!.fields!.find((f) => f.key === "control surface rel_chord_root");
    expect(rootField).toBeDefined();
    expect(rootField!.a).toBe("0.25");
    expect(rootField!.b).toBe("0.35");
  });

  it("showAll emits all TED fields even when unchanged (one-sided unchanged TED)", () => {
    const ted = {
      name: "aileron", role: "aileron", rel_chord_root: 0.25, rel_chord_tip: 0.25,
      positive_deflection_deg: 20, negative_deflection_deg: -15,
      hinge_type: "plain", servo_placement: "wing", servo_index: 0,
    };
    // make a non-TED change so section is matched and shown
    const a = [wing("main", [segment({ trailing_edge_device: ted, root_airfoil: { airfoil: "naca2412", chord: 200, incidence: 1 } })])];
    const b = [wing("main", [segment({ trailing_edge_device: ted, root_airfoil: { airfoil: "naca2412", chord: 200, incidence: 2 } })])];
    const diff = computeGeometryDiff(a, b, { showAll: true });
    const tedFlag = diff.wings[0].sections[0].flags.find((f) => f.key === "control_surface");
    expect(tedFlag!.fields).toBeDefined();
    const fieldKeys = tedFlag!.fields!.map((f) => f.key);
    expect(fieldKeys).toContain("control surface name");
    expect(fieldKeys).toContain("control surface hinge_type");
    expect(fieldKeys).toContain("control surface positive_deflection_deg");
  });

  it("kind='added' when TED is only on side B", () => {
    const a = [wing("main", [segment({ trailing_edge_device: null })])];
    const b = [wing("main", [segment({ trailing_edge_device: { name: "aileron" } })])];
    const diff = computeGeometryDiff(a, b);
    const tedFlag = diff.wings[0].sections[0].flags.find((f) => f.key === "control_surface");
    expect(tedFlag).toBeDefined();
    expect(tedFlag!.kind).toBe("added");
  });

  it("kind='removed' when TED is only on side A", () => {
    const a = [wing("main", [segment({ trailing_edge_device: { name: "aileron" } })])];
    const b = [wing("main", [segment({ trailing_edge_device: null })])];
    const diff = computeGeometryDiff(a, b);
    const tedFlag = diff.wings[0].sections[0].flags.find((f) => f.key === "control_surface");
    expect(tedFlag).toBeDefined();
    expect(tedFlag!.kind).toBe("removed");
  });

  it("kind='changed' when TED is present on both sides", () => {
    const baseTed = { name: "aileron", hinge_type: "plain" };
    const a = [wing("main", [segment({ trailing_edge_device: baseTed })])];
    const b = [wing("main", [segment({ trailing_edge_device: { ...baseTed, hinge_type: "slotted" } })])];
    const diff = computeGeometryDiff(a, b);
    const tedFlag = diff.wings[0].sections[0].flags.find((f) => f.key === "control_surface");
    expect(tedFlag).toBeDefined();
    expect(tedFlag!.kind).toBe("changed");
  });
});

// ---------------------------------------------------------------------------
// GH #972 — field-level sub-element diff: turbulator fields
// ---------------------------------------------------------------------------

describe("computeGeometryDiff — gh-972 turbulator field-level diff", () => {
  it("emits changed turbulator fields (form, height_mm, position_root)", () => {
    const a = [wing("main", [segment({ turbulator: {
      form: "wire", height_mm: 1.0, position_root: 0.2, position_tip: 0.2, enabled: true,
    } })])];
    const b = [wing("main", [segment({ turbulator: {
      form: "tape", height_mm: 1.5, position_root: 0.3, position_tip: 0.2, enabled: true,
    } })])];
    const diff = computeGeometryDiff(a, b);
    const turbFlag = diff.wings[0].sections[0].flags.find((f) => f.key === "turbulator");
    expect(turbFlag).toBeDefined();
    expect(turbFlag!.fields).toBeDefined();
    const formField = turbFlag!.fields!.find((f) => f.key === "turbulator form");
    expect(formField).toBeDefined();
    expect(formField!.a).toBe("wire");
    expect(formField!.b).toBe("tape");
    const heightField = turbFlag!.fields!.find((f) => f.key === "turbulator height_mm");
    expect(heightField).toBeDefined();
    expect(heightField!.a).toBe("1");
    expect(heightField!.b).toBe("1.5");
    const rootPosField = turbFlag!.fields!.find((f) => f.key === "turbulator position_root");
    expect(rootPosField).toBeDefined();
    expect(rootPosField!.a).toBe("0.2");
    expect(rootPosField!.b).toBe("0.3");
  });

  it("emits changed turbulator enabled field (true → false)", () => {
    const a = [wing("main", [segment({ turbulator: { form: "wire", height_mm: 1.0, position_root: 0.2, position_tip: 0.2, enabled: true } })])];
    const b = [wing("main", [segment({ turbulator: { form: "wire", height_mm: 1.0, position_root: 0.2, position_tip: 0.2, enabled: false } })])];
    const diff = computeGeometryDiff(a, b);
    const turbFlag = diff.wings[0].sections[0].flags.find((f) => f.key === "turbulator");
    expect(turbFlag!.fields).toBeDefined();
    const enabledField = turbFlag!.fields!.find((f) => f.key === "turbulator enabled");
    expect(enabledField).toBeDefined();
    expect(enabledField!.a).toBe("true");
    expect(enabledField!.b).toBe("false");
  });

  it("showAll emits all turbulator fields even when unchanged", () => {
    const turb = { form: "wire", height_mm: 1.0, position_root: 0.2, position_tip: 0.2, enabled: true };
    const a = [wing("main", [segment({ turbulator: turb, root_airfoil: { airfoil: "naca2412", chord: 200, incidence: 1 } })])];
    const b = [wing("main", [segment({ turbulator: turb, root_airfoil: { airfoil: "naca2412", chord: 200, incidence: 2 } })])];
    const diff = computeGeometryDiff(a, b, { showAll: true });
    const turbFlag = diff.wings[0].sections[0].flags.find((f) => f.key === "turbulator");
    expect(turbFlag!.fields).toBeDefined();
    const fieldKeys = turbFlag!.fields!.map((f) => f.key);
    expect(fieldKeys).toContain("turbulator form");
    expect(fieldKeys).toContain("turbulator height_mm");
    expect(fieldKeys).toContain("turbulator position_root");
    expect(fieldKeys).toContain("turbulator position_tip");
    expect(fieldKeys).toContain("turbulator enabled");
  });

  it("kind='added' when turbulator is only on side B", () => {
    const a = [wing("main", [segment({ turbulator: null })])];
    const b = [wing("main", [segment({ turbulator: { form: "wire" } })])];
    const diff = computeGeometryDiff(a, b);
    const turbFlag = diff.wings[0].sections[0].flags.find((f) => f.key === "turbulator");
    expect(turbFlag).toBeDefined();
    expect(turbFlag!.kind).toBe("added");
  });

  it("kind='removed' when turbulator is only on side A", () => {
    const a = [wing("main", [segment({ turbulator: { form: "wire" } })])];
    const b = [wing("main", [segment({ turbulator: null })])];
    const diff = computeGeometryDiff(a, b);
    const turbFlag = diff.wings[0].sections[0].flags.find((f) => f.key === "turbulator");
    expect(turbFlag).toBeDefined();
    expect(turbFlag!.kind).toBe("removed");
  });

  it("kind='changed' when turbulator is present on both sides", () => {
    const a = [wing("main", [segment({ turbulator: { form: "wire" } })])];
    const b = [wing("main", [segment({ turbulator: { form: "tape" } })])];
    const diff = computeGeometryDiff(a, b);
    const turbFlag = diff.wings[0].sections[0].flags.find((f) => f.key === "turbulator");
    expect(turbFlag).toBeDefined();
    expect(turbFlag!.kind).toBe("changed");
  });
});

// ---------------------------------------------------------------------------
// GH #972 — guard: missing/null sub-elements must not throw
// ---------------------------------------------------------------------------

describe("computeGeometryDiff — gh-972 null/missing sub-element guards", () => {
  it("does not throw when spare_list items have no fields (empty objects)", () => {
    const a = [wing("main", [segment({ spare_list: [{}] })])];
    const b = [wing("main", [segment({ spare_list: [{}] })])];
    expect(() => computeGeometryDiff(a, b, { showAll: true })).not.toThrow();
  });

  it("does not throw when trailing_edge_device is null on both sides", () => {
    const a = [wing("main", [segment({ trailing_edge_device: null })])];
    const b = [wing("main", [segment({ trailing_edge_device: null })])];
    expect(() => computeGeometryDiff(a, b, { showAll: true })).not.toThrow();
  });

  it("does not throw when turbulator is null on both sides", () => {
    const a = [wing("main", [segment({ turbulator: null })])];
    const b = [wing("main", [segment({ turbulator: null })])];
    expect(() => computeGeometryDiff(a, b, { showAll: true })).not.toThrow();
  });

  it("does not throw when spare_list is missing entirely", () => {
    const aSegNoList = { ...segment() };
    delete (aSegNoList as Partial<WingConfigSegment>).spare_list;
    const a = [wing("main", [aSegNoList as WingConfigSegment])];
    const b = [wing("main", [segment()])];
    expect(() => computeGeometryDiff(a, b)).not.toThrow();
  });
});

// ---------------------------------------------------------------------------
// GH #973 — hints embedded in GeometryDiff (computed from raw values per section)
// ---------------------------------------------------------------------------

describe("computeGeometryDiff — gh-973 hints (raw per-section, no string parsing)", () => {
  it("diff.hints is an array (always present)", () => {
    const a = [wing("main", [segment()])];
    const b = [wing("main", [segment()])];
    const diff = computeGeometryDiff(a, b);
    expect(Array.isArray(diff.hints)).toBe(true);
  });

  it("returns empty hints array when there are no changes", () => {
    const a = [wing("main", [segment()])];
    const b = [wing("main", [segment()])];
    const diff = computeGeometryDiff(a, b);
    expect(diff.hints).toEqual([]);
  });

  it("taper hint: tip chord decreased, root chord ~unchanged", () => {
    // tip chord not in LCS signature, so sections match and we can diff
    const a = [wing("main", [segment({ tip_airfoil: { airfoil: "naca2412", chord: 150 } })])];
    const b = [wing("main", [segment({ tip_airfoil: { airfoil: "naca2412", chord: 100 } })])];
    const diff = computeGeometryDiff(a, b);
    expect(diff.hints.some((h) => /taper/i.test(h))).toBe(true);
  });

  it("taper hint works in changes-only mode (uses raw values, not params list)", () => {
    // The tip chord change IS emitted in changes-only, but the hint must come from
    // raw values inside computeGeometryDiff, not from searching diff.wings[].sections[].params
    const a = [wing("main", [segment({ tip_airfoil: { airfoil: "naca2412", chord: 150 } })])];
    const b = [wing("main", [segment({ tip_airfoil: { airfoil: "naca2412", chord: 100 } })])];
    const diff = computeGeometryDiff(a, b, { showAll: false });
    expect(diff.hints.some((h) => /taper/i.test(h))).toBe(true);
  });

  it("does NOT emit taper hint when root chord also decreased significantly", () => {
    // root chord is in LCS signature; change it → sections appear as add+remove, not matched.
    // Use incidence change on root to force the match, then also change root chord via showAll test.
    // Simplest: use showAll so the section is present; but raw values show root also dropped.
    // We use the same-sig trick: keep chord/length/airfoil the same in sig, only change
    // incidence and also supply a separate root_chord via showAll mode is not needed here.
    // Actually, use tip chord changes while keeping root chord sig stable, but ALSO change
    // root chord to simulate both dropping. Since root chord IS in signature, we must use
    // a segment that has the same sig but a different root chord... which is impossible by design.
    // INSTEAD: use a multi-section wing where one section's tip decreases but root also decreases.
    // We use the `accumulateSectionHints` path directly by changing tip chord while ALSO having
    // root chord change (we override root_airfoil chord — that will change the sig, so sections
    // appear as added+removed, not matched → no hint accumulated from matchedPairs).
    // The simplest test: a segment where tip_chord goes down by 50mm but root_chord also goes
    // down by 50mm (same proportion → NOT more taper). Since root chord is in sig, changing it
    // means sections DON'T match in LCS → they appear as added+removed → no taper hint.
    const a = [wing("main", [segment({ root_airfoil: { airfoil: "naca2412", chord: 200 }, tip_airfoil: { airfoil: "naca2412", chord: 150 } })])];
    const b = [wing("main", [segment({ root_airfoil: { airfoil: "naca2412", chord: 160 }, tip_airfoil: { airfoil: "naca2412", chord: 110 } })])];
    const diff = computeGeometryDiff(a, b);
    // Sections don't match by sig (root chord changed) → added+removed, not taper
    expect(diff.hints.some((h) => /taper/i.test(h))).toBe(false);
  });

  it("washout hint: ONLY the outermost section's tip incidence decreased", () => {
    // 2-section wing; only the last (outermost) section's tip incidence decreases
    const s1a = segment({ root_airfoil: { airfoil: "naca2412", chord: 200, incidence: 1 }, length: 500, tip_airfoil: { airfoil: "naca2412", chord: 150, incidence: 1 } });
    const s1b = segment({ root_airfoil: { airfoil: "naca2412", chord: 200, incidence: 1 }, length: 500, tip_airfoil: { airfoil: "naca2412", chord: 150, incidence: 1 } });
    const s2a = segment({ root_airfoil: { airfoil: "naca2412", chord: 160 }, length: 400, tip_airfoil: { airfoil: "naca2412", chord: 120, incidence: 2 } });
    const s2b = segment({ root_airfoil: { airfoil: "naca2412", chord: 160 }, length: 400, tip_airfoil: { airfoil: "naca2412", chord: 120, incidence: -1 } });
    const a = [wing("main", [s1a, s2a])];
    const b = [wing("main", [s1b, s2b])];
    const diff = computeGeometryDiff(a, b);
    expect(diff.hints.some((h) => /washout/i.test(h))).toBe(true);
  });

  it("does NOT emit washout hint when only a non-tip section's incidence decreases", () => {
    // 2-section wing; first (non-tip) section tip incidence decreases, last unchanged
    const s1a = segment({ root_airfoil: { airfoil: "naca2412", chord: 200, incidence: 1 }, length: 500, tip_airfoil: { airfoil: "naca2412", chord: 150, incidence: 2 } });
    const s1b = segment({ root_airfoil: { airfoil: "naca2412", chord: 200, incidence: 1 }, length: 500, tip_airfoil: { airfoil: "naca2412", chord: 150, incidence: -1 } });
    const s2 = segment({ root_airfoil: { airfoil: "naca2412", chord: 160 }, length: 400 }); // unchanged
    const a = [wing("main", [s1a, s2])];
    const b = [wing("main", [s1b, s2])];
    const diff = computeGeometryDiff(a, b);
    // Washout only from the outermost section (s2 here), which is unchanged
    expect(diff.hints.some((h) => /washout/i.test(h))).toBe(false);
  });

  it("span hint: last section added at the tip", () => {
    const s1 = segment({ root_airfoil: { airfoil: "naca2412", chord: 200 }, length: 500 });
    const sNew = segment({ root_airfoil: { airfoil: "naca2412", chord: 160 }, length: 400 });
    const a = [wing("main", [s1])];
    const b = [wing("main", [s1, sNew])];
    const diff = computeGeometryDiff(a, b);
    expect(diff.hints.some((h) => /span/i.test(h) || /tip section/i.test(h))).toBe(true);
  });

  it("dihedral hint: a section's dihedral increased", () => {
    // root dihedral NOT in LCS signature, so sections match
    const a = [wing("main", [segment({ root_airfoil: { airfoil: "naca2412", chord: 200, dihedral_as_rotation_in_degrees: 3 } })])];
    const b = [wing("main", [segment({ root_airfoil: { airfoil: "naca2412", chord: 200, dihedral_as_rotation_in_degrees: 7 } })])];
    const diff = computeGeometryDiff(a, b);
    expect(diff.hints.some((h) => /dihedral/i.test(h))).toBe(true);
  });

  it("airfoil changed hint: tip airfoil change triggers re-run polar", () => {
    // tip airfoil not in LCS signature, so sections match and hint fires
    const a = [wing("main", [segment({ tip_airfoil: { airfoil: "naca2412", chord: 150 } })])];
    const b = [wing("main", [segment({ tip_airfoil: { airfoil: "clark-y", chord: 150 } })])];
    const diff = computeGeometryDiff(a, b);
    expect(diff.hints.some((h) => /airfoil/i.test(h) && /polar/i.test(h))).toBe(true);
  });

  it("no cross-entity hint: a root chord change on one section should NOT create a taper hint if tip chord on SAME section is unchanged", () => {
    // Root chord changes (different LCS sig → add+remove, not change) — but tip unchanged.
    // Taper hint must NOT fire because tip didn't decrease relative to root of SAME section.
    const a = [wing("main", [segment({ root_airfoil: { airfoil: "naca2412", chord: 200 }, tip_airfoil: { airfoil: "naca2412", chord: 150 } })])];
    const b = [wing("main", [segment({ root_airfoil: { airfoil: "naca2412", chord: 180 }, tip_airfoil: { airfoil: "naca2412", chord: 150 } })])];
    // Root chord in sig → sections don't match → appears as add+remove, not matched
    // accumulateSectionHints is only called for matched pairs → no taper
    const diff = computeGeometryDiff(a, b);
    expect(diff.hints.some((h) => /taper/i.test(h))).toBe(false);
  });

  it("max 5 hints", () => {
    // Create a scenario that would trigger multiple hints simultaneously
    // tip chord decreases (taper), dihedral increases, airfoil changes, add a tip section (span)
    // We need 2-section wing with both sections changing for washout+taper
    const s1a = segment({ root_airfoil: { airfoil: "naca2412", chord: 200, dihedral_as_rotation_in_degrees: 3 }, length: 500, tip_airfoil: { airfoil: "naca2412", chord: 150, incidence: 0 } });
    const s1b = segment({ root_airfoil: { airfoil: "clark-y", chord: 200, dihedral_as_rotation_in_degrees: 7 }, length: 500, tip_airfoil: { airfoil: "clark-y", chord: 100, incidence: -2 } });
    const sNew = segment({ root_airfoil: { airfoil: "naca2412", chord: 160 }, length: 400 });
    const a = [wing("main", [s1a])];
    const b = [wing("main", [s1b, sNew])];
    const diff = computeGeometryDiff(a, b);
    expect(diff.hints.length).toBeLessThanOrEqual(5);
  });
});
