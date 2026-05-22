# Polar metrics in the Workbench Chip-Row — design

**Date:** 2026-05-23 (rev 2)
**Status:** Draft (pending user review)
**Type:** Frontend feature
**GitHub issue:** #626
**Reviewers (rev 1):**
- `aerodynamics-expert` (Anderson §6.7.2) — *"Approve with minor changes"*; flagged 2 correctness items + 2 missing-physics items + minors.
- `aircraft-design-scholz` (Scholz §5.7 / Sadraey §4) — *"Revise and re-review"*; flagged missing canonical figure of merit, weak design utility, profile-naive thresholds, weak ACs.

Rev 2 addresses all 15 findings from those two reviews.

## 1 · Motivation

The Mission Tab investigation on 2026-05-22 (GitHub #625) showed that the
workbench provides no quick way to tell whether an aircraft's polar is
healthy or degenerate. The four governing scalars — `C_D0`, `e_oswald`,
`AR`, `C_L,max` — are computed and cached in
`assumption_computation_context` but never surfaced in the chip strip.
Two downstream symptoms expose the gap:

1. The Mission radar `glide` and `climb` axes come back missing on
   aircraft whose parabolic polar fit was rejected by
   `_fit_parabolic_polar` (`assumption_compute_service.py:924-1032`).
2. The chip-row V-speeds report physically impossible relationships
   (`V_min,sink < V_stall`, `V_md = V_stall`) — those are downstream of
   the same polar problem but the cause is invisible.

The canonical Scholz/Sadraey figure of merit for polar quality is
`(L/D)_max`. The canonical Anderson §6.7.2 derivation shows the
stall-margin of the L/D optimum collapses to a single dimensionless
ratio. This feature surfaces both.

## 2 · Goal

Surface a Scholz/Sadraey-grade polar summary in the workbench chip strip
so the user can read polar health at a glance:

- the **canonical figure of merit** `(L/D)_max`,
- the **operating CL margin** via the pair `(C_L,md, C_L,max)`,
- the **induced-drag factor** `k = 1/(πeAR)`,
- a **degeneracy ratio** `ρ` with **profile-aware** traffic-light
  thresholds and an actionable tooltip that points at the Matching
  Chart.

## 3 · The ρ derivation (self-contained)

From Anderson §6.7.2 for a parabolic polar `C_D = C_D0 + C_L² / (π·e·AR)`:

- Maximum L/D occurs at **`C_L,md = √(π·e·AR · C_D0)`** (induced drag
  equals parasite drag — Anderson §6.7.2). At this CL,
  `(L/D)_max = ½·√(π·e·AR / C_D0)`.
- Minimum power required (minimum sink rate for a steady glide) occurs
  at **`C_L,mp = √3 · C_L,md`** (Anderson §6.7.4).

Define the dimensionless ratio

> **ρ ≡ C_D0 · π·e·AR / C_L,max² = (C_L,md / C_L,max)²**

Then:

- `ρ = 1` ⇔ `C_L,md = C_L,max` ⇔ `V_md = V_stall` (L/D-max coincident
  with stall).
- `ρ = 1/3` ⇔ `C_L,mp = C_L,max` ⇔ `V_min,sink = V_stall`.

The form `ρ = (C_L,md / C_L,max)²` is the intuitive one — the
squared ratio of the L/D-max CL to the stall CL. ρ = 0.25 means
"L/D-max is at half the stall CL — comfortable margin."

ρ is evaluated at the cached **cruise Reynolds number**. Off-design
Re (climb, landing approach) may differ; for low-Reynolds RC the polar
shape can change appreciably between operating points. The ρ tooltip
states this explicitly.

## 4 · Scope

### In scope

A new thematic **Polar** row with **eight chips**:

```
Re   C_D0   e*   k   C_L,md   C_L,max   (L/D)_max   ρ
```

Plus:

- Refactor `InfoChipRow.tsx` into a thin container + four sibling row
  components (Speed / Geometry / Polar / Stability) + a shared `Chip`
  primitive.
- Pure derivation helpers exported for testing: `computeK`,
  `computeCLmd`, `computeEMax`, `computeRho`,
  `rhoThresholdsForProfile`.
- Profile-aware ρ thresholds (powered vs glider) using `ctx.is_glider`.
- All derived quantities bail out to `—` when the parabolic fit was
  rejected (`e_oswald_fallback_used = true`) — the polar is
  non-parabolic and derived quantities are no longer meaningful.
- Tooltips that lead with the *consequence* and end with the formula.
- Tests for derivation identities, profile-aware thresholds, sailplane
  no-false-alarm case, #625 reproduction case.

### Out of scope (separate follow-ups)

- **`C_L,cruise`** — needs the aircraft mass; depends on #625 Bug B fix
  (`mass_kg` not currently in `assumption_computation_context`). After
  #625 lands, adding this chip is trivial.
- **Per-configuration `C_L,max`** chips for takeoff / landing.
- **Bug C from #625** — clamping `V_md` / `V_min,sink` against `V_stall`.
- **Mission-profile-aware thresholds beyond `is_glider`** (separate
  bands for RC trainer / aerobatic / transport).
- **Hobbyist "verb mode"** (`ρ: healthy / marginal / degenerate`).
- **Matching-chart anchor / route** — the ρ tooltip *text* refers the
  user to the Matching Chart; clicking the chip does not yet navigate.
- **Color-blind alternative** to the traffic light.
- **Regime-specific `e_oswald` fallback** (the 0.80 default is
  jet-transport-naive).
- **Backend changes.**

## 5 · Architecture

```
frontend/components/workbench/
  Chip.tsx                ← extracted primitive
  SpeedChipRow.tsx        ← Row 1 (no behaviour change)
  GeometryChipRow.tsx     ← Row 2a: S_ref, MAC, B_ref, AR    [AR is new]
  PolarChipRow.tsx        ← Row 2b: Re, C_D0, e*, k, C_L,md, C_L,max,
                                    (L/D)_max, ρ              [new]
  StabilityChipRow.tsx    ← Row 2c (no behaviour change)
  InfoChipRow.tsx         ← container ≤ 80 lines

frontend/lib/
  polar.ts                ← pure helpers (computeK / computeCLmd /
                            computeEMax / computeRho /
                            rhoThresholdsForProfile)

frontend/__tests__/
  Chip.test.tsx
  SpeedChipRow.test.tsx
  GeometryChipRow.test.tsx
  PolarChipRow.test.tsx               ← centre of test effort
  StabilityChipRow.test.tsx
  InfoChipRow.test.tsx
  polar.test.ts                       ← pure-helper round-trip tests
```

Each row component is a pure renderer with props
`{ ctx: ComputationContext | null, isRecomputing: boolean }`. The
container owns SWR, refresh button, recomputing pill.

## 6 · Data flow

```
GET /aeroplanes/{id}/assumptions/computation-context
        │
        ▼
useComputationContext(aeroplaneId)
        │   (TypeScript interface extended — see §7)
        ▼
InfoChipRow (container)
        │
        ├─ SpeedChipRow      (ctx, isRecomputing)
        ├─ GeometryChipRow   (ctx, isRecomputing)
        ├─ PolarChipRow      (ctx, isRecomputing)
        └─ StabilityChipRow  (ctx, isRecomputing, cgAggregation…)
```

## 7 · TypeScript interface changes

`frontend/hooks/useComputationContext.ts` — extend `ComputationContext`:

```ts
interface ComputationContext {
  // ... existing keys unchanged ...

  cd0: number | null;
  e_oswald: number | null;
  e_oswald_quality: "high" | "medium" | "low" | "unknown";
  e_oswald_fallback_used: boolean;
  is_glider: boolean;          // already in the runtime payload
  polar_by_config: {
    clean: {
      cd0: number | null;
      e_oswald: number | null;
      cl_max: number | null;
    };
  } | null;
}
```

## 8 · PolarChipRow — details

### 8.1 Chips

| # | Chip | Source | Format | Notes |
|---|---|---|---|---|
| 1 | `Re` | `ctx.reynolds` | `toExponential(1)` | At cruise (`MAC × V_cruise × ρ/μ`) |
| 2 | `C_D0` | `ctx.cd0` | `.toFixed(4)` | Stability-run value (single-CL) |
| 3 | `e` / `e*` | `ctx.e_oswald` or fallback `0.80` | `.toFixed(2)` | `*` when `e_oswald_fallback_used`; quality colour from `e_oswald_quality` (§8.3) |
| 4 | `k` | `computeK(e, AR)` | `.toFixed(4)` | `—` under ρ-bail rule (§8.5) |
| 5 | `C_L,md` | `computeCLmd(cd0, e, AR)` | `.toFixed(2)` | `—` under ρ-bail rule |
| 6 | `C_L,max` | `ctx.polar_by_config?.clean?.cl_max` | `.toFixed(2)` | Clean configuration only (tooltip §9) |
| 7 | `(L/D)_max` | `computeEMax(cd0, e, AR)` | `.toFixed(1)` | `—` under ρ-bail rule; **Scholz §5.7 canonical figure** |
| 8 | `ρ` | `computeRho(cd0, e, AR, cl_max, fallbackUsed)` | `.toFixed(2)` | `—` under ρ-bail rule; profile-aware traffic-light colour (§8.4) |

### 8.2 Helpers (pure TS, exported)

```ts
export function computeK(
  eFromCtx: number | null, fallbackUsed: boolean, ar: number | null,
): number | null {
  if (fallbackUsed) return null;   // ρ-bail rule
  if (eFromCtx == null || ar == null || eFromCtx <= 0 || ar <= 0) {
    return null;
  }
  return 1 / (Math.PI * eFromCtx * ar);
}

export function computeCLmd(
  cd0: number | null, eFromCtx: number | null,
  fallbackUsed: boolean, ar: number | null,
): number | null {
  if (fallbackUsed) return null;   // ρ-bail rule
  if (cd0 == null || eFromCtx == null || ar == null) return null;
  if (cd0 <= 0 || eFromCtx <= 0 || ar <= 0) return null;
  return Math.sqrt(Math.PI * eFromCtx * ar * cd0);
}

export function computeEMax(
  cd0: number | null, eFromCtx: number | null,
  fallbackUsed: boolean, ar: number | null,
): number | null {
  if (fallbackUsed) return null;   // ρ-bail rule
  if (cd0 == null || eFromCtx == null || ar == null) return null;
  if (cd0 <= 0 || eFromCtx <= 0 || ar <= 0) return null;
  return 0.5 * Math.sqrt((Math.PI * eFromCtx * ar) / cd0);
}

export function computeRho(
  cd0: number | null, eFromCtx: number | null,
  fallbackUsed: boolean, ar: number | null,
  clMax: number | null,
): number | null {
  if (fallbackUsed) return null;   // ρ-bail rule
  if (cd0 == null || eFromCtx == null || ar == null || clMax == null) {
    return null;
  }
  if (cd0 <= 0 || eFromCtx <= 0 || ar <= 0 || clMax <= 0) return null;
  return (cd0 * Math.PI * eFromCtx * ar) / (clMax * clMax);
}

export type RhoThresholds = { amber: number; red: number };

export function rhoThresholdsForProfile(isGlider: boolean): RhoThresholds {
  // Per Scholz/Sadraey: sailplanes intentionally operate near
  // V_min,sink ≈ V_stall (ρ ≈ 1/3 is normal). Shift amber up.
  // Red boundary stays at 1.0 (V_md = V_stall is bad for any aircraft).
  return isGlider ? { amber: 2 / 3, red: 1.0 } : { amber: 1 / 3, red: 1.0 };
}
```

### 8.3 Quality colour mapping (applied to `e` value only)

| `e_oswald_quality` | Tailwind class |
|---|---|
| `high` (R² > 0.99) | `text-emerald-400` |
| `medium` (0.95 ≤ R² ≤ 0.99) | `text-amber-400` |
| `low` (R² < 0.95) | `text-orange-400` |
| `unknown` — **always when `e_oswald_fallback_used`** | `text-muted-foreground` |

When `e_oswald_fallback_used === true`, quality is necessarily `unknown`
and the `e*` value renders muted. Tests assert this combination
explicitly.

### 8.4 ρ traffic light (profile-aware)

Powered (`is_glider === false`):

| Range | Tailwind class |
|---|---|
| `ρ < 1/3` | `text-emerald-400` |
| `1/3 ≤ ρ < 1` | `text-amber-400` |
| `ρ ≥ 1` | `text-red-400` |

Glider (`is_glider === true`):

| Range | Tailwind class |
|---|---|
| `ρ < 2/3` | `text-emerald-400` |
| `2/3 ≤ ρ < 1` | `text-amber-400` |
| `ρ ≥ 1` | `text-red-400` |

Boundaries are **lower-inclusive** in both bands — tested at
`ρ = 1/3`, `ρ = 2/3`, `ρ = 1.00`.

### 8.5 The ρ-bail rule (all derived quantities)

When `e_oswald_fallback_used === true`, the parabolic OLS fit
(`_fit_parabolic_polar`, `assumption_compute_service.py:924-1032`) was
rejected for substantive physical reasons (laminar-bubble drag dip,
`e` outside (0.4, 1.0], `cd0` deviation > 20 % from the stability run,
non-monotonic `dCD/d(CL²)`, etc.). Every one of these signals that the
polar **is not parabolic**.

Computing a "parabolic-polar diagnostic" on a non-parabolic polar
produces a number that *looks* like a measurement but is actually
"what the metric would be *if* the polar were parabolic with the
literature-average e = 0.80, which we established it isn't."

The rule, applied uniformly to **k, C_L,md, (L/D)_max, ρ**:

> If `e_oswald_fallback_used === true`, all four derived chips render
> `—` with a tooltip explaining the polar is not parabolic.

Raw chips (`Re`, `C_D0`, `e*`, `C_L,max`) remain visible. The `e*`
asterisk + muted colour communicates "we know this polar isn't
parabolic; the four derived quantities have therefore been suppressed."

### 8.6 Chip primitive — new prop

Extracted `Chip` keeps every existing prop (`icon`, `symbol`,
`value | valueNode`, `description`, `stale`). One new optional prop:

```ts
valueColorClassName?: string;
```

Applied to the value span only; `stale = true` (recompute red) takes
priority.

## 9 · Tooltips (consequence-first)

All tooltips lead with the consequence/meaning a designer cares about,
then optionally include the formula on the same line.

| Symbol | Tooltip |
|---|---|
| `Re` | *"Reynolds number at cruise (characteristic length = MAC). Polar shape is Re-dependent; this row's metrics describe cruise-Re behaviour."* |
| `C_D0` | *"Zero-lift drag coefficient (parasite drag). Lower is better. ρ uses this together with e and AR. Source: stability run (single-CL eval)."* |
| `e` | *"Oswald efficiency — combined non-elliptical-lift-distribution loss and parasite-drag-with-lift. Typical 0.70–0.95. Colour reflects fit quality."* |
| `e*` | *"Polar fit was rejected — fallback 0.80 used (regime-naive). All derived polar quantities (k, C_L,md, L/D-max, ρ) are therefore suppressed."* |
| `k` | *"Induced-drag factor k = 1/(πeAR). Drag rises as k·C_L². Lower k = less induced drag at the same lift."* |
| `C_L,md` | *"Lift coefficient where L/D is maximum (best glide). Should sit well below C_L,max. If C_L,md ≥ C_L,max your wing must stall to reach best glide."* |
| `C_L,max` | *"Maximum lift coefficient (clean configuration, no flaps). From AeroBuildup — known to underestimate at Re < 3×10⁵; treat as conservative for RC."* |
| `(L/D)_max` | *"Maximum lift-to-drag ratio. The headline polar number. Sailplane > 30 · GA 10–18 · jet transport 16–22 · trainer 8–12. Formula: ½·√(πeAR/C_D0)."* |
| `ρ` (emerald) | *"Polar health: healthy. L/D-max sits comfortably above stall. ρ = (C_L,md/C_L,max)² ≤ threshold."* |
| `ρ` (amber, powered) | *"Polar health: min-sink point at/below stall. L/D-max still reachable. Consider raising AR or lowering W/S — see Matching Chart. ρ = (C_L,md/C_L,max)²."* |
| `ρ` (amber, glider) | *"Polar health: tightening sailplane optimum. Still healthy for glider regime. ρ = (C_L,md/C_L,max)²."* |
| `ρ` (red) | *"Polar health: L/D-max coincident with or past stall — polar is degenerate. Resize wing: raise AR or improve C_L,max — see Matching Chart. ρ = (C_L,md/C_L,max)²."* |
| Four derived chips when bail-rule fires | *"Parabolic polar fit was rejected (see e*). Derived polar quantities are not meaningful when the polar is non-parabolic."* |

## 10 · Edge cases

| Case | Behaviour |
|---|---|
| `ctx === null` (no recompute) | All chips show `—`; refresh button stays active |
| Polar fit rejected (`e_oswald_fallback_used = true`) | `e*=0.80` muted; **k, C_L,md, (L/D)_max, ρ all = `—`** with shared bail-rule tooltip |
| `cd0 = null` | `C_D0=—`; all four derived = `—` |
| `cl_max = null` (no clean polar) | `C_L,max=—`; `C_L,md` and `(L/D)_max` still computable; `ρ = —` |
| `aspect_ratio = null` | `AR=—` in Geometry row; `k, C_L,md, (L/D)_max, ρ` all = `—` in Polar row |
| `is_glider === true` | All chips visible; ρ uses `{ amber: 2/3, red: 1.0 }` threshold set |
| `isRecomputing === true` | Stale red on all chip values overrides quality and traffic-light colours |

## 11 · Implementation order (TDD)

1. Extract `Chip.tsx` primitive (move existing inner function verbatim;
   add `valueColorClassName`). `Chip.test.tsx` — RED → GREEN.
2. Extract `SpeedChipRow.tsx`; migrate relevant tests. Verify.
3. Extract `GeometryChipRow.tsx` (existing chips first, **without**
   AR). Verify.
4. Extract `StabilityChipRow.tsx`. Verify.
5. Extend `ComputationContext` type with new fields.
6. Add `AR` chip to `GeometryChipRow.tsx`. Add the test case.
7. Create `frontend/lib/polar.ts` with the five pure helpers.
   `polar.test.ts` covers derivation identities (§13.A). RED → GREEN.
8. Write `PolarChipRow.test.tsx` (cases in §13.B). RED.
9. Implement `PolarChipRow.tsx`. GREEN.
10. Wire `PolarChipRow` into `InfoChipRow.tsx`. Adjust
    `InfoChipRow.test.tsx` for four-row order. GREEN.

## 12 · Acceptance criteria

### 12.A Structural

- [ ] `InfoChipRow.tsx` reduces to ≤ 80 lines (container only).
- [ ] Six new component files + one helpers file (`lib/polar.ts`).
- [ ] Six new test files (one per row + one for helpers).
- [ ] `AR` chip appears in `GeometryChipRow`.

### 12.B Diagnostic value

- [ ] **Derivation identities:** `computeCLmd² = π·e·AR·C_D0`;
      `(L/D)_max = (π·e·AR) / (4·C_L,md)`;
      `ρ · C_L,max² = π·e·AR·C_D0`;
      `ρ = (computeCLmd / cl_max)²` within float ε.
- [ ] **Powered traffic-light:** `ρ = 1/3` → amber; `ρ = 1.00` → red.
- [ ] **Glider traffic-light:** `ρ = 2/3` → amber; `ρ = 1.00` → red.
- [ ] **Healthy aircraft fixture** (CD0=0.02, e=0.80, AR=7, CL_max=1.4,
      is_glider=false) → ρ ≈ 0.180 emerald, all derived chips
      populated.
- [ ] **Sailplane no-false-alarm fixture** (CD0=0.008, e=0.95, AR=36,
      CL_max=1.5, is_glider=true) → ρ ≈ 0.382 emerald under glider
      thresholds (would be amber under powered).
- [ ] **#625 reproduction** (e_oswald_fallback_used=true) → `e*=0.80`
      muted; k, C_L,md, (L/D)_max, ρ all `—`; shared bail tooltip.
- [ ] **Empty context** → all chips `—`, no crashes.

### 12.C Behaviour

- [ ] `e_oswald_fallback_used = true` triggers `e*` + fallback tooltip
      + muted colour.
- [ ] Polar chips remain visible for gliders (no `!is_glider`
      gating).
- [ ] `isRecomputing = true` overrides quality and traffic-light
      colours with stale red.
- [ ] ρ red tooltip contains the literal phrase "see Matching Chart".
- [ ] `npm run test:unit` passes.

## 13 · Test cases

### 13.A `polar.test.ts` (helper round-trips)

1. `computeCLmd(0.02, 0.80, false, 7) ≈ 0.594`
   `= √(π·0.80·7·0.02)`.
2. `computeEMax(0.02, 0.80, false, 7) ≈ 13.21`
   `= ½·√(π·0.80·7/0.02)`.
3. `computeRho(0.02, 0.80, false, 7, 1.4) ≈ 0.180`.
4. `computeRho ≡ (computeCLmd / cl_max)²` — fuzz over 10 random
   inputs.
5. `computeK(0.80, false, 7) ≈ 0.0568`.
6. `rhoThresholdsForProfile(false)` → `{ amber: 1/3, red: 1.0 }`;
   `(true)` → `{ amber: 2/3, red: 1.0 }`.
7. **Bail rule:** every helper returns `null` when `fallbackUsed=true`,
   regardless of other inputs.
8. Each negative / zero / null input on each helper → `null`.

### 13.B `PolarChipRow.test.tsx` (component)

9. **Healthy powered** — fixture from 12.B → all eight chips
   populated, ρ emerald.
10. **Sailplane** — fixture from 12.B → eight chips populated, ρ
    emerald *despite* ρ ≈ 0.38 (would be amber on powered).
11. **Powered amber lower boundary** — `ρ = 1/3` exact → amber.
12. **Powered red boundary** — `ρ = 1.00` exact → red.
13. **Glider amber lower boundary** — `ρ = 2/3` + `is_glider=true` →
    amber.
14. **Quality matrix on `e`:** high / medium / low / unknown →
    emerald / amber / orange / muted.
15. **#625 reproduction** — fallback → `e*=0.80` muted; k, C_L,md,
    (L/D)_max, ρ render `—`.
16. **Per-null input** (cd0=null, then cl_max=null, then AR=null) →
    that chip + every dependent derived chip → `—`.
17. **`ctx === null`** — all chips `—`.
18. **Tooltip text:** `(L/D)_max` tooltip contains "headline polar
    number"; ρ red tooltip contains "see Matching Chart"; bail tooltip
    contains "non-parabolic".
19. **`isRecomputing = true`** overrides all colours with stale red.

## 14 · Decisions

1. All four governing scalars plus the derived ρ.
2. Four thematic rows (Speed / Geometry / Polar / Stability).
3. Annotation level = Diagnostic.
4. Empty values → `—` with explanatory tooltips.
5. Full split into six new components.
6. Polar chips always visible (no `is_glider` hide gating).
7. Stale red overrides quality and traffic-light colours.

**Rev-2 (post-expert-review):**

8. **ρ-bail rule.** When `e_oswald_fallback_used = true`, all four
   derived polar quantities render `—`. Reason — Aero #1: the metric
   is only meaningful for parabolic polars; computing it on rejected
   fits produces a measurement-shaped non-measurement.
9. **Profile-aware ρ thresholds.** Glider `{ 2/3, 1.0 }`; powered
   `{ 1/3, 1.0 }`. Reason — Scholz: high-performance sailplanes
   intentionally operate with `V_min,sink ≈ V_stall`; flat ⅓ amber
   generates false alarms on healthy gliders.
10. **`(L/D)_max` is a first-class chip.** Scholz §5.7 canonical
    figure of merit.
11. **`C_L,md` is a first-class chip.** `C_D0` alone is not
    interpretable; the `(C_L,md, C_L,max)` pair tells the
    operating-CL story.
12. **`k` is a first-class chip.** `k = 1/(πeAR)` is the canonical
    induced-drag factor in Scholz / Sadraey notation.
13. **`C_L,cruise` deferred** (depends on #625 mass-context fix).
14. **Tooltips are consequence-first**, not formula-first.
15. **ρ-red tooltip prescribes** ("see Matching Chart") — converts
    passive diagnostic into actionable feedback.
16. **Re-conditional caveat** in `Re` tooltip — this row describes
    cruise-Re behaviour.
17. **CL_max low-Re bias caveat** in `C_L,max` tooltip — AeroBuildup
    conservative at Re < 3×10⁵.
18. **Sailplane no-false-alarm fixture** in the test suite.

## 15 · References

- **GitHub #625** — Mission Radar bug cluster (trigger).
- **GitHub #575** — earlier InfoChipRow split.
- **GitHub #545 / #550** — Mission Tab spider chart epic.
- **`assumption_compute_service.py:434-488`** — backend writer.
- **`assumption_compute_service.py:924-1032`** — `_fit_parabolic_polar`
  rejection guards.
- **Anderson, *Fundamentals of Aerodynamics* 6e, §6.7.2–§6.7.4** —
  L/D-max and the optimum-CL conditions.
- **Scholz, *Flugzeugentwurf* §5.6.2 / §5.7 / §5.8.**
- **Sadraey, *Aircraft Design* §4** — induced-drag factor `k`.

## 16 · Domain-expert-review record (rev 1 → rev 2)

| # | Sev | Source | Action |
|---|---|---|---|
| 1 | MAJOR | Aero | **Addressed** — ρ-bail rule (§8.5, §10, §13.B-15). |
| 2 | CRITICAL | Scholz | **Addressed** — `(L/D)_max` first-class chip (§8.1). |
| 3 | CRITICAL | Scholz | **Addressed** — `C_L,md` first-class chip (§8.1). `C_L,cruise` deferred (§4 Out of scope). |
| 4 | MAJOR | Aero | **Addressed** — amber tooltip reworded "min-sink at/below stall" (§9). |
| 5 | MAJOR | Scholz | **Addressed** — profile-aware thresholds (§8.4, §13.A-6, §13.B-10/13). |
| 6 | MAJOR | Scholz | **Addressed** — ρ-red tooltip prescribes "see Matching Chart" (§9). |
| 7 | MAJOR | Aero | **Addressed** — Re-conditional caveat + ρ derivation §3. |
| 8 | MAJOR | Aero | **Addressed** — CL_max low-Re bias caveat in tooltip (§9). |
| 9 | MAJOR | Scholz | **Addressed** — AC §12.B tests diagnostic value (healthy / sailplane / #625). |
| 10 | MINOR | Scholz | **Addressed** — consequence-first tooltips (§9). |
| 11 | MINOR | Scholz | **Addressed** — `k` first-class chip (§8.1). |
| 12 | NIT | Aero | **Addressed** — intuitive form `ρ = (C_L,md/C_L,max)²` (§3 + §9). |
| 13 | NIT | Scholz | **Addressed** — ρ derivation self-contained in §3. |
| 14 | MINOR | Aero | **Addressed** — `unknown` + fallback combination explicit (§8.3). |
| 15 | MINOR | Scholz | **Addressed** — `C_L,max,clean` precision in tooltip (§9). |
