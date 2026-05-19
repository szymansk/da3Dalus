/**
 * Unit tests for the useStripForces hook — gh-577 operating_point_id round-trip.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useStripForces } from "@/hooks/useStripForces";

const FAKE_RESULT = {
  alpha: 4.2,
  beta: 0.0,
  mach: 0.0,
  sref: 1.0,
  cref: 1.0,
  bref: 1.0,
  surfaces: [],
};

describe("useStripForces.runAll (gh-577)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("sends operating_point_id when set", async () => {
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify(FAKE_RESULT), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const { result } = renderHook(() => useStripForces("aero-1"));
    await act(async () => {
      await result.current.runAll({
        velocity: 20,
        alpha: 5,
        beta: 0,
        altitude: 100,
        xyz_ref: [0.183, 0, 0],
        operating_point_id: 42,
      });
    });
    const [, options] = fetchSpy.mock.calls[0];
    const body = JSON.parse(options!.body as string);
    expect(body.operating_point_id).toBe(42);
  });

  it("omits operating_point_id when null (manual diagnostic mode)", async () => {
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify(FAKE_RESULT), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const { result } = renderHook(() => useStripForces("aero-1"));
    await act(async () => {
      await result.current.runAll({
        velocity: 20,
        alpha: 5,
        beta: 0,
        altitude: 100,
        xyz_ref: [0, 0, 0],
        operating_point_id: null,
      });
    });
    const [, options] = fetchSpy.mock.calls[0];
    const body = JSON.parse(options!.body as string);
    expect("operating_point_id" in body).toBe(false);
  });

  it("surfaces a 422 validation error message readably", async () => {
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
    const { result } = renderHook(() => useStripForces("aero-1"));
    await act(async () => {
      await result.current.runAll({
        velocity: 20,
        alpha: 5,
        beta: 0,
        altitude: 100,
        xyz_ref: [0, 0, 0],
        operating_point_id: 42,
      });
    });
    expect(result.current.error).toContain("Strip forces — invalid request");
    expect(result.current.error).toContain("NOT_TRIMMED");
  });
});
