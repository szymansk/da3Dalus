# mass-and-balance — External Contracts

> REST contract read from `app/api/v2/endpoints/aeroplane/weight_items.py` and
> `.../mass_cg.py`, cross-checked against `code-analysis.md` §Module:
> mass-and-balance. 🟢
> Both routers are mounted with `prefix=""` (`app/main.py:211` via the
> `aeroplane` package router), so there is **no** `/api/v2` segment.
> `{aeroplane_id}` is always the public **UUID** (typed `UUID4` on the path). 🟢

## Error contract 🟢

Both routers declare their own `_raise_http` / `_call` pair. The mapping is
identical in the two files:

| Service exception | HTTP | Body |
|---|---|---|
| `NotFoundError` | 404 | `{"detail": exc.message}` |
| `ValidationError` / `ValidationDomainError` | 422 | `{"detail": exc.message}` |
| `ConflictError` | 409 | `{"detail": exc.message}` |
| any other `ServiceException` | 500 | `{"detail": exc.message}` |
| any non-`ServiceException` | 500 | `{"detail": "Unexpected error: <repr>"}` |

> **Divergence from `aeroplane-core`.** These routes return FastAPI's bare
> `{"detail": …}` envelope, **not** the `{"error": {code, message, details}}`
> envelope produced by `aeroplane/base.py`'s `_raise_http_from_domain`. A client
> that parses `error.code` will find nothing here. 🟢 (`Q-CC-3`)
>
> The catch-all interpolates the raw exception text (`f"Unexpected error:
> {exc}"`), and `weight_items_service` wraps `SQLAlchemyError` as
> `InternalError(message=f"Database error: {exc}")` — so driver-level messages
> can reach the response body. 🟢 (`Q-CC-3`)
>
> `mass_cg.py`'s `_call` logs the catch-all with `exc_info=True`;
> `weight_items.py` is retired (`Q-MB-1`). 🟢
>
> 409 is declared in the OpenAPI `responses` of every weight-item route but no
> service path raises `ConflictError`. 🟡 declared, unreachable.

## Weight-item routes — `app/api/v2/endpoints/aeroplane/weight_items.py` 🟢

Base path: `/aeroplanes/{aeroplane_id}/weight-items`

### `GET /aeroplanes/{aeroplane_id}/weight-items`

| | |
|---|---|
| `operation_id` | `list_weight_items` |
| Request | — |
| Response | `WeightSummary` |
| Status | 200 · 404 · 500 |
| Semantics | Recomputes the summary inline over the loaded rows and rounds every published number to **6 decimals** |

```jsonc
{
  "items": [
    { "id": 1, "name": "battery 3S 2200", "mass_kg": 0.185,
      "x_m": 0.08, "y_m": 0.0, "z_m": 0.01,
      "description": null, "category": "battery" }
  ],
  "total_mass_kg": 0.185,   // 0 (not null) for an empty inventory
  "cg_x_m": 0.08,           // null when total_mass_kg <= 0
  "cg_y_m": 0.0,
  "cg_z_m": 0.01
}
```

### `POST /aeroplanes/{aeroplane_id}/weight-items`

| | |
|---|---|
| `operation_id` | `create_weight_item` |
| Request | `WeightItemWrite` |
| Response | `WeightItemRead` |
| Status | **201** · 404 · 422 · 500 |
| Side effects | `db.flush()` + `db.refresh()`, then best-effort `sync_weight_items_to_assumptions` |

`WeightItemWrite`:

| Field | Type | Required | Default | Constraint |
|---|---|---|---|---|
| `name` | string | yes | — | `min_length=1` |
| `mass_kg` | float | yes | — | `ge=0`, **kilograms** |
| `x_m` / `y_m` / `z_m` | float | no | `0.0` | **metres**, aeroplane coordinates |
| `description` | string \| null | no | `null` | free text |
| `category` *(retired, `Q-MB-1`)* | string | no | `"other"` | `electronics` \| `battery` \| `structural` \| `payload` \| `other` — **Pydantic-only**, the column is a plain `String` 🔴 |

`WeightItemRead` = `WeightItemWrite` + `id: int`.

### `GET /aeroplanes/{aeroplane_id}/weight-items/{item_id}`

| | |
|---|---|
| `operation_id` | `get_weight_item` |
| Response | `WeightItemRead` |
| Status | 200 · 404 · 500 |
| Semantics | The query filters on `aeroplane_id` **and** `id`, so an item belonging to another aeroplane is a 404 |

### `PUT /aeroplanes/{aeroplane_id}/weight-items/{item_id}`

| | |
|---|---|
| `operation_id` | `update_weight_item` |
| Request | `WeightItemWrite` — **full replacement**, `model_dump()` writes every field including the defaults |
| Response | `WeightItemRead` |
| Status | 200 · 404 · 422 · 500 |
| Side effects | best-effort assumption sync |

> There is no PATCH. Omitting `x_m` in a PUT resets it to `0.0`. 🟢

### `DELETE /aeroplanes/{aeroplane_id}/weight-items/{item_id}`

| | |
|---|---|
| `operation_id` | `delete_weight_item` |
| Response | none — **204 No Content** |
| Status | **204** · 404 · 500 |
| Side effects | best-effort assumption sync after the delete + flush |

## Mass/CG routes — `app/api/v2/endpoints/aeroplane/mass_cg.py` 🟢

### `POST /aeroplanes/{aeroplane_id}/design_metrics`

| | |
|---|---|
| `operation_id` | `compute_design_metrics` |
| Request | `DesignMetricsRequest` |
| Response | `DesignMetricsResponse` |
| Status | 200 · 404 · 422 · 500 |
| Cost | The only route in the module that touches AeroSandbox — it builds the complete ASB airplane to read `s_ref` |

`DesignMetricsRequest`:

| Field | Type | Default | Constraint |
|---|---|---|---|
| `velocity` | float | `15` | `gt=0`, m/s |
| `altitude` | float | `0` | `ge=0`, metres — fed to `asb.Atmosphere` |

`DesignMetricsResponse` (all values SI):

| Field | Unit | Formula |
|---|---|---|
| `mass_kg` | kg | effective `mass` assumption |
| `s_ref` | m² | from the built ASB airplane |
| `cl_max` | – | effective `cl_max` assumption |
| `wing_loading_pa` | Pa (N/m²) | `mass_kg · 9.81 / s_ref` |
| `stall_speed_ms` | m/s | `sqrt(2·W / (ρ · s_ref · cl_max))` |
| `required_cl` | – | `W / (½·ρ·velocity² · s_ref)` |
| `cl_margin` | – | `cl_max − required_cl`; `> 0` ⇒ above stall |

422 cases, each with its own message:

| Condition | Message |
|---|---|
| `mass_kg ≤ 0` | `mass_kg must be positive` |
| `s_ref ≤ 0` (no wings) | `Wing reference area (s_ref) is zero or negative — add wings first` |
| `cl_max ≤ 0` | `cl_max must be positive` |
| `rho ≤ 0` | `rho must be positive` |
| `velocity ≤ 0` | `velocity must be positive` (also caught earlier by `gt=0`) |

404 when the aeroplane, the `mass` assumption row or the `cl_max` assumption row
is missing. 500 when the ASB conversion fails (`InternalError`, message
*"Could not compute wing reference area: …"*).

### `GET /aeroplanes/{aeroplane_id}/cg_comparison`

| | |
|---|---|
| `operation_id` | `get_cg_comparison` |
| Request | — |
| Response | `CGComparisonResponse` |
| Status | 200 · 404 · 500 |

| Field | Type | Meaning |
|---|---|---|
| `design_cg_x` | float | effective `cg_x` assumption — *CG_aero* = `x_np − SM·MAC` (metres) |
| `component_cg_x` / `_y` / `_z` | float \| null | mass-weighted aggregate over `weight_items` (metres) |
| `component_total_mass_kg` | float \| null | `Σ mᵢ` (kg) |
| `delta_x` | float \| null | `design_cg_x − component_cg_x`; **positive ⇒ the design CG is aft of the components** 🟡 |
| `within_tolerance` | bool \| null | `|delta_x| < 0.01 m` |

Every `component_*` field, `delta_x` and `within_tolerance` are `null` together
when the inventory is empty or its total mass is `≤ 0`. `design_cg_x` is always
present — or the request is a 404. 🟢

404 when the aeroplane **or** the `cg_x` design-assumption row is missing. 🟡 The single envelope (`Q-CC-3`) requires distinguishable `code` values. A
missing assumption row reporting as "aeroplane not found" is indistinguishable
to the client, because the bare `{"detail": …}` envelope carries no entity code.

## Unit contract for this module 🟢

| Quantity | Unit |
|---|---|
| `mass_kg`, `total_mass_kg`, `component_total_mass_kg` | kilograms |
| `x_m` / `y_m` / `z_m`, `cg_*_m`, `design_cg_x`, `component_cg_*`, `delta_x` | metres |
| `CG_TOLERANCE_M` | metres (`0.01`) |
| `wing_loading_pa` | pascals (N/m²) |
| `stall_speed_ms`, `velocity` | m/s |
| `altitude` | metres |
| `s_ref` | m² |
| `cl_max`, `required_cl`, `cl_margin` | dimensionless |
| `GRAVITY` | `9.81` m/s² — 🟡 collapses into one physical-constants module with `powertrain`'s `9.80665` (`Q-MB-8`) |

The component tree, whose roll-up feeds the same `mass` assumption, works in
**grams** and **millimetres**; the conversion to kilograms happens in
`get_aircraft_total_weight_kg` before it reaches this module.

## Events published 🟢

| Event | When | Consumer |
|---|---|---|
| `AssumptionChanged(aeroplane_id, parameter_name="mass")` | at the end of both syncs, after `update_calculated_value` | `assumption_compute_service` — retrim + V_stall recompute |
| `mark_ops_dirty(db, aeroplane.id)` | same place, immediately before the publish | `invalidation_service` — marks operating points DIRTY |

Both fire on **every** sync, including one that writes `None`. 🟢

## Not part of this contract

- The component tree itself and `GET /component-tree/weight` →
  [`aeroplane-core`](../aeroplane-core/contracts.md).
- `design_assumptions` CRUD, `active_source` switching, the divergence ladder,
  the CG envelope and loading scenarios → `mission-and-sizing`.
- `GET /aeroplanes/{id}/total_mass_kg` and its upsert — a **separate** scalar on
  the `aeroplanes` row, owned by `aeroplane-core`, unrelated to the `mass`
  design assumption. 🟢 **The `mass` design assumption is authoritative and `total_mass_kg` becomes a derived view of it** (`Q-MB-7`, maintainer-answered). Previously the two masses were easy to confuse and nothing
  reconciles them.
</content>
