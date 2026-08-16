# design-assumptions — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker (🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP).
> Parent: [`../tasks.md`](../tasks.md) T-01 / T-02.
> Contracts: [`../contracts.md`](../contracts.md) §A.

## Prerequisites

- [ ] `platform-core`: `get_db()` owning the transaction boundary (BR-78 /
      ADR 0009 — this service must never call `db.begin()` or `db.commit()`),
      `event_bus` with an `AssumptionChanged(aeroplane_id, parameter_name)`
      event, and a `job_tracker` exposing `schedule_recompute_assumptions(id)`,
      `get_recompute_job(id)`.
- [ ] `aero-analysis`: `invalidation_service.mark_ops_dirty(session,
      aeroplane_id)` and the `AssumptionChanged` routing table.
- [ ] Tables `design_assumptions` and `aircraft_computation_config`, plus the
      `aeroplanes.assumption_computation_context` JSON column.
- [ ] No AeroSandbox dependency — **every task below must be testable in the CI
      fast tier** (ADR 0015).

## Tasks

- [ ] **T-01 — The parameter catalogue.**
  Declare `VALID_PARAMETERS` (the 15-name `Literal`), `PARAMETER_DEFAULTS`,
  `PARAMETER_UNITS` and the 7-member `DESIGN_CHOICE_PARAMS` frozenset, with the
  in-code provenance comments preserved (the RC P/W band for `power_to_weight`,
  pack-level LiPo for `battery_specific_energy_wh_per_kg`, `0.0` = "not set" for
  `battery_capacity_wh` / `motor_continuous_power_w` / `t_static_N`,
  `design_speed_mps` overwritten by `V_md` per gh-935).
  - Legacy origin: `app/schemas/design_assumption.py:11-108`
  - Definition of done: the four structures agree on exactly 15 names; every
    name has a unit entry; `power_to_weight` and `prop_efficiency` are **not**
    design choices (they are user-set now, powertrain-computed later).
  - Confidence: 🟢

- [ ] **T-02 — Divergence, pure.**

  ```python
  compute_divergence_pct(estimate, calculated):
      if calculated is None or calculated == 0:  return None
      return round(abs(estimate - calculated) / abs(calculated) * 100, 1)

  divergence_level(pct):   None|<5 -> "none" · <15 -> "info"
                           <=30 -> "warning" · else -> "alert"
  ```

  - Legacy origin: `app/schemas/design_assumption.py:110-131`
  - Definition of done: both functions are importable without a DB session;
    `est 1.5 / calc 1.8` ⇒ `16.7` / `"warning"`; the denominator is the
    **calculated** value; the 1-decimal rounding is asserted.
  - 🔴 **Deviation to decide:** `calculated == 0` returns `None`, which hides an
    arbitrarily large divergence exactly where a zero is a legitimate value
    (`t_static_N` on a glider, `power_to_weight` on a sailplane preset). Either
    return a sentinel level or make the zero case explicit in the response.
  - Confidence: 🟢

- [ ] **T-03 — The read projection.**
  `_assumption_to_read(model) -> AssumptionRead` materialising
  `effective_value` (calculated when `CALCULATED` **and** non-null, else the
  estimate), `divergence_level`, `unit` from `PARAMETER_UNITS` (default `""`)
  and `is_design_choice`.
  - Legacy origin: `app/services/design_assumptions_service.py:40-64`
  - Definition of done: this is the **only** place the API materialises an
    effective value; no downstream code branches on `active_source`.
  - Confidence: 🟢

- [ ] **T-04 — The single effective-value reader.**
  `get_effective_assumption(db, aeroplane_id: int, param_name) -> float | None`
  with the `PARAMETER_DEFAULTS.get(param_name)` fallback on a missing row.
  - Legacy origin: `app/services/design_assumptions_service.py:66-89`
  - Definition of done: a grep for `query(DesignAssumptionModel)` outside this
    module and the preset writer returns nothing.
  - 🔴 **Deviation required:** delete
    `mass_cg_service.get_effective_assumption_value` (`:112-128`) — a second
    reader keyed by **UUID** that **raises** `NotFoundError` instead of falling
    back. `flight_envelope_service._load_assumptions` already wraps it in a
    `try/except NotFoundError` to restore this function's behaviour; migrate it
    to this one.
  - Confidence: 🟢 for the behaviour, 🔴 for the consolidation

- [ ] **T-05 — Idempotent seeding.**
  `seed_defaults(db, aeroplane_uuid)`: read the existing `parameter_name` set,
  insert only the missing rows with `estimate_value = default` and
  `active_source = "ESTIMATE"`, then insert the `aircraft_computation_config`
  row from `COMPUTATION_CONFIG_DEFAULTS` when absent; `flush`; return
  `list_assumptions(...)`.
  - Legacy origin: `app/services/design_assumptions_service.py:92-127`
  - Definition of done: two consecutive calls leave 15 assumption rows and one
    config row; an already-edited estimate is not reset; the function is safe to
    call from `recompute_assumptions` on **every** run (BR-MS1).
  - Confidence: 🟢

- [ ] **T-06 — `list_assumptions` with `warnings_count`.**
  Count rows whose `divergence_level` is `"warning"` **or** `"alert"`.
  - Legacy origin: `:130-149`
  - Definition of done: three `warning` plus one `alert` ⇒ `warnings_count == 4`.
  - Confidence: 🟢

- [ ] **T-07 — The event gate on an estimate edit (BR-27).**
  Capture `active_was_estimate = row.active_source == "ESTIMATE"` **before** the
  write. Write `estimate_value`, recompute `divergence_pct`, flush + refresh.
  Only when `active_was_estimate`: `mark_ops_dirty` for `{mass, cg_x}`, then
  publish `AssumptionChanged`.
  - Legacy origin: `app/services/design_assumptions_service.py:152-197`
  - Definition of done: editing an estimate under an active `CALCULATED`
    publishes nothing and dirties nothing; editing `cl_max` under `ESTIMATE`
    publishes but dirties no OP; the flag is read before the assignment (a
    refactor that reads it after silently breaks the rule).
  - Confidence: 🟢

- [ ] **T-08 — `switch_source` with both guards and the `cg_x` exclusion.**

  ```
  active_source == "CALCULATED":
      param in DESIGN_CHOICE_PARAMS  → ValidationError
          "Parameter '<name>' is a design choice and cannot use CALCULATED source"
      row.calculated_value is None   → ValidationError
          "No calculated value available for '<name>'"
  write; flush; refresh
  mark_ops_dirty                     iff param in {mass, cg_x}
  event_bus.publish(AssumptionChanged)   ALWAYS
  job_tracker.schedule_recompute_assumptions   iff param != "cg_x"
  ```

  - Legacy origin: `:200-246`
  - Definition of done: all seven design choices 422 on `CALCULATED`; switching
    `cg_x` publishes but schedules **no** recompute (BR-83); switching to the
    value already held still publishes (pin the behaviour, then decide).
  - Confidence: 🟢

- [ ] **T-09 — `update_calculated_value` and the four-fold auto-switch guard.**

  ```
  should_switch = auto_switch_source
                  and row.calculated_value is None
                  and row.active_source == "ESTIMATE"
                  and param_name not in DESIGN_CHOICE_PARAMS
  ```

  Write `calculated_value`, `calculated_source`, recompute `divergence_pct`,
  apply the switch, flush + refresh. **Publish nothing** — the caller owns the
  fan-out.
  - Legacy origin: `:249-304`
  - Definition of done: the first calculated value switches the source; after a
    manual switch back to `ESTIMATE` a second calculated value does **not**;
    a design choice never switches; no event is emitted from this function.
  - 🟡 **Deviation to consider:** nothing stops this function from writing a
    `calculated_value` onto a design choice, so it can display a divergence it
    can never activate. Reject the write, or document it as intentional.
  - Confidence: 🟢

- [ ] **T-10 — The computation-config surface.**
  `ComputationConfigRead` / `ComputationConfigWrite` with the seven fields and
  their bounds (`coarse_alpha_step_deg`, `fine_alpha_margin_deg`,
  `fine_alpha_step_deg` all `gt=0`; `fine_velocity_count` `2…50`;
  `debounce_seconds` `0.5…30`). Both GET and PUT materialise the row from
  `COMPUTATION_CONFIG_DEFAULTS` when absent; the PUT merges with
  `model_dump(exclude_none=True)`.
  - Legacy origin: `app/schemas/computation_config.py`,
    `app/models/computation_config.py:8-16`,
    `app/api/v2/endpoints/aeroplane/design_assumptions.py:261-340`
  - Definition of done: a partial PUT leaves omitted fields untouched; each
    bound produces a 422; a GET on a fresh aircraft returns the defaults and
    leaves a row behind.
  - 🔴 **Deviation required:** add a model validator for
    `coarse_alpha_min_deg < coarse_alpha_max_deg` (and, if the sweep depends on
    it, `fine_alpha_step_deg ≤ fine_alpha_margin_deg`). An inverted range is
    accepted today and yields an empty sweep with no error.
  - Confidence: 🟢

- [ ] **T-11 — The recompute-job surface.**
  `GET …/assumptions/recompute-status` and `POST …/recompute` returning the same
  envelope `{status, started_at, finished_at, error}` — `job.status.value.lower()`,
  ISO-8601 timestamps or `null`, and `{"status": "idle", null, null, null}` when
  no job row exists. The POST schedules the job and answers **202** regardless.
  - Legacy origin: `design_assumptions.py:168-229`
  - Definition of done: the two routes return an identical shape; a POST with no
    event loop still returns 202 with `status: "idle"`.
  - 🟡 The job tracker is in-memory: after a restart the status is `"idle"` even
    if work was in flight. Decide whether that needs persisting.
  - Confidence: 🟢

- [ ] **T-12 — The read-only computation-context route.**
  `GET …/assumptions/computation-context` returning
  `aeroplane.assumption_computation_context` **or `null`** — never a stub, never
  a partially-populated default.
  - Legacy origin: `design_assumptions.py:236-258`
  - Definition of done: a cold-start aircraft returns `null` and the client
    renders "not computed yet" rather than zeros.
  - Confidence: 🟢

- [ ] **T-13 — The transport layer.**
  The nine routes of [`../contracts.md`](../contracts.md) §A with
  `_PARAM_NAME_PATTERN` built at import time from `PARAMETER_DEFAULTS.keys()`,
  the `_raise_http` mapper (404 / 422 / 409 / 500) and the `_call` wrapper that
  converts an unexpected exception into a 500.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/design_assumptions.py:40-102`
  - Definition of done: an unknown parameter name is a **path-level 422** that
    never enters the service; `POST …/assumptions` returns **201**.
  - 🔴 The mapper interpolates the raw exception text into the response body —
    sanitise it, and align the envelope with whatever
    [`../tasks.md`](../tasks.md) T-17 settles on.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Divergence table.** Parametrised over
      `(estimate, calculated) → (pct, level)` including `calculated=None`,
      `calculated=0`, exactly `5`, `15` and `30` % (boundary behaviour:
      `<5` none, `<15` info, `≤30` warning).
- [ ] **TT-02 — Effective value.** `CALCULATED` + non-null ⇒ calculated;
      `CALCULATED` + null ⇒ estimate; `ESTIMATE` ⇒ estimate.
- [ ] **TT-03 — Missing row.** `get_effective_assumption` returns the catalogue
      default; an unknown parameter returns `None`.
- [ ] **TT-04 — Seeding idempotence.** Two calls ⇒ 15 rows + 1 config row; an
      edited estimate survives.
- [ ] **TT-05 — Event gate.** Four cases: `ESTIMATE`+`mass` (publish + dirty),
      `ESTIMATE`+`cl_max` (publish, no dirty), `CALCULATED`+`mass` (nothing),
      `CALCULATED`+`cl_max` (nothing). Assert on a mocked `event_bus` and a
      mocked `mark_ops_dirty`.
- [ ] **TT-06 — `switch_source` always publishes**, in both directions.
- [ ] **TT-07 — `cg_x` schedules no recompute** on `switch_source`; every other
      parameter does (BR-83 regression).
- [ ] **TT-08 — Design choices.** All seven 422 on `CALCULATED`; none of the
      seven auto-switches.
- [ ] **TT-09 — No calculated value ⇒ 422** on an explicit switch.
- [ ] **TT-10 — Auto-switch fires once.** First value switches; manual switch
      back; second value leaves `ESTIMATE`.
- [ ] **TT-11 — `update_calculated_value` is silent.** A mocked `event_bus`
      records zero publications.
- [ ] **TT-12 — `warnings_count`** counts `warning` **and** `alert`.
- [ ] **TT-13 — NaN/Inf estimate ⇒ 422** at the schema level.
- [ ] **TT-14 — Unknown parameter name ⇒ 422** with the service patched to raise
      if entered.
- [ ] **TT-15 — Config bounds.** `fine_velocity_count` 1 and 51 ⇒ 422;
      `debounce_seconds` 0.4 and 30.1 ⇒ 422; each `gt=0` field at 0 ⇒ 422.
- [ ] **TT-16 — Config merge.** A one-field PUT leaves the other six unchanged.
- [ ] **TT-17 — Config materialised on read.** GET on a fresh aircraft returns
      the defaults and a row exists afterwards.
- [ ] **TT-18 — Inverted α range** — pin today's acceptance, then flip the
      assertion when T-10's validator lands.
- [ ] **TT-19 — Recompute envelope.** No job ⇒ `idle` + three nulls; POST ⇒ 202.
- [ ] **TT-20 — Context passthrough.** `null` before the first recompute; the
      stored dict afterwards, unmodified.
- [ ] **TT-21 — Aeroplane 404** on every service entry point.
- [ ] **TT-22 — Fast-tier only.** The whole file imports without AeroSandbox;
      assert via a test that fails if `aerosandbox` appears in
      `sys.modules` after importing the service.

## Data Migration Tasks

- [ ] **TM-01 — `design_assumptions`.** `id` PK autoincrement; `aeroplane_id`
      FK `ON DELETE CASCADE`, INDEXED; `parameter_name` String NOT NULL;
      `estimate_value` Float NOT NULL; `calculated_value`, `calculated_source`,
      `divergence_pct` nullable; `active_source` NOT NULL default `"ESTIMATE"`;
      `updated_at` DateTime(tz) with `now()` + `onupdate`;
      `UniqueConstraint(aeroplane_id, parameter_name)` named
      `uq_assumption_aeroplane_param`.
      🔴 Decide `min_static_margin` / `max_static_margin`: add them to the
      catalogue and backfill, or delete the `stability_service` lookup and
      promote the 5 % / 25 % bounds to named constants.
- [ ] **TM-02 — `aircraft_computation_config`.** `aeroplane_id` FK
      `ON DELETE CASCADE`, INDEXED, plus `uq_computation_config_aeroplane`; the
      seven Float/Integer columns defaulting to `COMPUTATION_CONFIG_DEFAULTS`.
      Backfill one row per existing aeroplane so the "materialise on read"
      behaviour is never needed for legacy data.

## Suggested Order

1. **T-01 → T-04** are pure and have no DB dependency — build and test them
   first; every later task consumes them.
2. **T-05** (seeding) before anything that reads a row.
3. **T-07 → T-09** are the three writers; do them together so the event matrix
   is implemented as one decision table rather than three ad-hoc branches.
4. **T-06, T-10 → T-12** are independent read surfaces and can be built in
   parallel.
5. **T-13** (transport) last.

Blocking edges: T-03 ⇠ T-02 · T-04 ⇠ T-01 · T-05 ⇠ T-01 · T-06 ⇠ T-03 ·
T-07/T-08/T-09 ⇠ T-03, T-05 · T-13 ⇠ everything.

## Pending Gaps (🔴)

- **Two effective-value readers** (T-04). Consolidating them changes
  `flight_envelope_service`'s missing-row behaviour from "raise then catch" to
  "default" — confirm that is intended before deleting the second one.
- **`min_static_margin` / `max_static_margin`** (TM-01) are read by
  `stability_service` but never seeded. Seed, or delete the lookup.
- **A zero calculated value hides the divergence** (T-02). Which is right for
  `t_static_N = 0` on a glider — no divergence, or an explicit "estimate against
  a zero calculation" state?
- **The preset writer bypasses `update_assumption`.** A mission change rewrites
  five estimates directly on the ORM rows, so no `AssumptionChanged` fires even
  when those estimates are the effective values. Should the preset go through
  `update_assumption`, and if so, does the resulting recompute storm need a
  batch mode?
- **A calculated value can be written onto a design choice** (T-09) — guarded on
  the switch only.
- **A no-op `switch_source` still fans out** (T-08). Keep, or make it idempotent?
- **The in-memory job tracker** (T-11) reports `idle` after a restart.
- **The error envelope and the raw-exception interpolation** (T-13) — settled at
  module level in [`../tasks.md`](../tasks.md) T-17.
- **No trace of a suppressed fan-out.** An estimate edit under an active
  `CALCULATED` is silent in the logs too, so "why did my change do nothing?" has
  no server-side answer. Should it log at DEBUG, or return a hint on the
  response?
