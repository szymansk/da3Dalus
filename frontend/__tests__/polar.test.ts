import { describe, it, expect } from "vitest";
import {
  computeK,
  computeCLmd,
  computeEMax,
  computeRho,
  rhoThresholdsForProfile,
  qualityColorClassName,
  rhoColorClassName,
} from "@/lib/polar";

describe("polar.computeCLmd", () => {
  it("matches √(π·e·AR·CD0)", () => {
    const v = computeCLmd(0.02, 0.8, false, 7);
    expect(v).toBeCloseTo(Math.sqrt(Math.PI * 0.8 * 7 * 0.02), 4);
    expect(v).toBeCloseTo(0.5932, 3);
  });
  it("returns null when fit was rejected (ρ-bail rule)", () => {
    expect(computeCLmd(0.02, 0.8, true, 7)).toBeNull();
  });
  it("returns null on each null/zero/negative input", () => {
    expect(computeCLmd(null, 0.8, false, 7)).toBeNull();
    expect(computeCLmd(0.02, null, false, 7)).toBeNull();
    expect(computeCLmd(0.02, 0.8, false, null)).toBeNull();
    expect(computeCLmd(0, 0.8, false, 7)).toBeNull();
    expect(computeCLmd(0.02, 0, false, 7)).toBeNull();
    expect(computeCLmd(0.02, 0.8, false, 0)).toBeNull();
    expect(computeCLmd(-0.01, 0.8, false, 7)).toBeNull();
  });
  it("rejects non-finite inputs (Infinity / -Infinity / NaN)", () => {
    // Corrupt-payload guard — a backend `np.inf` from a degenerate fit
    // would otherwise propagate through .toFixed(2) as "Infinity" in the
    // chip rather than the documented "—" bail state.
    expect(computeCLmd(Infinity, 0.8, false, 7)).toBeNull();
    expect(computeCLmd(0.02, Infinity, false, 7)).toBeNull();
    expect(computeCLmd(0.02, 0.8, false, Infinity)).toBeNull();
    expect(computeCLmd(-Infinity, 0.8, false, 7)).toBeNull();
    expect(computeCLmd(NaN, 0.8, false, 7)).toBeNull();
    expect(computeCLmd(0.02, NaN, false, 7)).toBeNull();
    expect(computeCLmd(0.02, 0.8, false, NaN)).toBeNull();
  });
});

describe("polar.computeEMax", () => {
  it("matches ½·√(π·e·AR/CD0)", () => {
    const v = computeEMax(0.02, 0.8, false, 7);
    expect(v).toBeCloseTo(0.5 * Math.sqrt((Math.PI * 0.8 * 7) / 0.02), 3);
    expect(v).toBeCloseTo(14.83, 2);
  });
  it("ρ-bail when fit rejected", () => {
    expect(computeEMax(0.02, 0.8, true, 7)).toBeNull();
  });
  it("rejects non-finite inputs", () => {
    expect(computeEMax(Infinity, 0.8, false, 7)).toBeNull();
    expect(computeEMax(0.02, NaN, false, 7)).toBeNull();
    expect(computeEMax(0.02, 0.8, false, Infinity)).toBeNull();
  });
  it("cross-helper identity (L/D)_max · C_L,md = (π·e·AR) / 2 on the grid", () => {
    // Cross-pin computeEMax against computeCLmd so a sign/factor regression
    // in only one helper is caught even when both still match their own
    // formula tests.  Anderson §6.7.2 derivation:
    //   (L/D)_max = ½·√(π·e·AR / C_D0)
    //   C_L,md    =      √(π·e·AR · C_D0)
    //   ⇒ (L/D)_max · C_L,md = (π·e·AR) / 2
    const cases: ReadonlyArray<[number, number, number]> = [
      [0.008, 0.95, 36],
      [0.02, 0.80, 7],
      [0.04, 0.75, 6],
      [0.012, 0.85, 18],
      [0.025, 0.78, 10],
      [0.015, 0.90, 25],
    ];
    for (const [cd0, e, ar] of cases) {
      const eMax = computeEMax(cd0, e, false, ar);
      const clMd = computeCLmd(cd0, e, false, ar);
      expect(eMax).not.toBeNull();
      expect(clMd).not.toBeNull();
      expect(eMax! * clMd!).toBeCloseTo((Math.PI * e * ar) / 2, 6);
    }
  });
});

describe("polar.computeRho", () => {
  it("matches CD0·π·e·AR / CL_max²", () => {
    const v = computeRho(0.02, 0.8, false, 7, 1.4);
    expect(v).toBeCloseTo((0.02 * Math.PI * 0.8 * 7) / (1.4 * 1.4), 4);
    expect(v).toBeCloseTo(0.18, 2);
  });
  it("identity ρ = (CL_md/CL_max)² across a deterministic grid", () => {
    // Deterministic table — covers GA, RC, sailplane, and edge-of-range
    // combinations of (CD0, e, AR, CL_max).
    const cases: ReadonlyArray<[number, number, number, number]> = [
      [0.008, 0.95, 36, 1.5],   // ASH-25-class sailplane
      [0.02, 0.80, 7, 1.4],     // GA trainer
      [0.04, 0.75, 6, 1.0],     // draggy RC trainer
      [0.012, 0.85, 18, 1.3],   // motorglider
      [0.025, 0.78, 10, 1.5],   // GA
      [0.015, 0.90, 25, 1.4],   // high-performance glider
    ];
    for (const [cd0, e, ar, clMax] of cases) {
      const rho = computeRho(cd0, e, false, ar, clMax);
      const clMd = computeCLmd(cd0, e, false, ar);
      expect(rho).not.toBeNull();
      expect(clMd).not.toBeNull();
      expect(rho!).toBeCloseTo((clMd! / clMax) ** 2, 6);
    }
  });
  it("ρ-bail when fit rejected", () => {
    expect(computeRho(0.02, 0.8, true, 7, 1.4)).toBeNull();
  });
  it("rejects non-finite inputs", () => {
    expect(computeRho(Infinity, 0.8, false, 7, 1.4)).toBeNull();
    expect(computeRho(0.02, 0.8, false, NaN, 1.4)).toBeNull();
    expect(computeRho(0.02, 0.8, false, 7, Infinity)).toBeNull();
  });
});

describe("polar.computeK", () => {
  it("matches 1/(π·e·AR)", () => {
    expect(computeK(0.8, false, 7)).toBeCloseTo(
      1 / (Math.PI * 0.8 * 7),
      6,
    );
  });
  it("ρ-bail when fit rejected", () => {
    expect(computeK(0.8, true, 7)).toBeNull();
  });
});

describe("polar.rhoThresholdsForProfile", () => {
  it("powered uses { amber: 1/3, red: 1.0 }", () => {
    expect(rhoThresholdsForProfile(false)).toEqual({
      amber: 1 / 3,
      red: 1.0,
    });
  });
  it("glider uses { amber: 2/3, red: 1.0 }", () => {
    expect(rhoThresholdsForProfile(true)).toEqual({
      amber: 2 / 3,
      red: 1.0,
    });
  });
});

describe("polar.qualityColorClassName", () => {
  it.each([
    ["high", "text-emerald-400"],
    ["medium", "text-amber-400"],
    ["low", "text-orange-400"],
    ["unknown", "text-muted-foreground"],
  ] as const)("%s → %s", (q, cls) => {
    expect(qualityColorClassName(q)).toBe(cls);
  });
  it("undefined quality → muted (defensive)", () => {
    expect(qualityColorClassName(undefined)).toBe("text-muted-foreground");
  });
});

describe("polar.rhoColorClassName", () => {
  it("null ρ → muted", () => {
    expect(rhoColorClassName(null, false)).toBe("text-muted-foreground");
  });
  it("powered: ρ < 1/3 → emerald", () => {
    expect(rhoColorClassName(0.2, false)).toBe("text-emerald-400");
  });
  it("powered: ρ = 1/3 → amber (lower-inclusive)", () => {
    expect(rhoColorClassName(1 / 3, false)).toBe("text-amber-400");
  });
  it("powered: ρ ∈ (1/3, 1) → amber", () => {
    expect(rhoColorClassName(0.5, false)).toBe("text-amber-400");
  });
  it("powered: ρ = 1 → red (upper-inclusive)", () => {
    expect(rhoColorClassName(1.0, false)).toBe("text-red-400");
  });
  it("powered: ρ > 1 → red", () => {
    expect(rhoColorClassName(1.2, false)).toBe("text-red-400");
  });
  it("glider: ρ = 1/3 → still emerald (under 2/3 amber)", () => {
    expect(rhoColorClassName(1 / 3, true)).toBe("text-emerald-400");
  });
  it("glider: ρ = 2/3 → amber", () => {
    expect(rhoColorClassName(2 / 3, true)).toBe("text-amber-400");
  });
  it("glider: ρ ∈ (2/3, 1) → amber (interior)", () => {
    expect(rhoColorClassName(0.85, true)).toBe("text-amber-400");
  });
  it("glider: ρ = 1 → red", () => {
    expect(rhoColorClassName(1.0, true)).toBe("text-red-400");
  });
});
