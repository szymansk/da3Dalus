import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { usePreviewState } from "@/hooks/usePreviewState";

const mockFetch = vi.fn();
global.fetch = mockFetch;

function mockTessellationSuccess(data: Record<string, unknown>) {
  mockFetch
    .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) })
    .mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: "SUCCESS", result: { data } }),
    });
}

describe("usePreviewState", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns empty visibleParts initially", () => {
    const { result } = renderHook(() => usePreviewState("aero-1"));
    expect(result.current.visibleParts).toEqual([]);
  });

  it("toggleWing triggers tessellation and populates visibleParts", async () => {
    const tessData = { faces: [1, 2, 3] };
    mockTessellationSuccess(tessData);

    const { result } = renderHook(() => usePreviewState("aero-1"));

    act(() => {
      result.current.toggleWing("main_wing");
    });

    await waitFor(() => {
      expect(result.current.visibleParts).toHaveLength(1);
    });
    expect(result.current.visibleParts[0]).toEqual({ data: tessData });
  });

  it("visibleParts reference is stable when loading state changes", async () => {
    const tessData = { faces: [1, 2, 3] };
    mockTessellationSuccess(tessData);

    const { result } = renderHook(() => usePreviewState("aero-1"));

    act(() => {
      result.current.toggleWing("main_wing");
    });

    await waitFor(() => {
      expect(result.current.visibleParts).toHaveLength(1);
    });

    const refAfterLoad = result.current.visibleParts;

    mockTessellationSuccess({ faces: [4, 5, 6] });
    act(() => {
      result.current.toggleWing("tail_wing");
    });

    // During loading of tail_wing, main_wing's visibleParts reference should stay stable
    // (not create a new array just because loading state toggled)
    expect(result.current.visibleParts).toBe(refAfterLoad);
  });

  it("visibleParts reference changes when data actually changes", async () => {
    const tessData1 = { faces: [1, 2, 3] };
    const tessData2 = { faces: [4, 5, 6] };
    mockTessellationSuccess(tessData1);

    const { result } = renderHook(() => usePreviewState("aero-1"));

    act(() => {
      result.current.toggleWing("main_wing");
    });

    await waitFor(() => {
      expect(result.current.visibleParts).toHaveLength(1);
    });

    const refAfterFirst = result.current.visibleParts;

    mockTessellationSuccess(tessData2);
    act(() => {
      result.current.toggleWing("tail_wing");
    });

    await waitFor(() => {
      expect(result.current.visibleParts).toHaveLength(2);
    });

    expect(result.current.visibleParts).not.toBe(refAfterFirst);
  });

  it("toggleWing hides a visible wing", async () => {
    const tessData = { faces: [1, 2, 3] };
    mockTessellationSuccess(tessData);

    const { result } = renderHook(() => usePreviewState("aero-1"));

    act(() => {
      result.current.toggleWing("main_wing");
    });

    await waitFor(() => {
      expect(result.current.visibleParts).toHaveLength(1);
    });

    act(() => {
      result.current.toggleWing("main_wing");
    });

    expect(result.current.visibleParts).toHaveLength(0);
  });

  it("resets state when aeroplaneId changes", async () => {
    const tessData = { faces: [1, 2, 3] };
    mockTessellationSuccess(tessData);

    const { result, rerender } = renderHook(
      ({ id }) => usePreviewState(id),
      { initialProps: { id: "aero-1" } },
    );

    act(() => {
      result.current.toggleWing("main_wing");
    });

    await waitFor(() => {
      expect(result.current.visibleParts).toHaveLength(1);
    });

    rerender({ id: "aero-2" });

    expect(result.current.visibleParts).toHaveLength(0);
  });

  it("isAnyLoading reflects loading state", async () => {
    mockFetch
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: "PENDING" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: "SUCCESS", result: { data: { x: 1 } } }),
      });

    const { result } = renderHook(() => usePreviewState("aero-1"));

    act(() => {
      result.current.toggleWing("wing_a");
    });

    await waitFor(() => {
      expect(result.current.isAnyLoading).toBe(true);
    });

    await waitFor(() => {
      expect(result.current.isAnyLoading).toBe(false);
    });
  });
});
