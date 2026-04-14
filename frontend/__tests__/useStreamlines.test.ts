/**
 * Unit tests for the useStreamlines hook.
 *
 * Mocks global.fetch to verify correct API calls and state transitions
 * for computing streamlines on an aeroplane.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useStreamlines, type StreamlinesParams } from "@/hooks/useStreamlines";

const FAKE_FIGURE = {
  data: [{ type: "scatter3d", x: [1, 2], y: [3, 4], z: [5, 6] }],
  layout: { title: "Streamlines" },
};

const DEFAULT_PARAMS: StreamlinesParams = {
  velocity: 20,
  alpha: 5,
  beta: 0,
  altitude: 0,
};

describe("useStreamlines", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns initial state: figure=null, isComputing=false, error=null", () => {
    const { result } = renderHook(() => useStreamlines("aero-1"));

    expect(result.current.figure).toBeNull();
    expect(result.current.isComputing).toBe(false);
    expect(result.current.error).toBeNull();
    expect(typeof result.current.computeStreamlines).toBe("function");
  });

  it("sets isComputing=true during fetch, then sets figure on success", async () => {
    let resolveFetch!: (value: Response) => void;
    const fetchPromise = new Promise<Response>((resolve) => {
      resolveFetch = resolve;
    });
    vi.spyOn(global, "fetch").mockReturnValue(fetchPromise as Promise<Response>);

    const { result } = renderHook(() => useStreamlines("aero-1"));

    // Start computing - don't await yet
    let computePromise: Promise<void>;
    act(() => {
      computePromise = result.current.computeStreamlines(DEFAULT_PARAMS);
    });

    // isComputing should be true while fetch is pending
    expect(result.current.isComputing).toBe(true);
    expect(result.current.figure).toBeNull();
    expect(result.current.error).toBeNull();

    // Resolve the fetch
    await act(async () => {
      resolveFetch(
        new Response(JSON.stringify(FAKE_FIGURE), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
      await computePromise;
    });

    expect(result.current.isComputing).toBe(false);
    expect(result.current.figure).toEqual(FAKE_FIGURE);
    expect(result.current.error).toBeNull();
  });

  it("sends correct POST request with params", async () => {
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify(FAKE_FIGURE), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { result } = renderHook(() => useStreamlines("aero-42"));

    await act(async () => {
      await result.current.computeStreamlines({
        velocity: 30,
        alpha: 10,
        beta: 2,
        altitude: 500,
      });
    });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, options] = fetchSpy.mock.calls[0];
    expect(url).toContain("/aeroplanes/aero-42/streamlines");
    expect(options).toMatchObject({
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    const body = JSON.parse(options!.body as string);
    expect(body).toEqual({
      velocity: 30,
      alpha: 10,
      beta: 2,
      altitude: 500,
    });
  });

  it("sets error string on API error (non-ok response)", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response("Internal Server Error", { status: 500 }),
    );

    const { result } = renderHook(() => useStreamlines("aero-1"));

    await act(async () => {
      await result.current.computeStreamlines(DEFAULT_PARAMS);
    });

    expect(result.current.isComputing).toBe(false);
    expect(result.current.figure).toBeNull();
    expect(result.current.error).toBe("Streamlines failed: 500 Internal Server Error");
  });

  it("sets error string on network failure", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));

    const { result } = renderHook(() => useStreamlines("aero-1"));

    await act(async () => {
      await result.current.computeStreamlines(DEFAULT_PARAMS);
    });

    expect(result.current.isComputing).toBe(false);
    expect(result.current.figure).toBeNull();
    expect(result.current.error).toBe("Failed to fetch");
  });

  it("does not fetch when aeroplaneId is null", async () => {
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify(FAKE_FIGURE), { status: 200 }),
    );

    const { result } = renderHook(() => useStreamlines(null));

    await act(async () => {
      await result.current.computeStreamlines(DEFAULT_PARAMS);
    });

    expect(fetchSpy).not.toHaveBeenCalled();
    // State should remain at initial values
    expect(result.current.figure).toBeNull();
    expect(result.current.isComputing).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("clears previous figure and error when starting a new computation", async () => {
    // First call fails
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response("Bad Request", { status: 400 }),
    );

    const { result } = renderHook(() => useStreamlines("aero-1"));

    await act(async () => {
      await result.current.computeStreamlines(DEFAULT_PARAMS);
    });
    expect(result.current.error).toBeTruthy();

    // Second call succeeds - error should be cleared immediately
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(FAKE_FIGURE), { status: 200 }),
    );

    await act(async () => {
      await result.current.computeStreamlines(DEFAULT_PARAMS);
    });

    expect(result.current.error).toBeNull();
    expect(result.current.figure).toEqual(FAKE_FIGURE);
  });
});
