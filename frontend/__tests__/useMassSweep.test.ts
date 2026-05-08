import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useMassSweep, type MassSweepData } from "@/hooks/useMassSweep";

const FAKE_SWEEP: MassSweepData = {
  s_ref: 0.42,
  cl_max: 1.5,
  velocity: 15.0,
  altitude: 0.0,
  points: [
    { mass_kg: 1.0, wing_loading_pa: 23.4, stall_speed_ms: 8.1, required_cl: 0.3, cl_margin: 1.2 },
    { mass_kg: 2.0, wing_loading_pa: 46.8, stall_speed_ms: 11.5, required_cl: 0.6, cl_margin: 0.9 },
    { mass_kg: 3.0, wing_loading_pa: 70.1, stall_speed_ms: 14.1, required_cl: 0.9, cl_margin: 0.6 },
    { mass_kg: 4.0, wing_loading_pa: 93.5, stall_speed_ms: 16.3, required_cl: 1.2, cl_margin: 0.3 },
    { mass_kg: 5.0, wing_loading_pa: 116.9, stall_speed_ms: 18.2, required_cl: 1.5, cl_margin: 0.0 },
    { mass_kg: 6.0, wing_loading_pa: 140.3, stall_speed_ms: 19.9, required_cl: 1.8, cl_margin: -0.3 },
  ],
};

describe("useMassSweep", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns null data when aeroplaneId is null", () => {
    const { result } = renderHook(() => useMassSweep(null));

    expect(result.current.data).toBeNull();
    expect(result.current.isComputing).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("compute() POSTs mass sweep request and sets data", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(FAKE_SWEEP),
    });

    const { result } = renderHook(() => useMassSweep("42"));

    await act(async () => {
      await result.current.compute({ velocity: 15, altitude: 0 });
    });

    expect(globalThis.fetch).toHaveBeenCalledOnce();
    const [url, opts] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain("/aeroplanes/42/mass_sweep");
    expect(opts.method).toBe("POST");
    const body = JSON.parse(opts.body);
    expect(body.velocity).toBe(15);
    expect(body.altitude).toBe(0);
    expect(body.masses_kg).toBeDefined();
    expect(body.masses_kg.length).toBeGreaterThan(0);

    expect(result.current.data).toEqual(FAKE_SWEEP);
    expect(result.current.isComputing).toBe(false);
  });

  it("sets error on failed compute", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve("Internal server error"),
    });

    const { result } = renderHook(() => useMassSweep("42"));

    await act(async () => {
      await result.current.compute({ velocity: 15, altitude: 0 });
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toContain("500");
    expect(result.current.isComputing).toBe(false);
  });

  it("sets isComputing during compute", async () => {
    let resolvePromise: (value: unknown) => void;
    const pending = new Promise((resolve) => {
      resolvePromise = resolve;
    });
    globalThis.fetch = vi.fn().mockReturnValue(pending);

    const { result } = renderHook(() => useMassSweep("42"));

    act(() => {
      result.current.compute({ velocity: 15, altitude: 0 });
    });

    await waitFor(() => {
      expect(result.current.isComputing).toBe(true);
    });

    await act(async () => {
      resolvePromise!({
        ok: true,
        status: 200,
        json: () => Promise.resolve(FAKE_SWEEP),
      });
    });

    await waitFor(() => {
      expect(result.current.isComputing).toBe(false);
    });
  });

  it("clears previous error on new compute", async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: () => Promise.resolve("Server error"),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(FAKE_SWEEP),
      });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useMassSweep("42"));

    await act(async () => {
      await result.current.compute({ velocity: 15, altitude: 0 });
    });
    expect(result.current.error).toContain("500");

    await act(async () => {
      await result.current.compute({ velocity: 15, altitude: 0 });
    });
    expect(result.current.error).toBeNull();
    expect(result.current.data).toEqual(FAKE_SWEEP);
  });

  it("clears data when aeroplaneId changes", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(FAKE_SWEEP),
    });

    const { result, rerender } = renderHook(
      ({ id }) => useMassSweep(id),
      { initialProps: { id: "42" as string | null } },
    );

    await act(async () => {
      await result.current.compute({ velocity: 15, altitude: 0 });
    });
    expect(result.current.data).toEqual(FAKE_SWEEP);

    rerender({ id: "99" });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("clears data when aeroplaneId becomes null", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(FAKE_SWEEP),
    });

    const { result, rerender } = renderHook(
      ({ id }) => useMassSweep(id),
      { initialProps: { id: "42" as string | null } },
    );

    await act(async () => {
      await result.current.compute({ velocity: 15, altitude: 0 });
    });
    expect(result.current.data).toEqual(FAKE_SWEEP);

    rerender({ id: null });

    expect(result.current.data).toBeNull();
  });

  it("uses custom masses when provided", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(FAKE_SWEEP),
    });

    const { result } = renderHook(() => useMassSweep("42"));

    const customMasses = [1, 2, 3, 4, 5];
    await act(async () => {
      await result.current.compute({ velocity: 20, altitude: 100, masses: customMasses });
    });

    const body = JSON.parse(
      (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].body,
    );
    expect(body.masses_kg).toEqual(customMasses);
    expect(body.velocity).toBe(20);
    expect(body.altitude).toBe(100);
  });
});
