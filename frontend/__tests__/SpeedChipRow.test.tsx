import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (p: Record<string, unknown>) => React.createElement("span", p);
  return {
    Wind: icon, AlertTriangle: icon, Plane: icon, Gauge: icon,
    TrendingUp: icon, Zap: icon,
  };
});

import { SpeedChipRow } from "@/components/workbench/SpeedChipRow";
import type { ComputationContext } from "@/hooks/useComputationContext";

const baseCtx = {
  v_cruise_mps: 18.0,
  v_stall_mps: 13.2,
  v_md_mps: 17.0,
  v_min_sink_mps: 14.5,
  v_max_mps: 25.0,
  v_a_mps: 19.0,
  v_dive_mps: 35.0,
  v_x_mps: 12.0,
  v_y_mps: 15.5,
  is_glider: false,
};

describe("SpeedChipRow", () => {
  it("renders all V-speed chips when context complete", () => {
    render(<SpeedChipRow ctx={baseCtx as unknown as ComputationContext} isRecomputing={false} />);
    expect(screen.getByText(/13\.2 m\/s/)).toBeInTheDocument();
    expect(screen.getByText(/18\.0 m\/s/)).toBeInTheDocument();
    expect(screen.getByText(/35\.0 m\/s/)).toBeInTheDocument();
  });

  it("V_cruise* tooltip indicates auto-derived", () => {
    render(
      <SpeedChipRow
        ctx={{ ...baseCtx, v_cruise_auto: true } as unknown as ComputationContext}
        isRecomputing={false}
      />,
    );
    expect(screen.getByText(/auto-derived from cruise sizing/i)).toBeInTheDocument();
  });

  it("hides V_a, V_max, V_dive when is_glider=true", () => {
    render(
      <SpeedChipRow
        ctx={{ ...baseCtx, is_glider: true } as unknown as ComputationContext}
        isRecomputing={false}
      />,
    );
    expect(screen.queryByText(/manoeuvring speed/i)).toBeNull();
    expect(screen.queryByText(/Maximum operating speed/i)).toBeNull();
    expect(screen.queryByText(/dive speed/i)).toBeNull();
  });

  it("shows dashes when ctx is null", () => {
    render(<SpeedChipRow ctx={null} isRecomputing={false} />);
    const dashes = screen.getAllByText("–");
    expect(dashes.length).toBeGreaterThanOrEqual(6);
  });

  it("rightSlot renders next to the speed chips", () => {
    render(
      <SpeedChipRow
        ctx={baseCtx as unknown as ComputationContext}
        isRecomputing={false}
        rightSlot={<button data-testid="my-slot">slot</button>}
      />,
    );
    expect(screen.getByTestId("my-slot")).toBeInTheDocument();
  });

  // gh-871: angle of attack display
  describe("gh-871 α at characteristic speeds", () => {
    it("shows α alongside V_stall when alpha_stall_deg is available", () => {
      render(
        <SpeedChipRow
          ctx={{ ...baseCtx, alpha_stall_deg: 14.5 } as unknown as ComputationContext}
          isRecomputing={false}
        />,
      );
      // V_stall chip must show "13.2 m/s @ 14.5°"
      expect(screen.getByText("13.2 m/s @ 14.5°")).toBeInTheDocument();
    });

    it("shows α alongside V_min_sink when alpha_min_sink_deg is available", () => {
      render(
        <SpeedChipRow
          ctx={{ ...baseCtx, alpha_min_sink_deg: 8.3 } as unknown as ComputationContext}
          isRecomputing={false}
        />,
      );
      expect(screen.getByText("14.5 m/s @ 8.3°")).toBeInTheDocument();
    });

    it("shows α alongside V_md when alpha_best_glide_deg is available", () => {
      render(
        <SpeedChipRow
          ctx={{ ...baseCtx, alpha_best_glide_deg: 6.2 } as unknown as ComputationContext}
          isRecomputing={false}
        />,
      );
      expect(screen.getByText("17.0 m/s @ 6.2°")).toBeInTheDocument();
    });

    it("shows speed without α suffix when alpha_stall_deg is null", () => {
      render(
        <SpeedChipRow
          ctx={{ ...baseCtx, alpha_stall_deg: null } as unknown as ComputationContext}
          isRecomputing={false}
        />,
      );
      expect(screen.getByText("13.2 m/s")).toBeInTheDocument();
    });

    it("shows speed without α suffix when alpha field is absent from context", () => {
      // baseCtx has no alpha fields at all
      render(<SpeedChipRow ctx={baseCtx as unknown as ComputationContext} isRecomputing={false} />);
      // No "@ " pattern should appear in the V_stall chip when alpha is absent
      const stall = screen.getByText(/13\.2 m\/s/);
      expect(stall.textContent).not.toContain("@");
    });

    it("all three alpha chips together", () => {
      render(
        <SpeedChipRow
          ctx={{
            ...baseCtx,
            alpha_stall_deg: 14.5,
            alpha_min_sink_deg: 8.3,
            alpha_best_glide_deg: 6.2,
          } as unknown as ComputationContext}
          isRecomputing={false}
        />,
      );
      expect(screen.getByText("13.2 m/s @ 14.5°")).toBeInTheDocument();
      expect(screen.getByText("14.5 m/s @ 8.3°")).toBeInTheDocument();
      expect(screen.getByText("17.0 m/s @ 6.2°")).toBeInTheDocument();
    });
  });
});
