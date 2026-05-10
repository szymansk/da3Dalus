import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import {
  useOperatingPoints,
  extractControlSurfaces,
  type StoredOperatingPoint,
  type AVLTrimResult,
  type AeroBuildupTrimResult,
  type TrimConstraint,
  type ControlSurface,
} from "@/hooks/useOperatingPoints";
import type { Wing } from "@/hooks/useWings";

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

    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(calledUrl.toString()).toContain("/operating_points?aircraft_id=42");
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
    expect(body).toEqual({ replace_existing: true });

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

  it("updateDeflections() calls PATCH endpoint and refreshes", async () => {
    const point = makeOP();
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve([point]) })
      .mockResolvedValueOnce({ ok: true, status: 200 })
      .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve([point]) });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useOperatingPoints("42"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.updateDeflections(1, { elevator: -5 });
    });

    expect(mockFetch.mock.calls[1][0]).toContain("/operating_points/1/deflections");
    expect(mockFetch.mock.calls[1][1]).toEqual(
      expect.objectContaining({ method: "PATCH" }),
    );
    const body = JSON.parse(mockFetch.mock.calls[1][1].body);
    expect(body).toEqual({ control_deflections: { elevator: -5 } });
    // Refresh was called (3rd fetch call)
    expect(mockFetch).toHaveBeenCalledTimes(3);
    expect(result.current.error).toBeNull();
  });

  it("updateDeflections() sets error on failure", async () => {
    const point = makeOP();
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve([point]) })
      .mockResolvedValueOnce({ ok: false, status: 400, text: () => Promise.resolve("Bad request") });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useOperatingPoints("42"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.updateDeflections(1, { elevator: -5 });
    });

    expect(result.current.error).toContain("400");
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
    Info: icon,
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
      controlSurfaces: [] as ControlSurface[],
      onUpdateDeflections: vi.fn().mockResolvedValue(undefined),
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

  it("clicking Generate Default OPs calls onGenerate without event args (gh-470)", async () => {
    if (!OperatingPointsPanel) return;

    const user = userEvent.setup();
    const { props } = renderPanel();

    const btn = screen.getByRole("button", { name: /generate/i });
    await user.click(btn);

    expect(props.onGenerate).toHaveBeenCalledOnce();
    expect(props.onGenerate).toHaveBeenCalledWith();
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

  it("displays error message when error prop is set", () => {
    if (!OperatingPointsPanel) return;
    renderPanel({ error: "Something went wrong" });
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("shows loading state", () => {
    if (!OperatingPointsPanel) return;
    renderPanel({ isLoading: true });
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("shows generating state on button", () => {
    if (!OperatingPointsPanel) return;
    renderPanel({ isGenerating: true });
    expect(screen.getByText("Generating...")).toBeInTheDocument();
  });

  it("drawer shows flight condition details", async () => {
    if (!OperatingPointsPanel) return;
    const user = userEvent.setup();
    const points = [makeOP({
      id: 1, name: "Test OP", velocity: 25.0, alpha: 0.05, beta: 0.01,
      altitude: 1000, config: "takeoff", description: "Test description",
    })];
    renderPanel({ points });
    await user.click(screen.getByText("Test OP"));
    await waitFor(() => {
      expect(screen.getByText("Flight Conditions")).toBeInTheDocument();
    });
    expect(screen.getByText("Test description")).toBeInTheDocument();
    expect(screen.getByText("25.00 m/s")).toBeInTheDocument();
    expect(screen.getByText("1000 m")).toBeInTheDocument();
    expect(screen.getAllByText("takeoff").length).toBeGreaterThanOrEqual(2);
  });

  it("drawer shows warnings when present", async () => {
    if (!OperatingPointsPanel) return;
    const user = userEvent.setup();
    const points = [makeOP({
      id: 1, name: "Warned", warnings: ["Stall warning", "Control limit"],
    })];
    renderPanel({ points });
    await user.click(screen.getByText("Warned"));
    await waitFor(() => {
      expect(screen.getByText("Stall warning")).toBeInTheDocument();
    });
    expect(screen.getByText("Control limit")).toBeInTheDocument();
  });

  it("drawer shows controls section when controls exist", async () => {
    if (!OperatingPointsPanel) return;
    const user = userEvent.setup();
    const points = [makeOP({
      id: 1, name: "Trimmed OP", controls: { elevator: -2.1, aileron: 0.5 },
    })];
    renderPanel({ points });
    await user.click(screen.getByText("Trimmed OP"));
    await waitFor(() => {
      expect(screen.getByText("Controls")).toBeInTheDocument();
    });
    expect(screen.getByText("elevator")).toBeInTheDocument();
    expect(screen.getByText("aileron")).toBeInTheDocument();
  });

  it("runs AVL trim and shows result", async () => {
    if (!OperatingPointsPanel) return;
    const user = userEvent.setup();
    const points = [makeOP({ id: 1, name: "TrimMe" })];
    const onTrimWithAvl = vi.fn().mockResolvedValue(FAKE_AVL_RESULT);
    renderPanel({ points, onTrimWithAvl });
    await user.click(screen.getByText("TrimMe"));
    await waitFor(() => {
      expect(screen.getByText("Trim with AVL")).toBeInTheDocument();
    });
    const runBtn = screen.getByRole("button", { name: /run avl trim/i });
    await user.click(runBtn);
    await waitFor(() => {
      expect(onTrimWithAvl).toHaveBeenCalledOnce();
    });
    await waitFor(() => {
      expect(screen.getByText("Converged")).toBeInTheDocument();
    });
  });

  it("runs AeroBuildup trim and shows result", async () => {
    if (!OperatingPointsPanel) return;
    const user = userEvent.setup();
    const points = [makeOP({ id: 1, name: "AbTrim" })];
    const onTrimWithAerobuildup = vi.fn().mockResolvedValue(FAKE_AEROBUILDUP_RESULT);
    renderPanel({ points, onTrimWithAerobuildup });
    await user.click(screen.getByText("AbTrim"));
    await waitFor(() => {
      expect(screen.getByText("Trim with AeroBuildup")).toBeInTheDocument();
    });
    const runBtn = screen.getByRole("button", { name: /run aerobuildup trim/i });
    await user.click(runBtn);
    await waitFor(() => {
      expect(onTrimWithAerobuildup).toHaveBeenCalledOnce();
    });
    await waitFor(() => {
      expect(screen.getByText("Converged")).toBeInTheDocument();
    });
  });

  it("sorts table by clicking column headers", async () => {
    if (!OperatingPointsPanel) return;
    const user = userEvent.setup();
    const points = [
      makeOP({ id: 1, name: "Bravo", velocity: 30 }),
      makeOP({ id: 2, name: "Alpha", velocity: 10 }),
    ];
    renderPanel({ points });
    const rows = screen.getAllByRole("row");
    expect(rows[1]).toHaveTextContent("Alpha");
    expect(rows[2]).toHaveTextContent("Bravo");
    const velocityHeader = screen.getByText("Velocity (m/s)");
    await user.click(velocityHeader);
    const rowsAfter = screen.getAllByRole("row");
    expect(rowsAfter[1]).toHaveTextContent("Alpha");
    await user.click(velocityHeader);
    const rowsDesc = screen.getAllByRole("row");
    expect(rowsDesc[1]).toHaveTextContent("Bravo");
  });

  it("adds and removes AVL trim constraints", async () => {
    if (!OperatingPointsPanel) return;
    const user = userEvent.setup();
    const points = [makeOP({ id: 1, name: "Constrained" })];
    renderPanel({ points });
    await user.click(screen.getByText("Constrained"));
    await waitFor(() => {
      expect(screen.getByText("Trim with AVL")).toBeInTheDocument();
    });
    const addBtn = screen.getByText("+ Constraint");
    await user.click(addBtn);
    const variableInputs = screen.getAllByDisplayValue("elevator");
    expect(variableInputs.length).toBeGreaterThanOrEqual(1);
  });

  it("shows not converged result for failed trim", async () => {
    if (!OperatingPointsPanel) return;
    const user = userEvent.setup();
    const points = [makeOP({ id: 1, name: "FailTrim" })];
    const failedResult = { ...FAKE_AVL_RESULT, converged: false };
    const onTrimWithAvl = vi.fn().mockResolvedValue(failedResult);
    renderPanel({ points, onTrimWithAvl });
    await user.click(screen.getByText("FailTrim"));
    await waitFor(() => {
      expect(screen.getByText("Trim with AVL")).toBeInTheDocument();
    });
    const runBtn = screen.getByRole("button", { name: /run avl trim/i });
    await user.click(runBtn);
    await waitFor(() => {
      expect(screen.getByText("Not Converged")).toBeInTheDocument();
    });
  });

  it("closes drawer with Escape key", async () => {
    if (!OperatingPointsPanel) return;
    const user = userEvent.setup();
    const points = [makeOP({ id: 1, name: "EscTest" })];
    renderPanel({ points });
    await user.click(screen.getByText("EscTest"));
    await waitFor(() => {
      expect(screen.getByText("Flight Conditions")).toBeInTheDocument();
    });
    await user.keyboard("{Escape}");
    await waitFor(() => {
      expect(screen.queryByText("Flight Conditions")).not.toBeInTheDocument();
    });
  });

  it("AVL trim result shows trimmed deflections and aero coefficients", async () => {
    if (!OperatingPointsPanel) return;
    const user = userEvent.setup();
    const points = [makeOP({ id: 1, name: "FullResult" })];
    const onTrimWithAvl = vi.fn().mockResolvedValue(FAKE_AVL_RESULT);
    renderPanel({ points, onTrimWithAvl });
    await user.click(screen.getByText("FullResult"));
    await waitFor(() => {
      expect(screen.getByText("Run AVL Trim")).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /run avl trim/i }));
    await waitFor(() => {
      expect(screen.getByText("Trimmed Deflections")).toBeInTheDocument();
    });
    expect(screen.getByText("Aero Coefficients")).toBeInTheDocument();
    expect(screen.getByText("-2.5000")).toBeInTheDocument();
  });

  it("AeroBuildup trim result shows trim variable and achieved value", async () => {
    if (!OperatingPointsPanel) return;
    const user = userEvent.setup();
    const points = [makeOP({ id: 1, name: "AbFullResult" })];
    const onTrimWithAerobuildup = vi.fn().mockResolvedValue(FAKE_AEROBUILDUP_RESULT);
    renderPanel({ points, onTrimWithAerobuildup });
    await user.click(screen.getByText("AbFullResult"));
    await waitFor(() => {
      expect(screen.getByText("Trim with AeroBuildup")).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /run aerobuildup trim/i }));
    await waitFor(() => {
      expect(screen.getByText("-3.0000")).toBeInTheDocument();
    });
    expect(screen.getAllByText("0.500000").length).toBeGreaterThanOrEqual(1);
  });

  it("displays status badge in drawer", async () => {
    if (!OperatingPointsPanel) return;
    const user = userEvent.setup();
    const points = [makeOP({ id: 1, name: "BadgeTest", status: "LIMIT_REACHED" })];
    renderPanel({ points });
    await user.click(screen.getByText("BadgeTest"));
    await waitFor(() => {
      expect(screen.getAllByText("Status").length).toBeGreaterThanOrEqual(2);
    });
    const badges = screen.getAllByText("Limit Reached");
    expect(badges.length).toBeGreaterThanOrEqual(2);
  });

  it("trim buttons disabled when isTrimming is true", async () => {
    if (!OperatingPointsPanel) return;
    const user = userEvent.setup();
    const points = [makeOP({ id: 1, name: "DisabledTest" })];
    renderPanel({ points, isTrimming: true });
    await user.click(screen.getByText("DisabledTest"));
    await waitFor(() => {
      const trimmingButtons = screen.getAllByText("Trimming...");
      expect(trimmingButtons.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("modifies AVL constraint values via inputs", async () => {
    if (!OperatingPointsPanel) return;
    const user = userEvent.setup();
    const points = [makeOP({ id: 1, name: "InputTest" })];
    renderPanel({ points });
    await user.click(screen.getByText("InputTest"));
    await waitFor(() => {
      expect(screen.getByText("Trim with AVL")).toBeInTheDocument();
    });
    const variableInputs = screen.getAllByDisplayValue("elevator");
    const avlInput = variableInputs[0];
    await user.clear(avlInput);
    await user.type(avlInput, "aileron");
    expect(avlInput).toHaveValue("aileron");
  });

  it("modifies AeroBuildup trim form inputs", async () => {
    if (!OperatingPointsPanel) return;
    const user = userEvent.setup();
    const points = [makeOP({ id: 1, name: "AbInputTest" })];
    renderPanel({ points });
    await user.click(screen.getByText("AbInputTest"));
    await waitFor(() => {
      expect(screen.getByText("Trim with AeroBuildup")).toBeInTheDocument();
    });
    const elevatorInputs = screen.getAllByDisplayValue("elevator");
    expect(elevatorInputs.length).toBeGreaterThanOrEqual(2);
    const coeffInput = screen.getByDisplayValue("CL");
    expect(coeffInput).toBeInTheDocument();
  });

  it("removes an AVL constraint", async () => {
    if (!OperatingPointsPanel) return;
    const user = userEvent.setup();
    const points = [makeOP({ id: 1, name: "RemoveTest" })];
    renderPanel({ points });
    await user.click(screen.getByText("RemoveTest"));
    await waitFor(() => {
      expect(screen.getByText("Trim with AVL")).toBeInTheDocument();
    });
    await user.click(screen.getByText("+ Constraint"));
    const valueInputsBefore = screen.getAllByDisplayValue("0");
    const removeButtons = screen.getAllByRole("button").filter(
      (b) => b.querySelector("[size]") && b.closest(".flex.items-end"),
    );
    if (removeButtons.length > 0) {
      await user.click(removeButtons[removeButtons.length - 1]);
    }
    const valueInputsAfter = screen.getAllByDisplayValue("0");
    expect(valueInputsAfter.length).toBeLessThanOrEqual(valueInputsBefore.length);
  });

  it("sorts by different columns: config and status", async () => {
    if (!OperatingPointsPanel) return;
    const user = userEvent.setup();
    const points = [
      makeOP({ id: 1, name: "Point1", config: "landing", status: "TRIMMED", beta: 0.05 }),
      makeOP({ id: 2, name: "Point2", config: "clean", status: "NOT_TRIMMED", beta: 0.01 }),
    ];
    renderPanel({ points });
    await user.click(screen.getByText("Config"));
    const rows = screen.getAllByRole("row");
    expect(rows[1]).toHaveTextContent("Point2");
    await user.click(screen.getByText("Beta (deg)"));
    const rowsBeta = screen.getAllByRole("row");
    expect(rowsBeta[1]).toHaveTextContent("Point2");
  });

  it("drawer shows Control Deflections section when control surfaces exist", async () => {
    if (!OperatingPointsPanel) return;
    const user = userEvent.setup();
    const points = [makeOP({ id: 1, name: "DeflTest" })];
    const controlSurfaces: ControlSurface[] = [
      { name: "elevator", deflection_deg: 0 },
      { name: "aileron", deflection_deg: 5 },
    ];
    renderPanel({ points, controlSurfaces });
    await user.click(screen.getByText("DeflTest"));
    await waitFor(() => {
      expect(screen.getByText("Control Deflections")).toBeInTheDocument();
    });
    expect(screen.getByLabelText("elevator deflection")).toBeInTheDocument();
    expect(screen.getByLabelText("aileron deflection")).toBeInTheDocument();
  });

  it("shows 'No control surfaces found' when empty", async () => {
    if (!OperatingPointsPanel) return;
    const user = userEvent.setup();
    const points = [makeOP({ id: 1, name: "EmptyCS" })];
    renderPanel({ points, controlSurfaces: [] });
    await user.click(screen.getByText("EmptyCS"));
    await waitFor(() => {
      expect(screen.getByText("Control Deflections")).toBeInTheDocument();
    });
    expect(screen.getByText("No control surfaces found")).toBeInTheDocument();
  });

  it("shows override values when control_deflections is set", async () => {
    if (!OperatingPointsPanel) return;
    const user = userEvent.setup();
    const points = [
      makeOP({
        id: 1,
        name: "OverrideTest",
        control_deflections: { elevator: -3.5 },
      }),
    ];
    const controlSurfaces: ControlSurface[] = [
      { name: "elevator", deflection_deg: 0 },
    ];
    renderPanel({ points, controlSurfaces });
    await user.click(screen.getByText("OverrideTest"));
    await waitFor(() => {
      expect(screen.getByText("Control Deflections")).toBeInTheDocument();
    });
    const input = screen.getByLabelText("elevator deflection");
    expect(input).toHaveValue(-3.5);
  });

  it("Save Deflections button calls onUpdateDeflections", async () => {
    if (!OperatingPointsPanel) return;
    const user = userEvent.setup();
    const points = [makeOP({ id: 1, name: "SaveTest" })];
    const controlSurfaces: ControlSurface[] = [
      { name: "elevator", deflection_deg: 0 },
    ];
    const onUpdateDeflections = vi.fn().mockResolvedValue(undefined);
    renderPanel({ points, controlSurfaces, onUpdateDeflections });
    await user.click(screen.getByText("SaveTest"));
    await waitFor(() => {
      expect(screen.getByText("Control Deflections")).toBeInTheDocument();
    });
    const saveBtn = screen.getByRole("button", { name: /save deflections/i });
    await user.click(saveBtn);
    expect(onUpdateDeflections).toHaveBeenCalledWith(1, { elevator: 0 });
  });
});

describe("extractControlSurfaces", () => {
  it("extracts control surfaces from wing trailing edge devices", () => {
    const wings: Wing[] = [
      {
        name: "main_wing",
        symmetric: true,
        x_secs: [
          {
            xyz_le: [0, 0, 0],
            chord: 1.0,
            twist: 0,
            airfoil: "NACA2412",
            trailing_edge_device: { name: "elevator", deflection_deg: -2 },
          },
          {
            xyz_le: [0, 1, 0],
            chord: 0.8,
            twist: 0,
            airfoil: "NACA2412",
            trailing_edge_device: null,
          },
        ],
      },
    ];
    const result = extractControlSurfaces(wings);
    expect(result).toEqual([{ name: "elevator", deflection_deg: -2 }]);
  });

  it("deduplicates by name, keeping first occurrence", () => {
    const wings: Wing[] = [
      {
        name: "main_wing",
        symmetric: true,
        x_secs: [
          {
            xyz_le: [0, 0, 0],
            chord: 1.0,
            twist: 0,
            airfoil: "NACA2412",
            trailing_edge_device: { name: "aileron", deflection_deg: 5 },
          },
          {
            xyz_le: [0, 1, 0],
            chord: 0.8,
            twist: 0,
            airfoil: "NACA2412",
            trailing_edge_device: { name: "aileron", deflection_deg: 10 },
          },
        ],
      },
    ];
    const result = extractControlSurfaces(wings);
    expect(result).toEqual([{ name: "aileron", deflection_deg: 5 }]);
  });

  it("returns empty array for wings without TEDs", () => {
    const wings: Wing[] = [
      {
        name: "main_wing",
        symmetric: true,
        x_secs: [
          {
            xyz_le: [0, 0, 0],
            chord: 1.0,
            twist: 0,
            airfoil: "NACA2412",
          },
        ],
      },
    ];
    const result = extractControlSurfaces(wings);
    expect(result).toEqual([]);
  });

  it("handles null/undefined trailing_edge_device", () => {
    const wings: Wing[] = [
      {
        name: "main_wing",
        symmetric: true,
        x_secs: [
          {
            xyz_le: [0, 0, 0],
            chord: 1.0,
            twist: 0,
            airfoil: "NACA2412",
            trailing_edge_device: null,
            control_surface: null,
          },
          {
            xyz_le: [0, 1, 0],
            chord: 0.8,
            twist: 0,
            airfoil: "NACA2412",
            trailing_edge_device: undefined,
            control_surface: undefined,
          },
        ],
      },
    ];
    const result = extractControlSurfaces(wings);
    expect(result).toEqual([]);
  });
});
