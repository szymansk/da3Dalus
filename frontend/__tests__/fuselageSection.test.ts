import { describe, it, expect } from "vitest";
import {
  parseLowerExponent,
  sectionExponent,
  sectionExponentLabel,
  sectionOffset,
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
