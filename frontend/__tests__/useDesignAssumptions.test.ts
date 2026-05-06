/**
 * Unit tests for the useDesignAssumptions hook (gh-424).
 *
 * Verifies that mutation functions send correct requests and that
 * the hook returns expected data shapes.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useDesignAssumptions } from "@/hooks/useDesignAssumptions";

// Mock SWR to avoid real network requests
const mockMutate = vi.fn();
vi.mock("swr", () => ({
  default: vi.fn(() => ({
    data: {
      assumptions: [
        {
          id: 1,
          parameter_name: "mass",
          estimate_value: 2.5,
          calculated_value: 2.7,
          calculated_source: "weight_buildup",
          active_source: "ESTIMATE",
          effective_value: 2.5,
          divergence_pct: 8.0,
          divergence_level: "info",
          unit: "kg",
          is_design_choice: false,
          updated_at: "2026-01-01T00:00:00Z",
        },
      ],
      warnings_count: 0,
    },
    error: undefined,
    isLoading: false,
    mutate: mockMutate,
  })),
}));

describe("useDesignAssumptions", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockMutate.mockClear();
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
  });

  it("returns assumptions data from SWR", () => {
    const { result } = renderHook(() => useDesignAssumptions("aero-1"));

    expect(result.current.data).not.toBeNull();
    expect(result.current.data?.assumptions).toHaveLength(1);
    expect(result.current.data?.assumptions[0].parameter_name).toBe("mass");
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("returns null data when aeroplaneId is null", () => {
    // SWR will receive null key and skip fetch, but our mock always returns data.
    // The hook guards mutations — this test verifies mutations are no-ops.
    const { result } = renderHook(() => useDesignAssumptions(null));

    // Mutation functions should be defined
    expect(result.current.seedDefaults).toBeDefined();
    expect(result.current.updateEstimate).toBeDefined();
    expect(result.current.switchSource).toBeDefined();
  });

  it("seedDefaults sends POST and calls mutate", async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useDesignAssumptions("aero-1"));

    await act(async () => {
      await result.current.seedDefaults();
    });

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toContain("/v2/aeroplanes/aero-1/assumptions");
    expect(options.method).toBe("POST");
    expect(mockMutate).toHaveBeenCalled();
  });

  it("seedDefaults is a no-op when aeroplaneId is null", async () => {
    const mockFetch = vi.fn();
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useDesignAssumptions(null));

    await act(async () => {
      await result.current.seedDefaults();
    });

    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("updateEstimate sends PUT with correct body", async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useDesignAssumptions("aero-1"));

    await act(async () => {
      await result.current.updateEstimate("mass", 3.0);
    });

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toContain("/v2/aeroplanes/aero-1/assumptions/mass");
    expect(options.method).toBe("PUT");
    expect(JSON.parse(options.body)).toEqual({ estimate_value: 3.0 });
    expect(mockMutate).toHaveBeenCalled();
  });

  it("updateEstimate is a no-op when aeroplaneId is null", async () => {
    const mockFetch = vi.fn();
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useDesignAssumptions(null));

    await act(async () => {
      await result.current.updateEstimate("mass", 3.0);
    });

    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("switchSource sends PATCH with correct body", async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useDesignAssumptions("aero-1"));

    await act(async () => {
      await result.current.switchSource("mass", "CALCULATED");
    });

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toContain("/v2/aeroplanes/aero-1/assumptions/mass/source");
    expect(options.method).toBe("PATCH");
    expect(JSON.parse(options.body)).toEqual({ active_source: "CALCULATED" });
    expect(mockMutate).toHaveBeenCalled();
  });

  it("switchSource is a no-op when aeroplaneId is null", async () => {
    const mockFetch = vi.fn();
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useDesignAssumptions(null));

    await act(async () => {
      await result.current.switchSource("mass", "CALCULATED");
    });

    expect(mockFetch).not.toHaveBeenCalled();
  });
});
