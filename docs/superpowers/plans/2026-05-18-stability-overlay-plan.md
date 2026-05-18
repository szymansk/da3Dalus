# Stability Overlay (Plotly) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render NP, CG (SOLL design-target + IST component-aggregate), Static-Margin band, and SOLL↔IST delta-link as Plotly `scatter3d` traces composited into the workbench's existing Plotly-based `WingOutlineViewer` via a small composable overlay registry. Frontend-only — no backend changes.

**Architecture:** `WingOutlineViewer` receives one new optional prop `extraTraces?: PlotlyData[]`. A `useOverlayRegistry` hook lets independent overlay components publish their own traces and own toggle. `StabilityOverlay` is the first such overlay; future overlays (mass distribution, axes, propeller disc, …) compose into the same registry without further changes to `WingOutlineViewer`.

**Tech Stack:** Next.js 16 App Router, React 19, Plotly.js via `plotly.js-gl3d-dist-min` (already a project dep), SWR for data, Tailwind CSS (dark theme, accent `#FF8400`), Vitest for unit tests.

**Issue:** #569
**Spec (synced local copy):** `docs/superpowers/specs/2026-05-18-construction-view-stability-overlay-design.md`
**Branch:** `feat/gh-569-stability-overlay`
**Out of scope:** Backend changes, modifying `CadViewer.tsx` (different surface), removing the Stability tab (sub-issue #567), fixing `cg_agg_m` footer bug (#568), mounting in airfoil-preview page.

---

## File Structure

**New files:**

| File | Responsibility |
|---|---|
| `frontend/components/workbench/stability-overlay/divergence-color.ts` | Shared `cgDivergenceColor(soll, ist, mac)` helper extracted from `InfoChipRow.tsx`. |
| `frontend/components/workbench/stability-overlay/buildStabilityTraces.ts` | Pure function: `(ctx) => PlotlyData[]`. No React, no Plotly imports — only the data shape. |
| `frontend/components/workbench/stability-overlay/StabilityOverlay.tsx` | React component: `useComputationContext`, toggle state, registry call, toggle button UI. |
| `frontend/hooks/useOverlayRegistry.ts` | Hook providing `{ traces, register(key) }`. Tiny — backed by `useReducer` over a `Record<string, PlotlyData[]>`. |
| `frontend/__tests__/stability-overlay/divergence-color.test.ts` | Tests for color helper. |
| `frontend/__tests__/stability-overlay/buildStabilityTraces.test.ts` | Tests for trace builder (all data states). |
| `frontend/__tests__/stability-overlay/StabilityOverlay.test.tsx` | Tests for overlay component (toggle, persistence, registry call). |
| `frontend/__tests__/useOverlayRegistry.test.ts` | Tests for registry hook. |

**Modified files:**

| File | Change |
|---|---|
| `frontend/components/workbench/WingOutlineViewer.tsx` | Add one optional prop `extraTraces?: PlotlyData[]`. Append it to `traces` before `Plotly.newPlot`. Extend the `useEffect` deps array to include `extraTraces`. Three-line additive change. Existing trace-building logic untouched. |
| `frontend/app/workbench/page.tsx` (or whichever component mounts `WingOutlineViewer` in the workbench) | Use `useOverlayRegistry`; pass `traces` to `WingOutlineViewer.extraTraces`; mount `<StabilityOverlay register={...} />`. |
| `frontend/components/workbench/InfoChipRow.tsx` | Replace local `cgDivergenceColor` (lines ~75-80) with import from the new shared module. |

**Docs (committed in Task 0):**

- `docs/superpowers/specs/2026-05-18-construction-view-stability-overlay-design.md` (already drafted)
- `docs/superpowers/plans/2026-05-18-stability-overlay-plan.md` (this file)

---

## Dependency Graph

```
T0 (spec+plan commit)
T1 (extract divergence-color) ─┐
T2 (WingOutlineViewer extraTraces) ──┐
T3 (useOverlayRegistry) ─────────────┤
T4 (buildStabilityTraces pure fn) ───┤
                                     │
                                     └──> T5 (StabilityOverlay component + toggle + persistence)
                                                            │
                                                            └──> T6 (wire into workbench page)
                                                                                │
                                                                                └──> T7 (manual browser verification)
```

T1, T2, T3, T4 are pairwise independent and can be parallelised.

---

## Conventions Applied to Every Task

- **TDD:** Each implementation task is RED → GREEN → REFACTOR.
- **Test runner:** `cd frontend && npm run test:unit -- <pattern>` for Vitest.
- **Commit cadence:** One commit per task, conventional message with `feat(gh-569):` / `refactor(gh-569):` / `test(gh-569):` / `docs(gh-569):` prefix.
- **No backend touches.**
- **Vercel best practices** (`/vercel-react-best-practices`, `/vercel-composition-patterns`): hooks at top level, exhaustive deps, memo where measurable, compose rather than extend.

---

## Task 0: Commit spec and plan to the feature branch

**Files:**
- `docs/superpowers/specs/2026-05-18-construction-view-stability-overlay-design.md` (already exists in this worktree)
- `docs/superpowers/plans/2026-05-18-stability-overlay-plan.md` (this file)

- [ ] **Step 1: Verify both files present**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-569-stability-overlay
ls -la docs/superpowers/specs/2026-05-18-construction-view-stability-overlay-design.md
ls -la docs/superpowers/plans/2026-05-18-stability-overlay-plan.md
```

Expected: both files exist.

- [ ] **Step 2: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-569-stability-overlay
git add docs/superpowers/specs/2026-05-18-construction-view-stability-overlay-design.md \
        docs/superpowers/plans/2026-05-18-stability-overlay-plan.md
git commit -m "docs(gh-569): add spec and implementation plan for Plotly stability overlay"
```

- [ ] **Step 3: Push the branch**

```bash
git push -u github feat/gh-569-stability-overlay
```

---

## Task 1: Extract `cgDivergenceColor` to a shared module

Same as before — independent of the Plotly switch. The helper is reused by `StabilityOverlay` to colour the CG-IST marker.

**Files:**
- Create: `frontend/components/workbench/stability-overlay/divergence-color.ts`
- Create: `frontend/__tests__/stability-overlay/divergence-color.test.ts`
- Modify: `frontend/components/workbench/InfoChipRow.tsx` (replace local def with import)

- [ ] **Step 1: Read the current implementation to capture exact thresholds**

```bash
grep -A 12 "function cgDivergenceColor" /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-569-stability-overlay/frontend/components/workbench/InfoChipRow.tsx
```

Capture the **exact** threshold values and class names used. The example tests below assume:

- `|Δ|/MAC ≤ 1 %` → green
- `|Δ|/MAC ≤ 3 %` → yellow
- `|Δ|/MAC > 3 %` → red

If the real thresholds differ, adjust both the test expectations AND the implementation to the real values.

- [ ] **Step 2: Write the failing test**

Create `frontend/__tests__/stability-overlay/divergence-color.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { cgDivergenceColor } from "../../components/workbench/stability-overlay/divergence-color";

describe("cgDivergenceColor", () => {
  it("returns the green class for |Δ| ≤ 1% MAC", () => {
    expect(cgDivergenceColor(2.440, 2.445, 1.0)).toMatch(/green/);
  });

  it("returns the yellow class for 1% < |Δ| ≤ 3% MAC", () => {
    expect(cgDivergenceColor(2.440, 2.460, 1.0)).toMatch(/yellow/);
  });

  it("returns the red class for |Δ| > 3% MAC", () => {
    expect(cgDivergenceColor(2.440, 2.500, 1.0)).toMatch(/red/);
  });

  it("is symmetric in IST above vs below SOLL", () => {
    expect(cgDivergenceColor(2.440, 2.420, 1.0)).toEqual(
      cgDivergenceColor(2.440, 2.460, 1.0),
    );
  });

  it("normalises by MAC", () => {
    expect(cgDivergenceColor(2.440, 2.450, 2.0)).toMatch(/green/);
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-569-stability-overlay/frontend
npm run test:unit -- divergence-color
```

Expected: FAIL with module-not-found.

- [ ] **Step 4: Implement**

Create `frontend/components/workbench/stability-overlay/divergence-color.ts`:

```typescript
/**
 * Color class for CG divergence indicator (SOLL vs IST).
 *
 * Returns a Tailwind text-color class based on the absolute delta
 * between design CG and aggregated CG, normalised by MAC.
 *
 * Thresholds (match InfoChipRow legacy behaviour — verify in source):
 *   |Δ|/MAC ≤ 1%  → green
 *   |Δ|/MAC ≤ 3%  → yellow
 *   |Δ|/MAC > 3%  → red
 */
export function cgDivergenceColor(
  cgSoll: number,
  cgIst: number,
  mac: number,
): string {
  const deltaPct = (Math.abs(cgIst - cgSoll) / mac) * 100;
  if (deltaPct <= 1) return "text-green-400";
  if (deltaPct <= 3) return "text-yellow-400";
  return "text-red-400";
}
```

(Adjust the thresholds / class strings to match the source captured in Step 1.)

- [ ] **Step 5: Run tests to verify they pass**

```bash
npm run test:unit -- divergence-color
```

Expected: PASS.

- [ ] **Step 6: Refactor `InfoChipRow.tsx`**

Add the import near the top:

```typescript
import { cgDivergenceColor } from "./stability-overlay/divergence-color";
```

Delete the local function definition (lines around 75-80).

- [ ] **Step 7: Verify `InfoChipRow` tests still pass**

```bash
npm run test:unit -- InfoChipRow
```

Expected: PASS unchanged.

- [ ] **Step 8: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-569-stability-overlay
git add frontend/components/workbench/stability-overlay/divergence-color.ts \
        frontend/__tests__/stability-overlay/divergence-color.test.ts \
        frontend/components/workbench/InfoChipRow.tsx
git commit -m "refactor(gh-569): extract cgDivergenceColor to shared module"
```

---

## Task 2: Add `extraTraces` prop to `WingOutlineViewer`

**Files:**
- Modify: `frontend/components/workbench/WingOutlineViewer.tsx`
- (No new test file — exercised via component-integration; the trace concat is one line.)

- [ ] **Step 1: Read the current props interface and the useEffect that calls `Plotly.newPlot`**

```bash
sed -n '8,30p' /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-569-stability-overlay/frontend/components/workbench/WingOutlineViewer.tsx
sed -n '855,912p' /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-569-stability-overlay/frontend/components/workbench/WingOutlineViewer.tsx
```

Note the existing useEffect dep array (line 910) and the empty-scene placeholder (lines 870-877).

- [ ] **Step 2: Extend the props interface**

Add to `WingOutlineViewerProps`:

```typescript
interface WingOutlineViewerProps {
  // ... existing props ...
  /** Additional Plotly traces appended after wing/fuselage traces.
   *  Used by overlay components (gh-569: stability) via useOverlayRegistry. */
  extraTraces?: PlotlyData[];
}
```

Where `PlotlyData` is the existing alias used in the file (search for `PlotlyData` to confirm the import or re-export).

- [ ] **Step 3: Use the prop**

In the component signature:

```typescript
export function WingOutlineViewer({
  wings, fuselages, visibleWings, visibleFuselages,
  selectedXsecIndex, selectedWing, selectedFuselage, selectedFuselageXsecIndex,
  extraTraces,
}: Readonly<WingOutlineViewerProps>) {
```

After the existing trace collection and before the empty-scene placeholder check (around line 868):

```typescript
const traces = await collectAllTraces({ ... });

// gh-569: append overlay traces from useOverlayRegistry
if (extraTraces && extraTraces.length > 0) {
  traces.push(...extraTraces);
}

// Guard: empty scene placeholder (existing logic, line 869-877)
if (traces.length === 0) {
  traces.push({ ... });
}
```

Add `extraTraces` to the `useEffect` deps array (line 910):

```typescript
}, [
  wings, fuselages, visibleWings, visibleFuselages,
  selectedXsecIndex, selectedWing, selectedFuselage, selectedFuselageXsecIndex,
  showQuarterChord,
  extraTraces,
]);
```

- [ ] **Step 4: Run existing tests to verify no regression**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-569-stability-overlay/frontend
npm run test:unit -- WingOutlineViewer
```

Expected: existing tests pass unchanged (the prop is optional and defaults to undefined).

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workbench/WingOutlineViewer.tsx
git commit -m "feat(gh-569): add additive extraTraces prop to WingOutlineViewer

Enables overlay components (gh-569 stability, future expansions)
to publish Plotly traces into the construction preview without
modifying the viewer's trace-building logic."
```

---

## Task 3: `useOverlayRegistry` hook

**Files:**
- Create: `frontend/hooks/useOverlayRegistry.ts`
- Create: `frontend/__tests__/useOverlayRegistry.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/__tests__/useOverlayRegistry.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useOverlayRegistry } from "../hooks/useOverlayRegistry";

describe("useOverlayRegistry", () => {
  it("starts with an empty traces array", () => {
    const { result } = renderHook(() => useOverlayRegistry());
    expect(result.current.traces).toEqual([]);
  });

  it("returns a stable register(key) callback per key", () => {
    const { result } = renderHook(() => useOverlayRegistry());
    const cb1 = result.current.register("stability");
    const cb2 = result.current.register("stability");
    expect(cb1).toBe(cb2);
  });

  it("accumulates traces registered under different keys", () => {
    const { result } = renderHook(() => useOverlayRegistry());

    act(() => {
      result.current.register("a")([{ type: "scatter3d", x: [1], y: [0], z: [0] }]);
      result.current.register("b")([{ type: "scatter3d", x: [2], y: [0], z: [0] }]);
    });

    expect(result.current.traces).toHaveLength(2);
    expect(result.current.traces[0].x).toEqual([1]);
    expect(result.current.traces[1].x).toEqual([2]);
  });

  it("replaces traces for an existing key on re-register", () => {
    const { result } = renderHook(() => useOverlayRegistry());
    const register = result.current.register("stability");

    act(() => { register([{ type: "scatter3d", x: [1], y: [0], z: [0] }]); });
    act(() => { register([{ type: "scatter3d", x: [99], y: [0], z: [0] }]); });

    expect(result.current.traces).toHaveLength(1);
    expect(result.current.traces[0].x).toEqual([99]);
  });

  it("removes the key when registering an empty array", () => {
    const { result } = renderHook(() => useOverlayRegistry());
    const register = result.current.register("stability");
    act(() => { register([{ type: "scatter3d", x: [1], y: [0], z: [0] }]); });
    act(() => { register([]); });
    expect(result.current.traces).toEqual([]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-569-stability-overlay/frontend
npm run test:unit -- useOverlayRegistry
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

Create `frontend/hooks/useOverlayRegistry.ts`:

```typescript
"use client";

import { useCallback, useMemo, useRef, useState } from "react";

// Use a loose type — the registry doesn't need to know the Plotly schema.
// Components publish whatever Plotly accepts in its `data` array.
export type PlotlyTrace = Record<string, unknown>;

export interface UseOverlayRegistryReturn {
  /** Flat list of all registered traces, in insertion order by key. */
  traces: PlotlyTrace[];
  /** Returns a stable setter that publishes (or clears) the traces for `key`. */
  register: (key: string) => (next: PlotlyTrace[]) => void;
}

/**
 * Composable overlay registry for the workbench Plotly preview.
 *
 * Each overlay component (e.g. StabilityOverlay) holds a stable
 * `register(key)` setter; calling it with a non-empty array publishes
 * those traces into the registry. Calling with an empty array removes
 * the key entirely.
 *
 * The flat `traces` array is fed to <WingOutlineViewer extraTraces={...}/>.
 *
 * Order of traces follows the order in which keys were first registered.
 */
export function useOverlayRegistry(): UseOverlayRegistryReturn {
  const [byKey, setByKey] = useState<Record<string, PlotlyTrace[]>>({});
  // Insertion order tracker — stable across renders.
  const orderRef = useRef<string[]>([]);
  // Stable register callbacks, memoised per key.
  const cbRef = useRef<Record<string, (next: PlotlyTrace[]) => void>>({});

  const register = useCallback((key: string) => {
    if (!cbRef.current[key]) {
      cbRef.current[key] = (next) => {
        setByKey((prev) => {
          if (next.length === 0) {
            // remove
            const { [key]: _gone, ...rest } = prev;
            orderRef.current = orderRef.current.filter((k) => k !== key);
            return rest;
          }
          if (!orderRef.current.includes(key)) {
            orderRef.current = [...orderRef.current, key];
          }
          return { ...prev, [key]: next };
        });
      };
    }
    return cbRef.current[key];
  }, []);

  const traces = useMemo<PlotlyTrace[]>(
    () => orderRef.current.flatMap((k) => byKey[k] ?? []),
    [byKey],
  );

  return { traces, register };
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm run test:unit -- useOverlayRegistry
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/hooks/useOverlayRegistry.ts \
        frontend/__tests__/useOverlayRegistry.test.ts
git commit -m "feat(gh-569): add useOverlayRegistry hook for composable Plotly overlays"
```

---

## Task 4: `buildStabilityTraces` pure function

**Files:**
- Create: `frontend/components/workbench/stability-overlay/buildStabilityTraces.ts`
- Create: `frontend/__tests__/stability-overlay/buildStabilityTraces.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/__tests__/stability-overlay/buildStabilityTraces.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { buildStabilityTraces } from "../../components/workbench/stability-overlay/buildStabilityTraces";

const FULL = {
  x_np_m: 2.607,
  mac_m: 1.387,
  cg_agg_m: 2.510,
  target_static_margin: 0.12,
};

describe("buildStabilityTraces", () => {
  describe("complete data", () => {
    const traces = buildStabilityTraces(FULL);

    it("returns 5 traces: NP, CG SOLL, CG IST, SM band, delta link", () => {
      expect(traces).toHaveLength(5);
    });

    it("places NP at x_np_m * 1000 (mm) along the x axis", () => {
      const np = traces.find((t) => t.name === "NP")!;
      expect((np.x as number[])[0]).toBeCloseTo(2607, 0);
    });

    it("places CG SOLL at (x_np_m − target_sm · mac_m) * 1000", () => {
      const cgSoll = traces.find((t) => t.name === "CG (design)")!;
      const expected = (2.607 - 0.12 * 1.387) * 1000;
      expect((cgSoll.x as number[])[0]).toBeCloseTo(expected, 0);
    });

    it("places CG IST at cg_agg_m * 1000", () => {
      const cgIst = traces.find((t) => t.name === "CG (actual)")!;
      expect((cgIst.x as number[])[0]).toBeCloseTo(2510, 0);
    });

    it("uses orange #FF8400 for CG SOLL marker", () => {
      const cgSoll = traces.find((t) => t.name === "CG (design)")!;
      const marker = cgSoll.marker as { color?: string };
      expect(marker.color?.toUpperCase()).toBe("#FF8400");
    });

    it("renders SM band as a line between SOLL CG and NP", () => {
      const band = traces.find((t) => t.name === "Static Margin")!;
      expect((band.x as number[]).length).toBe(2);
      expect(band.mode).toBe("lines");
    });

    it("renders delta link only when |Δ|/MAC > 1%", () => {
      // FULL: |2.510 - (2.607-0.12*1.387)| / 1.387 ≈ ?
      // soll = 2.607 - 0.16644 = 2.44056
      // delta = |2.510 - 2.44056| / 1.387 = 0.0500 ≈ 5.0% → link present
      const link = traces.find((t) => t.name === "Δ SOLL→IST");
      expect(link).toBeDefined();
    });
  });

  describe("graceful degradation", () => {
    it("omits CG IST trace when cg_agg_m is null", () => {
      const traces = buildStabilityTraces({ ...FULL, cg_agg_m: null });
      expect(traces.find((t) => t.name === "CG (actual)")).toBeUndefined();
      expect(traces.find((t) => t.name === "Δ SOLL→IST")).toBeUndefined();
    });

    it("returns empty array when x_np_m is null", () => {
      const traces = buildStabilityTraces({ ...FULL, x_np_m: null });
      expect(traces).toEqual([]);
    });

    it("omits SM band when target_static_margin is null", () => {
      const traces = buildStabilityTraces({ ...FULL, target_static_margin: null });
      expect(traces.find((t) => t.name === "Static Margin")).toBeUndefined();
      expect(traces.find((t) => t.name === "CG (design)")).toBeUndefined();
      // IST still rendered if cg_agg_m present
      expect(traces.find((t) => t.name === "CG (actual)")).toBeDefined();
      expect(traces.find((t) => t.name === "NP")).toBeDefined();
    });

    it("does not render delta link when |Δ|/MAC ≤ 1%", () => {
      const cgIstAtSoll = 2.607 - 0.12 * 1.387; // exactly at SOLL
      const traces = buildStabilityTraces({ ...FULL, cg_agg_m: cgIstAtSoll });
      expect(traces.find((t) => t.name === "Δ SOLL→IST")).toBeUndefined();
    });
  });

  describe("hovertext", () => {
    const traces = buildStabilityTraces(FULL);

    it("NP trace hovertext includes the NP value in metres", () => {
      const np = traces.find((t) => t.name === "NP")!;
      expect(String(np.hovertext)).toContain("2.607");
    });

    it("CG IST trace hovertext includes the Δ to target", () => {
      const ist = traces.find((t) => t.name === "CG (actual)")!;
      expect(String(ist.hovertext)).toMatch(/Δ|delta/i);
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
npm run test:unit -- buildStabilityTraces
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

Create `frontend/components/workbench/stability-overlay/buildStabilityTraces.ts`:

```typescript
import { cgDivergenceColor } from "./divergence-color";

/** Loose Plotly trace shape — keeps this file Plotly-import-free. */
export type PlotlyTrace = Record<string, unknown>;

export interface StabilityCtx {
  x_np_m: number | null;
  mac_m: number | null;
  cg_agg_m: number | null;
  target_static_margin: number | null;
}

const M_TO_MM = 1000;
const DELTA_LINK_THRESHOLD_PCT = 1; // |Δ|/MAC > 1% renders the link

const COLOR_NP = "#3b82f6";        // tailwind blue-500
const COLOR_CG_SOLL = "#FF8400";   // project theme accent
const COLOR_CG_IST_OUTLINE = "#9ca3af"; // tailwind gray-400 (overridden by divergence in 'line' colour)
const COLOR_SM_BAND = "#a3e635";   // tailwind lime-400

const SIZE_NP_PX = 8;
const SIZE_CG_SOLL_PX = 12;
const SIZE_CG_IST_PX = 6;

/** Map a Tailwind text-color class to a hex string for Plotly. */
function tailwindToHex(cls: string): string {
  if (cls.includes("green")) return "#4ade80";
  if (cls.includes("yellow")) return "#facc15";
  if (cls.includes("red")) return "#f87171";
  return "#9ca3af";
}

/**
 * Build the Plotly scatter3d traces for the stability overlay.
 *
 * Returns an empty array when there is no NP — the overlay cannot
 * usefully render anything without it.
 *
 * Coordinates: input is metres (backend); output is millimetres
 * (matches WingOutlineViewer's coordinate frame).
 */
export function buildStabilityTraces(ctx: StabilityCtx): PlotlyTrace[] {
  if (ctx.x_np_m == null) return [];

  const traces: PlotlyTrace[] = [];
  const xNpMm = ctx.x_np_m * M_TO_MM;
  const hasMac = ctx.mac_m != null && ctx.mac_m > 0;
  const hasSoll = hasMac && ctx.target_static_margin != null;
  const xSollM = hasSoll ? ctx.x_np_m - (ctx.target_static_margin as number) * (ctx.mac_m as number) : null;
  const xSollMm = xSollM != null ? xSollM * M_TO_MM : null;
  const xIstMm = ctx.cg_agg_m != null ? ctx.cg_agg_m * M_TO_MM : null;

  // NP marker
  traces.push({
    type: "scatter3d",
    mode: "markers",
    name: "NP",
    x: [xNpMm], y: [0], z: [0],
    marker: { size: SIZE_NP_PX, color: COLOR_NP, symbol: "circle" },
    hovertext: `Neutral Point<br>x = ${ctx.x_np_m.toFixed(3)} m${hasMac ? `<br>MAC = ${(ctx.mac_m as number).toFixed(2)} m` : ""}`,
    hoverinfo: "text",
    showlegend: false,
  });

  // CG SOLL marker (design target)
  if (hasSoll && xSollMm != null) {
    traces.push({
      type: "scatter3d",
      mode: "markers",
      name: "CG (design)",
      x: [xSollMm], y: [0], z: [0],
      marker: { size: SIZE_CG_SOLL_PX, color: COLOR_CG_SOLL, symbol: "circle" },
      hovertext: `CG (design target)<br>x = ${(xSollM as number).toFixed(3)} m<br>target SM = ${((ctx.target_static_margin as number) * 100).toFixed(1)} % MAC`,
      hoverinfo: "text",
      showlegend: false,
    });
  }

  // SM band (line between SOLL CG and NP)
  if (hasSoll && xSollMm != null) {
    traces.push({
      type: "scatter3d",
      mode: "lines",
      name: "Static Margin",
      x: [xSollMm, xNpMm], y: [0, 0], z: [0, 0],
      line: { color: COLOR_SM_BAND, width: 4 },
      hovertext: `Target Static Margin = ${((ctx.target_static_margin as number) * 100).toFixed(1)} % MAC`,
      hoverinfo: "text",
      showlegend: false,
    });
  }

  // CG IST marker (component aggregate)
  if (xIstMm != null) {
    const istColor = hasSoll && hasMac
      ? tailwindToHex(cgDivergenceColor(xSollM as number, ctx.cg_agg_m as number, ctx.mac_m as number))
      : COLOR_CG_IST_OUTLINE;
    const resultingSmPct = hasMac
      ? ((ctx.x_np_m - (ctx.cg_agg_m as number)) / (ctx.mac_m as number)) * 100
      : null;
    const deltaPct = hasSoll && hasMac
      ? (((ctx.cg_agg_m as number) - (xSollM as number)) / (ctx.mac_m as number)) * 100
      : null;
    const lines = [`CG (component aggregate)`, `x = ${(ctx.cg_agg_m as number).toFixed(3)} m`];
    if (resultingSmPct != null) lines.push(`resulting SM = ${resultingSmPct.toFixed(1)} % MAC`);
    if (deltaPct != null) lines.push(`Δ to target = ${deltaPct >= 0 ? "+" : ""}${deltaPct.toFixed(1)} % MAC`);
    traces.push({
      type: "scatter3d",
      mode: "markers",
      name: "CG (actual)",
      x: [xIstMm], y: [0], z: [0],
      marker: {
        size: SIZE_CG_IST_PX,
        color: istColor,
        symbol: "circle-open",
        line: { color: istColor, width: 2 },
        opacity: 0.85,
      },
      hovertext: lines.join("<br>"),
      hoverinfo: "text",
      showlegend: false,
    });

    // Delta link — only when SOLL exists and |Δ|/MAC > threshold
    if (hasSoll && xSollMm != null && deltaPct != null && Math.abs(deltaPct) > DELTA_LINK_THRESHOLD_PCT) {
      traces.push({
        type: "scatter3d",
        mode: "lines",
        name: "Δ SOLL→IST",
        x: [xSollMm, xIstMm], y: [0, 0], z: [0, 0],
        line: { color: istColor, width: 2, dash: "dash" },
        hoverinfo: "skip",
        showlegend: false,
      });
    }
  }

  return traces;
}
```

- [ ] **Step 4: Run tests**

```bash
npm run test:unit -- buildStabilityTraces
```

Expected: all 11 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workbench/stability-overlay/buildStabilityTraces.ts \
        frontend/__tests__/stability-overlay/buildStabilityTraces.test.ts
git commit -m "feat(gh-569): add buildStabilityTraces pure function (Plotly traces)"
```

---

## Task 5: `StabilityOverlay` component + toggle + persistence

**Files:**
- Create: `frontend/components/workbench/stability-overlay/StabilityOverlay.tsx`
- Create: `frontend/__tests__/stability-overlay/StabilityOverlay.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/__tests__/stability-overlay/StabilityOverlay.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

vi.mock("@/hooks/useComputationContext", () => ({
  useComputationContext: vi.fn(),
}));

import { useComputationContext } from "@/hooks/useComputationContext";
import { StabilityOverlay } from "../../components/workbench/stability-overlay/StabilityOverlay";

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
  beforeEach(() => { localStorage.clear(); });

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

  it("clears its registered traces on unmount", () => {
    withCtx({ x_np_m: 2.607, mac_m: 1.387, cg_agg_m: 2.510, target_static_margin: 0.12 });
    const register = vi.fn();
    const { unmount } = render(<StabilityOverlay aeroplaneId="a" register={register} />);
    unmount();
    // Last call should be the cleanup with empty array
    const lastCall = register.mock.calls[register.mock.calls.length - 1][0];
    expect(lastCall).toEqual([]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
npm run test:unit -- StabilityOverlay
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

Create `frontend/components/workbench/stability-overlay/StabilityOverlay.tsx`:

```typescript
"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useComputationContext } from "@/hooks/useComputationContext";
import { buildStabilityTraces, type PlotlyTrace } from "./buildStabilityTraces";

const STORAGE_KEY = "stabilityOverlayEnabled";

interface Props {
  aeroplaneId: string | null;
  /** Stable setter from useOverlayRegistry — pass register('stability'). */
  register: (next: PlotlyTrace[]) => void;
}

/**
 * Self-contained overlay component that publishes Plotly traces for the
 * stability visualisation (NP, CG SOLL, CG IST, SM band, delta link)
 * into the parent overlay registry, and renders its own toggle button.
 *
 * Mount inside the workbench preview's overlay bar. Composes alongside
 * <WingOutlineViewer extraTraces={registry.traces} />.
 */
export function StabilityOverlay({ aeroplaneId, register }: Readonly<Props>) {
  const { data: ctx } = useComputationContext(aeroplaneId);

  const [enabled, setEnabled] = useState<boolean>(() => {
    if (typeof window === "undefined") return true;
    return localStorage.getItem(STORAGE_KEY) !== "false";
  });

  const toggle = useCallback(() => {
    setEnabled((prev) => {
      const next = !prev;
      if (typeof window !== "undefined") {
        localStorage.setItem(STORAGE_KEY, String(next));
      }
      return next;
    });
  }, []);

  const traces = useMemo<PlotlyTrace[]>(() => {
    if (!enabled || !ctx) return [];
    return buildStabilityTraces({
      x_np_m: ctx.x_np_m,
      mac_m: ctx.mac_m,
      cg_agg_m: ctx.cg_agg_m,
      target_static_margin: ctx.target_static_margin,
    });
  }, [enabled, ctx]);

  useEffect(() => {
    register(traces);
    return () => { register([]); };
  }, [register, traces]);

  const hasData = ctx?.x_np_m != null;

  return (
    <button
      onClick={toggle}
      disabled={!hasData}
      title={hasData ? "Toggle stability markers" : "No aero data — run analysis first"}
      className={`rounded-lg border px-2 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[10px] backdrop-blur-sm ${
        enabled && hasData
          ? "border-primary bg-primary/20 text-primary"
          : "border-border bg-card/80 text-muted-foreground hover:text-foreground"
      } disabled:opacity-50`}
    >
      Stability
    </button>
  );
}
```

- [ ] **Step 4: Run tests**

```bash
npm run test:unit -- StabilityOverlay
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workbench/stability-overlay/StabilityOverlay.tsx \
        frontend/__tests__/stability-overlay/StabilityOverlay.test.tsx
git commit -m "feat(gh-569): add StabilityOverlay component with toggle and persistence"
```

---

## Task 6: Wire into the workbench page

**Files:**
- Identify the workbench page that mounts `WingOutlineViewer` — likely `frontend/app/workbench/page.tsx`, but possibly via an intermediate panel.
- Modify the identified file.

- [ ] **Step 1: Locate the mount point**

```bash
grep -rln "WingOutlineViewer" /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-569-stability-overlay/frontend/app /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-569-stability-overlay/frontend/components --include="*.tsx"
```

Identify the workbench-only mount (NOT the airfoil-preview page). Verify it has access to `aeroplaneId`.

- [ ] **Step 2: Modify the page/panel**

Add the registry and overlay alongside the viewer:

```typescript
import { useOverlayRegistry } from "@/hooks/useOverlayRegistry";
import { StabilityOverlay } from "@/components/workbench/stability-overlay/StabilityOverlay";

// ...inside the component:
const { traces: overlayTraces, register } = useOverlayRegistry();
const stabilityRegister = register("stability");

// In the render tree, where WingOutlineViewer is mounted:
<div className="relative h-full w-full">
  <WingOutlineViewer
    wings={wings}
    fuselages={fuselages}
    visibleWings={visibleWings}
    visibleFuselages={visibleFuselages}
    selectedXsecIndex={selectedXsecIndex}
    selectedWing={selectedWing}
    selectedFuselage={selectedFuselage}
    selectedFuselageXsecIndex={selectedFuselageXsecIndex}
    extraTraces={overlayTraces}
  />
  {/* Overlay toolbar — augments the existing bottom-right bar in WingOutlineViewer */}
  <div className="absolute bottom-3 right-3 z-30 flex gap-1" style={{ pointerEvents: "auto" }}>
    <StabilityOverlay aeroplaneId={aeroplaneId} register={stabilityRegister} />
    {/* Future overlays mount here */}
  </div>
</div>
```

**Important:** Place the overlay toolbar in a sibling absolute container so it appears alongside (or replaces) the `WingOutlineViewer`'s own toggle bar. Confirm there is no z-index or layout conflict with the existing `¼ Chord` button.

If the existing `¼ Chord` button is also still desired, an alternative is to relocate the new toggle to a different corner (e.g. `bottom-3 left-3`). Pick whatever matches the visual hierarchy after a quick browser check.

- [ ] **Step 3: Verify no regression in existing workbench tests**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-569-stability-overlay/frontend
npm run test:unit
```

Expected: full suite passes (new tests + existing tests).

- [ ] **Step 4: Commit**

```bash
git add frontend/app/workbench/page.tsx   # or whichever file was modified
git commit -m "feat(gh-569): mount StabilityOverlay in workbench construction preview"
```

---

## Task 7: Manual browser verification against issue #569 acceptance criteria

**Purpose:** Validate the feature in a real browser against every checkbox in issue #569.

- [ ] **Step 1: Install frontend dependencies in the worktree (first time only)**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-569-stability-overlay/frontend
npm install
```

- [ ] **Step 2: Start the backend and frontend**

```bash
# Terminal 1 (backend):
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-569-stability-overlay
poetry install
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2 (frontend):
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-569-stability-overlay/frontend
npm run dev
```

- [ ] **Step 3: Walk through the issue #569 acceptance criteria**

Open the workbench in a browser. Select an aeroplane with computed `x_np_m`. Verify each checkbox:

- [ ] NP marker (blue) at correct longitudinal position.
- [ ] CG SOLL marker (orange `#FF8400`) at `x_np_m − target_sm · mac_m`.
- [ ] CG IST marker (outline-styled) at `cg_agg_m` (when present); colour green/yellow/red per divergence.
- [ ] SM band between SOLL CG and NP.
- [ ] SOLL↔IST link (dashed) when `|Δ|/MAC > 1 %`.
- [ ] Hovertext shows the per-marker breakdown.
- [ ] Update one of (NP, target SM, cg_agg) and confirm markers move; camera stays.
- [ ] Graceful degradation: try an aircraft with `cg_agg_m == null` — only NP + SOLL + SM band shown.
- [ ] Graceful degradation: try an aircraft with no aero analysis (no NP) — toggle disabled, no markers.
- [ ] Toggle on/off works; preference persists across page reload.
- [ ] **Not mounted in airfoil-preview page** — navigate to `/workbench/airfoil-preview` and verify no Stability toggle is present.
- [ ] No console errors during mount, update, unmount.
- [ ] Verify the existing `¼ Chord` toggle still works (no visual or functional regression).

- [ ] **Step 4: Document the verification result**

Append to this plan:

```markdown
## Appendix A: Manual Verification (T7)

Date: YYYY-MM-DD
Tester: <name>
Result: [PASS | FAIL with notes]

Notes / deviations from acceptance criteria:
- ...
```

- [ ] **Step 5: Final commit**

```bash
git add docs/superpowers/plans/2026-05-18-stability-overlay-plan.md
git commit -m "docs(gh-569): record manual browser verification result"
```

---

## Self-Review Checklist

**Spec coverage** — every acceptance criterion in issue #569 mapped to a task:

| Acceptance criterion (from #569) | Task |
|---|---|
| `useOverlayRegistry` with `{traces, register(key)}` + unit tests | T3 |
| `WingOutlineViewer.extraTraces` additive prop; existing tests pass; deps array extended | T2 |
| `StabilityOverlay` component built; renders its toggle only | T5 |
| NP marker (blue) at `x_np_m * 1000` mm | T4, T5 |
| CG SOLL marker (orange `#FF8400`, larger) at `(x_np_m − target_sm · mac_m) * 1000` | T4, T5 |
| CG IST marker outline-styled; colour via `cgDivergenceColor()` | T1, T4, T5 |
| SM band line trace between SOLL CG and NP | T4 |
| Delta link (dashed) when `|Δ|/MAC > 1 %` | T4 |
| Native Plotly hovertext per marker | T4 |
| Traces update on ctx change; camera preserved | T4, T5, T6 (existing camera logic) |
| Graceful degradation across 4 data states | T4, T5 |
| Toggle in overlay bar; localStorage persistence | T5 |
| Mounted only in workbench page (NOT airfoil-preview) | T6 |
| Unit tests for registry, builder, color, overlay states | T1, T3, T4, T5 |
| Manual browser verification | T7 |

**Placeholder scan** — no "TBD" / "TODO" / "implement later". ✓

**Type consistency** — `PlotlyTrace`/`PlotlyData` aliases consistent across T2/T3/T4/T5; `StabilityCtx` shape (`x_np_m`, `mac_m`, `cg_agg_m`, `target_static_margin`) consistent across T4/T5; `register(key) → (next: PlotlyTrace[]) => void` consistent across T3/T5/T6. ✓

**Out-of-scope discipline** — no tasks touch backend, no tasks delete the Stability tab, no tasks fix #568, no mounting in airfoil-preview page. ✓
