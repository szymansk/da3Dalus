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
  superellipsePath,
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

describe("superellipsePath (section SVG)", () => {
  it("keeps the top up (SVG y grows downwards) and squares the belly", () => {
    const pts = superellipsePath(BOXY_BELLY, 8)
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
