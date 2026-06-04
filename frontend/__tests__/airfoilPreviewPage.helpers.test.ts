/**
 * Unit tests for airfoil-preview page helper functions (gh-825).
 * Tests activeLensScore and computeRe pure helpers in isolation.
 */
import { describe, it, expect } from "vitest";
import { activeLensScore, computeRe } from "../app/workbench/airfoil-preview/page";

const ITEM = {
  re_agnostic: 0.80,
  mission: 0.70,
  target_cl_cruise: 0.60,
};

describe("activeLensScore — active-lens badge helper (gh-825)", () => {
  it("returns re_agnostic for lens 're_agnostic'", () => {
    expect(activeLensScore(ITEM, "re_agnostic")).toBe(0.80);
  });

  it("returns re_agnostic for undefined lens (default)", () => {
    expect(activeLensScore(ITEM, undefined)).toBe(0.80);
  });

  it("returns mission score for lens 'mission'", () => {
    expect(activeLensScore(ITEM, "mission")).toBe(0.70);
  });

  it("falls back to re_agnostic when lens is 'mission' but mission is null", () => {
    const item = { ...ITEM, mission: null };
    expect(activeLensScore(item, "mission")).toBe(0.80);
  });

  it("returns target_cl_cruise score for lens 'target_cl_cruise'", () => {
    expect(activeLensScore(ITEM, "target_cl_cruise")).toBe(0.60);
  });

  it("falls back to re_agnostic when lens is 'target_cl_cruise' but score is null", () => {
    const item = { ...ITEM, target_cl_cruise: null };
    expect(activeLensScore(item, "target_cl_cruise")).toBe(0.80);
  });

  it("returns re_agnostic for unknown lens (display-only glide lenses fall through)", () => {
    // target_cl_best_glide and target_cl_min_sink are display-only;
    // activeLensScore deliberately falls through to re_agnostic for any unknown lens
    expect(activeLensScore(ITEM, "target_cl_best_glide")).toBe(0.80);
    expect(activeLensScore(ITEM, "target_cl_min_sink")).toBe(0.80);
  });

  it("score badge matches the ranking order: mission badge uses mission score, not re_agnostic", () => {
    // Regression guard: previous code hardcoded item.re_agnostic regardless of lens,
    // causing the badge to mismatch the ranked order when mission/cruise lens is active.
    const highMissionItem = { re_agnostic: 0.50, mission: 0.95, target_cl_cruise: null };
    expect(activeLensScore(highMissionItem, "mission")).toBe(0.95);
    // must NOT return the lower re_agnostic value
    expect(activeLensScore(highMissionItem, "mission")).not.toBe(0.50);
  });
});

describe("computeRe — Reynolds number helper", () => {
  it("computes correct Re for a given velocity and chord", () => {
    // Re = V * c / nu = 14 * (200/1000) / 1.46e-5 ≈ 191781
    const re = computeRe(14, 200);
    expect(re).toBeGreaterThan(190000);
    expect(re).toBeLessThan(195000);
  });
});
