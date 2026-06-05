import { describe, expect, it } from "vitest";

import { finiteOr } from "@/lib/numericInput";

describe("finiteOr", () => {
  it("keeps a user-entered 0 instead of falling back (the gh-787 bug)", () => {
    expect(finiteOr("0", -5)).toBe(0);
  });

  it("parses normal positive and negative values", () => {
    expect(finiteOr("3.5", -5)).toBe(3.5);
    expect(finiteOr("-2", 1)).toBe(-2);
    expect(finiteOr("1e3", 0)).toBe(1000);
  });

  it("falls back on empty / whitespace / non-numeric input", () => {
    expect(finiteOr("", -5)).toBe(-5);
    expect(finiteOr("   ", -5)).toBe(-5);
    expect(finiteOr("abc", 7)).toBe(7);
  });

  it("falls back on non-finite parses (Infinity / NaN)", () => {
    expect(finiteOr("Infinity", 1)).toBe(1);
    expect(finiteOr("NaN", 2)).toBe(2);
  });

  it("ignores trailing garbage the same way parseFloat does, but stays finite", () => {
    // parseFloat("12abc") === 12 — a finite value, so it is kept.
    expect(finiteOr("12abc", 0)).toBe(12);
  });
});
