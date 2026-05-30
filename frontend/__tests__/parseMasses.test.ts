import { describe, it, expect } from "vitest";
import { parseMasses } from "@/lib/masses";

describe("parseMasses", () => {
  it("parses German comma decimals with semicolon separators", () => {
    expect(parseMasses("1,5; 2,0; 2,5")).toEqual([1.5, 2.0, 2.5]);
  });

  it("accepts dot decimals as well", () => {
    expect(parseMasses("1.5; 2.5")).toEqual([1.5, 2.5]);
  });

  it("drops empty, non-numeric and non-positive tokens", () => {
    expect(parseMasses("1,5; ; abc; -2; 0; 3")).toEqual([1.5, 3]);
  });

  it("returns an empty array for empty/whitespace input", () => {
    expect(parseMasses("")).toEqual([]);
    expect(parseMasses("   ")).toEqual([]);
  });

  it("handles a single value", () => {
    expect(parseMasses("1,5")).toEqual([1.5]);
  });
});
