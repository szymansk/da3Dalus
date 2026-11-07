import { describe, it, expect, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { useCanonAircraft } from "@/hooks/useCanonAircraft";

const swr = vi.fn();
vi.mock("swr", () => ({ default: (...args: unknown[]) => swr(...args) }));

describe("useCanonAircraft", () => {
  it("reads the fleet and the stored aeroplanes from the canon endpoint", () => {
    const fleet = [{ id: "bryan", name: "BRYAN", mass_kg: 0.151, flap_deflections: {} }];
    const aeroplanes = [{ id: "6f1c1a52-8f3c-4a43-9d9a-2c7c4c3b5a10", name: "Mine", mass_kg: null }];
    swr.mockReturnValue({ data: { fleet, aeroplanes }, error: undefined, isLoading: false });
    const { result } = renderHook(() => useCanonAircraft());
    expect(swr.mock.calls[0][0]).toBe("/canon/aircraft");
    expect(result.current.fleet).toEqual(fleet);
    expect(result.current.aeroplanes).toEqual(aeroplanes);
  });

  it("has no aircraft while loading", () => {
    swr.mockReturnValue({ data: undefined, error: undefined, isLoading: true });
    const { result } = renderHook(() => useCanonAircraft());
    expect(result.current.fleet).toEqual([]);
    expect(result.current.aeroplanes).toEqual([]);
    expect(result.current.isLoading).toBe(true);
  });
});
