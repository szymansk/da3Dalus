# cad-generation — External Contracts

> REST contract for `app/api/v2/endpoints/cad.py` (412 l.). All routes are
> mounted at the **application root** — there is no `/api/v2` segment. 🟢
> `{aeroplane_id}` is always the **public UUID** (`AeroPlaneID`), never the
> integer PK; a wing is addressed by its **name**. 🟢
> Verified directly against the route decorators and handler bodies; where this
> refines `code-analysis.md` §Module: cad-generation the divergence is marked
> **↺ refined**.

## Conditional mounting — the first thing a client must know 🟢

The **entire CAD router is conditionally included**: `app/main.py:222-223` adds
it only when the `cad_designer` / CadQuery import succeeded. On a platform
without a geometry kernel (`linux/aarch64`, ADR 0017) these five paths **do not
exist** — a client receives a plain 404 from the router table, not a 503 and not
a capability flag. There is no discovery endpoint that reports the difference.
🔴 GAP: a client cannot distinguish "CAD unavailable on this deployment" from
"unknown aeroplane".

## Global error contract 🟢

`_raise_http_from_domain` (`cad.py:41-56`) is the single mapping:

| Exception | HTTP | Envelope `code` |
|---|---|---|
| `NotFoundError` | 404 | `not_found` |
| `ValidationError` | 422 | `validation_error` |
| `ConflictError` | 409 | `conflict` |
| `InternalError` / any other `ServiceException` | 500 | `internal_error` |

```json
{ "error": { "code": "validation_error", "message": "…", "details": { … } } }
```

Every handler additionally wraps a bare `Exception` into
`HTTPException(500, detail=f"Unexpected error: {exc}")`. 🔴 GAP: that fallback
emits FastAPI's `{"detail": …}` shape, **not** the `{"error": {...}}` envelope,
and it interpolates the raw exception text — so an unexpected 500 has a
different body shape and a wider information surface than a mapped one. All five
routes declare `404 · 409 · 422 · 500` in their `responses` block.

## Unit contract for this module 🟢

| Quantity | Wire unit | Worker unit |
|---|---|---|
| stored wing geometry (`xyz_le`, `chord`) | metres (owned by `wing-design`) | — |
| `wing_scale` passed to the worker | — | `1000.0`, metres → **millimetres** |
| tessellation vertices, `bb`, `loc` | **millimetres** | millimetres |
| exporter `tolerance` / `angular_tolerance` | `0.1` / `0.1` (mm, Creator units) | same |
| tessellation `deviation` / `angular_tolerance` | `0.1` / `0.2` | same |

The parent converts `WingModel → AsbWingSchema` (metres) and pickles it; the
worker rebuilds `asb_wing_schema_to_wing_config(schema, scale=1000.0)`. **The
viewer envelope is therefore in millimetres**, and nothing in the response
declares that. 🔴 GAP.

## Routes

Base: the application root.

| # | Method | Path | `operation_id` | Request | Response | Status |
|---|---|---|---|---|---|---|
| 1 | POST | `/aeroplanes/{aeroplane_id}/wings/{wing_name}/tessellation` | `start_wing_tessellation` | — | `CadTaskAcceptedResponse` | **202** · 404 · 409 · 422 · 500 |
| 2 | GET | `/aeroplanes/{aeroplane_id}/tessellation` | `get_aeroplane_tessellation` | — | merged scene (below) | 200 · **404 when nothing is cached** · 409 · 422 · 500 |
| 3 | POST | `/aeroplanes/{aeroplane_id}/wings/{wing_name}/{creator_url_type}/{exporter_url_type}` | `create_wing_loft_export` | query + optional `AeroplaneSettings` body | `CadTaskAcceptedResponse` | **202** · 404 · **409 concurrent export** · **422 unmapped exporter** · 500 |
| 4 | GET | `/aeroplanes/{aeroplane_id}/status` | `get_aeroplane_task_status` | query `task_type`, `wing_name` | `CadTaskStatusResponse` | 200 · 404 · 409 · 422 · 500 |
| 5 | GET | `/aeroplanes/{aeroplane_id}/wings/{wing_name}/{creator_url_type}/{exporter_url_type}/zip` | `download_export_zip` | — | `ZipAssetResponse` | 200 · 404 · 409 · 422 · 500 |

**↺ refined vs `code-analysis.md`:** the download route is **not**
`GET /aeroplanes/{id}/zip`. It carries the full wing/creator/exporter path
segments, and it returns a **JSON descriptor with a static URL**, not the file
bytes (see route 5).

### 1 · Start a wing tessellation 🟢

```
POST /aeroplanes/{aeroplane_id}/wings/{wing_name}/tessellation  →  202
```

1. `get_aeroplane_with_wings` → 404 on an unknown aeroplane.
2. `get_wing_from_aeroplane` → 404 on an unknown wing.
3. `wing_model_to_asb_wing_schema(wing)` → `pickle.dumps`.
4. `tessellation_service.start_tessellation_task(aeroplane_id, wing_name, wing_schema_pickle)`.

Response body:

```json
{ "aeroplane_id": "<uuid>", "href": "/aeroplanes/<uuid>" }
```

🔴 **The `href` does not point at the status resource.** It is
`/aeroplanes/{id}`, while the handler docstring says the result "can be
retrieved via GET /status". A client following `href` literally polls the wrong
URL; the correct poll is route 4 with `task_type=tessellation&wing_name=…`.

🔴 **No concurrency guard.** Unlike route 3, this path never calls
`check_task_available`, so a second POST for the same wing silently overwrites
the registry entry `f"{aeroplane_id}:tessellation:{wing_name}"` and the first
task's result becomes unreachable. The declared `409` is therefore never
returned by this route.

### 2 · Merged scene 🟢

```
GET /aeroplanes/{aeroplane_id}/tessellation  →  200 | 404
```

Reads every cached row for the aeroplane, merges them (`_merge_tessellation_entries`,
`cad.py:101-135`), and answers 404 when the cache is empty. Response:

```json
{
  "data": {
    "shapes": {
      "version": 3,
      "name": "<name>",
      "id": "<id>",
      "parts": [ … ],
      "loc": [[0,0,0],[0,0,0,1]],
      "bb": { "min": [0,0,0], "max": [0,0,0] }
    },
    "instances": [ … ]
  },
  "type": "data",
  "config": { "theme": "dark", "control": "orbit" },
  "count": 12,
  "is_stale": false
}
```

Guarantees:

- Each cached `shapes` blob is **deep-copied** before mutation — the cache rows
  are never modified by a read. 🟢
- Colour is assigned by component type: `#FF8400` when
  `component_type == "wing"`, `#888888` otherwise (`cad.py:121`). 🟢
- Every `{ref: N}` is rebased into the merged `instances` array by
  `_offset_refs` (`cad.py:79-88`), so a client may index directly. 🟢
- `is_stale` is true when **any** contributing entry is stale. 🟡 INFERRED — the
  aggregation rule was not read line by line.
- 🟢 **`bb` is removed from the response and `_expand_bounding_box` deleted** (`Q-CG-3`, maintainer-answered). Previously **`bb` is always `{"min":[0,0,0],"max":[0,0,0]}`.** The producer writes
  `BoundingBox.to_dict()` → `{xmin,xmax,ymin,ymax,zmin,zmax}`
  (`ocp_utils.py:1217-1225`), while `_expand_bounding_box` (`cad.py:91-99`)
  returns early unless the dict carries `"min"` **and** `"max"`. A client must
  not use this field for camera fitting.

### 3 · Start a wing export 🟢

```
POST /aeroplanes/{aeroplane_id}/wings/{wing_name}/{creator_url_type}/{exporter_url_type}
  →  202
```

| Parameter | In | Type | Default | Note |
|---|---|---|---|---|
| `creator_url_type` | path | `CreatorUrlType` | `wing_loft` | `wing_loft` \| `vase_mode_wing` |
| `exporter_url_type` | path | `ExporterUrlType` | `stl` | `stl` \| `step` \| `amf` \| `iges` \| `3mf` |
| `leading_edge_offset_factor` | query | `float` | `0.1` | vase mode only |
| `trailing_edge_offset_factor` | query | `float` | `0.15` | vase mode only |
| `aeroplane_settings` | body | `AeroplaneSettings \| None` | `None` | "not needed for a simple loft" |

**↺ refined:** the two offset factors are **query** parameters with defaults on
the endpoint, not body fields (`cad.py:266-271`).

Flow: resolve aeroplane (404) → resolve wing (404) →
`check_task_available(aeroplane_id)` → **409 `conflict`** when a task for the
same aeroplane is `PENDING`/`RUNNING` → `register_pending_task` →
`map_exporter_type` (**422** on an unmapped value) → `build_wing_blueprint` →
pickle → `submit(..., wing_scale=1000.0)` → 202.

Response body is the same `CadTaskAcceptedResponse` as route 1, with the same
🔴 `href = "/aeroplanes/{id}"` wart.

**Concurrency scope (BR-CG3/BR-CG6).** The 409 is **per aeroplane only**. Two
exports for *different* aeroplanes run in parallel across the four-worker pool
and share the single `./tmp/exports` directory, which the worker zips wholesale
and then empties — so they corrupt one another. This is a property of the
contract as shipped, not just of the implementation. 🔴

### 4 · Task status 🟢

```
GET /aeroplanes/{aeroplane_id}/status?task_type=&wing_name=  →  200
```

| Parameter | In | Type | Default | Note |
|---|---|---|---|---|
| `task_type` | query | `str \| None` | `None` | `"tessellation"`, or `None` for the CAD export task |
| `wing_name` | query | `str \| None` | `None` | required for `task_type=tessellation` |

Task-key resolution (`cad.py:334-340`) — **↺ refined**, three branches not two:

```
task_type == "tessellation" and wing_name  →  f"{aeroplane_id}:tessellation:{wing_name}"
task_type (any other truthy value)         →  f"{aeroplane_id}:{task_type}"
otherwise                                  →  aeroplane_id          # the export task
```

Status → body mapping:

| `status` | `message` | `result` |
|---|---|---|
| `PENDING` | `"Task is pending."` | `null` |
| `RUNNING` (derived from `future.running()`) | `"Task is processing."` | `null` |
| `SUCCESS` | `null` | the worker's `result` dict (e.g. `{"zipfile": …}`) |
| `FAILURE` | the recorded `error` text, else `"An error occurred"` | `null` |

`response_model_exclude_none=True`, so `message` and `result` are **omitted**
rather than sent as `null`. Response:

```json
{ "aeroplane_id": "<uuid>", "href": "/aeroplanes/<uuid>", "status": "SUCCESS",
  "result": { "zipfile": "./tmp/<uuid>.zip" } }
```

Guarantees and caveats:

- For a tessellation `FAILURE`, `message` is exactly
  `"Tessellation failed: <ExceptionClassName>"` — type only, no detail. 🟢
- The `aeroplane_id` is logged with `\n`/`\r` stripped (log-injection guard,
  `cad.py:341`). 🟢
- 🟡 An unknown key yields whatever `get_task_result` returns for a missing
  task; the registry is **in-memory and parent-process only**, so after a
  restart a running build is indistinguishable from one that never existed.

### 5 · Export archive descriptor 🟢

```
GET /aeroplanes/{aeroplane_id}/wings/{wing_name}/{creator_url_type}/{exporter_url_type}/zip
  →  200
```

**↺ refined:** this route returns **JSON, not bytes**. It resolves the recorded
export path, re-homes it under `tmp/` if necessary, and answers a descriptor
pointing at the `/static` mount (`app/main.py:242-245` maps `/static` → `tmp/`):

```
file_path         = cad_service.get_export_file_path(aeroplane_id)
static_file_path  = _ensure_file_under_tmp(file_path, aeroplane_id)   # cad.py:59-76
static_relative   = static_file_path.relative_to((cwd / "tmp").resolve()).as_posix()
base_url          = request.base_url  (rstrip "/")
                    → falls back to settings.base_url when it is the literal "apiserver"
```

```json
{ "url": "<base_url>/static/<relative path>",
  "filename": "<uuid>.zip",
  "mime_type": "application/zip" }
```

`_ensure_file_under_tmp` copies a path that is not already under `CWD/tmp` into
`tmp/{aeroplane_id}/zip/<name>` before deriving the URL. 🟢
🟡 The `"apiserver"` sentinel is a deployment-specific work-around for a
container hostname leaking into `request.base_url`.
🔴 The four path parameters (`wing_name`, `creator_url_type`,
`exporter_url_type`) are **ignored** by the handler — the export path is keyed on
the aeroplane alone (`get_export_file_path(aeroplane_id)`), so a download URL
built with the wrong wing or format still returns the last archive for that
aeroplane.

## Response schemas 🟢

`app/schemas/api_responses.py`:

| Schema | Fields |
|---|---|
| `CadTaskAcceptedResponse` (l.19) | `aeroplane_id: str`, `href: str` |
| `CadTaskStatusResponse` (l.24) | `aeroplane_id: str`, `href: str`, `status: str`, `message: str \| None`, `result: dict \| None` |
| `ZipAssetResponse` (l.32) | `url: str`, `filename: str`, `mime_type: str` |
| `AeroplaneSettings` (l.39) | `printer_settings: Printer3dSettings \| None`, `servo_information: dict[int, ServoSettings] \| None` |

`app/schemas/AeroplaneRequest.py`:

| Enum | Members |
|---|---|
| `CreatorUrlType` (l.44) | `wing_loft` \| `vase_mode_wing` |
| `ExporterUrlType` (l.55) | `stl` \| `step` \| `amf` \| `iges` \| `3mf` |

`status` is a plain `str`, not an enum — the four values `PENDING`, `RUNNING`,
`SUCCESS`, `FAILURE` are a convention only. 🟡

## Stored tessellation envelope (the cache row's `tessellation_json`) 🟢

| Key | Type | Notes |
|---|---|---|
| `data.instances` | `list` | `ocp_tessellate` instance array; `{ref: N}` in `shapes` indexes into it |
| `data.shapes` | `dict` | nested `parts` tree carrying `color`, `loc`, `bb` |
| `data.shapes.bb` | `dict` | `BoundingBox.to_dict()` → `xmin/xmax/ymin/ymax/zmin/zmax` — **not** `min`/`max` |
| `type` | `"data"` | literal |
| `config` | `dict` | `{"theme": "dark", "control": "orbit"}` |
| `count` | `int` | `part_group.count_shapes()` |

Produced with `deviation = 0.1`, `angular_tolerance = 0.2`, colour `#FF8400`,
alpha `1.0`, and passed through `_numpy_to_list` so no NumPy type reaches the
JSON column. 🟢

## Known contract defects 🔴

| # | Defect | Effect on the contract |
|---|---|---|
| D-1 | `map_exporter_type` returns `"ExportTo3MFCreator"`; the class is `ExportTo3mfCreator` (`ExportTo3mfCreator.py:10`) | Every `3mf` export is accepted with 202 and then fails asynchronously with `status = FAILURE`. The advertised format never works. The unit test at `app/tests/test_cad_service_extended.py:130` asserts the wrong spelling and pins the defect |
| D-2 | `ExporterUrlType.AMF = "amf"` has no mapping entry | An enum value published in the OpenAPI schema always answers **422** |
| D-3 | Producer/consumer disagree on the bounding-box key set | Route 2 always answers `bb = {"min":[0,0,0],"max":[0,0,0]}` |
| D-4 | `href` on routes 1 and 3 is `/aeroplanes/{id}` | Following it does not reach the status resource the docstring promises |
| D-5 | Route 5 ignores its wing/creator/exporter path segments | A URL naming a different wing or format returns the same archive |
| D-6 | Route 1 declares 409 but never raises it | A second concurrent tessellation silently discards the first task |
| D-7 | The bare-`Exception` fallback returns `{"detail": …}` with interpolated exception text | Two different 500 body shapes, and a wider information surface on the unmapped path |
| D-8 | Nothing in either envelope declares millimetres | A consumer must know the unit out of band |

A re-implementation must fix D-1…D-8 rather than reproduce them; see
[`tasks.md`](tasks.md) tasks **T-06**, **T-08**, **T-09**, **T-24**.

## Not part of this contract

- Construction-plan CRUD, execution, the SSE stream and the **artefact REST
  routes** (`/construction-plans/{plan_id}/artifacts/…`) →
  [`construction-plans`](../construction-plans/contracts.md). This module owns
  the artefact *storage semantics* those routes call into — see
  [`artifact-serving/`](artifact-serving/requirements.md).
- The Creator contract, the `$TYPE` serialisation dialect and the exporter
  classes themselves → [`cad-designer-topology`](../cad-designer-topology/requirements.md).
- Wing, station and spar persistence, and the metre/millimetre boundary on the
  wing side → [`wing-design`](../wing-design/contracts.md).
- Fuselage geometry and the slicer → `fuselage-design`.
- The client-side viewer (`three-cad-viewer` bootstrapping, `resolveRefs`,
  camera handling) → `frontend-workbench`.
- MCP tool wrappers that re-enter these handlers in-process → `mcp-server`.
