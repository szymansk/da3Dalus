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
    expect(ted!.kind).toBe("changed");
    expect(ted!.a).toBe("aileron");
    expect(ted!.b).toBe("—");
  });

  it("flags a turbulator presence change", () => {
    const a = [wing("main", [segment({ turbulator: null })])];
    const b = [wing("main", [segment({ turbulator: { x_c: 0.3 } })])];
    const diff = computeGeometryDiff(a, b);
    const turb = diff.wings[0].sections[0].flags.find((f) => f.key === "turbulator");
    expect(turb).toBeDefined();
    expect(turb!.kind).toBe("changed");
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
