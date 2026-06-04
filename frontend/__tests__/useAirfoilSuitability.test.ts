/**
 * Unit tests for useAirfoilSuitability hook (gh-822).
 * Verifies that the SWR query string is built correctly per the frozen contract.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { useAirfoilSuitability } from "@/hooks/useAirfoilSuitability";

// ── Capture the SWR key ──────────────────────────────────────────
let capturedKey: string | null = undefined as unknown as string | null;

vi.mock("swr", () => ({
  default: vi.fn((key: string | null) => {
    capturedKey = key;
    return {
      data: null,
      error: null,
      isLoading: false,
    };
  }),
}));

describe("useAirfoilSuitability — query string construction", () => {
  beforeEach(() => {
    capturedKey = undefined as unknown as string | null;
  });

  it("returns null key (no fetch) when chord_m is missing", () => {
    renderHook(() =>
      useAirfoilSuitability({ chord_m: undefined, speed_ms: 14 }),
    );
    expect(capturedKey).toBeNull();
  });

  it("returns null key (no fetch) when speed_ms is missing", () => {
    renderHook(() =>
      useAirfoilSuitability({ chord_m: 0.2, speed_ms: undefined }),
    );
    expect(capturedKey).toBeNull();
  });

  it("returns null key when both missing", () => {
    renderHook(() =>
      useAirfoilSuitability({ chord_m: undefined, speed_ms: undefined }),
    );
    expect(capturedKey).toBeNull();
  });

  it("builds key with chord_m and speed_ms only when no aeroplane_id", () => {
    renderHook(() =>
      useAirfoilSuitability({ chord_m: 0.2, speed_ms: 14 }),
    );
    expect(capturedKey).not.toBeNull();
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.pathname).toBe("/airfoils/db/suitability");
    expect(url.searchParams.get("chord_m")).toBe("0.2");
    expect(url.searchParams.get("speed_ms")).toBe("14");
    expect(url.searchParams.has("aeroplane_id")).toBe(false);
  });

  it("appends aeroplane_id as UUID string verbatim when aeroplane_id is present", () => {
    const uuid = "3fa85f64-5717-4562-b3fc-2c963f66afa6";
    renderHook(() =>
      useAirfoilSuitability({ chord_m: 0.2, speed_ms: 14, aeroplane_id: uuid }),
    );
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.searchParams.get("aeroplane_id")).toBe(uuid);
  });

  it("appends mission_type when provided", () => {
    renderHook(() =>
      useAirfoilSuitability({
        chord_m: 0.2,
        speed_ms: 14,
        mission_type: "trainer",
      }),
    );
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.searchParams.get("mission_type")).toBe("trainer");
  });

  it("appends target_cl_cruise when provided", () => {
    renderHook(() =>
      useAirfoilSuitability({
        chord_m: 0.2,
        speed_ms: 14,
        target_cl_cruise: 0.6,
      }),
    );
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.searchParams.get("target_cl_cruise")).toBe("0.6");
  });

  it("appends target_cl_loiter when provided", () => {
    renderHook(() =>
      useAirfoilSuitability({
        chord_m: 0.2,
        speed_ms: 14,
        target_cl_loiter: 0.9,
      }),
    );
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.searchParams.get("target_cl_loiter")).toBe("0.9");
  });

  it("builds complete query string with all optional params", () => {
    const uuid = "3fa85f64-5717-4562-b3fc-2c963f66afa6";
    renderHook(() =>
      useAirfoilSuitability({
        chord_m: 0.3,
        speed_ms: 18,
        aeroplane_id: uuid,
        mission_type: "sport",
        target_cl_cruise: 0.7,
        target_cl_loiter: 1.0,
      }),
    );
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.searchParams.get("chord_m")).toBe("0.3");
    expect(url.searchParams.get("speed_ms")).toBe("18");
    expect(url.searchParams.get("aeroplane_id")).toBe(uuid);
    expect(url.searchParams.get("mission_type")).toBe("sport");
    expect(url.searchParams.get("target_cl_cruise")).toBe("0.7");
    expect(url.searchParams.get("target_cl_loiter")).toBe("1");
  });

  // The spec says: appends aeroplane_id as the UUID string from
  // useAeroplaneContext().aeroplaneId VERBATIM when present.
  // Since the hook accepts aeroplane_id as a param (injected by the caller
  // which uses useAeroplaneContext), the hook test verifies the verbatim pass-through.
  it("does NOT add aeroplane_id when aeroplane_id is null", () => {
    renderHook(() =>
      useAirfoilSuitability({ chord_m: 0.2, speed_ms: 14, aeroplane_id: null }),
    );
    const url = new URL(capturedKey!, "http://localhost");
    expect(url.searchParams.has("aeroplane_id")).toBe(false);
  });
});
