/**
 * Unit tests for the useAnalysisStatus hook.
 *
 * Tests polling behavior, initial state, fetch on aeroplaneId change,
 * and automatic polling start/stop based on status.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";

import type { AnalysisStatus } from "@/hooks/useAnalysisStatus";
import { useAnalysisStatus } from "@/hooks/useAnalysisStatus";

const EMPTY_STATUS: AnalysisStatus = {
  op_counts: {},
  total_ops: 0,
  retrim_active: false,
  retrim_debouncing: false,
  last_computation: null,
};

function makeStatus(overrides: Partial<AnalysisStatus> = {}): AnalysisStatus {
  return { ...EMPTY_STATUS, ...overrides };
}

describe("useAnalysisStatus", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns EMPTY_STATUS initially when aeroplaneId is null", () => {
    const { result } = renderHook(() => useAnalysisStatus(null));

    expect(result.current.status).toEqual(EMPTY_STATUS);
    expect(result.current.isPolling).toBe(false);
  });

  it("fetches status on mount when aeroplaneId is provided", async () => {
    const statusData = makeStatus({
      op_counts: { TRIMMED: 5 },
      total_ops: 5,
    });
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(statusData),
    });

    const { result } = renderHook(() => useAnalysisStatus("42"));

    await waitFor(() => {
      expect(result.current.status.total_ops).toBe(5);
    });

    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock
      .calls[0][0];
    expect(calledUrl).toContain("/aeroplanes/42/analysis-status");
    expect(result.current.status.op_counts).toEqual({ TRIMMED: 5 });
  });

  it("starts polling when dirty OPs exist", async () => {
    const dirtyStatus = makeStatus({
      op_counts: { DIRTY: 3, TRIMMED: 2 },
      total_ops: 5,
    });

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(dirtyStatus),
    });

    const { result } = renderHook(() => useAnalysisStatus("42"));

    await waitFor(() => {
      expect(result.current.status.op_counts["DIRTY"]).toBe(3);
    });

    expect(result.current.isPolling).toBe(true);
  });

  it("starts polling when computing OPs exist", async () => {
    const computingStatus = makeStatus({
      op_counts: { COMPUTING: 2, TRIMMED: 3 },
      total_ops: 5,
    });

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(computingStatus),
    });

    const { result } = renderHook(() => useAnalysisStatus("42"));

    await waitFor(() => {
      expect(result.current.status.op_counts["COMPUTING"]).toBe(2);
    });

    expect(result.current.isPolling).toBe(true);
  });

  it(
    "stops polling when all trimmed",
    async () => {
      // First return dirty, then trimmed
      const dirtyStatus = makeStatus({
        op_counts: { DIRTY: 2 },
        total_ops: 2,
      });
      const trimmedStatus = makeStatus({
        op_counts: { TRIMMED: 2 },
        total_ops: 2,
      });

      let callCount = 0;
      globalThis.fetch = vi.fn().mockImplementation(() => {
        callCount++;
        const data = callCount === 1 ? dirtyStatus : trimmedStatus;
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(data),
        });
      });

      const { result } = renderHook(() => useAnalysisStatus("42"));

      // Wait for initial fetch with dirty status, then polling starts
      await waitFor(() => {
        expect(result.current.isPolling).toBe(true);
      });

      // Wait for polling to fetch trimmed and stop (poll interval is 2s)
      await waitFor(
        () => {
          expect(result.current.isPolling).toBe(false);
        },
        { timeout: 8000 },
      );
    },
    10000,
  );

  it("resets status when aeroplaneId becomes null", async () => {
    const statusData = makeStatus({
      op_counts: { TRIMMED: 3 },
      total_ops: 3,
    });
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(statusData),
    });

    const { result, rerender } = renderHook(
      ({ id }) => useAnalysisStatus(id),
      { initialProps: { id: "42" as string | null } },
    );

    await waitFor(() => {
      expect(result.current.status.total_ops).toBe(3);
    });

    rerender({ id: null });

    expect(result.current.status).toEqual(EMPTY_STATUS);
  });

  it("silently ignores fetch errors", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
    });

    const { result } = renderHook(() => useAnalysisStatus("42"));

    // Wait a tick for the effect to complete
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    // Should still have empty status — no error thrown
    expect(result.current.status).toEqual(EMPTY_STATUS);
  });

  it("starts polling when retrim_active is true", async () => {
    const activeStatus = makeStatus({
      op_counts: { TRIMMED: 5 },
      total_ops: 5,
      retrim_active: true,
    });

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(activeStatus),
    });

    const { result } = renderHook(() => useAnalysisStatus("42"));

    await waitFor(() => {
      expect(result.current.status.retrim_active).toBe(true);
    });

    expect(result.current.isPolling).toBe(true);
  });

  it("starts polling when retrim_debouncing is true", async () => {
    const debouncingStatus = makeStatus({
      op_counts: { TRIMMED: 5 },
      total_ops: 5,
      retrim_debouncing: true,
    });

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(debouncingStatus),
    });

    const { result } = renderHook(() => useAnalysisStatus("42"));

    await waitFor(() => {
      expect(result.current.status.retrim_debouncing).toBe(true);
    });

    expect(result.current.isPolling).toBe(true);
  });

  it("exposes a refresh function", async () => {
    const statusData = makeStatus({
      op_counts: { TRIMMED: 5 },
      total_ops: 5,
    });
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(statusData),
    });

    const { result } = renderHook(() => useAnalysisStatus("42"));

    await waitFor(() => {
      expect(result.current.status.total_ops).toBe(5);
    });

    expect(typeof result.current.refresh).toBe("function");

    // Call refresh and verify fetch was called again
    await act(async () => {
      await result.current.refresh();
    });

    expect(
      (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls.length,
    ).toBeGreaterThanOrEqual(2);
  });
});
