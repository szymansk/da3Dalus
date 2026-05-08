/**
 * Unit tests for the useFlightEnvelope hook (gh-422).
 *
 * Verifies initial fetch, 404 handling, compute, and refresh behaviour.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import {
  useFlightEnvelope,
  type FlightEnvelopeData,
} from "@/hooks/useFlightEnvelope";

const FAKE_ENVELOPE: FlightEnvelopeData = {
  id: 1,
  aeroplane_id: 42,
  vn_curve: {
    positive: [
      { velocity_mps: 10, load_factor: 1.0 },
      { velocity_mps: 30, load_factor: 3.8 },
    ],
    negative: [
      { velocity_mps: 10, load_factor: -1.0 },
      { velocity_mps: 30, load_factor: -1.5 },
    ],
    dive_speed_mps: 45,
    stall_speed_mps: 12,
  },
  kpis: [
    {
      label: "v_stall",
      display_name: "Stall Speed",
      value: 12.0,
      unit: "m/s",
      source_op_id: null,
      confidence: "trimmed",
    },
  ],
  operating_points: [
    {
      op_id: 1,
      name: "cruise",
      velocity_mps: 20,
      load_factor: 1.0,
      status: "TRIMMED",
      label: "Cruise",
    },
  ],
  assumptions_snapshot: { mass_kg: 2.5, n_positive: 3.8 },
  computed_at: "2026-05-07T12:00:00Z",
};

describe("useFlightEnvelope", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns null data when aeroplaneId is null", () => {
    const { result } = renderHook(() => useFlightEnvelope(null));

    expect(result.current.data).toBeNull();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isComputing).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("fetches envelope data on mount", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(FAKE_ENVELOPE),
    });

    const { result } = renderHook(() => useFlightEnvelope("42"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/aeroplanes/42/flight-envelope"),
    );
    expect(result.current.data).toEqual(FAKE_ENVELOPE);
    expect(result.current.error).toBeNull();
  });

  it("handles 404 by setting data to null", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      text: () => Promise.resolve("Not found"),
    });

    const { result } = renderHook(() => useFlightEnvelope("42"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("sets error on non-404 fetch failure", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve("Internal server error"),
    });

    const { result } = renderHook(() => useFlightEnvelope("42"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toContain("500");
  });

  it("compute() POSTs and sets data from response", async () => {
    // Initial fetch returns 404
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: () => Promise.resolve("Not found"),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(FAKE_ENVELOPE),
      });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useFlightEnvelope("42"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.compute();
    });

    // Second call should be the POST
    expect(mockFetch.mock.calls[1][0]).toContain(
      "/aeroplanes/42/flight-envelope/compute",
    );
    expect(mockFetch.mock.calls[1][1]).toEqual({ method: "POST" });
    expect(result.current.data).toEqual(FAKE_ENVELOPE);
    expect(result.current.isComputing).toBe(false);
  });

  it("refresh() re-fetches GET endpoint", async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({ ...FAKE_ENVELOPE, computed_at: "old" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({ ...FAKE_ENVELOPE, computed_at: "new" }),
      });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useFlightEnvelope("42"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.refresh();
    });

    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(result.current.data?.computed_at).toBe("new");
  });

  it("clears data when aeroplaneId becomes null", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(FAKE_ENVELOPE),
    });

    const { result, rerender } = renderHook(
      ({ id }) => useFlightEnvelope(id),
      { initialProps: { id: "42" as string | null } },
    );

    await waitFor(() => {
      expect(result.current.data).toEqual(FAKE_ENVELOPE);
    });

    rerender({ id: null });

    expect(result.current.data).toBeNull();
  });
});
