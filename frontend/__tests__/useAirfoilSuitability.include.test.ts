/**
 * Tests for the additive `include` param on useAirfoilSuitability — ITEM 5-FE.
 *
 * Contract:
 *   - When `include` (array of names) is supplied and non-empty, buildKey
 *     appends `&include=<comma-joined>` to the SWR key.
 *   - When `include` is undefined (old callers), the key is UNCHANGED
 *     (byte-for-byte identical to today's behaviour → SWR cache not busted).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { useAirfoilSuitability } from "@/hooks/useAirfoilSuitability";

// ── Capture the SWR key ──────────────────────────────────────────

let capturedKey: string | null = undefined as unknown as string | null;

vi.mock("swr", () => ({
  default: vi.fn((key: string | null) => {
    capturedKey = key;
    return { data: null, error: null, isLoading: false };
  }),
}));

describe("useAirfoilSuitability — include param (ITEM 5-FE)", () => {
  beforeEach(() => {
    capturedKey = undefined as unknown as string | null;
  });

  // ── Backward-compatibility: old callers unaffected ──────────────

  it("key is UNCHANGED (no include param) when include is undefined", () => {
    renderHook(() =>
      useAirfoilSuitability({ chord_m: 0.2, speed_ms: 14 }),
    );
    expect(capturedKey).not.toBeNull();
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.searchParams.has("include")).toBe(false);
  });

  it("key is UNCHANGED when include is an empty array", () => {
    renderHook(() =>
      useAirfoilSuitability({ chord_m: 0.2, speed_ms: 14, include: [] }),
    );
    expect(capturedKey).not.toBeNull();
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.searchParams.has("include")).toBe(false);
  });

  // ── New include param behaviour ─────────────────────────────────

  it("appends include param when a single name is given", () => {
    renderHook(() =>
      useAirfoilSuitability({ chord_m: 0.2, speed_ms: 14, include: ["s1223"] }),
    );
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.searchParams.get("include")).toBe("s1223");
  });

  it("appends include param as comma-joined string for multiple names", () => {
    renderHook(() =>
      useAirfoilSuitability({
        chord_m: 0.2,
        speed_ms: 14,
        include: ["s1223", "ag35"],
      }),
    );
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.searchParams.get("include")).toBe("s1223,ag35");
  });

  it("include param is still null key when chord_m is missing", () => {
    renderHook(() =>
      useAirfoilSuitability({ chord_m: undefined, speed_ms: 14, include: ["e423"] }),
    );
    expect(capturedKey).toBeNull();
  });

  it("include param works together with aeroplane_id and other optional params", () => {
    const uuid = "3fa85f64-5717-4562-b3fc-2c963f66afa6";
    renderHook(() =>
      useAirfoilSuitability({
        chord_m: 0.3,
        speed_ms: 18,
        aeroplane_id: uuid,
        mission_type: "trainer",
        include: ["clark-y", "naca0012"],
      }),
    );
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.searchParams.get("include")).toBe("clark-y,naca0012");
    expect(url.searchParams.get("aeroplane_id")).toBe(uuid);
    expect(url.searchParams.get("mission_type")).toBe("trainer");
  });

  it("include with a single name produces a different key than without include", () => {
    renderHook(() =>
      useAirfoilSuitability({ chord_m: 0.2, speed_ms: 14 }),
    );
    const keyWithout = capturedKey;

    renderHook(() =>
      useAirfoilSuitability({ chord_m: 0.2, speed_ms: 14, include: ["e423"] }),
    );
    const keyWith = capturedKey;

    expect(keyWithout).not.toBe(keyWith);
    expect(keyWith).toMatch(/include=e423/);
  });
});
