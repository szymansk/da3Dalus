/**
 * Picker heads-only behaviour (gh-907).
 *
 * The backend's GET /aeroplanes defaults to heads_only=true, which means
 * immutable snapshot nodes are excluded from the response.  The frontend
 * does NOT need to append ?heads_only=true — the default is correct.
 *
 * Tests:
 * 1. useAeroplanes sends the request to /aeroplanes WITHOUT a heads_only=false
 *    override (the correct default is preserved).
 * 2. When the mock API response contains only head nodes (is_main_branch: true),
 *    useAeroplanes exposes exactly those nodes — no filtering logic needed on the
 *    frontend side because the backend already does it.
 * 3. No extra ?heads_only param is appended by the hook (which would be
 *    redundant but would also be fine — we just verify the current contract).
 */

import { renderHook, waitFor } from "@testing-library/react";
import React from "react";
import { SWRConfig } from "swr";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import { useAeroplanes, type Aeroplane } from "@/hooks/useAeroplanes";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

/** Only head nodes — what the backend returns by default (heads_only=true). */
const HEADS_ONLY: Aeroplane[] = [
  {
    id: "uuid-main",
    name: "My Plane (main)",
    total_mass_kg: null,
    created_at: "2026-06-07T10:00:00Z",
    updated_at: "2026-06-07T10:00:00Z",
    int_id: 10,
    root_id: 10,
    branch_name: "main",
    is_main_branch: true,
  },
  {
    id: "uuid-ai-branch",
    name: "My Plane (ai/winglet)",
    total_mass_kg: null,
    created_at: "2026-06-08T09:00:00Z",
    updated_at: "2026-06-08T09:00:00Z",
    int_id: 20,
    root_id: 10,
    branch_name: "ai/winglet",
    is_main_branch: false,
  },
];

let mockFetch: ReturnType<typeof vi.fn>;

beforeEach(() => {
  mockFetch = vi.fn().mockImplementation((url: string) => {
    // Return only heads — as the backend does by default.
    if ((url as string).includes("/aeroplanes")) {
      return Promise.resolve(
        new Response(JSON.stringify({ aeroplanes: HEADS_ONLY }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      );
    }
    return Promise.resolve(new Response("not found", { status: 404 }));
  });
  vi.stubGlobal("fetch", mockFetch);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      {children}
    </SWRConfig>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useAeroplanes — heads-only picker (gh-907)", () => {
  // -------------------------------------------------------------------------
  // 1. Correct API path — no heads_only=false override
  // -------------------------------------------------------------------------
  it("fetches /aeroplanes without overriding heads_only=false", async () => {
    const { result } = renderHook(() => useAeroplanes(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    const calls = mockFetch.mock.calls as [string, unknown][];
    const aeroplanesCall = calls.find(([url]) => url.includes("/aeroplanes"));
    expect(aeroplanesCall).toBeDefined();

    const [url] = aeroplanesCall!;
    // The URL must NOT carry heads_only=false — that would break the default.
    expect(url).not.toContain("heads_only=false");
  });

  // -------------------------------------------------------------------------
  // 2. Hook exposes exactly the head nodes returned by the API
  // -------------------------------------------------------------------------
  it("exposes exactly the aeroplane list returned by the API (heads only)", async () => {
    const { result } = renderHook(() => useAeroplanes(), { wrapper });

    await waitFor(() =>
      expect(result.current.aeroplanes).toHaveLength(2),
    );

    // Both nodes are heads of their respective branches
    const ids = result.current.aeroplanes.map((a) => a.id);
    expect(ids).toContain("uuid-main");
    expect(ids).toContain("uuid-ai-branch");
  });

  // -------------------------------------------------------------------------
  // 3. Versioning metadata fields are preserved
  // -------------------------------------------------------------------------
  it("preserves versioning metadata (int_id, root_id, branch_name, is_main_branch)", async () => {
    const { result } = renderHook(() => useAeroplanes(), { wrapper });

    await waitFor(() =>
      expect(result.current.aeroplanes).toHaveLength(2),
    );

    const main = result.current.aeroplanes.find((a) => a.id === "uuid-main");
    expect(main?.int_id).toBe(10);
    expect(main?.root_id).toBe(10);
    expect(main?.branch_name).toBe("main");
    expect(main?.is_main_branch).toBe(true);

    const ai = result.current.aeroplanes.find((a) => a.id === "uuid-ai-branch");
    expect(ai?.int_id).toBe(20);
    expect(ai?.branch_name).toBe("ai/winglet");
    expect(ai?.is_main_branch).toBe(false);
  });

  // -------------------------------------------------------------------------
  // 4. Snapshot nodes (non-heads) are NOT in the picker when API excludes them
  // -------------------------------------------------------------------------
  it("does not include snapshot (non-head) nodes when the API omits them", async () => {
    // This confirms the picker relies on the backend filtering — there is no
    // client-side filter that needs testing.  If the API returns 2 heads,
    // the hook exposes 2 aeroplanes.  The test documents the contract.
    const { result } = renderHook(() => useAeroplanes(), { wrapper });

    await waitFor(() =>
      expect(result.current.aeroplanes).toHaveLength(HEADS_ONLY.length),
    );

    // None of the returned aeroplanes should look like an immutable snapshot
    // (they have branch metadata present → they are branch heads).
    for (const a of result.current.aeroplanes) {
      // Each aeroplane must have a branch_name (branch heads always do).
      expect(a.branch_name).not.toBeNull();
    }
  });
});
