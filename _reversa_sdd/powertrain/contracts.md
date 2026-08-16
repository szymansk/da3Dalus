# powertrain — External Contracts

> REST contract read from `app/api/v2/endpoints/components.py`,
> `component_types.py` and the four `aeroplane/powertrain_*.py` routers,
> cross-checked against `code-analysis.md` §Module: powertrain. 🟢
> All routers are mounted with `prefix=""` (`app/main.py:213-215`); the
> `/components` and `/component-types` prefixes live on the routers themselves.
> There is **no** `/api/v2` segment. 🟢

## Error contract 🟢

Every router in the module declares its own `_raise_http`. The mapping is
uniform, the **body is FastAPI's bare `{"detail": …}`** — not the
`{"error": {code, message, details}}` envelope of `aeroplane-core`. 🟢 One envelope everywhere (`Q-CC-3`).

| Service exception | HTTP |
|---|---|
| `NotFoundError` | 404 |
| `ValidationError` / `ValidationDomainError` | 422 |
| `ConflictError` | 409 (components / component-types only) |
| `InternalError` | 500 |
| any other `ServiceException` | 500 |
| any non-`ServiceException` | 500 `{"detail": "Unexpected error: <repr>"}` |

Two spellings of the same status code coexist:
`powertrain_solution_space.py` uses `HTTP_422_UNPROCESSABLE_CONTENT`, every
other router uses `HTTP_422_UNPROCESSABLE_ENTITY`. 🟡

`powertrain_performance.py` raises `HTTPException` **directly** from its
`_resolve_motor` / `_resolve_battery` / `_load_polar_rows` helpers rather than
raising a domain exception — so those 404/422s bypass `_raise_http`. 🟡

## Component library — `/components` 🟢

Router prefix `/components`, tag `components`.

### `GET /components`

| | |
|---|---|
| `operation_id` | `list_components` |
| Query | `component_type: str?` (exact match), `q: str?` (name search) |
| Response | `ComponentList{items: ComponentRead[], total: int}` |
| Status | 200 · 500 |
| Semantics | `has_polar` / `polar_id` are batch-resolved from `model_ref` in one pass — no N+1 |

### `GET /components/types`

| | |
|---|---|
| `operation_id` | `list_component_types` |
| Response | `ComponentTypesResponse{types: string[]}` |
| Status | 200 |
| Note | Backward-compatible **name list**. Prefer `GET /component-types` for the full metadata |

### `POST /components` · `GET|PUT|DELETE /components/{component_id}`

| | |
|---|---|
| `operation_id` | `create_component` · `get_component` · `update_component` · `delete_component` |
| Request (POST/PUT) | `ComponentWrite` |
| Response | `ComponentRead` (DELETE: **204**, no body) |
| Status | **201** / 200 / 200 / **204** · 404 · 409 · 422 · 500 |
| Validation | `specs` is validated against `component_types.schema_def` on **every** write (BR-60) |

`ComponentWrite`:

| Field | Type | Req. | Constraint | Unit |
|---|---|---|---|---|
| `name` | string | yes | `min_length=1` | — |
| `component_type` | string | yes | `min_length=1`; a **free string** validated at the service layer against the registry (gh#83) | — |
| `manufacturer` | string \| null | no | — | — |
| `description` | string \| null | no | — | — |
| `mass_g` | float \| null | no | `ge=0`; `null` = **unknown**, never a silent 0 | **grams** |
| `bbox_x_mm` / `_y_` / `_z_` | float \| null | no | `ge=0` | **mm** |
| `model_ref` | string \| null | no | join key to `propeller_polars.model_ref` | — |
| `specs` | object | no | `{}` — type-specific; **unknown keys accepted** | per property |

`ComponentRead` = `ComponentWrite` + `id`, `created_at`, `updated_at`,
`has_polar: bool = false`, `polar_id: int | null`.

### `POST|GET /components/{component_id}/model`

| | |
|---|---|
| `operation_id` | `upload_component_model` · `download_component_model` |
| Status | 200 · 404 · 422 · 500 |
| Semantics | 3D model (STEP/STL) upload and retrieval; `model_ref` names the stored artefact |

## Type registry — `/component-types` 🟢

Router prefix `/component-types`, tag `component-types`.

| Method | Path | `operation_id` | Status |
|---|---|---|---|
| GET | `` | `list_component_types_v2` | 200 |
| GET | `/{type_id}` | `get_component_type` | 200 · 404 |
| POST | `` | `create_component_type` | **201** · 409 · 422 |
| PUT | `/{type_id}` | `update_component_type` | 200 · 404 · 422 |
| DELETE | `/{type_id}` | `delete_component_type` | 204 · **409** · 404 |

`PropertyDefinition` (one entry of the `schema` list):

| Field | Type | Meaning |
|---|---|---|
| `name` | string | the `specs` key |
| `label` | string | UI label — 🟢 translated to English (`Q-CC-5`) |
| `type` | `number` \| `string` \| `boolean` | validated python type |
| `unit` | string? | display unit |
| `required` | bool | missing ⇒ 422 `missing_required` |
| `min` / `max` | float? | inclusive numeric range |
| `options` | list? | closed value set |

Mutability: `update_type` may change `label`, `description` and `schema`;
**never** `name` or `deletable`. 🟢
Deletion: `deletable=False` (all 12 seeded types) ⇒ **409**; a type referenced by
≥ 1 component ⇒ **409** with the reference count. 🟢

## Performance — `POST /aeroplanes/{aeroplane_id}/powertrain/performance` 🟢

| | |
|---|---|
| `operation_id` | `compute_powertrain_performance` |
| Path | `aeroplane_id: UUID4` — the aeroplane must exist, but **no aeroplane data is read**; the UUID is an anchoring formality 🟡 |
| Request | `PowertrainPerformanceEndpointRequest` |
| Response | `PowertrainPerformanceResponse` |
| Status | 200 · 404 · 422 · 500 |

Request:

| Field | Type | Default | Constraint |
|---|---|---|---|
| `motor_component_id` | int | — | must resolve to `component_type == "brushless_motor"` or **404** |
| `battery_component_id` | int | — | must resolve to `component_type == "battery"` or 404 |
| `propeller_polar_id` | int | — | `propeller_polars.id`; missing ⇒ 404, no samples ⇒ 422 |
| `v_min_ms` | float | `0.0` | `ge=0` |
| `v_max_ms` | float | `30.0` | `gt=0` |
| `n_points` | int | `20` | `1…200` (the service schema allows up to 500) |
| `altitude_m` | float | `0.0` | `ge=0` — 🟢 ISA via one shared `asb.Atmosphere` helper (`Q-PT-9`) |
| `throttle` | float | `1.0` | `0 < t ≤ 1` |

Spec extraction and its 422s:

| Source | Keys read | 422 when missing |
|---|---|---|
| motor | `kv_rpm_per_volt` (or `kv`), `gear_ratio`, `efficiency_pct`, `cells_lipo_max`, `io_no_load_a`, `max_current_a`, `continuous_current_a`, `rm_ohm` | `kv_rpm_per_volt`, `cells_lipo_max` |
| battery | `cells`, `capacity_mah`, `c_rate` | `cells`, `capacity_mah` |
| polar | `diameter_in` + all samples | no sample rows |

Response:

| Field | Type | Meaning |
|---|---|---|
| `samples[]` | `PerformanceSample` | `velocity_ms`, `thrust_n (≥0)`, `p_shaft_w (≥0)`, `eta_prop (0-1)`, `J (≥0)`, `rpm (≥0)`, `estimated` |
| `p_available_w` | float | the shaft-power ceiling |
| `warnings[]` | string[] | extrapolation, zero-RPM, unknown power limits, infeasibility |
| `notes` | string | model provenance — which of the two motor models produced the curve |

`estimated = true` ⇒ Model A (fixed RPM); `false` ⇒ Model B (QPROP). 🟢

## Solution space — `GET /aeroplanes/{aeroplane_id}/powertrain/solution-space` 🟢

| | |
|---|---|
| `operation_id` | `get_powertrain_solution_space` |
| Response | `PowertrainSolutionSpaceResponse` |
| Status | 200 · 404 · **422** (`V_top ≤ V_cruise`, `t_target ≤ 0`) · 500 |

All 15 assumptions are **optional query parameters**; any subset overrides the
spec defaults. `cell_counts` is multi-value
(`?cell_counts=3&cell_counts=4`).

| Query param | Default | Constraint |
|---|---|---|
| `cell_counts` | `[2, 3, 4, 6]` | list of int |
| `eta_prop_lo` / `eta_prop_hi` | `0.65` / `0.78` | `0.01…0.99` |
| `eta_motor` | `0.85` | `0.01…0.99` |
| `eta_esc` | `0.94` | `0.01…0.99` |
| `dod` | `0.80` | `0.01…1.0` |
| `esc_margin` | `1.4` | `≥ 1.0` |
| `c_margin` | `1.25` | `≥ 1.0` |
| `load_rpm_factor` | `0.85` | `0.5…1.0` |
| `prop_pd` | `0.65` | `0.3…1.5` (trainer 0.65 · 3D 0.5 · glider 0.8 · speed 1.0) |
| `t_target_min` | `10.0` | `> 0` |
| `v_top_mps` | `1.4 × V_cruise` | `> 0` |
| `rho` | `1.225` | `> 0` |
| `g` | `9.80665` | `> 0` |

Response:

| Field | Meaning |
|---|---|
| `rows[]` | one `SolutionRow` per cell count |
| `feasible_regions[]` | `FeasibleRegion{cell_count, capacity_floor_mah, i_peak_a, capacity_curve_mah[], c_rate_curve[]}` — the C-rate hyperbola sampled at 40 points over `[cap_floor, 4·cap_floor]` |
| `shopping_specs[]` | `ShoppingSpec{cell_count, battery_min_mah, battery_min_c, battery_v_nom, esc_min_a, motor_min_peak_w, motor_cont_w, kv_approx}` |
| `v_cruise_mps`, `v_top_mps`, `t_target_min` | the resolved inputs |
| `warnings[]` | one per fallback — `s_ref_m2 → 0.25 m²`, `e_oswald → 0.75`, `aspect_ratio → 7.0`, `v_cruise → 15 m/s`, `mass → 1.5 kg`, `cd0 → 0.03` |

`SolutionRow` — scalars at the η band **mid-point**, `_lo`/`_hi` at the band
extremes with the deliberate inversion (`_lo` uses `eta_prop_hi`, because a more
efficient prop needs *less* current):

| Field | Unit |
|---|---|
| `cell_count`, `v_nom_v` (`S·3.7`), `v_sag_v` (`S·3.5`) | – / V / V |
| `p_cruise_w`, `p_cruise_lo_w`, `p_cruise_hi_w` | W (electrical) |
| `p_top_w`, `p_top_lo_w`, `p_top_hi_w` | W (electrical) |
| `energy_wh` | Wh |
| `capacity_mah_min` (+ `_lo`/`_hi`) | mAh |
| `i_peak_a` (+ `_lo`/`_hi`) | A |
| `c_min` (+ `_lo`/`_hi`) | C, **including** `c_margin` |
| `esc_min_a` (+ `_lo`/`_hi`) | A, **including** `esc_margin` |
| `motor_peak_w`, `motor_cont_w` | W **shaft** — comparable with catalogue `max_power_w` |
| `kv_approx` | rpm/V — 🟢 from the APC polar database (`Q-PT-3`) |
| `has_motor_match`, `has_battery_match`, `has_esc_match` | bool — catalogue availability |

Catalogue matching keys 🟢 — the Pydantic spec-model spellings are canonical and importers normalise (`Q-PT-4`). Previously three vocabularies:

| Match | Keys read |
|---|---|
| motor | `max_power_w` \| `max_continuous_power_w` ≥ `motor_peak_w` |
| battery | `capacity_mah` ≥ floor **and** (`c_rating` \| `discharge_c`) ≥ `c_min` |
| ESC | (`max_current_a` \| `continuous_current_a`) ≥ `esc_min_a` |

## Catalog sweep — `POST /aeroplanes/{aeroplane_id}/powertrain/sizing` 🟢

| | |
|---|---|
| `operation_id` | `size_powertrain` |
| Request | `PowertrainSizingRequest` |
| Response | `PowertrainSizingResponse` |
| Status | 200 · 404 · 422 · 500 |

> The path is `/powertrain/sizing` — `code-analysis.md` records it as
> `/powertrain_sizing`; the router is authoritative. 🟢

`PowertrainSizingRequest`:

| Field | Type | Req. | Constraint | Fallback when omitted |
|---|---|---|---|---|
| `airframe_mass_kg` | float | yes | `ge=0` | — |
| `target_cruise_speed_ms` | float | yes | `gt=0` | — |
| `target_top_speed_ms` | float | yes | `gt=0` | — |
| `target_flight_time_min` | float | yes | `gt=0` | — |
| `max_current_draw_a` | float? | no | `ge=0` | no current limit |
| `altitude_m` | float | no | `ge=0`, default `0.0` | — |
| `cd0` | float? | no | `ge=0` | context → `0.03` |
| `e_oswald` | float? | no | `0 < e ≤ 1` | context → `0.8` |
| `aspect_ratio` | float? | no | `gt=0` | context → `8.0` |
| `s_ref_m2` | float? | no | `gt=0` | context → `0.5` |
| `eta_prop` / `eta_motor` / `eta_esc` | float? | no | `0 < η ≤ 1` | `0.65` / `0.85` / `0.94` |

`PowertrainSizingResponse{recommendations: PowertrainCandidate[], warnings:
string[]}` — at most **10**, sorted by `confidence` descending.

`PowertrainCandidate`:

| Field | Meaning |
|---|---|
| `motor_id` / `motor_name` | the selected motor |
| `esc_id` / `esc_name` | the **first** ESC in query order meeting the peak-current all-of gate (`Q-PT-1`) 🟢; `null` when none fits, unflagged 🟡 |
| `battery_id` / `battery_name` | the selected battery |
| `propeller` | free-text diameter/pitch suggestion |
| `estimated_flight_time_min` | `(cap_Ah / I_cruise) · 0.8 · 60`, rounded to 1 dp |
| `estimated_cruise_power_w` | from `endurance_service._power_required`, 1 dp |
| `estimated_top_speed_ms` | echoes the requested target, 1 dp 🟡 |
| `confidence` | `min(t_flight / t_target, 1.0)`, 3 dp, `0…1` |

A combination is **excluded** when `I_cruise > max_current_draw_a`, when the
battery capacity or voltage resolves to `≤ 0`, or when either mass is missing.
An empty motor or battery catalogue yields `recommendations: []` **with**
warnings naming the gap. 🟢

## Sizing modal — `GET /aeroplanes/{aeroplane_id}/powertrain/sizing-modal-params` 🟢

| | |
|---|---|
| `operation_id` | `get_powertrain_sizing_modal_params` |
| Response | `PowertrainModalParamsResponse` |
| Status | 200 · 404 · 500 |
| Content | `altitude_m` (0.0), `cd0` (from the gh-924 context, editable), `s_ref_m2` (read-only display), `eta_prop` (0.65), `eta_motor` (0.85), `motors[]` sorted by name with `efficiency_pct` defaulting to 85, `warnings[]` for every defaulted value |
| Note | Deliberately shows the **raw** motor KV, not the gear-aware `output_kv`, because the designer is picking a motor rather than an output shaft (BR-65) |

## Unit contract for this module 🟢

| Quantity | Unit |
|---|---|
| `mass_g`, `weight_g` | **grams** |
| `bbox_*_mm` | millimetres |
| `diameter_in`, `pitch_in` | **inches** (APC source units) |
| `inertia_kg_m2` | kg·m² |
| `J`, `Ct`, `Cp`, `Pe`, `eta_*`, `confidence` | dimensionless |
| `PWR_W`, `p_shaft_w`, `p_cruise_w`, `motor_*_w` | watts |
| `Torque_Nm` | N·m (stored, deliberately unused) |
| `Thrust_N`, `thrust_n` | newtons |
| `rpm` | rev/min |
| `capacity_mah` | mAh · `energy_wh` Wh · `i_peak_a` A · `c_min` C |
| `v_*_mps`, `velocity_ms` | m/s |
| `s_ref_m2` | m² · `altitude_m` m · `rho` kg/m³ |
| `kv_rpm_per_volt`, `kv_approx` | rpm/V |
| `rm_ohm` | ohm |
| `g` | `9.80665` m/s² — 🟡 collapses into one physical-constants module with `mass-and-balance` (`Q-MB-8`) |

## Snapshot contract (`data/cots/apc_props.json.gz`) 🟢

The durable reimport source, produced by `scripts/parse_apc_props.py`:

```jsonc
{
  "manufacturer": "APC",
  "name": "APC 10x10E",
  "component_type": "propeller",          // validated == "propeller", else an error
  "model_ref": "apc/10x10E",              // "." -> "p": 10.5x4.5 -> apc/10p5x4p5
  "source_url": "https://www.apcprop.com/files/PER3_10x10E.dat",
  "source_version": "v2022-01",           // the freshness proxy for skip-on-reimport
  "specs": { "diameter_in": 10.0, "pitch_in": 10.0, "variant": "E", "blades": 2,
             "weight_g": 43.3, "inertia_kg_m2": 1.2e-5 },
  "geometry": [ /* per-station blade rows, PE0 */ ],
  "polars": [ { "rpm": 3000, "samples": [ {"J":…,"Pe":…,"Ct":…,"Cp":…,
                                           "PWR_W":…,"Torque_Nm":…,"Thrust_N":…} ] } ]
}
```

Sibling snapshots: `dpower.json` (motors/ESCs), `generic_batteries.json`,
`spektrum_avian.json`, `carbon_tubes.json`, `hoellein_wood.json`.

`ImportResult` / `SeedResult`: `imported`/`created`, `updated`, `skipped`,
`errors[]`, plus `unit_warnings` on the PE0 enricher. 🟢

## Not part of this contract

- `GET /aeroplanes/{id}/endurance` → `mission-and-sizing` (it shares
  `_power_required` but is a different module's route).
- The component tree's consumption of `mass_g` / `density_kg_m3` /
  `print_resolution_mm` → [`aeroplane-core`](../aeroplane-core/contracts.md).
- Servo components as wing hardware → `wing-design`.
- Wood and tube component types → `construction-plans`.
</content>
