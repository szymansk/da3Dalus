import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

vi.mock("@/hooks/useComputationContext", () => ({
  useComputationContext: vi.fn(),
}));

import { useComputationContext } from "@/hooks/useComputationContext";
import { StabilityOverlay } from "@/components/workbench/stability-overlay/StabilityOverlay";

const mockedHook = vi.mocked(useComputationContext);

function withCtx(ctx: Record<string, unknown> | null) {
  mockedHook.mockReturnValue({
    data: ctx as never,
    error: null,
    isLoading: false,
    mutate: vi.fn(),
  } as never);
}

describe("StabilityOverlay", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("publishes 5 traces via register when fully enabled with complete data", () => {
    withCtx({ x_np_m: 2.607, mac_m: 1.387, cg_agg_m: 2.510, target_static_margin: 0.12 });
    const register = vi.fn();
    render(<StabilityOverlay aeroplaneId="a" register={register} />);
    expect(register).toHaveBeenCalled();
    const lastCall = register.mock.calls[register.mock.calls.length - 1][0];
    expect(lastCall).toHaveLength(5);
  });

  it("publishes empty array when ctx is null", () => {
    withCtx(null);
    const register = vi.fn();
    render(<StabilityOverlay aeroplaneId="a" register={register} />);
    const lastCall = register.mock.calls[register.mock.calls.length - 1][0];
    expect(lastCall).toEqual([]);
  });

  it("publishes empty array when toggled off", () => {
    withCtx({ x_np_m: 2.607, mac_m: 1.387, cg_agg_m: 2.510, target_static_margin: 0.12 });
    const register = vi.fn();
    render(<StabilityOverlay aeroplaneId="a" register={register} />);
    fireEvent.click(screen.getByRole("button", { name: /stability/i }));
    const lastCall = register.mock.calls[register.mock.calls.length - 1][0];
    expect(lastCall).toEqual([]);
  });

  it("persists toggle state in localStorage", () => {
    withCtx({ x_np_m: 2.607, mac_m: 1.387, cg_agg_m: 2.510, target_static_margin: 0.12 });
    const register = vi.fn();
    render(<StabilityOverlay aeroplaneId="a" register={register} />);
    fireEvent.click(screen.getByRole("button", { name: /stability/i }));
    expect(localStorage.getItem("stabilityOverlayEnabled")).toBe("false");
  });

  it("reads initial state from localStorage", () => {
    localStorage.setItem("stabilityOverlayEnabled", "false");
    withCtx({ x_np_m: 2.607, mac_m: 1.387, cg_agg_m: 2.510, target_static_margin: 0.12 });
    const register = vi.fn();
    render(<StabilityOverlay aeroplaneId="a" register={register} />);
    const lastCall = register.mock.calls[register.mock.calls.length - 1][0];
    expect(lastCall).toEqual([]);
  });

  it("omits IST trace when cg_agg_m is null", () => {
    withCtx({ x_np_m: 2.607, mac_m: 1.387, cg_agg_m: null, target_static_margin: 0.12 });
    const register = vi.fn();
    render(<StabilityOverlay aeroplaneId="a" register={register} />);
    const lastCall = register.mock.calls[register.mock.calls.length - 1][0];
    const names = lastCall.map((t: { name: string }) => t.name);
    expect(names).not.toContain("CG (actual)");
    expect(names).toContain("NP");
    expect(names).toContain("CG (design)");
  });

  it("forwards referenceY and referenceZ to the trace builder", () => {
    withCtx({ x_np_m: 2.607, mac_m: 1.387, cg_agg_m: 2.510, target_static_margin: 0.12 });
    const register = vi.fn();
    render(
      <StabilityOverlay aeroplaneId="a" register={register} referenceY={0} referenceZ={0.45} />,
    );
    const lastCall = register.mock.calls[register.mock.calls.length - 1][0];
    const np = lastCall.find((t: { name: string }) => t.name === "NP")!;
    expect((np.y as number[])[0]).toBeCloseTo(0, 6);
    expect((np.z as number[])[0]).toBeCloseTo(0.45, 6);
  });

  it("clears its registered traces on unmount", () => {
    withCtx({ x_np_m: 2.607, mac_m: 1.387, cg_agg_m: 2.510, target_static_margin: 0.12 });
    const register = vi.fn();
    const { unmount } = render(<StabilityOverlay aeroplaneId="a" register={register} />);
    register.mockClear();
    unmount();
    expect(register).toHaveBeenCalledTimes(1);
    expect(register).toHaveBeenCalledWith([]);
  });
});
