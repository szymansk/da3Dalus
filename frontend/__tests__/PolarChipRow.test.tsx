import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (p: Record<string, unknown>) => React.createElement("span", p);
  return {
    Wind: icon, Gauge: icon, Activity: icon,
    Target: icon, TrendingUp: icon, AlertTriangle: icon,
  };
});

import { PolarChipRow } from "@/components/workbench/PolarChipRow";
import type { ComputationContext } from "@/hooks/useComputationContext";

// Healthy powered fixture: CD0=0.02, e=0.80, AR=7, CL_max=1.4
// → ρ = 0.02·π·0.8·7/1.4² ≈ 0.180 emerald
const HEALTHY = {
  reynolds: 540000,
  cd0: 0.02,
  e_oswald: 0.80,
  e_oswald_quality: "high" as const,
  e_oswald_fallback_used: false,
  aspect_ratio: 7,
  polar_by_config: { clean: { cl_max: 1.4 } },
  is_glider: false,
};

// Sailplane: CD0=0.008, e=0.95, AR=36, CL_max=1.5, is_glider=true
// ρ = 0.008·π·0.95·36/1.5² ≈ 0.382 — amber on powered thresholds,
// emerald on glider (amber boundary 2/3)
const SAILPLANE = {
  reynolds: 1.2e6,
  cd0: 0.008,
  e_oswald: 0.95,
  e_oswald_quality: "high" as const,
  e_oswald_fallback_used: false,
  aspect_ratio: 36,
  polar_by_config: { clean: { cl_max: 1.5 } },
  is_glider: true,
};

// Fit-rejected (gh-625 reproduction): e_oswald_fallback_used=true
const REJECTED = {
  reynolds: 230000,
  cd0: 0.04,
  e_oswald: null,
  e_oswald_quality: "unknown" as const,
  e_oswald_fallback_used: true,
  aspect_ratio: 6,
  polar_by_config: { clean: { cl_max: 1.0 } },
  is_glider: false,
};

function findRhoValueSpan(container: HTMLElement, rhoText: RegExp): HTMLElement {
  // The ρ value span is inside the polar chip-row, with the rho text.
  const matches = screen.getAllByText(rhoText);
  // Return the last match — the chip's value span (the surrounding chip
  // may render multiple matching texts on different lines; we want the
  // actual value span which carries the colour).
  return matches[matches.length - 1] as HTMLElement;
}

describe("PolarChipRow", () => {
  it("healthy powered: all 8 chips populated, ρ emerald", () => {
    const { container } = render(
      <PolarChipRow
        ctx={HEALTHY as unknown as ComputationContext}
        isRecomputing={false}
      />,
    );
    expect(screen.getByText(/5\.4e\+?5/)).toBeInTheDocument(); // Re
    expect(screen.getByText(/^0\.0200$/)).toBeInTheDocument(); // CD0
    expect(screen.getByText(/^0\.80$/)).toBeInTheDocument();   // e
    expect(screen.getByText(/^0\.0568$/)).toBeInTheDocument(); // k = 1/(π·0.8·7)
    expect(screen.getByText(/^0\.59$/)).toBeInTheDocument();   // C_L,md ≈ 0.5932 → 0.59
    expect(screen.getByText(/^1\.40$/)).toBeInTheDocument();   // C_L,max
    expect(screen.getByText(/^14\.8$/)).toBeInTheDocument();   // (L/D)_max ≈ 14.83
    expect(screen.getByText(/^0\.18$/)).toBeInTheDocument();   // ρ
    expect(container.querySelector(".text-emerald-400")).not.toBeNull();
  });

  it("sailplane: ρ ≈ 0.38 → emerald on glider thresholds", () => {
    render(
      <PolarChipRow
        ctx={SAILPLANE as unknown as ComputationContext}
        isRecomputing={false}
      />,
    );
    const rho = findRhoValueSpan(document.body, /^0\.38$/);
    expect(rho.className).toContain("text-emerald-400");
  });

  it("powered amber lower boundary (ρ = 1/3) → amber", () => {
    // ρ = CD0·π·e·AR / CL_max² = 1/3.  e=0.8, AR=7, CL_max=1.0
    // → CD0 = (1/3) · 1 / (π · 0.8 · 7) = 0.01895
    const ctx = {
      ...HEALTHY,
      cd0: 1 / (3 * Math.PI * 0.8 * 7),
      polar_by_config: { clean: { cl_max: 1.0 } },
    };
    render(
      <PolarChipRow
        ctx={ctx as unknown as ComputationContext}
        isRecomputing={false}
      />,
    );
    const rho = findRhoValueSpan(document.body, /^0\.33$/);
    expect(rho.className).toContain("text-amber-400");
  });

  it("powered red boundary (ρ = 1.00) → red", () => {
    const ctx = {
      ...HEALTHY,
      cd0: 1.0 / (Math.PI * 0.8 * 7), // ρ = 1.0 with CL_max=1
      polar_by_config: { clean: { cl_max: 1.0 } },
    };
    render(
      <PolarChipRow
        ctx={ctx as unknown as ComputationContext}
        isRecomputing={false}
      />,
    );
    const rho = findRhoValueSpan(document.body, /^1\.00$/);
    expect(rho.className).toContain("text-red-400");
  });

  it("glider amber lower boundary (ρ = 2/3, is_glider=true) → amber", () => {
    const ctx = {
      ...SAILPLANE,
      cd0: (2 / 3) / (Math.PI * 0.95 * 36),
      polar_by_config: { clean: { cl_max: 1.0 } },
    };
    render(
      <PolarChipRow
        ctx={ctx as unknown as ComputationContext}
        isRecomputing={false}
      />,
    );
    const rho = findRhoValueSpan(document.body, /^0\.67$/);
    expect(rho.className).toContain("text-amber-400");
  });

  it.each([
    ["high", "text-emerald-400"],
    ["medium", "text-amber-400"],
    ["low", "text-orange-400"],
    ["unknown", "text-muted-foreground"],
  ] as const)("e-quality %s → %s", (q, cls) => {
    const ctx = { ...HEALTHY, e_oswald_quality: q };
    const { container } = render(
      <PolarChipRow
        ctx={ctx as unknown as ComputationContext}
        isRecomputing={false}
      />,
    );
    expect(container.innerHTML).toContain(cls);
  });

  it("#625 reproduction: e* muted + k/CLmd/EMax/ρ all '–'", () => {
    const { container } = render(
      <PolarChipRow
        ctx={REJECTED as unknown as ComputationContext}
        isRecomputing={false}
      />,
    );
    // e* muted
    expect(container.innerHTML).toContain("text-muted-foreground");
    // four derived chips render '–'
    expect(screen.getAllByText("–").length).toBeGreaterThanOrEqual(4);
  });

  it("each null input nukes its dependents", () => {
    const variants: Array<Partial<typeof HEALTHY>> = [
      { ...HEALTHY, cd0: null },
      { ...HEALTHY, aspect_ratio: null },
      { ...HEALTHY, polar_by_config: { clean: { cl_max: null } } },
    ];
    for (const ctx of variants) {
      const { unmount } = render(
        <PolarChipRow
          ctx={ctx as unknown as ComputationContext}
          isRecomputing={false}
        />,
      );
      expect(screen.getAllByText("–").length).toBeGreaterThanOrEqual(1);
      unmount();
    }
  });

  it("ctx=null → at least 7 dashes (CD0, e, k, CLmd, CLmax, EMax, ρ)", () => {
    render(<PolarChipRow ctx={null} isRecomputing={false} />);
    expect(screen.getAllByText("–").length).toBeGreaterThanOrEqual(7);
  });

  it("ρ-red tooltip prescribes 'see Matching Chart'", () => {
    const ctx = {
      ...HEALTHY,
      cd0: 1.0 / (Math.PI * 0.8 * 7),
      polar_by_config: { clean: { cl_max: 1.0 } },
    };
    render(
      <PolarChipRow
        ctx={ctx as unknown as ComputationContext}
        isRecomputing={false}
      />,
    );
    expect(screen.getByText(/see Matching Chart/i)).toBeInTheDocument();
  });

  it("(L/D)_max tooltip contains 'headline polar number'", () => {
    render(
      <PolarChipRow
        ctx={HEALTHY as unknown as ComputationContext}
        isRecomputing={false}
      />,
    );
    expect(screen.getByText(/headline polar number/i)).toBeInTheDocument();
  });

  it("bail-rule tooltip contains 'non-parabolic'", () => {
    render(
      <PolarChipRow
        ctx={REJECTED as unknown as ComputationContext}
        isRecomputing={false}
      />,
    );
    // Tooltip text appears in all 4 bailed derived chips (k, C_L,md,
    // (L/D)_max, ρ) — assert at least one match exists.
    expect(screen.getAllByText(/non-parabolic/i).length).toBeGreaterThanOrEqual(1);
  });

  it("isRecomputing=true puts stale red on the ρ value (overrides emerald)", () => {
    render(
      <PolarChipRow
        ctx={HEALTHY as unknown as ComputationContext}
        isRecomputing={true}
      />,
    );
    const rho = findRhoValueSpan(document.body, /^0\.18$/);
    expect(rho.className).toContain("text-red-400");
  });
});
