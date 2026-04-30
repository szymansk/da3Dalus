import { describe, it, expect } from "vitest";
import { avlLanguage, avlTheme } from "@/components/workbench/avlLanguage";

describe("avlLanguage", () => {
  it("exports a Monarch language definition", () => {
    expect(avlLanguage.tokenizer).toBeDefined();
    expect(avlLanguage.tokenizer.root).toBeDefined();
    expect(avlLanguage.tokenizer.root.length).toBeGreaterThan(0);
  });

  it("defines keywords", () => {
    expect(avlLanguage.keywords).toContain("SURFACE");
    expect(avlLanguage.keywords).toContain("SECTION");
    expect(avlLanguage.keywords).toContain("BODY");
    expect(avlLanguage.keywords).toContain("CONTROL");
  });

  it("exports a dark theme", () => {
    expect(avlTheme.base).toBe("vs-dark");
    expect(avlTheme.rules.length).toBeGreaterThan(0);
  });
});
