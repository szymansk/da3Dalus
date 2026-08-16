# construction-plans — External Contracts

> REST contract exactly as captured in `code-analysis.md` §Module:
> construction-plans and verified against the route decorators.
> All routes are mounted at the **application root** — there is no `/api/v2`
> segment. 🟢 `{aeroplane_id}` is always the **public UUID**; `{plan_id}` and
> `{part_id}` are **integer primary keys**; `{execution_id}` is the
> timestamp-based directory name `%Y%m%dT%H%M%SZ` (with a `-N` suffix on
> same-second collisions) allocated by `artifact_service`.

## Global error contract 🟢

This module does **not** use the `_raise_http_from_domain` envelope of the
aeroplane routers. Each of the three plan routers defines its own
`_handle_service_error`:

```python
status_map = {
    NotFoundError:    404,
    ValidationError:  422,
    InternalError:    500,
}
code = status_map.get(type(exc), 500)
raise HTTPException(status_code=code, detail=str(exc.message))
```

(`construction_plans.py:37-47`, `aeroplane_construction_plans.py:26-36`,
`construction_templates.py:23-33`.) The response body is therefore the bare
FastAPI shape:

```json
{ "detail": "…" }
```

⚠ 🟢 **One error envelope everywhere; the per-module mappers are deleted** (`Q-CC-3`). Previously `ConflictError` was not in the map: It falls through
`status_map.get(..., 500)` and surfaces as a **500**, not a 409. No plan-service
path raises `ConflictError` today, so the defect is latent — but it forecloses
any future conflict semantics on plans.

⚠ 🟢 **One envelope everywhere** (`Q-CC-3`). Previously two coexisted: The rest of the API answers
`{"error": {"code", "message", "details"}}`. A client cannot parse errors
uniformly across this API. Recorded as a global gap in `data-dictionary.md`
§"HTTP error envelopes — two coexisting shapes".

### Construction-parts router — a different, fuller mapping 🟢

`app/api/v2/endpoints/aeroplane/construction_parts.py:44-63` maps:

| Exception | HTTP | Note |
|---|---|---|
| `NotFoundError` | 404 | also the answer for a part id under the wrong aeroplane |
| `ValidationError` | 422 | empty upload, bad suffix, STEP-from-STL request |
| `ConflictError` **with** `details["reason"] == "file_too_large"` | **413** | the marker exists solely to split this case out |
| `ConflictError` (any other) | 409 | e.g. deleting a locked part |
| anything else | 500 | |

Body shape is still `{"detail": "…"}`.

## Platform gating 🟢

- The Creator catalog route answers `200 []` when `cad_designer` cannot be
  imported — it never 500s and never 503s (ADR 0017).
- Plan **execution** requires CadQuery. On a platform without it the decode or
  the `create_shape()` call fails and surfaces as an `ExecutionResult` with
  `status == "error"` (HTTP 200) or a 422 decode error — there is **no**
  capability probe on these routes. 🟡
- Construction-part **upload** works without CadQuery; only the geometry fields
  come back null.

## Unit contract for this module 🟢

| Quantity | Wire unit | Note |
|---|---|---|
| `wing_config` passed to Creators | **millimetres** | `wing_model_to_wing_config(wing, scale=1000.0)` — the metre DB is converted at the execution boundary (ADR 0001) |
| `Printer3dSettings.layer_height` / `wall_thickness` / `rel_gap_wall_thickness` | millimetres | fallback `0.24 / 0.42 / 0.075` |
| `ConstructionPartRead.volume_mm3` | mm³ | STEP uploads only |
| `ConstructionPartRead.area_mm2` | mm² | STEP uploads only |
| `ConstructionPartRead.bbox_x_mm` / `bbox_y_mm` / `bbox_z_mm` | millimetres | STEP uploads only |
| `ExecutionResult.duration_ms` | milliseconds | |
| tessellation `deviation` / `angular_tolerance` | dimensionless | `0.1` / `0.2`, identical to `cad-generation`'s wing tessellation |
| `ArtifactFile.size_bytes` | bytes | |
| `ArtifactFile.modified` / `ArtifactDirectory.created` | ISO-8601 string | |

## Plan routes — `app/api/v2/endpoints/construction_plans.py` (294 l.) 🟢

Base path: `/construction-plans`

| Method | Path | Handler (`operation_id`) | Request | Response | Status |
|---|---|---|---|---|---|
| GET | `/construction-plans/creators` | `list_creators` | — | `list[CreatorInfo]` | 200 · 500 |
| GET | `/construction-plans` | `list_construction_plans` | query `plan_type?` | `list[PlanSummary]` | 200 · 500 |
| POST | `/construction-plans` | `create_construction_plan` | `PlanCreate` | `PlanRead` | **201** · 422 · 500 |
| GET | `/construction-plans/{plan_id}` | `get_construction_plan` | — | `PlanRead` | 200 · 404 · 500 |
| PUT | `/construction-plans/{plan_id}` | `update_construction_plan` | `PlanCreate` | `PlanRead` | 200 · 404 · 422 · 500 |
| DELETE | `/construction-plans/{plan_id}` | `delete_construction_plan` | — | — | **204** · 404 · 500 |
| POST | `/construction-plans/{plan_id}/execute` | `execute_construction_plan` | `ExecuteRequest` | `ExecutionResult` | 200 · 404 · 422 · 500 |

⚠ **Route ordering is load-bearing.** `/construction-plans/creators` is declared
**before** `/construction-plans/{plan_id}`, with an in-code comment saying so
(`construction_plans.py:51-59`). Reversed, the literal `"creators"` would be
captured as a `plan_id` and the catalog would be unreachable. 🟢

⚠ **`POST .../execute` answers 200 even when the execution failed.** Failure is
carried in the body as `ExecutionResult.status == "error"`; only *setup* errors
(unknown plan → 404, template without an aeroplane → 422, undecodable tree →
422) use a non-2xx status. A client must inspect the body. 🟢

### Artefact routes 🟢

Base path: `/construction-plans/{plan_id}/artifacts`

| Method | Path suffix | Handler | Query | Response | Status |
|---|---|---|---|---|---|
| GET | `` | `list_plan_artifacts` | — | `list[ArtifactDirectory]` | 200 · 404 · 500 |
| GET | `/{execution_id}` | `list_artifact_files` | `subpath: str = ""`, `recursive: bool = false` | `list[ArtifactFile]` | 200 · 404 · 500 |
| GET | `/{execution_id}/zip` | `download_execution_zip` | — | `application/zip`, filename `plan-{plan_id}-{execution_id}.zip` | 200 · 404 · 500 |
| GET | `/{execution_id}/{filename:path}` | `download_artifact_file` | — | file download, filename = basename | 200 · 404 · 422 · 500 |
| DELETE | `/{execution_id}/{filename:path}` | `delete_artifact_file` | — | — | **204** · 404 · 500 |
| DELETE | `/{execution_id}` | `delete_execution` | — | — | **204** · 404 · 500 |

The `{filename:path}` converter accepts subdirectory paths such as
`wing/file.stl`. Every path is resolved and confined by
`artifact_service._ensure_within_base`; a traversal attempt raises
`ValidationError` → 422. `get_file_path` additionally rejects symlinks. An
execution with no files yields a **valid empty zip**, not a 404. Storage
semantics are specified in `cad-generation`. 🟢

⚠ 🟡 `list_executions` scans `_template_runs` as though it were an aeroplane
directory, unlike `_resolve_execution_dir`, which skips it — so a template run
can appear in a plan listing with `aeroplane_id == "_template_runs"`.

## Aeroplane-scoped plan routes — `aeroplane_construction_plans.py` (150 l.) 🟢

| Method | Path | Handler (`operation_id`) | Request | Response | Status |
|---|---|---|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/construction-plans` | `list_aeroplane_construction_plans` | — | `list[PlanSummary]` | 200 · 404 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/construction-plans/from-template/{template_id}` | `instantiate_template` | `InstantiateRequest` (optional body) | `PlanRead` | **201** · 404 · **422 not a template** · 500 |
| POST | `/aeroplanes/{aeroplane_id}/construction-plans/{plan_id}/execute` | `execute_aeroplane_construction_plan` | — (the aeroplane comes from the path) | `ExecutionResult` | 200 · 404 · 422 · 500 |
| GET | `/aeroplanes/{aeroplane_id}/construction-plans/{plan_id}/execute-stream` | `execute_aeroplane_construction_plan_stream` | — | **SSE** | 200 · 404 · 422 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/construction-plans/{plan_id}/to-template` | `plan_to_template` | `ToTemplateRequest` (optional body) | `PlanRead` | **201** · 404 · 500 |

The aeroplane-scoped `/execute` builds `ExecuteRequest(aeroplane_id=<path>)`
internally, so a template can be executed through this route without a body. 🟢

### SSE contract — `GET .../{plan_id}/execute-stream` 🟢

`media_type: text/event-stream`, headers:

| Header | Value | Why |
|---|---|---|
| `Cache-Control` | `no-cache` | |
| `Connection` | `keep-alive` | |
| `X-Accel-Buffering` | `no` | stops nginx buffering the stream |

Frames:

```
event: shape
data: {"name": "<shape id>", "tessellation": { … }}

event: complete
data: {"duration_ms": 1234, "shape_keys": ["…"], "tessellation": { … } | null,
       "artifact_dir": "…", "execution_id": "20260731T004512Z"}

event: error
data: {"error": "…", "duration_ms": 1234,
       "artifact_dir": "…", "execution_id": "20260731T004512Z"}
```

Guarantees:

- One `shape` frame per `Workplane.display(...)` call inside any Creator — the
  gate is the `@conditional_execute("DISPLAY_CONSTRUCTION_STEP")` decorator plus
  a module-global display callback, both armed for the duration of the stream
  and restored in `finally`. 🟢
- All NumPy values in a `tessellation` payload are flattened to plain JSON by
  `_numpy_to_list` before serialisation. 🟢
- Queue starvation after **300 s** emits
  `event: error {"error": "Execution timed out"}`; the worker thread is then
  joined with a **5 s** timeout. The thread is a daemon, so a hung OCCT call is
  abandoned, not awaited. 🟢
- Setup errors (unknown plan, template without an aeroplane) are raised **before**
  the `StreamingResponse` is created and therefore surface as ordinary HTTP
  status codes, not as an `error` frame. 🟢

⚠ 🟡 Both the display callback and `DISPLAY_CONSTRUCTION_STEP` are
**process-global**. Two concurrent streams cross-deliver shape frames, and a
non-streaming execution running at the same time will have its shapes emitted
into the open stream.

## Template routes — `construction_templates.py` (65 l.) 🟢

| Method | Path | Handler | Request | Response | Status |
|---|---|---|---|---|---|
| GET | `/construction-templates` | `list_construction_templates` | — | `list[PlanSummary]` | 200 · 500 |
| POST | `/construction-templates` | `create_construction_template` | `PlanCreate` | `PlanRead` | **201** · 422 · 500 |

This router is a convenience projection: it lists rows with
`plan_type == "template"` and creates rows stamped as templates. The generic
`/construction-plans?plan_type=template` returns the same set. 🟢

## Construction-part routes — `aeroplane/construction_parts.py` (218 l.) 🟢

Base path: `/aeroplanes/{aeroplane_id}/construction-parts`

| Method | Path suffix | Handler | Request | Response | Status |
|---|---|---|---|---|---|
| GET | `` | `list_construction_parts` | — | `ConstructionPartList` | 200 · 404 · 500 |
| POST | `` | `upload_construction_part` | **multipart** — see below | `ConstructionPartRead` | **201** · 404 · **413 too large** · 422 · 500 |
| GET | `/{part_id}` | `get_construction_part` | — | `ConstructionPartRead` | 200 · 404 · 500 |
| PUT | `/{part_id}` | `update_construction_part` | `ConstructionPartUpdate` | `ConstructionPartRead` | 200 · 404 · 422 · 500 |
| DELETE | `/{part_id}` | `delete_construction_part` | — | — | **204** · 404 · **409 locked** · 500 |
| PUT | `/{part_id}/lock` | `lock_construction_part` | — | `ConstructionPartRead` | 200 · 404 · 500 |
| PUT | `/{part_id}/unlock` | `unlock_construction_part` | — | `ConstructionPartRead` | 200 · 404 · 500 |
| GET | `/{part_id}/file` | `download_construction_part_file` | query `format: "step" \| "stl" = "stl"` | file download | 200 · 404 · 422 · 500 |

### Upload multipart fields 🟢

| Field | Type | Required | Note |
|---|---|---|---|
| `file` | `UploadFile` | yes | `.step` / `.stp` / `.stl`; ≤ 52 428 800 bytes |
| `name` | form `str`, `min_length=1` | yes | display name |
| `material_component_id` | form `int` | no | FK → `components.id`; **not** constrained to a `material` component |
| `thumbnail_url` | form `str` | no | preview image URL |

Stored at `tmp/construction_parts/{aeroplane_id}/{part_id}_{uuid4().hex[:8]}{ext}`
— CWD-relative. 🟢 Artefacts live under `ARTIFACTS_BASE_DIR`, and a relative value is now **rejected** rather than resolved against the process CWD (`Q-PC-6`, `Q-CP-9`).

### Download semantics 🟢

| Source format | `?format=` | Result |
|---|---|---|
| `step` | `step` | the stored file |
| `step` | `stl` | regenerated on the fly via CadQuery into a `tempfile.mkstemp` file — 🔴 **never cleaned up** |
| `stl` | `stl` | the stored file |
| `stl` | `step` | `ValidationError` → **422** (the conversion is not lossless) |

Response filename is always `construction_part_{part_id}.{format}`.

## Schemas

### `PlanCreate` (`app/schemas/construction_plan.py:11`) 🟢

| Field | Type | Required | Default | Note |
|---|---|---|---|---|
| `name` | `str`, `min_length=1` | yes | — | not unique |
| `description` | `str \| None` | no | `None` | |
| `tree_json` | `dict` | yes | — | serialised `ConstructionRootNode` (`$TYPE` dialect); only the root is validated |
| `plan_type` | `str` | no | `"template"` | free text — `"template"` \| `"plan"` by convention, no enum |
| `aeroplane_id` | `str \| None` | no | `None` | required in practice for `plan_type == "plan"`, **not enforced by the schema** 🟡 |

### `PlanRead` (l.26) 🟢
`PlanCreate` + `id: int`, `created_at: datetime`, `updated_at: datetime`.
`model_config = {"from_attributes": True}`.

### `PlanSummary` (l.36) 🟢
`id`, `name`, `description`, `step_count: int = 0`, `plan_type`,
`aeroplane_id`, `created_at`. `step_count` is computed by `_count_steps`, which
counts successor nodes recursively and **excludes the root**.

### `InstantiateRequest` (l.53) / `ToTemplateRequest` (l.59) 🟢
Both carry a single optional `name: str | None` override. The body itself is
optional on both routes.

### `CreatorParam` (l.68) 🟢

| Field | Type | Note |
|---|---|---|
| `name` | `str` | constructor parameter name |
| `type` | `str` | rendered by `_type_to_str` — generics keep their subscript; `typing.` and `cad_designer.airplane.types.` prefixes stripped |
| `default` | `Any \| None` | `None` when the parameter is required |
| `required` | `bool` | `True` when the signature has no default |
| `description` | `str \| None` | from the class docstring's `Attributes:` block |
| `options` | `list[str] \| None` | from `Literal` / `Optional[Literal]` / `Annotated[Literal]` / nested unions |

### `CreatorOutput` (l.79) 🟢
`key: str` (e.g. `{id}`, `{id}.cape`), `description: str` — parsed from the
class docstring's `Returns:` block.

### `CreatorInfo` (l.86) 🟢
`class_name`, `category`, `description: str | None`,
`parameters: list[CreatorParam]`, `outputs: list[CreatorOutput] = []`,
`suggested_id: str | None`.
`category ∈ {wing, fuselage, cad_operations, export_import, components, other}`
(`_CATEGORY_MAP`, `construction_plan_service.py:406-420`). The list is sorted by
`(category, class_name)`. `suggested_id` may contain `{param}` placeholders,
resolved by the decoder from sibling parameter values.

### `ExecuteRequest` (l.106) 🟢
`aeroplane_id: str | None` — optional for a bound plan, **required for a
template** (absent on both the stored plan and the request → 422).

### `ExecutionResult` (l.120) 🟢

| Field | Type | Default | Note |
|---|---|---|---|
| `status` | `Literal["success", "error"]` | — | the real outcome; HTTP is 200 either way |
| `shape_keys` | `list[str]` | `[]` | every key produced by the tree |
| `export_paths` | `list[str]` | `[]` | rewritten absolute export directories |
| `error` | `str \| None` | `None` | populated only when `status == "error"` |
| `duration_ms` | `int` | `0` | |
| `tessellation` | `dict \| None` | `None` | three-cad-viewer payload; `None` when best-effort tessellation failed |
| `artifact_dir` | `str \| None` | `None` | server-side directory, relative to the artefact base |
| `execution_id` | `str \| None` | `None` | `%Y%m%dT%H%M%SZ` (+ `-N` on collision) |

🟡 A `warnings` field carries `DesignWarning`s (`P-WARN-0`, `Q-CP-3`). Today there is no such field, which is why a wing dropped during
`wing_config` conversion cannot be reported.

### `ArtifactFile` (l.144) / `ArtifactDirectory` (l.153) 🟢
`ArtifactFile`: `name: str`, `is_dir: bool = False`, `size_bytes: int = 0`,
`modified: str` (ISO).
`ArtifactDirectory`: `execution_id: str`, `plan_id: int`, `aeroplane_id: str`,
`created: str` (ISO), `file_count: int = 0`.

### `ConstructionPartRead` (`app/schemas/construction_part.py:11`) 🟢
`id`, `aeroplane_id`, `name`, `volume_mm3`, `area_mm2`, `bbox_x_mm`,
`bbox_y_mm`, `bbox_z_mm` (all optional, `ge=0`), `material_component_id`,
`locked: bool`, `thumbnail_url`, `file_path`, `file_format`, `created_at`,
`updated_at`.

### `ConstructionPartUpdate` (l.51) 🟢
`name: str | None` (`min_length=1`), `material_component_id: int | None`,
`thumbnail_url: str | None`. **The file and every geometry field are
deliberately not updatable.**

### `ConstructionPartList` (l.59) 🟢
`aeroplane_id: str`, `items: list[ConstructionPartRead]`, `total: int`.

## Known contract defects 🔴

| # | Defect | Consequence |
|---|---|---|
| D-1 | `ConflictError` missing from the plan routers' `status_map` | a conflict answers **500** instead of 409 |
| D-2 | Two error-envelope shapes across the API (`{"detail"}` here, `{"error": {...}}` on aeroplane routes) | no uniform client-side error parsing |
| D-3 | `ExecutionResult` has no warnings field | a plan executed against a partially converted aircraft reports plain success |
| D-4 | `PlanCreate.aeroplane_id` is not required for `plan_type == "plan"` | a "plan" row can be created unbound; the error only appears at execution |
| D-5 | `plan_type` is free text with no enum or check constraint | a typo produces a row that is neither a template nor a plan |
| D-6 | `construction_plans.aeroplane_id` is a `String` FK to an `Integer` PK, no `ON DELETE` | schema is SQLite-only; deleting an aeroplane leaves its plans |
| D-7 | `construction_parts.aeroplane_id` has no FK | deleting an aeroplane orphans rows **and** files |
| D-8 | STL-from-STEP downloads leak a `mkstemp` file per request | unbounded temp-file growth |
| D-9 | Part files live outside `ARTIFACTS_BASE_DIR` | outside the traversal-guarded tree and any retention policy |
| D-10 | `list_executions` does not skip `_template_runs` | a template run appears in a plan listing with `aeroplane_id == "_template_runs"` |
| D-11 | `material_component_id` is not constrained to `material` components | any component id is accepted; only the UI filters |
| D-12 | Execution routes have no CadQuery capability probe | a platform without CadQuery answers 200 with `status == "error"` rather than 503 |

## Not part of this contract

- The `$TYPE` encode/decode rules, `AbstractShapeCreator`, the Creator classes
  themselves and `Workplane.display` → **`cad-designer-topology`** (frozen,
  ADR 0002).
- Artefact directory allocation, execution-id generation, traversal guards, zip
  construction and the `_template_runs` wiping rule →
  **`cad-generation`** (`artifact_service`). Only the routes over them are
  specified here.
- The CAD process pool, wing tessellation and wing export tasks →
  **`cad-generation`**.
- The **spar** plan (`spar_plan_service`, `spar_insert_service`, `spar_solver`)
  → **`wing-design`**. It shares only the word "plan".
- `wing_model_to_wing_config` and the metre/millimetre boundary →
  **`wing-design`** (ADR 0001).
- `component_tree.construction_part_id` and the component tree →
  **`aeroplane-core`**.
- The plan editor UI, the Creator gallery rendering and the `three-cad-viewer`
  embedding → **`frontend-workbench`**.
