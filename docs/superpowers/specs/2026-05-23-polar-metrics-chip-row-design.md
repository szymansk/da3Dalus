# Polar metrics in the Workbench Chip-Row — design

**Date:** 2026-05-23
**Status:** Draft (pending user review)
**Type:** Frontend feature
**Brainstorm transcript:** in-session, 2026-05-22 / 2026-05-23

## 1 · Motivation

The Mission Tab investigation on 2026-05-22 (see GitHub issue #625) surfaced a
recurring difficulty: a user cannot tell from the workbench whether their
*aerodynamic polar* is healthy or degenerate. Two symptoms today expose this
gap:

1. The Mission radar Ist polygon collapses on aircraft whose polar is
   degenerate — `glide` and `climb` come back missing because
   `_fit_parabolic_polar` rejected the OLS fit (`assumption_compute_service.py
   :924-1032`).
2. The V-speed chip-row reports physically impossible relationships
   (`V_min,sink < V_stall`, `V_md == V_stall`) because the closed-form speeds
   do not clamp to `V_stall` (tracked as Bug C in #625) — but the underlying
   *cause* (a degenerate polar) is invisible to the user.

Both symptoms stem from a polar where
`C_D0 · π · e · AR ≈ C_L,max²` — i.e. the L/D optimum sits at or past the
stall point. With the four governing scalars not displayed anywhere on the
workbench header, the user has no fast way to diagnose which lever (`C_D0`,
`e`, `AR`, `C_L,max`) is responsible.

## 2 · Goal

Surface the four polar/geometry scalars **plus a derived degeneracy ratio ρ**
directly in the existing two-row chip strip at the top of the workbench, so
the user can self-diagnose polar quality at a glance without leaving the
screen.

## 3 · Scope

### In scope

- Add four new chips: `C_D0`, `e_oswald`, `AR`, `C_L,max` (clean).
- Add a fifth derived chip: `ρ = C_D0·π·e·AR / C_L,max²` with traffic-light
  colouring.
- Re-organise the existing second chip row into three thematic sections —
  *Geometry*, *Polar*, *Stability* — so the chip strip stays scannable as
  it grows from two to four logical rows.
- Refactor `InfoChipRow.tsx` into a thin container plus four sibling row
  components and a shared `Chip` primitive. Extract the existing chips into
  their new homes without behaviour change.

### Out of scope (separate follow-ups)

- **Per-configuration `C_L,max`** chips for takeoff / landing.
- **Bug C** (clamping `V_md` and `V_min,sink` against `V_stall`) — separate
  ticket already noted in #625.
- **Color-blind alternative** to the ρ traffic light. The tooltip text
  redundantly carries the threshold meaning, so the colour-blind degraded
  experience is still informative; a richer fix is its own UX ticket.
- **Backend changes.** All values are already cached in
  `assumption_computation_context` by `recompute_assumptions`
  (`assumption_compute_service.py:434-488`); only the consumer side moves.

## 4 · Architecture

```
frontend/components/workbench/
  Chip.tsx                ← extracted primitive (existing internal Chip fn moves here)
  SpeedChipRow.tsx        ← Row 1: V_stall, V_min,sink, V_md, V_cruise(*),
                                   V_x, V_y, V_a, V_max, V_dive
  GeometryChipRow.tsx     ← Row 2a: S_ref, MAC, B_ref, AR
  PolarChipRow.tsx        ← Row 2b: Re, C_D0, e, C_L,max, ρ        [new content]
  StabilityChipRow.tsx    ← Row 2c: NP, SM, CG
  InfoChipRow.tsx         ← container: data fetch, refresh button,
                            recomputing pill, renders the 4 rows
  renderSymbol.tsx        (unchanged)

frontend/__tests__/
  Chip.test.tsx                ← new
  SpeedChipRow.test.tsx        ← migrated cases
  GeometryChipRow.test.tsx     ← migrated cases + AR
  PolarChipRow.test.tsx        ← new, focus: ρ + empty-state + quality colours
  StabilityChipRow.test.tsx    ← migrated cases
  InfoChipRow.test.tsx         ← reduced to container behaviour
```

Each row component is a pure renderer with props
`{ ctx: ComputationContext | null, isRecomputing: boolean }` plus, for
`StabilityChipRow`, the existing CG-aggregation divergence inputs it
already reads. No row component performs its own SWR call; the container
remains the single source of truth.

## 5 · Data flow

```
GET /aeroplanes/{id}/assumptions/computation-context
        │
        ▼
useComputationContext(aeroplaneId)
        │   (TypeScript interface extended — see §6)
        ▼
InfoChipRow (container)
        │
        ├─ SpeedChipRow      (ctx, isRecomputing)
        ├─ GeometryChipRow   (ctx, isRecomputing)
        ├─ PolarChipRow      (ctx, isRecomputing)
        └─ StabilityChipRow  (ctx, isRecomputing, cgAggregation…)
```

## 6 · TypeScript interface changes

`frontend/hooks/useComputationContext.ts` — extend `ComputationContext`:

```ts
interface ComputationContext {
  // ... existing keys (v_cruise_mps, v_s1_mps, s_ref_m2, mac_m, b_ref_m,
  // reynolds, aspect_ratio, x_np_m, target_static_margin, cg_agg_m,
  // is_glider, is_tailless, v_cruise_auto, …) — unchanged

  // Newly typed (already present in the JSON response):
  cd0: number | null;
  e_oswald: number | null;
  e_oswald_quality: "high" | "medium" | "low" | "unknown";
  e_oswald_fallback_used: boolean;
  polar_by_config: {
    clean: {
      cd0: number | null;
      e_oswald: number | null;
      cl_max: number | null;
      // takeoff/landing also exist but are not consumed in this feature
    };
  } | null;
}
```

No runtime parser is added — the existing endpoint returns the raw JSON and
TypeScript types are advisory.

## 7 · PolarChipRow — details

### 7.1 Chips

| Chip | Symbol | Source | Format | Default colour |
|---|---|---|---|---|
| Reynolds | `Re` | `ctx.reynolds` | `toExponential(1)` | foreground |
| Zero-lift drag | `C_D0` | `ctx.cd0` | `.toFixed(4)` | foreground |
| Span efficiency | `e` or `e*` | `ctx.e_oswald` (or 0.80 fallback) | `.toFixed(2)` | derived from `e_oswald_quality` — see §7.3 |
| Max lift (clean) | `C_L,max` | `ctx.polar_by_config?.clean?.cl_max` | `.toFixed(2)` | foreground |
| Degeneracy ratio | `ρ` | computed — see §7.2 | `.toFixed(2)` | traffic light — see §7.4 |

When a source is `null`, the value renders as `—` and the chip's tooltip
explains why (see §9).

### 7.2 ρ computation

Pure helper exported from `PolarChipRow.tsx` for unit testing:

```ts
export function computeRho(
  cd0: number | null,
  eFromCtx: number | null,
  fallbackUsed: boolean,
  ar: number | null,
  clMax: number | null,
): number | null {
  const e = eFromCtx ?? (fallbackUsed ? 0.80 : null);
  if (cd0 == null || e == null || ar == null || clMax == null) return null;
  if (cd0 <= 0 || e <= 0 || ar <= 0 || clMax <= 0) return null;
  return (cd0 * Math.PI * e * ar) / (clMax * clMax);
}
```

### 7.3 Quality colour mapping (applied to the `e` value)

| `e_oswald_quality` | Tailwind class |
|---|---|
| `high` (R² > 0.99) | `text-emerald-400` |
| `medium` (0.95 ≤ R² ≤ 0.99) | `text-amber-400` |
| `low` (R² < 0.95) | `text-orange-400` |
| `unknown` (fit not run / rejected) | `text-muted-foreground` |

### 7.4 ρ traffic light

| Range | Meaning | Tailwind class |
|---|---|---|
| `ρ < 1/3` | healthy polar | `text-emerald-400` |
| `1/3 ≤ ρ < 1` | V_min,sink at or below V_stall | `text-amber-400` |
| `ρ ≥ 1` | degenerate: V_md at stall | `text-red-400` |

### 7.5 Fallback marker for `e`

When `ctx.e_oswald_fallback_used === true`:

- Symbol becomes `e*` (asterisk handled by the existing `renderSymbol`
  helper, mirroring the `V_cruise*` precedent).
- Value displays the fallback `0.80`.
- Tooltip is replaced by the fallback variant (see §8).

## 8 · Tooltips

One concise sentence each, consistent with existing chip tooltips. ρ gets
two lines because the threshold semantics are the actionable part.

| Symbol | Tooltip |
|---|---|
| `Re` | (unchanged) *"Reynolds number at cruise (characteristic length = MAC)"* |
| `C_D0` | *"Zero-lift drag coefficient from the parabolic polar fit (stability run)."* |
| `e` | *"Oswald span efficiency from the parabolic polar fit."* |
| `e*` | *"Polar fit was rejected — fallback value 0.80 used internally. Value colour reflects fit quality."* |
| `C_L,max` | *"Maximum lift coefficient (clean configuration) from AeroBuildup."* |
| `AR` | *"Aspect ratio = b² / S_ref (main wing)."* |
| `ρ` | *"Polar degeneracy ρ = C_D0·π·e·AR / C_L,max². ρ<⅓ healthy · ⅓≤ρ<1 V_min,sink at/below stall · ρ≥1 V_md at stall."* |

## 9 · Edge cases

| Case | Behaviour |
|---|---|
| `ctx === null` (no recompute has run) | All chips show `—`; refresh button stays active |
| Polar fit rejected (`e_oswald = null`, `e_oswald_fallback_used = true`) | `e*=0.80` with `text-muted-foreground`; ρ computed with fallback e *only when CD0 and CL_max are both present* |
| `cd0 = null` | `C_D0=—`; ρ=`—` |
| `cl_max = null` (clean polar missing entirely) | `C_L,max=—`; ρ=`—` |
| `aspect_ratio = null` (geometry issue) | `AR=—` (in GeometryChipRow); ρ=`—` |
| `is_glider === true` | **All five polar chips remain visible.** No conditional hide — polar health matters more, not less, for gliders |
| `isRecomputing === true` | Stale red colour applies to all chip values; overrides quality and traffic-light colours |

## 10 · Chip primitive — new prop

The extracted `Chip` component keeps every existing prop (`icon`, `symbol`,
`value | valueNode`, `description`, `stale`). One new optional prop is
added:

```ts
valueColorClassName?: string;   // Tailwind class applied to the value span only
```

`stale` (recompute red) has priority over `valueColorClassName`. The primitive
remains semantically neutral — colour meaning lives in the calling row
component.

## 11 · Testing strategy

`PolarChipRow.test.tsx` is the centre of the test effort. Required cases:

1. Healthy context (CD0=0.01, e=0.85, AR=15, CL_max=1.2) → all five chips
   render; ρ = 0.01·π·0.85·15 / 1.44 ≈ 0.28 with `text-emerald-400`.
2. Threshold matrix for ρ — six cases pin inclusion semantics:
   ρ ∈ {0.20, 1/3, 0.50, 0.99, 1.00, 1.20} → emerald, amber (lower
   boundary inclusive), amber, amber, red (upper boundary inclusive),
   red.
3. Asterisk pathway: `e_oswald_fallback_used = true` → symbol `e*`, value
   `0.80`, fallback tooltip.
4. Quality matrix on `e`: `high` / `medium` / `low` / `unknown` → emerald /
   amber / orange / muted.
5. Each individual `null` input (`cd0`, `e`, `aspect_ratio`, `cl_max`)
   propagates correctly: that chip and ρ both go to `—`.
6. `ctx === null` → every chip `—`, no crashes.
7. Tooltip text correctness — assert visible after hover/focus; ρ tooltip
   contains the threshold breakdown.
8. `isRecomputing = true` overrides quality and traffic-light colours with
   `text-red-400`.

`Chip.test.tsx`: render with `value`, with `valueNode`, `stale` red,
`valueColorClassName` applied, `stale` overrides `valueColorClassName`.

`SpeedChipRow.test.tsx`, `GeometryChipRow.test.tsx`,
`StabilityChipRow.test.tsx`: migrate the relevant cases from the current
`InfoChipRow.test.tsx`. No new behaviour — only sub-component scoping.

`InfoChipRow.test.tsx` is reduced to container behaviour: renders all four
rows in the expected order; refresh button calls SWR `mutate`; recomputing
pill appears when `isRecomputing`.

## 12 · Implementation order (TDD)

The order minimises risk of regressing existing chip behaviour:

1. Extract `Chip.tsx` (move existing inner function verbatim, add
   `valueColorClassName`). Write `Chip.test.tsx`. Verify existing
   `InfoChipRow.test.tsx` still passes after `InfoChipRow.tsx` imports the
   primitive.
2. Extract `SpeedChipRow.tsx`; migrate the relevant tests. Verify.
3. Extract `GeometryChipRow.tsx` (existing chips first, **without** AR);
   migrate tests. Verify.
4. Extract `StabilityChipRow.tsx`; migrate tests. Verify.
5. Extend `ComputationContext` type with the new fields.
6. Add AR chip to `GeometryChipRow.tsx`; add the new test case.
7. Write `PolarChipRow.test.tsx` (all 8 cases) — RED.
8. Implement `PolarChipRow.tsx` and the `computeRho` helper — GREEN.
9. Wire `PolarChipRow` into `InfoChipRow.tsx` between Geometry and
   Stability. Update `InfoChipRow.test.tsx` to assert the four-row order.

Each step is a self-contained commit. Step 8 is the only place where new
visual logic lands; steps 1–6 are mechanical refactors.

## 13 · Acceptance criteria

- [ ] `InfoChipRow.tsx` is ≤ 80 lines (container only).
- [ ] Four row components exist as sibling files, each with its own test
      file.
- [ ] A `PolarChipRow` row appears in the workbench between Geometry and
      Stability.
- [ ] For a healthy polar (R² > 0.95, ρ < 1/3), the row shows `Re`,
      `C_D0`, `e`, `C_L,max`, `ρ` all populated, `ρ` in emerald.
- [ ] For the reproduction aeroplane in #625 (polar fit rejected), the row
      shows `Re=…`, `C_D0=—`, `e*=0.80` in muted grey, `C_L,max=—`,
      `ρ=—`. Tooltips explain each `—`.
- [ ] `ρ` traffic-light thresholds are unit-tested at the boundaries.
- [ ] Tooltip on `ρ` contains the threshold meaning verbatim.
- [ ] `is_glider === true` does **not** hide any polar chip.
- [ ] During recompute, all chip values are red (existing stale pattern
      continues to win).
- [ ] `npm run test:unit` passes.

## 14 · Decisions taken during brainstorming

1. **All four values plus the derived ρ.** Plain values alone are not
   sufficient for self-diagnosis; ρ does the interpretation.
2. **Thematic split: Speed / Geometry / Polar / Stability — four rows.**
   The Polar row gets its own thematic section rather than being appended
   to Geometry (which would be eleven chips wide).
3. **Annotation level = Diagnostic.** Asterisk on `e` when fallback, quality
   colour on `e`, and the traffic-light ρ chip — all of these in one shot,
   not staged.
4. **Empty values render as `—` with an explanatory tooltip.** No hidden
   chips; explicit absence is preferable to invisible omission (the same
   principle that the Mission radar epic #561 is currently failing on).
5. **Full split into five new components.** `InfoChipRow.tsx` becomes a
   thin container. Three extracted rows have no behaviour change; the
   Polar row introduces the new logic. The shared `Chip` primitive
   eliminates the duplicate inner function and adds a single new prop.
6. **Polar chips always visible.** Gliders specifically benefit from polar
   transparency, so the `!is_glider` gating used by V_a / V_max / V_dive is
   not extended.
7. **Stale red overrides quality and traffic-light colours.** Single source
   of visual truth during recompute; the user knows the values are
   provisional.

## 15 · References

- **#625** — Mission Radar Ist polygon bug cluster (the trigger that surfaced
  the diagnostic gap).
- **#575** — InfoChipRow split into two rows / refresh button. This spec
  refactors the same component.
- **#545 / #550** — Mission Tab spider chart epic & component (the
  downstream consumer of these polar values).
- **`assumption_compute_service.py:434-488`** — backend writer of the
  context keys this UI consumes.
- **`field_length_service.py:322-335`** — gh-548 wiring that revealed the
  mass-source mismatch. Adjacent context for #625 Bug B.
- **Anderson, *Fundamentals of Aerodynamics* 6e, §6.7.2** — derivation of
  L/D-max and the optimum-CL conditions used in the ρ formula.
