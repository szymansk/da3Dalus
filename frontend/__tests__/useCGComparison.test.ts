/**
 * Unit tests for the useCGComparison hook (gh-437).
 *
 * Verifies that the hook returns expected data shapes and that
 * syncDesignCG sends the correct request.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useCGComparison } from "@/hooks/useCGComparison";

// Mock SWR to avoid real network requests
const mockMutate = vi.fn();
vi.mock("swr", () => ({
  default: vi.fn(() => ({
    data: {
      design_cg_x: 0.25,
      component_cg_x: 0.28,
      component_cg_y: null,
      component_cg_z: null,
      component_total_mass_kg: 2.5,
      delta_x: -0.03,
      within_tolerance: false,
    },
    error: undefined,
    isLoading: false,
    mutate: mockMutate,
  })),
}));

describe("useCGComparison", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockMutate.mockClear();
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
  });

  it("returns CG comparison data from SWR", () => {
    const { result } = renderHook(() => useCGComparison("aero-1"));

    expect(result.current.data).not.toBeNull();
    expect(result.current.data?.design_cg_x).toBe(0.25);
    expect(result.current.data?.component_cg_x).toBe(0.28);
    expect(result.current.data?.delta_x).toBe(-0.03);
    expect(result.current.data?.within_tolerance).toBe(false);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("syncDesignCG sends PUT with correct body and calls mutate", async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useCGComparison("aero-1"));

    await act(async () => {
      await result.current.syncDesignCG(0.28);
    });

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toContain("/aeroplanes/aero-1/assumptions/cg_x");
    expect(options.method).toBe("PUT");
    expect(JSON.parse(options.body)).toEqual({ estimate_value: 0.28 });
    expect(mockMutate).toHaveBeenCalled();
  });

  it("syncDesignCG is a no-op when aeroplaneId is null", async () => {
    const mockFetch = vi.fn();
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useCGComparison(null));

    await act(async () => {
      await result.current.syncDesignCG(0.28);
    });

    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("syncDesignCG throws on non-ok response", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve("Internal error"),
    });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useCGComparison("aero-1"));

    await expect(
      act(async () => {
        await result.current.syncDesignCG(0.28);
      }),
    ).rejects.toThrow("Failed to sync CG: 500");
    expect(mockMutate).not.toHaveBeenCalled();
  });
});
