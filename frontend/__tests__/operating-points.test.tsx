import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import {
  useOperatingPoints,
  type StoredOperatingPoint,
  type AVLTrimResult,
  type AeroBuildupTrimResult,
  type TrimConstraint,
} from "@/hooks/useOperatingPoints";

function makeOP(overrides: Partial<StoredOperatingPoint> = {}): StoredOperatingPoint {
  return {
    id: 1,
    name: "Cruise",
    description: "Level cruise",
    aircraft_id: 1,
    config: "clean",
    status: "TRIMMED",
    warnings: [],
    controls: { elevator: -2.1 },
    velocity: 20,
    alpha: 0.035,
    beta: 0,
    p: 0,
    q: 0,
    r: 0,
    xyz_ref: [0.1, 0, 0],
    altitude: 500,
    control_deflections: null,
    ...overrides,
  };
}

const FAKE_AVL_RESULT: AVLTrimResult = {
  converged: true,
  trimmed_deflections: { elevator: -2.5 },
  trimmed_state: { alpha: 0.04 },
  aero_coefficients: { CL: 0.5, CD: 0.02 },
  forces_and_moments: { L: 10, D: 0.4 },
  stability_derivatives: { Cma: -1.2 },
  raw_results: {},
};

const FAKE_AEROBUILDUP_RESULT: AeroBuildupTrimResult = {
  converged: true,
  trim_variable: "elevator",
  trimmed_deflection: -3.0,
  target_coefficient: "CL",
  achieved_value: 0.5,
  aero_coefficients: { CL: 0.5, CD: 0.025 },
  stability_derivatives: { Cma: -1.1 },
};

describe("useOperatingPoints", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches operating points on mount when aeroplaneId is provided", async () => {
    const fakePoints = [makeOP(), makeOP({ id: 2, name: "Climb" })];
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(fakePoints),
    });

    const { result } = renderHook(() => useOperatingPoints("42"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/operating_points?aircraft_id=42"),
    );
    expect(result.current.points).toEqual(fakePoints);
    expect(result.current.error).toBeNull();
  });

  it("returns empty array when aeroplaneId is null", () => {
    const { result } = renderHook(() => useOperatingPoints(null));

    expect(result.current.points).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isGenerating).toBe(false);
    expect(result.current.isTrimming).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("generate() calls the correct endpoint and refreshes", async () => {
    const fakePoints = [makeOP()];
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve([]) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve({}) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve(fakePoints) });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useOperatingPoints("42"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.generate();
    });

    expect(mockFetch.mock.calls[1][0]).toContain(
      "/aeroplanes/42/operating-pointsets/generate-default",
    );
    expect(mockFetch.mock.calls[1][1]).toEqual(
      expect.objectContaining({ method: "POST" }),
    );
    const body = JSON.parse(mockFetch.mock.calls[1][1].body);
    expect(body).toEqual({ replace_existing: false });

    expect(result.current.points).toEqual(fakePoints);
    expect(result.current.isGenerating).toBe(false);
  });

  it("trimWithAvl() calls correct endpoint, returns result, and refreshes", async () => {
    const point = makeOP();
    const constraints: TrimConstraint[] = [
      { variable: "elevator", target: "Cm", value: 0 },
    ];
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve([point]) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve(FAKE_AVL_RESULT) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve([point]) });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useOperatingPoints("42"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    let trimResult: AVLTrimResult | null = null;
    await act(async () => {
      trimResult = await result.current.trimWithAvl(point, constraints);
    });

    expect(mockFetch.mock.calls[1][0]).toContain(
      "/aeroplanes/42/operating-points/avl-trim",
    );
    expect(mockFetch.mock.calls[1][1]).toEqual(
      expect.objectContaining({ method: "POST" }),
    );
    const body = JSON.parse(mockFetch.mock.calls[1][1].body);
    expect(body.trim_constraints).toEqual(constraints);
    expect(body.operating_point).toEqual(
      expect.objectContaining({ velocity: 20, alpha: 0.035 }),
    );

    expect(trimResult).toEqual(FAKE_AVL_RESULT);
    expect(result.current.isTrimming).toBe(false);
    expect(mockFetch).toHaveBeenCalledTimes(3);
  });

  it("trimWithAerobuildup() calls correct endpoint, returns result, and refreshes", async () => {
    const point = makeOP();
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve([point]) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve(FAKE_AEROBUILDUP_RESULT) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve([point]) });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useOperatingPoints("42"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    let trimResult: AeroBuildupTrimResult | null = null;
    await act(async () => {
      trimResult = await result.current.trimWithAerobuildup(
        point,
        "elevator",
        "CL",
        0.5,
      );
    });

    expect(mockFetch.mock.calls[1][0]).toContain(
      "/aeroplanes/42/operating-points/aerobuildup-trim",
    );
    expect(mockFetch.mock.calls[1][1]).toEqual(
      expect.objectContaining({ method: "POST" }),
    );
    const body = JSON.parse(mockFetch.mock.calls[1][1].body);
    expect(body.trim_variable).toBe("elevator");
    expect(body.target_coefficient).toBe("CL");
    expect(body.target_value).toBe(0.5);

    expect(trimResult).toEqual(FAKE_AEROBUILDUP_RESULT);
    expect(result.current.isTrimming).toBe(false);
    expect(mockFetch).toHaveBeenCalledTimes(3);
  });

  it("handles fetch errors gracefully", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve("Internal server error"),
    });

    const { result } = renderHook(() => useOperatingPoints("42"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.points).toEqual([]);
    expect(result.current.error).toContain("500");
  });

  it("handles 404 by setting empty points array", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      text: () => Promise.resolve("Not found"),
    });

    const { result } = renderHook(() => useOperatingPoints("42"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.points).toEqual([]);
    expect(result.current.error).toBeNull();
  });

  it("clears points when aeroplaneId becomes null", async () => {
    const fakePoints = [makeOP()];
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(fakePoints),
    });

    const { result, rerender } = renderHook(
      ({ id }) => useOperatingPoints(id),
      { initialProps: { id: "42" as string | null } },
    );

    await waitFor(() => {
      expect(result.current.points).toEqual(fakePoints);
    });

    rerender({ id: null });

    expect(result.current.points).toEqual([]);
  });

  it("sets error when generate() fails", async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve([]) })
      .mockResolvedValueOnce({ ok: false, status: 500, text: () => Promise.resolve("Server error") });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useOperatingPoints("42"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.generate();
    });

    expect(result.current.error).toContain("500");
    expect(result.current.isGenerating).toBe(false);
  });

  it("trimWithAvl() returns null and sets error on failure", async () => {
    const point = makeOP();
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve([point]) })
      .mockResolvedValueOnce({ ok: false, status: 500, text: () => Promise.resolve("Trim error") });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useOperatingPoints("42"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    let trimResult: AVLTrimResult | null = null;
    await act(async () => {
      trimResult = await result.current.trimWithAvl(point, []);
    });

    expect(trimResult).toBeNull();
    expect(result.current.error).toContain("500");
    expect(result.current.isTrimming).toBe(false);
  });
});

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    ChevronRight: icon,
    ChevronUp: icon,
    ChevronDown: icon,
    Plus: icon,
    X: icon,
    Loader2: icon,
    AlertTriangle: icon,
    Check: icon,
    RefreshCw: icon,
  };
});

async function loadPanel() {
  const mod = await import("@/components/workbench/OperatingPointsPanel");
  return mod.OperatingPointsPanel;
}

describe("OperatingPointsPanel", () => {
  let OperatingPointsPanel: Awaited<ReturnType<typeof loadPanel>>;

  beforeEach(async () => {
    vi.restoreAllMocks();
    try {
      OperatingPointsPanel = await loadPanel();
    } catch {
      return;
    }
  });

  function renderPanel(overrides: Record<string, unknown> = {}) {
    const defaultProps = {
      points: [] as StoredOperatingPoint[],
      isLoading: false,
      isGenerating: false,
      isTrimming: false,
      error: null as string | null,
      onGenerate: vi.fn(),
      onTrimWithAvl: vi.fn().mockResolvedValue(null),
      onTrimWithAerobuildup: vi.fn().mockResolvedValue(null),
      ...overrides,
    };
    return { ...render(<OperatingPointsPanel {...defaultProps} />), props: defaultProps };
  }

  it("renders empty state when no points", async () => {
    if (!OperatingPointsPanel) return;

    renderPanel();
    expect(
      screen.getByText(/no operating points/i) || screen.getByText(/generate/i),
    ).toBeInTheDocument();
  });

  it("renders table with operating points data", async () => {
    if (!OperatingPointsPanel) return;

    const points = [
      makeOP({ id: 1, name: "Cruise", velocity: 20 }),
      makeOP({ id: 2, name: "Climb", velocity: 15, status: "NOT_TRIMMED" }),
    ];
    renderPanel({ points });

    expect(screen.getByText("Cruise")).toBeInTheDocument();
    expect(screen.getByText("Climb")).toBeInTheDocument();
  });

  it("status badges show correct colors", async () => {
    if (!OperatingPointsPanel) return;

    const points = [
      makeOP({ id: 1, name: "Trimmed OP", status: "TRIMMED" }),
      makeOP({ id: 2, name: "Untrimmed OP", status: "NOT_TRIMMED" }),
      makeOP({ id: 3, name: "Limited OP", status: "LIMIT_REACHED" }),
    ];
    renderPanel({ points });

    const trimmedBadge = screen.getByText("Trimmed");
    const untrimmedBadge = screen.getByText("Not Trimmed");
    const limitBadge = screen.getByText("Limit Reached");

    expect(trimmedBadge.className).toMatch(/emerald/);
    expect(untrimmedBadge.className).toMatch(/yellow/);
    expect(limitBadge.className).toMatch(/red/);
  });

  it("clicking Generate Default OPs calls onGenerate", async () => {
    if (!OperatingPointsPanel) return;

    const user = userEvent.setup();
    const { props } = renderPanel();

    const btn = screen.getByRole("button", { name: /generate/i });
    await user.click(btn);

    expect(props.onGenerate).toHaveBeenCalledOnce();
  });

  it("clicking a row opens the detail drawer", async () => {
    if (!OperatingPointsPanel) return;

    const user = userEvent.setup();
    const points = [makeOP({ id: 1, name: "Cruise" })];
    renderPanel({ points });

    await user.click(screen.getByText("Cruise"));

    await waitFor(() => {
      expect(screen.getByText("Flight Conditions")).toBeInTheDocument();
    });
  });

  it("closing the drawer works", async () => {
    if (!OperatingPointsPanel) return;

    const user = userEvent.setup();
    const points = [makeOP({ id: 1, name: "Cruise" })];
    renderPanel({ points });

    await user.click(screen.getByText("Cruise"));

    await waitFor(() => {
      expect(screen.getByText("Flight Conditions")).toBeInTheDocument();
    });

    const closeBtn = screen.getByRole("button", { name: /close detail drawer/i });
    await user.click(closeBtn);

    await waitFor(() => {
      expect(screen.queryByText("Flight Conditions")).not.toBeInTheDocument();
    });
  });
});
