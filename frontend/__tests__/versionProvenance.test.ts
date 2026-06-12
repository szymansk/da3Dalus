import { describe, it, expect } from "vitest";
import { isAgentAuthor, authorLabel } from "@/lib/versionProvenance";

describe("isAgentAuthor", () => {
  it("treats 'ai' and 'copilot' (any case) as agent", () => {
    expect(isAgentAuthor("ai")).toBe(true);
    expect(isAgentAuthor("copilot")).toBe(true);
    expect(isAgentAuthor("Copilot")).toBe(true);
    expect(isAgentAuthor(" AI ")).toBe(true);
  });

  it("treats human and unknown as NOT agent", () => {
    expect(isAgentAuthor("human")).toBe(false);
    expect(isAgentAuthor(null)).toBe(false);
    expect(isAgentAuthor(undefined)).toBe(false);
    expect(isAgentAuthor("")).toBe(false);
  });
});

describe("authorLabel", () => {
  it("renders null/empty as em dash, not 'unknown'", () => {
    expect(authorLabel(null)).toBe("—");
    expect(authorLabel("")).toBe("—");
    expect(authorLabel("   ")).toBe("—");
  });

  it("passes through real authors", () => {
    expect(authorLabel("copilot")).toBe("copilot");
    expect(authorLabel("human")).toBe("human");
  });
});
