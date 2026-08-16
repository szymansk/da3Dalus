# ADR 0011 — CG is a top-down design target, not the aggregate of component masses

- **Status:** Accepted — in force
- **Decided:** 2026-05 (gh-465); made explicit in `sync_weight_items_to_assumptions`'s docstring
- **Deciders:** Marc Szymanski (maintainer)
- **Confidence:** 🟢 CONFIRMED (code + docstrings); the *rationale* is 🟡 partly reconstructed

## Context

There are two ways to answer "where is the centre of gravity". **Bottom-up:** add
up every component's mass and position — what a CAD BoM naturally produces.
**Top-down:** the CG the *stability requirement* demands,
`x_cg = x_np − SM_target · MAC`. In conceptual and preliminary design these are not
two estimates of the same number — they are a **requirement** and a **status**. You
decide where the CG must be for the aircraft to fly the way you want, then move
batteries and servos until the components agree. Writing the component aggregate
into the design CG would invert the design loop: handling would become a side
effect of where the battery happened to fit.

## Decision

**`cg_x` is `CG_aero` — the CG stability demands — and is written only by
`assumption_compute_service`. The aggregated component CG (`CG_agg`) is never
written back into it.**

```
cg_x     = x_np − target_static_margin · MAC   (step 6 of recompute_assumptions,
                                                stored as CALCULATED)
CG_agg   = Σ(mᵢ·xᵢ) / Σmᵢ                       (exposed for comparison only)

comparison:  Δx = cg_x_design − cg_x_components
             within_tolerance = |Δx| < CG_TOLERANCE_M = 0.01 m
```

1. **Mass is different from CG.** Mass *is* bottom-up: producers write the `mass`
   assumption's CALCULATED side with `auto_switch_source=True`. A new aircraft
   starts from the seeded estimate of **1.5 kg**.
2. **`CG_agg` reaches the user as a comparison**, via `get_cg_comparison` and
   `assumption_computation_context.cg_agg_m` — never as an input to sizing.
3. **The envelope framing.** The min/max CG across all loading scenarios is the
   **Loading Envelope**; it must sit inside the **Stability Envelope**
   (`cg_stability_aft = x_np − target_SM·MAC`, forward limit from the elevator
   authority service, gh-500, with a conservative `0.30·MAC` stub as fallback).
   `enrich_context_with_cg_envelope` adds its keys **additively** and stores `None`
   rather than deceptive stubs when `x_np`/`MAC` are absent.
4. **Static margin is classified, not just reported** (Scholz §4.2):
   `<0.02` error (phugoid divergent) · `<target` warn · `≤0.20` ok · `≤0.30` warn
   (trim drag) · else error (elevator authority). The 2–3 % MAC
   dynamic-instability band is Sadraey §11.4
   ([ADR 0023](0023-engineering-constants-carry-provenance.md)).
5. **An empty component tree yields `None`, not `0.0`**, so the caller *clears* the
   calculated mass rather than asserting a 0 kg aircraft.

## Consequences

- The design loop runs in the correct direction; the comparison is an actionable
  delta with a 1 cm verdict; cold start works. `cg_x` is deliberately excluded from
  `_RECOMPUTE_TRIGGERING_PARAMS` because it is the recompute's own output.
- 🔴 **Two mass producers overwrite one another silently**, and `weight_items`
  carries no `component_id`, so the same battery in both places is double-counted
  and undetected. Both resolved by
  [ADR 0022](0022-one-authority-per-user-facing-quantity.md): the tree is
  authoritative, `weight_items` is retired.
- 🔴 **`CG_agg` ignores y and z downstream** — all three axes are computed, only
  `cg_x` reaches the computation context.
- 🔴 **`compute_recommended_cg` has no caller.** The top-down rule is implemented and
  unit-tested in `mass_cg_service`, but production reads it from
  `loading_scenario_service` and `assumption_compute_service` instead — two
  implementations of the project's central CG rule coexist.
- **Mass sync failures are invisible** — both call sites deliberately swallow
  exceptions so a failed sync never blocks the CRUD that triggered it. A cold-start
  chicken-and-egg on the first recompute (`x_np=None`/`mac=None`) is demoted to INFO
  as documented behaviour (gh-685), not a bug.

**Rejected:** writing `CG_agg` into `cg_x` — it inverts the design loop, rejected
explicitly by gh-465.

## Related

[ADR 0010](0010-design-assumptions-carry-estimate-and-calculated.md) ·
[ADR 0004](0004-one-aero-truth-per-aircraft.md) ·
[ADR 0022](0022-one-authority-per-user-facing-quantity.md) ·
[ADR 0023](0023-engineering-constants-carry-provenance.md) ·
domain rules BR-28 … BR-33 · [`../domain.md`](../domain.md) gap G-3 ·
[`../questions.md`](../questions.md) §Q-MB-1, §Q-MB-7, §Q-MB-8, §Q-MB-9.
Evidence: commit `628f1e25` (gh-465);
`app/services/mass_cg_service.py:20-21, 36, 174-186, 224-250`;
`app/services/loading_scenario_service.py:51-53`; project memory
`project_design_cycle_philosophy`.
