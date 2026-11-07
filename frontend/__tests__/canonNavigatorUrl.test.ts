import { describe, it, expect } from "vitest";
import { canonNavigatorUrl } from "@/lib/canonNavigator";

describe("canonNavigatorUrl", () => {
  it("connects the generated navigator page to the backend for a fleet aircraft", () => {
    const url = new URL(
      canonNavigatorUrl("http://localhost:8001", { fleet: "rv-7" }),
      "http://app.test",
    );
    expect(url.pathname).toBe("/canon-navigator.html");
    expect(url.searchParams.get("connected")).toBe("1");
    expect(url.searchParams.get("api")).toBe("http://localhost:8001");
    expect(url.searchParams.get("fleet")).toBe("rv-7");
    expect(url.searchParams.has("aeroplane")).toBe(false);
  });

  it("connects it for a stored aeroplane by its id", () => {
    const id = "6f1c1a52-8f3c-4a43-9d9a-2c7c4c3b5a10";
    const url = new URL(
      canonNavigatorUrl("http://localhost:8001", { aeroplane: id }),
      "http://app.test",
    );
    expect(url.searchParams.get("aeroplane")).toBe(id);
    expect(url.searchParams.has("fleet")).toBe(false);
  });

  it("encodes an address with a path or a query", () => {
    const url = new URL(
      canonNavigatorUrl("https://x.test/pr-12/api?a=b&c=d", { fleet: "bryan" }),
      "http://app.test",
    );
    expect(url.searchParams.get("api")).toBe("https://x.test/pr-12/api?a=b&c=d");
  });

  it("serves the page under the app's base path", () => {
    const url = new URL(
      canonNavigatorUrl("/pr-12/backend", { fleet: "bryan" }, "/pr-12"),
      "http://app.test",
    );
    expect(url.pathname).toBe("/pr-12/canon-navigator.html");
    expect(url.searchParams.get("api")).toBe("/pr-12/backend");
  });
});
