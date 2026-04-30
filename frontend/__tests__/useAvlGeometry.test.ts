import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useAvlGeometry } from "@/hooks/useAvlGeometry";

const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("useAvlGeometry", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches geometry on mount", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          content: "SURFACE\n",
          is_dirty: false,
          is_user_edited: false,
        }),
    });

    const { result } = renderHook(() => useAvlGeometry("test-id"));

    await waitFor(() => {
      expect(result.current.content).toBe("SURFACE\n");
    });
    expect(result.current.isDirty).toBe(false);
    expect(result.current.isUserEdited).toBe(false);
  });

  it("does not fetch when aeroplaneId is null", () => {
    renderHook(() => useAvlGeometry(null));
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("save sends PUT request", async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({ content: "OLD", is_dirty: false, is_user_edited: false }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({ content: "NEW", is_dirty: false, is_user_edited: true }),
      });

    const { result } = renderHook(() => useAvlGeometry("test-id"));

    await waitFor(() => expect(result.current.content).toBe("OLD"));

    await act(async () => {
      await result.current.save("NEW");
    });

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/aeroplanes/test-id/avl-geometry"),
      expect.objectContaining({ method: "PUT" }),
    );
  });
});
