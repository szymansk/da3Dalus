# stability-derivatives — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker. Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `AnalysisModel` with `reference.Xnp`, `reference.Cref` and
      `derivatives.Cma/Cnb/Clb` ([`../tasks.md`](../tasks.md) T-01).
- [ ] `analyse_aerodynamics` dispatcher ([`../tasks.md`](../tasks.md) T-02).
- [ ] `resolve_operating_point` and deflection validation
      ([`../operating-point-solve/tasks.md`](../operating-point-solve/tasks.md)
      T-04, T-05).
- [ ] An aeroplane schema exposing per-wing x-sections
      (`x_le/y_le/z_le/chord/twist`) and per-fuselage x-sections
      (`x_c/width/height`).
- [ ] A `stability_results` table with `UniqueConstraint(aeroplane_id, solver)`.
- [ ] The event bus and SQLAlchemy listener infrastructure (`platform-core`).

## Tasks

- [ ] **T-01 — `compute_geometry_hash`.**
  Build the canonical dict of **stability-relevant** geometry only — per-wing
  `x_le/y_le/z_le/chord/twist` per x-section, per-fuselage `x_c/width/height` —
  serialise it deterministically (sorted keys) and take `sha256(...)[:16]`.
  - Legacy origin: `app/services/stability_service.py:102-141`
  - Definition of done: changing a chord or a twist changes the hash; adding a
    spar, a servo, a turbulator or a mass item does **not**; the hash is stable
    across two runs on unchanged geometry (no dict-ordering nondeterminism).
  - Confidence: 🟢

- [ ] **T-02 — The derived stability block.**

  ```
  static_margin           = (Xnp − Xcg) / MAC          Xcg = operating_point.xyz_ref[0]
  static_margin_pct       = 100 · static_margin
  stability_class         = "stable"   if pct > 5
                            "neutral"  if 0 ≤ pct ≤ 5
                            "unstable" if pct < 0
  cg_range_forward        = Xnp − (max_pct / 100) · MAC
  cg_range_aft            = Xnp − (min_pct / 100) · MAC
  is_statically_stable    = Cma < 0
  is_directionally_stable = Cnb > 0
  is_laterally_stable     = Clb < 0
  ```

  - Legacy origin: `app/services/stability_service.py:289-362`
  - Definition of done: the worked example (Xnp 0.30 m, Xcg 0.26 m, MAC 0.20 m)
    yields margin 0.20, 20 %, `stable`, `cg_range_forward` 0.25 m,
    `cg_range_aft` 0.29 m; the boundary values 0 % and 5 % land in `neutral`.
  - Confidence: 🟢

- [ ] **T-03 — Margin bounds, made real.**
  Read `min_static_margin` / `max_static_margin`, defaulting to 5 % / 25 %.
  - Legacy origin: `app/services/stability_service.py:225-254`
  - Definition of done: setting the parameters actually changes `cg_range_*`.
  - 🟡 **Drop the dead lookup and promote the 5 % / 15 % band** (`Q-AA-2`, derived). The legacy queries two parameter names that are
    **not** in `VALID_PARAMETERS` / `PARAMETER_DEFAULTS`, so they are never
    seeded and the query always returns empty. Either add both to the parameter
    catalogue (with defaults 5 and 25) **or** delete the lookup and promote the
    numbers to named constants. Do not keep the current state, which presents as
    configurable and is not.
  - Confidence: 🟡

- [ ] **T-04 — Trim α and trim control extraction.**
  Record `trim_alpha_deg` from the (already degree-valued) operating point and
  the pitch-axis deflection from the resolved deflections.
  - Legacy origin: `app/services/stability_service.py` (`_find_trim_elevator`)
  - Definition of done: a conventional aircraft reports its elevator deflection;
    a V-tail reports its **pitch-axis** deflection.
  - 🟢 **Decided (`Q-WD-1`):** resolve through the mixing layer. The legacy takes the first deflection whose
    name **contains `"elevator"`** (case-insensitive), which never matches
    `[ruddervator]pitch_htail_1`. Resolve the pitch control through the gh-772
    axis decomposition (role ∈ `{elevator, stabilator, elevon, ruddervator}` →
    primary/pitch axis) instead of a substring match, and record **which** control
    was used so a `NULL` is explainable.
  - Confidence: 🟡

- [ ] **T-05 — `persist_stability_result` upsert.**
  Upsert on `(aeroplane_id, solver)`, writing every derived value plus
  `cg_x_used`, `geometry_hash`, `computed_at` and `status = "CURRENT"`.
  - Legacy origin: `app/services/stability_service.py`,
    `app/models/stability_result.py:25`
  - Definition of done: two AeroBuildup runs leave one row; an AVL run adds a
    second; no history rows accumulate.
  - Confidence: 🟢

- [ ] **T-06 — `get_cached_stability`.**
  Return the newest row, preferring `CURRENT` over `DIRTY`; 404 when none
  exists.
  - Legacy origin: `app/services/stability_service.py`
  - Definition of done: with both a `CURRENT` and a `DIRTY` row, the `CURRENT`
    one is returned; the response carries `status` so the caller can see
    staleness.
  - 🟡 **Deviation recommended:** replace the legacy `ORDER BY status ASC` — which
    works only because `'CURRENT' < 'DIRTY'` alphabetically — with an explicit
    rank (`CASE status WHEN 'CURRENT' THEN 0 ELSE 1 END`), so a future status
    value cannot silently reorder the query.
  - Confidence: 🟢

- [ ] **T-07 — Dirty listeners, registered exactly once.**
  `after_insert/update/delete` on `WingModel`, `WingXSecModel`, `FuselageModel`:
  mark `stability_results.status = 'DIRTY'`, call `mark_ops_dirty`, publish
  `GeometryChanged`.
  - Legacy origin: `app/models/stability_events.py`
  - Definition of done: a wing edit flips a `CURRENT` row to `DIRTY`;
    `GeometryChanged` is published **once** per write.
  - 🟡 **Factor the shared listener out so a geometry write publishes `GeometryChanged` once** (`Q-AA-4`, derived; ADR 0022 applied to invalidation paths). The legacy attaches the same three models again in
    `avl_geometry_events.py`. Register once, in one owning module, and have the
    AVL side subscribe rather than re-attach.
  - Confidence: 🟢

- [ ] **T-08 — Delete `_auto_populate_cd0`.**
  The legacy writes `result.CD` (**total** CD) into the `cd0` assumption's
  `calculated_value` with source `"stability_analysis"` when the tool is
  AeroBuildup.
  - Legacy origin: `app/services/stability_service.py:257-281`
  - Definition of done: `cd0` has exactly **one** writer,
    `assumption_compute_service._parasite_cd0`; a stability run leaves the
    assumption untouched; a regression test asserts that running a stability
    summary does not change `cd0`.
  - Confidence: 🟢 — deleted (`Q-AA-1`); confirmed BR-14 / ADR 0004 violation (removal is a deliberate
    deviation from the legacy)

- [ ] **T-09 — The two routes.**
  `POST /aeroplanes/{id}/stability_summary/{analysis_tool}` →
  `StabilitySummaryResponse` (200 · 404 · 422 · 500) and
  `GET /aeroplanes/{id}/stability` → `StabilityResultRead`
  (200 · **404 no cached result** · 500), both on the non-finite-safe router.
  - Legacy origin: `app/api/v2/endpoints/aeroanalysis.py:186-234`
  - Definition of done: the generated OpenAPI matches
    [`../contracts.md`](../contracts.md); a NaN margin serialises as `null`.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Worked margin example.** Xnp 0.30, Xcg 0.26, MAC 0.20 → 0.20 /
      20 % / `stable` / 0.25 / 0.29.
- [ ] **TT-02 — Classification boundaries.** 5.0 % → `neutral`, 5.01 % →
      `stable`, 0.0 % → `neutral`, −0.01 % → `unstable`.
- [ ] **TT-03 — Sign tests.** Each of `Cma`, `Cnb`, `Clb` flipped
      independently toggles exactly one boolean.
- [ ] **TT-04 — Hash sensitivity.** Chord change → different hash; spar / servo /
      turbulator / mass change → identical hash.
- [ ] **TT-05 — Hash determinism.** Two computations on unchanged geometry are
      byte-identical.
- [ ] **TT-06 — Upsert.** Two same-solver runs → one row; two different solvers →
      two rows.
- [ ] **TT-07 — Cached preference.** `CURRENT` beats `DIRTY`; add a third status
      value to the fixture and assert the explicit rank still returns `CURRENT`
      (guards the T-06 deviation).
- [ ] **TT-08 — 404 on a never-analysed aircraft.**
- [ ] **TT-09 — Dirty listener.** A wing x-section update flips the row to
      `DIRTY` and publishes `GeometryChanged` exactly once.
- [ ] **TT-10 — Configurable bounds (T-03).** Setting `min_static_margin` to 8 %
      changes `cg_range_aft`.
- [ ] **TT-11 — #955 regression (T-04).** A V-tail aircraft reports a **non-null**
      pitch trim deflection.
- [ ] **TT-12 — BR-14 regression (T-08).** Running a stability summary does not
      modify the `cd0` assumption.
- [ ] **TT-13 — Non-finite safety.** A `NaN` neutral point serialises as `null`
      and the body remains valid JSON.
- [ ] **TT-14 — Solver agnosticism.** The same aircraft summarised with
      AeroBuildup and with VLM produces the same response **shape**; only the
      `solver` field and the numbers differ.
- [ ] **TT-15 — Fast-tier coverage.** Every test above runs without AeroSandbox
      by stubbing `analyse_aerodynamics` to return a hand-built `AnalysisModel`
      (ADR 0015).

## Suggested Order

1. **T-01** first — the hash is independent of the solver and unblocks the
   persistence tests.
2. **T-02** next; it is pure arithmetic over envelope fields and can be tested
   with a hand-built `AnalysisModel`.
3. **T-03** and **T-04** carry the two deviations and should be decided (and
   documented) before T-05 freezes the row shape.
4. **T-05, T-06** — persistence and read.
5. **T-07** — invalidation, after there is something to invalidate.
6. **T-08** — the deletion; land it together with T-05 so `cd0` never has two
   writers even transiently.
7. **T-09** last.

Blocking edges: T-05 ⇠ T-01, T-02, T-03, T-04 · T-06 ⇠ T-05 · T-07 ⇠ T-05 ·
T-09 ⇠ T-05, T-06.

## Pending Gaps

- **`_auto_populate_cd0` (T-08).** Removal is the documented intent, but nothing
  records why it was added. Check whether any consumer relies on `cd0` being
  populated by a stability run alone before deleting it.
- **Margin-bound parameters (T-03).** Seed them, or make the constants explicit?
  Seeding adds two entries to the parameter catalogue and to every existing
  aircraft; the constant route removes a documented (if non-functional)
  configuration point.
- **Trim-control identification (T-04).** Should the row record *which* control
  variable produced `trim_elevator_deg`, so a `NULL` distinguishes "no pitch
  control" from "no match"? The column name itself (`trim_elevator_deg`)
  presumes a conventional elevator.
- **Two SM ladders.** This module's `stable/neutral/unstable` ladder and
  `loading_scenario_service`'s `error/warn/ok` ladder disagree on the same
  aircraft. Which is authoritative for the UI, and should they be unified?
- **Geometry-hash verification.** The hash is stored but never recomputed and
  compared on read. Should `GET …/stability` verify it and downgrade the status
  itself, rather than relying on the listeners?
- **Dynamic stability is absent.** AVL can produce eigenmodes and a
  `dutch_role_start` operating-point target exists, but no path computes damping
  or mode shapes. Is that deliberate scope, or a gap?
