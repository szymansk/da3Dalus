import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (p: Record<string, unknown>) => React.createElement("span", p);
  return { Square: icon, Ruler: icon, ArrowLeftRight: icon, Gauge: icon };
});

import { GeometryChipRow } from "@/components/workbench/GeometryChipRow";
import type { ComputationContext } from "@/hooks/useComputationContext";

describe("GeometryChipRow", () => {
  it("renders S_ref, MAC, B_ref, AR", () => {
    render(
      <GeometryChipRow
        ctx={{
          s_ref_m2: 0.4,
          mac_m: 0.21,
          b_ref_m: 2.0,
          aspect_ratio: 10.0,
        } as unknown as ComputationContext}
        isRecomputing={false}
      />,
    );
    expect(screen.getByText(/0\.400 m²/)).toBeInTheDocument();
    expect(screen.getByText(/0\.21 m/)).toBeInTheDocument();
    expect(screen.getByText(/2\.00 m/)).toBeInTheDocument();
    expect(screen.getByText(/10\.00$/)).toBeInTheDocument();
  });

  it("AR=null → '–'", () => {
    render(
      <GeometryChipRow
        ctx={{ s_ref_m2: 0.4, mac_m: 0.21, b_ref_m: 2, aspect_ratio: null } as unknown as ComputationContext}
        isRecomputing={false}
      />,
    );
    expect(screen.getAllByText("–").length).toBeGreaterThanOrEqual(1);
  });

  it("ctx=null → all dashes", () => {
    render(<GeometryChipRow ctx={null} isRecomputing={false} />);
    expect(screen.getAllByText("–").length).toBe(4);
  });
});
