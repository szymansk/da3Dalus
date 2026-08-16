# mission-objectives-presets

> Use-case specification, nested under the module
> [`mission-and-sizing`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: mission-and-sizing
> (R4, "Mission objectives and presets"), `_reversa_sdd/data-dictionary.md`
> §`mission_objectives` / §`mission_presets`, `_reversa_sdd/domain.md` §2.4.

## Overview

`mission-objectives-presets` is where the designer says **what the aircraft is
for**. A `mission_type` selects one of nine seeded presets; the preset carries
a Soll polygon on seven comparison axes, the normalisation ranges that put real
numbers on that 0–1 scale, and five suggested design-assumption estimates that
are written into the aircraft the moment the mission changes. Seven editable
performance targets and the field-performance inputs live alongside, one row per
aeroplane. 🟢

The KPI service closes the loop: it reads the cached aero context and reports
where the aircraft *actually* sits on those same seven axes, so the Ist polygon
and the Soll polygon are directly comparable. It runs **no solver** — it is
closed-form on top of data that already exists. 🟢

## Responsibilities

- Hold exactly one `mission_objectives` row per aeroplane, with a default that
  is returned rather than persisted when the row is absent. 🟢
- Apply the selected preset's `suggested_estimates` to
  `design_assumptions.estimate_value` — and to nothing else — whenever
  `mission_type` changes. 🟢
- Seed and expose the nine-preset library idempotently. 🟢
- Compute the seven Ist axes closed-form from the cached context. 🟢
- Build the Soll polygon from the user's own editable targets for the active
  mission, and from the static preset polygon for comparison overlays. 🟢
- Report **why** an axis is unavailable instead of silently zeroing it. 🟢

**Explicitly NOT this use case's responsibility:** producing the context values
the axes read (→ `aero-analysis`), owning the estimate/calculated duality
(→ [`../design-assumptions/`](../design-assumptions/requirements.md)),
computing field lengths (delegated to `field_length_service`), and the matching
chart's per-profile constraint applicability (→ [`../design.md`](../design.md)
§Matching chart, which keys off the same mission ids).

## Business Rules

> Global ids (`BR-*`) are inherited verbatim from
> [`../../domain.md`](../../domain.md); `BR-MS*` from
> [`../requirements.md`](../requirements.md). `BR-MS34`…`BR-MS38` are new,
> discovered while writing this specification.

- **BR-MS3 — One `mission_objectives` row per aeroplane.** 🟢 Unique FK. It
  holds seven performance targets plus the field-performance inputs migrated out
  of assumptions (`available_runway_m`, `runway_type`, `t_static_N`,
  `takeoff_mode`) and the three optional gh-477 landing inputs
  (`landing_surface`, `landing_safety_factor`, `available_field_length_m`).
- **BR-MS4 — Changing `mission_type` rewrites estimates, never calculations.**
  🟢 `upsert_mission_objective` compares the stored `mission_type` with the
  payload's and, when they differ (including on the first create), calls
  `_apply_preset_estimates`, which writes the preset's `suggested_estimates`
  into `design_assumptions.estimate_value` for `g_limit`,
  `target_static_margin`, `cl_max`, `power_to_weight`, `prop_efficiency` —
  **only** `estimate_value`. `calculated_value`, `calculated_source` and
  `active_source` stay owned by `assumption_compute_service`.
  🟢 An unknown `mission_type` fails visibly and the column gains a real reference constraint (`Q-MS-10` / `P-WARN-0`, `Q-CC-7`). Previously a silent no-op: the preset lookup returns
  `None` and the function returns. HTTP 200, no estimate changes, no warning.
  The docstring defers the rejection to the KPI service, which does not reject
  either.
  🟢 The preset writer routes through `update_assumption` so the change fans out (`Q-MS-10`, narrowed); the *whether* is `Q-MS-10b`. Previously the writer created a missing `DesignAssumptionModel` row **directly**,
  bypassing `update_assumption`, so a mission change publishes no
  `AssumptionChanged` and dirties no operating point even when those estimates
  are the effective values.
- **BR-MS5 — Nine seeded presets, seven KPI axes.** 🟢 `SEED_PRESETS` with the
  idempotent `seed_mission_presets`: `trainer`, `sport`, `sailplane`,
  `wing_racer`, `acro_3d`, `stol_bush`, `slope_soarer`, `motor_glider`,
  `flying_wing`. Each carries a `target_polygon` (0–1 per axis), the
  `axis_ranges` used to normalise real values onto that scale, and the
  `suggested_estimates`. Axes: `stall_safety`, `glide`, `climb`, `cruise`,
  `maneuver`, `wing_loading`, `field_friendliness`.
  🟢 A real FK is added (`Q-CC-7`). Previously a free-text `String` PK with no FK
  from `mission_objectives.mission_type`, so the two can drift apart.
- **BR-MS34 — The preset `power_to_weight` values are dimensionally
  inconsistent.** 🟢 W/kg is canonical; the seven T/W-shaped presets are re-authored (`Q-MS-1`, maintainer-answered).

  ```
  design_assumptions catalogue:  power_to_weight  unit "W/kg"  default 220.0
  SEED_PRESETS suggested_estimates.power_to_weight:
      trainer 0.5 · sport 0.7 · sailplane 0.0 · wing_racer 1.0
      acro_3d 1.4 · stol_bush 0.8 · slope_soarer 0.0
      motor_glider 100.0 · flying_wing 100.0
  ```

  Seven of the nine write a dimensionless, T/W-shaped number into a W/kg field;
  the two glider-derived presets (gh-580/gh-582) write real W/kg. Selecting
  `trainer` therefore sets the aircraft's power loading to **0.5 W/kg**, which
  the matching chart's power-loading constraint and the `is_glider` test
  (`P/W ≤ 0`) both consume. The existing tests pin `0.0` and `100.0` as W/kg,
  so the glider presets are the intended reading and the other seven are wrong.
- **BR-MS35 — Preset resolution never fails on a bad id, only on an empty
  table.** 🟢 `compute_mission_kpis` resolves the primary preset as
  `presets[missions[0]]` → `presets["trainer"]` → **raise**. An unknown mission
  id therefore silently normalises against the trainer ranges; a table with
  neither the id nor `trainer` raises a `RuntimeError` (HTTP **500**) rather
  than returning a degenerate empty radar. Unknown ids in the *overlay* list are
  silently dropped. The user-controlled id is deliberately kept out of the log
  line (Sonar S5145) and only echoed in the exception message.
- **BR-MS36 — The Soll polygon for the user's own mission comes from their
  editable targets, not from the preset (gh-767).** 🟢 For
  `mid == objective.mission_type` the scores are
  `_objective_target_scores(objective, preset.axis_ranges)` — each target
  normalised through the **same** `_normalise_score` and the **same**
  `axis_ranges` as the matching Ist axis, so the white Soll line tracks live
  edits and stays directly comparable to the orange Ist polygon. Comparison
  overlays keep their static `target_polygon`.
  🟢 `field_friendliness` is special: its Ist axis is an *achievement ratio*
  (`target_field_length_m / effective`), not a range-normalised physical value,
  so meeting the declared target is full score by construction — the Soll score
  is hard-coded `1.0`.
- **BR-MS37 — A missing axis is a hole with a reason, not a zero.** 🟢 Every
  `_kpi_*` calculator returns `provenance="missing"` with `value`, `unit` and
  `score_0_1` all `None` when its inputs are absent; the radar renders a polygon
  gap. `field_friendliness` additionally carries the user-facing cause in
  `warning` (e.g. *"Set t_static_N…"*), taken from the `ServiceException`
  message. `_ctx_get` treats **zero and negative** context values as absent,
  because none of the consumed quantities is physically non-positive.
  🟡 A degenerate `axis_range` (`hi <= lo`) collapses the score to `0.0` rather
  than to `None` — the one place a missing answer is reported as a bad one.
- **BR-MS38 — The KPI set is closed-form; only one axis leaves the module.** 🟢
  Six axes are pure functions of the cached context plus the objective.
  `field_friendliness` delegates to `field_length_service`, is the only axis
  that can raise, and degrades to `missing` on `ImportError` (the service is
  unavailable on platforms without AeroSandbox) or on any `ServiceException`.
  Anything else propagates — an unexpected exception is a bug, not a
  user-actionable condition.
- **BR-14 — Everything reads the single-source context.** 🟢 The Ist axes read
  `v_cruise_mps`, `v_s1_mps`, `aspect_ratio`, `cd0`, `e_oswald`,
  `polar_by_config.clean.{ld_max, cd0, e_oswald}`, `flight_envelope_n_max`,
  `s_ref_m2` and `mass_kg`. None of them re-derives a polar.
- **BR-MS-open — `context_hash` is a cache key with no cache.** 🟡 The response
  carries a 64-character SHA-256 of the context dict
  (`json.dumps(ctx, sort_keys=True, default=str)`), constrained
  `min_length=64, max_length=64` on the schema, but nothing server-side stores
  or compares it.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Return the persisted objective, or a fresh default instance | Must | No row ⇒ the twelve documented defaults, and no row is created |
| RF-02 | Never share the default object between callers | Must | Two GETs return independent instances |
| RF-03 | Upsert exactly one row per aeroplane | Must | A second `PUT` updates rather than inserts |
| RF-04 | Apply the preset estimates when `mission_type` changes | Must | Including on the first create, when the previous value is `None` |
| RF-05 | Do not re-apply when `mission_type` is unchanged | Must | A `PUT` that only edits `target_cruise_mps` leaves the estimates alone |
| RF-06 | Write `estimate_value` only | Must | `calculated_value`, `calculated_source` and `active_source` are byte-identical afterwards |
| RF-07 | Create a missing assumption row when applying a preset | Should | A parameter absent from `design_assumptions` is inserted with the preset value |
| RF-08 | Validate the objective's field bounds | Must | `target_stall_safety = 0.9` ⇒ 422; `landing_safety_factor = 0.5` ⇒ 422 |
| RF-09 | Accept the three gh-477 landing inputs as optional | Must | All absent ⇒ grass-short / 1.5 / no sufficiency check |
| RF-10 | Seed the nine presets idempotently | Must | Two calls leave nine rows; existing rows are untouched |
| RF-11 | List the nine presets with tuple-typed `axis_ranges` | Must | `GET /mission-presets` returns 9, each with 7 axes on both JSON blobs |
| RF-12 | Compute seven Ist axes on every request | Must | `ist_polygon` always has exactly seven keys |
| RF-13 | Normalise through the **primary** preset's ranges | Must | The active mission's ranges drive the Ist scores |
| RF-14 | Report a missing axis as `provenance="missing"` with `null` value/score | Must | A cold-start aircraft returns seven `missing` axes, not seven zeros |
| RF-15 | Carry the user-facing cause on a missing `field_friendliness` | Should | Missing `t_static_N` ⇒ `warning` names it |
| RF-16 | Treat zero and negative context values as absent | Must | `s_ref_m2 = 0` ⇒ `wing_loading` is `missing`, not a division by zero |
| RF-17 | Build the active mission's Soll polygon from the objective (gh-767) | Must | Editing `target_glide_ld` moves the white line without a re-seed |
| RF-18 | Keep the static polygon for comparison overlays | Must | A second mission id in `missions` uses its own `target_polygon` |
| RF-19 | Score `field_friendliness` Soll at 1.0 by construction | Must | Independent of the declared target value |
| RF-20 | Drop unknown overlay ids silently, fall back to `trainer` for the primary | Should | `missions=["spaceplane"]` ⇒ trainer ranges, `active_mission_id="spaceplane"` |
| RF-21 | Fail loudly when the preset table is empty | Must | 500 with a message naming the missing id and the seed |
| RF-22 | Issue no solver call | Must | A mocked `AeroBuildup` is never invoked |
| RF-23 | Return a 64-character `context_hash` | Should | Stable for an unchanged context |
| RF-24 | Never log the user-controlled mission id | Must | Sonar S5145 |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Performance | The KPI set is closed-form on cached data — no AeroBuildup re-run | `mission_kpi_service` module docstring | 🟢 |
| Performance | Six of seven axes are pure arithmetic; only `field_friendliness` calls another service | `_kpi_*` functions | 🟢 |
| Correctness | Preset application touches `estimate_value` exclusively | `_apply_preset_estimates` | 🟢 |
| Correctness | Ist and Soll are normalised through the same function and the same ranges, so the two polygons are comparable | `_normalise_score`, `_objective_target_scores` | 🟢 |
| Correctness | Non-positive context values are rejected rather than divided by | `_ctx_get` | 🟢 |
| Robustness | An unresolvable primary mission degrades to `trainer` instead of failing | `compute_mission_kpis` | 🟢 |
| Robustness | An empty preset table fails **loudly** rather than returning an unrenderable radar | same, `RuntimeError` | 🟢 |
| Robustness | `field_length_service` unavailability (no AeroSandbox) degrades one axis, not the response | `try: from … import` / `ImportError` | 🟢 |
| Robustness | The parabolic-fit provenance chain survives a rejected fit (gh-681) | `_resolve_polar_inputs` | 🟢 |
| Security | The user-controlled mission id is kept out of the log record | `compute_mission_kpis` logger call | 🟢 |
| Observability | Every axis carries its `formula` string for the UI side-drawer | `MissionAxisKpi.formula` | 🟢 |
| Observability | Every axis carries `provenance` and the range it was normalised against | same | 🟢 |
| Auditability | `computed_at` and a 64-char `context_hash` accompany every KPI set | `MissionKpiSet` | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Mission objectives

  Scenario: A missing row yields the default without persisting it
    Given an aeroplane with no mission objective
    When I GET the mission objectives
    Then mission_type is "trainer"
    And target_cruise_mps is 18.0
    And no mission_objectives row exists afterwards

  Scenario: The default is not a shared singleton
    Given two aeroplanes with no mission objective
    When I read both defaults and mutate one
    Then the other is unaffected

  Scenario: Upsert is idempotent in cardinality
    When I PUT mission objectives twice
    Then exactly one row exists for the aeroplane

Feature: Preset estimates

  Scenario: Changing the mission rewrites estimates only
    Given an aircraft with cl_max calculated 1.32 and active_source CALCULATED
    When I set mission_type to "sailplane"
    Then the cl_max estimate becomes 1.3
    And the calculated value is still 1.32
    And active_source is still CALCULATED

  Scenario: The first create applies the preset
    Given an aeroplane with no mission objective
    When I PUT mission_type "acro_3d"
    Then the target_static_margin estimate becomes 0.0
    And the g_limit estimate becomes 8.0

  Scenario: An unchanged mission does not re-apply
    Given a mission objective with mission_type "trainer" and an edited g_limit estimate of 4.2
    When I PUT the same objective with a new target_cruise_mps
    Then the g_limit estimate is still 4.2

  Scenario: An unknown mission type does nothing
    When I set mission_type to "spaceplane"
    Then the response status is 200
    And no estimate changes
    And no warning is returned
    # 🟢 rejects unknown mission_type (Q-MS-10 / P-WARN-0)

  Scenario: A preset write does not fan out
    Given mass and cl_max with active_source ESTIMATE
    When the mission changes
    Then no AssumptionChanged is published
    And no operating point becomes DIRTY
    # 🟢 routes through update_assumption (Q-MS-10)

Feature: Preset library

  Scenario: Nine presets, seven axes each
    When I GET /mission-presets
    Then nine presets are returned
    And each has seven target_polygon keys and seven axis_ranges keys

  Scenario: Seeding is idempotent
    When seed_mission_presets runs twice
    Then nine rows exist
    And an externally edited label is not overwritten

Feature: Mission KPIs

  Scenario: Seven axes, always
    Given any aeroplane
    When I GET the mission KPIs
    Then ist_polygon has exactly seven axes

  Scenario: A cold start is holes, not zeros
    Given an aeroplane with no computation context
    Then every axis has provenance "missing"
    And value, unit and score_0_1 are null

  Scenario: A zero reference area is a hole
    Given a context with s_ref_m2 of 0
    Then wing_loading has provenance "missing"
    And no division is attempted

  Scenario: Glide prefers the empirical maximum
    Given a clean polar with ld_max 18.4 and cd0/e/AR that imply 21.0
    Then the glide axis value is 18.4
    But with ld_max absent it is 0.5·sqrt(pi·e·AR/cd0)

  Scenario: Climb energy uses the closed form
    Given cd0 0.03, e 0.85 and AR 8
    Then the climb axis value is (3·pi·e·AR)^0.75 / (4 · cd0^0.25)

  Scenario: Scores clip to the range
    Given an axis range of 5 to 18 and a value of 22
    Then score_0_1 is 1.0

  Scenario: The active mission's Soll line follows the user's targets
    Given mission_type "trainer" and target_glide_ld 12.0
    When I raise target_glide_ld to 16.0
    Then the trainer target polygon's glide score rises
    And the trainer preset row is unchanged

  Scenario: An overlay keeps its static polygon
    Given missions=["trainer", "sailplane"] and mission_type "trainer"
    Then the trainer polygon comes from the objective
    And the sailplane polygon comes from the preset row

  Scenario: Field friendliness is full score by construction
    Then the Soll score for field_friendliness is 1.0 for every mission

  Scenario: A missing field-length input explains itself
    Given an aeroplane with t_static_N 0 on a powered runway mode
    Then field_friendliness has provenance "missing"
    And its warning names the missing input

  Scenario: An unknown primary mission falls back to trainer
    When I request missions=["spaceplane"]
    Then the response status is 200
    And active_mission_id is "spaceplane"
    And the Ist axes are normalised against the trainer ranges

  Scenario: An empty preset table is a 500
    Given the mission_presets table is empty
    When I GET the mission KPIs
    Then the response status is 500
    And the message tells the operator to run the seed

  Scenario: No solver runs
    Given AeroBuildup is patched to raise
    When I GET the mission KPIs
    Then seven axes are returned
    And AeroBuildup was never called
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| One objective row per aeroplane with a non-persisting default (RF-01…RF-03) | Must | The entry point for design intent; a persisted default would masquerade as a user choice |
| Estimates-only preset application (RF-04…RF-06) | Must | BR-MS4; touching `calculated_value` would let a mission switch silently overwrite physics |
| Idempotent seeding (RF-10) | Must | Runs at startup and in test fixtures |
| Seven axes, always (RF-12) | Must | The radar cannot render a variable axis set |
| Missing-as-hole with a cause (RF-14, RF-15, RF-16) | Must | A zero on a radar reads as "bad", not "unknown" — the opposite of the truth |
| Same normalisation for Ist and Soll (RF-13, RF-17) | Must | gh-767; two polygons on different scales are worse than one |
| Loud failure on an empty preset table (RF-21) | Must | The alternative is an unrenderable radar with no diagnosis |
| No solver call (RF-22) | Must | The KPI panel is a read view; a solver call here would make every page load a compute |
| Field bounds on the objective (RF-08) | Must | `target_stall_safety < 1` is physically meaningless |
| Static overlays (RF-18, RF-19) | Should | The comparison feature on top of the working single-mission view |
| Preset listing (RF-11) | Must | Drives the mission picker |
| Trainer fallback for an unknown primary (RF-20) | Should | Degradation; the correct fix is the missing FK |
| `context_hash` (RF-23) | Could | Emitted, never consumed server-side |
| Rejecting an unknown `mission_type` | **Must** | 🟢 decided (`Q-MS-10`, `P-WARN-0`) |
| A real FK from `mission_objectives.mission_type` | **Must** | 🟢 decided (`Q-CC-7`) |
| Fixing the preset `power_to_weight` units | **Must** | 🟢 decided (`Q-MS-1`); seven presets wrote 0.5–1.4 into a W/kg field |
| Publishing `AssumptionChanged` from the preset writer | **Must** | 🟢 the write routes through `update_assumption` (`Q-MS-10`); whether it fans out is `Q-MS-10b`. Previously a mission change is invisible to the invalidation chain |
| Writing `calculated_value` from a preset | Won't | BR-MS4 |
| Re-running a solver to build the radar | Won't | BR-MS38 |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/models/mission_objective.py` | `MissionObjectiveModel` (`:9`) — unique FK | 🟢 |
| `app/models/mission_preset.py` | `MissionPresetModel` (`:8`) — String PK | 🟢 |
| `app/schemas/mission_objective.py` | `MissionObjective`, `MissionPreset`, `MissionPresetEstimates`, `RunwayType`, `TakeoffMode`, `LandingSurface` | 🟢 |
| `app/schemas/mission_kpi.py` | `AxisName`, `Provenance`, `MissionAxisKpi`, `MissionTargetPolygon`, `MissionKpiSet` | 🟢 |
| `app/services/mission_objective_service.py` | `_default_objective`, `get_mission_objective`, `upsert_mission_objective`, `_apply_preset_estimates`, `list_mission_presets`, `seed_mission_presets` | 🟢 |
| `app/services/mission_preset_seed.py` | `SEED_PRESETS` — nine entries | 🟢 |
| `app/services/mission_kpi_service.py` | `_normalise_score`, `_missing`, `_ctx_get`, `_resolve_polar_inputs`, the seven `_kpi_*`, `_compute_field_length_score`, `_objective_target_scores`, `_hash_context`, `compute_mission_kpis` | 🟢 |
| `app/services/field_length_service.py` | `compute_field_lengths_for_aeroplane` — the only external call | 🟢 |
| `app/api/v2/endpoints/aeroplane/mission_objectives.py` | `get_objectives`, `put_objectives`, `get_presets`, `get_kpis` | 🟢 |
