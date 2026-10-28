import { describe, it, expect } from "vitest";
import { canonNavigatorUrl } from "@/lib/canonNavigator";

describe("canonNavigatorUrl", () => {
  it("connects the generated navigator page to the backend for one aircraft", () => {
    const url = new URL(
      canonNavigatorUrl("http://localhost:8001", "rv-7"),
      "http://app.test",
    );
    expect(url.pathname).toBe("/canon-navigator.html");
    expect(url.searchParams.get("connected")).toBe("1");
    expect(url.searchParams.get("api")).toBe("http://localhost:8001");
    expect(url.searchParams.get("aircraft")).toBe("rv-7");
  });

  it("encodes an address with a path or a query", () => {
    const url = new URL(
      canonNavigatorUrl("https://x.test/pr-12/api?a=b&c=d", "bryan"),
      "http://app.test",
    );
    expect(url.searchParams.get("api")).toBe("https://x.test/pr-12/api?a=b&c=d");
  });
});
