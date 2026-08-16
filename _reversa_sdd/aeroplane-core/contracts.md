# aeroplane-core — External Contracts

> REST contract exactly as captured in `code-analysis.md` §Module: aeroplane-core.
> All routes are mounted at the **application root** — `openvsp_import` is the only
> router carrying a path prefix, so there is no `/api/v2` segment here. 🟢
> `{aeroplane_id}` is always the **public UUID**, never the integer PK. 🟢

## Global error contract 🟢

Domain exceptions (`app/core/exceptions.py`) are translated by
`_raise_http_from_domain` (`app/api/v2/endpoints/aeroplane/base.py:52-67`):

| Exception | HTTP | Envelope `code` |
|---|---|---|
| `NotFoundError` | 404 | `not_found` |
| `ValidationError` / `ValidationDomainError` | 422 | `validation_error` |
| `ConflictError` | 409 | `conflict` |
| `InternalError` | 500 | `internal_error` |
| bare `ServiceException` | 500 | `service_error` |

Uniform body:

```json
{ "error": { "code": "not_found", "message": "Aeroplane not found", "details": { "id": "…", "entity": "Aeroplane" } } }
```

`details` is serialised with `jsonable_encoder(..., custom_encoder={BaseException: str})`.
Every handler additionally carries a defensive `except Exception → 500`.
🔴 Two global handlers emit **German** messages in an otherwise English API:
`IntegrityError → 409 "name existiert bereits"` and
`RequestValidationError → 422 "Ungültige Eingabedaten"`.

## Aggregate routes — `app/api/v2/endpoints/aeroplane/base.py` 🟢

### `GET /aeroplanes`

| | |
|---|---|
| Handler | `get_aeroplanes` (l.76) |
| Query | `heads_only: bool = True` |
| Response | `GetAeroplaneResponse` — the list of aeroplanes ordered by `name` |
| Status | 200 · 500 |
| Semantics | With `heads_only=true` only branch-head nodes are returned, hiding immutable version snapshots (l.78-95) |

### `POST /aeroplanes`

| | |
|---|---|
| Handler | `create_aeroplane` (l.130) |
| Request | aeroplane name |
| Response | `CreateAeroplaneResponse` (carries the new UUID) |
| Status | **201** · 422 · 500 |
| Side effects | Creates the lineage root (`root_id = id`) and the `main` branch (`is_main=true`, `created_by="human"`) in the same transaction |

### `GET /aeroplanes/{aeroplane_id}`

| | |
|---|---|
| Handler | `get_aeroplane` (l.154) |
| Response | `AeroplaneSchema` — `name`, `total_mass_kg`, `wings: OrderedDict[str, AsbWingSchema]`, `fuselages: OrderedDict[str, FuselageSchema]`, `xyz_ref: list[float]` (metres) |
| Status | 200 · 404 · 500 |
| Note | Wing/fuselage ordering is preserved but **the first wing is not necessarily the main wing** — the main wing is the largest planform area (gh-788) |

### `DELETE /aeroplanes/{aeroplane_id}`

| | |
|---|---|
| Handler | `delete_aeroplane` (l.176) |
| Response | `OperationStatusResponse` |
| Status | 200 · 404 · 500 |
| Side effects | ORM cascade over wings, fuselages, weight items, assumptions, copilot messages, loading scenarios, stability results; then best-effort `cleanup_aeroplane_step_files()` whose failure is logged and ignored |

### `GET /aeroplanes/{aeroplane_id}/total_mass_kg`

| | |
|---|---|
| Handler | `get_aeroplane_total_mass_in_kg` (l.200) |
| Response | `AeroplaneMassRequest` (the same schema is used for read) |
| Status | 200 · 404 · 500 |

### `POST /aeroplanes/{aeroplane_id}/total_mass_kg`

| | |
|---|---|
| Handler | `create_aeroplane_total_mass_kg` (l.226) |
| Request | `AeroplaneMassRequest` — `total_mass_kg: float` (kg) |
| Response | `OperationStatusResponse` |
| Status | **201 on create · 200 on update** · 404 · 422 · 500 |
| Semantics | Upsert; `set_aeroplane_mass` returns `True` when the value was newly created, which selects the status code |

### `GET /aeroplanes/{aeroplane_id}/airplane_configuration`

| | |
|---|---|
| Handler | `get_aeroplane_airplane_configuration` (l.261) |
| Response | `AirplaneConfigurationResponse` — the `cad_designer` `AirplaneConfiguration` payload (millimetre world) |
| Status | 200 · **422 when `total_mass_kg` is null** · 404 · 500 |
| Guarantees | The body contains no `np.ndarray` / `np.generic`; `_to_json_compatible` runs before the response is built |

## Component-tree routes — `app/api/v2/endpoints/aeroplane/component_tree.py` (l.52-128) 🟢

Base path: `/aeroplanes/{aeroplane_id}/component-tree`

| Method | Path | Operation | Status |
|---|---|---|---|
| GET | `` | read the whole tree with computed `total_weight_g` and `weight_status` | 200 · 404 · 500 |
| POST | `` | add a node (`group` \| `cad_shape` \| `cots`) | 201 · 404 · 422 · 500 |
| PUT | `/{node_id}` | partial update of a node | 200 · 404 · 422 · 500 |
| DELETE | `/{node_id}` | delete a node (subtree follows the cascade) | 200 · 404 · 500 |
| POST | `/move` | reparent a node | 200 · **422 on a descendant target** · 404 · 500 |
| GET | `/weight` | aircraft total weight in kg | 200 · 404 · 500 |

### Node payload — significant fields 🟢

| Field | Type | Meaning |
|---|---|---|
| `node_type` | `"group"` \| `"cad_shape"` \| `"cots"` | free-text discriminator |
| `parent_id` | int \| null | null ⇒ root |
| `sort_index` | int | sibling ordering |
| `weight_override_g` | float \| null | **grams**; highest precedence |
| `component_id` | int \| null | COTS component (`mass_g × quantity`) |
| `quantity` | int | multiplier for COTS mass |
| `construction_part_id` | int \| null | snapshot source for `volume_mm3` / `area_mm2` / `material_id` |
| `volume_mm3`, `area_mm2` | float \| null | CAD-shape metrics (**mm³ / mm²**) |
| `material_id` | int \| null | material component supplying `density_kg_m3` |
| `print_type` | `"volume"` \| `"surface"` | selects the weight formula |
| `print_resolution_mm` | float | default **0.4**, surface prints only |
| `scale_factor` | float | multiplier on the calculated mass |
| `synced_from` | string \| null | `"wing:<name>"` / `"fuselage:<name>"` for auto-synced groups |

### Computed read-only fields 🟢

| Field | Rule |
|---|---|
| `own_weight_g` | precedence chain: `override` → `cots` → `calculated` → `none` |
| `weight_source` | `"override"` \| `"cots"` \| `"calculated"` \| `"none"` |
| `total_weight_g` | own + Σ children (post-order) |
| `weight_status` | leaf: `valid` if source ≠ `none` else `invalid`; parent: all-valid ⇒ `valid`, all-invalid ⇒ `partial` if own present else `invalid`, mixed ⇒ `partial` |

`GET /weight` returns `null` (not `0`) when the tree is empty. 🟢

## Unit contract for this module 🟢

| Quantity | Unit |
|---|---|
| `total_mass_kg` | kilograms |
| `xyz_ref` | metres |
| component-tree weights (`own_weight_g`, `total_weight_g`, `weight_override_g`) | grams |
| `get_aircraft_total_weight_kg` | kilograms |
| `volume_mm3` / `area_mm2` / `print_resolution_mm` | mm³ / mm² / mm |
| `AirplaneConfiguration` payload geometry | **millimetres** (`cad_designer` world) |

## Not part of this contract

- Branch, snapshot, adopt, restore and compare routes → `versioning`.
- `/aeroplanes/{id}/wings/**` and `/aeroplanes/{id}/fuselages/**` →
  `wing-design` / `fuselage-design`.
- MCP tool wrappers that re-enter these handlers in-process → `mcp-server`.
