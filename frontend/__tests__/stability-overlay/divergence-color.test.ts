import { describe, it, expect } from "vitest";
import { cgDivergenceColor } from "@/components/workbench/stability-overlay/divergence-color";

// Thresholds (match the original InfoChipRow helper):
//   |Δ|/MAC * 100 <  5%        → text-emerald-400 (green)
//   5% <= |Δ|/MAC * 100 <= 15% → text-orange-400 (orange / yellow band)
//   |Δ|/MAC * 100 >  15%       → text-red-400 (red)
describe("cgDivergenceColor", () => {
  it("returns the green class for |Δ| < 5% MAC", () => {
    // 0.005 / 1.0 * 100 = 0.5%  → green
    expect(cgDivergenceColor(2.440, 2.445, 1.0)).toMatch(/emerald/);
  });

  it("returns the orange class for 5% <= |Δ| <= 15% MAC", () => {
    // 0.100 / 1.0 * 100 = 10.0% → orange
    expect(cgDivergenceColor(2.440, 2.540, 1.0)).toMatch(/orange/);
  });

  it("returns the red class for |Δ| > 15% MAC", () => {
    // 0.200 / 1.0 * 100 = 20.0% → red
    expect(cgDivergenceColor(2.440, 2.640, 1.0)).toMatch(/red/);
  });

  it("is symmetric in IST above vs below SOLL", () => {
    // Both are 10% absolute divergence → identical class
    expect(cgDivergenceColor(2.440, 2.340, 1.0)).toEqual(
      cgDivergenceColor(2.440, 2.540, 1.0),
    );
  });

  it("normalises by MAC", () => {
    // 0.050 / 2.0 * 100 = 2.5% → still under 5% → green
    expect(cgDivergenceColor(2.440, 2.490, 2.0)).toMatch(/emerald/);
  });
});
