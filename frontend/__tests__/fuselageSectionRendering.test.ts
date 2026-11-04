/**
 * The three fuselage renderers (workbench viewer, import preview, section
 * SVG) and the import save all have to honour the lower-half exponent
 * `n_lower` (gh-1157). The pure builders are tested directly.
 */
import { describe, it, expect, vi, afterEach } from "vitest";

vi.mock("@/lib/fetcher", () => ({ API_BASE: "http://api.test" }));

import { buildFuselageTraces } from "@/components/workbench/WingOutlineViewer";
import {
  buildFuselageSurface,
  saveFuselage,
  sectionPath,
  type XSec,
} from "@/components/workbench/ImportFuselageDialog";
import type { Fuselage } from "@/hooks/useFuselage";

// Unit half-axes: the outline offset is cos/sin raised to 2/n.
const BOXY_BELLY: XSec = { xyz: [0, 0, 0], a: 1, b: 1, n: 2, n_lower: 8 };
const ROUND: XSec = { xyz: [1, 0, 0], a: 1, b: 1, n: 2 };
const C45 = Math.SQRT1_2;
const BOXY_45 = Math.pow(C45, 2 / 8); // ≈ 0.917

describe("buildFuselageTraces (workbench viewer)", () => {
  const fuselage: Fuselage = { name: "f", x_secs: [BOXY_BELLY, ROUND] };

  it("draws the lower half with n_lower and the upper half with n", () => {
    const traces = buildFuselageTraces(fuselage, "#fff");
    // [centreline, outline 0, outline 1, 4 longitudinal lines]
    expect(traces).toHaveLength(7);
    const outline = traces[1];
    // 32 points per turn: j=4 is 45° (upper), j=28 is 315° (lower)
    expect(outline.y[4]).toBeCloseTo(C45, 6);
    expect(outline.z[4]).toBeCloseTo(C45, 6);
    expect(outline.y[28]).toBeCloseTo(BOXY_45, 6);
    expect(outline.z[28]).toBeCloseTo(-BOXY_45, 6);
    // the round section has no n_lower: its lower half stays round
    expect(traces[2].y[28]).toBeCloseTo(C45, 6);
  });

  it("puts the bottom longitudinal line at -b and highlights the selected section", () => {
    const traces = buildFuselageTraces(fuselage, "#fff", 1);
    const bottom = traces[6];
    expect(bottom.z[0]).toBeCloseTo(-1, 6);
    expect(traces[2].line.color).not.toBe("#fff");
    expect(traces[1].line.color).toBe("#fff");
  });
});

describe("buildFuselageSurface (import preview)", () => {
  it("uses n_lower for the lower half of each surface row", () => {
    const surf = buildFuselageSurface([BOXY_BELLY, ROUND], "#f80", 0.5, "s", 8);
    // 8 samples per turn: j=1 is 45°, j=7 is 315°
    expect(surf.y[0][1]).toBeCloseTo(C45, 6);
    expect(surf.y[0][7]).toBeCloseTo(BOXY_45, 6);
    expect(surf.z[0][7]).toBeCloseTo(-BOXY_45, 6);
    expect(surf.x[1][7]).toBe(1);
    expect(surf.y[1][7]).toBeCloseTo(C45, 6);
  });
});

describe("sectionPath (section SVG)", () => {
  it("keeps the top up (SVG y grows downwards) and squares the belly", () => {
    const pts = sectionPath(BOXY_BELLY, 8)
      .replace(/Z$/, "")
      .split(" ")
      .map((p) => p.slice(1).split(",").map(Number));
    expect(pts).toHaveLength(9);
    // 45°: upper half, SVG y negative
    expect(pts[1][0]).toBeCloseTo(C45, 3);
    expect(pts[1][1]).toBeCloseTo(-C45, 3);
    // 315°: lower half with n_lower, SVG y positive
    expect(pts[7][0]).toBeCloseTo(BOXY_45, 3);
    expect(pts[7][1]).toBeCloseTo(BOXY_45, 3);
  });
});

describe("saveFuselage (import dialog)", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("sends n_lower, and null for symmetric sections", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200 });
    vi.stubGlobal("fetch", fetchMock);

    await saveFuselage("aero-1", "main body", [BOXY_BELLY, ROUND]);

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://api.test/aeroplanes/aero-1/fuselages/main%20body");
    expect(init.method).toBe("PUT");
    const body = JSON.parse(init.body);
    expect(body.x_secs.map((x: XSec) => x.n_lower)).toEqual([8, null]);
  });
});

// ── gh-1349: every renderer draws the closed contour when a section has one ──

/** Asymmetric, concave (notched) closed loop, counter-clockwise. */
const CONTOUR: [number, number][] = [
  [0, -1], [0.6, -0.8], [1, 0], [0.4, 0.2], [0.5, 0.9], [0, 1], [-0.7, 0.4], [-0.5, -0.6],
];
const C0: XSec = { xyz: [0, 0, 0], a: 1, b: 1, n: 2, contour: CONTOUR };
const C1: XSec = { xyz: [1, 0, 0.1], a: 1, b: 1, n: 2, contour: CONTOUR };

describe("contour sections (gh-1349)", () => {
  it("the workbench viewer draws the contour as given, closed, with lines through its extremes", () => {
    const traces = buildFuselageTraces({ name: "f", x_secs: [C0, C1] }, "#fff");
    expect(traces).toHaveLength(7);
    const outline = traces[1];
    expect(outline.y).toEqual([...CONTOUR.map(([y]) => y), 0]);
    expect(outline.z).toEqual([...CONTOUR.map(([, z]) => z), -1]);
    expect(traces[2].z[0]).toBeCloseTo(-0.9, 12); // xyz z offset 0.1 applied
    // longitudinal lines: right side, top, left side, bottom
    expect(traces[3].y).toEqual([1, 1]);
    expect(traces[4].z).toEqual([1, 1.1]);
    expect(traces[5].y).toEqual([-0.7, -0.7]);
    expect(traces[6].z).toEqual([-1, -0.9]);
  });

  it("the import preview surface lofts point i to point i of the contours", () => {
    const surf = buildFuselageSurface([C0, C1], "#f80", 0.5, "s", 8);
    expect(surf.y[0]).toHaveLength(CONTOUR.length + 1);
    expect(surf.y[1]).toHaveLength(CONTOUR.length + 1);
    expect(surf.z[0][2]).toBe(0);
    expect(surf.z[1][2]).toBeCloseTo(0.1, 12);
    expect(surf.y[0][6]).toBe(-0.7);
  });

  it("the section SVG draws the contour, top up", () => {
    const pts = sectionPath(C0, 8)
      .replace(/Z$/, "")
      .split(" ")
      .map((p) => p.slice(1).split(",").map(Number));
    expect(pts).toHaveLength(CONTOUR.length + 1);
    expect(pts[0]).toEqual([0, 1]); // (0, -1), SVG y down
    expect(pts[5]).toEqual([0, -1]); // (0, 1)
  });

  it("the import save keeps the contour and sends null without one", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200 });
    vi.stubGlobal("fetch", fetchMock);
    await saveFuselage("aero-1", "body", [C0, ROUND]);
    const sent = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(sent.x_secs[0].contour).toEqual(CONTOUR);
    expect(sent.x_secs[1].contour).toBeNull();
    vi.unstubAllGlobals();
  });
});
