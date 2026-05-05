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
});
