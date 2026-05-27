/**
 * gh-751: deleteAeroplane must remove the row from the SWR cache
 * synchronously (optimistic update), then run the backend DELETE in
 * the background, and roll back on error.
 *
 * Pre-fix flow: DELETE → await → mutate() refetch → wait → UI updates.
 * Users perceived a noticeable lag between click and the row
 * disappearing.
 */

import { act, renderHook, waitFor } from "@testing-library/react";
import React from "react";
import { SWRConfig } from "swr";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useAeroplanes, type Aeroplane } from "@/hooks/useAeroplanes";

const INITIAL: Aeroplane[] = [
  { id: "a1", name: "First", total_mass_kg: null, created_at: "", updated_at: "" },
  { id: "a2", name: "Second", total_mass_kg: null, created_at: "", updated_at: "" },
  { id: "a3", name: "Third", total_mass_kg: null, created_at: "", updated_at: "" },
];

let mockFetch: ReturnType<typeof vi.fn>;

beforeEach(() => {
  mockFetch = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
    if (init?.method === "DELETE") {
      // Deferred resolution — tests control when the DELETE settles.
      return new Promise((resolve) => {
        resolveDelete = () => resolve(new Response(null, { status: 204 }));
        rejectDelete = () =>
          resolve(new Response(null, { status: 500, statusText: "Internal" }));
      });
    }
    // Initial GET /aeroplanes — list with 3 entries.
    return Promise.resolve(
      new Response(JSON.stringify({ aeroplanes: INITIAL }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
  });
  vi.stubGlobal("fetch", mockFetch);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
  resolveDelete = null;
  rejectDelete = null;
});

let resolveDelete: (() => void) | null = null;
let rejectDelete: (() => void) | null = null;

function wrapper({ children }: { children: React.ReactNode }) {
  // Fresh SWR cache per test — avoid cross-test leakage.
  return (
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      {children}
    </SWRConfig>
  );
}

describe("useAeroplanes.deleteAeroplane — gh-751 optimistic update", () => {
  it("removes the row from the cache before the DELETE settles", async () => {
    const { result } = renderHook(() => useAeroplanes(), { wrapper });

    // Wait for the initial GET /aeroplanes to populate the cache.
    await waitFor(() =>
      expect(result.current.aeroplanes.map((a) => a.id)).toEqual(["a1", "a2", "a3"]),
    );

    // Trigger the delete but DO NOT resolve the underlying DELETE yet.
    let deletePromise: Promise<void>;
    act(() => {
      deletePromise = result.current.deleteAeroplane("a2");
    });

    // The cache must update immediately — before the DELETE settles.
    // This is the gh-751 fix: optimisticData runs in the same tick as
    // the call site, so the UI sees the row disappear within one
    // render frame.
    await waitFor(() =>
      expect(result.current.aeroplanes.map((a) => a.id)).toEqual(["a1", "a3"]),
    );

    // Now let the DELETE complete and confirm the cache stays consistent.
    resolveDelete?.();
    await act(async () => {
      await deletePromise;
    });
    expect(result.current.aeroplanes.map((a) => a.id)).toEqual(["a1", "a3"]);
  });

  it("rolls back the row on backend failure", async () => {
    const { result } = renderHook(() => useAeroplanes(), { wrapper });
    await waitFor(() => expect(result.current.aeroplanes).toHaveLength(3));

    // Trigger the delete with a backend that will fail.
    let deletePromise: Promise<void>;
    act(() => {
      deletePromise = result.current.deleteAeroplane("a2");
    });

    // Optimistic removal first.
    await waitFor(() =>
      expect(result.current.aeroplanes.map((a) => a.id)).toEqual(["a1", "a3"]),
    );

    // Backend returns 500 → SWR's rollbackOnError must restore "a2".
    rejectDelete?.();
    await act(async () => {
      await deletePromise.catch(() => {
        /* expected — caller's error path */
      });
    });
    await waitFor(() =>
      expect(result.current.aeroplanes.map((a) => a.id)).toEqual([
        "a1",
        "a2",
        "a3",
      ]),
    );
  });

  it("does not refetch after a successful DELETE (revalidate: false)", async () => {
    const { result } = renderHook(() => useAeroplanes(), { wrapper });
    await waitFor(() => expect(result.current.aeroplanes).toHaveLength(3));

    // The initial GET should have been called once.
    const getCallsBefore = mockFetch.mock.calls.filter(
      (c) => !c[1]?.method || c[1].method === "GET",
    ).length;

    let p: Promise<void>;
    act(() => {
      p = result.current.deleteAeroplane("a2");
    });
    resolveDelete?.();
    await act(async () => {
      await p;
    });
    await waitFor(() => expect(result.current.aeroplanes).toHaveLength(2));

    // No additional GET should have been issued — the optimistic
    // update + the function's own return value populate the cache,
    // so a backend refetch is wasted work. Saves one round trip per
    // delete on every page that renders the list.
    const getCallsAfter = mockFetch.mock.calls.filter(
      (c) => !c[1]?.method || c[1].method === "GET",
    ).length;
    expect(getCallsAfter).toBe(getCallsBefore);
  });
});
