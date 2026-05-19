/**
 * Tests for the structured error-message parser (gh-577 review).
 */
import { describe, it, expect } from "vitest";
import { parseApiError } from "@/lib/parseApiError";

function makeResponse(status: number, body: string, json = true): Response {
  return new Response(body, {
    status,
    headers: { "Content-Type": json ? "application/json" : "text/plain" },
  });
}

describe("parseApiError", () => {
  it("extracts message from custom ServiceException envelope", async () => {
    const res = makeResponse(
      422,
      JSON.stringify({
        error: { code: "validation", message: "OperatingPoint not trimmed" },
      }),
    );
    expect(await parseApiError(res, "Streamlines")).toBe(
      "Streamlines — invalid request: OperatingPoint not trimmed",
    );
  });

  it("extracts message from FastAPI default detail envelope", async () => {
    const res = makeResponse(
      404,
      JSON.stringify({ detail: "Aeroplane not found" }),
    );
    expect(await parseApiError(res, "Streamlines")).toBe(
      "Streamlines — not found: Aeroplane not found",
    );
  });

  it("falls back to plain text when body is not JSON", async () => {
    const res = makeResponse(500, "boom", false);
    expect(await parseApiError(res, "Streamlines")).toBe(
      "Streamlines failed (500): boom",
    );
  });

  it("falls back to statusText for empty body", async () => {
    const res = new Response(null, { status: 503, statusText: "unavail" });
    expect(await parseApiError(res, "Streamlines")).toBe(
      "Streamlines failed (503): unavail",
    );
  });
});
