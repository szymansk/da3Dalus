# mission-and-sizing — Implementation Tasks

> Executable sequence to re-implement the module from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker (🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP).
> Nested use cases carry their own task lists:
> [`design-assumptions`](design-assumptions/tasks.md) ·
> [`mission-objectives-presets`](mission-objectives-presets/tasks.md) ·
> [`operating-point-sweep`](operating-point-sweep/tasks.md) ·
> [`flight-envelope`](flight-envelope/tasks.md).
> The tasks below are the **module-level** work: the surfaces those four use
> cases do not own (loading scenarios, CG envelope, matching chart, field
> lengths, SM sizing, forward CG) plus the transport layer and the cross-cutting
> invariants.

## Prerequisites

- [ ] **`platform-core`**: `get_db()` owning the transaction boundary (BR-78 /
      ADR 0009), the event bus (`AssumptionChanged`, `GeometryChanged`), and the
      debounced `job_tracker` with `schedule_recompute_assumptions` +
      `get_recompute_job`.
- [ ] **`aero-analysis`**: `recompute_assumptions` writing
      `aeroplanes.assumption_computation_context`. Every read surface in this
      module consumes that context (BR-14) — none of them may re-derive
      `cd0` / `e` / `L-D` / `x_np`.
- [ ] **`mass-and-balance`**: `compute_cg_agg_for_aeroplane`,
      `aggregate_weight_items`, and the component tree that loading scenarios
      override.
- [ ] **`wing-design`** + **`fuselage-design`**: able to produce an
      `asb.Airplane` (`aeroplane_service.get_aeroplane_airplane_configuration`)
      and to report TED roles + hinge limits.
- [ ] **AeroSandbox ≥ 4.0.7** — only for the operating-point trim solve and the
      `b_ref` lookup in `flight_envelope_service._get_b_ref`. Every other
      surface in this module is closed-form.
- [ ] Tables: `design_assumptions`, `aircraft_computation_config`,
      `mission_objectives`, `mission_presets`, `rc_flight_profiles`,
      `loading_scenarios`, `flight_envelopes`, plus the
      `aeroplanes.assumption_computation_context` and
      `aeroplanes.flight_profile_id` columns.
- [ ] A seeded `mission_presets` table — `compute_mission_kpis` raises a
      `RuntimeError` (HTTP 500) when it is empty.

## Tasks

- [ ] **T-01 — Assumption catalogue + the effective-value read.**
  Implement `VALID_PARAMETERS` (15 names), `PARAMETER_DEFAULTS`,
  `PARAMETER_UNITS`, `DESIGN_CHOICE_PARAMS` (7 names) and the single reader
  `get_effective_assumption(db, aeroplane_id, param) -> float | None`:
  `calculated_value` when `active_source == "CALCULATED"` **and** it is
  non-null, else `estimate_value`; on a missing row fall back to
  `PARAMETER_DEFAULTS.get(param)`.
  - Legacy origin: `app/schemas/design_assumption.py:11-108`,
    `app/services/design_assumptions_service.py:66-89`
  - Definition of done: this is the **only** function in the codebase that reads
    `DesignAssumptionModel` for a value; a grep for
    `query(DesignAssumptionModel)` outside the assumptions service and the
    preset writer returns nothing.
  - Confidence: 🟢
  - Detail: [`design-assumptions/tasks.md`](design-assumptions/tasks.md)

- [ ] **T-02 — The ESTIMATE/CALCULATED duality, the event gate and the loop
      breaker.**
  Implement `seed_defaults` (idempotent, also seeds the computation config),
  `update_assumption`, `switch_source`, `update_calculated_value` and the
  divergence ladder exactly as BR-24…BR-27 and BR-83 describe.
  - Legacy origin: `app/services/design_assumptions_service.py:92-304`
  - Definition of done: editing an estimate under an active `CALCULATED`
    publishes nothing; `switch_source` always publishes and schedules a
    recompute for every parameter **except `cg_x`**; a design choice can never
    be switched to `CALCULATED`; a second calculated value never re-triggers the
    auto-switch.
  - Confidence: 🟢
  - Detail: [`design-assumptions/tasks.md`](design-assumptions/tasks.md)

- [ ] **T-03 — Mission objectives, the nine presets and the KPI spider.**
  One `mission_objectives` row per aeroplane; `_apply_preset_estimates` writing
  `estimate_value` **only**; `seed_mission_presets` idempotent over
  `SEED_PRESETS`; the seven closed-form KPI axes normalised through the primary
  preset's `axis_ranges`.
  - Legacy origin: `app/services/mission_objective_service.py`,
    `app/services/mission_preset_seed.py`,
    `app/services/mission_kpi_service.py`
  - Definition of done: a preset switch leaves `calculated_value`,
    `calculated_source` and `active_source` byte-identical; the KPI service
    issues **no** solver call.
  - Confidence: 🟢
  - Detail: [`mission-objectives-presets/tasks.md`](mission-objectives-presets/tasks.md)

- [ ] **T-04 — The global flight-profile library and the `V_md` substitution.**
  CRUD with a unique `name`, **409** on deleting an assigned profile,
  assign/detach per aeroplane, `_default_profile()`, and
  `_load_effective_flight_profile` returning `(dict, source_profile_id | None)`
  where the `None` drives `user_set_cruise = False` ⇒ cruise speed becomes
  `V_md` with `v_cruise_auto = True` (BR-MS7).
  - Legacy origin: `app/services/flight_profile_service.py`,
    `app/api/v2/endpoints/flight_profiles.py`,
    `operating_point_generator_service._load_effective_flight_profile` (`:287`)
  - Definition of done: an unassigned aircraft cruises at `v_md_mps` with
    `v_cruise_auto = true`; deleting an assigned profile returns 409; the
    `v_max` fallback is `max(1.35·V_cruise, V_cruise + 8)`.
  - 🟢 **`n` becomes derived from bank and climb angle (`n = cos γ/cos φ`), with explicit overrides carrying a `DesignWarning`** (`Q-MS-13 ①`). Storing both was two producers of one number (ADR 0022), and create-only validation was the worst of both worlds. Previously the validator
    exists only on `RCFlightProfileCreate`. Add it to `RCFlightProfileUpdate`,
    or a PATCH can leave the profile self-inconsistent.
  - 🟡 The handler docstrings are German; translate them — they are the OpenAPI
    descriptions of an English-only product.
  - Confidence: 🟢

- [ ] **T-05 — The 15-target operating-point sweep.**
  Target definitions, reference speeds, flap clipping, capability gating, the
  two-stage trim, turn feasibility, persistence and the SSE/process-pool
  streaming path.
  - Legacy origin: `app/services/operating_point_generator_service.py`
  - Definition of done: see
    [`operating-point-sweep/tasks.md`](operating-point-sweep/tasks.md).
  - Confidence: 🟢

- [ ] **T-06 — The V-n envelope, the Pratt-Walker gust envelope and the six
      KPIs.**
  - Legacy origin: `app/services/flight_envelope_service.py`
  - Definition of done: see
    [`flight-envelope/tasks.md`](flight-envelope/tasks.md).
  - Confidence: 🟢

- [ ] **T-07 — Loading scenarios and the four override types.**
  `compute_scenario_cg` over a per-component list with toggles
  (`enabled=False` removes the component), mass overrides, position overrides
  and additive adhoc items, falling back to a `base_mass_kg / base_cg_x`
  aggregation for pre-migration aeroplanes. CRUD with 201/204 and the
  `is_default` flag that supplies `cg_agg_m`.
  - Legacy origin: `app/services/loading_scenario_service.py`,
    `app/api/v2/endpoints/aeroplane/loading_scenarios.py`,
    `app/schemas/loading_scenario.py`
  - Definition of done: a toggle removes exactly one component from the
    aggregation and nothing else; an adhoc item adds mass at its own `(x, y, z)`;
    a mass override does not move the component; creating a scenario marks every
    OP `DIRTY`.
  - 🟢 **`component_uuid` is validated at write time** (`Q-MS-13 ③`); a referenced component cannot be deleted, only changed (`Q-PT-7`), so a dangling override can no longer arise. Previously unvalidated: an override
    naming a deleted component is accepted and silently does nothing — either
    reject it with 422 or report it in `warnings`.
  - Confidence: 🟢

- [ ] **T-08 — The CG envelope, the SM ladder and the stability-envelope
      override.**

  ```
  cg_loading_fwd_m = min(cg_x over all scenarios)
  cg_loading_aft_m = max(cg_x over all scenarios)

  compute_stability_envelope(x_np, mac, target_sm):
      cg_stability_aft_m = x_np − target_sm · MAC
      cg_stability_fwd_m = x_np − 0.30 · MAC        ← conservative STUB

  classification (Scholz §4.2, loading_scenario_service.py:51-53):
      sm < 0.02        → "error"   (Phugoid divergent)
      sm < target_sm   → "warn"
      sm ≤ 0.20        → "ok"
      sm ≤ 0.30        → "warn"    (heavy nose, trim drag)
      else             → "error"   (elevator authority)
      x_np / MAC absent → "unknown", SM values None (never a stub)

  invariant: cg_loading_aft_m ≤ cg_stability_aft_m
  ```

  `recompute_assumptions` overrides the forward stub with
  `elevator_authority_service.compute_forward_cg_limit` (gh-500); on failure the
  stub is kept and `forward_cg_result` is stored either way. A `ValueError`
  mentioning `x_np=None` / `mac=None` is demoted to **INFO** — the documented
  cold-start chicken-and-egg (gh-685), not a bug.
  - Legacy origin: `app/services/loading_scenario_service.py:51-53`,
    `compute_stability_envelope`, `app/services/elevator_authority_service.py`
  - Definition of done: `sm = 0.015 → error`, `0.10 → ok`, `0.25 → warn`,
    `0.35 → error`; with no `x_np` the classification is `unknown` and both SM
    values are `null`; on elevator-authority success `cg_stability_fwd_m` is not
    `x_np − 0.30·MAC`.
  - Confidence: 🟢

- [ ] **T-09 — Additive context enrichment.**
  `enrich_context_with_cg_envelope` adds `cg_forward_m`, `cg_aft_m`,
  `sm_at_fwd = (x_np − cg_fwd)/MAC`, `sm_at_aft`, `cg_stability_fwd_m`,
  `cg_stability_aft_m` **without touching `cg_agg_m`**.
  - Legacy origin: `app/services/loading_scenario_service.py`
  - Definition of done: `cg_agg_m` is byte-identical before and after; when
    `x_np`/MAC are absent the SM keys are written as `None`, not as stubs.
  - Confidence: 🟢

- [ ] **T-10 — Landing field length by energy balance (gh-477).**

  ```
  V_S0      = sqrt(2·m·g / (ρ·S·CL_max_landing))
  V_TD      = 1.15 · V_S0                       # _V_TD_OVER_V_S0, RC rule of thumb
  s_ground  = V_TD² / (2·g·μ_eff)               # energy balance; mass cancels
  L_landing = safety · (15 m flare + s_ground)  # _LANDING_FLARE_M = 15.0
  net_recovery → s_ground = 0; L collapses to the padded flare

  LANDING_SURFACE_MU = grass_short 0.15 · grass_long 0.22 · hard_paved 0.07
                       soft_soil 0.30 · belly_grass 0.40 · net_recovery 0.0
  defaults: surface grass_short, safety 1.5 (_LANDING_SAFETY_DEFAULT), < 1.0 rejected
  ```

  Compare against `available_field_length_m` into a **tri-state**
  `landing_field_sufficient` (`True` / `False` / `None`) and publish
  `landing_field_length_m`, `landing_surface_used`,
  `landing_field_sufficient` on the context.
  - Legacy origin: `app/services/assumption_compute_service.py:1782-1848`
  - Definition of done: `net_recovery` gives a zero ground roll; doubling the
    mass does not change `s_ground`; no `available_field_length_m` yields
    `null`, **not** `false`.
  - 🟡 Record the provenance in code: the μ values come from operational RC/UAV
    practice (Raymer ch. 17 / Roskam P.7 territory), **not** from Anderson.
  - Confidence: 🟢

- [ ] **T-11 — The Roskam field-length endpoint and its 422 preconditions.**
  `compute_field_lengths(aircraft, takeoff_mode, landing_mode)` returning the
  seven `FieldLengthRead` fields, with the four missing-input guards raising a
  bare `ServiceException` mapped to **422** with a remediation sentence. Read
  thrust from `MissionObjective.t_static_N` (gh-548), and detect the flap type
  by joining `TED → WingXSecDetail → WingXSec → Wing` for `role == "flap"`
  (→ `"plain"`, else `None`).
  - Legacy origin: `app/api/v2/endpoints/aeroplane/field_lengths.py:51-77,
    :139-190`, `app/services/field_length_service.py`
  - Definition of done: a cold-start aircraft returns 422 naming the exact
    missing input and the remediation, never a 500 and never a fabricated
    number; the Loftin/Roskam constants are **declared here and imported
    elsewhere**.
  - 🟢 **The gh-477 energy balance is the model the UI trusts** (`Q-MS-2`, expert consensus endorsed by the maintainer); the Roskam correlation is calibrated on a braked Cessna 172N and does not transfer to RC/UAV scale (ADR 0023). Previously two models coexisted — Roskam
    §3.4 on this endpoint and the gh-477 energy balance in the context — with no
    cross-check. Decide which is authoritative for the UI.
  - Confidence: 🟢

- [ ] **T-12 — The matching chart.**
  200 W/S steps over `[10, 1500] N/m²`; the five classical constraints; the five
  RC-additive constraints; `_PROFILE_CONSTRAINT_MAP` applicability; the mode
  defaults; feasibility within **3 %** (line) / **5 %** (vertical). Import
  `_K_TO_50FT`, `_K_LDG_50FT`, `_K_LDG_HARD`, `_C_TO` from
  `field_length_service` — never re-declare them.
  - Legacy origin: `app/services/matching_chart_service.py:71-73, :77,
    :448-479, :589, :656-657`,
    `app/api/v2/endpoints/aeroplane/matching_chart.py:48-121`
  - Definition of done: a `sailplane` profile evaluates **only** the stall
    constraint while the others are still returned with
    `applicable_for_profile = false`; a hand-launch mode zeroes the takeoff
    constraint and adds the 80 N/m² cap; the four constants appear in exactly one
    module.
  - Confidence: 🟢

- [ ] **T-13 — `DEFAULT_E_OSWALD` must warn, not substitute (gh-956 / ADR 0012).**
  The endpoint already omits `e_oswald` from the aircraft dict unless
  `ctx["e_oswald"] > 0`. Make the service turn that omission into a
  **user-visible design warning** on `MatchingChartResponse.warnings` rather
  than silently computing with `0.8`.
  - Legacy origin: `matching_chart.py:104-107`,
    `matching_chart_service.py:77`
  - Definition of done: a cold-start chart carries a warning naming the fallback
    and its value; no chart silently uses `0.8`.
  - Confidence: 🟢 for the behaviour, 🔴 for the intended fix

- [ ] **T-14 — Log-forging safety (Sonar S5145).**
  Never log the user-controlled `flight_profile` string directly; map it through
  the constant `_LOG_PROFILE_LABELS` table via `_sanitize_profile_for_log`.
  Apply the same rule to the user-controlled mission id in
  `mission_kpi_service`.
  - Legacy origin: `matching_chart_service._sanitize_profile_for_log`,
    `mission_kpi_service.compute_mission_kpis` (the log line deliberately omits
    the id)
  - Definition of done: a profile name containing a newline cannot inject a log
    record; only mapped labels appear.
  - Confidence: 🟢

- [ ] **T-15 — SM sizing suggestions and the apply loop.**
  `GET …/sm-suggestion?at_cg=aft|fwd` returning the five-valued `status`, up to
  two levers (`wing_shift`, `htail_scale`), `block_save` when `SM < 0.02`, and
  the `mass_coupling_warning` whenever a `wing_shift` option exists.
  `POST …/sm-suggestions/apply` with `dry_run`, **400** for
  canard/tailless/no-NP, **409** when the apply loop does not converge in 3
  iterations (gh-509, Scholz A6).
  - Legacy origin: `app/api/v2/endpoints/aeroplane/sm_suggestions.py`,
    `app/services/sm_sizing_service.py`, `app/schemas/sm_sizing.py`
  - Definition of done: `dry_run = true` writes nothing and still returns
    `predicted_sm`; a non-converging apply is a 409, not a silent partial edit.
  - 🟢 **Decided (`Q-MS-14`):** the seeded default is `0.10` and there is one authority. Previously the endpoint read `target_static_margin` from
    the context with an inline default of **0.10**, while the seeded assumption
    default is **0.12**. Collapse the two onto one constant.
  - Confidence: 🟢

- [ ] **T-16 — The forward-CG limit endpoint.**
  `POST …/forward-cg/recompute?solver=asb|avl` implementing

  ```
  x_cg_fwd = x_np − (Cm_ac + Cm_δe·δe_max + ΔCm_flap) · c_ref / CL_max_landing
  Cm_δe measured TE-UP (negative) ⇒ Cm_δe > 0;  δe_max = |δ_neg| · π/180
  ```

  with `cg_fwd_m = null` on the infeasibility guard, the confidence tier
  (`solver=avl` ⇒ always `avl_full`), and the `0.30·MAC` stub fallback on any
  failure — still HTTP 200, with the failure recorded in the result.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/forward_cg.py`,
    `app/services/elevator_authority_service.py`, `app/schemas/forward_cg.py`
  - Definition of done: `solver=avl` is never selected automatically; a solver
    failure returns the stub with a lower confidence tier rather than a 500.
  - Confidence: 🟢

- [ ] **T-17 — The REST surface.**
  Wire the 33 routes of [`contracts.md`](contracts.md) at the application root
  (`prefix=""`), with the per-file domain-exception mapper on every handler and
  the path-regex constraint on `{param_name}`.
  - Legacy origin: `app/main.py:206-231`,
    `app/api/v2/endpoints/aeroplane/__init__.py:34-57`, the nine endpoint
    modules
  - Definition of done: the generated OpenAPI matches the contract tables
    (method, path, request model, response model, documented status codes); no
    route acquires an `/api/v2` prefix.
  - 🟢 **Decided (`Q-CC-3`):** one envelope; the seven local mappers are deleted. Previously
    two response envelopes coexist today, and the matching-chart / field-length
    pair maps a bare `ServiceException` to **422** while every other handler maps
    it to **500**. Pick one envelope and one mapping, and keep the 422 semantics
    for genuinely user-actionable missing inputs by raising a
    `ValidationDomainError` there instead of a bare `ServiceException`.
  - 🟡 Consider mounting these routers on `NonFiniteSafeJSONResponse` too — a NaN
    in a `t_w_points` array or a V-n `load_factor` is not neutralised today.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Effective value and divergence.** `estimate 1.5 / calculated 1.8
      / CALCULATED` ⇒ effective `1.8`, divergence `16.7 %`, level `warning`;
      `calculated = 0` or `null` ⇒ `divergence_pct is None`, level `none`.
- [ ] **TT-02 — Event gating.** An estimate edit under an active `CALCULATED`
      publishes no `AssumptionChanged` and dirties no OP; `switch_source` always
      publishes; `switch_source("cg_x")` schedules **no** recompute.
- [ ] **TT-03 — Design choices.** All seven reject `CALCULATED` with 422; a
      `CALCULATED` switch with `calculated_value IS NULL` also 422s.
- [ ] **TT-04 — Auto-switch fires once.** First calculated value flips the
      source; after a manual switch back to `ESTIMATE`, a second calculated value
      leaves it on `ESTIMATE`.
- [ ] **TT-05 — Seeding is idempotent.** Two `seed_defaults` calls leave 15
      assumption rows and one computation-config row.
- [ ] **TT-06 — Unknown parameter name is a path-level 422**, not a service 404.
- [ ] **TT-07 — Preset switch touches estimates only.** `calculated_value`,
      `calculated_source` and `active_source` are unchanged for all five
      preset-controlled parameters.
- [ ] **TT-08 — Unknown `mission_type`** currently returns 200 with no change —
      pin the behaviour.
- [ ] **TT-09 — Nine presets, seven axes.** `GET /mission-presets` returns 9;
      every preset's `target_polygon` and `axis_ranges` cover exactly the seven
      axes.
- [ ] **TT-10 — Empty preset table is a 500**, not an empty radar.
- [ ] **TT-11 — KPI axes are closed-form.** With `AeroBuildup` mocked to raise,
      `compute_mission_kpis` still returns seven axes; the mock is never called.
- [ ] **TT-12 — Profile deletion conflict.** A profile assigned to an aircraft
      cannot be deleted (409); after detach it can.
- [ ] **TT-13 — `V_md` substitution.** With no profile assigned,
      `v_cruise_auto` is `true` and `v_cruise_mps == v_md_mps`.
- [ ] **TT-14 — Profile validators.** `max_level_speed ≤ cruise` → 422;
      `target_turn_n` above `1/cos(max_bank)+0.05` → 422; `agile` with no roll
      rate defaults to 240 dps.
- [ ] **TT-15 — SM ladder.** `0.015 → error` · `0.10 → ok` · `0.25 → warn` ·
      `0.35 → error`; no `x_np` → `unknown` with `null` SM values.
- [ ] **TT-16 — Four override types.** A toggle removes exactly one component; a
      mass override does not move it; a position override does not change total
      mass; an adhoc item adds both.
- [ ] **TT-17 — Enrichment is additive.** `cg_agg_m` is byte-identical before
      and after `enrich_context_with_cg_envelope`.
- [ ] **TT-18 — Landing field length.** `net_recovery` ⇒ ground roll `0`;
      doubling the mass leaves `s_ground` unchanged; missing
      `available_field_length_m` ⇒ `landing_field_sufficient is None`;
      `landing_safety_factor < 1.0` is rejected.
- [ ] **TT-19 — Field-length 422 preconditions.** Each of the four missing
      inputs produces a 422 whose message names the input and the remedy.
- [ ] **TT-20 — Matching-chart applicability.** `flight_profile=sailplane`
      marks only `stall` as `applicable_for_profile`; `custom`/unknown marks all;
      `rc_hand_launch` zeroes the takeoff constraint and adds the 80 N/m² cap.
- [ ] **TT-21 — Constant single-declaration.** A source-level assertion that
      `_K_TO_50FT`, `_K_LDG_50FT`, `_K_LDG_HARD` and `_C_TO` are declared in
      exactly one module.
- [ ] **TT-22 — Feasibility tolerances.** A line constraint 2 % away binds and
      3.5 % away does not; a vertical constraint 4 % away binds and 6 % away does
      not.
- [ ] **TT-23 — Oswald design warning.** A cold-start chart (no `e_oswald` in
      the context) carries a warning naming the fallback.
- [ ] **TT-24 — Log forging.** A profile name containing `\n` produces exactly
      one log record and only a mapped label.
- [ ] **TT-25 — SM apply.** `dry_run = true` leaves the geometry untouched and
      still returns `predicted_sm`; a non-converging apply returns 409.
- [ ] **TT-26 — Forward CG fallback.** A solver failure returns 200 with the
      `0.30·MAC` stub and a lowered confidence tier.
- [ ] **TT-27 — Fast-tier coverage.** Every task above has at least one test that
      runs **without** AeroSandbox installed, stubbing the solver boundary
      (ADR 0015 — the CI fast tier has no aero dependencies, so unmocked tests
      leave this code uncovered against the 80 % new-code gate). Only T-05, T-06
      and the `_get_b_ref` lookup touch a solver at all; everything else is
      closed-form and must be covered in the fast tier.

## Data Migration Tasks

- [ ] **TM-01 — `design_assumptions`.** `UniqueConstraint(aeroplane_id,
      parameter_name)` → `uq_assumption_aeroplane_param`; FK
      `ON DELETE CASCADE`; `estimate_value` NOT NULL; `active_source` defaulting
      to `"ESTIMATE"`; `updated_at` with `onupdate`.
      🟡 Backfill: `min_static_margin` / `max_static_margin` are read by
      `stability_service` but were never seeded. Either add them to the
      catalogue and backfill, or delete the lookup.
- [ ] **TM-02 — `aircraft_computation_config`.**
      `uq_computation_config_aeroplane`; the seven columns with the
      `COMPUTATION_CONFIG_DEFAULTS` values.
- [ ] **TM-03 — `mission_objectives`.** **UNIQUE, INDEXED** FK to
      `aeroplanes.id` with `ON DELETE CASCADE` (one row per aeroplane); the
      twelve required columns with their server defaults plus the three nullable
      gh-477 landing columns.
      🟢 Decided (`Q-CC-7`): add the FK to `mission_presets.id`.
- [ ] **TM-04 — `mission_presets`.** **String primary key**; `target_polygon`,
      `axis_ranges` and `suggested_estimates` as JSON.
      🟡 `axis_ranges` is stored as `{axis: [min, max]}` (lists) but read as
      tuples — the service converts on both boundaries; keep that conversion or
      normalise the storage.
- [ ] **TM-05 — `rc_flight_profiles`.** UNIQUE INDEXED `name`; the four JSON
      blobs; `created_at` / `updated_at`. Referenced by
      `aeroplanes.flight_profile_id` **and**
      `operating_pointsets.source_flight_profile_id` — both must survive a
      profile delete only through the 409 guard, not through a cascade.
- [ ] **TM-06 — `loading_scenarios`.** FK `ON DELETE CASCADE`, INDEXED;
      `component_overrides` JSON defaulting to `{}`; `is_default` boolean.
      🟢 **`is_default` gains a partial unique index** — two defaults produce a non-deterministic `cg_agg_m` (`Q-MS-13 ②`).
      add a partial unique index or resolve deterministically.
- [ ] **TM-07 — `flight_envelopes`.** **UNIQUE** FK per aeroplane
      `ON DELETE CASCADE`; `vn_curve_json`, `kpis_json`, `markers_json`,
      `assumptions_snapshot` JSON; `computed_at` tz-aware.

## Suggested Order

1. **T-01 → T-02** first: every other task in this module and in
   `aero-analysis` reads assumptions through them.
2. **T-03, T-04** next — they write assumption *estimates* and drive the cruise
   speed, so they must sit on top of a working T-02.
3. **T-05** (OP sweep) depends on T-04 (profile + `V_md`) and on the
   `aero-analysis` context.
4. **T-06** (flight envelope) depends on T-01 (mass, `cl_max`, `g_limit`) and
   reads the OP rows T-05 produces.
5. **T-07 → T-09** (loading, CG envelope, enrichment) are independent of the
   solver work and can run in parallel with T-05/T-06; T-09 must land with T-08
   so the context and the endpoint agree.
6. **T-10, T-11** (the two landing models) together, so the duplication is
   resolved rather than shipped twice.
7. **T-12 → T-14** (matching chart) after T-11 — it imports T-11's constants.
8. **T-15, T-16** (SM sizing, forward CG) after T-08, whose stub they override.
9. **T-17** (transport) last.

Blocking edges: T-02 ⇠ T-01 · T-03 ⇠ T-02 · T-05 ⇠ T-04 · T-06 ⇠ T-01, T-05 ·
T-08 ⇠ T-07 · T-09 ⇠ T-08 · T-12 ⇠ T-11 · T-13 ⇠ T-12 · T-15 ⇠ T-08 ·
T-16 ⇠ T-08 · T-17 ⇠ everything.

## Pending Gaps (🔴)

- **One error contract, or seven?** (T-17) Seven local mappers, two response
  envelopes, and a 422↔500 split for the same exception type. Which shape wins,
  and does the matching-chart/field-length 422 semantics survive as an explicit
  `ValidationDomainError`?
- **Two landing-distance models** (T-10 vs T-11). Roskam §3.4 on
  `/field-lengths`, gh-477 energy balance in the context, no cross-check and no
  statement of which the UI should trust.
- **Two thrust sources.** `MissionObjective.t_static_N` (gh-548, used by the
  field-length endpoint) and the `t_static_N` design assumption (used by the
  matching chart). They can disagree silently.
- **Three defaults for `target_static_margin`**: `0.12` (seeded assumption),
  `0.10` (inline default in the SM-suggestion endpoint), and whatever the active
  mission preset wrote. Which is authoritative?
- **`power_to_weight` unit divergence.** Seven presets write dimensionless
  0.0–1.4 into a parameter catalogued as **W/kg** with a default of 220;
  `motor_glider` and `flying_wing` write `100.0` W/kg. One of the two readings is
  wrong, and the matching chart's power-loading constraint consumes it.
- **`min_static_margin` / `max_static_margin`** (TM-01) are read but never
  seeded, so the 5 % / 25 % CG-range bounds are unreachable configuration.
- **`is_default` on `loading_scenarios` is unconstrained** (TM-06) — two default
  scenarios produce a non-deterministic `cg_agg_m`.
- **Unvalidated `component_uuid`** in scenario overrides (T-07) — a stale
  override is indistinguishable from a no-op.
- **No cross-field validation on the computation config** (T-01/T-17) — an
  inverted α range yields an empty sweep with no error.
- **`ComputeEnvelopeRequest.force_recompute` is dead surface** — the POST takes
  no body. Delete it or wire it.
- **German docstrings on `flight_profiles`** (T-04) leak into the OpenAPI of an
  English-only product.
- **The gh-477 μ table has no calibration source** beyond "operational RC/UAV
  practice". It is the single largest lever on the landing answer.
