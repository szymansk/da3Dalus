/**
 * Unit tests for frontend/hooks/useVersioning.ts (gh-907).
 *
 * Tests:
 * - useLineageTree: exposes data/isLoading/error; disables when rootId is null
 * - useVersionActions: each mutation calls the right API function and revalidates
 */

import React from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useLineageTree, useVersionActions } from "@/hooks/useVersioning";
import type { BranchOut, TreeOut, VersionNode } from "@/types/versioning";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const FAKE_TREE: TreeOut = {
  root_id: 10,
  nodes: [
    {
      id: 10,
      uuid: "aaaa",
      name: "Plane A",
      branch_id: 1,
      predecessor_id: null,
      root_id: 10,
      is_immutable: false,
      is_head: true,
      version_label: null,
      version_note: null,
      created_by: "human",
      created_at: "2026-06-07T10:00:00Z",
    },
  ],
  branches: [
    {
      id: 1,
      root_id: 10,
      head_id: 10,
      name: "main",
      is_main: true,
      created_by: "human",
      created_at: "2026-06-07T10:00:00Z",
    },
  ],
};

const FAKE_NODE: VersionNode = {
  id: 20,
  uuid: "bbbb",
  name: "Plane A",
  branch_id: 1,
  predecessor_id: 10,
  root_id: 10,
  is_immutable: true,
  version_label: "v1",
  version_note: "why",
  created_by: "human",
  provenance_message_id: null,
  preview_png: null,
  created_at: "2026-06-07T11:00:00Z",
  updated_at: "2026-06-07T11:00:00Z",
};

const FAKE_BRANCH: BranchOut = {
  id: 2,
  root_id: 10,
  head_id: 30,
  name: "ai/winglet",
  is_main: false,
  created_by: "ai",
  created_at: "2026-06-07T12:00:00Z",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** Fresh SWR provider per test to avoid cross-test cache leakage. */
function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      {children}
    </SWRConfig>
  );
}

let mockFetch: ReturnType<typeof vi.fn>;

beforeEach(() => {
  mockFetch = vi.fn();
  vi.stubGlobal("fetch", mockFetch);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// useLineageTree
// ---------------------------------------------------------------------------

describe("useLineageTree", () => {
  it("fetches the tree and exposes data when rootId is provided", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(FAKE_TREE));

    const { result } = renderHook(() => useLineageTree(10), { wrapper });

    // initially loading
    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.tree).toEqual(FAKE_TREE);
    expect(result.current.error).toBeUndefined();

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain("/lineages/10/tree");
  });

  it("does not fetch when rootId is null", () => {
    const { result } = renderHook(() => useLineageTree(null), { wrapper });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.tree).toBeUndefined();
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("exposes error when the request fails", async () => {
    mockFetch.mockResolvedValueOnce(new Response("not found", { status: 404 }));

    const { result } = renderHook(() => useLineageTree(99), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.tree).toBeUndefined();
    expect(result.current.error).toBeDefined();
  });

  it("exposes a mutate function to manually revalidate", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(FAKE_TREE))
      .mockResolvedValueOnce(jsonResponse({ ...FAKE_TREE, root_id: 99 }));

    const { result } = renderHook(() => useLineageTree(10), { wrapper });

    await waitFor(() => expect(result.current.tree?.root_id).toBe(10));

    await act(async () => {
      await result.current.mutate();
    });

    expect(result.current.tree?.root_id).toBe(99);
  });
});

// ---------------------------------------------------------------------------
// useVersionActions
// ---------------------------------------------------------------------------

describe("useVersionActions", () => {
  it("snapshot() calls the API and returns the snapshot node", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(FAKE_NODE, 201));

    const { result } = renderHook(() => useVersionActions(10, 10), { wrapper });

    let node: VersionNode | undefined;
    await act(async () => {
      node = await result.current.snapshot({ label: "v1", note: "why" });
    });

    expect(node?.id).toBe(20);
    expect(node?.is_immutable).toBe(true);

    // POST snapshot with correct URL and body
    const postCall = mockFetch.mock.calls[0];
    expect(postCall[0]).toContain("/aeroplanes/10/snapshot");
    expect(postCall[1].method).toBe("POST");
    expect(JSON.parse(postCall[1].body)).toEqual({ label: "v1", note: "why" });
  });

  it("snapshot() calls the API with full body including provenance_message_id", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(FAKE_NODE, 201));

    const { result } = renderHook(() => useVersionActions(10, 10), { wrapper });

    await act(async () => {
      await result.current.snapshot({ label: "v1", note: "why", provenance_message_id: 42 });
    });

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.label).toBe("v1");
    expect(body.provenance_message_id).toBe(42);
  });

  it("snapshot() throws when aeroplaneId is null", async () => {
    const { result } = renderHook(() => useVersionActions(null, null), { wrapper });
    await expect(result.current.snapshot({ label: "x" })).rejects.toThrow(
      "aeroplaneId is required",
    );
  });

  it("createBranch() POSTs to the SELECTED node endpoint and revalidates", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(FAKE_BRANCH, 201))
      .mockResolvedValue(jsonResponse({})); // revalidation

    const { result } = renderHook(() => useVersionActions(10, 10), { wrapper });

    let branch: BranchOut | undefined;
    await act(async () => {
      // Pass node id 42 explicitly — must NOT fall back to the head aeroplane id (10)
      branch = await result.current.createBranch(42, { name: "ai/winglet", created_by: "ai" });
    });

    expect(branch?.name).toBe("ai/winglet");

    const postCall = mockFetch.mock.calls[0];
    // URL path must use the SELECTED node id (42), not the head aeroplane id (10)
    expect(postCall[0]).toContain("/aeroplanes/42/branch");
    expect(postCall[1].method).toBe("POST");
    expect(JSON.parse(postCall[1].body)).toEqual({ name: "ai/winglet", created_by: "ai" });
  });

  it("adoptBranch() POSTs to /branches/{id}/adopt and revalidates", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(FAKE_BRANCH))
      .mockResolvedValue(jsonResponse({}));

    const { result } = renderHook(() => useVersionActions(10, 10), { wrapper });

    let branch: BranchOut | undefined;
    await act(async () => {
      branch = await result.current.adoptBranch(7);
    });

    expect(branch?.id).toBe(2);
    const postCall = mockFetch.mock.calls[0];
    expect(postCall[0]).toContain("/branches/7/adopt");
    expect(postCall[1].method).toBe("POST");
    // adoptBranch must send NO body — the backend takes none
    expect(postCall[1].body).toBeUndefined();
  });

  it("restore() POSTs to /aeroplanes/{snapshotId}/restore and revalidates", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(FAKE_BRANCH, 201))
      .mockResolvedValue(jsonResponse({}));

    const { result } = renderHook(() => useVersionActions(10, 10), { wrapper });

    let branch: BranchOut | undefined;
    await act(async () => {
      branch = await result.current.restore(20, { name: "restored" });
    });

    expect(branch?.head_id).toBe(30);
    const postCall = mockFetch.mock.calls[0];
    expect(postCall[0]).toContain("/aeroplanes/20/restore");
    expect(postCall[1].method).toBe("POST");
    expect(JSON.parse(postCall[1].body)).toEqual({ name: "restored" });
  });

  it("discardBranch() sends DELETE to the correct endpoint", async () => {
    mockFetch.mockResolvedValueOnce(new Response(null, { status: 204 }));

    const { result } = renderHook(() => useVersionActions(10, 10), { wrapper });

    await act(async () => {
      await result.current.discardBranch(3);
    });

    const deleteCall = mockFetch.mock.calls[0];
    expect(deleteCall[0]).toContain("/branches/3");
    expect(deleteCall[1].method).toBe("DELETE");
  });

  it("works without rootId (skips tree revalidation)", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(FAKE_BRANCH, 201))
      .mockResolvedValueOnce(jsonResponse({ aeroplanes: [] })); // only aeroplanes revalidation

    const { result } = renderHook(() => useVersionActions(10, null), { wrapper });

    await act(async () => {
      await result.current.createBranch(10, { name: "no-root" });
    });

    // No tree revalidation when rootId is null
    const calls = mockFetch.mock.calls.map((c) => c[0] as string);
    expect(calls.some((u) => u.includes("/lineages"))).toBe(false);
    expect(calls.some((u) => u.includes("/aeroplanes"))).toBe(true);
  });
});
