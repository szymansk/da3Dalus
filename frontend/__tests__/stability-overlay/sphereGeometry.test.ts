import { describe, it, expect } from "vitest";
import { makeIcosphere } from "@/components/workbench/stability-overlay/sphereGeometry";

describe("makeIcosphere", () => {
  it("returns 12 vertices and 20 faces", () => {
    const s = makeIcosphere(0, 0, 0, 1);
    expect(s.x).toHaveLength(12);
    expect(s.y).toHaveLength(12);
    expect(s.z).toHaveLength(12);
    expect(s.i).toHaveLength(20);
    expect(s.j).toHaveLength(20);
    expect(s.k).toHaveLength(20);
  });

  it("places all vertices at the requested radius from the centre", () => {
    const s = makeIcosphere(2, 3, 4, 0.5);
    for (let n = 0; n < s.x.length; n++) {
      const dx = s.x[n] - 2;
      const dy = s.y[n] - 3;
      const dz = s.z[n] - 4;
      const r = Math.sqrt(dx * dx + dy * dy + dz * dz);
      expect(r).toBeCloseTo(0.5, 6);
    }
  });

  it("face indices reference valid vertex slots", () => {
    const s = makeIcosphere(0, 0, 0, 1);
    for (let n = 0; n < s.i.length; n++) {
      expect(s.i[n]).toBeGreaterThanOrEqual(0);
      expect(s.i[n]).toBeLessThan(12);
      expect(s.j[n]).toBeGreaterThanOrEqual(0);
      expect(s.j[n]).toBeLessThan(12);
      expect(s.k[n]).toBeGreaterThanOrEqual(0);
      expect(s.k[n]).toBeLessThan(12);
    }
  });
});
