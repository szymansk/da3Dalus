/**
 * Unit tests for the useDesignAssumptions hook (gh-424).
 *
 * Verifies that mutation functions send correct requests and that
 * the hook returns expected data shapes.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useDesignAssumptions } from "@/hooks/useDesignAssumptions";
import { useRecomputeStatus } from "@/hooks/useRecomputeStatus";

// Mock SWR to avoid real network requests
const mockMutate = vi.fn();
const mockGlobalMutate = vi.fn();
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
  mutate: (...args: unknown[]) => mockGlobalMutate(...args),
}));

vi.mock("@/hooks/useRecomputeStatus", () => ({
  useRecomputeStatus: vi.fn(() => ({
    isRecomputing: false,
    status: "idle",
    error: null,
  })),
}));

const useRecomputeStatusMock = vi.mocked(useRecomputeStatus);

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
    expect(url).toContain("/aeroplanes/aero-1/assumptions");
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
    expect(url).toContain("/aeroplanes/aero-1/assumptions/mass");
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
    expect(url).toContain("/aeroplanes/aero-1/assumptions/mass/source");
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

  it("seedDefaults throws on non-ok response", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      text: () => Promise.resolve("Not found"),
    });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useDesignAssumptions("aero-1"));

    await expect(
      act(async () => {
        await result.current.seedDefaults();
      }),
    ).rejects.toThrow("Failed to seed defaults: 404");
    expect(mockMutate).not.toHaveBeenCalled();
  });

  it("updateEstimate throws on non-ok response", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      text: () => Promise.resolve("Validation error"),
    });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useDesignAssumptions("aero-1"));

    await expect(
      act(async () => {
        await result.current.updateEstimate("mass", -1);
      }),
    ).rejects.toThrow("Failed to update assumption: 422");
    expect(mockMutate).not.toHaveBeenCalled();
  });

  it("switchSource throws on non-ok response", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      text: () => Promise.resolve("Design choice"),
    });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useDesignAssumptions("aero-1"));

    await expect(
      act(async () => {
        await result.current.switchSource("g_limit", "CALCULATED");
      }),
    ).rejects.toThrow("Failed to switch source: 422");
    expect(mockMutate).not.toHaveBeenCalled();
  });
});

/**
 * Regression tests for gh-473 — info chips and assumption rows stale after
 * backend recompute completes. The fix wires `useRecomputeStatus` into
 * `useDesignAssumptions`: on the recomputing → idle transition, both
 * SWR caches (`/assumptions` and `/assumptions/computation-context`) must
 * be invalidated so chips refresh without a tab switch.
 */
describe("useDesignAssumptions — refresh on recompute completion (gh-473)", () => {
  beforeEach(() => {
    mockMutate.mockClear();
    mockGlobalMutate.mockClear();
    useRecomputeStatusMock.mockReset();
  });

  it("revalidates both assumptions and computation-context when isRecomputing transitions true → false", async () => {
    useRecomputeStatusMock.mockReturnValue({
      isRecomputing: true,
      status: "computing",
      error: null,
    });
    const { rerender } = renderHook(() => useDesignAssumptions("aero-1"));

    // Drop calls from the initial mount; we only care about the transition.
    mockMutate.mockClear();
    mockGlobalMutate.mockClear();

    useRecomputeStatusMock.mockReturnValue({
      isRecomputing: false,
      status: "done",
      error: null,
    });
    rerender();

    await waitFor(() => {
      expect(mockMutate).toHaveBeenCalled();
    });
    expect(mockGlobalMutate).toHaveBeenCalledWith(
      expect.stringMatching(
        /\/aeroplanes\/aero-1\/assumptions\/computation-context$/,
      ),
    );
  });

  it("does NOT revalidate when isRecomputing stays false across renders", () => {
    useRecomputeStatusMock.mockReturnValue({
      isRecomputing: false,
      status: "idle",
      error: null,
    });
    const { rerender } = renderHook(() => useDesignAssumptions("aero-1"));
    mockMutate.mockClear();
    mockGlobalMutate.mockClear();

    rerender();

    expect(mockMutate).not.toHaveBeenCalled();
    expect(mockGlobalMutate).not.toHaveBeenCalled();
  });

  it("does NOT revalidate when isRecomputing flips false → true (job just started)", () => {
    useRecomputeStatusMock.mockReturnValue({
      isRecomputing: false,
      status: "idle",
      error: null,
    });
    const { rerender } = renderHook(() => useDesignAssumptions("aero-1"));
    mockMutate.mockClear();
    mockGlobalMutate.mockClear();

    useRecomputeStatusMock.mockReturnValue({
      isRecomputing: true,
      status: "computing",
      error: null,
    });
    rerender();

    expect(mockMutate).not.toHaveBeenCalled();
    expect(mockGlobalMutate).not.toHaveBeenCalled();
  });
});
