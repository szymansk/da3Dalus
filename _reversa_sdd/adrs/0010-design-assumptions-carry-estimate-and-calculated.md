# ADR 0010 — Every design parameter carries both an estimate and a calculation

- **Status:** Accepted — in force
- **Decided:** 2026-05 (gh-465, commit `628f1e25`)
- **Deciders:** Marc Szymanski (maintainer)
- **Confidence:** 🟢 CONFIRMED (schema, service, commit)

## Context

Conceptual design is iterative in a specific way: you *guess* a parameter, size the
aircraft with it, compute what the geometry actually delivers, and compare. The
guess is not noise to be discarded once the calculation exists — it is the design
intent, and the gap between the two is the signal the designer wants. There is also
a cold-start problem: a brand-new aircraft has no geometry, so nothing *can* be
calculated, and it must still be sizeable. And some parameters are never derivable
at all — target static margin, load factor limit, motor and ESC efficiency are
*choices*, not outcomes.

## Decision

**A design assumption is a triple: `estimate_value`, `calculated_value`,
`active_source`.**

```
effective_value = calculated_value  if active_source == "CALCULATED" and it exists
                  else estimate_value

divergence_pct  = |estimate − calculated| / |calculated| × 100
divergence_level: <5 none · <15 info · ≤30 warning · else alert
```

1. **15 parameters** are seeded idempotently from `PARAMETER_DEFAULTS`
   (`mass` 1.5 kg, `cg_x` 0.15 m, `cd0` 0.03, `cl_max` 1.4, `g_limit` 3.0, …).
   `seed_defaults` is called unconditionally by `recompute_assumptions`, because
   wings can be created before the user opens the Assumptions tab.
2. **Seven `DESIGN_CHOICE_PARAMS` can never be calculated** and can never be switched
   to `CALCULATED`: `target_static_margin`, `g_limit`, `battery_capacity_wh`,
   `battery_specific_energy_wh_per_kg`, `propulsion_eta_motor`,
   `propulsion_eta_esc`, `motor_continuous_power_w`.
3. **Auto-switch fires exactly once.** `update_calculated_value(...,
   auto_switch_source=True)` flips `active_source` to `CALCULATED` only on the
   *first* calculated value, only from `ESTIMATE`, and never for a design choice.
   After that the user's manual choice sticks.
4. **Events fire only when the *effective* value changes.** `update_assumption`
   publishes `AssumptionChanged` only when `active_source == "ESTIMATE"`;
   `switch_source` always fires.
5. **Provenance is stored** in `calculated_source` (`aerobuildup`,
   `best_glide_v_md`, `stability_analysis`, `weight_items`, `component_tree`, …).
6. **Mission presets write estimates only.** `calculated_value`,
   `calculated_source` and `active_source` stay owned by
   `assumption_compute_service`.

## Consequences

- A brand-new aircraft is immediately sizeable and converges to physics as geometry
  appears, and **divergence is a product feature** — impossible to express with a
  single value. Design choices are structurally protected from a solver.
- 🔴 **Two resolvers exist** for the effective value —
  `design_assumptions_service.get_effective_assumption` (falls back to
  `PARAMETER_DEFAULTS`, returns `None`) and
  `mass_cg_service.get_effective_assumption_value` (raises `NotFoundError`) — so two
  aircraft in one database can behave differently depending on which a caller picked.
- 🔴 Three further defects, each resolved elsewhere: `min_static_margin` /
  `max_static_margin` are read but never seeded, so the 5 % / 25 % CG bounds are
  hard-coded while appearing configurable
  ([ADR 0021](0021-complete-but-unreachable-code-is-deleted-by-default.md)); two
  producers write the same `mass` `calculated_value`
  ([ADR 0022](0022-one-authority-per-user-facing-quantity.md)); and
  `_apply_preset_estimates` silently no-ops on an unknown `mission_type`, because
  `mission_presets.id` is a free-text PK with no FK.
- The recompute-trigger set must exclude its own outputs (`cg_x`, `cd0`, `cl_max`)
  or it loops — a coupling easy to break when adding a parameter.

**Rejected:** always preferring the calculated value — the designer must be able to
pin a value the tools disagree with; that *is* preliminary design.

## Related

[ADR 0004](0004-one-aero-truth-per-aircraft.md) ·
[ADR 0011](0011-cg-is-a-top-down-design-target.md) ·
[`../state-machines.md`](../state-machines.md) §5 · domain rules BR-24 … BR-27.
Evidence: commit `628f1e25` (gh-465); `app/schemas/design_assumption.py:72-108`
(the parameter catalogue);
[`../data-dictionary.md`](../data-dictionary.md) § `design_assumptions`.

---

## Amendment — 2026-08-15 — the `assumption_computation_context` contract

**Source:** [`../questions.md`](../questions.md) §Q-CC-10. **Confidence:** 🟢
CONFIRMED.

The duality above governs the 15 catalogued design parameters. The quantities
*feeding* them travel in `aeroplanes.assumption_computation_context` — ~40 keys
produced once at the cruise point and read by nine consumers. ADR 0004 flags that
blob as a JSON column with no schema; this amendment gives it a contract. The
decisive input: **the fundamental key set is considered finished** (further keys may
be added, but occasionally). That removes the usual trade-off — a Pydantic model is
insensitive to *additions*, and what it prevents is **silent renames and typos**,
precisely the failure mode here.

1. **A typed Pydantic model** in one shared location, with **`extra="allow"`** so an
   occasional new key never breaks an older consumer, while every known key is typed
   and validated.
2. **`context_version`** — the *schema* version, so a consumer can detect a context
   produced under an older shape and act deliberately.
3. **A freshness marker** — `computed_at` plus a hash of the inputs the context was
   derived from.
4. **A producer/consumer contract test** — asserting that every key the nine
   consumers read is a key the producer actually writes.
5. **No defaults on a missing key.** The RC-typical fallbacks — `cd0 0.03`, `e 0.8`,
   `AR 8.0`, `S 0.5 m²`, `mass 1.0 kg` — are **removed**. A missing key emits a
   `DesignWarning` with `category = input_missing` and **`severity = error`**, per
   `P-WARN-0` /
   [ADR 0020](0020-one-designwarning-channel-no-undeclared-fallbacks.md).

**Schema version and freshness are different failure modes, and the second is
sharper.** The fallbacks fire only on **missing** values, never on **outdated** ones,
so today *a stale context is indistinguishable from a fresh one*: change the wing
geometry without recomputing and all nine consumers silently continue with the old
numbers (`Q-PT-8`).

**Cost.** Every consumer must handle a `DesignWarning` where it previously received a
number, so responses that used to render a plausible chart now render nothing plus an
`error`. The shared model needs an owned home (`Q-CC-15`).

**Related:** [ADR 0004](0004-one-aero-truth-per-aircraft.md) (the context itself) ·
[ADR 0020](0020-one-designwarning-channel-no-undeclared-fallbacks.md) (the channel) ·
[ADR 0022](0022-one-authority-per-user-facing-quantity.md) (the contract test as a
general instrument) · [`../questions.md`](../questions.md) §Q-CC-10, §Q-PT-8,
§Q-MS-8, §Q-AA-1, §Q-CC-15.
