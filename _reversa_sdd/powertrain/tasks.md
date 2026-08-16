# powertrain — Implementation Tasks

> Executable sequence to re-implement the module from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker.
> Use-case task lists:
> [`cots-powertrain-components`](cots-powertrain-components/tasks.md) ·
> [`propeller-polars`](propeller-polars/tasks.md) ·
> [`performance-model`](performance-model/tasks.md) ·
> [`powertrain-sizing`](powertrain-sizing/tasks.md).

## Prerequisites

- [ ] `aeroplanes` table with a public `uuid` (the four aeroplane-scoped routes
      resolve it, even where the data is unused).
- [ ] `design_assumptions` + `design_assumptions_service.get_effective_assumption`
      and `PARAMETER_DEFAULTS` — module `mission-and-sizing`.
- [ ] `assumption_computation_context` on `aeroplanes` (gh-924) — module
      `aero-analysis`. Both sizing paths read it and must warn when it is empty.
- [ ] `endurance_service._power_required` and the efficiency constants
      `DEFAULT_ETA_PROP/MOTOR/ESC = 0.65 / 0.85 / 0.94`.
- [ ] `get_db()` request-scoped session (ADR 0009); the reimport CLIs commit
      once at the end, outside the request cycle.
- [ ] NumPy. **No** AeroSandbox and **no** CadQuery — every route in this module
      must run in the CI fast tier.
- [ ] The committed snapshots in `data/cots/` (`apc_props.json.gz`,
      `dpower.json`, `generic_batteries.json`, …). The gitignored
      `data/apc_raw/` is only needed to regenerate them.

## Tasks

- [ ] **T-01 — `components` table.**
  `name`, `component_type` (indexed String discriminator), `manufacturer`,
  `description`, `mass_g` (nullable — `NULL` means *unknown*), `bbox_{x,y,z}_mm`,
  `model_ref`, `specs` (JSON, default `{}`), `created_at` / `updated_at`.
  - Legacy origin: `app/models/component.py:8`
  - Definition of done: a component of any type round-trips; `mass_g = NULL`
    stays `NULL` and is never coerced to `0`.
  - Confidence: 🟢

- [ ] **T-02 — `component_types` table with the `schema` → `schema_def` mapping.**
  `name` (UNIQUE, indexed, immutable), `label`, `description`, `schema` (JSON
  list, **mapped as `schema_def`** because `schema` collides with a Pydantic
  attribute), `deletable` (default `True`, `server_default="1"`).
  - Legacy origin: `app/models/component_type.py:20, 28`
  - Definition of done: the Python attribute is `schema_def` while the column is
    `schema`; a test asserts both, because getting this wrong breaks every
    Pydantic serialisation of the model.
  - Confidence: 🟢

- [ ] **T-03 — `validate_specs`.**
  Unknown type → `ValidationError` naming `GET /component-types`; missing
  required → reason `missing_required`; wrong python type, out-of-range
  (inclusive `min`/`max`), value not in `options` → `ValidationError`; **unknown
  keys accepted**. Called on every create and update.
  - Legacy origin: `app/services/component_type_service.py:240-271`
  - Definition of done: a table-driven test with one case per rejection branch
    **plus** an explicit test that an undeclared key is accepted (this is the
    behaviour `prop_component_seed` depends on).
  - Confidence: 🟢

- [ ] **T-04 — The 12 seeded types + idempotent seeding + additive patching.**
  `DEFAULT_SEED_TYPES` with `deletable=False`; `seed_default_types` called at
  startup and by the test fixture; `_patch_schema_fields` merges newly declared
  properties onto existing rows.
  - Legacy origin: `component_type_service.py:331, 682, 710`
  - Definition of done: two consecutive seeds leave exactly 12 rows; adding a
    property to the seed list makes it appear on an already-seeded row without a
    migration. Reproduce the German labels verbatim and record them as a gap.
  - Confidence: 🟢

- [ ] **T-05 — Type deletion guards.**
  `deletable=False` → 409; referenced by ≥ 1 component → 409 with the count.
  `update_type` may change `label` / `description` / `schema` only.
  - Legacy origin: `component_type_service.py` (delete + update paths)
  - Definition of done: both 409s are covered; a `PUT` attempting to change
    `name` or `deletable` leaves them unchanged and does not error.
  - Confidence: 🟢

- [ ] **T-06 — Component CRUD + the polar bridge.**
  `list_components(db, component_type, q)` with a **batch** `polar_id`
  resolution; `create/get/update/delete_component`; `ComponentRead` carrying
  `has_polar` / `polar_id`.
  - Legacy origin: `app/services/component_service.py`
  - Definition of done: listing N propellers issues a constant number of
    statements (query counter); `has_polar` is `true` exactly when a polar
    shares the `model_ref`.
  - Confidence: 🟢

- [ ] **T-07 — `propeller_polars` + `propeller_polar_samples`.**
  Header keyed `(manufacturer, name)` with `model_ref`, `source_url`,
  `source_version`, `diameter_in`, `pitch_in`, `variant` (default `""`),
  `blades` (default `2`), `weight_g`, `inertia_kg_m2`, `geometry` (JSON);
  samples `(propeller_id, rpm, J, Ct, Cp, Pe, PWR_W, Torque_Nm, Thrust_N)` with
  `cascade="all, delete-orphan"`.
  - Legacy origin: `app/models/prop_polar.py:21, 71`
  - Definition of done: deleting a header removes its samples. Reproduce the
    **absence** of a unique constraint on `(propeller_id, rpm, J)` and record it
    as a gap — the protection is `_upsert_samples`, not the schema.
  - Confidence: 🟢

- [ ] **T-08 — The PER3 parser.**
  Header-line-1 geometry (filename as the **logged fallback**); SI columns only
  at fixed indices `J=1, Pe=2, Ct=3, Cp=4, PWR_W=8, Torque_Nm=9, Thrust_N=10`;
  rows with `< 11` fields skipped; blade count from `-([3-9])$` on the variant
  with `DEFAULT_BLADES = 2`; `model_ref = "apc/<designation>"` with `.` → `p`.
  - Legacy origin: `scripts/parse_apc_props.py:162-168, 302-304`
  - Definition of done: `PER3_105x45` parses as 10.5 × 4.5 in; `10x10E` → variant
    `"E"`, 2 blades; `10x10M-JK` → variant `"M-JK"`, **2** blades; `E-3` → 3.
  - Confidence: 🟢

- [ ] **T-09 — `import_prop_polars` with the freshness proxy.**
  Upsert on `(manufacturer, name)`; reject `component_type != "propeller"` into
  `ImportResult.errors`; `_records_equal` compares `source_version`,
  `source_url`, `variant` and the "row lacks `weight_g` but the snapshot has
  one" case; `_upsert_samples` **deletes all** then re-inserts.
  - Legacy origin: `app/services/prop_polar_import.py`
  - Definition of done: an unchanged snapshot reports every record `skipped`; a
    bumped `source_version` reports `updated`; a changed sample value with an
    unchanged version is **skipped** (reproduce the documented limitation and
    record it as a gap), and `force=True` overrides it.
  - Confidence: 🟢

- [ ] **T-10 — PE0 enrichment with the kg→g guard.**
  Match PE0 records to snapshot records by `(diameter, pitch, variant)`; write
  `weight_g`, `inertia_kg_m2` and the per-station `geometry`; reject a weight
  below `MIN_PLAUSIBLE_WEIGHT_G = 1.0` into `unit_warnings`; log unmatched rows.
  - Legacy origin: `app/services/prop_polar_enrich.py:29`
  - Definition of done: a 0.043 g parse is counted, not written; an unmatched
    PE0 row is logged and the run still succeeds.
  - Confidence: 🟢

- [ ] **T-11 — `seed_propeller_components` (the polar → component mirror).**
  Idempotent on `model_ref`; `mass_g` populated from `weight_g` on create (both
  grams, no conversion); a **NULL** `mass_g` backfilled once the polar gains a
  weight; a **non-null** `mass_g` never clobbered; polars without a `model_ref`
  skipped.
  - Legacy origin: `app/services/prop_component_seed.py`
  - Definition of done: three tests, one per mass rule. Reproduce the fact that
    the seed **bypasses `validate_specs`** and record the consequence (a NULL
    `diameter_in` yields a component that 422s on its first API `PUT`).
  - Confidence: 🟢

- [ ] **T-12 — `cots_import` for the non-propeller snapshots.**
  Upsert on `(manufacturer, name)`; `_VALID_COMPONENT_TYPES` gating.
  - Legacy origin: `app/services/cots_import.py:26-40`
  - Definition of done: a record with an unknown type lands in `errors`.
    Record the duplication with `DEFAULT_SEED_TYPES` as a gap rather than
    unifying them silently.
  - Confidence: 🟢

- [ ] **T-13 — `interpolate_ct_cp_pe`.**
  Sort by `J`; `np.interp` on `Ct` and `Cp`; **clamp** `J` to `[J_min, J_max]`
  and raise an `extrapolation_warning`; clamp `Ct` at 0; recompute
  `Pe = Ct·J/Cp` (0 when `Cp ≤ 0` or `J = 0`).
  - Legacy origin: `app/services/powertrain_performance.py:278`
  - Definition of done: a `J` above the maximum returns the endpoint value and
    sets the warning flag; `Pe` never comes from the stored column.
  - Confidence: 🟢

- [ ] **T-14 — Model A, the fixed-RPM chain.**
  `V_bat = cells·3.7` (**loaded**, not 4.2); `n = output_kv · V_bat · throttle`
  with `output_kv = kv_rpm_per_volt / (gear_ratio or 1)`;
  `P_elec_max = min(motor limit, battery limit)`;
  `P_shaft_max = P_elec_max · η_motor` (`efficiency_pct/100` else `0.85`);
  per V: `J`, `Ct/Cp/Pe`, `T = Ct·ρ·n²·D⁴` clamped `≥ 0`,
  `P = clip(Cp·ρ·n³·D⁵, 0, P_shaft_max)`, `η_prop = clip(Pe, 0, 1)`,
  `estimated = True`.
  - Legacy origin: `app/services/powertrain_performance.py:48-51` and the
    curve loop
  - Definition of done: a test asserts the RPM is **constant** across the sweep
    and that using 4.2 V per cell would change the power by ~13 % (guards
    BR-65).
  - Confidence: 🟢

- [ ] **T-15 — Model B, the QPROP torque balance.**
  `Kv_si = output_kv·2π/60`; `I(n) = (V_term − ω/Kv_si)/Rm`;
  `Q_motor = (I − I₀)/Kv_si`; `Q_prop = Cp·ρ·n²·D⁵/(2π)`; bisection over
  **80** iterations between the free-run RPM and the back-EMF floor, with the
  documented clamps; `η_motor = (V_term − I·Rm)(I − I₀)/(V_term·I)` clipped to
  `[0,1]`; `P_shaft = Q·ω`; `estimated = False`.
  - Legacy origin: `app/services/powertrain_performance.py:569`
  - Definition of done: RPM **falls** as velocity rises; the iteration count is
    bounded; both degenerate brackets return a clamped value instead of
    diverging.
  - Confidence: 🟢

- [ ] **T-16 — Degenerate-input warnings.**
  `prop_rpm ≤ 0` ⇒ an all-zero curve plus *"Computed RPM is zero — check motor
  KV and battery voltage"*; both power limits unknown ⇒ `V_bat × 100 A` plus a
  warning; `P_shaft_max < 0.1 W` ⇒ an infeasibility warning.
  - Legacy origin: `app/services/powertrain_performance.py`
  - Definition of done: each of the three cases returns 200 with its exact
    warning text — never an exception, never a silent zero (ADR 0012).
  - Confidence: 🟢

- [ ] **T-17 — `compute_solution_space`.**
  Read the gh-924 context with a warned fallback per input, resolve mass and
  cd0, validate `t_target_min > 0` and `V_top > V_cruise`, then compute
  `_p_aero` / `_p_elec` / `_per_cell` three times (mid, lo, hi η) per cell
  count, with `I_peak = P_top_elec / V_sag` (**no second efficiency division**,
  gh-978).
  - Legacy origin: `app/services/powertrain_solution_space_service.py:83-169,
    239-345`
  - Definition of done: an empty context yields ≥ 4 named warnings and still
    200; a regression test pins `I_peak` against a hand-computed value so the
    double-division cannot reappear.
  - Confidence: 🟢

- [ ] **T-18 — The feasible region and the shopping spec.**
  `_build_hyperbola(i_peak, cap_floor, n=40)` over `[cap_floor, 4·cap_floor]`;
  one `ShoppingSpec` per cell count.
  - Legacy origin: `powertrain_solution_space_service.py:172-184`
  - Definition of done: 40 points; `C = I_peak/(cap/1000)` holds at every
    sample; a zero `cap_floor` or `i_peak` returns two empty lists rather than
    raising.
  - Confidence: 🟢

- [ ] **T-19 — Catalogue matching flags.**
  `_catalog_motor_match` on **shaft** power (`max_power_w` ∥
  `max_continuous_power_w`); `_catalog_battery_match` on `capacity_mah` **and**
  (`c_rating` ∥ `discharge_c`); `_catalog_esc_match` on
  (`max_current_a` ∥ `continuous_current_a`).
  - Legacy origin: `powertrain_solution_space_service.py:192-231`
  - Definition of done: each flag is `false` on an empty catalogue without
    failing the request; a test documents that a battery carrying only `c_rate`
    (the `BatterySpec` spelling) matches **nothing** here — the vocabulary gap.
  - Confidence: 🟢

- [ ] **T-20 — `size_powertrain`, the catalog sweep.**
  Motor × battery cross-product; `total_mass = airframe + motor + battery`;
  `η_total = η_prop·η_motor·η_esc`; power from
  `endurance_service._power_required`; reject `I_cruise > max_current_draw_a`;
  `t_flight = (cap_Ah/I_cruise)·0.8·60`; first-fitting ESC; `confidence =
  min(t_flight/t_target, 1.0)`; sort desc, cap at 10.
  - Legacy origin: `app/services/powertrain_sizing_service.py:230-318`
  - Definition of done: the physics is **delegated**, not re-derived — a test
    patches `_power_required` and asserts it is called; the legacy
    `_required_power_w` shim still raises `NotImplementedError`.
  - Confidence: 🟢

- [ ] **T-21 — Aero-parameter resolution and empty-catalogue warnings.**
  3-tier priority (request → context → RC default `cd0 0.03`, `e 0.8`,
  `AR 8.0`, `S 0.5`) with a per-parameter warning; battery voltage walk
  `voltage_v → voltage → nominal_voltage → cells·3.7 → 11.1`; no motors or no
  batteries ⇒ `recommendations: []` **plus** warnings.
  - Legacy origin: `powertrain_sizing_service.py:44-47, 275-300`
  - Definition of done: each tier is covered; a battery carrying only `cells`
    resolves to `cells·3.7`, not 11.1 (guards gh-992).
  - Confidence: 🟢

- [ ] **T-22 — `get_modal_params`.**
  `cd0` / `s_ref_m2` from the context with the same fallback pattern;
  `DEFAULT_MOTOR_ETA = 0.85`, `DEFAULT_ETA_PROP = 0.65`; motors sorted by name
  with `efficiency_pct` defaulting to 85; **raw** KV, not `output_kv`.
  - Legacy origin: `app/services/powertrain_sizing_modal_service.py`
  - Definition of done: a test asserts the raw KV is returned — this is the one
    place BR-65's gear-aware rule is deliberately not applied.
  - Confidence: 🟢

- [ ] **T-23 — The routers.**
  `/components` and `/component-types` (prefixes on the routers), plus the four
  aeroplane-scoped powertrain routes exactly as in
  [`contracts.md`](contracts.md), including
  `POST /aeroplanes/{id}/powertrain/sizing` (**not** `/powertrain_sizing`) and
  the 15 optional query params on the solution space.
  - Legacy origin: `app/api/v2/endpoints/components.py`,
    `component_types.py`, `aeroplane/powertrain_*.py`
  - Definition of done: contract tests per status code; a test asserts the
    performance endpoint 404s for a non-existent aeroplane **even though it
    reads no aeroplane data**.
  - Confidence: 🟢

- [ ] **T-24 — The reimport CLIs.**
  `scripts/import_cots.py`, `import_apc_props.py`,
  `seed_propeller_components.py` — each reading a committed snapshot, each
  committing once at the end.
  - Legacy origin: the three scripts
  - Definition of done: running each twice is idempotent; none of them opens a
    network connection (assert with a socket guard).
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — `validate_specs` matrix:** one case per rejection branch plus
      the accepted-unknown-key case.
- [ ] **TT-02 — Seeding idempotence** and additive schema patching.
- [ ] **TT-03 — Type deletion guards:** seeded (409) and referenced (409 with
      the count).
- [ ] **TT-04 — Component list:** type filter, name search, constant query count
      for `has_polar`.
- [ ] **TT-05 — PER3 parsing matrix:** `105x45`, `10x10E`, `10x10M-JK`,
      `10x10E-3`, a short row, a header-less file (filename fallback + log).
- [ ] **TT-06 — Import semantics:** skipped / updated / errors; `force=True`;
      wholesale sample replacement with no duplicates.
- [ ] **TT-07 — PE0 guard:** sub-gram rejected into `unit_warnings`; unmatched
      logged.
- [ ] **TT-08 — Mirror mass rules:** create-from-polar, NULL backfill,
      non-null preserved.
- [ ] **TT-09 — Interpolation:** in-range, below `J_min`, above `J_max` (both
      clamped + warned), `Cp ≤ 0` ⇒ `Pe = 0`, `Ct` clamped at 0.
- [ ] **TT-10 — Model A:** constant RPM; the `min()` power ceiling; 3.7 V per
      cell; gear-aware `output_kv`.
- [ ] **TT-11 — Model B:** falling RPM; bounded iterations; both bracket clamps;
      `η_motor` inside `[0,1]`.
- [ ] **TT-12 — Model selection:** `rm_ohm` present ⇒ `estimated = false`;
      absent ⇒ `true`.
- [ ] **TT-13 — Degenerate warnings:** zero RPM, unknown power limits,
      `P_shaft_max < 0.1 W`.
- [ ] **TT-14 — Missing-spec 422s:** motor without KV, motor without
      `cells_lipo_max`, battery without `cells`/`capacity_mah`, polar without
      samples.
- [ ] **TT-15 — Solution space:** one row per cell count; `v_nom = S·3.7`;
      `v_sag = S·3.5`; the band inversion (`_lo` uses `eta_prop_hi`).
- [ ] **TT-16 — gh-978 regression:** `I_peak` matches a hand-computed
      `P_top_elec / V_sag` — no second efficiency division.
- [ ] **TT-17 — Fallback warnings:** an empty context produces one warning per
      missing input, and the request still returns 200.
- [ ] **TT-18 — Domain validation:** `t_target_min ≤ 0` and
      `V_top ≤ V_cruise` ⇒ 422.
- [ ] **TT-19 — Hyperbola:** 40 points, `C·cap` invariant, degenerate inputs ⇒
      empty lists.
- [ ] **TT-20 — Sweep ranking:** ≤ 10 candidates, descending confidence,
      over-current combinations excluded, empty catalogue ⇒ warnings.
- [ ] **TT-21 — Delegation guard:** `_power_required` is called by the sweep;
      `_required_power_w` still raises `NotImplementedError`.
- [ ] **TT-22 — Battery voltage walk:** each of the four keys in priority order.
- [ ] **TT-23 — Modal params:** raw KV, defaulted efficiency, warnings.
- [ ] **TT-24 — Fast-tier guard:** importing every service in this module must
      not import `aerosandbox` or `cadquery`.
- [ ] **TT-25 — Offline guard:** the three reimport CLIs open no socket.

## Data Migration Tasks

- [ ] **TM-01 — Seed the 12 component types** on an empty database
      (idempotent; also runs at every startup).
- [ ] **TM-02 — Import the COTS snapshots** (`import_cots.py`) and the APC
      polars (`import_apc_props.py`), then mirror them into components
      (`seed_propeller_components.py`). Order matters: the mirror needs the
      polars.
- [ ] **TM-03 — Backfill `blades` and `variant`** on pre-gh-1004 / pre-gh-999
      rows — handled by `_records_equal`'s `variant` comparison, which forces an
      update for rows that predate the field.
- [ ] **TM-04 — Backfill `weight_g` / `inertia_kg_m2`** on pre-gh-1000 rows —
      handled by the "row lacks `weight_g` but the snapshot has one" clause.
- [ ] **TM-05 — Backfill `components.mass_g` from `weight_g`** for propellers
      whose mass is still `NULL` (gh-1017), **never** overwriting a non-null
      value.

## Suggested Order

1. **T-01 → T-05** first: the table pair and the type registry. Nothing else in
   the module can be written or validated without them, and `validate_specs` is
   the module's only integrity mechanism.
2. **T-06** — component CRUD, which makes the library usable end to end.
3. **T-07 → T-12** the ingestion chain, in pipeline order: schema → parser →
   importer → enricher → mirror → the sibling COTS importer. Each stage is
   independently testable against a small fixture snapshot.
4. **T-13** before T-14/T-15: both motor models consume the interpolation, and
   it is a pure function.
5. **T-14** and **T-15** in parallel — they share only the interpolation.
   **T-16** immediately after, since the warnings are part of both.
6. **T-17 → T-19** the solution space; it depends on none of the performance
   model (it uses its own `_p_aero`), so it can be built concurrently with 13–16.
7. **T-20 → T-22** the sweep and the modal, both of which need
   `endurance_service` to exist.
8. **T-23 → T-24** last: the routers, then the CLIs.

## Pending Gaps (🔴)

- **Should `_find_matching_esc` pick the smallest or lightest fitting ESC**
  rather than the first row the database happens to return?
- **Should propeller mass enter `size_powertrain`'s total?** Motor and battery
  masses do; the propeller's is now known (gh-1000/1017) and ignored.
- **Should the solution-space KV use a real propeller diameter** from the APC
  database instead of the fixed 0.30 m Phase-1 constant?
- **Should `prop_component_seed` run `validate_specs`?** It writes rows directly,
  so a polar with a NULL `diameter_in` produces a component that violates its own
  type schema.
- **Should `variant` be declared in the `propeller` type schema?** It is written
  by the seed and survives only because unknown keys are accepted.
- **Which spelling wins for the battery C-rate and the ESC current** —
  `c_rate` / `c_rating` / `discharge_c`, `continuous_current_a` /
  `max_continuous_a` / `max_current_a`? A battery imported under one name is
  invisible to the other consumer.
- **Should windmilling drag be modelled?** `Ct` is clamped at 0, so a power-off
  descent reports zero propeller drag.
- **Should the module use `asb.Atmosphere`** instead of
  `1.225·exp(−h/8500)`, or is the aero-stack divergence acceptable below a few
  hundred metres?
- **Should the 12-type taxonomy live in one place** rather than in both
  `DEFAULT_SEED_TYPES` and `cots_import._VALID_COMPONENT_TYPES`?
- **Should the seeded schema labels be translated to English?** They are German
  and rendered directly in the component editor.
- **Should `(propeller_id, rpm, J)` carry a unique constraint**, or is
  delete-then-insert the intended protection?
- **Should a candidate with no fitting ESC be flagged** rather than returned
  with `esc_id = null`?
- **Should the performance endpoint be aeroplane-scoped at all**, given it reads
  no aeroplane data?
- **Is the QPROP path reachable in practice?** No seeded motor carries `rm_ohm`,
  so the refined model is dormant for the entire shipped catalogue.
</content>
