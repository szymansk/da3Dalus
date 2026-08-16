# wing-design — External Contracts

> REST contract exactly as captured in `code-analysis.md` §Module: wing-design.
> All routes are mounted at the **application root** — there is no `/api/v2`
> segment. 🟢 `{aeroplane_id}` is always the **public UUID**, never the integer
> PK. 🟢 A wing is addressed by its **name**, a station by its **index**.

## Global error contract 🟢

The same `_raise_http_from_domain` mapping as `aeroplane-core` applies
(`app/api/v2/endpoints/aeroplane/base.py:52-67`):

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

⚠ **Duplicate-name divergence.** `create_wing` raises `ValidationError` → **422**
for a duplicate wing name, whereas `create_fuselage` raises `ConflictError` →
**409** for the same situation (`wing_service.py:285-289` vs
`fuselage_service.py:80-84`). 🟢 CONFIRMED, 🔴 GAP on whether this is intended.

## Unit contract for this module 🟢

| Quantity | Wire unit | Storage unit |
|---|---|---|
| `xyz_le`, `chord` | metres | metres |
| `twist`, `dihedral` | degrees | degrees |
| spar `spare_support_dimension_width/height`, `spare_length`, `spare_start`, `spare_origin` | **metres** | **millimetres** (gh-402) |
| `spare_vector` | dimensionless unit vector | dimensionless |
| TED `hinge_spacing`, `side_spacing_root/tip` | millimetres | millimetres |
| servo dimensions (`app/schemas/Servo.py`) | millimetres | millimetres |
| turbulator `position_root` / `position_tip` | x/c fraction `[0,1]` | same |
| turbulator `height_mm` | millimetres | millimetres |
| `WingConfiguration` payload geometry | **millimetres** | — |
| spar sizing `M` / `σ_allow` / dimensions / `W` | N·m / MPa / mm / mm³ | — |

The self-describing `units` block on a wing always reports
`{geometry_length: "m", detail_length: "m", angle: "deg"}`
(`aeroplanemodel.py:297-303`). 🟡 **`units` describes the wire format only, and
that is correct** (`Q-WD-2`): the API delivers metres either way, so a
storage-unit override would put "how this column happens to be persisted" into
the public contract — which **ADR 0019** rule 4 forbids, since such a field
exists only because of an internal representation and carries no meaning for a
client. No override is added. Derived from the ADR rather than decided
directly, so INFERRED.

## Wing routes — `app/api/v2/endpoints/aeroplane/wings.py` (1039 l., ≈30 routes) 🟢

Base path: `/aeroplanes/{aeroplane_id}/wings`

| Method | Path suffix | Handler | Request | Response | Status |
|---|---|---|---|---|---|
| GET | `` | `get_aeroplane_wings` | — | wing names | 200 · 404 · 500 |
| PUT | `/{wing_name}` | `create_aeroplane_wing` | `AsbWingSchema` | wing | 201 · **422 duplicate name** · 404 · 500 |
| POST | `/{wing_name}` | `update_aeroplane_wing` | `AsbWingSchema` | wing | 200 · 404 · 422 · 500 |
| GET | `/{wing_name}` | `get_aeroplane_wing` | — | `AsbWingReadSchema` | 200 · 404 · 500 |
| DELETE | `/{wing_name}` | `delete_aeroplane_wing` | — | `OperationStatusResponse` | 200 · 404 · 500 |
| POST | `/{wing_name}/from-wingconfig` | `create_aeroplane_wing_from_wingconfig` | `WingConfiguration` (**mm**) | wing | 201 · 404 · 422 · 500 |
| GET | `/{wing_name}/wingconfig` | `get_wing_as_wingconfig` | — | `WingConfiguration` (**mm**) | 200 · 404 · 500 |
| PUT | `/{wing_name}/wingconfig` | `put_wing_as_wingconfig` | `WingConfiguration` (**mm**) | wing | 200 · 404 · 422 · 500 |

**Side effects.** `PUT /{wing_name}` and `POST .../from-wingconfig` create the
component-tree group `wing:<name>`; `DELETE /{wing_name}` removes nodes by the
`synced_from` prefix (gh#108, `wing_service.create_wing:298-300`). 🟢

**`design_model` stamping.** `'asb'` on the ASB-geometry create path,
`'wc'` on the `WingConfiguration` create path, `NULL` for legacy rows
(`wing_service.py:292, 341`; `aeroplaneschema.py:652-655`). 🟢

## Station routes 🟢

Base path: `/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections`

| Method | Path suffix | Operation | Status |
|---|---|---|---|
| GET | `` | list stations, ordered by `sort_index` | 200 · 404 · 500 |
| DELETE | `` | delete all stations | 200 · 404 · 500 |
| GET | `/{i}` | read station `i` | 200 · 404 · 500 |
| POST | `/{i}` | create a station at index `i` | 201 · 404 · **422 terminal-station segment data** · 500 |
| PUT | `/{i}` | update station `i` | 200 · 404 · **422 terminal-station segment data** · 500 |
| DELETE | `/{i}` | delete station `i` | 200 · 404 · 500 |

**Terminal-station rule (BR-5).** Any segment-scoped field
(`spare_list`, `trailing_edge_device`, `turbulator`, `x_sec_type`, `tip_type`,
`number_interpolation_points`) on the **last** station is rejected. Three
independent layers enforce it: schema
(`AsbWingSchema.validate_last_xsec_has_no_segment_details`,
`aeroplaneschema.py:666-680`), model (`WingModel.from_dict` blanks the six fields
when `index == len(xsec_dicts) - 1`, `aeroplanemodel.py:489-490`) and service
(`_assert_non_terminal_xsec_or_raise`, `wing_service.py:151-156`). 🟢

**Minimum stations.** `AsbWingSchema.x_secs` carries `min_length=2`. 🟢

### `WingXSecSchema` — request/response fields 🟢

| Field | Type | Required | Unit / note |
|---|---|---|---|
| `xyz_le` | `list[float]` | yes | metres, leading-edge point |
| `chord` | `float` | yes | metres |
| `twist` | `float` | yes | degrees |
| `dihedral` | `float \| None` | no | degrees; explicitly persisted (gh-951), `NULL` ⇒ derive from geometry |
| `airfoil` | `str \| HttpUrl` | yes | `.dat` path or URL |
| `control_surface` | `ControlSurfaceSchema \| None` | no | ASB projection of the TED; `hinge_point` default `0.8`, `symmetric` default `True` |
| `x_sec_type` | `"root" \| "segment" \| "tip" \| None` | no | segment-scoped |
| `tip_type` | `"flat" \| "round" \| None` | no | segment-scoped, meaningful only when `x_sec_type == "tip"` |
| `number_interpolation_points` | `int \| None` | no | segment-scoped loft sampling override |
| `spare_list` | `list[SpareDetailSchema] \| None` | no | segment-scoped |
| `trailing_edge_device` | `TrailingEdgeDeviceDetailSchema \| None` | no | segment-scoped |
| `turbulator` | `TurbulatorDetailSchema \| None` | no | segment-scoped |

`AsbWingGeometryWriteSchema` and `WingXSecGeometryWriteSchema` are the
`extra="forbid"` geometry-only write variants — they carry no spar, TED or
turbulator fields at all. 🟢

## Spar routes 🟢

Base path: `.../cross_sections/{i}/spars`

| Method | Path suffix | Operation | Status |
|---|---|---|---|
| GET | `` | list the segment's spars, ordered by `sort_index` | 200 · 404 · 500 |
| POST | `` | create a spar | 201 · 404 · **422 terminal station** · 500 |
| PUT | `/{spar_index}` | update a spar | 200 · 404 · 422 · 500 |
| DELETE | `/{spar_index}` | delete a spar | 200 · 404 · 500 |

### `SpareDetailSchema` — the metre/millimetre boundary 🟢

| Field | Type | Wire unit | Storage |
|---|---|---|---|
| `spare_support_dimension_width` | float, required | m | mm |
| `spare_support_dimension_height` | float, required | m | mm |
| `spare_position_factor` | float \| null | relative chord `0–1` | same |
| `spare_length` | float \| null | m | mm |
| `spare_start` | float \| null | m | mm |
| `spare_mode` | `normal \| follow \| standard \| standard_backward \| orthogonal_backward` \| null | — | — |
| `spare_vector` | `[x,y,z]` \| null | **dimensionless** | dimensionless |
| `spare_origin` | `[x,y,z]` \| null | m | mm |

Conversion happens in `wing_service._convert_spare_to_meters` (l.49-66) and
`_convert_spare_to_mm` (l.69-88) with `_MM_TO_M = 0.001` (l.43) and
`_M_TO_MM = 1000.0` (l.46). `spare_vector` is never scaled. 🟢

⚠ The `SpareDetailSchema` field descriptions say "in meters" — true of the wire
format, false of the storage. 🟡 **The descriptions are clarified** to say they
describe the wire format (`Q-WD-2`); they are not factually wrong, so this is a
clarification rather than a correction. It must land **before** TypeScript
client generation (`Q-CC-11`), which bakes these descriptions into generated
code.

## Trailing-edge-device routes 🟢

| Method | Path | Operation | Status |
|---|---|---|---|
| GET | `.../cross_sections/{i}/trailing_edge_device` | read the TED | 200 · 404 · 500 |
| PATCH | `.../cross_sections/{i}/trailing_edge_device` | partial update (`TrailingEdgeDevicePatchSchema`, `extra="forbid"`, non-empty patch required) | 200 · 404 · **422 role-gated mixing** · 500 |
| DELETE | `.../cross_sections/{i}/trailing_edge_device` | delete the TED (cascades to the servo) | 200 · 404 · 500 |
| GET / PATCH / DELETE | `.../trailing_edge_device/servo` | TED servo, 1:1 child | 200 · 404 · 422 · 500 |
| GET / PATCH / DELETE | `.../cross_sections/{i}/control_surface` | the ASB-compatible projection | 200 · 404 · 422 · 500 |
| GET / PATCH / DELETE | `.../control_surface/cad_details` | CAD-only subset (`ControlSurfaceCadDetailsSchema`) | 200 · 404 · 422 · 500 |
| GET / PATCH / DELETE | `.../control_surface/cad_details/servo_details` | servo subset | 200 · 404 · 422 · 500 |

### Mixing fields — validation contract (gh-772) 🟢

| Field | Range | Legal for |
|---|---|---|
| `mix_gain_primary` | `0 < x ≤ 5`, default `1.0` | any role |
| `mix_gain_secondary` | `0 < x ≤ 5`, default `1.0` | `≠ 1.0` only for `DUAL_ROLE_VALUES = {elevon, flaperon, ruddervator}` |
| `differential_ratio` | `0.3 < x ≤ 3`, default `1.0` | `≠ 1.0` only for `DIFFERENTIAL_ROLE_VALUES = {aileron, elevon, flaperon, ruddervator}` |

Comparisons use `math.isclose(rel_tol=1e-9, abs_tol=1e-9)`; a `None` role on a
partial patch **skips** the check entirely
(`_validate_mix_fields`, `aeroplaneschema.py:51-78`). Violations → **422**. 🟢

`differential_ratio` is a **reporting-only kinematic** applied after trim for
left/right display; it never alters the aero or trim solution
(`control_surface_mixing.py:14-15`; `aeroplaneschema.py:372-381`). 🟢

### Derived control variables (not a REST payload, but part of the contract) 🟢

`axis_control_name` → `[{role}]{axis}_{wing_key}_{xsec_index}`, e.g.
`[ruddervator]pitch_htail_1`. A dual-role surface produces two variables:

| axis | `sgn_dup` | gain | `symmetric` | baseline deflection |
|---|---|---|---|---|
| primary (`pitch` \| `lift`) | `+1.0` | `mix_gain_primary` | `True` | the surface's deflection |
| secondary (`roll` \| `yaw`) | `−1.0` | `mix_gain_secondary` | `False` | **`0.0`** |

`assert_unique_control_names` raises before any AVL geometry is written, because
AVL silently collapses identically named `CONTROL` variables into a single DOF
(`control_surface_mixing.py:149-164`). 🟢

## Turbulator routes (gh-934) 🟢

| Method | Path | Operation | Status |
|---|---|---|---|
| GET | `.../cross_sections/{i}/turbulator` | read the segment's turbulator | 200 · 404 · 500 |
| PUT | `.../cross_sections/{i}/turbulator` | create or replace | 200 · 404 · **422 terminal station** · 500 |
| DELETE | `.../cross_sections/{i}/turbulator` | delete | 200 · 404 · 500 |

`TurbulatorDetailSchema`: `form` (`zigzag` \| `dots` \| `thread`, default
`zigzag`), `height_mm` (`≥ 0`, default `0.3`), `position_root`
(**required**, x/c `[0,1]`), `position_tip` (x/c `[0,1]`, falls back to
`position_root`), `enabled` (default `True`). 🟢

### `POST /aeroplanes/{aeroplane_id}/turbulator/optimize` 🟢

| | |
|---|---|
| Handler | `turbulator_optimizer.py:173` |
| Response | per-section `xtr_opt`, `delta_cd`, plus aircraft-level `ΔCD0` and a warnings list |
| Status | 200 · 404 · 422 · 500 |
| Guarantees | `xtr_opt ∈ XTR_GRID = linspace(0.2, 0.9, 15)`; `delta_cd = cd_tripped − cd_clean`; anomalies (all-NaN `cd`, mean `analysis_confidence < 0.80`, boundary optimum) are returned as **warnings**, never substituted by a fallback value (ADR 0012) |

## Diagnostic routes 🟢

| Method | Path | Operation | Status |
|---|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/wings/{wing_name}/section-aoa` | per-section angle of attack (`section_aoa.py:74`); returns **half-span** sections only | 200 · 404 · 500 |

## Not part of this contract

- Building the CAD solid from a `WingConfiguration` → `cad-generation`.
- Running VLM / AeroBuildup / AVL over the wing → `aero-analysis`,
  `avl-integration`.
- Spar-plan persistence beyond `_sync_spares_for_xsec` and the construction
  drawings that consume it → `construction-plans`.
- The frozen `cad_designer` topology classes themselves →
  `cad-designer-topology` (read-only, ADR 0002).
- MCP tool wrappers that re-enter these handlers in-process → `mcp-server`.
