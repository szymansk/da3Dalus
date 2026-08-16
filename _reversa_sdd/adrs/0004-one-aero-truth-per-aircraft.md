# ADR 0004 — One aero truth per aircraft: the cached computation context

- **Status:** Accepted — in force
- **Decided:** 2026-06-09 (gh-924, commit `8847b13d`)
- **Deciders:** Marc Szymanski (maintainer), ratified by three domain-expert reviews
- **Confidence:** 🟢 CONFIRMED (detailed commit body with before/after numbers)

## Context

Over roughly a year the codebase grew several independent producers of the same
four aerodynamic scalars, each locally reasonable, none agreeing. For one aircraft
the application simultaneously showed **three different `cd0` values**, **two
neutral points** (0.080 m and 0.109 m — a 36 % spread), and `L/D ≈ 17` on the
dashboard against `L/D ≈ 24` on the analysis chart. **The AI copilot UAT surfaced
it**: asked for glide performance, the model read two sources and produced a
contradiction a human had been tolerating as "different views". The root cause was
not the computation but the **definition**.

## Decision

**One aircraft has exactly one aerodynamic truth, produced once and read by
everyone.** `assumption_compute_service.recompute_assumptions` computes it at the
**cruise design point** and caches it on
`aeroplanes.assumption_computation_context` (~40 keys: speeds, geometry, aero,
α-at-characteristic-speeds, polars, stability/CG, envelope, provenance).

```
cd0        = CD_total − CL²/(π·AR·e)      # PARASITE, not total CD (Anderson §6.7.2)
e          = AeroBuildup Trefftz span efficiency
(L/D)max   = ½·√(π·AR·e / CD0)            # Scholz eq. 5.39, not argmax(CL/CD)
x_np       = one cruise-design-point value (Anderson §4.9: α-independent)
```

- **Provenance is explicit.** The Oswald chain is
  `aerobuildup_trefftz → fit → fallback`, recorded in
  `polar_by_config[*].e_oswald_provenance` and mirrored by
  `context["e_oswald_fallback_used"]`.
- **Fallback rows are backfilled** with the authoritative parasite `cd0` and
  Trefftz `e`, so every Reynolds-dependent consumer reads the same value.
- **Every downstream consumer reads the context** — speed polar, V-n envelope,
  matching chart, mission KPIs, endurance, spar sizing, powertrain solution space
  and sizing, and the copilot's `run_analysis`, which explicitly *overrides* its
  freshly computed neutral point with `ctx["x_np_m"]`.
- **No consumer derives its own.**

Ratified by three domain-expert reviews (Anderson, AeroSandbox, Scholz/Sadraey as
lead) against real AeroBuildup data and verified with a real recompute.

## Consequences

- Verified single-valued afterwards: `cd0 = 0.0133`, `e = 0.79`, `L/D = 23.0`
  (equal to the closed form), `x_np = 0.080` everywhere. The context is a
  **contract**, so the copilot can answer deterministically.
- The context is a **JSON blob, not a typed schema**; consumers navigate it by
  dotted key and a rename breaks readers silently. Constrained by the
  [ADR 0010 amendment](0010-design-assumptions-carry-estimate-and-calculated.md).
- It is **cached, therefore staleable** — freshness depends entirely on the
  `GeometryChanged` / `AssumptionChanged` → debounced-recompute chain.
- Recompute is expensive and synchronous: it holds a SQLite write transaction open
  for seconds while AeroBuildup runs (hence WAL + 30 s busy timeout).
- 🔴 Two known violations, both now resolved elsewhere:
  `stability_service._auto_populate_cd0` writes the **total** CD into the `cd0`
  assumption on a different trigger (deleted under
  [ADR 0022](0022-one-authority-per-user-facing-quantity.md)); a missing `mass`
  assumption silently yields a **1.0 kg** speed polar (an `error`-severity
  `DesignWarning` under
  [ADR 0020](0020-one-designwarning-channel-no-undeclared-fallbacks.md)).

**Rejected:** accepting multiple values labelled by method — for these four
quantities there *is* a physically correct answer, and presenting several is a
defect, not a feature.

## Related

[ADR 0003](0003-aerosandbox-default-avl-exception.md) ·
[ADR 0010](0010-design-assumptions-carry-estimate-and-calculated.md) ·
[ADR 0012](0012-design-warnings-instead-of-silent-fallbacks.md) ·
[ADR 0022](0022-one-authority-per-user-facing-quantity.md) (generalises this) ·
domain rules BR-14, BR-16, BR-17, BR-18.
Evidence: commits `8847b13d` (gh-924), `de22bcec` (gh-956), `55485f1c` (gh-493);
`app/services/assumption_compute_service.py:59-809`; the context key table in
[`../data-dictionary.md`](../data-dictionary.md); project memory
`project_aero_single_source_of_truth`.
