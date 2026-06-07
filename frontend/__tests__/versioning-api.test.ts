/**
 * Unit tests for frontend/lib/versioning-api.ts (gh-907).
 *
 * Each client function must hit the correct URL, method, and request body.
 * fetch is stubbed so no real network calls are made.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as vapi from "@/lib/versioning-api";
import type { BranchOut, CompareOut, TreeOut, VersionNode } from "@/types/versioning";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const FAKE_VERSION_NODE: VersionNode = {
  id: 10,
  uuid: "aaaa-bbbb",
  name: "My Plane",
  branch_id: 1,
  predecessor_id: null,
  root_id: 10,
  is_immutable: true,
  version_label: "v1",
  version_note: "first snapshot",
  created_by: "human",
  provenance_message_id: null,
  preview_png: null,
  created_at: "2026-06-07T10:00:00Z",
  updated_at: "2026-06-07T10:00:00Z",
};

const FAKE_BRANCH_OUT: BranchOut = {
  id: 1,
  root_id: 10,
  head_id: 11,
  name: "main",
  is_main: true,
  created_by: "human",
  created_at: "2026-06-07T10:00:00Z",
};

const FAKE_TREE_OUT: TreeOut = {
  root_id: 10,
  nodes: [
    {
      id: 10,
      uuid: "aaaa-bbbb",
      name: "My Plane",
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
  branches: [FAKE_BRANCH_OUT],
};

const FAKE_COMPARE_OUT: CompareOut = {
  node_a: FAKE_VERSION_NODE,
  node_b: { ...FAKE_VERSION_NODE, id: 11 },
  metrics_a: { wingspan_m: 1.5 },
  metrics_b: { wingspan_m: 1.6 },
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

// ---------------------------------------------------------------------------
// Setup / teardown
// ---------------------------------------------------------------------------

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
// snapshot
// ---------------------------------------------------------------------------

describe("snapshot()", () => {
  it("POSTs to /aeroplanes/{id}/snapshot with label + note", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(FAKE_VERSION_NODE, 201));

    const result = await vapi.snapshot(42, { label: "v1", note: "why" });

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/aeroplanes/42/snapshot");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ label: "v1", note: "why" });
    expect(result.id).toBe(10);
    expect(result.is_immutable).toBe(true);
  });

  it("POSTs with only label (note omitted)", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(FAKE_VERSION_NODE, 201));

    await vapi.snapshot(5, { label: "minimal" });

    const body = JSON.parse(mockFetch.mock.calls[0][1].body as string);
    expect(body.label).toBe("minimal");
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce(new Response("not found", { status: 404 }));
    await expect(vapi.snapshot(99, { label: "x" })).rejects.toThrow("404");
  });
});

// ---------------------------------------------------------------------------
// createBranch
// ---------------------------------------------------------------------------

describe("createBranch()", () => {
  it("POSTs to /aeroplanes/{id}/branch with name + created_by", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(FAKE_BRANCH_OUT, 201));

    const result = await vapi.createBranch(42, { name: "ai/winglet", created_by: "ai" });

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/aeroplanes/42/branch");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ name: "ai/winglet", created_by: "ai" });
    expect(result.name).toBe("main");
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce(new Response("conflict", { status: 409 }));
    await expect(vapi.createBranch(1, { name: "x" })).rejects.toThrow("409");
  });
});

// ---------------------------------------------------------------------------
// adoptBranch
// ---------------------------------------------------------------------------

describe("adoptBranch()", () => {
  it("POSTs to /branches/{id}/adopt with empty body", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(FAKE_BRANCH_OUT));

    const result = await vapi.adoptBranch(7);

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/branches/7/adopt");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({});
    expect(result.id).toBe(1);
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce(new Response("already main", { status: 409 }));
    await expect(vapi.adoptBranch(99)).rejects.toThrow("409");
  });
});

// ---------------------------------------------------------------------------
// restore
// ---------------------------------------------------------------------------

describe("restore()", () => {
  it("POSTs to /aeroplanes/{snapshot_id}/restore with branch name", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(FAKE_BRANCH_OUT, 201));

    const result = await vapi.restore(20, { name: "restored-from-v1" });

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/aeroplanes/20/restore");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ name: "restored-from-v1" });
    expect(result.head_id).toBe(11);
  });
});

// ---------------------------------------------------------------------------
// discardBranch
// ---------------------------------------------------------------------------

describe("discardBranch()", () => {
  it("sends DELETE to /branches/{id}", async () => {
    mockFetch.mockResolvedValueOnce(new Response(null, { status: 204 }));

    await vapi.discardBranch(3);

    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toContain("/branches/3");
    expect(init.method).toBe("DELETE");
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce(new Response("cannot discard main", { status: 409 }));
    await expect(vapi.discardBranch(1)).rejects.toThrow("409");
  });
});

// ---------------------------------------------------------------------------
// getLineageTree
// ---------------------------------------------------------------------------

describe("getLineageTree()", () => {
  it("GETs /lineages/{root_id}/tree and returns TreeOut", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(FAKE_TREE_OUT));

    const result = await vapi.getLineageTree(10);

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain("/lineages/10/tree");
    expect(result.root_id).toBe(10);
    expect(result.nodes).toHaveLength(1);
    expect(result.branches).toHaveLength(1);
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce(new Response("not found", { status: 404 }));
    await expect(vapi.getLineageTree(999)).rejects.toThrow("404");
  });
});

// ---------------------------------------------------------------------------
// compareNodes
// ---------------------------------------------------------------------------

describe("compareNodes()", () => {
  it("GETs /aeroplanes/compare?a=&b= and returns CompareOut", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(FAKE_COMPARE_OUT));

    const result = await vapi.compareNodes(10, 11);

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain("/aeroplanes/compare");
    expect(url).toContain("a=10");
    expect(url).toContain("b=11");
    expect(result.node_a.id).toBe(10);
    expect(result.node_b.id).toBe(11);
    expect(result.metrics_a).toEqual({ wingspan_m: 1.5 });
    expect(result.metrics_b).toEqual({ wingspan_m: 1.6 });
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce(new Response("not found", { status: 404 }));
    await expect(vapi.compareNodes(1, 2)).rejects.toThrow("404");
  });
});
