/**
 * Unit tests for buildTurbulatorTraces (WingOutlineViewer, gh-936).
 *
 * The function is a pure trace builder that needs only a WingTraceCtx
 * (no React, no DOM, no Plotly) — so we can test it directly.
 */
import { describe, it, expect } from "vitest";
import { buildTurbulatorTraces } from "@/components/workbench/WingOutlineViewer";
import type { WingTraceCtx } from "@/components/workbench/WingOutlineViewer";
import type { XSec } from "@/hooks/useWings";

// ── Helpers ───────────────────────────────────────────────────────

function makeXsec(overrides: Partial<XSec> = {}): XSec {
  return {
    xyz_le: [0, 0, 0],
    chord: 0.2,
    twist: 0,
    airfoil: "naca0012",
    ...overrides,
  };
}

function makeCtx(xsecs: XSec[], overrides: Partial<WingTraceCtx> = {}): WingTraceCtx {
  return {
    xsecs,
    airfoils: xsecs.map(() => null),
    dihedrals: xsecs.map(() => 0),
    selectedIdx: null,
    ...overrides,
  };
}

// ── Tests ─────────────────────────────────────────────────────────

describe("buildTurbulatorTraces", () => {
  it("returns empty array when xsecs list has fewer than 2 entries", () => {
    const ctx = makeCtx([makeXsec()]);
    expect(buildTurbulatorTraces(ctx)).toHaveLength(0);
  });

  it("returns empty array when no xsec has a turbulator", () => {
    const ctx = makeCtx([makeXsec(), makeXsec()]);
    expect(buildTurbulatorTraces(ctx)).toHaveLength(0);
  });

  it("returns empty array when turbulator is null", () => {
    const ctx = makeCtx([
      makeXsec({ turbulator: null }),
      makeXsec(),
    ]);
    expect(buildTurbulatorTraces(ctx)).toHaveLength(0);
  });

  it("returns one trace per segment that has a turbulator", () => {
    const ctx = makeCtx([
      makeXsec({ turbulator: { form: "zigzag", height_mm: 0.3, position_root: 0.1, enabled: true } }),
      makeXsec(),
    ]);
    const traces = buildTurbulatorTraces(ctx);
    expect(traces).toHaveLength(1);
  });

  it("each trace is a dotted scatter3d (markers) along the spanwise line", () => {
    const ctx = makeCtx([
      makeXsec({ turbulator: { form: "zigzag", height_mm: 0.3, position_root: 0.1, enabled: true } }),
      makeXsec({ xyz_le: [0, 0.3, 0], chord: 0.18, twist: 0, airfoil: "naca0012" }),
    ]);
    const [trace] = buildTurbulatorTraces(ctx);
    expect(trace.type).toBe("scatter3d");
    // Dotted appearance: rendered as markers (scatter3d lines cannot be dashed).
    expect(trace.mode).toBe("markers");
    // Evenly spaced dots root→tip (N + 1 points).
    expect(trace.x.length).toBeGreaterThan(2);
    expect(trace.y).toHaveLength(trace.x.length);
    expect(trace.z).toHaveLength(trace.x.length);
  });

  it("trace x-coordinates reflect position_root on root xsec", () => {
    // Root xsec at origin with chord 1.0, position_root 0.25
    // transformProfile([0.25],[0], chord=1, twist=0, xyz_le=[0,0,0], dih=0)
    // => x = 0 + 0.25*1 = 0.25
    const ctx = makeCtx([
      makeXsec({ xyz_le: [0, 0, 0], chord: 1.0, twist: 0,
        turbulator: { form: "zigzag", height_mm: 0.3, position_root: 0.25, enabled: true } }),
      makeXsec({ xyz_le: [0, 1, 0], chord: 1.0, twist: 0, airfoil: "naca0012" }),
    ]);
    const [trace] = buildTurbulatorTraces(ctx);
    expect(trace.x[0]).toBeCloseTo(0.25, 5);
  });

  it("uses position_tip for the tip station when set", () => {
    const ctx = makeCtx([
      makeXsec({ xyz_le: [0, 0, 0], chord: 1.0, twist: 0,
        turbulator: { form: "zigzag", height_mm: 0.3, position_root: 0.1, position_tip: 0.2, enabled: true } }),
      makeXsec({ xyz_le: [0, 1, 0], chord: 1.0, twist: 0, airfoil: "naca0012" }),
    ]);
    const [trace] = buildTurbulatorTraces(ctx);
    // Tip xsec: xyz_le=[0,1,0], chord=1, position_tip=0.2 → x = 0 + 0.2*1 = 0.2.
    // The tip station is the LAST dot of the strip.
    expect(trace.x.at(-1)).toBeCloseTo(0.2, 5);
  });

  it("falls back to position_root for tip when position_tip is not set", () => {
    const ctx = makeCtx([
      makeXsec({ xyz_le: [0, 0, 0], chord: 1.0, twist: 0,
        turbulator: { form: "zigzag", height_mm: 0.3, position_root: 0.15, enabled: true } }),
      makeXsec({ xyz_le: [0, 1, 0], chord: 1.0, twist: 0, airfoil: "naca0012" }),
    ]);
    const [trace] = buildTurbulatorTraces(ctx);
    // Tip uses position_root (0.15) as fallback → last dot at 0.15
    expect(trace.x.at(-1)).toBeCloseTo(0.15, 5);
  });

  it("falls back to position_root when position_tip is null", () => {
    const ctx = makeCtx([
      makeXsec({ xyz_le: [0, 0, 0], chord: 1.0, twist: 0,
        turbulator: { form: "zigzag", height_mm: 0.3, position_root: 0.12, position_tip: null, enabled: true } }),
      makeXsec({ xyz_le: [0, 1, 0], chord: 1.0, twist: 0, airfoil: "naca0012" }),
    ]);
    const [trace] = buildTurbulatorTraces(ctx);
    expect(trace.x.at(-1)).toBeCloseTo(0.12, 5);
  });

  it("skips segment when turbulator has no position_root", () => {
    const turb = { form: "zigzag", height_mm: 0.3, enabled: true } as unknown as import("@/hooks/useWings").Turbulator;
    // Cast to force missing position_root to undefined
    const ctx = makeCtx([
      makeXsec({ turbulator: turb }),
      makeXsec(),
    ]);
    // position_root is undefined → should skip
    expect(buildTurbulatorTraces(ctx)).toHaveLength(0);
  });

  it("handles multiple segments — only those with turbulators emit traces", () => {
    const ctx = makeCtx([
      makeXsec({ turbulator: { form: "dots", height_mm: 0.2, position_root: 0.1, enabled: true } }),
      makeXsec({ xyz_le: [0, 0.3, 0], chord: 0.18, twist: 0, airfoil: "naca0012" }), // no turbulator
      makeXsec({ xyz_le: [0, 0.6, 0], chord: 0.15, twist: 0, airfoil: "naca0012",
        turbulator: { form: "thread", height_mm: 0.4, position_root: 0.2, enabled: true } }),
      makeXsec({ xyz_le: [0, 0.9, 0], chord: 0.12, twist: 0, airfoil: "naca0012" }),
    ]);
    // segments 0 and 2 have turbulators; segment 1 does not
    const traces = buildTurbulatorTraces(ctx);
    expect(traces).toHaveLength(2);
  });

  it("terminal (last) xsec never emits a trace — loop stops at length-1", () => {
    // Even if the last xsec has a turbulator, i < xsecs.length - 1 prevents it
    const ctx = makeCtx([
      makeXsec(),
      makeXsec({ turbulator: { form: "zigzag", height_mm: 0.3, position_root: 0.1, enabled: true } }),
    ]);
    expect(buildTurbulatorTraces(ctx)).toHaveLength(0);
  });

  it("trace uses a distinct cyan marker colour (not the airfoil orange)", () => {
    const ctx = makeCtx([
      makeXsec({ turbulator: { form: "zigzag", height_mm: 0.3, position_root: 0.1, enabled: true } }),
      makeXsec(),
    ]);
    const [trace] = buildTurbulatorTraces(ctx);
    // COLOR_TURBULATOR = "#22D3EE" — bright cyan, deliberately far from the
    // airfoil orange (#FF8400) / TED green (#30A46C) / spar purple (#6E56CF).
    const color = (trace.marker.color as string).toUpperCase();
    expect(color).toBe("#22D3EE");
    expect(color).not.toBe("#FF8400");
  });

  it("draws the strip on the upper surface (z follows the airfoil upper ordinate)", () => {
    // Provide an airfoil whose upper surface at x/c=0.3 is well above the chord
    // line; the dots must sit at that height, not on the camber line (z=0).
    const upperAf = {
      x: [0, 0.3, 1], y: [0, 0.1, 0],
      upper_x: [0, 0.3, 1], upper_y: [0, 0.1, 0],
    };
    const ctx = makeCtx(
      [
        makeXsec({ chord: 1.0, turbulator: { form: "zigzag", height_mm: 0.3, position_root: 0.3, enabled: true } }),
        makeXsec({ xyz_le: [0, 1, 0], chord: 1.0 }),
      ],
      { airfoils: [upperAf, upperAf] as unknown as WingTraceCtx["airfoils"] },
    );
    const [trace] = buildTurbulatorTraces(ctx);
    // upper_y(0.3) = 0.1, chord 1 → z ≈ 0.1 (not 0)
    expect(trace.z[0]).toBeCloseTo(0.1, 5);
  });

  it("trace has showlegend: false and hoverinfo: skip", () => {
    const ctx = makeCtx([
      makeXsec({ turbulator: { form: "zigzag", height_mm: 0.3, position_root: 0.1, enabled: true } }),
      makeXsec(),
    ]);
    const [trace] = buildTurbulatorTraces(ctx);
    expect(trace.showlegend).toBe(false);
    expect(trace.hoverinfo).toBe("skip");
  });
});
