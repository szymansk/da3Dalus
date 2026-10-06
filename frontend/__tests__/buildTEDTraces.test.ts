/**
 * gh-1163: a trailing-edge device over several segments is drawn along ONE
 * straight hinge line. Segment i runs from its rel_chord_root (section i) to
 * its own rel_chord_tip (section i+1).
 */
import { describe, it, expect } from "vitest";
import { buildTEDTraces } from "@/components/workbench/WingOutlineViewer";
import type { WingTraceCtx } from "@/components/workbench/WingOutlineViewer";
import type { XSec } from "@/hooks/useWings";

function xsec(y: number, chord: number, ted?: Record<string, unknown>): XSec {
  return {
    xyz_le: [0, y, 0],
    chord,
    twist: 0,
    airfoil: "naca0012",
    ...(ted ? { trailing_edge_device: ted } : {}),
  } as XSec;
}

function ctx(xsecs: XSec[]): WingTraceCtx {
  return { xsecs, airfoils: xsecs.map(() => null), dihedrals: xsecs.map(() => 0), selectedIdx: null };
}

// Unswept hinge at x = 0.10 on a surface tapering 0.20 -> 0.16 -> 0.12.
const TAPERED = [
  xsec(0, 0.2, { name: "elev", rel_chord_root: 0.5, rel_chord_tip: 0.625 }),
  xsec(0.25, 0.16, { name: "elev", rel_chord_root: 0.625, rel_chord_tip: 0.1 / 0.12 }),
  xsec(0.5, 0.12),
];

describe("buildTEDTraces", () => {
  it("draws every segment's hinge on the same straight line", () => {
    const traces = buildTEDTraces(ctx(TAPERED));
    // per TED segment: hinge line + outline
    const hinges = traces.filter((_, i) => i % 2 === 0);
    expect(hinges).toHaveLength(2);
    for (const h of hinges) {
      expect(h.x[0]).toBeCloseTo(0.1, 9);
      expect(h.x[1]).toBeCloseTo(0.1, 9);
    }
    expect(hinges[0].y).toEqual([0, 0.25]);
    expect(hinges[1].y).toEqual([0.25, 0.5]);
  });

  it("keeps the root fraction at the tip when rel_chord_tip is missing", () => {
    const traces = buildTEDTraces(ctx([xsec(0, 0.2, { name: "flap", rel_chord_root: 0.8 }), xsec(0.3, 0.1)]));
    expect(traces[0].x[0]).toBeCloseTo(0.16, 9);
    expect(traces[0].x[1]).toBeCloseTo(0.08, 9);
  });
});
