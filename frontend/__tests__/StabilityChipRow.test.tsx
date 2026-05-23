import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (p: Record<string, unknown>) => React.createElement("span", p);
  return { Target: icon, Navigation: icon };
});

import { StabilityChipRow } from "@/components/workbench/StabilityChipRow";
import type { ComputationContext } from "@/hooks/useComputationContext";

describe("StabilityChipRow", () => {
  it("renders NP, SM, CG", () => {
    render(
      <StabilityChipRow
        ctx={{
          x_np_m: 0.085,
          target_static_margin: 0.12,
          cg_agg_m: 0.092,
          mac_m: 0.21,
        } as unknown as ComputationContext}
        cgAero={0.073}
        isRecomputing={false}
      />,
    );
    expect(screen.getByText(/0\.085 m/)).toBeInTheDocument();
    expect(screen.getByText(/12%/)).toBeInTheDocument();
    expect(screen.getByText(/0\.073 m/)).toBeInTheDocument();
  });

  it("ctx=null → dashes", () => {
    render(<StabilityChipRow ctx={null} cgAero={null} isRecomputing={false} />);
    expect(screen.getAllByText("–").length).toBeGreaterThanOrEqual(3);
  });
});
