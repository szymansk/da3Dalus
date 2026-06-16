/**
 * Unit tests for the useSparSizing hook (gh-1008).
 *
 * Mirrors useSpanwiseLoads: a manual fetch-based POST to
 * /aeroplanes/{id}/spanwise_loads_with_sizing. Pins URL + query-string
 * building for the sizing params (material_id, shape, and the optional
 * safety_factor_j / packing_factor / sigma_allow_mpa_override / cap_width_mm),
 * the operating-point request body, data passthrough, and the
 * loading/error state machine.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import {
  useSparSizing,
  type SpanwiseLoadsWithSizingResult,
  type SparSizingParams,
} from "@/hooks/useSparSizing";

const FAKE_RESULT: SpanwiseLoadsWithSizingResult = {
  alpha: 2.0,
  velocity_mps: 30.0,
  altitude_m: 0.0,
  dynamic_pressure_Pa: 551.25,
  surfaces: [],
  spar_sizing: [
    {
      surface_name: "Main Wing",
      shape: "tube",
      material_name: "Carbon Fiber",
      sigma_allow_mpa: 500,
      density_kg_m3: 1600,
      g_limit: 4,
      g_limit_fallback: false,
      safety_factor_j: 1.5,
      packing_factor: 0.8,
      stations: [],
      root_station: {
        y_m: 0,
        chord_m: 0.3,
        profile_thickness_mm: 36,
        outer_mm: 28.8,
        tc_ratio: 0.12,
        tc_fallback: false,
        m_design_Nm: 24000,
        required_W_mm3: 48000,
        solved_mm: 0.5,
        feasible: true,
        infeasibility_reason: null,
        cross_section_area_mm2: 45,
      },
      spar_mass_half_kg: 0.4,
      spar_mass_full_kg: 0.8,
      tc_fallback_warning: null,
    },
  ],
};

const BASE_OP = {
  velocity: 30,
  alpha: 2,
  beta: 0,
  altitude: 0,
  xyz_ref: [0.183, 0, 0],
};

const BASE_SIZING: SparSizingParams = {
  material_id: 7,
  shape: "tube",
};

function okResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("useSparSizing (gh-1008)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("does not fetch and stays idle when aeroplaneId is null", async () => {
    const fetchSpy = vi.spyOn(global, "fetch");
    const { result } = renderHook(() => useSparSizing(null));

    await act(async () => {
      await result.current.run(BASE_OP, BASE_SIZING);
    });

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(result.current.result).toBeNull();
    expect(result.current.isRunning).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("POSTs to spanwise_loads_with_sizing with required query params + op body", async () => {
    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(okResponse(FAKE_RESULT));
    const { result } = renderHook(() => useSparSizing("aero-1"));

    await act(async () => {
      await result.current.run(BASE_OP, BASE_SIZING);
    });

    const [url, options] = fetchSpy.mock.calls[0];
    const u = new URL(String(url), "http://x");
    expect(u.pathname).toContain("/aeroplanes/aero-1/spanwise_loads_with_sizing");
    expect(u.searchParams.get("material_id")).toBe("7");
    expect(u.searchParams.get("shape")).toBe("tube");
    // optional params omitted when not provided
    expect(u.searchParams.has("safety_factor_j")).toBe(false);
    expect(u.searchParams.has("packing_factor")).toBe(false);
    expect(u.searchParams.has("sigma_allow_mpa_override")).toBe(false);
    expect(u.searchParams.has("cap_width_mm")).toBe(false);

    expect(options).toMatchObject({ method: "POST" });
    const body = JSON.parse(options!.body as string);
    expect(body).toMatchObject({ velocity: 30, alpha: 2, beta: 0, altitude: 0 });
    expect("operating_point_id" in body).toBe(false);

    expect(result.current.result).toEqual(FAKE_RESULT);
    expect(result.current.error).toBeNull();
    expect(result.current.isRunning).toBe(false);
  });

  it("includes all optional sizing params and operating_point_id when set", async () => {
    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(okResponse(FAKE_RESULT));
    const { result } = renderHook(() => useSparSizing("aero-1"));

    await act(async () => {
      await result.current.run(
        { ...BASE_OP, operating_point_id: 42 },
        {
          material_id: 3,
          shape: "capped",
          safety_factor_j: 2,
          packing_factor: 0.7,
          sigma_allow_mpa_override: 350,
          cap_width_mm: 10,
        },
      );
    });

    const [url, options] = fetchSpy.mock.calls[0];
    const u = new URL(String(url), "http://x");
    expect(u.searchParams.get("material_id")).toBe("3");
    expect(u.searchParams.get("shape")).toBe("capped");
    expect(u.searchParams.get("safety_factor_j")).toBe("2");
    expect(u.searchParams.get("packing_factor")).toBe("0.7");
    expect(u.searchParams.get("sigma_allow_mpa_override")).toBe("350");
    expect(u.searchParams.get("cap_width_mm")).toBe("10");

    const body = JSON.parse(options!.body as string);
    expect(body.operating_point_id).toBe(42);
  });

  it("surfaces a 422 validation error readably and clears the result", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "validation_error",
            message: "sigma_allow must be positive, got 0",
          },
        }),
        { status: 422, headers: { "Content-Type": "application/json" } },
      ),
    );
    const { result } = renderHook(() => useSparSizing("aero-1"));

    await act(async () => {
      await result.current.run(BASE_OP, {
        ...BASE_SIZING,
        sigma_allow_mpa_override: 0,
      });
    });

    expect(result.current.error).toContain("Spar sizing — invalid request");
    expect(result.current.error).toContain("sigma_allow must be positive");
    expect(result.current.result).toBeNull();
    expect(result.current.isRunning).toBe(false);
  });

  it("captures a throwing fetch as an error string", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new Error("network down"));
    const { result } = renderHook(() => useSparSizing("aero-1"));

    await act(async () => {
      await result.current.run(BASE_OP, BASE_SIZING);
    });

    expect(result.current.error).toBe("network down");
    expect(result.current.result).toBeNull();
    expect(result.current.isRunning).toBe(false);
  });
});
