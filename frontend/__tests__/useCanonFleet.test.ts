import { describe, it, expect, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { useCanonFleet } from "@/hooks/useCanonFleet";

const swr = vi.fn();
vi.mock("swr", () => ({ default: (...args: unknown[]) => swr(...args) }));

describe("useCanonFleet", () => {
  it("reads the fleet from the canon endpoint", () => {
    const fleet = [{ id: "bryan", name: "BRYAN", mass_kg: 0.151, flap_deflections: {} }];
    swr.mockReturnValue({ data: fleet, error: undefined, isLoading: false });
    const { result } = renderHook(() => useCanonFleet());
    expect(swr.mock.calls[0][0]).toBe("/canon/fleet");
    expect(result.current.fleet).toEqual(fleet);
  });

  it("is an empty fleet while loading", () => {
    swr.mockReturnValue({ data: undefined, error: undefined, isLoading: true });
    const { result } = renderHook(() => useCanonFleet());
    expect(result.current.fleet).toEqual([]);
    expect(result.current.isLoading).toBe(true);
  });
});
