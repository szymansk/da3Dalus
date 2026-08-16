# mission-and-sizing — External Contracts

> REST contract as captured in `_reversa_sdd/code-analysis.md` §Module:
> mission-and-sizing and **verified against the route decorators** in
> `app/api/v2/endpoints/aeroplane/{design_assumptions,mission_objectives,
> loading_scenarios,flight_envelope,matching_chart,field_lengths,
> sm_suggestions,forward_cg}.py` and `app/api/v2/endpoints/flight_profiles.py`.
> Confidence markers: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Companion documents: [`requirements.md`](requirements.md),
> [`design.md`](design.md), [`tasks.md`](tasks.md).

🟢 Every route below is mounted at the **application root** — `prefix=""`.
`app/main.py:211` mounts `aeroplane_v2.router` with `prefix=""`, and
`app/api/v2/endpoints/aeroplane/__init__.py:34-57` composes the sub-routers
without a prefix of their own; `flight_profiles.router` is mounted the same way
at `app/main.py:220`. There is **no** `/api/v2` path segment on this module's
routes (only `openvsp_import` carries that prefix, `app/main.py:212`).

🟡 [`design.md`](design.md) §Interface says "26 routes across nine endpoint
modules". The decorator enumeration below yields **33 routes owned by this
module** plus **2 generation routes hosted on the operating-point router**. The
enumeration wins; the 26 is a stale count.

---

## Global error contract — 🟢 **One error envelope everywhere; the seven local mappers are deleted** (`Q-CC-3`, maintainer-answered).

Unlike `aero-analysis`, which funnels every handler through one
`_raise_http_from_domain` and one `{"error": {code, message, details}}`
envelope, this module ships **five different local mappers** and returns
FastAPI's bare `{"detail": "…"}` body. 🟢

| Mapper (file) | `NotFoundError` | `ValidationError` / `ValidationDomainError` | `ConflictError` | `InternalError` | bare `ServiceException` |
|---|---|---|---|---|---|
| `design_assumptions.py:42-54` `_raise_http` | 404 | 422 | 409 | 500 | **500** |
| `loading_scenarios.py:32-42` `_raise_http` | 404 | 422 | 409 | 500 | **500** |
| `flight_profiles.py:34-48` `_raise_http_from_domain` | 404 | 422 | 409 | 500 | **500** |
| `forward_cg.py:41-50` `_raise_http` | 404 | 422 | — | 500 | **500** |
| `flight_envelope.py:20-28` `_raise_http_from_domain` | 404 | — | — | 500 | **500** |
| `matching_chart.py:29-37` `_raise_http_from_domain` | 404 | — | — | 500 | **422** ⚠ |
| `field_lengths.py:32-39` `_raise_http_from_domain` | 404 | — | — | 500 | **422** ⚠ |

⚠ **The matching-chart and field-length handlers map a bare `ServiceException`
to 422, every other handler maps it to 500.** 🟢 This is deliberate: those two
services raise a plain `ServiceException` for *user-actionable missing inputs*
("Wing reference area (s_ref_m2) is not available. Trigger an assumption
recompute first.", `field_lengths.py:145-166`), and 422 is the honest answer for
"your aircraft is not ready yet". The cost is that a genuine internal failure in
those two services is also reported as 422. 🟢 One envelope (`Q-CC-3`).

Every handler additionally wraps unexpected exceptions:
`except Exception → 500 "Unexpected error: {exc}"`. 🟢
🟢 🟢 **One error envelope everywhere; the seven local mappers are deleted** (`Q-CC-3`, maintainer-answered). Previously the raw exception text was interpolated on all seven
mappers — it is not sanitised.

**Response body shape** 🟢 one envelope (`Q-CC-3`); previously `HTTPException(detail=<str>)` produced
`{"detail": "…"}`. `aero-analysis` produces `{"error": {"code", "message",
"details"}}`. Both shapes coexist in the same API
(see [`../data-dictionary.md`](../data-dictionary.md) §platform-core, "HTTP
error envelopes — **two coexisting shapes**"). A client cannot parse errors
uniformly across the two modules.

**Non-finite floats** 🟡: none of this module's routers sets
`default_response_class=NonFiniteSafeJSONResponse`. A NaN reaching a
matching-chart `t_w_points` entry or a V-n `load_factor` is **not** neutralised
here, unlike on the analysis router (ADR 0012).

---

## Unit contract for this module 🟢

| Quantity | Wire unit | Storage unit |
|---|---|---|
| all V-speeds (`v_cruise_mps`, `v_stall_mps`, `velocity`, …) | m/s | m/s |
| `alpha`, `beta` in generated OP **responses** | degrees | **radians** on `operating_points` |
| CG positions (`cg_x`, `cg_*_m`, `x_m`, `x_np_m`) | metres | metres |
| `mass`, `mass_kg`, `mass_kg_override` | kg | kg |
| wing loading `ws_n_m2`, `target_wing_loading_n_m2` | N/m² | N/m² |
| `t_static_N`, `bungee_force_N` | N | N |
| field lengths, `available_runway_m`, `stretch_m` | m | m |
| `g_limit`, `n_target`, `load_factor`, `target_maneuver_n` | g (dimensionless load factor) | same |
| `target_static_margin`, `sm_at_fwd`, `sm_at_aft` | **fraction of MAC** (0.12 = 12 %) | same |
| `divergence_pct` | **percent** | percent |
| angles in profiles / chart (`max_bank_deg`, `gamma_climb_deg`, `max_alpha_deg`) | degrees | degrees |
| `power_to_weight` | **W/kg** — 🟢 canonical; the seven T/W-shaped presets are re-authored (`Q-MS-1`, maintainer-answered). Previously seven presets wrote a dimensionless 0.0–1.4 into it — see BR-MS34 |
| `altitude_m`, `wind_mps` | m, m/s | m, m/s |

`{aeroplane_id}` / `{uuid}` is always the **public UUID** (`pydantic.UUID4`),
never the integer PK. 🟢 `{profile_id}` and `{scenario_id}` are **integer PKs**
(`ge=1` on the profile path parameter). 🟢

---

## A. Design assumptions — `aeroplane/design_assumptions.py` (9 routes) 🟢

| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/assumptions` | — | `AssumptionsSummary` | **201** · 404 · 422 · 500 |
| GET | `/aeroplanes/{aeroplane_id}/assumptions` | — | `AssumptionsSummary` | 200 · 404 · 500 |
| PUT | `/aeroplanes/{aeroplane_id}/assumptions/{param_name}` | `AssumptionWrite` | `AssumptionRead` | 200 · 404 · 422 · 500 |
| PATCH | `/aeroplanes/{aeroplane_id}/assumptions/{param_name}/source` | `AssumptionSourceSwitch` | `AssumptionRead` | 200 · 404 · **422** · 500 |
| GET | `/aeroplanes/{aeroplane_id}/assumptions/recompute-status` | — | `{status, started_at, finished_at, error}` | 200 · 404 |
| POST | `/aeroplanes/{aeroplane_id}/recompute` | — | same job envelope | **202** · 404 |
| GET | `/aeroplanes/{aeroplane_id}/assumptions/computation-context` | — | `dict \| null` | 200 · 404 |
| GET | `/aeroplanes/{aeroplane_id}/computation-config` | — | `ComputationConfigRead` | 200 · 404 |
| PUT | `/aeroplanes/{aeroplane_id}/computation-config` | `ComputationConfigWrite` | `ComputationConfigRead` | 200 · 404 · 422 |

🟢 `{param_name}` is constrained **by the path regex**
`^(mass|cg_x|target_static_margin|cd0|cl_max|g_limit|power_to_weight|prop_efficiency|battery_capacity_wh|battery_specific_energy_wh_per_kg|propulsion_eta_motor|propulsion_eta_esc|motor_continuous_power_w|t_static_N|design_speed_mps)$`,
built at import time from `PARAMETER_DEFAULTS.keys()`
(`design_assumptions.py:40`). An unknown name is therefore a **FastAPI 422 path
validation error**, not a service 404.

### `AssumptionWrite` (request) 🟢

| Field | Type | Note |
|---|---|---|
| `estimate_value` | float, `allow_inf_nan=False` | NaN/Inf are rejected by the schema |

### `AssumptionSourceSwitch` (request) 🟢

| Field | Type | Note |
|---|---|---|
| `active_source` | `"ESTIMATE"` \| `"CALCULATED"` | |

**422 conditions on the PATCH** 🟢 (`design_assumptions_service.switch_source`):

1. `active_source = "CALCULATED"` for a `DESIGN_CHOICE_PARAMS` member →
   `"Parameter '<name>' is a design choice and cannot use CALCULATED source"`.
2. `active_source = "CALCULATED"` while `calculated_value IS NULL` →
   `"No calculated value available for '<name>'"`.

### `AssumptionRead` (response) 🟢

| Field | Type | Note |
|---|---|---|
| `id` | int | |
| `parameter_name` | one of the 15 catalogued names | |
| `estimate_value` | float | the user's manual value |
| `calculated_value` | float \| null | written by the compute/aggregation services |
| `calculated_source` | str \| null | e.g. `aerobuildup`, `best_glide_v_md`, `stability_analysis` |
| `active_source` | `ESTIMATE` \| `CALCULATED` | |
| `effective_value` | float | `calculated` if `CALCULATED` **and** non-null, else `estimate` |
| `divergence_pct` | float \| null | `round(\|est − calc\| / \|calc\| · 100, 1)`; **null when `calc` is null or `calc == 0`** |
| `divergence_level` | `none` \| `info` \| `warning` \| `alert` | `<5` none · `<15` info · `≤30` warning · else alert |
| `unit` | str | from `PARAMETER_UNITS`; `""` when dimensionless |
| `is_design_choice` | bool | membership in `DESIGN_CHOICE_PARAMS` |
| `updated_at` | datetime | |

`AssumptionsSummary` = `{assumptions: AssumptionRead[], warnings_count: int}`,
where `warnings_count` counts levels `warning` **and** `alert`. 🟢

### The parameter catalogue — 15 rows seeded 🟢

(`app/schemas/design_assumption.py:72-108`)

| Parameter | Unit | Default | Design choice | Calculated by |
|---|---|---|---|---|
| `mass` | kg | `1.5` | no | weight-item / component-tree sync |
| `cg_x` | m | `0.15` | no | `x_np − target_SM·MAC` (recompute, BR-28) |
| `target_static_margin` | fraction MAC | `0.12` | **yes** | — |
| `cd0` | — | `0.03` | no | **parasite** CD0 — 🟢 one authority from the cruise point (`Q-AA-*`, gh-924); previously total CD on the stability path |
| `cl_max` | — | `1.4` | no | fine α×V sweep maximum |
| `g_limit` | g | `3.0` | **yes** | — |
| `power_to_weight` | W/kg | `220.0` | no | powertrain (future) |
| `prop_efficiency` | — | `0.65` | no | powertrain (future) |
| `battery_capacity_wh` | Wh | `0.0` (= unset) | **yes** | — |
| `battery_specific_energy_wh_per_kg` | Wh/kg | `180.0` (pack-level LiPo) | **yes** | — |
| `propulsion_eta_motor` | — | `0.85` | **yes** | — |
| `propulsion_eta_esc` | — | `0.94` | **yes** | — |
| `motor_continuous_power_w` | W | `0.0` (= unset) | **yes** | — |
| `t_static_N` | N | `0.0` (glider / unknown) | no | — |
| `design_speed_mps` | m/s | `15.0` | no | `V_md` via `best_glide_v_md` (gh-935) |

🟡 `min_static_margin` / `max_static_margin` are **read** by `stability_service`
but are absent from `VALID_PARAMETERS`, absent from `PARAMETER_DEFAULTS`, and
never seeded — so they cannot be reached through this contract at all.

### The recompute job envelope 🟢

`GET …/assumptions/recompute-status` and `POST …/recompute` return the **same**
shape, read from `app.core.background_jobs.job_tracker`:

```json
{ "status": "idle | pending | running | done | failed",
  "started_at": "ISO-8601 | null",
  "finished_at": "ISO-8601 | null",
  "error": "string | null" }
```

`status` is `job.status.value.lower()`; with no job row it is `"idle"` with
three nulls. 🟢
🟡 `POST …/recompute` answers **202 Accepted** even when no event loop was
available to schedule the task — it returns `status: "idle"` and the client must
notice. The request was accepted; the work may not have started.

### `ComputationConfigRead` / `ComputationConfigWrite` 🟢

| Field | Read | Write (all optional) | Default |
|---|---|---|---|
| `id`, `aeroplane_id` | int | — | — |
| `coarse_alpha_min_deg` | float | float | `−5.0` |
| `coarse_alpha_max_deg` | float | float | `25.0` |
| `coarse_alpha_step_deg` | float | float `gt=0` | `1.0` |
| `fine_alpha_margin_deg` | float | float `gt=0` | `5.0` |
| `fine_alpha_step_deg` | float | float `gt=0` | `0.5` |
| `fine_velocity_count` | int | int `ge=2, le=50` | `8` |
| `debounce_seconds` | float | float `ge=0.5, le=30.0` | `2.0` |

🟢 Both GET and PUT **create the row on demand** from
`COMPUTATION_CONFIG_DEFAULTS` when it does not exist — a read is a write. The
PUT merges with `model_dump(exclude_none=True)`, so a `null` field keeps its
current value.
🟡 There is no cross-field validation: `coarse_alpha_min_deg = 30` with
`coarse_alpha_max_deg = 10` is accepted and produces an empty sweep.

---

## B. Mission objectives, presets and KPIs — `aeroplane/mission_objectives.py` (4 routes) 🟢

| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| GET | `/aeroplanes/{uuid}/mission-objectives` | — | `MissionObjective` | 200 · 404 |
| PUT | `/aeroplanes/{uuid}/mission-objectives` | `MissionObjective` | `MissionObjective` | 200 · 404 · 422 |
| GET | `/mission-presets` | — | `MissionPreset[]` | 200 |
| GET | `/aeroplanes/{uuid}/mission-kpis` | query `missions: str[]` (repeatable, default `[]`) | `MissionKpiSet` | 200 · 404 · **500** |

🟢 The GET on `mission-objectives` **never 404s on a missing row** — it returns
`_default_objective()` (`mission_type="trainer"`, cruise 18 m/s, stall safety
1.8, n 3.0, L/D 12, climb energy 22, W/S 412 N/m², field 50 m, runway 50 m
grass, `t_static_N` 18 N, takeoff `runway`). The 404 is only for an unknown
aeroplane UUID.

### `MissionObjective` (request **and** response) 🟢

| Field | Type | Validation | Default (server) |
|---|---|---|---|
| `mission_type` | str | required; 🟢 FK → `mission_presets.id` declared (`Q-CC-7`) | `"trainer"` |
| `target_cruise_mps` | float | `ge=0` | `18.0` |
| `target_stall_safety` | float | `ge=1.0` (`V_cruise/V_s1`) | `1.8` |
| `target_maneuver_n` | float | `ge=1.0` | `3.0` |
| `target_glide_ld` | float | `ge=0` | `12.0` |
| `target_climb_energy` | float | `ge=0` (`C_L^1.5/C_D`) | `22.0` |
| `target_wing_loading_n_m2` | float | `ge=0` | `412.0` |
| `target_field_length_m` | float | `ge=0` | `50.0` |
| `available_runway_m` | float | `ge=0` | `50.0` |
| `runway_type` | `grass` \| `asphalt` \| `belly` | | `"grass"` |
| `t_static_N` | float | `ge=0` | `18.0` |
| `takeoff_mode` | `runway` \| `hand_launch` \| `bungee` \| `catapult` | | `"runway"` |
| `landing_surface` | `grass_short` \| `grass_long` \| `hard_paved` \| `soft_soil` \| `belly_grass` \| `net_recovery` \| null | gh-477 | `null` |
| `landing_safety_factor` | float \| null | `ge=1.0, le=3.0` | `null` ⇒ service uses `1.5` |
| `available_field_length_m` | float \| null | `ge=0` | `null` ⇒ no sufficiency check |

**Side effect of the PUT** 🟢: when `mission_type` differs from the stored value
(including the first create), `_apply_preset_estimates` writes the preset's
`suggested_estimates` into `design_assumptions.estimate_value` for
`g_limit`, `target_static_margin`, `cl_max`, `power_to_weight`,
`prop_efficiency` — and **only** `estimate_value`. `calculated_value`,
`calculated_source` and `active_source` are untouched.
🟢 An unknown `mission_type` fails visibly (`Q-MS-10`/`P-WARN-0`). Previously a silent no-op: HTTP 200, no estimate
changes, no warning. The docstring explicitly defers the rejection to the KPI
service, which does not reject either (it falls back to `trainer`).

### `MissionPreset` (response) 🟢

| Field | Type | Note |
|---|---|---|
| `id` | str | stable id, **String primary key** |
| `label`, `description` | str | |
| `target_polygon` | `{axis: 0..1}` | the Soll polygon, 7 axes |
| `axis_ranges` | `{axis: [min, max]}` | tuples in the schema, **lists** in the DB column |
| `suggested_estimates` | `MissionPresetEstimates` | `g_limit`, `target_static_margin`, `cl_max`, `power_to_weight`, `prop_efficiency` |

Axes (`AxisName`): `stall_safety`, `glide`, `climb`, `cruise`, `maneuver`,
`wing_loading`, `field_friendliness`. 🟢
Nine seeded ids: `trainer`, `sport`, `sailplane`, `wing_racer`, `acro_3d`,
`stol_bush`, `slope_soarer`, `motor_glider`, `flying_wing`. 🟢

### `MissionKpiSet` (response) 🟢

| Field | Type | Note |
|---|---|---|
| `aeroplane_uuid` | str | |
| `ist_polygon` | `{axis: MissionAxisKpi}` | exactly 7 entries, always present |
| `target_polygons` | `MissionTargetPolygon[]` | one per **resolvable** id in `missions`; unknown ids are silently dropped |
| `active_mission_id` | str | `missions[0]`, else `objective.mission_type` |
| `computed_at` | ISO-8601 UTC | |
| `context_hash` | str, **exactly 64 chars** | `sha256(json.dumps(ctx, sort_keys=True))` |

`MissionAxisKpi` = `{axis, value \| null, unit \| null, score_0_1 \| null,
range_min, range_max, provenance ∈ {computed, estimated, missing}, formula,
warning \| null}`. 🟢 A `missing` axis renders as a polygon gap and carries the
user-facing reason in `warning` (e.g. *"Set t_static_N…"*).

🟢 **500, not 404, when the preset table is empty**: with neither the requested
id nor a `trainer` fallback present, `compute_mission_kpis` raises a
`RuntimeError` — a deliberate loud failure instead of a degenerate empty radar.
The user-controlled mission id is kept out of the log line (Sonar S5145) and
only echoed in the exception message.

---

## C. Flight profiles — `flight_profiles.py` (7 routes) 🟢

| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| POST | `/flight-profiles` | `RCFlightProfileCreate` | `RCFlightProfileRead` | **201** · 409 · 422 · 500 |
| GET | `/flight-profiles` | query `type?`, `skip ≥ 0 = 0`, `limit ∈ [1,500] = 100` | `RCFlightProfileRead[]` | 200 · 500 |
| GET | `/flight-profiles/{profile_id}` | `profile_id ≥ 1` | `RCFlightProfileRead` | 200 · 404 · 500 |
| PATCH | `/flight-profiles/{profile_id}` | `RCFlightProfileUpdate` | `RCFlightProfileRead` | 200 · 404 · 409 · 422 · 500 |
| DELETE | `/flight-profiles/{profile_id}` | — | `{status, operation}` | 200 · 404 · **409** · 500 |
| PUT | `/aeroplanes/{aeroplane_id}/flight-profile/{profile_id}` | — | `AircraftFlightProfileAssignmentRead` | 200 · 404 · 500 |
| DELETE | `/aeroplanes/{aeroplane_id}/flight-profile` | — | `AircraftFlightProfileAssignmentRead` | 200 · 404 · 500 |

🟢 **409 on delete** while any aeroplane still references the profile — the
central referential guarantee of the global library (BR-MS6).
🟢 The assignment PUT **overwrites** an existing assignment; the DELETE sets
`aeroplanes.flight_profile_id = NULL`. Both return
`{aircraft_id: str, flight_profile_id: int | null}`.
🟡 The `flight_profiles` handlers carry **German docstrings**, which surface
verbatim in the generated OpenAPI of an English-only product.

### `RCFlightProfileCreate` 🟢 — `extra="forbid"` on every nested model

| Block | Field | Validation | Default |
|---|---|---|---|
| — | `name` | 3–64 chars, `^[a-zA-Z0-9_\- ]+$`, no leading/trailing space, **unique** | required |
| — | `type` | `trainer` \| `warbird` \| `fpv_cruiser` \| `3d` \| `glider` \| `motor_glider` \| `slope_soarer` \| `flying_wing` \| `custom` | required |
| `environment` | `altitude_m` | `−100 … 6000` | `0` |
| | `wind_mps` | `0 … 25` | `0` |
| `goals` | `cruise_speed_mps` | `> 0` | **required** |
| | `max_level_speed_mps` | must be `> cruise_speed_mps` | `null` |
| | `min_speed_margin_vs_clean` | `1.05 … 1.60` | `1.20` |
| | `takeoff_speed_margin_vs_to` | `1.05 … 1.80` | `1.25` |
| | `approach_speed_margin_vs_ldg` | `1.10 … 2.00` | `1.30` |
| | `target_turn_n` | `1.0 … 4.0` | `2.0` |
| | `loiter_s` | `0 … 10800` | `null` |
| `handling` | `stability_preference` | `stable` \| `neutral` \| `agile` | `stable` |
| | `roll_rate_target_dps` | `10 … 600` | `null`; **auto-set to 240 when `agile`** |
| | `pitch_response` | `smooth` \| `balanced` \| `snappy` | `smooth` |
| | `yaw_coupling_tolerance` | `low` \| `medium` \| `high` | `low` |
| `constraints` | `max_bank_deg` | `0 … 85` | `60` |
| | `max_alpha_deg` | `0 … 25` | `null` |
| | `max_beta_deg` | `0 … 30` | `null` |

**Cross-field validators** 🟢:

```
max_level_speed_mps > cruise_speed_mps                       (Goals)
target_turn_n ≤ 1/cos(max_bank_deg) + 0.05                   (Create)
   "target_turn_n is greater than what is achievable with max_bank_deg."
stability_preference == agile and roll_rate_target_dps is None
   → roll_rate_target_dps = 240                              (Handling)
```

🟢 🟢 **`n` becomes derived from bank and climb angle (`n = cos γ/cos φ`), with explicit overrides carrying a `DesignWarning`** (`Q-MS-13 ①`). Storing both was two producers of one number (ADR 0022), and create-only validation was the worst of both worlds. Previously the check existed only on `RCFlightProfileCreate`. The
PATCH schema `RCFlightProfileUpdate` carries no model validator, so a partial
update can lower `max_bank_deg` below what `target_turn_n` requires.

### `_default_profile()` — the "no profile assigned" contract 🟢

```
environment  altitude_m 0 · wind_mps 0
goals        cruise_speed_mps 18 · max_level_speed_mps 28
             min_speed_margin_vs_clean 1.20
             takeoff_speed_margin_vs_to 1.25
             approach_speed_margin_vs_ldg 1.30
             target_turn_n 2.0 · loiter_s 600
constraints  max_alpha_deg 25 · max_beta_deg 30
source_profile_id = None      ← load-bearing, see BR-MS7
```

---

## D. Operating-point generation — hosted on `operating_points.py` (2 routes) 🟢

> These two routes live on the operating-point router
> ([`../aero-analysis/contracts.md`](../aero-analysis/contracts.md)) but their
> **semantics** are specified here and in
> [`operating-point-sweep/`](operating-point-sweep/requirements.md).

| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/operating-pointsets/generate-default` | `GenerateOperatingPointSetRequest` (body optional) | `GeneratedOperatingPointSetRead` | 200 · 404 · 422 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/operating-pointsets/generate-default/stream` | same | **SSE stream** (`text/event-stream`) | 200 |

### `GenerateOperatingPointSetRequest` 🟢

| Field | Type | Default | Note |
|---|---|---|---|
| `replace_existing` | bool | `false` | **deletes every** `operating_pointsets` **and** `operating_points` row of the aircraft first |
| `profile_id_override` | int \| null | `null` | use this profile instead of the aircraft's assignment |

⚠ `replace_existing = true` is **aircraft-wide**, not set-scoped: it removes
manually created operating points too. 🟢

### `GeneratedOperatingPointSetRead` 🟢

`{id, name, description, aircraft_id, source_flight_profile_id,
operating_points: StoredOperatingPointRead[]}`, with
`name = "default_operating_point_set"` and
`description = "Auto-generated standard operating point set including
Dutch-roll start point."`.

### SSE contract (gh-865) 🟢

```
event: targets   data: {"opset_id": <int>,
                        "targets": [{"name","config","status":"COMPUTING"}, …]}
event: op        data: <StoredOperatingPointRead JSON>     # one per solved point
event: skip      data: {"name": "<target>"}                # solve returned nothing
event: error     data: {"message": "<setup failure>"}      # then the stream ends
event: done      data: {"opset_id": <int>, "count": <int>}
```

Headers: `Cache-Control: no-cache`, `X-Accel-Buffering: no`. 🟢
Guarantees 🟢: the empty point-set row is created and **committed before** the
`targets` event; each solved point is inserted, appended to
`opset.operating_points` and **committed before** its `op` event, so a dropped
connection leaves a valid partial set. `op` events arrive in
`as_completed` order, **not** target order.
🟡 **`skip` is not what the code-analysis says it is.** Capability-filtered
targets are removed from `supported` *before* the `targets` event
(`generate_default_set_stream_for_aircraft`), so they never appear and never
produce a `skip`. A `skip` is emitted only when a worker solve raised or
returned `None`. A client cannot distinguish "your aircraft has no rudder" from
"this target failed to solve" — the first is silent, the second is a `skip`
without a reason field.
🟡 The streaming generator calls `db.commit()` directly, bypassing the
`get_db()` transaction boundary (BR-78 / ADR 0009). This is required for
incremental visibility, but it is an explicit exception to the rule.

---

## E. Flight envelope — `aeroplane/flight_envelope.py` (2 routes) 🟢

| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/flight-envelope` | — | `FlightEnvelopeRead` | 200 · **404 no cached envelope** · 500 |
| POST | `/aeroplanes/{aeroplane_id}/flight-envelope/compute` | — | `FlightEnvelopeRead` | 200 · 404 · 500 |

🟢 The GET returns 404 with *"No flight envelope computed yet for this
aeroplane."* when the row is absent — distinct from the 404 for an unknown
aeroplane. The POST upserts (one row per aeroplane) and always recomputes.
🟡 `ComputeEnvelopeRequest{force_recompute}` exists in
`app/schemas/flight_envelope.py` but the POST **takes no body** — the field is
dead surface.

### `FlightEnvelopeRead` 🟢

| Field | Type | Note |
|---|---|---|
| `id`, `aeroplane_id` | int | |
| `vn_curve` | `VnCurve` | |
| `kpis` | `PerformanceKPI[]` | **exactly 6, always** |
| `operating_points` | `VnMarker[]` | one per OP row with `velocity > 0` |
| `assumptions_snapshot` | dict | `{mass, cl_max, g_limit}` effective at compute time |
| `computed_at` | datetime(tz) | |
| `gust_warnings` | `(GustCriticalWarning \| GustValidityWarning)[]` | mirrors `vn_curve.gust_warnings` |

`VnCurve` = `{positive[], negative[], dive_speed_mps, stall_speed_mps,
gust_lines_positive[], gust_lines_negative[], gust_warnings[]}`; the manoeuvre
arrays hold **exactly 60** `VnPoint{velocity_mps, load_factor}` each, from
`V_stall` to `V_dive`. `velocity_mps` is validated `≥ 0`. All values are
`round(x, 6)`. 🟢

`gust_lines_*` are **empty** (not null, not zero-filled) whenever `CL_α` or
`b_ref` is unavailable — the gust envelope is simply absent. 🟢

| Warning | Fields | Fires when |
|---|---|---|
| `GustCriticalWarning` | `velocity_mps`, `n_gust`, `g_limit`, `message` | first `V` where `1+Δn > g_limit` or `1−Δn < −0.4·g_limit` |
| `GustValidityWarning` | `mu_g_value`, `validity_min = 3.0`, `validity_max = 200.0`, `message` | `μ_g ∉ [3, 200]` — the **normal** case for low-W/S RC models (gh-497) |

`PerformanceKPI{label, display_name, value, unit, source_op_id \| null,
confidence ∈ {trimmed, computed, estimated, limit}}`; the six labels are
`stall_speed`, `best_ld_speed`, `min_sink_speed`, `max_speed`,
`max_load_factor`, `dive_speed`. 🟢

`VnMarker{op_id, name, velocity_mps, load_factor, status, label}`.
🟡 `load_factor` is hard-coded to 1.0 today (`Q-MS-6` fixes it; the stored OP has no
CL), and `label` is set to `op.name` — so the `best_ld` / `min_sink` marker
lookup that produces the `"trimmed"` confidence tier can only ever hit an
operating point literally named `best_ld` or `min_sink`. The generator never
produces those names, so `confidence = "trimmed"` is unreachable through the
standard flow. See BR-MS35.

---

## F. Loading scenarios and CG envelope — `aeroplane/loading_scenarios.py` (6 routes) 🟢

| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/loading-scenarios` | — | `LoadingScenarioRead[]` | 200 · 404 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/loading-scenarios` | `LoadingScenarioCreate` | `LoadingScenarioRead` | **201** · 404 · 422 · 500 |
| PATCH | `/aeroplanes/{aeroplane_id}/loading-scenarios/{scenario_id}` | `LoadingScenarioUpdate` | `LoadingScenarioRead` | 200 · 404 · 422 · 500 |
| DELETE | `/aeroplanes/{aeroplane_id}/loading-scenarios/{scenario_id}` | — | — | **204** · 404 · 500 |
| GET | `/aeroplanes/{aeroplane_id}/cg-envelope` | — | `CgEnvelopeRead` | 200 · 404 · 500 |
| GET | `/aeroplanes/{aeroplane_id}/loading-scenarios/templates` | query `aircraft_class = "rc_trainer"` | `dict[]` | 200 · 404 · 500 |

🟢 **Creating a scenario marks every operating point DIRTY** and triggers a
retrim at the envelope extremes — a write to this resource fans out into
`aero-analysis`.
🟡 The templates route is **not** persisted state: it returns a starting set the
user may accept or discard; nothing is created at aeroplane creation.
🟡 `GET …/loading-scenarios/templates` is declared **after**
`…/loading-scenarios/{scenario_id}` in the same router, but the paths do not
collide because `{scenario_id}` is typed `int` and `templates` fails that
coercion — a 422 would result if the ordering ever changed.

### `LoadingScenarioCreate` / `Update` / `Read` 🟢

| Field | Type | Note |
|---|---|---|
| `name` | str | e.g. `"Battery Fwd"` |
| `aircraft_class` | `rc_trainer` \| `rc_aerobatic` \| `rc_pylon_3d` \| `rc_combust` \| `uav_survey` \| `glider` \| `boxwing` | default `rc_trainer` |
| `component_overrides` | `ComponentOverrides` | four override kinds, below |
| `is_default` | bool | default `false`; the default scenario supplies `cg_agg_m` |

`ComponentOverrides` 🟢 — **the four override types (BR-MS23)**:

| Key | Item shape | Effect |
|---|---|---|
| `toggles[]` | `{component_uuid, enabled}` | `enabled=false` removes the component from the aggregation |
| `mass_overrides[]` | `{component_uuid, mass_kg_override (gt 0)}` | replaces the component's mass |
| `position_overrides[]` | `{component_uuid, x_m_override, y_m_override?, z_m_override?}` | replaces the component's CG position |
| `adhoc_items[]` | `{name, mass_kg (gt 0), x_m, y_m = 0, z_m = 0, category}` | adds mass not in the component tree |

`category ∈ {pilot, payload, ballast, fuel, fpv_gear, other}`, default
`payload`. 🟢
🟢 🟢 **`component_uuid` is validated at write time** (`Q-MS-13 ③`); a referenced component cannot be deleted, only changed (`Q-PT-7`), so a dangling override can no longer arise. Previously a plain `str` with no existence check — an override
naming a deleted component is accepted and silently does nothing.

### `CgEnvelopeRead` 🟢

| Field | Type | Meaning |
|---|---|---|
| `cg_loading_fwd_m` | float | `min(cg_x)` over all scenarios |
| `cg_loading_aft_m` | float | `max(cg_x)` over all scenarios |
| `cg_stability_fwd_m` | float \| null | elevator-authority limit (gh-500); **null** until `x_np`/MAC exist |
| `cg_stability_aft_m` | float \| null | `x_np − target_sm · MAC` |
| `sm_at_fwd`, `sm_at_aft` | float \| null | `(x_np − cg)/MAC`; **null, never a stub**, when the stability envelope is unavailable |
| `classification` | `error` \| `warn` \| `ok` \| **`unknown`** | `unknown` when `x_np`/MAC are not yet computed |
| `warnings` | str[] | human-readable |

Classification ladder (Scholz §4.2, `loading_scenario_service.py:51-53`) 🟢:

```
sm < 0.02        → "error"   (Phugoid divergent)
sm < target_sm   → "warn"
sm ≤ 0.20        → "ok"
sm ≤ 0.30        → "warn"    (heavy nose, trim drag)
else             → "error"   (elevator authority)
```

Invariant the response is meant to police 🟢:
`cg_loading_aft_m ≤ cg_stability_aft_m`.

---

## G. Matching chart — `aeroplane/matching_chart.py` (1 route) 🟢

| Method | Path | Response | Status |
|---|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/matching-chart` | `MatchingChartResponse` | 200 · 404 · **422** |

Query parameters 🟢:

| Name | Type | Default | Note |
|---|---|---|---|
| `mode` | `rc_runway` \| `rc_hand_launch` \| `uav_runway` \| `uav_belly_land` | `rc_runway` | sets field-length, climb-gradient and stall-speed defaults |
| `s_runway` | float `gt=0` | mode default | field length target [m] |
| `v_s_target` | float `gt=0` | mode default | max acceptable clean stall speed [m/s] |
| `gamma_climb_deg` | float `gt=0, le=30` | mode default | climb gradient [°] |
| `v_cruise_mps` | float `gt=0` | `ctx["v_md_mps"]` | cruise constraint speed |
| `flight_profile` | str | `MissionObjective.mission_type`, else none | gh-613 Phase B applicability |

Mode defaults (`s_runway`, `γ_climb`, `V_s_target`) 🟢: `rc_runway`
50 m / 5° / 7 m/s · `rc_hand_launch` 0 / 5° / 7 · `uav_runway` and
`uav_belly_land` 200 m / 4° / 12 · `ga_runway` 500 m / 1.5° / 27.7 (FAR-23.65,
54 kt). An unknown mode logs a warning and falls back to `uav_runway`.
🟡 `ga_runway` is reachable in the **service** but is not a member of the
`AircraftMode` literal, so the endpoint cannot select it.

**Input resolution** (`_resolve_aircraft_params`) 🟢:

```
mass_kg      ← get_effective_assumption("mass")     else PARAMETER_DEFAULTS 1.5
cl_max       ← get_effective_assumption("cl_max")   else 1.4
cd0          ← get_effective_assumption("cd0")      else 0.03
t_static_N   ← get_effective_assumption("t_static_N"); ≤ 0 ⇒ 0.0
ar           ← ctx["aspect_ratio"]                  else 7.0
cl_max_takeoff = cl_max                     # clean CL_max, deliberately conservative
cl_max_landing = cl_max · 1.3               # rough flap factor
s_ref_m2, b_ref_m, v_md_mps, v_stall_mps    ← ctx, omitted when absent
e_oswald     ← ctx["e_oswald"] ONLY when > 0; otherwise OMITTED so the service
               emits a design warning and falls back to 0.8 (gh-956 / ADR 0012)
v_cruise     ← query override, else ctx["v_md_mps"], else service estimate
```

### `MatchingChartResponse` 🟢

| Field | Type | Note |
|---|---|---|
| `ws_range_n_m2` | float[] | the W/S sweep — 200 steps over `[10, 1500] N/m²` |
| `constraints` | `ConstraintLine[]` | |
| `design_point` | `{ws_n_m2, t_w}` | `T/W = T_static_SL / W_MTOW` |
| `feasibility` | `feasible` \| `infeasible_below_constraints` | |
| `warnings` | str[] | e.g. polar fallback used, `V_cruise` estimated |

`ConstraintLine` 🟢:

| Field | Type | Note |
|---|---|---|
| `name` | str | `Takeoff`, `Landing`, `Cruise`, `Climb`, `Stall`, … |
| `t_w_points` | float[] \| null | **line** constraint, one value per `ws_range_n_m2` entry |
| `ws_max` | float \| null | **vertical** constraint; exactly one of the two is non-null |
| `color` | str | hex |
| `binding` | bool | line binds within **3 %** in T/W; vertical within **5 %** in W/S |
| `hover_text` | str \| null | short formula / reference |
| `category` | `universal` \| `rc_specific` \| `cs25_only` | provenance |
| `binding_for_warning` | bool | `false` excludes it from the insufficient-T/W warning (CS-25-only) |
| `applicable_for_profile` | bool | `false` ⇒ do not render; **the data is still returned for auditability** |

Constraint formulas (Loftin / Scholz §5.2–5.4) 🟢:

```
takeoff (line)      T/W = C_TO·K_TO_50FT·(W/S) / (ρ·g·CL_max_TO·s_TO_50ft)
                    s_runway = 0 → 0            (hand launch: no constraint)
landing (vertical)  W/S_max = s_LDG_50ft·ρ·CL_max_LDG / (K_LDG_HARD·K_LDG_50FT)
cruise  (line)      T/W = q·CD0/(W/S) + (W/S)·k/q        k = 1/(π·e·AR)
climb   (line)      T/W = sin γ + [q·CD0/(W/S) + (W/S)·k/q]
stall   (vertical)  W/S_max = ½·ρ·V_s_target²·CL_max_clean     (CLEAN, not landing)
V_md                = sqrt(2·(W/S) / (ρ·sqrt(CD0/k)))

constants IMPORTED from field_length_service, never re-declared:
  _K_TO_50FT 1.66 · _K_LDG_50FT 2.73 · _K_LDG_HARD 0.5847 · _C_TO 1.21
```

RC-additive constraints (gh-613 Phase B) 🟢:

```
mission_min_tw   acro_3d 1.5 (hover) · wing_racer 0.8 · sport 0.5
power_loading    T/W ≥ (P/m)·η_prop / (g·V_climb),  V_climb = 1.3·V_stall
                 P/m: trainer 125 · sport 200 · wing_racer 275 · acro_3d 400 W/kg
vertical_climb   T/W ≥ 1 + D/W                              (acro / 3D)
wcl (vertical)   W/S_max = (WCL·47.88)^(2/3) · AR^0.25      Lennon lb/ft^4.5 → SI
                 WCL upper: trainer 6.0 · sport 12.0
hand_launch      W/S ≤ 80 N/m²   (only when mode == rc_hand_launch)
```

Applicability (`_PROFILE_CONSTRAINT_MAP`) 🟢:

| Profile | Applicable constraints |
|---|---|
| `trainer` | stall, climb, power_loading, wcl |
| `sport` | stall, climb, mission_min_tw, power_loading, wcl |
| `wing_racer` | stall, cruise, power_loading |
| `acro_3d` | stall, mission_min_tw, power_loading, vertical_climb |
| `stol_bush` | stall, takeoff, landing, climb |
| `slope_soarer` / `glider` / `sailplane` | stall |
| `motor_glider` / `flying_wing` | stall, climb, cruise |
| `custom` / unknown | **all** (back-compat) |

🟢 **Log-forging safety (Sonar S5145):** the user-controlled `flight_profile`
query string is never logged directly — `_sanitize_profile_for_log` maps it
through the constant `_LOG_PROFILE_LABELS` table.

---

## H. Field lengths — `aeroplane/field_lengths.py` (1 route) 🟢

| Method | Path | Response | Status |
|---|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/field-lengths` | `FieldLengthRead` | 200 · 404 · **422** |

Query parameters 🟢:

| Name | Type | Default | Note |
|---|---|---|---|
| `takeoff_mode` | `runway` \| `hand_launch` \| `bungee` \| `catapult` | `runway` | overrides the `MissionObjective` value |
| `landing_mode` | `runway` \| `belly_land` | `runway` | |
| `v_throw_mps` | float `gt=0` | `null` ⇒ 10 m/s | `hand_launch` only |
| `v_release_mps` | float `gt=0` | `null` | `bungee` / `catapult` |
| `bungee_force_N` | float `gt=0` | `null` | `bungee` |
| `stretch_m` | float `gt=0` | `null` | `bungee` |

**422 preconditions** 🟢 — each raises a bare `ServiceException` mapped to 422
with a remediation sentence, *before* any computation:

| Missing input | Message |
|---|---|
| `ctx["s_ref_m2"]` absent or ≤ 0 | *"Wing reference area (s_ref_m2) is not available. Trigger an assumption recompute first by saving the wing geometry."* |
| `ctx["v_stall_mps"]` absent or ≤ 0 | *"Stall speed (v_stall_mps) is not available. Trigger an assumption recompute first."* |
| mass absent or ≤ 0 (`ctx["mass_kg"]` → `aeroplane.total_mass_kg`) | *"Aircraft mass is not available. Set total_mass_kg on the aeroplane or trigger an assumption recompute."* |
| `t_static_N ≤ 0` on a mode that needs thrust | raised inside the service |

🟢 **Thrust comes from `MissionObjective.t_static_N` after gh-548**, not from
the design assumption — the assumption of the same name still exists and the
matching chart still reads it. 🟡 ADR 0022 requires one source for one physical quantity.
🟢 Flap-aware `CL_max`: `flap_type = ctx["flap_type"]` else `_detect_flap_type`,
which joins `TED → WingXSecDetail → WingXSec → Wing` and returns `"plain"` when
any TED has `role == "flap"`, else `None`. The DB stores no
plain/slotted/Fowler sub-type, so `"plain"` (1.1× TO / 1.3× LDG) is the
conservative stand-in. 🟡

### `FieldLengthRead` 🟢

| Field | Unit | Note |
|---|---|---|
| `s_to_ground_m` | m | takeoff ground roll |
| `s_to_50ft_m` | m | takeoff distance to clear the 50-ft obstacle |
| `s_ldg_ground_m` | m | landing ground roll |
| `s_ldg_50ft_m` | m | landing distance from 50 ft to stop |
| `vto_obstacle_mps` | m/s | `V_LOF = 1.2·V_S` |
| `vapp_mps` | m/s | `V_app = 1.3·V_S` |
| `mode_takeoff`, `mode_landing` | — | echo |
| `warnings` | str[] | e.g. insufficient climb-out margin |

> The **landing-field-length** computation of gh-477 (`V_S0`, `V_TD`,
> `s_ground`, `LANDING_SURFACE_MU`, the tri-state `landing_field_sufficient`)
> is **not** this endpoint. It runs inside `recompute_assumptions` and is
> published on `assumption_computation_context` as
> `landing_field_length_m` / `landing_surface_used` /
> `landing_field_sufficient`. 🟢 🟢 **The gh-477 energy balance is the model the UI trusts** (`Q-MS-2`, expert consensus endorsed by the maintainer); the Roskam correlation is calibrated on a braked Cessna 172N and does not transfer to RC/UAV scale (ADR 0023). Previously two models therefore
> coexist: Roskam §3.4 here, energy-balance there, with no cross-check.

---

## I. Static-margin sizing — `aeroplane/sm_suggestions.py` (2 routes) 🟢

| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/sm-suggestion` | query `at_cg ∈ {aft, fwd} = aft` | `SmSuggestionResponse` | 200 · 404 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/sm-suggestions/apply` | `SmApplyRequest` | `SmApplyResponse` | 200 · **400** · **409** · 404 · 422 |

`SmSuggestionResponse` 🟢:

| Field | Type | Note |
|---|---|---|
| `status` | `ok` \| `suggestion` \| `error` \| `not_applicable` \| `tailless_recommendation` | |
| `options` | `SmOption[]` | one per lever (`wing_shift`, `htail_scale`); empty for `ok` / `not_applicable` |
| `block_save` | bool | `true` when `SM < 0.02` — aerodynamically unstable |
| `mass_coupling_warning` | str \| null | present with a `wing_shift` option: the wing-mass CG shift is **not** in the analytic formula (≈ 15 % systematic error) |
| `message`, `hint` | str \| null | |
| `warnings` | str[] | |
| `target_static_margin`, `sm_forward_cg`, `sm_aft_cg` | float \| null | gh-579 tailless fields; null for conventional |

🟢 `target_sm` is read from `ctx["target_static_margin"]` with an inline default
of **0.10** — which differs from the seeded assumption default of **0.12**.
🟢 🟢 **The seeded default is `0.10`** and there is one authority for it (`Q-MS-14`, expert consensus endorsed by the maintainer).

`SmApplyRequest` 🟢: `{lever ∈ {wing_shift, htail_scale}, delta_value
(gt −0.9, lt 2.0), dry_run = false}` — `wing_shift` in **metres**,
`htail_scale` as a **fraction** (0.20 = +20 %); the `> −0.9` bound prevents a
non-positive chord.
`SmApplyResponse` 🟢: `{lever, delta_value, predicted_sm, dry_run, warnings[]}`.
🟢 **409** when the apply loop does not converge after 3 iterations
(gh-509, Scholz A6); **400** for canard / tailless / no-NP configurations.
🟢 With `dry_run = true` nothing is written; otherwise the geometry is updated
and a background recompute is scheduled.

---

## J. Forward CG limit — `aeroplane/forward_cg.py` (1 route) 🟢

| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/forward-cg/recompute` | query `solver ∈ {asb, avl} = asb` | `ForwardCGResult` | 200 · 404 · 422 · 500 |

Physics (gh-500, Anderson §7.7, NP-centred trim inversion) 🟢:

```
x_cg_fwd = x_np − (Cm_ac + Cm_δe·δe_max + ΔCm_flap) · c_ref / CL_max_landing

sign convention (Amendment B3):
  Cm_δe measured with TE-UP (negative) deflection  ⇒ Cm_δe > 0
  δe_max = |negative_deflection_deg| · π/180
  Cm_δe · δe_max > 0                                (nose-up trim contribution)
```

`ForwardCGResult` 🟢:

| Field | Type | Note |
|---|---|---|
| `cg_fwd_m` | float \| null | **null** when no feasible forward CG exists (infeasibility guard S3) |
| `confidence` | `ForwardCGConfidence` | `solver=avl` always returns the `avl_full` tier |
| `cm_delta_e` | float \| null | 1/rad; null on the stub path |
| `cl_max_landing` | float | includes the flap contribution when a flap run happened; fallback `CL_max_clean + 0.5` (Roskam §4.7) |
| `flap_state` | `deployed` \| `clean` \| `stub` | |

🟢 `solver=avl` is **opt-in** and meant for an explicit user action (V-tail,
elevon, flaperon layouts), never automatic. On any computation failure the
service falls back to the conservative `0.30·MAC` stub and still returns 200
with the failure recorded in the result.

---

## Not part of this contract

- Running solvers, the α-sweep, strip forces, stability results, the
  single-point/trim endpoints and the operating-point **CRUD** →
  `aero-analysis` ([`../aero-analysis/contracts.md`](../aero-analysis/contracts.md)).
- Emitting, running or storing `.avl` geometry, and the AVL trim route →
  `avl-integration` ([`../avl-integration/contracts.md`](../avl-integration/contracts.md)).
- Weight items, the component tree and mass aggregation →
  `mass-and-balance`.
- Wing/fuselage geometry, TED roles and hinge limits → `wing-design`,
  `fuselage-design`.
- Motor/prop/battery models behind `power_to_weight`, `prop_efficiency` and
  `t_static_N` → `powertrain`.
- The MCP tool wrappers that re-enter these handlers in-process →
  `mcp-server`.
