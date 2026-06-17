/**
 * gh-1042: useOperatingPoints.refresh() must build a valid URL even when the
 * API base is a RELATIVE path prefix (e.g. "/main/backend" on the multi-stage
 * ngrok deploy). `new URL(str)` with a single argument requires an absolute
 * URL, so a relative API base threw '"/main/backend/operating_points" cannot
 * be parsed as a URL'. We mock the API base to the relative prefix and assert
 * refresh() fetches the resolved URL instead of throwing.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";

// Force a RELATIVE API base, as the multi-stage deploy injects.
vi.mock("@/lib/fetcher", () => ({ API_BASE: "/main/backend" }));

import { useOperatingPoints } from "@/hooks/useOperatingPoints";

describe("useOperatingPoints refresh() with a relative API base (gh-1042)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("resolves the relative base against the page origin and fetches it", async () => {
    // Fresh Response per call — refresh runs on mount and again explicitly,
    // and a single Response body can only be read once.
    const fetchSpy = vi.spyOn(global, "fetch").mockImplementation(
      async () =>
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
    );

    const { result } = renderHook(() => useOperatingPoints("7"));

    await act(async () => {
      await result.current.refresh();
    });

    // refresh runs once on mount + once explicitly; without the fix new URL()
    // throws before fetch, so any fetch call proves the relative base resolved.
    await waitFor(() => expect(fetchSpy).toHaveBeenCalled());
    const arg = fetchSpy.mock.calls.at(-1)![0] as URL;
    const url = new URL(String(arg));
    // The relative "/main/backend" prefix is preserved in the resolved path.
    expect(url.pathname).toBe("/main/backend/operating_points");
    expect(url.searchParams.get("aircraft_id")).toBe("7");
    // No "cannot be parsed as a URL" error leaked into hook state.
    expect(result.current.error).toBeNull();
  });
});
