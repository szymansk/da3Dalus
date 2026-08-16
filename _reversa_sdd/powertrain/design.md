# powertrain — Technical Design

> Module-level design. Focuses on HOW the module is built, derived from the
> legacy code. Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Endpoint contract: [`contracts.md`](contracts.md).
> Use cases: [`cots-powertrain-components`](cots-powertrain-components/design.md) ·
> [`propeller-polars`](propeller-polars/design.md) ·
> [`performance-model`](performance-model/design.md) ·
> [`powertrain-sizing`](powertrain-sizing/design.md).

## Interface

### Persistence 🟢

| Table | Key | Rows | Owner |
|---|---|---|---|
| `components` | `id`; upserted on `(manufacturer, name)` or `(type, model_ref)` | every hardware part | [`cots-powertrain-components`](cots-powertrain-components/design.md) |
| `component_types` | `name` UNIQUE | 12 seeded + user types | idem |
| `propeller_polars` | `(manufacturer, name)` | 454 APC props | [`propeller-polars`](propeller-polars/design.md) |
| `propeller_polar_samples` | `propeller_id` FK, cascade delete | measurement rows | idem |

### Services 🟢

| Service | Entry point | Kind |
|---|---|---|
| `component_service` | `list_components`, `create/get/update/delete_component`, model up/download | CRUD + polar bridge |
| `component_type_service` | `validate_specs:240`, `seed_default_types:682`, `_patch_schema_fields:710`, type CRUD | dynamic schema registry |
| `cots_import` | snapshot → `components` upsert | ingestion |
| `prop_polar_import` | `import_prop_polars` | ingestion |
| `prop_polar_enrich` | PE0 weight / inertia / geometry | ingestion |
| `prop_component_seed` | `seed_propeller_components` | polar → component mirror |
| `powertrain_performance` | `compute_performance_curve`, `compute_prop_operating_point`, `interpolate_ct_cp_pe` | physics |
| `powertrain_solution_space_service` | `compute_solution_space:239` | required specs |
| `powertrain_sizing_service` | `size_powertrain:275` | catalog sweep |
| `powertrain_sizing_modal_service` | `get_modal_params` | UI pre-fill |
| `endurance_service` | `_power_required` | the **shared** drag polar |

### REST surface 🟢

| Method | Path | Service |
|---|---|---|
| GET | `/components` (`?component_type=`, `?q=`) | `component_service.list_components` |
| GET | `/components/types` | legacy name list |
| POST/GET/PUT/DELETE | `/components[/{component_id}]` | component CRUD |
| POST/GET | `/components/{component_id}/model` | 3D model upload / download |
| GET/POST/PUT/DELETE | `/component-types[/{type_id}]` | dynamic type registry |
| POST | `/aeroplanes/{aeroplane_id}/powertrain/performance` | `compute_performance_curve` |
| GET | `/aeroplanes/{aeroplane_id}/powertrain/solution-space` | `compute_solution_space` |
| GET | `/aeroplanes/{aeroplane_id}/powertrain/sizing-modal-params` | `get_modal_params` |
| POST | `/aeroplanes/{aeroplane_id}/powertrain/sizing` | `size_powertrain` |

## Main Flow

The module has **four largely independent pipelines**. They meet only at
`components` and `propeller_polars`.

```
                       data/apc_raw/**/PER3_*.dat   (gitignored, ~58 MB)
                                  │ scripts/parse_apc_props.py
                                  ▼
   data/cots/*.json ──┐   data/cots/apc_props.json.gz   (COMMITTED, ~8 MB)
   (dpower, batteries)│              │ enrich_apc_snapshot_pe0.py (+PE0)
                      │              ▼
        cots_import ──┤     prop_polar_import ──► propeller_polars
                      │                            + propeller_polar_samples
                      ▼                                   │
                  components ◄────── prop_component_seed ─┘
                      │
     ┌────────────────┼─────────────────────┬────────────────────┐
     ▼                ▼                     ▼                    ▼
 performance     solution space        sizing sweep         sizing modal
 (T,P,η per V)   (required specs)      (owned parts)        (pre-fill)
```

### F1 — The component library 🟢

`components` is one table for every type. `validate_specs` runs on every write:
it looks the type up in `component_types`, walks its `PropertyDefinition` list,
and enforces presence, python type, `min`/`max` and `options` — while **never**
rejecting an unknown key. See
[`cots-powertrain-components`](cots-powertrain-components/design.md).

### F2 — The polar pipeline 🟢

Three stages, all offline, whose durable artefact is a committed snapshot:
parse → enrich (PE0) → import, then a fourth stage mirrors each polar into a
`components` row keyed on `model_ref`. See
[`propeller-polars`](propeller-polars/design.md).

### F3 — The performance model 🟢

Given a motor, a battery, a propeller polar and a velocity sweep, the service
produces `(V, T, P_shaft, η_prop, J, rpm, estimated)` per point under one of two
motor models, with `Ct`/`Cp` interpolated at the advance ratio and `J` clamped
to the dataset. See [`performance-model`](performance-model/design.md).

### F4 — The two sizing paths 🟢

The **solution space** inverts the question (what must I buy) in pure Python;
the **catalog sweep** answers the direct one (what fits from what I own) by
delegating its physics to `endurance_service._power_required`. See
[`powertrain-sizing`](powertrain-sizing/design.md).

## Alternative Flows

- **Unknown `component_type` on a write:** `ValidationError` → 422 with the
  remediation *"use GET /component-types"*. 🟢
- **Deleting a seeded or referenced type:** 409 with the reference count. 🟢
- **Snapshot record with the wrong `component_type`:** collected into
  `ImportResult.errors`; the import continues. 🟢
- **Unchanged snapshot record:** counted as `skipped` — but only because
  `source_version` / `source_url` / `variant` / missing-`weight_g` all match.
  A silent upstream data correction is missed unless `force=True`. 🟢 COTS reference data is **corrected, not versioned** — corrections propagate to historical snapshots, and that is intended (`Q-PT-7`, maintainer-answered).
- **PE0 weight below 1 g:** rejected into `unit_warnings`; the row keeps its
  previous `weight_g`. 🟢
- **Polar without a `model_ref`:** skipped by the component mirror. 🟢
- **Motor / battery / polar missing a required spec:** 422 from the endpoint
  helper, naming the component id and name. 🟢
- **Propeller polar with no samples:** 422 *"has no sample rows"*. 🟢
- **`J` outside the dataset:** clamped with an `extrapolation_warning`. 🟢
- **`Ct` negative past zero thrust:** clamped to 0 — windmilling drag is
  silently absent. 🟡
- **Computed RPM ≤ 0:** an all-zero curve plus an explanatory warning. 🟢
- **Both motor and battery power limits unknown:** falls back to
  `V_bat × 100 A` with a warning. 🟢
- **`P_shaft_max < 0.1 W`:** infeasibility warning. 🟢
- **QPROP bracket degenerate:** `r_lo ≤ 0` clamps to `rpm_lo`, `r_hi ≥ 0`
  clamps to `rpm_hi` — the solver always returns a number. 🟡
- **Missing aero context on the solution space:** four named fallbacks with
  warnings; the request still succeeds 200. 🟢
- **`t_target_min ≤ 0` or `V_top ≤ V_cruise`:** `ValidationDomainError` → 422.
  🟢 Note the solution-space router maps it via
  `HTTP_422_UNPROCESSABLE_CONTENT` while the sibling routers use
  `HTTP_422_UNPROCESSABLE_ENTITY` — the same status code under two spellings.
  🟡
- **Empty catalogue on the sizing sweep:** `recommendations: []` **plus**
  warnings naming what is missing. 🟢
- **No ESC meeting the current:** the candidate is still returned with
  `esc_id = None`. 🟡 A recommendation with no ESC is not flagged as
  incomplete.

## Dependencies

- **`mission-and-sizing`** — `design_assumptions` (mass, cd0) via
  `get_effective_assumption`; `PARAMETER_DEFAULTS`; `endurance_service` for the
  drag polar (`_power_required`, gh-490) and the efficiency defaults
  (`0.65 / 0.85 / 0.94`).
- **`aero-analysis` (gh-924 context)** — `assumption_computation_context` is the
  single source for `s_ref_m2`, `e_oswald`, `aspect_ratio`, `v_cruise_mps` /
  `v_md_mps` and `cd0` (ADR 0004). Both sizing paths read it and warn on every
  fallback.
- **`aeroplane-core`** — the aeroplane row is resolved by UUID on all four
  aeroplane-scoped routes; on `performance` it is an **anchoring formality only**
  — no aeroplane data is read. 🟢
- **`aeroplane-core` component tree** — consumes `components.mass_g` (COTS
  branch) and `specs.density_kg_m3` + `specs.print_resolution_mm` (material
  branch) of the weight ladder.
- **`construction-plans`** — owns the wood/tube seeded types
  (`spar_tube`, `veneer`, `strip`, `triangular_strip`, `grooved_strip`).
- **`wing-design`** — owns the `servo` type and references
  `components.id` from `wing_xsec_ted_servos`.
- **NumPy** — `np.linspace`, `np.interp`, `np.clip` throughout the performance
  model. No AeroSandbox, no CadQuery anywhere in the module. 🟢
- **`app/db/session.py` (`get_db`)** — owns the transaction (ADR 0009). The
  reimport CLIs commit once at the end, outside the request cycle.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| One `components` table with a data-driven per-type schema instead of a table per type | ADR 0013; `component.py`, `component_type.py` | 🟢 |
| The type schema is a floor, not a complete contract — unknown keys pass | `validate_specs:240-271`; BR-60 | 🟢 |
| The taxonomy is seeded, idempotent and undeletable, but user-extensible | `DEFAULT_SEED_TYPES:331`, `deletable=False` | 🟢 |
| Ingestion reads a committed snapshot, never the network or the raw vendor files | ADR 0014 | 🟢 |
| Freshness is decided by `source_version`; corrections propagate to snapshots by design (`Q-PT-7`) 🟢 | `_records_equal`; BR-PT10 | 🟢 (a 🔴 limitation) |
| Samples are replaced wholesale rather than diffed | `_upsert_samples` | 🟢 |
| Implausible parsed data is rejected and counted, not written | `MIN_PLAUSIBLE_WEIGHT_G = 1.0` | 🟢 |
| A user-entered mass is never overwritten by an importer | `prop_component_seed`; BR-63 | 🟢 |
| Two motor models coexist, selected by whether `rm_ohm` is present | BR-PT13 | 🟢 |
| `η_prop` is J-dependent and recomputed from `Ct·J/Cp`, never a flat constant | BR-66 | 🟢 |
| Extrapolation is clamped **and reported**, never silent | `interpolate_ct_cp_pe:278`; ADR 0012 | 🟢 |
| Torque is derived from power because the stored column loses precision | BR-PT18 | 🟢 |
| The solution space is deliberately pure Python so it runs in the CI fast tier | module docstring | 🟢 |
| The drag polar exists once, in `endurance_service`, and is delegated to | BR-PT30; the `NotImplementedError` shim | 🟢 |
| Confidence is continuous (`min(t/t_target, 1)`) rather than a pass/fail cliff | gh-992 | 🟢 |
| An empty catalogue explains itself instead of returning an empty table | gh-992 | 🟢 |
| The sizing modal shows **raw** KV while the physics uses gear-aware `output_kv` | BR-65 | 🟢 |
| The module's air density is `1.225·exp(−h/8500)`, not `asb.Atmosphere` | 🟢 replaced by one shared ISA helper (`Q-PT-9`) | `powertrain_performance.py:346` | 🟢 (a 🔴 divergence) |

## Internal State

| State | Where | Lifecycle |
|---|---|---|
| The component library | `components` | user CRUD + importer upserts; **shared** across all aircraft (`EXCLUDED_TABLES` in the clone registry) |
| The type registry | `component_types` | seeded at startup, patched additively, user-extensible; also shared |
| The polar dataset | `propeller_polars` + `propeller_polar_samples` | written only by the importers; samples cascade-delete with their header |
| Performance curves, solution-space rows, sizing candidates | nowhere | computed per request and discarded |
| `has_polar` / `polar_id` on `ComponentRead` | nowhere | resolved per request from `model_ref` |

Nothing in this module is per-aircraft, which is why `versioning` lists
`components`, `component_types`, and the polar tables among the **shared
library** exclusions: a clone points at the same rows. 🟢

## Observability

- `ImportResult` / `SeedResult` carry `imported` / `created`, `updated`,
  `skipped`, `errors[]` (+ `unit_warnings` on the PE0 enricher) — the ingestion
  pipelines are the best-instrumented part of the module. 🟢
- Every computation route returns a `warnings: list[str]` and the performance
  response additionally carries `notes` naming the model that produced it. 🟢
- `logger.exception` on the defensive 500 in the solution-space and modal
  routers; per-router catch-alls disappear with the single envelope (`Q-CC-3`). 🟢
- Unmatched PE0 rows and filename-fallback parses are logged by the scripts. 🟢
- No metrics or counters: nothing records how often a curve is extrapolated,
  how often a sizing sweep returns zero candidates, or how often a motor's
  QPROP path is taken. 🟡

## Risks and Gaps

- 🟢 **`Rm` is NOT a prerequisite: the fixed-RPM model stays the default** (`Q-PT-6`, expert consensus endorsed by the maintainer). Investigated and closed — D-Power publishes no `rm_ohm` and its PDFs are one-row-per-motor spec tables. Previously:, so the QPROP path is dormant
  for every seeded motor. The shipped model is the fixed-RPM approximation whose
  own docstring calls it a simplification.
- 🟢 **An all-of gate on peak current replaces first-match** (`Q-PT-1`); previously the first ESC in query order, not the
  smallest or lightest that fits — `db.query(...).all()` has no `ORDER BY`, so
  the recommendation is arbitrary and unstable across databases.
- 🟢 **Propeller mass is added to the total** (`Q-PT-2`). Previously motor mass counted, propeller mass not: `size_powertrain` adds
  motor + battery mass to `airframe_mass_kg`; the propeller's now-known mass
  (gh-1000/1017) never enters the total.
- 🟢 **KV comes from the APC polar database** (`Q-PT-3`); the fixed 0.30 m approximation is removed. Previously:, documented
  as a Phase-1 approximation — while the complete APC database sits in the same
  service layer.
- 🟢 **The `component_types` schema is a complete contract, binding for every writer including the seeds** (`Q-PT-5`, maintainer-answered). It writes
  `ComponentModel` rows directly, so a polar with a NULL `diameter_in` /
  `pitch_in` produces a component that violates the seeded `propeller` schema
  and will 422 on its first API `PUT`.
- 🟢 **The schema is binding; `variant` is either added to it or rejected** (`Q-PT-5`). It is written
  by the seed and accepted only because unknown keys are never rejected.
- 🟢 **One canonical vocabulary — the Pydantic spec models; importers normalise** (`Q-PT-4`). Previously two coexisted: The sizing service reads
  `continuous_current_a` with a `max_continuous_a` fallback; the solution space
  reads `max_current_a` with a `continuous_current_a` fallback and
  `c_rating`/`discharge_c`, while `BatterySpec` reads `c_rate`. A battery
  imported with `c_rating` is invisible to the performance model.
- 🟡 **Windmilling drag is a genuine gap, not deliberate scope** (`Q-PT-10`, expert consensus endorsed by the maintainer) — a windmilling model is wanted. Today `Ct` clamped at 0 means a power-off — `Ct` clamped at 0 means a power-off
  descent reports zero propeller drag.
- 🟢 **One shared ISA helper wrapping `asb.Atmosphere`** (`Q-PT-9`, expert consensus endorsed by the maintainer) replaces the duplicated exponential. Previously `1.225·exp(−h/8500)` is duplicated across three services
  while the aero stack uses `asb.Atmosphere`; above a few hundred metres they
  disagree.
- 🟢 **One taxonomy — the `component_types` schema is the complete binding contract** (`Q-PT-5`). Previously two copies:
  (`DEFAULT_SEED_TYPES` and `_VALID_COMPONENT_TYPES`).
- 🟢 Translated to English (`Q-CC-5`). Previously German UI labels in the seeded schemas.
- 🟢 **A two-tier inertia guard plus data-integrity constraints are decided** (`Q-PT-12`, expert consensus endorsed by the maintainer). Previously no unique constraint on `(propeller_id, rpm, J)`: — duplicate protection
  relies entirely on `_upsert_samples` deleting first.
- 🟡 **A candidate with `esc_id = None` is returned unflagged**, so the UI
  cannot distinguish "no ESC needed" from "no ESC fits".
- 🟡 **The performance endpoint requires an aeroplane it never reads.** The UUID
  is an anchoring formality; the same computation is not reachable without one.
- 🟡 **`HTTP_422_UNPROCESSABLE_CONTENT` vs `HTTP_422_UNPROCESSABLE_ENTITY`** —
  the same code spelled two ways across the module's routers.
</content>
