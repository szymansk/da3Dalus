import { describe, it, expect } from "vitest";
import {
  contourPointCount,
  parseLowerExponent,
  sectionExponent,
  sectionExponentLabel,
  sectionExtremes,
  sectionOffset,
  sectionOutline,
  sectionShapeLabel,
  type ContourPoint,
} from "@/lib/fuselageSection";

const split = { a: 0.02, b: 0.025, n: 2, n_lower: 8 };

describe("fuselageSection (gh-1157)", () => {
  it("uses n above and n_lower below the centre line", () => {
    expect(sectionExponent(split, Math.PI / 4)).toBe(2);
    expect(sectionExponent(split, -Math.PI / 4)).toBe(8);
    expect(sectionExponent({ ...split, n_lower: null }, -Math.PI / 4)).toBe(2);
  });

  it("puts upper points on the n-curve and lower points on the n_lower-curve", () => {
    for (const t of [0.3, 1.2, 2.5]) {
      const up = sectionOffset(split, t);
      expect(Math.abs(up.y / split.a) ** 2 + Math.abs(up.z / split.b) ** 2).toBeCloseTo(1, 9);
      const down = sectionOffset(split, -t);
      expect(down.z).toBeLessThan(0);
      expect(Math.abs(down.y / split.a) ** 8 + Math.abs(down.z / split.b) ** 8).toBeCloseTo(1, 9);
    }
  });

  it("meets at (±a, 0) and reaches ±b at top and bottom", () => {
    expect(sectionOffset(split, 0).y).toBeCloseTo(split.a, 12);
    expect(sectionOffset(split, Math.PI).y).toBeCloseTo(-split.a, 12);
    expect(sectionOffset(split, Math.PI / 2).z).toBeCloseTo(split.b, 12);
    expect(sectionOffset(split, -Math.PI / 2).z).toBeCloseTo(-split.b, 12);
  });

  it("labels symmetric and split sections", () => {
    expect(sectionExponentLabel({ ...split, n_lower: null })).toBe("n=2.0");
    expect(sectionExponentLabel({ ...split, n_lower: 2 })).toBe("n=2.0");
    expect(sectionExponentLabel(split)).toBe("n=2.0/8.0");
  });

  it("parses the lower exponent field", () => {
    expect(parseLowerExponent("")).toBeNull();
    expect(parseLowerExponent("  ")).toBeNull();
    expect(parseLowerExponent("abc")).toBeNull();
    expect(parseLowerExponent("6")).toBe(6);
    expect(parseLowerExponent("0.1")).toBe(0.5);
    expect(parseLowerExponent("99")).toBe(50);
  });
});

// ── gh-1349: the optional closed point contour ─────────────────

/** Asymmetric former: wider on the right, canopy offset to the left. */
const ASYM: ContourPoint[] = [
  [0, -0.04], [0.035, -0.02], [0.03, 0.02], [0.01, 0.05], [-0.015, 0.03], [-0.02, -0.025],
];
/** Concave former: a wing-saddle notch cut into the bottom. */
const SADDLE: ContourPoint[] = [
  [0, -0.03], [0.02, -0.03], [0.02, -0.045], [0.03, -0.045], [0.03, 0.02],
  [0, 0.05], [-0.03, 0.02], [-0.03, -0.045], [-0.02, -0.045], [-0.02, -0.03],
];
const withContour = { a: 0.03, b: 0.045, n: 2.4, n_lower: 6, contour: ASYM };

describe("fuselageSection contour (gh-1349)", () => {
  it("draws an asymmetric contour as given and closes it, without mirroring", () => {
    const outline = sectionOutline(withContour, 32);
    expect(outline).toHaveLength(ASYM.length + 1);
    ASYM.forEach(([y, z], i) => expect(outline[i]).toEqual({ y, z }));
    expect(outline[outline.length - 1]).toEqual(outline[0]);
  });

  it("draws a concave contour point for point", () => {
    const outline = sectionOutline({ a: 0.03, b: 0.05, n: 2, contour: SADDLE }, 8);
    expect(outline.slice(0, -1).map((p) => [p.y, p.z])).toEqual(SADDLE);
  });

  it("ignores the sample count for a contour (never resampled)", () => {
    expect(sectionOutline(withContour, 8)).toEqual(sectionOutline(withContour, 200));
  });

  it("returns today's super-ellipse when there is no contour", () => {
    const plain = { a: 0.02, b: 0.025, n: 2, n_lower: 8 };
    const outline = sectionOutline({ ...plain, contour: null }, 16);
    expect(outline).toHaveLength(17);
    outline.forEach((p, j) => {
      const r = sectionOffset(plain, (2 * Math.PI * j) / 16);
      expect(p.y).toBeCloseTo(r.y, 12);
      expect(p.z).toBeCloseTo(r.z, 12);
    });
    expect(sectionOutline(plain, 16)).toEqual(outline);
  });

  it("takes the extremes from the contour itself, also when it is asymmetric", () => {
    expect(sectionExtremes(withContour)).toEqual({
      right: { y: 0.035, z: -0.02 },
      top: { y: 0.01, z: 0.05 },
      left: { y: -0.02, z: -0.025 },
      bottom: { y: 0, z: -0.04 },
    });
  });

  it("keeps the super-ellipse extremes at 0, 90, 180 and 270 degrees", () => {
    const plain = { a: 0.02, b: 0.025, n: 2, n_lower: 8 };
    const ext = sectionExtremes(plain);
    expect(ext.right).toEqual(sectionOffset(plain, 0));
    expect(ext.top).toEqual(sectionOffset(plain, Math.PI / 2));
    expect(ext.left).toEqual(sectionOffset(plain, Math.PI));
    expect(ext.bottom).toEqual(sectionOffset(plain, (3 * Math.PI) / 2));
  });

  it("counts the contour points and labels the section with them", () => {
    expect(contourPointCount(withContour)).toBe(6);
    expect(contourPointCount({ a: 1, b: 1, n: 2 })).toBeNull();
    expect(sectionShapeLabel(withContour)).toBe("n=2.4/6.0 \u00B7 contour (6 points)");
    expect(sectionShapeLabel({ a: 1, b: 1, n: 2 })).toBe("n=2.0");
  });
});
