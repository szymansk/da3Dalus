/**
 * Unit tests for the useMatchingChart hook — gh-492.
 *
 * Covers: URL construction, parameter filtering, null aeroplaneId,
 * SWR key computation, and hook return shape.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";

// Mock SWR to avoid network calls
vi.mock("swr", () => ({
  default: vi.fn(),
}));

vi.mock("@/lib/fetcher", () => ({
  fetcher: vi.fn(),
}));

import useSWR from "swr";
import { useMatchingChart } from "@/hooks/useMatchingChart";
import type { MatchingChartData } from "@/hooks/useMatchingChart";

const mockedUseSWR = vi.mocked(useSWR);

const MOCK_DATA: MatchingChartData = {
  ws_range_n_m2: [100, 200, 300],
  constraints: [
    {
      name: "Takeoff",
      t_w_points: [0.2, 0.2, 0.2],
      ws_max: null,
      color: "#FF8400",
      binding: true,
      hover_text: "Takeoff",
    },
  ],
  design_point: { ws_n_m2: 660, t_w: 0.178 },
  feasibility: "feasible",
  warnings: [],
};

const SWR_OK = {
  data: MOCK_DATA,
  error: undefined,
  isLoading: false,
  mutate: vi.fn(),
  isValidating: false,
};

const SWR_LOADING = {
  data: undefined,
  error: undefined,
  isLoading: true,
  mutate: vi.fn(),
  isValidating: true,
};

const SWR_ERROR = {
  data: undefined,
  error: new Error("404 Not Found"),
  isLoading: false,
  mutate: vi.fn(),
  isValidating: false,
};

describe("useMatchingChart", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: return OK state
    mockedUseSWR.mockReturnValue(SWR_OK as ReturnType<typeof useSWR>);
  });

  it("calls useSWR with null url when aeroplaneId is null", () => {
    renderHook(() => useMatchingChart(null));
    expect(mockedUseSWR).toHaveBeenCalledWith(null, expect.any(Function), expect.any(Object));
  });

  it("calls useSWR with correct url when aeroplaneId is set", () => {
    renderHook(() => useMatchingChart("aero-1"));
    const [url] = mockedUseSWR.mock.calls[0];
    expect(url).toContain("/aeroplanes/aero-1/matching-chart");
    expect(url).toContain("mode=rc_runway");
  });

  it("URL-encodes aeroplaneId with special characters", () => {
    renderHook(() => useMatchingChart("aero/test id"));
    const [url] = mockedUseSWR.mock.calls[0];
    expect(url).toContain("aero%2Ftest%20id");
  });

  it("includes mode=rc_runway by default", () => {
    renderHook(() => useMatchingChart("aero-1"));
    const [url] = mockedUseSWR.mock.calls[0];
    expect(url).toContain("mode=rc_runway");
  });

  it("includes custom mode in URL", () => {
    renderHook(() => useMatchingChart("aero-1", { mode: "uav_runway" }));
    const [url] = mockedUseSWR.mock.calls[0];
    expect(url).toContain("mode=uav_runway");
  });

  it("includes s_runway when sRunway is set", () => {
    renderHook(() => useMatchingChart("aero-1", { sRunway: 150 }));
    const [url] = mockedUseSWR.mock.calls[0];
    expect(url).toContain("s_runway=150");
  });

  it("omits s_runway when sRunway is null", () => {
    renderHook(() => useMatchingChart("aero-1", { sRunway: null }));
    const [url] = mockedUseSWR.mock.calls[0];
    expect(url).not.toContain("s_runway");
  });

  it("omits s_runway when sRunway is undefined", () => {
    renderHook(() => useMatchingChart("aero-1", { sRunway: undefined }));
    const [url] = mockedUseSWR.mock.calls[0];
    expect(url).not.toContain("s_runway");
  });

  it("includes v_s_target when vSTarget is set", () => {
    renderHook(() => useMatchingChart("aero-1", { vSTarget: 10 }));
    const [url] = mockedUseSWR.mock.calls[0];
    expect(url).toContain("v_s_target=10");
  });

  it("omits v_s_target when vSTarget is null", () => {
    renderHook(() => useMatchingChart("aero-1", { vSTarget: null }));
    const [url] = mockedUseSWR.mock.calls[0];
    expect(url).not.toContain("v_s_target");
  });

  it("includes gamma_climb_deg when gammaClimbDeg is set", () => {
    renderHook(() => useMatchingChart("aero-1", { gammaClimbDeg: 6 }));
    const [url] = mockedUseSWR.mock.calls[0];
    expect(url).toContain("gamma_climb_deg=6");
  });

  it("omits gamma_climb_deg when gammaClimbDeg is null", () => {
    renderHook(() => useMatchingChart("aero-1", { gammaClimbDeg: null }));
    const [url] = mockedUseSWR.mock.calls[0];
    expect(url).not.toContain("gamma_climb_deg");
  });

  it("includes v_cruise_mps when vCruiseMps is set", () => {
    renderHook(() => useMatchingChart("aero-1", { vCruiseMps: 25 }));
    const [url] = mockedUseSWR.mock.calls[0];
    expect(url).toContain("v_cruise_mps=25");
  });

  it("omits v_cruise_mps when vCruiseMps is null", () => {
    renderHook(() => useMatchingChart("aero-1", { vCruiseMps: null }));
    const [url] = mockedUseSWR.mock.calls[0];
    expect(url).not.toContain("v_cruise_mps");
  });

  it("passes revalidateOnFocus: false to useSWR", () => {
    renderHook(() => useMatchingChart("aero-1"));
    const [, , options] = mockedUseSWR.mock.calls[0];
    expect((options as { revalidateOnFocus: boolean }).revalidateOnFocus).toBe(false);
  });

  it("returns data from SWR", () => {
    mockedUseSWR.mockReturnValue(SWR_OK as ReturnType<typeof useSWR>);
    const { result } = renderHook(() => useMatchingChart("aero-1"));
    expect(result.current.data).toBe(MOCK_DATA);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeUndefined();
  });

  it("returns loading state from SWR", () => {
    mockedUseSWR.mockReturnValue(SWR_LOADING as ReturnType<typeof useSWR>);
    const { result } = renderHook(() => useMatchingChart("aero-1"));
    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it("returns error state from SWR", () => {
    mockedUseSWR.mockReturnValue(SWR_ERROR as ReturnType<typeof useSWR>);
    const { result } = renderHook(() => useMatchingChart("aero-1"));
    expect(result.current.error).toBeTruthy();
    expect(result.current.data).toBeUndefined();
  });

  it("returns mutate function", () => {
    mockedUseSWR.mockReturnValue(SWR_OK as ReturnType<typeof useSWR>);
    const { result } = renderHook(() => useMatchingChart("aero-1"));
    expect(typeof result.current.mutate).toBe("function");
  });

  it("builds URL with all params set", () => {
    renderHook(() =>
      useMatchingChart("aero-1", {
        mode: "uav_belly_land",
        sRunway: 200,
        vSTarget: 12,
        gammaClimbDeg: 4,
        vCruiseMps: 30,
      }),
    );
    const [url] = mockedUseSWR.mock.calls[0];
    expect(url).toContain("mode=uav_belly_land");
    expect(url).toContain("s_runway=200");
    expect(url).toContain("v_s_target=12");
    expect(url).toContain("gamma_climb_deg=4");
    expect(url).toContain("v_cruise_mps=30");
  });

  it("handles rc_hand_launch mode", () => {
    renderHook(() => useMatchingChart("aero-1", { mode: "rc_hand_launch" }));
    const [url] = mockedUseSWR.mock.calls[0];
    expect(url).toContain("mode=rc_hand_launch");
  });
});
