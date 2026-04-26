/**
 * GH#343 — regression test for the URL the executePlan hook calls.
 *
 * The bug: backend was rejecting template execution with 422
 * "Templates cannot be executed", because the guard was active in the
 * shared svc.execute_plan service. The frontend executePlan() hook
 * targets POST /aeroplanes/{aero_id}/construction-plans/{plan_id}/execute
 * which delegates to the same service.
 *
 * This test pins the exact URL/method/body that the frontend issues so
 * that any future refactor of the contract is caught immediately, before
 * a manual click-test reveals it.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { executePlan, executionZipUrl } from "@/hooks/useConstructionPlans";

describe("executePlan hook (gh#343 regression guard)", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("POSTs to /aeroplanes/{aero_id}/construction-plans/{plan_id}/execute with empty body", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          status: "success",
          shape_keys: [],
          duration_ms: 12,
          tessellation: null,
          artifact_dir: "/tmp/x",
          execution_id: "exec-1",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    const result = await executePlan("389b5778-54cc-484e-a2db-46f18e448f00", 27);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain(
      "/aeroplanes/389b5778-54cc-484e-a2db-46f18e448f00/construction-plans/27/execute",
    );
    expect(init).toMatchObject({
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    expect(result.status).toBe("success");
  });

  it("surfaces a backend 422 (e.g. template-guard regression) as a thrown error", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({ detail: "Templates cannot be executed. Instantiate as a plan first." }),
        { status: 422, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(executePlan("aero-x", 27)).rejects.toThrow(/422/);
  });
});

describe("executionZipUrl helper (gh#339)", () => {
  it("returns the /zip endpoint URL for a plan/execution pair", () => {
    const url = executionZipUrl(42, "20260426T094402Z");

    expect(url).toContain("/construction-plans/42/artifacts/");
    expect(url).toContain("/zip");
    expect(url).toMatch(/\/artifacts\/20260426T094402Z\/zip$/);
  });

  it("URL-encodes the execution_id", () => {
    const url = executionZipUrl(7, "exec id with spaces");
    expect(url).toContain("exec%20id%20with%20spaces");
  });
});
