import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) => React.createElement("span", props);
  return { Wind: icon, SlidersHorizontal: icon, Activity: icon, Ruler: icon, Target: icon, Navigation: icon, Settings: icon };
});

vi.mock("@/hooks/useComputationContext", () => ({
  useComputationContext: vi.fn(),
}));

import { useComputationContext } from "@/hooks/useComputationContext";

describe("Info Chip Row", () => {
  it("shows dynamic values when context is available", async () => {
    (useComputationContext as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        v_cruise_mps: 18.0,
        reynolds: 230000,
        mac_m: 0.21,
        x_np_m: 0.085,
        target_static_margin: 0.12,
        cg_agg_m: 0.092,
      },
      isLoading: false,
      error: null,
    });

    const { InfoChipRow } = await import("@/components/workbench/InfoChipRow");
    render(<InfoChipRow aeroplaneId="42" cgAero={0.073} />);

    expect(screen.getByText(/18\.0 m\/s/)).toBeInTheDocument();
    expect(screen.getByText(/2\.3e\+?5/i)).toBeInTheDocument();
    expect(screen.getByText(/0\.21 m/)).toBeInTheDocument();
    expect(screen.getByText(/0\.085 m/)).toBeInTheDocument();
  });

  it("shows dashes when no context", async () => {
    (useComputationContext as ReturnType<typeof vi.fn>).mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    const { InfoChipRow } = await import("@/components/workbench/InfoChipRow");
    render(<InfoChipRow aeroplaneId="42" cgAero={null} />);

    const dashes = screen.getAllByText("–");
    expect(dashes.length).toBeGreaterThanOrEqual(4);
  });
});
