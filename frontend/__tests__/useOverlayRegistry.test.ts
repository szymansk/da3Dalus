import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useOverlayRegistry } from "@/hooks/useOverlayRegistry";

describe("useOverlayRegistry", () => {
  it("starts with an empty traces array", () => {
    const { result } = renderHook(() => useOverlayRegistry());
    expect(result.current.traces).toEqual([]);
  });

  it("returns a stable register(key) callback per key across renders", () => {
    const { result, rerender } = renderHook(() => useOverlayRegistry());
    const cb1 = result.current.register("stability");
    rerender();
    const cb2 = result.current.register("stability");
    expect(cb1).toBe(cb2);
  });

  it("accumulates traces registered under different keys (insertion order preserved)", () => {
    const { result } = renderHook(() => useOverlayRegistry());

    act(() => {
      result.current.register("a")([{ type: "scatter3d", x: [1], y: [0], z: [0] }]);
      result.current.register("b")([{ type: "scatter3d", x: [2], y: [0], z: [0] }]);
    });

    expect(result.current.traces).toHaveLength(2);
    expect((result.current.traces[0] as { x: number[] }).x).toEqual([1]);
    expect((result.current.traces[1] as { x: number[] }).x).toEqual([2]);
  });

  it("replaces traces for an existing key on re-register", () => {
    const { result } = renderHook(() => useOverlayRegistry());

    act(() => { result.current.register("stability")([{ type: "scatter3d", x: [1], y: [0], z: [0] }]); });
    act(() => { result.current.register("stability")([{ type: "scatter3d", x: [99], y: [0], z: [0] }]); });

    expect(result.current.traces).toHaveLength(1);
    expect((result.current.traces[0] as { x: number[] }).x).toEqual([99]);
  });

  it("removes the key when registering an empty array", () => {
    const { result } = renderHook(() => useOverlayRegistry());

    act(() => { result.current.register("stability")([{ type: "scatter3d", x: [1], y: [0], z: [0] }]); });
    act(() => { result.current.register("stability")([]); });

    expect(result.current.traces).toEqual([]);
  });
});
