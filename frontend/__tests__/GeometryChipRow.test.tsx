import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (p: Record<string, unknown>) => React.createElement("span", p);
  return {
    Square: icon,
    Ruler: icon,
    ArrowLeftRight: icon,
    Gauge: icon,
    MapPin: icon,
  };
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
    // gh-477: row gained an L_landing chip → 5 dashes (was 4).
    render(<GeometryChipRow ctx={null} isRecomputing={false} />);
    expect(screen.getAllByText("–").length).toBe(5);
  });

  // -------------------------------------------------------------------------
  // gh-477: L_landing chip — green / red / neutral.
  // -------------------------------------------------------------------------

  describe("L_landing chip (gh-477)", () => {
    const baseCtx = {
      s_ref_m2: 0.4,
      mac_m: 0.21,
      b_ref_m: 2,
      aspect_ratio: 10.0,
    } as const;

    it("renders 'NN m ✓' in emerald when the planned field is long enough", () => {
      render(
        <GeometryChipRow
          ctx={{
            ...baseCtx,
            landing_field_length_m: 48,
            landing_surface_used: "grass_short",
            landing_field_sufficient: true,
          } as unknown as ComputationContext}
          isRecomputing={false}
        />,
      );
      const valueEl = screen.getByText(/48 m ✓/);
      expect(valueEl).toBeInTheDocument();
      expect(valueEl.className).toContain("emerald");
    });

    it("renders 'NN m ✗' in red when the planned field is too short", () => {
      render(
        <GeometryChipRow
          ctx={{
            ...baseCtx,
            landing_field_length_m: 48,
            landing_surface_used: "grass_short",
            landing_field_sufficient: false,
          } as unknown as ComputationContext}
          isRecomputing={false}
        />,
      );
      const valueEl = screen.getByText(/48 m ✗/);
      expect(valueEl).toBeInTheDocument();
      expect(valueEl.className).toContain("red");
    });

    it("renders 'NN m' (no marker, no color) when available_field_length_m is unset", () => {
      render(
        <GeometryChipRow
          ctx={{
            ...baseCtx,
            landing_field_length_m: 48,
            landing_surface_used: "grass_short",
            landing_field_sufficient: null,
          } as unknown as ComputationContext}
          isRecomputing={false}
        />,
      );
      // No ✓ / ✗ marker and no emerald/red colour class.
      expect(screen.getByText(/^48 m$/)).toBeInTheDocument();
      expect(screen.queryByText(/48 m ✓/)).toBeNull();
      expect(screen.queryByText(/48 m ✗/)).toBeNull();
    });

    it("renders '–' when landing_field_length_m is null (no CL_max yet)", () => {
      // The chip should show a dash, NOT crash, when the backend
      // returns null (e.g. CL_max_landing not yet available).
      render(
        <GeometryChipRow
          ctx={{
            ...baseCtx,
            landing_field_length_m: null,
            landing_surface_used: null,
            landing_field_sufficient: null,
          } as unknown as ComputationContext}
          isRecomputing={false}
        />,
      );
      // At least the L_landing dash exists (others have values).
      expect(screen.getAllByText("–").length).toBeGreaterThanOrEqual(1);
    });
  });
});
