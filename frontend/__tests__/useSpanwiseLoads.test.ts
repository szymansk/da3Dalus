/**
 * Unit tests for the useSpanwiseLoads hook (gh-1002).
 *
 * Mirrors the useStripForces hook: a manual fetch-based POST to
 * /aeroplanes/{id}/spanwise_loads with the same operating-point params.
 * Pins URL building, request-body construction (operating_point_id
 * round-trip), data passthrough, and the loading/error state machine.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import {
  useSpanwiseLoads,
  type SpanwiseLoadsResult,
} from "@/hooks/useSpanwiseLoads";

const FAKE_RESULT: SpanwiseLoadsResult = {
  alpha: 5.0,
  beta: 0.0,
  velocity_mps: 20.0,
  altitude_m: 100.0,
  dynamic_pressure_Pa: 242.0,
  surfaces: [
    {
      surface_name: "Main Wing",
      starboard: [
        { y_m: 0.1, chord_m: 0.3, shear_N: 50, bending_moment_Nm: 12 },
      ],
      port: [{ y_m: 0.1, chord_m: 0.3, shear_N: 50, bending_moment_Nm: 12 }],
      root_shear_N_starboard: 60,
      root_shear_N_port: 60,
      root_bending_moment_Nm_starboard: 15,
      root_bending_moment_Nm_port: 15,
    },
  ],
};

const BASE_PARAMS = {
  velocity: 20,
  alpha: 5,
  beta: 0,
  altitude: 100,
  xyz_ref: [0.183, 0, 0],
};

function okResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("useSpanwiseLoads (gh-1002)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("does not fetch and stays idle when aeroplaneId is null", async () => {
    const fetchSpy = vi.spyOn(global, "fetch");
    const { result } = renderHook(() => useSpanwiseLoads(null));

    await act(async () => {
      await result.current.run(BASE_PARAMS);
    });

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(result.current.result).toBeNull();
    expect(result.current.isRunning).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("POSTs to the spanwise_loads endpoint and stores the parsed result", async () => {
    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(okResponse(FAKE_RESULT));
    const { result } = renderHook(() => useSpanwiseLoads("aero-1"));

    await act(async () => {
      await result.current.run(BASE_PARAMS);
    });

    const [url, options] = fetchSpy.mock.calls[0];
    expect(String(url)).toContain("/aeroplanes/aero-1/spanwise_loads");
    expect(options).toMatchObject({
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    const body = JSON.parse(options!.body as string);
    expect(body).toMatchObject({
      velocity: 20,
      alpha: 5,
      beta: 0,
      altitude: 100,
      xyz_ref: [0.183, 0, 0],
    });

    expect(result.current.result).toEqual(FAKE_RESULT);
    expect(result.current.isRunning).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("sends operating_point_id when set", async () => {
    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(okResponse(FAKE_RESULT));
    const { result } = renderHook(() => useSpanwiseLoads("aero-1"));

    await act(async () => {
      await result.current.run({ ...BASE_PARAMS, operating_point_id: 42 });
    });

    const body = JSON.parse(fetchSpy.mock.calls[0][1]!.body as string);
    expect(body.operating_point_id).toBe(42);
  });

  it("omits operating_point_id when null (manual diagnostic mode)", async () => {
    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(okResponse(FAKE_RESULT));
    const { result } = renderHook(() => useSpanwiseLoads("aero-1"));

    await act(async () => {
      await result.current.run({ ...BASE_PARAMS, operating_point_id: null });
    });

    const body = JSON.parse(fetchSpy.mock.calls[0][1]!.body as string);
    expect("operating_point_id" in body).toBe(false);
  });

  it("surfaces a 422 validation error message readably and clears the result", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "validation_error",
            message:
              "OperatingPoint 42 has status 'NOT_TRIMMED'; only TRIMMED operating points may drive a trim-consistent run.",
          },
        }),
        { status: 422, headers: { "Content-Type": "application/json" } },
      ),
    );
    const { result } = renderHook(() => useSpanwiseLoads("aero-1"));

    await act(async () => {
      await result.current.run({ ...BASE_PARAMS, operating_point_id: 42 });
    });

    expect(result.current.error).toContain("Spanwise loads — invalid request");
    expect(result.current.error).toContain("NOT_TRIMMED");
    expect(result.current.result).toBeNull();
    expect(result.current.isRunning).toBe(false);
  });

  it("captures a network/throwing fetch as an error string", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new Error("network down"));
    const { result } = renderHook(() => useSpanwiseLoads("aero-1"));

    await act(async () => {
      await result.current.run(BASE_PARAMS);
    });

    expect(result.current.error).toBe("network down");
    expect(result.current.result).toBeNull();
    expect(result.current.isRunning).toBe(false);
  });
});
