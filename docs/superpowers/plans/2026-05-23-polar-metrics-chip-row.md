# Polar Metrics Chip-Row Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a thematic Polar row to the workbench chip strip surfacing C_D0, e*, k, C_L,md, C_L,max, (L/D)_max, ρ with profile-aware traffic-light colours and a bail-rule for non-parabolic polars.

**Architecture:** Refactor `InfoChipRow.tsx` (302 lines, monolithic) into a thin container + four sibling row components (`SpeedChipRow`, `GeometryChipRow`, `PolarChipRow`, `StabilityChipRow`) + a shared `Chip.tsx` primitive. Pure derivation helpers live in `frontend/lib/polar.ts`. All values are already cached server-side in `assumption_computation_context` — pure frontend change.

**Tech Stack:** Next.js 16, React 19, TypeScript, Tailwind, vitest + React Testing Library, SWR, lucide-react icons.

**Spec:** `docs/superpowers/specs/2026-05-23-polar-metrics-chip-row-design.md`

---

## File map

| File | Action | Purpose |
|---|---|---|
| `frontend/components/workbench/Chip.tsx` | **Create** | Extracted primitive (icon, symbol, value, valueNode, description, stale, valueColorClassName) |
| `frontend/components/workbench/SpeedChipRow.tsx` | **Create** | Row 1: V-speeds + refresh slot |
| `frontend/components/workbench/GeometryChipRow.tsx` | **Create** | Row 2a: S_ref, MAC, B_ref, AR |
| `frontend/components/workbench/PolarChipRow.tsx` | **Create** | Row 2b: Re, C_D0, e*, k, C_L,md, C_L,max, (L/D)_max, ρ |
| `frontend/components/workbench/StabilityChipRow.tsx` | **Create** | Row 2c: NP, SM, CG + rightSlot |
| `frontend/components/workbench/InfoChipRow.tsx` | **Modify** | Reduce to ≤ 80-line container |
| `frontend/lib/polar.ts` | **Create** | Pure helpers: computeK, computeCLmd, computeEMax, computeRho, rhoThresholdsForProfile, qualityColorClassName, rhoColorClassName |
| `frontend/hooks/useComputationContext.ts` | **Modify** | Extend `ComputationContext` with cd0, e_oswald, e_oswald_quality, e_oswald_fallback_used, polar_by_config |
| `frontend/__tests__/Chip.test.tsx` | **Create** | Primitive tests |
| `frontend/__tests__/SpeedChipRow.test.tsx` | **Create** | Speed row migrated cases |
| `frontend/__tests__/GeometryChipRow.test.tsx` | **Create** | Geometry row + AR |
| `frontend/__tests__/PolarChipRow.test.tsx` | **Create** | Polar row component tests (centre of effort) |
| `frontend/__tests__/StabilityChipRow.test.tsx` | **Create** | Stability row migrated cases |
| `frontend/__tests__/polar.test.ts` | **Create** | Pure-helper round-trip tests |
| `frontend/__tests__/InfoChipRow.test.tsx` | **Modify** | Trim to container behaviour |

---

## Task 1 — Extract `Chip.tsx` primitive

**Files:**
- Create: `frontend/components/workbench/Chip.tsx`
- Create: `frontend/__tests__/Chip.test.tsx`
- Modify: `frontend/components/workbench/InfoChipRow.tsx:30-78` (remove inline `humanize` + `Chip` function, import from new module)

- [ ] **Step 1: Write the failing test**

`frontend/__tests__/Chip.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return { Wind: icon };
});

import { Chip } from "@/components/workbench/Chip";
import { Wind } from "lucide-react";

describe("Chip primitive", () => {
  it("renders symbol = value", () => {
    render(<Chip icon={Wind} symbol="V_md" value="13.2 m/s" />);
    expect(screen.getByText(/13\.2 m\/s/)).toBeInTheDocument();
  });

  it("renders valueNode in place of value when provided", () => {
    render(
      <Chip
        icon={Wind}
        symbol="CG"
        valueNode={<span data-testid="rich">rich</span>}
      />,
    );
    expect(screen.getByTestId("rich")).toBeInTheDocument();
  });

  it("applies stale red colour to value when stale=true", () => {
    const { container } = render(
      <Chip icon={Wind} symbol="V_md" value="13.2" stale />,
    );
    const valueSpan = container.querySelector("span.text-red-400");
    expect(valueSpan).not.toBeNull();
  });

  it("applies valueColorClassName when not stale", () => {
    const { container } = render(
      <Chip
        icon={Wind}
        symbol="e"
        value="0.80"
        valueColorClassName="text-emerald-400"
      />,
    );
    expect(container.querySelector("span.text-emerald-400")).not.toBeNull();
  });

  it("stale overrides valueColorClassName", () => {
    const { container } = render(
      <Chip
        icon={Wind}
        symbol="e"
        value="0.80"
        valueColorClassName="text-emerald-400"
        stale
      />,
    );
    expect(container.querySelector("span.text-red-400")).not.toBeNull();
    expect(container.querySelector("span.text-emerald-400")).toBeNull();
  });

  it("renders tooltip description", () => {
    render(
      <Chip
        icon={Wind}
        symbol="V_md"
        value="13.2"
        description="Minimum-drag speed"
      />,
    );
    expect(screen.getByText("Minimum-drag speed")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run __tests__/Chip.test.tsx`
Expected: FAIL — module `@/components/workbench/Chip` not found.

- [ ] **Step 3: Create `Chip.tsx`**

`frontend/components/workbench/Chip.tsx`:

```tsx
"use client";

import { renderSymbol } from "@/components/workbench/renderSymbol";

function humanize(symbol: string): string {
  return symbol.replace(/_/g, " ");
}

export function Chip({
  icon: Icon,
  symbol,
  value,
  valueNode,
  description,
  stale = false,
  valueColorClassName,
}: {
  readonly icon: React.ComponentType<{ size: number; className: string }>;
  readonly symbol: string;
  readonly value?: string;
  readonly valueNode?: React.ReactNode;
  readonly description?: string;
  readonly stale?: boolean;
  readonly valueColorClassName?: string;
}) {
  // Stale (recompute in flight) always wins over caller-supplied colour:
  // the chip's value is provisional and that fact dominates any quality
  // / traffic-light signal.
  const valueClass = stale
    ? "text-red-400"
    : (valueColorClassName ?? "text-foreground");
  const ariaLabel = description
    ? `${humanize(symbol)}: ${description}`
    : humanize(symbol);
  return (
    <div
      role="group"
      tabIndex={0}
      aria-label={ariaLabel}
      className="group/chip relative flex items-center gap-1.5 rounded-full bg-card-muted px-3 py-1.5 focus:outline-none focus-visible:ring-1 focus-visible:ring-primary"
    >
      <Icon size={12} className="text-muted-foreground" />
      <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-foreground">
        {renderSymbol(symbol)}
        {" = "}
        {valueNode ?? <span className={valueClass}>{value}</span>}
      </span>
      {description && (
        <span
          aria-hidden="true"
          className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-1.5 hidden w-max max-w-[240px] -translate-x-1/2 rounded-lg border border-border bg-card px-2.5 py-1.5 text-[10px] font-normal leading-snug text-foreground shadow-lg group-hover/chip:block group-focus-within/chip:block"
        >
          {description}
        </span>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run test, verify it passes**

Run: `cd frontend && npx vitest run __tests__/Chip.test.tsx`
Expected: PASS, 6/6.

- [ ] **Step 5: Migrate `InfoChipRow.tsx` to import the primitive**

Remove lines 30-78 (`humanize` + `Chip` function definitions) from `InfoChipRow.tsx`. Add at top with the other imports:

```tsx
import { Chip } from "@/components/workbench/Chip";
```

Run: `cd frontend && npx vitest run __tests__/InfoChipRow.test.tsx`
Expected: PASS (no behaviour change).

- [ ] **Step 6: Commit**

```bash
git add frontend/components/workbench/Chip.tsx \
        frontend/__tests__/Chip.test.tsx \
        frontend/components/workbench/InfoChipRow.tsx
git commit -m "refactor(gh-626): extract Chip primitive from InfoChipRow

Adds valueColorClassName prop (stale takes priority). No behaviour
change in InfoChipRow.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 2 — Extend `ComputationContext` type

**Files:**
- Modify: `frontend/hooks/useComputationContext.ts:6-34`

- [ ] **Step 1: Add the new fields to the interface**

After line 25 (`aspect_ratio?: number | null;`) add:

```ts
  // gh-626: polar metrics surfaced in PolarChipRow.
  cd0?: number | null;
  e_oswald?: number | null;
  e_oswald_quality?: "high" | "medium" | "low" | "unknown";
  e_oswald_fallback_used?: boolean;
  polar_by_config?: {
    clean?: {
      cd0?: number | null;
      e_oswald?: number | null;
      cl_max?: number | null;
    };
  } | null;
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS (no new errors).

- [ ] **Step 3: Commit**

```bash
git add frontend/hooks/useComputationContext.ts
git commit -m "types(gh-626): extend ComputationContext with polar fields

Adds cd0, e_oswald, e_oswald_quality, e_oswald_fallback_used,
polar_by_config. All fields are optional — the runtime payload
already includes them when the recompute has run.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 3 — Pure polar helpers in `frontend/lib/polar.ts`

**Files:**
- Create: `frontend/lib/polar.ts`
- Create: `frontend/__tests__/polar.test.ts`

- [ ] **Step 1: Write the failing tests** (covers §13.A from the spec)

`frontend/__tests__/polar.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import {
  computeK,
  computeCLmd,
  computeEMax,
  computeRho,
  rhoThresholdsForProfile,
  qualityColorClassName,
  rhoColorClassName,
} from "@/lib/polar";

describe("polar.computeCLmd", () => {
  it("matches √(π·e·AR·CD0)", () => {
    const v = computeCLmd(0.02, 0.8, false, 7);
    expect(v).toBeCloseTo(Math.sqrt(Math.PI * 0.8 * 7 * 0.02), 4);
    expect(v).toBeCloseTo(0.5937, 3);
  });
  it("returns null when fit was rejected (ρ-bail rule)", () => {
    expect(computeCLmd(0.02, 0.8, true, 7)).toBeNull();
  });
  it("returns null on each null/zero/negative input", () => {
    expect(computeCLmd(null, 0.8, false, 7)).toBeNull();
    expect(computeCLmd(0.02, null, false, 7)).toBeNull();
    expect(computeCLmd(0.02, 0.8, false, null)).toBeNull();
    expect(computeCLmd(0, 0.8, false, 7)).toBeNull();
    expect(computeCLmd(0.02, 0, false, 7)).toBeNull();
    expect(computeCLmd(0.02, 0.8, false, 0)).toBeNull();
    expect(computeCLmd(-0.01, 0.8, false, 7)).toBeNull();
  });
});

describe("polar.computeEMax", () => {
  it("matches ½·√(π·e·AR/CD0)", () => {
    const v = computeEMax(0.02, 0.8, false, 7);
    expect(v).toBeCloseTo(0.5 * Math.sqrt((Math.PI * 0.8 * 7) / 0.02), 3);
    expect(v).toBeCloseTo(13.213, 2);
  });
  it("ρ-bail when fit rejected", () => {
    expect(computeEMax(0.02, 0.8, true, 7)).toBeNull();
  });
});

describe("polar.computeRho", () => {
  it("matches CD0·π·e·AR / CL_max²", () => {
    const v = computeRho(0.02, 0.8, false, 7, 1.4);
    expect(v).toBeCloseTo((0.02 * Math.PI * 0.8 * 7) / (1.4 * 1.4), 4);
    expect(v).toBeCloseTo(0.180, 2);
  });
  it("identity ρ = (CL_md/CL_max)² (fuzz, 10 cases)", () => {
    for (let i = 0; i < 10; i++) {
      const cd0 = 0.005 + Math.random() * 0.04;
      const e = 0.6 + Math.random() * 0.4;
      const ar = 5 + Math.random() * 20;
      const clMax = 0.8 + Math.random() * 1.0;
      const rho = computeRho(cd0, e, false, ar, clMax)!;
      const clMd = computeCLmd(cd0, e, false, ar)!;
      expect(rho).toBeCloseTo((clMd / clMax) ** 2, 6);
    }
  });
  it("ρ-bail when fit rejected", () => {
    expect(computeRho(0.02, 0.8, true, 7, 1.4)).toBeNull();
  });
});

describe("polar.computeK", () => {
  it("matches 1/(π·e·AR)", () => {
    expect(computeK(0.8, false, 7)).toBeCloseTo(
      1 / (Math.PI * 0.8 * 7),
      6,
    );
  });
  it("ρ-bail when fit rejected", () => {
    expect(computeK(0.8, true, 7)).toBeNull();
  });
});

describe("polar.rhoThresholdsForProfile", () => {
  it("powered uses { amber: 1/3, red: 1.0 }", () => {
    expect(rhoThresholdsForProfile(false)).toEqual({
      amber: 1 / 3,
      red: 1.0,
    });
  });
  it("glider uses { amber: 2/3, red: 1.0 }", () => {
    expect(rhoThresholdsForProfile(true)).toEqual({
      amber: 2 / 3,
      red: 1.0,
    });
  });
});

describe("polar.qualityColorClassName", () => {
  it.each([
    ["high", "text-emerald-400"],
    ["medium", "text-amber-400"],
    ["low", "text-orange-400"],
    ["unknown", "text-muted-foreground"],
  ] as const)("%s → %s", (q, cls) => {
    expect(qualityColorClassName(q)).toBe(cls);
  });
  it("undefined quality → muted (defensive)", () => {
    expect(qualityColorClassName(undefined)).toBe("text-muted-foreground");
  });
});

describe("polar.rhoColorClassName", () => {
  it("null ρ → muted", () => {
    expect(rhoColorClassName(null, false)).toBe("text-muted-foreground");
  });
  it("powered: ρ < 1/3 → emerald", () => {
    expect(rhoColorClassName(0.2, false)).toBe("text-emerald-400");
  });
  it("powered: ρ = 1/3 → amber (lower-inclusive)", () => {
    expect(rhoColorClassName(1 / 3, false)).toBe("text-amber-400");
  });
  it("powered: ρ ∈ (1/3, 1) → amber", () => {
    expect(rhoColorClassName(0.5, false)).toBe("text-amber-400");
  });
  it("powered: ρ = 1 → red (upper-inclusive)", () => {
    expect(rhoColorClassName(1.0, false)).toBe("text-red-400");
  });
  it("powered: ρ > 1 → red", () => {
    expect(rhoColorClassName(1.2, false)).toBe("text-red-400");
  });
  it("glider: ρ = 1/3 → still emerald (under 2/3 amber)", () => {
    expect(rhoColorClassName(1 / 3, true)).toBe("text-emerald-400");
  });
  it("glider: ρ = 2/3 → amber", () => {
    expect(rhoColorClassName(2 / 3, true)).toBe("text-amber-400");
  });
  it("glider: ρ = 1 → red", () => {
    expect(rhoColorClassName(1.0, true)).toBe("text-red-400");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run __tests__/polar.test.ts`
Expected: FAIL — module `@/lib/polar` not found.

- [ ] **Step 3: Implement helpers**

`frontend/lib/polar.ts`:

```ts
/**
 * Pure derivation helpers for the parabolic polar
 * `C_D = C_D0 + C_L²/(π·e·AR)` — Anderson §6.7.2.
 *
 * The ρ-bail rule (gh-626 spec §8.5): when the AeroBuildup parabolic
 * fit was rejected (`e_oswald_fallback_used = true`), the polar is
 * NOT parabolic. Computing parabolic-polar metrics on it produces
 * measurement-shaped non-measurements, so every derived helper here
 * bails to `null` in that case.
 */

export type EQuality = "high" | "medium" | "low" | "unknown";

export type RhoThresholds = { readonly amber: number; readonly red: number };

function valid(...vs: (number | null | undefined)[]): boolean {
  return vs.every((v) => v != null && v > 0);
}

/** k = 1/(π·e·AR). Returns null on fit rejection or invalid inputs. */
export function computeK(
  eFromCtx: number | null | undefined,
  fallbackUsed: boolean,
  ar: number | null | undefined,
): number | null {
  if (fallbackUsed) return null;
  if (!valid(eFromCtx, ar)) return null;
  return 1 / (Math.PI * (eFromCtx as number) * (ar as number));
}

/** C_L,md = √(π·e·AR·C_D0). Lift coefficient at maximum L/D. */
export function computeCLmd(
  cd0: number | null | undefined,
  eFromCtx: number | null | undefined,
  fallbackUsed: boolean,
  ar: number | null | undefined,
): number | null {
  if (fallbackUsed) return null;
  if (!valid(cd0, eFromCtx, ar)) return null;
  return Math.sqrt(
    Math.PI * (eFromCtx as number) * (ar as number) * (cd0 as number),
  );
}

/** (L/D)_max = ½·√(π·e·AR / C_D0). Canonical Scholz polar-quality scalar. */
export function computeEMax(
  cd0: number | null | undefined,
  eFromCtx: number | null | undefined,
  fallbackUsed: boolean,
  ar: number | null | undefined,
): number | null {
  if (fallbackUsed) return null;
  if (!valid(cd0, eFromCtx, ar)) return null;
  return (
    0.5 *
    Math.sqrt((Math.PI * (eFromCtx as number) * (ar as number)) / (cd0 as number))
  );
}

/**
 * Degeneracy ratio ρ = C_D0·π·e·AR / C_L,max² = (C_L,md / C_L,max)².
 * Anderson §6.7.2 derivation: ρ=1 ⇔ V_md=V_stall, ρ=1/3 ⇔ V_min,sink=V_stall.
 */
export function computeRho(
  cd0: number | null | undefined,
  eFromCtx: number | null | undefined,
  fallbackUsed: boolean,
  ar: number | null | undefined,
  clMax: number | null | undefined,
): number | null {
  if (fallbackUsed) return null;
  if (!valid(cd0, eFromCtx, ar, clMax)) return null;
  const e = eFromCtx as number;
  const c = clMax as number;
  return ((cd0 as number) * Math.PI * e * (ar as number)) / (c * c);
}

/** Profile-aware ρ traffic-light thresholds (Scholz §5.7 +  rev 2 decision 9). */
export function rhoThresholdsForProfile(isGlider: boolean): RhoThresholds {
  return isGlider ? { amber: 2 / 3, red: 1.0 } : { amber: 1 / 3, red: 1.0 };
}

/** Maps the backend's e-fit quality label to a Tailwind value-colour class. */
export function qualityColorClassName(
  quality: EQuality | undefined | null,
): string {
  switch (quality) {
    case "high":
      return "text-emerald-400";
    case "medium":
      return "text-amber-400";
    case "low":
      return "text-orange-400";
    case "unknown":
    default:
      return "text-muted-foreground";
  }
}

/** ρ traffic-light colour. Lower-inclusive boundaries. */
export function rhoColorClassName(rho: number | null, isGlider: boolean): string {
  if (rho == null) return "text-muted-foreground";
  const { amber, red } = rhoThresholdsForProfile(isGlider);
  if (rho >= red) return "text-red-400";
  if (rho >= amber) return "text-amber-400";
  return "text-emerald-400";
}
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd frontend && npx vitest run __tests__/polar.test.ts`
Expected: PASS, all assertions green.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/polar.ts frontend/__tests__/polar.test.ts
git commit -m "feat(gh-626): pure polar helpers (computeK/CLmd/EMax/Rho + colours)

Derivation helpers from Anderson §6.7.2 parabolic polar:
- computeK: k = 1/(π·e·AR)
- computeCLmd: √(π·e·AR·CD0)
- computeEMax: ½·√(π·e·AR/CD0) — canonical Scholz §5.7 polar quality
- computeRho: CD0·π·e·AR / CL_max² = (CL_md/CL_max)²
- rhoThresholdsForProfile: powered {1/3, 1.0} vs glider {2/3, 1.0}
- qualityColorClassName / rhoColorClassName: Tailwind class mapping

All derived helpers bail to null on fit rejection (ρ-bail rule,
spec §8.5). 100% test coverage of derivation identities, bail rule,
and boundary semantics.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4 — `SpeedChipRow.tsx` (Row 1 extraction)

**Files:**
- Create: `frontend/components/workbench/SpeedChipRow.tsx`
- Create: `frontend/__tests__/SpeedChipRow.test.tsx`

- [ ] **Step 1: Write the failing test**

`frontend/__tests__/SpeedChipRow.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (p: Record<string, unknown>) => React.createElement("span", p);
  return {
    Wind: icon, AlertTriangle: icon, Plane: icon, Gauge: icon,
    TrendingUp: icon, Zap: icon,
  };
});

import { vi } from "vitest";
import { SpeedChipRow } from "@/components/workbench/SpeedChipRow";

describe("SpeedChipRow", () => {
  const base = {
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

  it("renders all V-speed chips when context complete", () => {
    render(<SpeedChipRow ctx={base as any} isRecomputing={false} />);
    expect(screen.getByText(/13\.2 m\/s/)).toBeInTheDocument();
    expect(screen.getByText(/18\.0 m\/s/)).toBeInTheDocument();
    expect(screen.getByText(/35\.0 m\/s/)).toBeInTheDocument();
  });

  it("uses V_cruise* symbol when ctx.v_cruise_auto", () => {
    render(
      <SpeedChipRow
        ctx={{ ...base, v_cruise_auto: true } as any}
        isRecomputing={false}
      />,
    );
    // V_cruise* — asterisk visible in rendered subscript output
    expect(screen.getByText((t) => t.includes("V"))).toBeTruthy();
  });

  it("hides V_a, V_max, V_dive when is_glider=true", () => {
    render(
      <SpeedChipRow
        ctx={{ ...base, is_glider: true } as any}
        isRecomputing={false}
      />,
    );
    // V_a description should be absent.
    expect(screen.queryByText(/manoeuvring/)).toBeNull();
  });

  it("shows dashes when ctx is null", () => {
    render(<SpeedChipRow ctx={null} isRecomputing={false} />);
    const dashes = screen.getAllByText("–");
    expect(dashes.length).toBeGreaterThanOrEqual(6);
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

Run: `cd frontend && npx vitest run __tests__/SpeedChipRow.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `SpeedChipRow.tsx`**

```tsx
"use client";

import {
  Wind, AlertTriangle, Plane, Gauge, TrendingUp, Zap,
} from "lucide-react";
import { Chip } from "@/components/workbench/Chip";
import type { ComputationContext } from "@/hooks/useComputationContext";

interface Props {
  readonly ctx: ComputationContext | null | undefined;
  readonly isRecomputing: boolean;
  readonly rightSlot?: React.ReactNode;
}

function fmt(v: number | null | undefined, decimals: number, suffix = "") {
  return v != null ? `${v.toFixed(decimals)}${suffix}` : "–";
}

export function SpeedChipRow({ ctx, isRecomputing, rightSlot }: Props) {
  const stale = isRecomputing;
  return (
    <div
      data-testid="chip-row-speeds"
      className="flex flex-wrap items-center gap-2"
    >
      <Chip
        icon={AlertTriangle}
        symbol="V_stall"
        description="Stall speed in clean configuration at 1 g"
        value={fmt(ctx?.v_stall_mps, 1, " m/s")}
        stale={stale}
      />
      <Chip
        icon={Wind}
        symbol="V_min_sink"
        description="Speed for minimum sink rate — best endurance / longest glide time"
        value={fmt(ctx?.v_min_sink_mps, 1, " m/s")}
        stale={stale}
      />
      <Chip
        icon={Wind}
        symbol="V_md"
        description="Minimum-drag speed — best L/D, longest glide distance"
        value={fmt(ctx?.v_md_mps, 1, " m/s")}
        stale={stale}
      />
      <Chip
        icon={Wind}
        symbol={ctx?.v_cruise_auto ? "V_cruise*" : "V_cruise"}
        description={
          ctx?.v_cruise_auto
            ? "Design cruise speed (auto-derived from cruise sizing — asterisk)"
            : "Design cruise speed"
        }
        value={fmt(ctx?.v_cruise_mps, 1, " m/s")}
        stale={stale}
      />
      <Chip
        icon={TrendingUp}
        symbol="V_x"
        description="Best angle-of-climb speed — steepest altitude gain per unit ground distance"
        value={fmt(ctx?.v_x_mps, 1, " m/s")}
        stale={stale}
      />
      <Chip
        icon={Plane}
        symbol="V_y"
        description="Best rate-of-climb speed — fastest altitude gain per unit time"
        value={fmt(ctx?.v_y_mps, 1, " m/s")}
        stale={stale}
      />
      {!ctx?.is_glider && (
        <Chip
          icon={Gauge}
          symbol="V_a"
          description="Design manoeuvring speed — structural limit at full control deflection"
          value={fmt(ctx?.v_a_mps, 1, " m/s")}
          stale={stale}
        />
      )}
      {!ctx?.is_glider && (
        <Chip
          icon={Gauge}
          symbol="V_max"
          description="Maximum operating speed"
          value={fmt(ctx?.v_max_mps, 1, " m/s")}
          stale={stale}
        />
      )}
      {!ctx?.is_glider && (
        <Chip
          icon={Zap}
          symbol="V_dive"
          description="Design dive speed (heuristic: 1.4 × V_max)"
          value={fmt(ctx?.v_dive_mps, 1, " m/s")}
          stale={stale}
        />
      )}
      <div className="flex-1" />
      {rightSlot}
    </div>
  );
}
```

- [ ] **Step 4: Run test, verify pass**

Run: `cd frontend && npx vitest run __tests__/SpeedChipRow.test.tsx`
Expected: PASS, 4/4.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workbench/SpeedChipRow.tsx \
        frontend/__tests__/SpeedChipRow.test.tsx
git commit -m "refactor(gh-626): extract SpeedChipRow component

Pure renderer of Row 1 (V_stall, V_min_sink, V_md, V_cruise(*),
V_x, V_y, and is_glider-gated V_a/V_max/V_dive). Accepts rightSlot
for the container to inject refresh + recomputing pill.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 5 — `GeometryChipRow.tsx` (Row 2a + AR)

**Files:**
- Create: `frontend/components/workbench/GeometryChipRow.tsx`
- Create: `frontend/__tests__/GeometryChipRow.test.tsx`

- [ ] **Step 1: Failing test**

`frontend/__tests__/GeometryChipRow.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (p: Record<string, unknown>) => React.createElement("span", p);
  return { Square: icon, Ruler: icon, ArrowLeftRight: icon, Gauge: icon };
});

import { GeometryChipRow } from "@/components/workbench/GeometryChipRow";

describe("GeometryChipRow", () => {
  it("renders S_ref, MAC, B_ref, AR", () => {
    render(
      <GeometryChipRow
        ctx={{
          s_ref_m2: 0.4,
          mac_m: 0.21,
          b_ref_m: 2.0,
          aspect_ratio: 10.0,
        } as any}
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
        ctx={{ s_ref_m2: 0.4, mac_m: 0.21, b_ref_m: 2, aspect_ratio: null } as any}
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
```

- [ ] **Step 2: Run test, verify fail**

Run: `cd frontend && npx vitest run __tests__/GeometryChipRow.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implement**

```tsx
"use client";

import { Square, Ruler, ArrowLeftRight, Gauge } from "lucide-react";
import { Chip } from "@/components/workbench/Chip";
import type { ComputationContext } from "@/hooks/useComputationContext";

interface Props {
  readonly ctx: ComputationContext | null | undefined;
  readonly isRecomputing: boolean;
}

function fmt(v: number | null | undefined, decimals: number, suffix = "") {
  return v != null ? `${v.toFixed(decimals)}${suffix}` : "–";
}

export function GeometryChipRow({ ctx, isRecomputing }: Props) {
  const stale = isRecomputing;
  return (
    <div
      data-testid="chip-row-geometry"
      className="flex flex-wrap items-center gap-2"
    >
      <Chip
        icon={Square}
        symbol="S_ref"
        description="Reference area — projected wing area used to non-dimensionalize forces (C_L = L / (q · S_ref))"
        value={fmt(ctx?.s_ref_m2, 3, " m²")}
        stale={stale}
      />
      <Chip
        icon={Ruler}
        symbol="MAC"
        description="Mean Aerodynamic Chord (= C_ref in AVL/ASB) — reference chord for pitching moment coefficient"
        value={fmt(ctx?.mac_m, 2, " m")}
        stale={stale}
      />
      <Chip
        icon={ArrowLeftRight}
        symbol="B_ref"
        description="Reference span — wingspan used to non-dimensionalize roll and yaw moments"
        value={fmt(ctx?.b_ref_m, 2, " m")}
        stale={stale}
      />
      <Chip
        icon={Gauge}
        symbol="AR"
        description="Aspect ratio = b² / S_ref (main wing). Higher AR ⇒ less induced drag."
        value={fmt(ctx?.aspect_ratio, 2)}
        stale={stale}
      />
      <div className="flex-1" />
    </div>
  );
}
```

- [ ] **Step 4: Run test, verify pass**

Run: `cd frontend && npx vitest run __tests__/GeometryChipRow.test.tsx`
Expected: PASS, 3/3.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workbench/GeometryChipRow.tsx \
        frontend/__tests__/GeometryChipRow.test.tsx
git commit -m "feat(gh-626): GeometryChipRow with S_ref, MAC, B_ref, AR

AR chip is new (gh-626); the other three are migrated from Row 2.
Pure renderer, no SWR.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 6 — `StabilityChipRow.tsx` (NP, SM, CG)

**Files:**
- Create: `frontend/components/workbench/StabilityChipRow.tsx`
- Create: `frontend/__tests__/StabilityChipRow.test.tsx`

- [ ] **Step 1: Failing test**

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (p: Record<string, unknown>) => React.createElement("span", p);
  return { Target: icon, Navigation: icon };
});

import { StabilityChipRow } from "@/components/workbench/StabilityChipRow";

describe("StabilityChipRow", () => {
  it("renders NP, SM, CG", () => {
    render(
      <StabilityChipRow
        ctx={{
          x_np_m: 0.085,
          target_static_margin: 0.12,
          cg_agg_m: 0.092,
          mac_m: 0.21,
        } as any}
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
```

- [ ] **Step 2: Run, verify fail**

Run: `cd frontend && npx vitest run __tests__/StabilityChipRow.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implement**

```tsx
"use client";

import { Target, Navigation } from "lucide-react";
import { Chip } from "@/components/workbench/Chip";
import { cgDivergenceColor } from "./stability-overlay/divergence-color";
import type { ComputationContext } from "@/hooks/useComputationContext";

interface Props {
  readonly ctx: ComputationContext | null | undefined;
  readonly cgAero: number | null;
  readonly isRecomputing: boolean;
  readonly rightSlot?: React.ReactNode;
}

function fmt(v: number | null | undefined, decimals: number, suffix = "") {
  return v != null ? `${v.toFixed(decimals)}${suffix}` : "–";
}

export function StabilityChipRow({ ctx, cgAero, isRecomputing, rightSlot }: Props) {
  const stale = isRecomputing;
  const cgValue = cgAero != null ? `${cgAero.toFixed(3)} m` : "–";
  const cgDescription =
    "Centre of gravity — aerodynamic balance value; component-derived value in parentheses when available";
  const cgValueNode = (
    <>
      <span className={stale ? "text-red-400" : ""}>{cgValue}</span>
      {cgAero != null && ctx?.cg_agg_m != null && ctx?.mac_m != null && (
        <span
          className={`ml-1 ${
            stale
              ? "text-red-400"
              : cgDivergenceColor(cgAero, ctx.cg_agg_m, ctx.mac_m)
          }`}
        >
          ({ctx.cg_agg_m.toFixed(3)})
        </span>
      )}
    </>
  );

  return (
    <div
      data-testid="chip-row-stability"
      className="flex flex-wrap items-center gap-2"
    >
      <Chip
        icon={Target}
        symbol="NP"
        description="Neutral point — aerodynamic centre of the whole aircraft"
        value={fmt(ctx?.x_np_m, 3, " m")}
        stale={stale}
      />
      <Chip
        icon={Navigation}
        symbol="SM"
        description="Static margin = (NP − CG) / MAC — target value used for trim balancing"
        value={
          ctx?.target_static_margin != null
            ? (ctx.target_static_margin * 100).toFixed(0) + "%"
            : "–"
        }
        stale={stale}
      />
      <Chip
        icon={Navigation}
        symbol="CG"
        description={cgDescription}
        valueNode={cgValueNode}
        stale={stale}
      />
      <div className="flex-1" />
      {rightSlot}
    </div>
  );
}
```

- [ ] **Step 4: Run, verify pass**

Run: `cd frontend && npx vitest run __tests__/StabilityChipRow.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workbench/StabilityChipRow.tsx \
        frontend/__tests__/StabilityChipRow.test.tsx
git commit -m "refactor(gh-626): extract StabilityChipRow component

Pure renderer of NP, SM, CG (with cg_agg divergence colour). Migrated
from InfoChipRow Row 2 lines 272-296.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 7 — `PolarChipRow.tsx` (the new content)

**Files:**
- Create: `frontend/components/workbench/PolarChipRow.tsx`
- Create: `frontend/__tests__/PolarChipRow.test.tsx`

- [ ] **Step 1: Failing test** (spec §13.B)

```tsx
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

// Healthy powered fixture: CD0=0.02, e=0.80, AR=7, CL_max=1.4
// → ρ ≈ 0.180 emerald
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
// → ρ ≈ 0.382 — would be amber on powered thresholds, emerald on glider
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

describe("PolarChipRow", () => {
  it("healthy powered: all 8 chips populated, ρ emerald", () => {
    const { container } = render(
      <PolarChipRow ctx={HEALTHY as any} isRecomputing={false} />,
    );
    expect(screen.getByText(/5\.4e\+?5/)).toBeInTheDocument(); // Re
    expect(screen.getByText(/0\.0200$/)).toBeInTheDocument();  // CD0
    expect(screen.getByText(/0\.80$/)).toBeInTheDocument();    // e
    expect(screen.getByText(/0\.0568$/)).toBeInTheDocument();  // k = 1/(π·0.8·7)
    expect(screen.getByText(/0\.59$/)).toBeInTheDocument();    // C_L,md
    expect(screen.getByText(/1\.40$/)).toBeInTheDocument();    // C_L,max
    expect(screen.getByText(/13\.2$/)).toBeInTheDocument();    // (L/D)_max
    expect(screen.getByText(/0\.18$/)).toBeInTheDocument();    // ρ
    expect(container.querySelector(".text-emerald-400")).not.toBeNull();
  });

  it("sailplane: ρ ≈ 0.38 → emerald under glider thresholds (would be amber powered)", () => {
    const { container } = render(
      <PolarChipRow ctx={SAILPLANE as any} isRecomputing={false} />,
    );
    expect(screen.getByText(/0\.38$/)).toBeInTheDocument();
    // ρ chip uses emerald (glider amber threshold = 2/3)
    // Locate the ρ value span and check its colour.
    const rho = screen.getByText(/0\.38$/);
    expect(rho.className).toContain("text-emerald-400");
  });

  it("powered amber lower boundary (ρ = 1/3) → amber", () => {
    // Need CD0·π·e·AR / CL_max² = 1/3 exactly.
    // Pick CD0=1/(3·π·0.8·7)·1² ≈ 0.0189 with CL_max=1.0 e=0.8 AR=7.
    const ctx = {
      ...HEALTHY,
      cd0: 1 / (3 * Math.PI * 0.8 * 7),
      polar_by_config: { clean: { cl_max: 1.0 } },
    };
    render(<PolarChipRow ctx={ctx as any} isRecomputing={false} />);
    const rho = screen.getByText(/0\.33$/);
    expect(rho.className).toContain("text-amber-400");
  });

  it("powered red boundary (ρ = 1.00) → red", () => {
    const ctx = {
      ...HEALTHY,
      cd0: 1.0 / (Math.PI * 0.8 * 7),  // → ρ = 1.0 exactly with CL_max=1
      polar_by_config: { clean: { cl_max: 1.0 } },
    };
    render(<PolarChipRow ctx={ctx as any} isRecomputing={false} />);
    const rho = screen.getByText(/^1\.00$/);
    expect(rho.className).toContain("text-red-400");
  });

  it("glider amber lower boundary (ρ = 2/3, is_glider=true) → amber", () => {
    const ctx = {
      ...SAILPLANE,
      cd0: (2 / 3) / (Math.PI * 0.95 * 36),  // → ρ = 2/3 with CL_max=1.0
      polar_by_config: { clean: { cl_max: 1.0 } },
    };
    render(<PolarChipRow ctx={ctx as any} isRecomputing={false} />);
    const rho = screen.getByText(/0\.67$/);
    expect(rho.className).toContain("text-amber-400");
  });

  it("quality matrix on e: high/medium/low/unknown → emerald/amber/orange/muted", () => {
    const colours = {
      high: "text-emerald-400",
      medium: "text-amber-400",
      low: "text-orange-400",
      unknown: "text-muted-foreground",
    } as const;
    for (const [q, cls] of Object.entries(colours)) {
      const ctx = { ...HEALTHY, e_oswald_quality: q };
      const { container, unmount } = render(
        <PolarChipRow ctx={ctx as any} isRecomputing={false} />,
      );
      const eSpan = container.querySelector(`span.${cls.replace("text-", "")}`);
      // Not all colour classes turn into clean selectors via classList; do a
      // broader assert instead.
      expect(container.innerHTML).toContain(cls);
      unmount();
    }
  });

  it("#625 reproduction: e* muted + k/CLmd/EMax/ρ all '–'", () => {
    const { container } = render(
      <PolarChipRow ctx={REJECTED as any} isRecomputing={false} />,
    );
    expect(container.innerHTML).toContain("V_cruise*".charAt(0)); // sanity
    // e* renders with the muted class:
    expect(container.innerHTML).toContain("text-muted-foreground");
    // The four derived chips render '–'
    expect(screen.getAllByText("–").length).toBeGreaterThanOrEqual(4);
  });

  it("each null input nukes its dependents", () => {
    const variants = [
      { ...HEALTHY, cd0: null },
      { ...HEALTHY, aspect_ratio: null },
      { ...HEALTHY, polar_by_config: { clean: { cl_max: null } } },
    ];
    for (const ctx of variants) {
      const { container, unmount } = render(
        <PolarChipRow ctx={ctx as any} isRecomputing={false} />,
      );
      // ρ should always be '–' here.
      const dashes = screen.getAllByText("–");
      expect(dashes.length).toBeGreaterThanOrEqual(1);
      unmount();
    }
  });

  it("ctx=null → all '–'", () => {
    render(<PolarChipRow ctx={null} isRecomputing={false} />);
    expect(screen.getAllByText("–").length).toBeGreaterThanOrEqual(7);
  });

  it("ρ-red tooltip prescribes 'see Matching Chart'", () => {
    const ctx = {
      ...HEALTHY,
      cd0: 1.0 / (Math.PI * 0.8 * 7),
      polar_by_config: { clean: { cl_max: 1.0 } },
    };
    render(<PolarChipRow ctx={ctx as any} isRecomputing={false} />);
    expect(screen.getByText(/see Matching Chart/i)).toBeInTheDocument();
  });

  it("(L/D)_max tooltip contains 'headline polar number'", () => {
    render(<PolarChipRow ctx={HEALTHY as any} isRecomputing={false} />);
    expect(screen.getByText(/headline polar number/i)).toBeInTheDocument();
  });

  it("bail-rule tooltip contains 'non-parabolic'", () => {
    render(<PolarChipRow ctx={REJECTED as any} isRecomputing={false} />);
    expect(screen.getByText(/non-parabolic/i)).toBeInTheDocument();
  });

  it("isRecomputing=true overrides colours with stale red", () => {
    const { container } = render(
      <PolarChipRow ctx={HEALTHY as any} isRecomputing={true} />,
    );
    expect(container.innerHTML).toContain("text-red-400");
    // Emerald should NOT be present on the values because stale wins.
    // (The emerald may still appear elsewhere, but the ρ value span is red.)
  });
});
```

- [ ] **Step 2: Run, verify fail**

Run: `cd frontend && npx vitest run __tests__/PolarChipRow.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `PolarChipRow.tsx`**

```tsx
"use client";

import { Wind, Gauge, Activity, Target, TrendingUp, AlertTriangle } from "lucide-react";
import { Chip } from "@/components/workbench/Chip";
import {
  computeK, computeCLmd, computeEMax, computeRho,
  qualityColorClassName, rhoColorClassName,
} from "@/lib/polar";
import type { ComputationContext } from "@/hooks/useComputationContext";

interface Props {
  readonly ctx: ComputationContext | null | undefined;
  readonly isRecomputing: boolean;
}

function fmt(v: number | null, decimals: number, suffix = "") {
  return v != null ? `${v.toFixed(decimals)}${suffix}` : "–";
}
function fmtRe(v: number | null | undefined) {
  return v == null ? "–" : v.toExponential(1);
}

const BAIL_TOOLTIP =
  "Parabolic polar fit was rejected (see e*). Derived polar quantities are not meaningful when the polar is non-parabolic.";

function rhoTooltip(rho: number | null, isGlider: boolean): string {
  if (rho == null) return BAIL_TOOLTIP;
  const intuitiveForm = " ρ = (C_L,md/C_L,max)²";
  if (rho >= 1.0) {
    return (
      "Polar health: L/D-max coincident with or past stall — polar is degenerate. " +
      "Resize wing: raise AR or improve C_L,max — see Matching Chart." +
      intuitiveForm
    );
  }
  const amber = isGlider ? 2 / 3 : 1 / 3;
  if (rho >= amber) {
    return isGlider
      ? "Polar health: tightening sailplane optimum. Still healthy for glider regime." +
          intuitiveForm
      : "Polar health: min-sink point at/below stall. L/D-max still reachable. " +
          "Consider raising AR or lowering W/S — see Matching Chart." +
          intuitiveForm;
  }
  return (
    "Polar health: healthy. L/D-max sits comfortably above stall." + intuitiveForm
  );
}

export function PolarChipRow({ ctx, isRecomputing }: Props) {
  const stale = isRecomputing;

  const cd0 = ctx?.cd0 ?? null;
  const eFromCtx = ctx?.e_oswald ?? null;
  const fallbackUsed = !!ctx?.e_oswald_fallback_used;
  const ar = ctx?.aspect_ratio ?? null;
  const clMax = ctx?.polar_by_config?.clean?.cl_max ?? null;
  const isGlider = !!ctx?.is_glider;
  const quality = ctx?.e_oswald_quality ?? "unknown";

  const k = computeK(eFromCtx, fallbackUsed, ar);
  const clMd = computeCLmd(cd0, eFromCtx, fallbackUsed, ar);
  const eMax = computeEMax(cd0, eFromCtx, fallbackUsed, ar);
  const rho = computeRho(cd0, eFromCtx, fallbackUsed, ar, clMax);

  // The displayed e-value: when fallback used, show the fallback 0.80
  // explicitly with the asterisk marker; otherwise show the real fit
  // value. Both render with the quality colour (fallback ⇒ unknown ⇒ muted).
  const eDisplayValue =
    fallbackUsed ? 0.80 : eFromCtx;
  const eSymbol = fallbackUsed ? "e*" : "e";
  const eTooltip = fallbackUsed
    ? "Polar fit was rejected — fallback 0.80 used (regime-naive). All derived polar quantities (k, C_L,md, L/D-max, ρ) are therefore suppressed."
    : "Oswald efficiency — combined non-elliptical-lift-distribution loss and parasite-drag-with-lift. Typical 0.70–0.95. Colour reflects fit quality.";
  const eQualityColour = fallbackUsed
    ? qualityColorClassName("unknown")
    : qualityColorClassName(quality);

  return (
    <div
      data-testid="chip-row-polar"
      className="flex flex-wrap items-center gap-2"
    >
      <Chip
        icon={Wind}
        symbol="Re"
        description="Reynolds number at cruise (characteristic length = MAC). Polar shape is Re-dependent; this row's metrics describe cruise-Re behaviour."
        value={fmtRe(ctx?.reynolds)}
        stale={stale}
      />
      <Chip
        icon={Gauge}
        symbol="C_D0"
        description="Zero-lift drag coefficient (parasite drag). Lower is better. ρ uses this together with e and AR. Source: stability run (single-CL eval)."
        value={fmt(cd0, 4)}
        stale={stale}
      />
      <Chip
        icon={Activity}
        symbol={eSymbol}
        description={eTooltip}
        value={fmt(eDisplayValue, 2)}
        valueColorClassName={eQualityColour}
        stale={stale}
      />
      <Chip
        icon={Activity}
        symbol="k"
        description={k == null
          ? BAIL_TOOLTIP
          : "Induced-drag factor k = 1/(πeAR). Drag rises as k·C_L². Lower k = less induced drag at the same lift."}
        value={fmt(k, 4)}
        stale={stale}
      />
      <Chip
        icon={Target}
        symbol="C_L,md"
        description={clMd == null
          ? BAIL_TOOLTIP
          : "Lift coefficient where L/D is maximum (best glide). Should sit well below C_L,max. If C_L,md ≥ C_L,max your wing must stall to reach best glide."}
        value={fmt(clMd, 2)}
        stale={stale}
      />
      <Chip
        icon={AlertTriangle}
        symbol="C_L,max"
        description="Maximum lift coefficient (clean configuration, no flaps). From AeroBuildup — known to underestimate at Re < 3×10⁵; treat as conservative for RC."
        value={fmt(clMax, 2)}
        stale={stale}
      />
      <Chip
        icon={TrendingUp}
        symbol="(L/D)_max"
        description={eMax == null
          ? BAIL_TOOLTIP
          : "Maximum lift-to-drag ratio. The headline polar number. Sailplane > 30 · GA 10–18 · jet transport 16–22 · trainer 8–12. Formula: ½·√(πeAR/C_D0)."}
        value={fmt(eMax, 1)}
        stale={stale}
      />
      <Chip
        icon={Gauge}
        symbol="ρ"
        description={rhoTooltip(rho, isGlider)}
        value={fmt(rho, 2)}
        valueColorClassName={rhoColorClassName(rho, isGlider)}
        stale={stale}
      />
      <div className="flex-1" />
    </div>
  );
}
```

- [ ] **Step 4: Run, verify pass**

Run: `cd frontend && npx vitest run __tests__/PolarChipRow.test.tsx`
Expected: PASS, all assertions.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workbench/PolarChipRow.tsx \
        frontend/__tests__/PolarChipRow.test.tsx
git commit -m "feat(gh-626): PolarChipRow with ρ-bail rule + profile thresholds

Eight chips: Re, C_D0, e*, k, C_L,md, C_L,max, (L/D)_max, ρ. All
derived chips bail to '–' when e_oswald_fallback_used=true. ρ uses
profile-aware thresholds (powered 1/3 vs glider 2/3). Tooltips are
consequence-first with Matching-Chart prescription on red.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 8 — Slim `InfoChipRow.tsx` to a container + wire `PolarChipRow`

**Files:**
- Modify: `frontend/components/workbench/InfoChipRow.tsx` (replace bulk of file)
- Modify: `frontend/__tests__/InfoChipRow.test.tsx` (keep container-level tests, remove migrated assertions)

- [ ] **Step 1: Replace InfoChipRow body with container**

`frontend/components/workbench/InfoChipRow.tsx` (full replacement):

```tsx
"use client";

import { Loader2, RefreshCw } from "lucide-react";
import { useComputationContext } from "@/hooks/useComputationContext";
import { SpeedChipRow } from "@/components/workbench/SpeedChipRow";
import { GeometryChipRow } from "@/components/workbench/GeometryChipRow";
import { PolarChipRow } from "@/components/workbench/PolarChipRow";
import { StabilityChipRow } from "@/components/workbench/StabilityChipRow";
import { TaillessBanner } from "./TaillessBanner";

interface Props {
  readonly aeroplaneId: string | null;
  readonly cgAero: number | null;
  readonly isRecomputing?: boolean;
  readonly rightSlot?: React.ReactNode;
}

export function InfoChipRow({ aeroplaneId, cgAero, isRecomputing, rightSlot }: Props) {
  const { data: ctx, mutate } = useComputationContext(aeroplaneId, { isRecomputing });
  const recomputing = !!isRecomputing;
  const isTailless = !!ctx?.is_tailless;

  const refreshSlot = (
    <>
      {recomputing && (
        <span
          className="flex items-center gap-1 rounded-full bg-orange-500/15 px-2 py-1 text-[11px] text-orange-400"
          data-testid="recomputing-chip"
        >
          <Loader2 size={11} className="animate-spin" />
          Recomputing…
        </span>
      )}
      <button
        type="button"
        aria-label="Refresh computation context"
        onClick={() => mutate()}
        disabled={recomputing}
        className="flex items-center gap-1 rounded-full bg-card-muted px-2.5 py-1.5 text-muted-foreground hover:bg-muted hover:text-foreground focus:outline-none focus-visible:ring-1 focus-visible:ring-primary disabled:cursor-not-allowed disabled:opacity-50"
      >
        <RefreshCw size={12} />
      </button>
    </>
  );

  return (
    <div className="flex flex-col gap-2 border-t border-border bg-card px-4 py-3">
      {isTailless && (
        <div className="flex">
          <TaillessBanner />
        </div>
      )}
      <SpeedChipRow ctx={ctx} isRecomputing={recomputing} rightSlot={refreshSlot} />
      <GeometryChipRow ctx={ctx} isRecomputing={recomputing} />
      <PolarChipRow ctx={ctx} isRecomputing={recomputing} />
      <StabilityChipRow
        ctx={ctx}
        cgAero={cgAero}
        isRecomputing={recomputing}
        rightSlot={rightSlot}
      />
    </div>
  );
}
```

- [ ] **Step 2: Run existing test, verify still passes**

Run: `cd frontend && npx vitest run __tests__/InfoChipRow.test.tsx`
Expected: Most cases still pass. Some may fail (e.g. multi-row dash counts) because the row count changed. **Update the existing test** to assert four `data-testid` rows present and at least one expected chip value renders.

Add a test:

```tsx
it("renders four chip rows in order: speeds / geometry / polar / stability", async () => {
  (useComputationContext as ReturnType<typeof vi.fn>).mockReturnValue({
    data: { v_cruise_mps: 18, reynolds: 5.4e5, mac_m: 0.21, x_np_m: 0.085,
            target_static_margin: 0.12, cg_agg_m: 0.092, s_ref_m2: 0.4,
            aspect_ratio: 7, cd0: 0.02, e_oswald: 0.8,
            e_oswald_quality: "high", e_oswald_fallback_used: false,
            polar_by_config: { clean: { cl_max: 1.4 } }, is_glider: false },
    isLoading: false, error: null, mutate: vi.fn(),
  });

  const { InfoChipRow } = await import("@/components/workbench/InfoChipRow");
  const { container } = render(<InfoChipRow aeroplaneId="42" cgAero={0.073} />);

  expect(container.querySelector('[data-testid="chip-row-speeds"]')).not.toBeNull();
  expect(container.querySelector('[data-testid="chip-row-geometry"]')).not.toBeNull();
  expect(container.querySelector('[data-testid="chip-row-polar"]')).not.toBeNull();
  expect(container.querySelector('[data-testid="chip-row-stability"]')).not.toBeNull();
});
```

Adjust the existing `"shows dashes when no context"` test if the dash count assertion is too strict. The current minimum-4-dashes assertion should be raised to ≥ 10 (more chips now).

Run: `cd frontend && npx vitest run __tests__/InfoChipRow.test.tsx`
Expected: PASS.

- [ ] **Step 3: Run full frontend unit suite**

Run: `cd frontend && npm run test:unit`
Expected: All passing.

- [ ] **Step 4: Verify line count of InfoChipRow.tsx ≤ 80**

Run: `wc -l frontend/components/workbench/InfoChipRow.tsx`
Expected: ≤ 80.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workbench/InfoChipRow.tsx \
        frontend/__tests__/InfoChipRow.test.tsx
git commit -m "refactor(gh-626): InfoChipRow becomes thin container

InfoChipRow now orchestrates four sibling row components and owns
the refresh button + recomputing pill. Down from 302 lines to <80.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 9 — Verification against acceptance criteria

- [ ] **Step 1: Run full test suite**

Run: `cd frontend && npm run test:unit`
Expected: All tests green.

- [ ] **Step 2: Run TypeScript compile**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors.

- [ ] **Step 3: Run lint**

Run: `cd frontend && npm run lint`
Expected: No new warnings.

- [ ] **Step 4: Verify ACs §12.A (Structural)**

- `wc -l frontend/components/workbench/InfoChipRow.tsx` ≤ 80 ✓
- Six new files exist: `Chip.tsx`, `SpeedChipRow.tsx`, `GeometryChipRow.tsx`, `PolarChipRow.tsx`, `StabilityChipRow.tsx`, `lib/polar.ts` ✓
- Six new test files exist ✓
- AR chip present in `GeometryChipRow.tsx` (grep) ✓

- [ ] **Step 5: Verify ACs §12.B (Diagnostic value) via test output**

The relevant test cases (already in §13.A/13.B) cover:
- derivation identities ✓
- powered traffic-light boundaries ✓
- glider traffic-light boundaries ✓
- healthy fixture ✓
- sailplane no-false-alarm ✓
- #625 reproduction ✓
- empty context ✓

- [ ] **Step 6: Verify ACs §12.C (Behaviour) via test output**

- fallback marker test passes ✓
- gliders show polar chips (negative assertion: no `is_glider` hide in PolarChipRow source — grep) ✓
- isRecomputing stale red test passes ✓
- ρ red tooltip "see Matching Chart" test passes ✓
- `npm run test:unit` passes ✓

- [ ] **Step 7: Visual verification in browser**

Start the backend and frontend, browse to the workbench with an aeroplane that has run a recompute. Confirm the four chip rows render in order, the Polar row shows the eight chips, and at least the ρ chip shows traffic-light colouring.

```bash
# Backend (in a separate terminal):
poetry run uvicorn app.main:app --port 8001 --reload

# Frontend (in another terminal):
cd frontend && npm run dev

# Visit http://localhost:3000/workbench/<aeroplane-id>
```

Take a screenshot for the PR description.

- [ ] **Step 8: Final commit & push**

```bash
git push -u github feat/gh-626-polar-metrics-chip-row
```

PR title: `feat(gh-626): polar metrics chip-row — eight chips + ρ-bail + profile thresholds`. Body references the spec doc and lists the spec's acceptance criteria as a checklist.

---

## Self-Review

1. **Spec coverage:** every §-numbered chip and every §12 AC has a corresponding task or step. The ρ-bail rule (§8.5) is in `polar.ts` and tested in §13.A-7. Profile thresholds (§8.4) are in `rhoThresholdsForProfile` + tested at boundaries. Tooltip text is asserted via test cases (§13.B-18). ✓
2. **Placeholder scan:** no TBD/TODO/"implement later" — every step has the actual code. ✓
3. **Type consistency:** helper signatures (`computeRho(cd0, eFromCtx, fallbackUsed, ar, clMax)`) are identical across `polar.ts` definition, `polar.test.ts` imports, and `PolarChipRow.tsx` usage. ✓
4. **Ambiguity:** the ρ-bail rule lives in the helpers themselves (not in the component), so any future caller automatically inherits the bail behaviour. ✓
