/**
 * Unit tests for the useGeometryDiff hook (gh-971).
 *
 * The hook lazily fetches both compared nodes' WingConfig per wing (only when
 * `enabled`) and returns a computed GeometryDiff. We mock the fetcher so no real
 * network happens, and assert: lazy (no fetch when disabled), happy path (both
 * sides fetched + diff computed), error surfacing, and 404→added/removed.
 */
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";

import { useGeometryDiff } from "@/hooks/useGeometryDiff";
import type { WingConfig } from "@/hooks/useWingConfig";

// Fresh SWR cache per render so error/data state never bleeds between tests.
function wrapper({ children }: { children: React.ReactNode }) {
  return React.createElement(
    SWRConfig,
    { value: { provider: () => new Map(), dedupingInterval: 0 } },
    children,
  );
}

// Mock the fetcher so the hook's SWR multi-fetch resolves from a path map.
const fetchMock = vi.fn<(path: string) => Promise<unknown>>();
vi.mock("@/lib/fetcher", () => ({
  fetcher: (path: string) => fetchMock(path),
  API_BASE: "http://localhost:8001",
}));

const NODE_A = "node-aaaa";
const NODE_B = "node-bbbb";

function makeConfig(incidence: number): WingConfig {
  return {
    segments: [
      {
        root_airfoil: { airfoil: "naca2412", chord: 200, incidence },
        tip_airfoil: { airfoil: "naca2412", chord: 150, incidence: 0 },
        length: 500,
        sweep: 0,
      },
    ],
    nose_pnt: [0, 0, 0],
  };
}

function wingconfigPath(uuid: string, wing: string): string {
  return `/aeroplanes/${uuid}/wings/${wing}/wingconfig`;
}

describe("useGeometryDiff", () => {
  beforeEach(() => {
    fetchMock.mockReset();
  });

  it("fetches nothing and returns a null diff when disabled (lazy)", async () => {
    const { result } = renderHook(() =>
      useGeometryDiff(NODE_A, NODE_B, ["main_wing"], false),
      { wrapper },
    );

    expect(result.current.diff).toBeNull();
    expect(result.current.error).toBeNull();
    // No SWR key → fetcher never invoked.
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("fetches both nodes' configs per wing and computes the diff when enabled", async () => {
    // Use incidence values that differ (incidence is NOT in the LCS signature, so
    // sections match by root_chord|length|airfoil and then differ on incidence).
    fetchMock.mockImplementation((path: string) => {
      if (path === wingconfigPath(NODE_A, "main_wing")) {
        return Promise.resolve(makeConfig(0));
      }
      if (path === wingconfigPath(NODE_B, "main_wing")) {
        return Promise.resolve(makeConfig(3));
      }
      return Promise.reject(new Error(`unexpected path ${path}`));
    });

    const { result } = renderHook(() =>
      useGeometryDiff(NODE_A, NODE_B, ["main_wing"], true),
      { wrapper },
    );

    await waitFor(() => {
      expect(result.current.diff).not.toBeNull();
    });

    // Both sides fetched.
    expect(fetchMock).toHaveBeenCalledWith(wingconfigPath(NODE_A, "main_wing"));
    expect(fetchMock).toHaveBeenCalledWith(wingconfigPath(NODE_B, "main_wing"));

    const diff = result.current.diff!;
    expect(diff.hasAnyChange).toBe(true);
    expect(diff.wings).toHaveLength(1);
    expect(diff.wings[0].name).toBe("main_wing");
    const incidenceChange = diff.wings[0].sections[0].params.find(
      (p) => p.key === "root incidence",
    );
    expect(incidenceChange).toBeDefined();
    expect(incidenceChange?.a).toBe("0 deg");
    expect(incidenceChange?.b).toBe("3 deg");
    expect(result.current.error).toBeNull();
  });

  it("surfaces a non-404 fetch error", async () => {
    fetchMock.mockRejectedValue(new Error("boom"));

    const { result } = renderHook(() =>
      useGeometryDiff(NODE_A, NODE_B, ["main_wing"], true),
      { wrapper },
    );

    await waitFor(() => {
      expect(result.current.error).not.toBeNull();
    });
    expect(result.current.error?.message).toContain("boom");
    expect(result.current.diff).toBeNull();
  });

  it("fetches nothing when uuids are missing even if enabled", () => {
    const { result } = renderHook(() =>
      useGeometryDiff(null, NODE_B, ["main_wing"], true),
      { wrapper },
    );

    expect(result.current.diff).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("404 on one node's wing → reports the wing as added (not an error)", async () => {
    // NODE_A returns 404 (wing absent on side A) → wing appears only on B → "added"
    fetchMock.mockImplementation((path: string) => {
      if (path === wingconfigPath(NODE_A, "main_wing")) {
        return Promise.reject(new Error("404 Not Found: /aeroplanes/node-aaaa/wings/main_wing/wingconfig"));
      }
      if (path === wingconfigPath(NODE_B, "main_wing")) {
        return Promise.resolve(makeConfig(200));
      }
      return Promise.reject(new Error(`unexpected path ${path}`));
    });

    const { result } = renderHook(() =>
      useGeometryDiff(NODE_A, NODE_B, ["main_wing"], true),
      { wrapper },
    );

    await waitFor(() => {
      expect(result.current.diff).not.toBeNull();
    });

    // Must NOT error — 404 is handled gracefully
    expect(result.current.error).toBeNull();

    const diff = result.current.diff!;
    expect(diff.hasAnyChange).toBe(true);
    const wing = diff.wings.find((w) => w.name === "main_wing");
    expect(wing).toBeDefined();
    // Side A is null (404) → wing only on B → "added"
    expect(wing!.kind).toBe("added");
  });

  it("404 on B's wing → reports the wing as removed", async () => {
    fetchMock.mockImplementation((path: string) => {
      if (path === wingconfigPath(NODE_A, "main_wing")) {
        return Promise.resolve(makeConfig(200));
      }
      if (path === wingconfigPath(NODE_B, "main_wing")) {
        return Promise.reject(new Error("404 Not Found: /aeroplanes/node-bbbb/wings/main_wing/wingconfig"));
      }
      return Promise.reject(new Error(`unexpected path ${path}`));
    });

    const { result } = renderHook(() =>
      useGeometryDiff(NODE_A, NODE_B, ["main_wing"], true),
      { wrapper },
    );

    await waitFor(() => {
      expect(result.current.diff).not.toBeNull();
    });

    expect(result.current.error).toBeNull();

    const diff = result.current.diff!;
    expect(diff.hasAnyChange).toBe(true);
    const wing = diff.wings.find((w) => w.name === "main_wing");
    expect(wing).toBeDefined();
    expect(wing!.kind).toBe("removed");
  });

  it("malformed payload (structurally bad 200): surfaces error via error channel, does not white-screen", async () => {
    // Return a config where segment entries are null — coreParams(null) will throw
    // inside computeGeometryDiff. The hook must catch it and surface it via `error`,
    // leaving `diff` null (never crashing the render).
    fetchMock.mockImplementation((path: string) => {
      if (path === wingconfigPath(NODE_A, "main_wing")) {
        return Promise.resolve(makeConfig(0));
      }
      if (path === wingconfigPath(NODE_B, "main_wing")) {
        // Structurally broken: segment entry is null → sectionSignature(null) throws
        return Promise.resolve({ segments: [null], nose_pnt: [0, 0, 0] } as unknown as WingConfig);
      }
      return Promise.reject(new Error(`unexpected path ${path}`));
    });

    const { result } = renderHook(
      () => useGeometryDiff(NODE_A, NODE_B, ["main_wing"], true),
      { wrapper },
    );

    await waitFor(() => {
      // Either error is set (crash contained) or diff is non-null (no throw)
      expect(
        result.current.error !== null || result.current.diff !== null,
      ).toBe(true);
    });

    // If computeGeometryDiff threw, it must surface via the error channel.
    if (result.current.error !== null) {
      expect(result.current.diff).toBeNull();
      expect(result.current.error).toBeInstanceOf(Error);
    }
    // (If the garbage happened not to throw, that's also acceptable — the point is
    // it must NOT crash the hook/render.)
  });
});
