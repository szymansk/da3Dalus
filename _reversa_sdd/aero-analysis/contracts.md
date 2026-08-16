# aero-analysis — External Contracts

> REST contract as captured in `code-analysis.md` §Module: aero-analysis and
> verified against the route decorators in
> `app/api/v2/endpoints/aeroanalysis.py`, `…/operating_points.py` and
> `…/aeroplane/speed_polar.py`.
> 🟢 All routes are mounted at the **application root** — `prefix=""`
> (`app/main.py:225-227`). There is **no** `/api/v2` path segment on this
> module's routes (only `openvsp_import` carries that prefix).
> 🟡 `code-analysis.md` says "All under `/api/v2`" for this module; the router
> registration contradicts it. The registration wins.

## Global error contract 🟢

`_raise_http_from_domain` (`aeroanalysis.py:51-67`, mirrored in
`operating_points.py:43-59`) maps the domain exception hierarchy:

| Exception | HTTP | Envelope `code` |
|---|---|---|
| `NotFoundError` | 404 | `not_found` |
| `ValidationError` / `ValidationDomainError` | 422 | `validation_error` |
| `ConflictError` | 409 | `conflict` |
| `InternalError` | 500 | `internal_error` |
| bare `ServiceException` | 500 | `service_error` |

```json
{ "error": { "code": "validation_error", "message": "…", "details": { … } } }
```

Additional module-specific mappings 🟢:

| Cause | HTTP |
|---|---|
| unknown control-deflection name (`validate_deflections_against_airplane`) | **422**, listing unknown vs available names |
| array-valued `alpha`/`beta` with `analysis_tool=avl` | **422** (`ValueError` → validation) |
| `\|alpha\| > 180` or `\|beta\| > 180` in the request body | **422** — "almost certainly means radians were passed instead of degrees (gh-577/gh-587)" |
| material with `allowable_bending_stress_mpa ≤ 0` on a sizing request | **422** |
| AVL binary missing / AVL wrote no output | **500** (`FileNotFoundError` / `RuntimeError`) |

## Response encoding 🟢

The analysis router is constructed as
`APIRouter(default_response_class=NonFiniteSafeJSONResponse)`
(`aeroanalysis.py:43`): **NaN and Inf serialise as `null`**, never as a
fabricated number and never as invalid JSON (ADR 0012).
`operating_points.py` uses a plain `APIRouter()`. 🟡 The two routers therefore
differ in non-finite handling — a NaN reaching an operating-point response is
**not** neutralised.

## Unit contract for this module 🟢

| Quantity | Wire unit | Storage unit |
|---|---|---|
| `velocity`, all V-speeds | m/s | m/s |
| `alpha`, `beta` (request & response schemas) | **degrees** | **radians** on `operating_points` |
| `p`, `q`, `r` | rad/s | rad/s |
| `altitude`, `xyz_ref` | metres | metres |
| control deflections | degrees | degrees |
| `Sref` / `Cref` / `Bref` | m² / m / m | m² / m / m |
| strip `Chord`, `Xle/Yle/Zle` | metres | — |
| strip `Area` | m² | — |
| spar sizing `M` / `σ_allow` / dimensions | N·m / MPa / mm | — |
| `mass` | kg | kg |

The rad↔deg conversion happens **only** in
`operating_point_model_to_schema` (`operating_point_resolver.py`). 🟢

---

## Analysis routes — `app/api/v2/endpoints/aeroanalysis.py` (17 routes) 🟢

`{aeroplane_id}` is always the **public UUID** (`AeroPlaneID`), never the integer
PK.

### Strip forces and loads

| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/strip_forces` | body `OperatingPointSchema`, query `solver: "vlm" \| "avl" = "vlm"` | `StripForcesResponse` | 200 · 404 · 422 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/wings/{wing_name}/strip_forces` | same | `StripForcesResponse` | 200 · 404 · 422 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/spanwise_loads` | body `OperatingPointSchema`, query `solver` | `SpanwiseLoadsResponse` | 200 · 404 · 422 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/spanwise_loads_with_sizing` | body `OperatingPointSchema`, query `solver`, `material_id`, sizing params | `SpanwiseLoadsWithSizingResponse` | 200 · 404 · **422 σ_allow ≤ 0** · 500 |
| POST | `/aeroplanes/{aeroplane_id}/section-geometry` | `SectionGeometryRequest` (all fields optional) | `SectionGeometryResponse` | 200 · 404 · 422 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/spar-plan` | `SparPlanRequest` | `SparPlanResponse` | 200 · 404 · 422 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/spar-plan/insert` | `SparInsertRequest` (`dry_run`) | `SparInsertResponse` | 200 · 404 · 422 · 500 |

> `section-geometry`, `spar-plan` and `spar-plan/insert` are **hosted** on this
> router but specified by `wing-design`
> ([`../wing-design/spar-sizing/`](../wing-design/spar-sizing/requirements.md)).
> They appear here only so the HTTP surface is complete. 🟢

`StripForcesResponse` (`app/schemas/strip_forces.py:40`) 🟢:

| Field | Type | Note |
|---|---|---|
| `alpha`, `beta`, `mach` | float | flight-condition echo |
| `sref`, `cref`, `bref` | float | reference geometry |
| `surfaces[]` | `SurfaceStripForces` | `surface_name`, `surface_number`, `n_chordwise`, `n_spanwise`, `surface_area`, `strips[]` |
| `velocity_mps`, `altitude_m`, `xyz_ref_m[3]` | optional | gh-592 compute echo |
| `wing_name`, `operating_point_label` | optional str | |
| `reynolds` | optional float | `V·Cref/ν(altitude)`; `0.0` when `V` or `Cref ≤ 0` |
| `aero_model` | `"AVL"` \| `"ASB"` | which solver produced the strips (gh-674) |
| `computed_at` | datetime (UTC) | |

`StripForceEntry` uses **AVL's column names as aliases**: `j`, `Xle`, `Yle`,
`Zle`, `Chord`, `Area`, `c_cl`, `ai`, `cl_norm`, `cl`, `cd`, `cdv`, `cm_c/4`,
`cm_LE`, `C.P.x/c`.
⚠ **On the ASB path `cdv`, `cm_c/4` and `cm_LE` are always `0.0` and `C.P.x/c`
is always `0.25`** — the VLM is inviscid. This is a contract guarantee, not a
bug. 🟢

### Single-point analysis and stability

| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/wings/{wing_name}/{analysis_tool}` | `OperatingPointSchema` | analysis result | 200 · 404 · 422 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/operating_point/{analysis_tool}` | `OperatingPointSchema` | analysis result | 200 · 404 · 422 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/stability_summary/{analysis_tool}` | `OperatingPointSchema` | `StabilitySummaryResponse` | 200 · 404 · 422 · 500 |
| GET | `/aeroplanes/{aeroplane_id}/stability` | — | `StabilityResultRead` | 200 · **404 no cached result** · 500 |

`{analysis_tool}` is `AnalysisToolUrlType` ∈ `{avl, aerobuildup,
vortex_lattice}`. 🟢 `analyze_wing` and the single-wing strip-force path prune
the airplane to one wing and therefore **never** consult the stored AVL geometry
file; `analyze_airplane` does. 🟡

`GET …/stability` returns the cached row ordered `status ASC, computed_at DESC`
— `CURRENT` beats `DIRTY` alphabetically. 🟡

### Sweeps and figures

| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/alpha_sweep` | `AlphaSweepRequest` | sweep + six characteristic points + optional speed polar | 200 · 404 · 422 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/alpha_sweep/diagram` | `AlphaSweepRequest` | `StaticUrlResponse` | 200 · 404 · 422 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/simple_sweep` | `SimpleSweepRequest` | sweep result | 200 · 404 · 422 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/streamlines` | `OperatingPointSchema` | Plotly figure JSON | 200 · 404 · 422 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/operating_point/vortex_lattice/streamlines/three_view/url` | `OperatingPointSchema` | `StaticUrlResponse` | 200 · 404 · 422 · 500 |
| GET | `/aeroplanes/{aeroplane_id}/three_view/url` | — | `StaticUrlResponse` | 200 · 404 · 500 |

**Solver guarantees on these routes** 🟢:

- `alpha_sweep`, `alpha_sweep/diagram`, `simple_sweep` are hard-coded
  `AEROBUILDUP` — AVL is not reachable (it rejects array sweeps).
- `streamlines` and both three-view routes are hard-coded `VORTEX_LATTICE`.

`simple_sweep` sweeps over `alpha · velocity · beta · p · q · r · altitude ·
x · y · z`. 🟢

The α-sweep diagram renders a 3×2 matplotlib figure (coefficients, CL–CD polar,
CL–Cm, L/D, `Xnp`/`Xnp_lat`, summary) with collision-avoiding annotations and
colour-coded trend strips (`dCm/dα < −0.01` green / `≤ 0.01` amber / else red),
writes it to `tmp/{uuid}/png/alpha_sweep_<hex>.png` and returns a `/static/...`
URL. 🟢

### `OperatingPointSchema` — the shared request body 🟢

(`app/schemas/aeroanalysisschema.py:231`)

| Field | Type | Default | Note |
|---|---|---|---|
| `name`, `description` | str \| None | `None` | |
| `velocity` | float [m/s] | `10.0` | |
| `alpha` | float \| **list[float]** [**deg**] | `0.0` | a list makes it a sweep — AVL rejects it |
| `beta` | float [deg] | `0.0` | |
| `p` / `q` / `r` | float [rad/s] | `0.0` | |
| `xyz_ref` | list[float] [m] | `[0,0,0]` | moment reference — set to the CG |
| `altitude` | float [m] | `0.0` | |
| `cdcl_config` | `CdclConfig` \| None | `None` | **AVL only** |
| `spacing_config` | `SpacingConfig` \| None | `None` | **AVL only** |
| `control_deflections` | dict[str, float] \| None | `None` | validated against the airplane → 422 on unknown names |
| `operating_point_id` | int \| None | `None` | set ⇒ resolve the stored **TRIMMED** OP (gh-577) |

Validator: any `\|alpha\|` or `\|beta\| > 180` is rejected as a radian/degree
mix-up. 🟢

---

## Operating-point routes — `app/api/v2/endpoints/operating_points.py` (19 routes) 🟢

### Generation and trim

| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/analysis-status` | — | `AnalysisStatusResponse` | 200 · 404 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/operating-pointsets/generate-default` | `GenerateOperatingPointSetRequest` (optional) | `GeneratedOperatingPointSetRead` | 200 · 404 · 422 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/operating-pointsets/generate-default/stream` | same | **SSE stream** | 200 · 404 · 422 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/operating-points/trim` | `TrimOperatingPointRequest` | `TrimmedOperatingPointRead` | 200 · 404 · 422 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/operating-points/avl-trim` | `AVLTrimRequest` | `AVLTrimResult` | 200 · 404 · 422 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/operating-points/aerobuildup-trim` | `AeroBuildupTrimRequest` | `AeroBuildupTrimResult` | 200 · 404 · 422 · 500 |
| POST | `/aeroplanes/{aeroplane_uuid}/operating-points/add-turn` | `AddTurnRequest` | `StoredOperatingPointRead` | 200 · 404 · 422 · 500 |

> The **generation** routes are specified by `mission-and-sizing`
> ([`../mission-and-sizing/operating-point-sweep/`](../mission-and-sizing/operating-point-sweep/requirements.md));
> the **AVL trim** route by
> [`../avl-integration/`](../avl-integration/contracts.md). They are listed here
> because they live on this router. 🟢

`avl-trim` and `aerobuildup-trim` both return a `trim_enrichment` block computed
best-effort — an enrichment failure never fails the trim response. 🟢
`AeroBuildupTrimResult.converged` is `False` (with a detailed warning) when the
root is not bracketed; it does **not** raise. 🟢
🔴 `AVLTrimResult.converged` is inferred from `"CL" in raw` — see
[`../avl-integration/contracts.md`](../avl-integration/contracts.md).

### CRUD

| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| POST | `/operating_points/` | `StoredOperatingPointCreate` | `StoredOperatingPointRead` | 200 · 422 · 500 |
| GET | `/operating_points` | query `aircraft_id: UUID?`, `skip ≥ 0 = 0`, `limit ∈ [1,1000] = 200` | `list[StoredOperatingPointRead]` | 200 · 500 |
| GET | `/operating_points/{op_id}` | — | `StoredOperatingPointRead` | 200 · 404 · 500 |
| PUT | `/operating_points/{op_id}` | `StoredOperatingPointCreate` | `StoredOperatingPointRead` | 200 · 404 · 422 · 500 |
| PATCH | `/operating_points/{op_id}/deflections` | `OperatingPointDeflectionPatch` | `StoredOperatingPointRead` | 200 · 404 · 422 · 500 |
| DELETE | `/operating_points/{op_id}` | — | status envelope | 200 · 404 · 500 |
| POST | `/operating_pointsets/` | `OperatingPointSetSchema` | `OperatingPointSetSchema` | 200 · 422 · 500 |
| GET | `/operating_pointsets` | query `aircraft_id?`, `skip`, `limit` | `list[OperatingPointSetSchema]` | 200 · 500 |
| GET | `/operating_pointsets/{opset_id}` | — | `OperatingPointSetSchema` | 200 · 404 · 500 |
| PUT | `/operating_pointsets/{opset_id}` | `OperatingPointSetSchema` | `OperatingPointSetSchema` | 200 · 404 · 422 · 500 |
| DELETE | `/operating_pointsets/{opset_id}` | — | status envelope | 200 · 404 · 500 |

⚠ **The `/operating_points…` CRUD routes are addressed by integer PK and are
not scoped to an aeroplane.** Only the resolver path
(`resolve_operating_point`) constrains a row to its `aircraft_pk`; direct CRUD
does not. 🟡

### Persisted operating-point shape 🟢

(`operating_points`, `app/models/analysismodels.py:20`)

| Field | Unit / domain | Note |
|---|---|---|
| `name` | — | e.g. `cruise`, `turn_40`, `best_rate_climb_vy` |
| `description` | — | generated: `config=…, target_n=…, V=…, altitude=…` |
| `config` | `clean` \| `takeoff` \| `landing` | default `"clean"` |
| `status` | `NOT_TRIMMED` \| `COMPUTING` \| `TRIMMED` \| `LIMIT_REACHED` \| `DIRTY` \| `INVALID` | default `NOT_TRIMMED` |
| `warnings` | JSON list | `STALE_NO_POLAR`, `FLAP_DEFLECTION_CLIPPED`, `ALPHA_LIMIT_REACHED`, `BETA_LIMIT_REACHED`, `STALL_IN_TURN`, `NOT_TRIMMED`, `NO_CONTROL_TRIM_MVP` |
| `controls` | JSON `{name: deg}` | the trim solver's output |
| `control_deflections` | JSON `{name: deg}` \| NULL | **manual override**; wins when non-empty |
| `velocity` | m/s | |
| `alpha`, `beta` | **radians** | converted to degrees by the resolver |
| `p`, `q`, `r` | rad/s | non-zero only for turns |
| `xyz_ref` | `[x,y,z]` m | written as `[design_cg_x, 0, 0]` |
| `altitude` | m | |
| `trim_enrichment` | JSON | serialised `TrimEnrichment` |

`TrimEnrichment` (`app/schemas/aeroanalysisschema.py`) 🟢:
`analysis_goal`, `trim_method`, `trim_score`,
`trim_residuals: dict[str, float]` (**floats only**, gh-627),
`deflection_reserves`, `design_warnings`, `effectiveness`,
`stability_classification`, `mixer_values`, `result_summary`,
`aero_coefficients`.

| Nested type | Fields |
|---|---|
| `DeflectionReserve` | `deflection_deg`, `max_pos_deg`, `max_neg_deg`, `usage_fraction` |
| `DesignWarning` | `level` (`warning` \| `critical`), `category` (`authority` \| `trim_quality` \| `stability` \| `solver`), `surface`, `message` |
| `ControlEffectiveness` | `derivative`, `coefficient` (`Cm` \| `Cl` \| `Cn` \| `CL`), `surface` |
| `StabilityClassification` | `is_statically_stable`, `is_directionally_stable`, `is_laterally_stable`, `static_margin` (`−Cm_a/CL_a`), `overall_class` |
| `MixerValues` | `symmetric_offset`, `differential_throw`, `deflection_left`, `deflection_right`, `differential_ratio`, `role` |

🔴 On a dual-role aircraft the `deflection_reserves` are computed against the
hard-coded `(25.0, 25.0)` default and an extra `MixerValues`/deflection entry
appears at `0.0` under the raw DB name (open bug #955).

---

## Speed polar — `app/api/v2/endpoints/aeroplane/speed_polar.py` 🟢

| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/speed-polar` | — | `SpeedPolarResponse` | 200 · **404 aeroplane not found** · 500 |

Reads the cached aero context (BR-14) — it does **not** run a solver. Guarantees:
one curve per mass with the base mass always flagged `is_base`;
`V, w ∝ sqrt(m)`; markers at `V_stall`, min-sink and best-glide, each labelled
with α through the cached linear lift curve (gh-871). Display bounds
`v_axis_min = 0.7·min(V_stall)` and `v_axis_max = 1.3·V_dive` are emitted
**together or not at all** (gh-799). 🟢
🔴 With no `mass` assumption the polar is computed at **1.0 kg** and returned
without a user-visible warning.

---

## Cached stability read — `StabilityResultRead` 🟢

| Field | Unit | Note |
|---|---|---|
| `solver` | `avl` \| `aerobuildup` \| `vortex_lattice` | part of the unique key |
| `neutral_point_x` | m | `result.reference.Xnp` |
| `mac` | m | `result.reference.Cref` |
| `cg_x_used` | m | `operating_point.xyz_ref[0]` |
| `static_margin_pct` | % | `100·(Xnp − Xcg)/MAC` |
| `stability_class` | `stable` (>5 %) \| `neutral` (0–5 %) \| `unstable` (<0) | |
| `cg_range_forward` / `cg_range_aft` | m | `Xnp − 0.25·MAC` / `Xnp − 0.05·MAC` 🔴 the bounds are unreachable configuration |
| `Cma` / `Cnb` / `Clb` | — | stable when `Cma<0`, `Cnb>0`, `Clb<0` |
| `trim_alpha_deg` | deg | |
| `trim_elevator_deg` | deg | 🔴 first deflection whose **name contains `"elevator"`** — never matches `[ruddervator]pitch_…` |
| `is_statically_stable` / `is_directionally_stable` / `is_laterally_stable` | bool | |
| `computed_at` | datetime(tz) | |
| `status` | `CURRENT` \| `DIRTY` | |
| `geometry_hash` | str | `sha256(stability-relevant geometry)[:16]` |

## Not part of this contract

- Emitting, running or storing `.avl` geometry → `avl-integration`
  ([`../avl-integration/contracts.md`](../avl-integration/contracts.md)).
- Design assumptions, computation config, mission objectives, matching chart,
  V-n envelope, field lengths, flight profiles, OP **generation** semantics →
  `mission-and-sizing`
  ([`../mission-and-sizing/contracts.md`](../mission-and-sizing/contracts.md)).
- Spar sizing / spar plan semantics → `wing-design`
  ([`../wing-design/spar-sizing/`](../wing-design/spar-sizing/requirements.md)).
- Airfoil-level polars and NeuralFoil suitability → `airfoil-catalog`.
- MCP tool wrappers that re-enter these handlers in-process → `mcp-server`.
