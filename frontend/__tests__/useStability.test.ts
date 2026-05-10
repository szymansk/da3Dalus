import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useStability, type StabilityData } from "@/hooks/useStability";

const FAKE_STABILITY: StabilityData = {
  id: 1,
  aeroplane_id: 42,
  solver: "avl",
  neutral_point_x: 0.25,
  mac: 0.15,
  cg_x_used: 0.20,
  static_margin_pct: 33.3,
  stability_class: "stable",
  cg_range_forward: 0.17,
  cg_range_aft: 0.24,
  Cma: -1.2,
  Cnb: 0.05,
  Clb: -0.03,
  is_statically_stable: true,
  is_directionally_stable: true,
  is_laterally_stable: true,
  trim_alpha_deg: 2.5,
  trim_elevator_deg: -3.0,
  computed_at: "2026-05-08T12:00:00Z",
  status: "CURRENT",
  geometry_hash: "abc123",
};

describe("useStability", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns null data when aeroplaneId is null", () => {
    const { result } = renderHook(() => useStability(null));
    expect(result.current.data).toBeNull();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isComputing).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("fetches stability data on mount", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(FAKE_STABILITY),
    });
    const { result } = renderHook(() => useStability("42"));
    await waitFor(() => { expect(result.current.isLoading).toBe(false); });
    expect(globalThis.fetch).toHaveBeenCalledWith(expect.stringContaining("/aeroplanes/42/stability"));
    expect(result.current.data).toEqual(FAKE_STABILITY);
    expect(result.current.error).toBeNull();
  });

  it("handles 404 by setting data to null", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 404, text: () => Promise.resolve("Not found") });
    const { result } = renderHook(() => useStability("42"));
    await waitFor(() => { expect(result.current.isLoading).toBe(false); });
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("sets error on non-404 fetch failure", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 500, text: () => Promise.resolve("Internal server error") });
    const { result } = renderHook(() => useStability("42"));
    await waitFor(() => { expect(result.current.isLoading).toBe(false); });
    expect(result.current.data).toBeNull();
    expect(result.current.error).toContain("500");
  });

  it("compute() POSTs to stability_summary with design CG and refreshes cached data", async () => {
    const mockFetch = vi.fn()
      // 1. initial refresh on mount → /stability (no cached data yet)
      .mockResolvedValueOnce({ ok: false, status: 404, text: () => Promise.resolve("Not found") })
      // 2. compute → GET /assumptions to find effective cg_x
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({
          assumptions: [{ parameter_name: "cg_x", effective_value: 0.073 }],
        }),
      })
      // 3. compute → POST /stability_summary/avl
      .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve(FAKE_STABILITY) })
      // 4. refresh after compute → GET /stability
      .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve(FAKE_STABILITY) });
    globalThis.fetch = mockFetch;
    const { result } = renderHook(() => useStability("42"));
    await waitFor(() => { expect(result.current.isLoading).toBe(false); });
    await act(async () => { await result.current.compute(); });

    const stabPostCall = mockFetch.mock.calls.find(
      (c: [string, { method?: string }]) =>
        typeof c[0] === "string" && c[0].includes("/stability_summary/avl"),
    );
    expect(stabPostCall).toBeTruthy();
    expect(stabPostCall![1]).toEqual(expect.objectContaining({ method: "POST" }));
    const body = JSON.parse(String(stabPostCall![1].body));
    expect(body.xyz_ref).toEqual([0.073, 0, 0]);
    expect(result.current.data).toEqual(FAKE_STABILITY);
    expect(result.current.isComputing).toBe(false);
  });

  it("refresh() re-fetches GET endpoint", async () => {
    const mockFetch = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve({ ...FAKE_STABILITY, computed_at: "old" }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve({ ...FAKE_STABILITY, computed_at: "new" }) });
    globalThis.fetch = mockFetch;
    const { result } = renderHook(() => useStability("42"));
    await waitFor(() => { expect(result.current.isLoading).toBe(false); });
    await act(async () => { await result.current.refresh(); });
    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(result.current.data?.computed_at).toBe("new");
  });

  it("clears data when aeroplaneId becomes null", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve(FAKE_STABILITY) });
    const { result, rerender } = renderHook(({ id }) => useStability(id), { initialProps: { id: "42" as string | null } });
    await waitFor(() => { expect(result.current.data).toEqual(FAKE_STABILITY); });
    rerender({ id: null });
    expect(result.current.data).toBeNull();
  });
});
