import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useComputationContext } from "@/hooks/useComputationContext";

describe("useComputationContext", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches computation context for an aeroplane", async () => {
    const fakeContext = {
      v_cruise_mps: 18.0,
      reynolds: 230000,
      mac_m: 0.21,
      x_np_m: 0.085,
      target_static_margin: 0.12,
      cg_agg_m: 0.092,
      computed_at: "2026-05-10T14:30:00Z",
    };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(fakeContext),
    });

    const { result } = renderHook(() => useComputationContext("42"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual(fakeContext);
    const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(url.toString()).toContain("/assumptions/computation-context");
  });

  it("returns null when aeroplaneId is null", () => {
    const { result } = renderHook(() => useComputationContext(null));
    expect(result.current.data).toBeUndefined();
    expect(result.current.isLoading).toBe(false);
  });
});
