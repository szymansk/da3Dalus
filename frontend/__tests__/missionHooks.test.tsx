/**
 * Coverage tests for Mission Tab data layer (gh-550):
 * - frontend/lib/fetcher.ts (fetcher + putJson)
 * - frontend/hooks/useMissionKpis.ts
 * - frontend/hooks/useMissionObjectives.ts
 * - frontend/hooks/useMissionPresets.ts
 *
 * These pin the URL contracts and exercise the success/error branches so
 * future refactors don't silently break the Mission Tab API surface.
 */
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import { fetcher, putJson } from "@/lib/fetcher";
import { useMissionKpis } from "@/hooks/useMissionKpis";
import { useMissionObjectives } from "@/hooks/useMissionObjectives";
import { useMissionPresets } from "@/hooks/useMissionPresets";

// Fresh SWR cache per renderHook so tests don't share state.
const wrapper = ({ children }: { readonly children: React.ReactNode }) => (
  <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
    {children}
  </SWRConfig>
);

describe("fetcher", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns parsed JSON on 2xx", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ hello: "world" }), { status: 200 }),
    );

    const data = await fetcher<{ hello: string }>("/anything");

    expect(data).toEqual({ hello: "world" });
  });

  it("throws an Error with status and body on non-2xx", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response("boom", { status: 500, statusText: "Internal Server Error" }),
    );

    await expect(fetcher("/anything")).rejects.toThrow(/500.*boom/);
  });
});

describe("putJson", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("PUTs JSON body and returns parsed response", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );

    const out = await putJson<{ ok: boolean }>("/x", { a: 1 });

    expect(out).toEqual({ ok: true });
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/x");
    expect(init).toMatchObject({
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ a: 1 }),
    });
  });

  it("throws on non-2xx with status and message", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response("nope", { status: 422, statusText: "Unprocessable" }),
    );

    await expect(putJson("/x", {})).rejects.toThrow(/PUT \/x failed.*422.*nope/);
  });
});

describe("useMissionKpis", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("does not fetch when aeroplaneId is null", async () => {
    const fetchMock = vi.spyOn(global, "fetch");

    const { result } = renderHook(
      () => useMissionKpis(null, ["trainer"]),
      { wrapper },
    );

    expect(result.current.data).toBeUndefined();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("fetches mission KPIs with missions query string", async () => {
    const fake = {
      aeroplane_uuid: "uuid-1",
      ist_polygon: {},
      target_polygons: [],
      active_mission_id: "trainer",
      computed_at: "now",
      context_hash: "x",
    };
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify(fake), { status: 200 }),
    );

    const { result } = renderHook(
      () => useMissionKpis("uuid-1", ["trainer", "sport"]),
      { wrapper },
    );

    await waitFor(() => expect(result.current.data).toBeTruthy());

    const url = String(fetchMock.mock.calls[0][0]);
    expect(url).toContain("/aeroplanes/uuid-1/mission-kpis");
    expect(url).toContain("missions=trainer");
    expect(url).toContain("missions=sport");
  });
});

describe("useMissionObjectives", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("does not fetch when aeroplaneId is null and update is a no-op", async () => {
    const fetchMock = vi.spyOn(global, "fetch");

    const { result } = renderHook(() => useMissionObjectives(null), { wrapper });

    expect(fetchMock).not.toHaveBeenCalled();

    let updated: unknown = "sentinel";
    await act(async () => {
      updated = await result.current.update({
        mission_type: "trainer",
        target_cruise_mps: 0,
        target_stall_safety: 1.3,
        target_maneuver_n: 4,
        target_glide_ld: 10,
        target_climb_energy: 0,
        target_wing_loading_n_m2: 0,
        target_field_length_m: 0,
        available_runway_m: 0,
        runway_type: "grass",
        t_static_N: 0,
        takeoff_mode: "runway",
      });
    });

    expect(updated).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("fetches the GET endpoint and PUTs on update()", async () => {
    const initial = {
      mission_type: "trainer",
      target_cruise_mps: 20,
      target_stall_safety: 1.3,
      target_maneuver_n: 4,
      target_glide_ld: 10,
      target_climb_energy: 5,
      target_wing_loading_n_m2: 200,
      target_field_length_m: 50,
      available_runway_m: 100,
      runway_type: "grass" as const,
      t_static_N: 30,
      takeoff_mode: "runway" as const,
    };
    const updated = { ...initial, target_cruise_mps: 25 };

    const fetchMock = vi
      .spyOn(global, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify(initial), { status: 200 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(updated), { status: 200 }),
      );

    const { result } = renderHook(() => useMissionObjectives("aero-2"), {
      wrapper,
    });

    await waitFor(() => expect(result.current.data).toEqual(initial));

    let returned: unknown;
    await act(async () => {
      returned = await result.current.update(updated);
    });

    expect(returned).toEqual(updated);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    const [putUrl, putInit] = fetchMock.mock.calls[1];
    expect(String(putUrl)).toContain("/aeroplanes/aero-2/mission-objectives");
    expect(putInit).toMatchObject({ method: "PUT" });
  });
});

describe("useMissionPresets", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches the /mission-presets endpoint", async () => {
    const presets = [
      {
        id: "trainer",
        label: "Trainer",
        description: "",
        target_polygon: {},
        axis_ranges: {},
        suggested_estimates: {
          g_limit: 4,
          target_static_margin: 0.12,
          cl_max: 1.4,
          power_to_weight: 0.4,
          prop_efficiency: 0.6,
        },
      },
    ];
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify(presets), { status: 200 }),
    );

    const { result } = renderHook(() => useMissionPresets(), { wrapper });

    await waitFor(() => expect(result.current.data).toEqual(presets));
    expect(String(fetchMock.mock.calls[0][0])).toContain("/mission-presets");
  });
});
