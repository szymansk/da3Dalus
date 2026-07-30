/**
 * Unit tests for the useSparPlan hook (gh-1050).
 *
 * Mirrors useSparSizing: manual fetch-based POSTs to
 *   - /aeroplanes/{id}/spar-plan          (run → buildable pieces)
 *   - /aeroplanes/{id}/spar-plan/insert   (insert → dry_run preview / commit)
 * Pins URL + request bodies, data passthrough, dry_run flag, and the
 * loading/error state machine.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import {
  useSparPlan,
  type SparPlanParams,
  type SparPlanResult,
  type SparInsertResult,
} from "@/hooks/useSparPlan";

const FAKE_PLAN: SparPlanResult = {
  front_pieces: [
    {
      role: "front",
      spare_origin: [0, 0, 0],
      spare_vector: [0, 1, 0],
      outer_d: 0.0288,
      inner_d: 0.024,
      wall: 0.0024,
      shape: "tube",
      governing_y: 0,
      x_over_chord: 0.3,
      y_start: 0,
      y_end: 0.75,
      utilisation: 0.5,
      joint_to_next: "telescoping",
      feasible: true,
      infeasibility_reason: null,
    },
  ],
  rear_pieces: [],
  front_joint: "continuous",
  rear_joint: "continuous",
  reinforcement: null,
  feasible: true,
  infeasibility_reason: null,
  front_no_spar_from_y: null,
  rear_no_spar_from_y: null,
};

const FAKE_INSERT: SparInsertResult = {
  dry_run: true,
  committed: false,
  wing_name: "Main Wing",
  planned_spares: [
    {
      segment_index: 0,
      spar_index: 0,
      role: "front",
      spare_support_dimension_width: 0.0288,
      spare_support_dimension_height: 0.0288,
      spare_length: 0.75,
      outer_d: 0.0288,
      inner_d: 0.024,
      spare_origin: [0, 0, 0],
      spare_vector: [0, 1, 0],
      joint_note: "telescoping",
      feasible: true,
    },
  ],
  warnings: [],
  feasible: true,
  infeasibility_reason: null,
  snapshot_id: null,
  planned_segment_lengths: null,
};

const BASE: SparPlanParams = {
  material_id: 7,
  moments: [
    { y_span: 0, bending_moment_Nm: 100 },
    { y_span: 1, bending_moment_Nm: 0 },
  ],
};

function okResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("useSparPlan (gh-1050)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("does not fetch and stays idle when aeroplaneId is null", async () => {
    const fetchSpy = vi.spyOn(global, "fetch");
    const { result } = renderHook(() => useSparPlan(null));
    await act(async () => {
      await result.current.run(BASE);
    });
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(result.current.plan).toBeNull();
    expect(result.current.isRunning).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("POSTs to spar-plan with material_id + moments and passes data through", async () => {
    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(okResponse(FAKE_PLAN));
    const { result } = renderHook(() => useSparPlan("aero-1"));
    await act(async () => {
      await result.current.run(BASE);
    });
    const [url, options] = fetchSpy.mock.calls[0];
    const u = new URL(String(url), "http://x");
    expect(u.pathname).toContain("/aeroplanes/aero-1/spar-plan");
    expect(options).toMatchObject({ method: "POST" });
    const body = JSON.parse(options!.body as string);
    expect(body.material_id).toBe(7);
    expect(body.moments).toHaveLength(2);
    expect(result.current.plan).toEqual(FAKE_PLAN);
    expect(result.current.error).toBeNull();
    expect(result.current.isRunning).toBe(false);
  });

  it("includes optional plan params when set", async () => {
    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(okResponse(FAKE_PLAN));
    const { result } = renderHook(() => useSparPlan("aero-1"));
    await act(async () => {
      await result.current.run({
        ...BASE,
        wing_name: "Main Wing",
        safety_factor_j: 2,
        packing_factor: 0.7,
        sigma_allow_mpa_override: 350,
        n_span: 8,
      });
    });
    const body = JSON.parse(fetchSpy.mock.calls[0][1]!.body as string);
    expect(body.wing_name).toBe("Main Wing");
    expect(body.safety_factor_j).toBe(2);
    expect(body.packing_factor).toBe(0.7);
    expect(body.sigma_allow_mpa_override).toBe(350);
    expect(body.n_span).toBe(8);
  });

  it("surfaces a plan 422 error readably and clears the plan", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ error: { message: "infeasible plan" } }),
        { status: 422, headers: { "Content-Type": "application/json" } },
      ),
    );
    const { result } = renderHook(() => useSparPlan("aero-1"));
    await act(async () => {
      await result.current.run(BASE);
    });
    expect(result.current.error).toContain("Spar plan — invalid request");
    expect(result.current.error).toContain("infeasible plan");
    expect(result.current.plan).toBeNull();
  });

  it("captures a throwing fetch on run as an error string", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new Error("network down"));
    const { result } = renderHook(() => useSparPlan("aero-1"));
    await act(async () => {
      await result.current.run(BASE);
    });
    expect(result.current.error).toBe("network down");
    expect(result.current.plan).toBeNull();
  });

  it("insert sends dry_run=true for a preview and returns the result", async () => {
    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(okResponse(FAKE_INSERT));
    const { result } = renderHook(() => useSparPlan("aero-1"));
    let res: SparInsertResult | null = null;
    await act(async () => {
      res = await result.current.insert(BASE, true);
    });
    const [url, options] = fetchSpy.mock.calls[0];
    const u = new URL(String(url), "http://x");
    expect(u.pathname).toContain("/aeroplanes/aero-1/spar-plan/insert");
    const body = JSON.parse(options!.body as string);
    expect(body.dry_run).toBe(true);
    expect(body.material_id).toBe(7);
    expect(res).toEqual(FAKE_INSERT);
  });

  it("insert sends dry_run=false to commit", async () => {
    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(okResponse({ ...FAKE_INSERT, committed: true, dry_run: false }));
    const { result } = renderHook(() => useSparPlan("aero-1"));
    let res: SparInsertResult | null = null;
    await act(async () => {
      res = await result.current.insert(BASE, false);
    });
    const body = JSON.parse(fetchSpy.mock.calls[0][1]!.body as string);
    expect(body.dry_run).toBe(false);
    expect(res!.committed).toBe(true);
  });

  it("insert rejects (throws) on a non-ok response", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ error: { message: "boom" } }), {
        status: 422,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const { result } = renderHook(() => useSparPlan("aero-1"));
    await expect(result.current.insert(BASE, false)).rejects.toThrow(/boom/);
  });

  it("insert throws when there is no aeroplane", async () => {
    const { result } = renderHook(() => useSparPlan(null));
    await expect(result.current.insert(BASE, true)).rejects.toThrow(
      /No aeroplane/,
    );
  });

  // gh-1080: shape field plumbed through to the request body -----------------

  it("sends shape='rod' in the request body when specified", async () => {
    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(okResponse(FAKE_PLAN));
    const { result } = renderHook(() => useSparPlan("aero-1"));
    await act(async () => {
      await result.current.run({ ...BASE, shape: "rod" });
    });
    const body = JSON.parse(fetchSpy.mock.calls[0][1]!.body as string);
    expect(body.shape).toBe("rod");
  });

  it("omits shape from the request body when not specified (backend defaults to tube)", async () => {
    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(okResponse(FAKE_PLAN));
    const { result } = renderHook(() => useSparPlan("aero-1"));
    await act(async () => {
      await result.current.run(BASE);
    });
    const body = JSON.parse(fetchSpy.mock.calls[0][1]!.body as string);
    expect(body).not.toHaveProperty("shape");
  });

  it("sends shape='tube' when explicitly set", async () => {
    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(okResponse(FAKE_PLAN));
    const { result } = renderHook(() => useSparPlan("aero-1"));
    await act(async () => {
      await result.current.run({ ...BASE, shape: "tube" });
    });
    const body = JSON.parse(fetchSpy.mock.calls[0][1]!.body as string);
    expect(body.shape).toBe("tube");
  });

  // gh-1060: snapshot revert ------------------------------------------------

  it("restoreSnapshot POSTs to /aeroplanes/{snapshot_id}/restore with a name", async () => {
    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(okResponse({ id: 99, name: "revert" }));
    const { result } = renderHook(() => useSparPlan("aero-1"));
    await act(async () => {
      await result.current.restoreSnapshot(55);
    });
    const [url, options] = fetchSpy.mock.calls[0];
    const u = new URL(String(url), "http://x");
    expect(u.pathname).toContain("/aeroplanes/55/restore");
    expect(options).toMatchObject({ method: "POST" });
    const body = JSON.parse(options!.body as string);
    expect(typeof body.name).toBe("string");
    expect(body.name.length).toBeGreaterThan(0);
  });

  it("restoreSnapshot throws readably on a non-ok response", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ error: { message: "not a snapshot" } }), {
        status: 422,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const { result } = renderHook(() => useSparPlan("aero-1"));
    await expect(result.current.restoreSnapshot(55)).rejects.toThrow(
      /not a snapshot/,
    );
  });
});
