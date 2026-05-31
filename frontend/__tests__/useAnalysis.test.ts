/**
 * Unit tests for the useAnalysis hook.
 *
 * Verifies that AlphaSweepParams matches the backend's AlphaSweepRequest
 * schema and that runAlphaSweep sends the correct request body (gh-411).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useAnalysis, type AlphaSweepParams } from "@/hooks/useAnalysis";

const FAKE_RESPONSE = {
  analysis: {
    coefficients: { CL: [0.1, 0.5], CD: [0.01, 0.03], Cm: [-0.02, -0.05] },
    flight_condition: { alpha: [-5, 15] },
  },
};

describe("useAnalysis", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("AlphaSweepParams has fields matching backend AlphaSweepRequest", () => {
    const params: AlphaSweepParams = {
      alpha_start: -5,
      alpha_end: 15,
      alpha_num: 21,
      velocity: 14,
      beta: 0,
      altitude: 100,
      xyz_ref: [0, 0, 0],
    };

    // Verify the required field names exist at runtime
    expect(params).toHaveProperty("alpha_start");
    expect(params).toHaveProperty("alpha_end");
    expect(params).toHaveProperty("alpha_num");
    expect(params).toHaveProperty("velocity");
    expect(params).toHaveProperty("altitude");
    expect(params).toHaveProperty("xyz_ref");

    // These old field names must NOT exist in the interface
    expect(params).not.toHaveProperty("alpha_start_deg");
    expect(params).not.toHaveProperty("alpha_end_deg");
    expect(params).not.toHaveProperty("alpha_step_deg");
    expect(params).not.toHaveProperty("velocity_m_s");
    expect(params).not.toHaveProperty("xyz_ref_m");
  });

  it("sends all fields to the backend API", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(FAKE_RESPONSE),
    });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useAnalysis("aero-1"));

    const params: AlphaSweepParams = {
      alpha_start: -5,
      alpha_end: 15,
      alpha_num: 21,
      velocity: 14,
      beta: 0,
      altitude: 100,
      xyz_ref: [0.1, 0, 0],
    };

    await act(async () => {
      await result.current.runAlphaSweep(params);
    });

    expect(mockFetch).toHaveBeenCalledOnce();
    const body = JSON.parse(mockFetch.mock.calls[0][1].body);

    expect(body).toStrictEqual({
      alpha_start: -5,
      alpha_end: 15,
      alpha_num: 21,
      velocity: 14,
      beta: 0,
      altitude: 100,
      xyz_ref: [0.1, 0, 0],
    });
  });

  it("extracts CL/CD/Cm/alpha from nested API response", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(FAKE_RESPONSE),
    });

    const { result } = renderHook(() => useAnalysis("aero-1"));

    await act(async () => {
      await result.current.runAlphaSweep({
        alpha_start: -5,
        alpha_end: 15,
        alpha_num: 21,
        velocity: 14,
        beta: 0,
        altitude: 0,
        xyz_ref: [0, 0, 0],
      });
    });

    expect(result.current.result).toEqual({
      CL: [0.1, 0.5],
      CD: [0.01, 0.03],
      Cm: [-0.02, -0.05],
      alpha: [-5, 15],
    });
  });

  it("extracts speed_polar curves from the response", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          analysis: {
            coefficients: { CL: [0.5], CD: [0.02], Cm: [0.0] },
            flight_condition: { alpha: [2] },
          },
          speed_polar: {
            base_mass_kg: 1.5,
            s_ref: 0.225,
            rho: 1.225,
            altitude: 0,
            curves: [
              {
                mass_kg: 1.5,
                is_base: true,
                V: [12],
                w: [0.5],
                cl: [0.5],
                cd: [0.02],
                v_stall: 10,
                v_min_sink: 12,
                w_min: 0.5,
                v_best_glide: 13,
                ld_max: 25,
              },
            ],
            v_axis_min: 5.5,
            v_axis_max: 40.0,
          },
        }),
    });

    const { result } = renderHook(() => useAnalysis("aero-1"));
    await act(async () => {
      await result.current.runAlphaSweep({
        alpha_start: 0,
        alpha_end: 5,
        alpha_num: 2,
        velocity: 14,
        beta: 0,
        altitude: 0,
        xyz_ref: [0, 0, 0],
        masses_kg: [1.5],
      });
    });

    expect(result.current.speedPolar?.base_mass_kg).toBe(1.5);
    expect(result.current.speedPolar?.curves).toHaveLength(1);
    expect(result.current.speedPolar?.curves[0].is_base).toBe(true);
    expect(result.current.speedPolar?.v_axis_min).toBe(5.5);
    expect(result.current.speedPolar?.v_axis_max).toBe(40.0);
  });

  it("leaves speedPolar null when response omits speed_polar", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(FAKE_RESPONSE),
    });

    const { result } = renderHook(() => useAnalysis("aero-1"));
    await act(async () => {
      await result.current.runAlphaSweep({
        alpha_start: -5,
        alpha_end: 15,
        alpha_num: 21,
        velocity: 14,
        beta: 0,
        altitude: 0,
        xyz_ref: [0, 0, 0],
      });
    });

    expect(result.current.result).not.toBeNull();
    expect(result.current.speedPolar).toBeNull();
  });
});
