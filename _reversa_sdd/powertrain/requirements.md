# powertrain

> Module-level specification. Focuses on WHAT the module does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: powertrain,
> `_reversa_sdd/data-dictionary.md` §Module: powertrain,
> `_reversa_sdd/domain.md` §2.9, ADR 0013, ADR 0014, ADR 0012, ADR 0017.

## Overview

`powertrain` is the **electric propulsion** module: the COTS hardware library
with its user-extensible per-type schema, the APC propeller polar database and
its network-free ingestion pipeline, the motor+propeller performance model
(fixed-RPM and QPROP torque balance), the required-spec solution space, and the
catalog sweep that recommends motor+ESC+battery combinations. 🟢

It answers three different questions with three different services: *"what will
this combination do?"* (performance), *"what must I shop for?"* (solution
space), and *"which of the parts I already have fit?"* (sizing sweep). 🟢

## Responsibilities

- Own `components` — one table for **every** hardware type, discriminated by
  `component_type`, with type-specific fields in a JSON `specs` blob. 🟢
- Own `component_types` — the per-type property schema as **data**, seeded with
  12 types and extensible by the user at runtime. 🟢
- Validate every component write against its type schema. 🟢
- Own `propeller_polars` + `propeller_polar_samples` — the APC PER3 dataset —
  and the snapshot-driven ingestion, PE0 enrichment and component-mirroring
  pipelines. 🟢
- Compute `T(V)`, `P_shaft(V)`, `η_prop(J)` for a motor + battery + propeller
  combination, under either the fixed-RPM model or the QPROP torque balance. 🟢
- Compute the required-spec envelope (per LiPo cell count, across an η_prop
  band) with a feasible-region hyperbola and a shopping spec. 🟢
- Sweep the catalogue for motor × battery combinations that meet a mission, and
  rank them by a continuous confidence score. 🟢
- Serve the pre-fill defaults for the frontend sizing modal. 🟢
- Serve component 3D-model upload / download. 🟢

**Explicitly NOT this module's responsibility:** the drag polar itself
(→ `endurance_service._power_required`, module `mission-and-sizing`), the aero
context that feeds it (→ `aero-analysis`, gh-924), servo components as wing
hardware (→ `wing-design`), wood/tube component types (→ `construction-plans`),
and the mass of a component once it is placed in an aircraft
(→ `mass-and-balance` / `aeroplane-core`).

## Business Rules

> `BR-59`…`BR-66` and `BR-78` are global ids reused verbatim from
> [`../domain.md`](../domain.md). `BR-PT*` are module-local.

### The component library

- **BR-59 — One table, a data-driven per-type schema (ADR 0013).** 🟢
  `components` holds every hardware type. Fixed columns are only what all types
  share: `name`, `manufacturer`, `description`, `mass_g`, `bbox_{x,y,z}_mm`,
  `model_ref`. Everything else lives in `specs` (JSON). The contract is
  `component_types.schema` — a JSON list of `PropertyDefinition`s — mapped in
  Python as **`schema_def`** because `schema` collides with a Pydantic attribute
  (`component_type.py:28`).
- **BR-60 — `validate_specs` rejects bad values but accepts unknown keys.** 🟢
  ```
  unknown component_type              -> ValidationError ("use GET /component-types")
  required property missing           -> ValidationError (reason "missing_required")
  number: non-numeric / bool          -> ValidationError
  number: < min or > max              -> ValidationError
  string / boolean: wrong python type -> ValidationError
  options present, value not in       -> ValidationError
  unknown keys in specs               -> ACCEPTED
  ```
  (`component_type_service.py:240-271`, called on every create and update.) The
  schema is a **floor, not a complete contract** — which is why
  `specs["variant"]` can exist on propellers without being declared.
- **BR-61 — Seeded and referenced types cannot be deleted.** 🟢
  `deletable=False` → 409; a type referenced by ≥ 1 component → 409 with the
  reference count. `update_type` may change `label`, `description` and `schema`
  but never `name` or `deletable`.
- **BR-PT1 — Twelve seeded types, idempotently.** 🟢 `seed_default_types`
  (`component_type_service.py:682`, called at startup and by the test fixture):
  `material`, `servo`, `brushless_motor`, `battery`, `esc`, `propeller`,
  `receiver`, `spar_tube`, `veneer`, `strip`, `triangular_strip`,
  `grooved_strip`. Only four belong to the powertrain proper.
- **BR-PT2 — Schema fields are patched additively onto existing rows.** 🟢
  `_patch_schema_fields` (`:710`) merges newly declared properties into
  already-seeded types, so an existing database gains e.g. the gh-1006 `rm_ohm`
  field without a rebuild.
- **BR-62 — COTS ingestion is network-free and snapshot-driven (ADR 0014).** 🟢
  The durable source is a **committed** snapshot (`data/cots/apc_props.json.gz`,
  ~8 MB, 454 propellers; plus `dpower.json`, `generic_batteries.json`,
  `spektrum_avian.json`, `carbon_tubes.json`, `hoellein_wood.json`), never the
  gitignored raw vendor files and never a live fetch.
- **BR-PT3 — Two importers, two identities for one table.** 🟢 `cots_import`
  upserts on `(manufacturer, name)`; `prop_component_seed` upserts on
  `(component_type='propeller', model_ref)`. 🟡
- **BR-PT4 — `mass_g = NULL` means unknown, never zero.** 🟢 A component with no
  known mass leaves the column `NULL`; the component-tree weight ladder then
  reports `weight_source = "none"` rather than 0 g.
- 🟢 **The `component_types` schema is the single binding contract** (`Q-PT-5`); `_VALID_COMPONENT_TYPES` in `cots_import.py:26-40` was a second,
  independently maintained copy** of the 12-name taxonomy.
- 🟢 **All German user-facing strings are translated to English** (`Q-CC-5`, maintainer-answered), including the seeded `component_types` labels. Previously: (`"Durchmesser"`, `"Steigung"`,
  `"Blätter"`, `"Dauerstrom"`, `"Leerlaufstrom Io"`, …) in an otherwise English
  API, and they are rendered directly in the component editor.

### The propeller polars

- **BR-PT5 — The polar physics definitions.** 🟢 (`prop_polar.py:71-82`)
  ```
  J  = V / (n·D)         advance ratio         [–]
  Ct = T / (ρ·n²·D⁴)     thrust coefficient    [–]
  Cp = P / (ρ·n³·D⁵)     power coefficient     [–]
  Pe = Ct·J / Cp         propulsive efficiency [–]   (0 at J = 0)
  ```
  plus the dimensional `PWR_W`, `Torque_Nm`, `Thrust_N`.
- **BR-PT6 — Geometry comes from the file header, not the filename.** 🟢
  Diameter, pitch and variant are parsed from PER3 header line 1 — the only way
  to read `PER3_105x45` as 10.5 × 4.5 in and to catch variant suffixes.
  Filename parsing is the logged fallback.
- **BR-PT7 — Only the SI columns are kept.** 🟢 `J, Pe, Ct, Cp` plus `PWR` (W),
  `Torque` (N·m), `Thrust` (N) at fixed indices `1,2,3,4,8,9,10`; the imperial
  Hp/In-Lbf/Lbf columns are discarded and rows with fewer than 11 fields are
  skipped.
- **BR-PT8 — Blade count is a digit suffix, letters are not.** 🟢
  `_BLADE_COUNT_RE = -([3-9])$` on the **variant**: `""`→2, `"E"`→2, `"-4"`→4,
  `"E-3"`→3, and crucially `"M-JK"`→2 — marine/rotation letter suffixes
  (`M-JK`, `MRF-RH`, `P-LH`, `R-RH`) are not blade counts (gh-1004).
- **BR-PT9 — `model_ref` is the join key, with `.` → `p`.** 🟢
  `apc/<designation>`, so `10.5x4.5` becomes `apc/10p5x4p5`. It joins
  `propeller_polars` to `components`.
- **BR-PT10 — Reimport freshness is a proxy, not deep equality.** 🟢
  `_records_equal` compares `source_version`, `source_url`, `variant`, and the
  "row lacks `weight_g` but the snapshot has one" case. The docstring states the
  limitation: *if APC corrects polar data without bumping `source_version` the
  change is skipped; run with `force=True`.*
- **BR-PT11 — Samples are replaced wholesale.** 🟢 `_upsert_samples` deletes
  every sample of the propeller and re-inserts; there is no per-sample diff and
  no unique constraint on `(propeller_id, rpm, J)`.
- **BR-64 — Implausible parsed data is rejected, not written.** 🟢
  `MIN_PLAUSIBLE_WEIGHT_G = 1.0` — a parsed propeller weight below 1 g is
  treated as a kg→g conversion error and counted in `unit_warnings`. Unmatched
  PE0 rows are logged, never dropped silently.
- **BR-63 — User-entered mass always wins.** 🟢 `prop_component_seed` fills
  `mass_g` from `weight_g` on create, backfills a **NULL** `mass_g` when the
  polar later gains a weight, and **never clobbers a non-null** `mass_g`.
- **BR-PT12 — `has_polar` / `polar_id` are batch-resolved.** 🟢
  `component_service._resolve_polar_id` closes the loop so `ComponentRead`
  carries the bridge; `list_components` resolves them in one batch to avoid an
  N+1.

### The performance model

- **BR-65 — Nominal cell voltage is the *loaded* 3.7 V.** 🟢 Not 4.2 V peak,
  which would inflate power by 13 %. Motor KV is always the **gear-aware**
  `output_kv = kv_rpm_per_volt / (gear_ratio or 1)` — except in the sizing
  modal, which deliberately shows raw KV because the designer is picking a
  motor, not an output shaft.
- **BR-PT13 — Two motor models, selected by data availability.** 🟢
  `rm_ohm` absent ⇒ **Model A**, the fixed-RPM power-limited chain (gh-615);
  `rm_ohm > 0` ⇒ **Model B**, the QPROP 3-parameter torque balance (gh-1006).
  The response's `estimated` flag is `True` for A and `False` for B.
- **BR-PT14 — Model A's power ceiling is the smaller of two limits.** 🟢
  ```
  P_elec_max = min( max_current_a · 3.7 · cells_lipo_max ,          motor limit
                    (cap_mAh/1000) · C_rate · (cells·3.7) )         battery limit
  P_shaft_max = P_elec_max · η_motor          η_motor = efficiency_pct/100 else 0.85
  ```
  Both unknown ⇒ fall back to `V_bat × 100 A` **with a warning**.
- **BR-PT15 — Model B solves the torque balance by bisection.** 🟢
  ```
  Kv_si = output_kv·2π/60 ;  Kt = 1/Kv_si
  I(n)        = (V_term − ω/Kv_si) / Rm
  Q_motor(I)  = (I − I₀)/Kv_si                     I₀ = io_no_load_a or 0
  Q_prop(n)   = Cp·ρ·n²·D⁵ / (2π)                  Cp at J = V/(n·D)
  solve Q_motor − Q_prop = 0 by BISECTION, 80 iterations
    bracket  rpm_hi = free-run V_term·Kv_si·60/2π
             rpm_lo = the back-EMF floor set by max_current_a
    r_lo ≤ 0 -> clamp to rpm_lo ;  r_hi ≥ 0 -> clamp to rpm_hi
  η_motor = (V_term − I·Rm)(I − I₀)/(V_term·I)     clipped to [0,1]
  P_shaft = Q·ω
  ```
  Solved **per velocity point** — RPM becomes load-dependent, which is the
  entire point of the refinement.
- **BR-66 — Propeller efficiency is J-dependent, never a flat constant.** 🟢
  `η_prop = clip(Pe, 0, 1)` interpolated at the advance ratio, with `Pe`
  **recomputed** as `Ct·J/Cp` rather than read from the stored column (0 when
  `Cp ≤ 0` or `J = 0`).
- **BR-PT16 — `J` is clamped to the dataset with an explicit warning.** 🟢
  Interpolation sorts rows by `J`, uses `np.interp` on `Ct` and `Cp`, clamps `J`
  to `[J_min, J_max]` and raises an `extrapolation_warning` — the curve never
  runs off the data silently (ADR 0012).
- **BR-PT17 — `Ct` is clamped at 0; windmilling is out of scope.** 🟢 The
  slightly-negative tail past zero thrust is discarded, so a power-off descent
  reports zero propeller drag. 🟡 A windmilling model is wanted (`Q-PT-10`).
- **BR-PT18 — Torque is always derived, never read.** 🟢 `Q = P/(2π·n)`; the
  stored `Torque_Nm` column loses precision at 3 decimals for low-RPM rows and
  is deliberately unused.
- **BR-PT19 — RPM-aware callers pre-filter to the nearest RPM group.** 🟢
  `compute_prop_operating_point`, `compute_performance_curve` and
  `_prop_torque_demand` filter first; the J-only helper merges all RPMs because
  `Ct(J)` is nearly RPM-independent for standard APC props. 🟡
- **BR-PT20 — Degenerate inputs produce a curve plus a warning, not an error.**
  🟢 `prop_rpm ≤ 0` returns an all-zero curve with *"Computed RPM is zero —
  check motor KV and battery voltage"*; `P_shaft_max < 0.1 W` emits an
  infeasibility warning.
- **BR-PT21 — The module's own air density is exponential, not ISA.** 🟢
  `_air_density = 1.225·exp(−h/8500)` — **not** `asb.Atmosphere`. Above a few
  hundred metres the two disagree. 🟢 One shared ISA helper (`Q-PT-9`).

### Sizing

- **BR-PT22 — The solution space inverts the question.** 🟢 (gh-975) Instead of
  "which parts do I own that fit", it computes "what must I shop for", in
  **pure Python** (no CadQuery, no AeroSandbox) so it runs in the CI fast tier.
  ```
  C_L(V)    = 2·m·g / (ρ·V²·S_ref)
  C_D(V)    = cd0 + C_L² / (π·e·AR)
  P_aero(V) = ½·ρ·V³·S_ref·C_D(V)
  P_elec(V) = P_aero / (η_prop·η_motor·η_esc)
  E_Wh      = P_elec(V_cruise) · t_target_h / DoD
  ```
- **BR-PT23 — Battery current must not double-count efficiency.** 🟢
  `I_peak = P_top_elec / V_sag`, because `P_top_elec` is **already** battery
  power. Dividing again by η would double-count (gh-978 BLOCKER).
- **BR-PT24 — Per-cell derivation.** 🟢
  ```
  V_nom = S·3.7   V_sag = S·3.5
  cap_mAh = E_Wh / V_nom · 1000
  C_min   = (I_peak / (cap_mAh/1000)) · c_margin
  ESC_min = I_peak · esc_margin
  KV ≈ RPM_target / (V_nom · load_rpm_factor),
       RPM_target = V_top / (D · pitch/D) · 60,  D from the APC polar database (Q-PT-3) 🟢
  motor_peak_shaft_w = P_aero(V_top)    / η_prop_mid
  motor_cont_shaft_w = P_aero(V_cruise) / η_prop_mid
  ```
  The motor figures are deliberately **shaft** power so the catalog comparison
  against `max_power_w` is apples-to-apples.
- **BR-PT25 — Every row is computed three times to produce a band.** 🟢 At mid,
  low and high `η_prop`, with the deliberate inversion
  `p_cruise_lo_w = p_cruise_hi_e` — a *higher* efficiency needs *lower* power.
- **BR-PT26 — The feasible region is a sampled C-rate hyperbola.** 🟢
  `C = I_peak/(cap/1000)` over `[cap_floor, 4·cap_floor]` in
  `_HYPERBOLA_SAMPLES = 40` points.
- **BR-PT27 — Every fallback is warned about, never silent.** 🟢 The solution
  space reads the gh-924 context first and appends a named warning for each
  fallback: `s_ref_m2 → 0.25`, `e_oswald → 0.75`, `aspect_ratio → 7.0`,
  `v_cruise (or v_md) → 15 m/s`, `mass → 1.5 kg`, `cd0 → context, then the
  design assumption, then 0.03`. ADR 0012.
- **BR-PT28 — Two domain validations raise.** 🟢 `t_target_min ≤ 0` and
  `V_top ≤ V_cruise` raise `ValidationDomainError` → 422. `V_top` defaults to
  `1.4 · V_cruise`.
- **BR-PT29 — The catalog sweep is a motor × battery cross-product.** 🟢 ESCs
  are *matched*, not swept.
  ```
  total_mass = airframe_mass + motor.mass_g/1000 + battery.mass_g/1000
  η_total    = η_prop · η_motor · η_esc        defaults 0.65 · 0.85 · 0.94
  P_cruise   = endurance_service._power_required(ρ, V, cd0, e, AR, m, S, η_total)
  I_cruise   = P_cruise / V_pack
  reject if  I_cruise > max_current_draw_a
  t_flight   = (cap_Ah / I_cruise) · 0.8 · 60 min       ← 80 % usable capacity
  ESC        = all-of gate on PEAK current (Q-PT-1) 🟢
  confidence = min(t_flight / t_target, 1.0)            ← gh-992: no cliff
  sort by confidence desc, return top 10
  ```
- **BR-PT30 — The drag polar is delegated, not duplicated.** 🟢 The sweep calls
  `endurance_service._power_required` (gh-490 Model A) so there is one drag
  polar in the codebase. The legacy `_required_power_w` shim now raises
  `NotImplementedError` **by design** — an estimate-only mode without geometry
  is no longer allowed.
- **BR-PT31 — Aero parameters follow a 3-tier priority with per-parameter
  warnings.** 🟢 (gh-960) explicit request field → `assumption_computation_
  context` → RC-typical default (`cd0 0.03`, `e 0.8`, `AR 8.0`, `S 0.5 m²`).
- **BR-PT32 — Battery voltage resolution walks four keys.** 🟢
  `voltage_v → voltage → nominal_voltage → cells·3.7 → 11.1 V`, so a
  schema-valid battery is not mis-read as 3S (gh-992).
- **BR-PT33 — An empty catalogue returns explicit warnings, never a silent
  empty table.** 🟢 (gh-992)
- **BR-78 / ADR 0009 — Transactions belong to `get_db()`.** 🟢
- **ADR 0017 — Heavy dependencies are probed at import.** 🟢 The solution space
  and the performance model are pure Python/NumPy; nothing here needs
  CadQuery, and only `endurance_service` reaches the aero stack.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | List components with optional `component_type` and `q` name filters | Must | `GET /components?component_type=battery` → 200 with only batteries; `has_polar` resolved without N+1 |
| RF-02 | CRUD a component, validating `specs` against its type schema on every write | Must | A `brushless_motor` without a required property → 422 `missing_required` |
| RF-03 | Accept unknown `specs` keys | Must | A propeller with `specs.variant` (not in the schema) is created 201 |
| RF-04 | Upload and download a component 3D model | Should | `POST /components/{id}/model` then `GET` returns the same bytes |
| RF-05 | CRUD component types, with `name` and `deletable` immutable after create | Must | `PUT /component-types/{id}` changing `name` leaves it unchanged |
| RF-06 | Refuse to delete a seeded or referenced type | Must | Seeded type → 409; a type with 3 components → 409 naming the count |
| RF-07 | Seed the 12 default types idempotently at startup | Must | Two consecutive startups leave exactly 12 rows |
| RF-08 | Patch newly declared schema fields onto existing seeded types | Should | Adding `rm_ohm` to the seed makes it appear on an already-seeded `brushless_motor` type |
| RF-09 | Import propeller polars from the committed snapshot, upserting on `(manufacturer, name)` | Must | A reimport of an unchanged snapshot reports `skipped`, not `updated` |
| RF-10 | Reject a snapshot record whose `component_type` is not `"propeller"` | Must | The record lands in `ImportResult.errors` and no row is written |
| RF-11 | Replace all samples of a propeller on import | Must | Re-importing halves-then-doubles the sample count correctly, with no duplicates |
| RF-12 | Enrich polars with PE0 weight, inertia and geometry, rejecting sub-gram weights | Must | A parsed 0.043 g weight is counted in `unit_warnings` and not written |
| RF-13 | Mirror polars into `components` idempotently on `model_ref` | Must | Re-running the seed creates nothing new; a NULL `mass_g` is backfilled; a non-null one is preserved |
| RF-14 | Compute `T(V)`, `P_shaft(V)`, `η_prop(J)`, `J`, `rpm` per velocity point | Must | `POST .../powertrain/performance` → 200 with `n_points` samples |
| RF-15 | Select the QPROP model when `rm_ohm > 0`, the fixed-RPM model otherwise | Must | `estimated` is `false` with `rm_ohm`, `true` without |
| RF-16 | Clamp `J` to the dataset and warn instead of extrapolating | Must | A sweep beyond `J_max` returns a human-readable `extrapolation_warning` |
| RF-17 | Fail with 422 on missing motor/battery/propeller specs | Must | A motor without `kv_rpm_per_volt` → 422 naming the component |
| RF-18 | Return an all-zero curve with an explanatory warning when the computed RPM is zero | Must | KV × V_bat × throttle = 0 ⇒ zeros + *"Computed RPM is zero…"* |
| RF-19 | Compute the required-spec solution space per cell count across an η band | Must | `GET .../powertrain/solution-space` → 200 with one `SolutionRow` per requested cell count |
| RF-20 | Warn on every aero/mass fallback rather than defaulting silently | Must | An aircraft with no computation context returns ≥ 4 named warnings |
| RF-21 | Reject `t_target_min ≤ 0` and `V_top ≤ V_cruise` | Must | Both → 422 `ValidationDomainError` |
| RF-22 | Report catalogue availability per row (`has_motor_match` / `has_battery_match` / `has_esc_match`) | Should | An empty catalogue yields all three `false` without failing the request |
| RF-23 | Sweep the catalogue and return the top 10 candidates by confidence | Must | `POST .../powertrain/sizing` → 200 with ≤ 10 recommendations, descending |
| RF-24 | Reject a combination whose cruise current exceeds `max_current_draw_a` | Must | Such a combination never appears in the recommendations |
| RF-25 | Return explicit warnings, not an empty table, when the catalogue lacks motors or batteries | Must | No motors ⇒ `recommendations: []` plus a warning naming the gap |
| RF-26 | Serve pre-fill defaults for the sizing modal | Should | `GET .../powertrain/sizing-modal-params` → 200 with `cd0`, `s_ref_m2`, motors and warnings |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Extensibility | New hardware types are added as **data**, without a migration or a code change (ADR 0013) | `component_types.schema_def`, `validate_specs` | 🟢 |
| Reproducibility | Ingestion is offline and reproducible from a committed snapshot (ADR 0014) | `data/cots/*.json(.gz)`, `scripts/import_*.py` | 🟢 |
| Correctness | The curve never extrapolates silently — `J` is clamped and the clamp is reported | `interpolate_ct_cp_pe:278`; ADR 0012 | 🟢 |
| Correctness | Battery power is not divided by efficiency twice (gh-978) | `powertrain_solution_space_service._per_cell:129-139` | 🟢 |
| Correctness | Motor comparisons use shaft power on both sides | `_catalog_motor_match:192-207` | 🟢 |
| Correctness | Torque is derived from power, never read from the low-precision column | `powertrain_performance` | 🟢 |
| Performance | The solution space is pure Python so it runs in the CI fast tier | module docstring; no ASB/CQ import | 🟢 |
| Performance | `list_components` batch-resolves `polar_id` to avoid an N+1 | `component_service._resolve_polar_id` | 🟢 |
| Performance | The QPROP solve is bounded at 80 bisection iterations per velocity point | `powertrain_performance.py:569` | 🟢 |
| Robustness | Implausible parsed data is rejected and counted, not written (`MIN_PLAUSIBLE_WEIGHT_G`) | `prop_polar_enrich.py:29` | 🟢 |
| Robustness | User-entered mass is never clobbered by an importer | `prop_component_seed` | 🟢 |
| Usability | Every fallback and every infeasibility reaches the response as a warning string | `powertrain_solution_space_service`, `powertrain_sizing_service` | 🟢 |
| Portability | No route in the module requires CadQuery or AeroSandbox | whole module | 🟢 |
| Security | No authentication; model upload accepts a file into the artefact store | ADR 0016, `components.py:170-245` | 🟡 upload validation not audited here |

## Acceptance Criteria

```gherkin
Feature: Data-driven component types

  Scenario: A component is validated against its type schema
    Given the seeded "brushless_motor" type requires kv_rpm_per_volt
    When I POST a brushless_motor without kv_rpm_per_volt
    Then the response status is 422
    And the reason is "missing_required"

  Scenario: Unknown spec keys are accepted
    Given the seeded "propeller" type has no "variant" property
    When I POST a propeller with specs.variant = "E"
    Then the response status is 201
    And the stored specs contain variant

  Scenario: A seeded type cannot be deleted
    When I DELETE the "battery" component type
    Then the response status is 409

  Scenario: A referenced type cannot be deleted
    Given a user-created type with 3 components
    When I DELETE it
    Then the response status is 409
    And the message names the reference count

Feature: Propeller polar ingestion

  Scenario: An unchanged snapshot is skipped
    Given propeller polars already imported from the snapshot
    When I run the import again without force
    Then every record is counted as skipped
    And no samples are deleted

  Scenario: A non-propeller record is an error, not a row
    Given a snapshot record with component_type "battery"
    When I run the import
    Then the record appears in ImportResult.errors
    And no propeller_polars row is written

  Scenario: A sub-gram weight is a unit warning
    Given a PE0 record whose parsed weight is 0.043 g
    When I run the enrichment
    Then weight_g is not written
    And the record is counted in unit_warnings

  Scenario: User-entered mass survives a reseed
    Given a propeller component whose mass_g was edited to 41.0
    And its polar has weight_g 43.3
    When I run seed_propeller_components
    Then mass_g is still 41.0

Feature: Performance curves

  Scenario: The fixed-RPM model is used without Rm
    Given a motor with no rm_ohm
    When I compute the performance curve
    Then every sample has estimated = true
    And the rpm is identical at every velocity

  Scenario: The QPROP model is used with Rm
    Given a motor with rm_ohm 0.05
    When I compute the performance curve
    Then every sample has estimated = false
    And the rpm falls as velocity rises

  Scenario: Extrapolation is clamped and reported
    Given a velocity sweep whose J exceeds the dataset maximum
    When I compute the performance curve
    Then Ct and Cp are evaluated at J_max
    And the response warnings mention the extrapolation

  Scenario: A zero RPM is explained
    Given a motor and battery combination whose computed RPM is 0
    When I compute the performance curve
    Then every sample is zero
    And a warning says "Computed RPM is zero — check motor KV and battery voltage"

  Scenario: A motor without KV is refused
    Given a brushless_motor component with no kv_rpm_per_volt in specs
    When I POST the performance request
    Then the response status is 422
    And the message names the component id and name

Feature: Solution space

  Scenario: One row per cell count
    Given an aeroplane with a computed aero context
    When I GET the solution space with cell_counts 3 and 4
    Then the response has exactly two rows
    And each row has v_nom_v equal to cells * 3.7

  Scenario: Missing context is warned about, not fatal
    Given an aeroplane with an empty assumption_computation_context
    When I GET the solution space
    Then the response status is 200
    And warnings name s_ref_m2, e_oswald, aspect_ratio and v_cruise

  Scenario: An impossible mission is refused
    Given V_top 12 m/s and V_cruise 15 m/s
    When I GET the solution space
    Then the response status is 422

Feature: Catalog sizing sweep

  Scenario: Recommendations are ranked and capped
    Given 5 motors and 4 batteries in the catalogue
    When I POST a sizing request
    Then at most 10 recommendations are returned
    And they are sorted by confidence descending

  Scenario: An over-current combination is excluded
    Given a combination whose cruise current exceeds max_current_draw_a
    When I POST a sizing request
    Then that combination is absent from the recommendations

  Scenario: An empty catalogue explains itself
    Given no brushless_motor components
    When I POST a sizing request
    Then recommendations is empty
    And a warning names the missing motors
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Component + type CRUD with schema validation (RF-01…RF-07) | Must | Every other feature in the module reads `components`; the type schema is the only integrity mechanism |
| Snapshot ingestion + upsert semantics (RF-09…RF-11) | Must | The 454-propeller dataset is the module's factual base; a broken import silently degrades every curve |
| PE0 enrichment guards (RF-12) | Must | A kg→g error would put a 43 kg propeller on a 1.5 kg aircraft |
| Component mirror with the mass rules (RF-13) | Must | The bridge that lets a propeller be both a polar and a placeable part; the "never clobber" rule protects user data |
| Performance curves + model selection (RF-14/RF-15) | Must | The module's headline capability |
| Extrapolation clamp + warning (RF-16) | Must | The difference between a wrong curve and an honest one (ADR 0012) |
| Missing-spec 422s (RF-17) | Must | The alternative is a silent NaN curve |
| Solution space + fallback warnings (RF-19…RF-21) | Must | The "what do I buy" path; the warnings are what make its defaults trustworthy |
| Catalog sweep + exclusions + empty-catalogue warnings (RF-23…RF-25) | Must | The "what do I own" path |
| Zero-RPM explanation (RF-18) | Should | A degenerate but reachable configuration; the warning is what makes it diagnosable |
| Schema field patching (RF-08) | Should | Avoids a rebuild when a type gains a property; a manual re-seed would also work |
| Catalogue availability flags (RF-22) | Should | Decorates the solution space; the numbers stand without them |
| Sizing-modal pre-fill (RF-26) | Should | A UI convenience over data available elsewhere |
| Model upload/download (RF-04) | Could | Peripheral to propulsion; used by the viewer |
| Windmilling / negative-thrust modelling | **Should** | 🟡 a genuine gap, not deliberate scope (`Q-PT-10`); `Ct` is clamped at 0 today |
| KV from the real propeller diameter | **Must** | 🟢 decided (`Q-PT-3`): use the APC polar database; the fixed 0.30 m constant is removed |
| ISA atmosphere in the powertrain services | Won't | Not implemented — the exponential approximation is used |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/models/component.py` | `ComponentModel` | 🟢 |
| `app/models/component_type.py` | `ComponentTypeModel` (`schema` → `schema_def`) | 🟢 |
| `app/models/prop_polar.py` | `PropellerPolarModel`, `PropellerPolarSampleModel` | 🟢 |
| `app/services/component_service.py` | component CRUD, `_resolve_polar_id`, model upload/download | 🟢 |
| `app/services/component_type_service.py` | type CRUD, `validate_specs:240-271`, `DEFAULT_SEED_TYPES:331`, `seed_default_types:682`, `_patch_schema_fields:710` | 🟢 |
| `app/services/cots_import.py` | snapshot → `components` upsert, `_VALID_COMPONENT_TYPES:26-40` | 🟢 |
| `app/services/prop_polar_import.py` | `import_prop_polars`, `_records_equal`, `_upsert_samples` | 🟢 |
| `app/services/prop_polar_enrich.py` | PE0 enrichment, `MIN_PLAUSIBLE_WEIGHT_G:29` | 🟢 |
| `app/services/prop_component_seed.py` | `seed_propeller_components`, `_specs_from_polar` | 🟢 |
| `app/services/powertrain_performance.py` | `compute_performance_curve`, `interpolate_ct_cp_pe:278`, QPROP solver `:569`, `MotorSpec:82`, `BatterySpec:174` | 🟢 |
| `app/services/powertrain_solution_space_service.py` | `compute_solution_space:239`, `_p_aero:83`, `_p_elec:108`, `_per_cell:116`, `_build_hyperbola:172`, `_catalog_*_match:192-231` | 🟢 |
| `app/services/powertrain_sizing_service.py` | `size_powertrain:275`, `_evaluate_motor_battery_combo`, `_find_matching_esc`, `_compute_confidence`, `_resolve_aero_params` | 🟢 |
| `app/services/powertrain_sizing_modal_service.py` | `get_modal_params` | 🟢 |
| `app/api/v2/endpoints/components.py` | `/components` router (prefix on the router) | 🟢 |
| `app/api/v2/endpoints/component_types.py` | `/component-types` router | 🟢 |
| `app/api/v2/endpoints/aeroplane/powertrain_performance.py` | 1 route + `_resolve_motor` / `_resolve_battery` / `_load_polar_rows` | 🟢 |
| `app/api/v2/endpoints/aeroplane/powertrain_solution_space.py` | 1 route + 15 tunable query params | 🟢 |
| `app/api/v2/endpoints/aeroplane/powertrain_sizing.py` | 1 route | 🟢 |
| `app/api/v2/endpoints/aeroplane/powertrain_sizing_modal.py` | 1 route | 🟢 |
| `scripts/parse_apc_props.py`, `parse_apc_pe0.py`, `enrich_apc_snapshot_pe0.py` | snapshot producers | 🟢 |
| `scripts/import_apc_props.py`, `import_cots.py`, `seed_propeller_components.py` | reimport CLIs | 🟢 |
| `app/services/powertrain_sizing_service.py:55` | `_required_power_w` shim | 🟡 raises `NotImplementedError` by design |
</content>
