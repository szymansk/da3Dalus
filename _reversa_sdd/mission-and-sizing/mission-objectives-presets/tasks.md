# mission-objectives-presets — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker (🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP).
> Parent: [`../tasks.md`](../tasks.md) T-03.
> Contracts: [`../contracts.md`](../contracts.md) §B.

## Prerequisites

- [ ] [`../design-assumptions/`](../design-assumptions/tasks.md) T-01 and T-05:
      the parameter catalogue and `seed_defaults`, since the preset writer
      targets `design_assumptions.estimate_value` for five parameters.
- [ ] `aero-analysis`: `aeroplanes.assumption_computation_context` populated
      with `v_cruise_mps`, `v_s1_mps`, `aspect_ratio`, `cd0`, `e_oswald`,
      `polar_by_config.clean`, `flight_envelope_n_max`, `s_ref_m2`, `mass_kg`.
- [ ] `field_length_service.compute_field_lengths_for_aeroplane` — the only
      external call, and the only one that may raise.
- [ ] Tables `mission_objectives` (unique FK) and `mission_presets` (String PK),
      with the seed executed at startup **and** in test fixtures that build the
      schema via `Base.metadata.create_all` instead of Alembic.
- [ ] No AeroSandbox dependency on the KPI path — six of seven axes must be
      testable in the CI fast tier (ADR 0015).

## Tasks

- [ ] **T-01 — The objective schema and its bounds.**
  `MissionObjective` with `mission_type` plus seven targets, four
  field-performance inputs and three optional gh-477 landing inputs. Bounds:
  `target_stall_safety ≥ 1.0`, `target_maneuver_n ≥ 1.0`, everything else
  `≥ 0`; `landing_safety_factor ∈ [1.0, 3.0]`; the three literals
  `RunwayType`, `TakeoffMode`, `LandingSurface`.
  - Legacy origin: `app/schemas/mission_objective.py:14-66`
  - Definition of done: `target_stall_safety = 0.9` ⇒ 422;
    `landing_safety_factor = 0.5` ⇒ 422; the six `LandingSurface` values match
    the μ table keys in `assumption_compute_service.LANDING_SURFACE_MU`
    **exactly** — a mismatch silently selects the wrong friction coefficient.
  - Confidence: 🟢

- [ ] **T-02 — The non-persisting default.**
  `_default_objective()` returning a **new instance per call**;
  `get_mission_objective` returning it when no row exists, without writing.
  - Legacy origin: `app/services/mission_objective_service.py:12-44`
  - Definition of done: two reads return independent objects; no row is created
    by a GET; the twelve default values match the column server-defaults.
  - 🟡 The Python defaults duplicate the DB server-defaults. Derive one from the
    other, or add a test asserting they agree.
  - Confidence: 🟢

- [ ] **T-03 — The upsert with change detection.**
  Capture `old_mission_type` **before** mutating, create the row when absent,
  `setattr` every field from `payload.model_dump()`, flush, then apply the
  preset **only** when `old_mission_type != payload.mission_type` (so the first
  create, where the old value is `None`, always applies).
  - Legacy origin: `:47-77`
  - Definition of done: a second `PUT` updates rather than inserts; a `PUT` that
    changes only `target_cruise_mps` leaves the five estimates untouched; the
    first create applies the preset.
  - Confidence: 🟢

- [ ] **T-04 — `_apply_preset_estimates` — estimates only.**
  Look the preset up by id; for each of the five `suggested_estimates` find or
  create the `design_assumptions` row and set **`estimate_value` only**; flush.
  - Legacy origin: `:80-101`
  - Definition of done: after a mission switch, `calculated_value`,
    `calculated_source` and `active_source` are byte-identical for all five
    parameters; a parameter with no row is created with the preset value.
  - 🟢 **Decided (`Q-MS-10`, `P-WARN-0`):** an unknown `mission_type` fails visibly.
    Reject it (422) or return a warning — today a typo produces no error, no
    warning and no change, and the KPI service does not reject it either.
  - 🟢 **Decided (`Q-MS-10`):** the writer routes through `update_assumption`. Previously it set the ORM field directly, so no
    `AssumptionChanged` is published and no operating point is dirtied even when
    those estimates are the effective values. Route it through
    `update_assumption`, or document why a mission change must not invalidate.
  - Confidence: 🟢 for the behaviour, 🔴 for both fixes

- [ ] **T-05 — The nine seeded presets.**
  `SEED_PRESETS` with the id, label, description, `target_polygon` (7 axes),
  `axis_ranges` (7 axes) and `suggested_estimates` of each, reproducing the
  table in [`design.md`](design.md) §The nine presets — including the in-code
  caveats (`acro_3d` deliberately at `target_static_margin = 0.0`;
  `motor_glider`'s `prop_efficiency = 0.65` reflecting the **climb** segment and
  `g_limit = 5.3` citing CS-22.337).
  - Legacy origin: `app/services/mission_preset_seed.py`
  - Definition of done: nine entries; every `target_polygon` and `axis_ranges`
    covers exactly the seven `AxisName` values; the values match the table.
  - 🟢 **Decided (`Q-MS-1`):** W/kg is canonical and the presets are re-authored. `power_to_weight` is catalogued as
    **W/kg** with a default of `220.0`, but `trainer` 0.5 · `sport` 0.7 ·
    `wing_racer` 1.0 · `acro_3d` 1.4 · `stol_bush` 0.8 write a dimensionless
    T/W-shaped number, while `motor_glider` and `flying_wing` write `100.0`
    W/kg. The regression tests pin the W/kg reading. Convert the seven, or
    change the parameter's unit — but not both silently.
  - Confidence: 🟢 for the values, 🔴 for the units

- [ ] **T-06 — Idempotent seeding and the list projection.**
  `seed_mission_presets` inserting only ids absent from the table;
  `list_mission_presets` converting `axis_ranges` **lists → tuples** on read and
  `seed_mission_presets` converting **tuples → lists** on write.
  - Legacy origin: `mission_objective_service.py:104-143`
  - Definition of done: two seed runs leave nine rows and do not overwrite an
    externally edited label; a round-trip through the DB preserves the ranges.
  - Confidence: 🟢

- [ ] **T-07 — The normalisation primitives.**

  ```python
  _normalise_score(value, lo, hi):
      if hi <= lo:  return 0.0                     # degenerate range
      return clip((value - lo) / (hi - lo), 0.0, 1.0)

  _ctx_get(ctx, key):                              # absent | non-numeric | <= 0
      v = ctx.get(key)
      return float(v) if isinstance(v, (int, float)) and v > 0 else None

  _missing(axis, lo, hi, formula, warning=None) -> MissionAxisKpi
      value = unit = score_0_1 = None; provenance = "missing"
  ```

  - Legacy origin: `app/services/mission_kpi_service.py:56-100`
  - Definition of done: a value above the range clips to `1.0`, below to `0.0`;
    `s_ref_m2 = 0` reads as absent and never divides; a `missing` axis still
    reports its range so the radar knows where the gap is.
  - 🟡 **Deviation to consider:** a degenerate range returns `0.0` rather than
    `None` — an unknown rendered as a bad result.
  - Confidence: 🟢

- [ ] **T-08 — The gh-681 polar provenance chain.**

  ```
  ar   ← ctx["aspect_ratio"];  absent or <= 0 ⇒ hard stop (all four None)
  ld   ← polar_by_config.clean.ld_max            (empirical, gh-636); <= 0 ⇒ None
  cd0  ← polar_by_config.clean.cd0  →  ctx["cd0"]
  e    ← polar_by_config.clean.e_oswald → ctx["e_oswald"]
  ```

  - Legacy origin: `:130-165`
  - Definition of done: with the parabolic fit rejected (clean polar `cd0`/`e`
    are `None`) the axes still compute from the top-level context keys; with the
    aspect ratio missing every polar-derived axis is `missing`.
  - Confidence: 🟢

- [ ] **T-09 — The seven axis calculators.**
  Implement each per the table in [`design.md`](design.md) §The seven Ist axes,
  with the exact `formula` strings — they are user-visible in the side drawer.
  `glide` prefers the empirical `ld_max` and falls back to
  `0.5·√(π·e·AR/CD0)`; `climb` uses the closed form
  `(3·π·e·AR)^0.75 / (4·CD0^0.25)`; `wing_loading` uses `g = 9.81`;
  `maneuver` reads `flight_envelope_n_max` (accepting `int` or `float`, `> 0`).
  - Legacy origin: `:108-283`
  - Definition of done: each calculator is unit-tested in isolation; every axis
    returns `missing` rather than a fabricated number when an input is absent;
    the closed-form climb value matches a numeric maximisation of `CL^1.5/CD`
    over the same parabolic polar to within 1 %.
  - Confidence: 🟢

- [ ] **T-10 — `field_friendliness` and its degradation ladder.**
  Import `compute_field_lengths_for_aeroplane` at **module level** inside a
  `try/except ImportError` so the symbol exists for both runtime and
  `unittest.mock.patch`. Then:

  ```
  symbol is None or ImportError at call → missing, "Field-length service
                                          unavailable on this platform"
  ServiceException                      → missing, warning = exc.message
  any other exception                   → PROPAGATES (a bug, not a user condition)
  eff = max(s_to_50ft_m, s_ldg_50ft_m); eff <= 0 → missing
  score = clip(target_field_length_m / eff, 0, 1)
  ```

  Always pass `db` so the `MissionObjective` lookup stays in the caller's
  session.
  - Legacy origin: `:288-353`
  - Definition of done: a missing `t_static_N` yields `missing` with the
    service's own remediation sentence; an unexpected `TypeError` inside the
    field-length service reaches the endpoint's logging handler instead of being
    swallowed; the patched-symbol test works.
  - Confidence: 🟢

- [ ] **T-11 — The gh-767 Soll polygon.**
  `_objective_target_scores(objective, axis_ranges)` mapping the six numeric
  targets through the **same** `_normalise_score` and the **same**
  `axis_ranges` as the matching Ist axis, with
  `field_friendliness = 1.0` by construction.
  - Legacy origin: `:359-395`
  - Definition of done: raising `target_glide_ld` moves the white Soll line
    without touching the preset row; the `field_friendliness` Soll score is
    `1.0` for every mission and every target value.
  - Confidence: 🟢

- [ ] **T-12 — The aggregator.**
  Resolve `ids = missions or [objective.mission_type]`; primary preset
  `presets[ids[0]]` → `presets["trainer"]` → **raise `RuntimeError`**; mass from
  `ctx["mass_kg"]` (`> 0`) else `aeroplane.total_mass_kg` else `None`; build the
  seven Ist axes against the primary's ranges; build one
  `MissionTargetPolygon` per **resolvable** id, using the objective-derived
  scores for `objective.mission_type` and the static polygon otherwise; stamp
  `active_mission_id = ids[0]`, `computed_at` (ISO-8601 UTC) and
  `context_hash = sha256(json.dumps(ctx, sort_keys=True, default=str))`.
  - Legacy origin: `:398-499`
  - Definition of done: an unknown primary id returns 200 with the trainer
    ranges and the requested id echoed; unknown overlay ids are dropped; an
    empty preset table is a 500 naming the seed; `context_hash` is exactly 64
    characters and stable for an unchanged context.
  - 🟡 The hash is emitted but never consumed server-side — wire it to a cache
    or drop it.
  - Confidence: 🟢

- [ ] **T-13 — Log-forging safety on the mission id.**
  The empty-preset-table log record must **not** interpolate the
  user-controlled mission id; the client receives it through the exception
  message instead.
  - Legacy origin: `:432-447`
  - Definition of done: a mission id containing a newline cannot inject a log
    record.
  - Confidence: 🟢

- [ ] **T-14 — The transport layer.**
  The four routes of [`../contracts.md`](../contracts.md) §B, with
  `_resolve_aeroplane_id` raising a 404 for an unknown UUID and `missions` as a
  repeatable query parameter defaulting to an empty list.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/mission_objectives.py`
  - Definition of done: `GET /mission-presets` needs no aeroplane; the three
    aeroplane-scoped routes 404 on an unknown UUID; `missions` accepts zero, one
    or many values.
  - 🟡 These four handlers have **no** domain-exception mapper at all — they
    rely on the raw `HTTPException` from `_resolve_aeroplane_id` and on
    FastAPI's default 500. Align with whatever [`../tasks.md`](../tasks.md) T-17
    settles on.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Objective bounds.** `target_stall_safety` 0.9 ⇒ 422;
      `target_maneuver_n` 0.5 ⇒ 422; `landing_safety_factor` 0.5 and 3.5 ⇒ 422;
      all three landing inputs absent ⇒ accepted.
- [ ] **TT-02 — `LandingSurface` ↔ `LANDING_SURFACE_MU` parity.** The literal's
      six members equal the μ table's keys exactly (a set comparison, so a
      rename on either side fails the build).
- [ ] **TT-03 — Non-persisting default.** A GET on a fresh aeroplane returns the
      twelve defaults and leaves the table empty; two reads are independent
      objects.
- [ ] **TT-04 — Python defaults match the column server-defaults.**
- [ ] **TT-05 — Upsert cardinality.** Two PUTs ⇒ one row.
- [ ] **TT-06 — Preset applied on the first create** (old value `None`).
- [ ] **TT-07 — Preset not re-applied** when `mission_type` is unchanged, even
      though other fields changed.
- [ ] **TT-08 — Estimates only.** After a switch to `sailplane`, all five
      parameters' `calculated_value`, `calculated_source` and `active_source`
      are unchanged, and only `estimate_value` moved.
- [ ] **TT-09 — Missing assumption row is created** with the preset value and
      `active_source = "ESTIMATE"`.
- [ ] **TT-10 — Unknown `mission_type`** — pin today's silent 200 with no
      change, and flip the assertion when T-04's rejection lands.
- [ ] **TT-11 — No fan-out on a preset write.** A mocked `event_bus` records
      zero publications and no OP becomes `DIRTY` — pin, then revisit with T-04.
- [ ] **TT-12 — Nine presets, seven axes.** Every preset's `target_polygon` and
      `axis_ranges` key sets equal the seven `AxisName` values.
- [ ] **TT-13 — `power_to_weight` units.** Assert the intended unit per preset
      (the gh-580/gh-582 regressions already pin `0.0` for the two gliders and
      `100.0` for `motor_glider`); extend to all nine once T-05's conversion is
      decided.
- [ ] **TT-14 — Seeding idempotence** and no overwrite of an edited row.
- [ ] **TT-15 — `axis_ranges` round-trip** list ↔ tuple through the DB.
- [ ] **TT-16 — `_normalise_score`.** Below-range ⇒ 0.0; above ⇒ 1.0; midpoint ⇒
      0.5; `hi == lo` ⇒ 0.0.
- [ ] **TT-17 — `_ctx_get` rejects zero, negatives, strings and `None`.**
- [ ] **TT-18 — Cold start is seven holes.** Empty context ⇒ seven axes with
      `provenance="missing"` and `null` value/unit/score, each still carrying its
      range.
- [ ] **TT-19 — Polar provenance chain (gh-681).** With `polar_by_config.clean`
      rejected (`cd0`/`e` null) the glide and climb axes still compute from the
      top-level context; with `aspect_ratio` absent both are `missing`.
- [ ] **TT-20 — Glide prefers `ld_max`.** With both available the empirical
      value wins; without it the formula is used.
- [ ] **TT-21 — Climb closed form** matches a numeric maximisation of
      `CL^1.5/CD` over the same parabolic polar to within 1 %.
- [ ] **TT-22 — `wing_loading`** equals `m·g/S_ref` with `g = 9.81`; a zero
      `s_ref_m2` is a hole.
- [ ] **TT-23 — `field_friendliness` ladder.** Service `None` ⇒ platform
      message; `ServiceException` ⇒ its message; `eff <= 0` ⇒ hole; any other
      exception propagates.
- [ ] **TT-24 — Soll tracks the objective (gh-767).** Raising
      `target_glide_ld` raises the active mission's Soll glide score; the preset
      row is untouched; an overlay mission keeps its static polygon.
- [ ] **TT-25 — `field_friendliness` Soll is always 1.0.**
- [ ] **TT-26 — Unknown primary id** ⇒ 200, trainer ranges, requested id echoed;
      unknown overlay ids dropped.
- [ ] **TT-27 — Empty preset table ⇒ 500** with an operator message; the mission
      id does not appear in the log record.
- [ ] **TT-28 — No solver.** With `AeroBuildup` patched to raise, the KPI set is
      still produced and the mock is never called.
- [ ] **TT-29 — `context_hash`** is 64 characters and stable across two calls on
      an unchanged context.
- [ ] **TT-30 — Fast tier.** The whole KPI path (bar
      `field_friendliness`, which is mocked) runs without AeroSandbox installed.

## Data Migration Tasks

- [ ] **TM-01 — `mission_objectives`.** `aeroplane_id` FK **UNIQUE**, INDEXED,
      `ON DELETE CASCADE`; twelve NOT NULL columns with the server defaults of
      `_default_objective`; three nullable gh-477 landing columns.
      🟢 Decided (`Q-CC-7`): add the FK to `mission_presets.id`
      (and decide the on-delete behaviour for a preset that is still selected).
- [ ] **TM-02 — `mission_presets`.** **String** primary key; `label`,
      `description` (default `""`); `target_polygon`, `axis_ranges`,
      `suggested_estimates` as JSON. Ship the nine rows as a **data migration**
      as well as a runtime seed, because the KPI endpoint 500s on an empty
      table.
- [ ] **TM-03 — Field-performance migration (gh-548).**
      `available_runway_m`, `runway_type`, `t_static_N` and `takeoff_mode`
      moved **out of** `design_assumptions` into `mission_objectives`.
      🟡 The `t_static_N` **assumption still exists** and is still read by the
      matching chart while the field-length endpoint reads the objective.
      Decide which is authoritative and backfill the loser.

## Suggested Order

1. **T-01, T-02** first — the schema and the default are what every other task
   reads.
2. **T-05, T-06** (the preset library) before **T-03, T-04**, which look presets
   up.
3. **T-03 → T-04** together: change detection and the writer are one behaviour.
4. **T-07 → T-09** are pure and independent of the objective work; build them in
   parallel.
5. **T-10** after T-07 (it returns `_missing`) and after the field-length
   service exists.
6. **T-11 → T-12** last among the services — the aggregator consumes everything.
7. **T-13, T-14** with T-12.

Blocking edges: T-03 ⇠ T-01 · T-04 ⇠ T-05, T-03 · T-06 ⇠ T-05 · T-09 ⇠ T-07,
T-08 · T-10 ⇠ T-07 · T-11 ⇠ T-07 · T-12 ⇠ T-09, T-10, T-11 · T-14 ⇠ T-12.

## Pending Gaps (🔴)

- **`power_to_weight` units (T-05).** Seven presets write 0.5–1.4 into a
  parameter catalogued as W/kg with a 220 default; two write 100.0 W/kg and are
  pinned as W/kg by the gh-580/gh-582 tests. The matching chart's power-loading
  constraint and the `is_glider` test (`P/W ≤ 0`) both read this value. Which
  unit is canonical, and who backfills the existing rows?
- **Unknown `mission_type` (T-04).** Reject with 422, warn, or keep the silent
  no-op? The current docstring defers the decision to the KPI service, which
  also does not reject.
- **No FK from `mission_objectives.mission_type` (TM-01).** The trainer fallback
  in the KPI service exists only because the FK is missing.
- **The preset writer bypasses the assumption service (T-04).** Should a mission
  change publish `AssumptionChanged` for five parameters — and if so, does the
  resulting recompute/retrim storm need a batch mode?
- **Two `t_static_N` sources (TM-03).** The migrated objective column and the
  surviving design assumption can disagree; the field-length endpoint and the
  matching chart read different ones.
- **`wing_loading` axis ranges vs the objective default.** The preset ranges sit
  in a 10–120 band while `target_wing_loading_n_m2` defaults to `412 N/m²` and
  the Ist axis computes N/m². One of the two is in the wrong unit; the code says
  nothing.
- **A degenerate axis range scores `0.0` (T-07)** — an unknown rendered as a bad
  result.
- **`context_hash` (T-12)** is emitted and schema-enforced but never consumed.
- **Two mass sources** — `ctx["mass_kg"]` then `aeroplane.total_mass_kg` — with
  no statement of which is authoritative.
- **The four handlers have no domain-exception mapper (T-14)**, unlike the other
  eight endpoint modules in this cluster.
