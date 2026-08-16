# cad-generation — Technical Design

> Module-level design. Focuses on HOW the module is built, derived from the
> legacy code. Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Endpoint contracts in full: see [`contracts.md`](contracts.md).
> Behavioural slices: [`wing-tessellation/`](wing-tessellation/),
> [`wing-export-task/`](wing-export-task/),
> [`artifact-serving/`](artifact-serving/).

## Interface

### Process pool and export — `app/services/cad_service.py` (581 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `_get_executor` | `()` | `ProcessPoolExecutor` | lazy singleton, `max_workers=4`, `mp_context=get_context("spawn")` (l.72-78) |
| `shutdown_executor` | `()` | `None` | called from the FastAPI lifespan (`app/main.py:193`) and the test fixture (l.81-95) |
| `tasks` / `tasks_lock` | `Dict[str, Dict[str, Any]]` / `Lock` | — | parent-process, in-memory registry (l.62-63) |
| `check_task_available` | `(aeroplane_id)` | `None` | raises `ConflictError` when a task for the **same** aeroplane runs (l.159-176) |
| `register_pending_task` | `(key)` | `None` | writes `{"status": "PENDING"}` |
| `map_exporter_type` | `(exporter_url_type)` | `str` | Creator **class name**; 🔴 `3mf` typo, `amf` missing (l.185-203) |
| `build_wing_blueprint` | `(wing_name, creator_type, exporter_class, settings)` | `str` (JSON) | the three-node `$TYPE` tree (l.206-262) |
| `_convert_wing_to_pickle` | `(wing_model)` | `bytes` | `wing_model_to_asb_wing_schema` → `pickle.dumps` |
| `_extract_aeroplane_settings` | `(settings)` | `dict` | servo dicts + a pickled `Printer3dSettings` |
| `_run_construction_worker` | `(blueprint, wing_pickle, settings, wing_scale)` | `dict` | **top-level** so the pool can pickle it; rebuilds config + servos, decodes, builds, zips (l.303-377) |
| `start_wing_export_task` | `(db, aeroplane_id, wing_name, creator, exporter, settings)` | `dict` | submits to the pool; `wing_scale = 1000.0`, `fuselages=None` (l.517-518) |
| `get_task_result` | `(key)` | `dict` | derives `RUNNING` from `future.running()` |
| `get_export_file_path` | `(aeroplane_id)` | `str` | the recorded `./tmp/{aeroplane_id}.zip` |

### Tessellation — `app/services/tessellation_service.py` (385 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `_numpy_to_list` | `(obj)` | JSON-safe object | recursive NumPy flattener (l.36-50) |
| `_run_tessellation_worker` | `(wing_pickle, wing_name, wing_scale)` | `dict` | the worker body (l.53-165); type-only failure text (l.162-165) |
| `start_tessellation_task` | `(db, aeroplane_id, wing_name)` | `dict` | key `f"{uuid}:tessellation:{wing_name}"` (l.180); **no** `check_task_available` 🟡 |
| `trigger_background_tessellation` | `(aeroplane_id, wing_name, …)` | `None` | 2.0 s debounce + timer/future cancellation (l.240-300); 🔴 no caller |
| `_start_tessellation_and_cache` | `(…)` | `None` | submits, then `is_hash_current` gate before caching (l.366-368) |

### Cache — `app/services/tessellation_cache 🟢 (deleted, `Q-CG-4`)_service.py` (134 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `compute_geometry_hash` | `(data)` | `str` | `sha256(json.dumps(data, sort_keys=True, default=str))[:16]` (l.22-29) |
| `cache_tessellation` | `(db, aeroplane_id, component_type, component_name, tessellation_json, geometry_hash)` | row | upsert via `get_cached(...).first()` |
| `get_cached` | `(db, aeroplane_id, component_type, component_name)` | `Query` | the logical key — 🔴 not unique in the DDL |
| `get_all_cached` | `(db, aeroplane_id)` | `list[row]` | feeds scene assembly |
| `invalidate` | `(db, aeroplane_id, component_type, component_name)` | `int` | bulk `UPDATE … SET is_stale = True`, returns row count |
| `is_hash_current` | `(db, …, geometry_hash)` | `bool` | the stale-result guard |

### Invalidation hook — `app/services/tessellation_hooks.py` (56 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `on_wing_changed` | `(db, aeroplane_uuid, wing_name)` | `None` | resolves the aeroplane, invalidates `("wing", name)`, sanitises the name before logging (l.44); ends in the **GH #202** TODO (l.52-56) 🟡 |

### Artefacts — `app/services/artifact_service.py` (294 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `_ensure_within_base` | `(path)` | `Path` | `resolve()` + `relative_to(base)`; `ValidationError` on escape (l.25-36) |
| `create_execution_dir` | `(aeroplane_id, plan_id)` | `(Path, str)` | `<base>/<aeroplane_id>/<plan_id>/<execution_id>/` |
| `create_template_execution_dir` | `(template_id)` | `(Path, str)` | **`rmtree`s the previous run** (l.81-110) |
| `list_executions` | `(plan_id)` | `list[ArtifactDirectory]` | 🔴 does **not** skip `_template_runs` (l.123-142) |
| `list_files` | `(…, subpath, recursive)` | `list[ArtifactFile]` | |
| `get_file_path` | `(…, filename)` | `Path` | guards + **rejects symlinks** (l.202-203) |
| `zip_execution` | `(…)` | `Path` | `tempfile.mkstemp`, `ZIP_DEFLATED`, relative arcnames; empty → valid empty zip (l.233-265) |
| `delete_file` / `delete_execution` | `(…)` | `None` | `unlink` / `rmtree`, both guarded |
| `_resolve_execution_dir` | `(plan_id, execution_id)` | `Path` | scans per-aeroplane dirs **skipping** `_template_runs` (l.282-283), then falls back to it |

### REST layer — `app/api/v2/endpoints/cad.py` (412 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `_raise_http_from_domain` | `(exc)` | never | 404 / 422 / 409 / 500 (l.41-56) |
| `_ensure_file_under_tmp` | `(path, aeroplane_id)` | `Path` | copies into `tmp/{aeroplane_id}/zip/<name>` when outside `CWD/tmp` (l.59-76) |
| `_offset_refs` | `(shapes, offset)` | `None` | rebases every `{ref: N}` (l.79-88) |
| `_expand_bounding_box` | `(bb_min, bb_max, shapes)` | `None` | 🔴 early-returns unless the dict has `"min"` **and** `"max"` (l.91-99) |
| `_merge_tessellation_entries` | `(entries)` | `dict` | deep-copy, recolour, rebase, accumulate (l.101-135) |

### Data model 🟢

One table, `tessellation_cache 🟢 (deleted, `Q-CG-4`)` (`app/models/tessellation_cache 🟢 (deleted, `Q-CG-4`).py:8`):

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `id` | Integer PK | yes | autoincrement | indexed (`ix_tessellation_cache 🟢 (deleted, `Q-CG-4`)_id`) |
| `aeroplane_id` | Integer FK → `aeroplanes.id` `ON DELETE CASCADE` | yes | — | indexed; the **integer PK**, not the UUID |
| `component_type` | String | yes | — | `"wing"` \| `"fuselage"` — free text, no enum; only `"wing"` is ever written |
| `component_name` | String | yes | — | wing/fuselage name |
| `geometry_hash` | String | yes | — | `sha256(...)[:16]`, or the literal `"manual"` |
| `tessellation_json` | JSON | yes | — | the viewer envelope |
| `is_stale` | Boolean | yes | `False` | set by `tessellation_hooks.on_wing_changed` |
| `created_at` / `updated_at` | DateTime(tz) | yes | `now()` / `onupdate` | |

Migration: `alembic/versions/04b8c856eab9_add_tessellation_cache 🟢 (deleted, `Q-CG-4`)_table.py` —
creates the FK and two indexes only. 🔴 No unique constraint backs the logical
key `(aeroplane_id, component_type, component_name)`.

Everything else in this module is **filesystem** state, not database state.

## Main Flow

### F1 — Why a process, not a thread (ADR 0005) 🟢

```
ThreadPoolExecutor(max_workers=4)          →  ProcessPoolExecutor(max_workers=4)
mp_context = multiprocessing.get_context("spawn")     # NOT fork

root cause (cad_service.py:7-20):
  OCCT (CadQuery's C++ backend) is not thread-safe.
  BRepCheck messaging, memory pools and interrupt handlers share global state.
  .intersect().clean()  ≈100 ms on the main thread
                        never returns in a worker thread
spawn, because fork would fork an interpreter with OCCT already loaded.
```

The executor is created lazily on first use and shut down explicitly, so a
process that never runs CAD never pays for the pool.

### F2 — The picklability boundary 🟢

```
parent process                          worker process (spawn)
--------------                          ----------------------
WingModel
  └ wing_model_to_asb_wing_schema
      └ pickle.dumps(AsbWingSchema)  ──▶ pickle.loads
                                         asb_wing_schema_to_wing_config(
                                             schema, scale = 1000.0)   # m → mm
AeroplaneSettings
  └ servo dicts + pickled Printer3dSettings ──▶ ServoInformation rebuilt locally
                                                (cad_service.py:319-342)
```

`WingConfiguration` holds `cq.Vector` / OCCT `gp_Vec` instances and is **not
picklable**; the schema is the wire format between the two processes
(`cad_service.py:303-307`, `tessellation_service.py:81-82`). The worker entry
point is a module-level function so `submit` can pickle it.

### F3 — Wing export (`POST /aeroplanes/{id}/wings/{name}/{creator}/{exporter}`) 🟢

1. `get_aeroplane_with_wings` — `joinedload` of `xsecs → detail → spares` and
   `TED → servo`; unknown aeroplane → 404.
2. `get_wing_from_aeroplane` — unknown wing → 404.
3. `check_task_available(aeroplane_id)` — a running task for the **same**
   aeroplane → `ConflictError` → 409 (`cad_service.py:159-176`).
4. `register_pending_task` → `status = PENDING`.
5. `map_exporter_type(exporter_url_type)` → the Creator **class name**;
   an unmapped value (`amf`) → `ValidationError` → 422.
6. `build_wing_blueprint` (see F4).
7. `_convert_wing_to_pickle` and `_extract_aeroplane_settings`.
8. `_get_executor().submit(_run_construction_worker, …, wing_scale = 1000.0)`
   (`cad_service.py:517`); `fuselages=None` — "not yet routed through the REST
   path" (l.518).
9. Respond **202** with `CadTaskAcceptedResponse`.
10. Worker: unpickle → rebuild the configuration → `json.loads(blueprint,
    cls=GeneralJSONDecoder, wing_config=…, fuselage_config=…,
    servo_information=…, printer_settings=…)` → `blue_print.create_shape()`.
11. Worker: zip `./tmp/exports/*` into `./tmp/{aeroplane_id}.zip`, then
    `os.unlink` every file in `./tmp/exports` (`cad_service.py:368-377`).
12. `future.add_done_callback` writes `{status: SUCCESS, result: {zipfile}}` (or
    `FAILURE` + error/traceback) into `tasks`.

### F4 — The export blueprint 🟢

```
ConstructionRootNode  creator_id "eHawk-wing.root.root", loglevel 50
├── ConstructionStepNode  creator_id = <wing_name>, loglevel 50
│     creator: WingLoftCreator | VaseModeWingCreator
│             offset 0
│             wing_index <wing_name>
│             wing_side  "BOTH"
│             loglevel   10
│             (vase mode only: leading_edge_offset_factor,
│                              trailing_edge_offset_factor)
└── ConstructionStepNode  creator_id "output-wing", loglevel 50
      creator: <exporter class>
              file_path         "./tmp/exports"
              tolerance         0.1
              angular_tolerance 0.1
              loglevel          20

defaults: leading_edge_offset_factor  = 0.1   (cad.py:266-271)
          trailing_edge_offset_factor = 0.15
          wing_scale                  = 1000.0 (cad_service.py:517)
```

The literal root id `"eHawk-wing.root.root"` is inherited from the legacy
hand-authored plan and is not derived from the aeroplane — 🟡 it is a constant,
not an identifier.

### F5 — Exporter mapping 🟢 (both defects decided, `Q-CG-1`)

```
map_exporter_type (cad_service.py:185-203)
  stl  → "ExportToStlCreator"    ✔
  step → "ExportToStepCreator"   ✔
  iges → "ExportToIgesCreator"   ✔
  3mf  → "ExportTo3MFCreator"    ✘  real class: ExportTo3mfCreator
  amf  → (absent)                ✘  ExporterUrlType.AMF exists in the enum
```

The decoder resolves `$TYPE` with `getattr(module, name)`, so `3mf` raises
`AttributeError` **inside the worker** and the task ends `FAILURE`; `amf` fails
earlier with `ValidationError` → 422. `app/tests/test_cad_service_extended.py:130`
asserts the wrong spelling and therefore pins the defect;
`construction_plan_service.py:563` uses the correct one.

### F6 — The `./tmp/exports` race 🟢 (per-execution directory, `Q-CG-2`)

```
worker A (aeroplane 1) ─┐
                        ├─▶  ./tmp/exports   (single shared directory)
worker B (aeroplane 2) ─┘

A: zip EVERYTHING in ./tmp/exports  →  ./tmp/1.zip
A: unlink EVERYTHING in ./tmp/exports
   ⇒ B's partial output is captured into A's archive and/or deleted mid-write
```

`check_task_available` serialises **per aeroplane** only, while the pool runs
four workers — there is no cross-aeroplane mutual exclusion by construction.
`zipf.write(file.path)` also stores the `tmp/exports/` prefix inside the archive
rather than a flat arcname.

### F7 — Tessellation worker 🟢

```
wing_schema  = pickle.loads(...)
wing_config  = asb_wing_schema_to_wing_config(wing_schema, scale=1000.0)
creator      = WingLoftCreator(creator_id="tessellation",
                               wing_index=wing_name,
                               wing_side="BOTH",
                               wing_config={wing_name: wing_config})
shapes       = creator._create_shape(shapes_of_interest={}, input_shapes={})
part_group, instances = to_ocpgroup(shape, names=[wing_name],
                                    colors=["#FF8400"], alphas=[1.0])
params       = {"deviation": 0.1, "angular_tolerance": 0.2}
instances, shapes, _ = tessellate_group(part_group, instances, params,
                                        progress=None)
shapes["bb"] = combined_bb(shapes).to_dict()
result       = {"data": {"instances": …, "shapes": …},
                "type": "data",
                "config": {"theme": "dark", "control": "orbit"},
                "count": part_group.count_shapes()}
```

Two things worth flagging:

- The worker calls the **private** `_create_shape` hook directly rather than the
  public `create_shape` template method, bypassing `return_needed_shapes` and
  the log-level dance. Harmless here (no upstream shapes) but it means
  `WingLoftCreator` is used **off-contract**. 🟡 See
  [`cad-designer-topology`](../cad-designer-topology/requirements.md) for the
  contract being bypassed.
- Failures are reported as
  `{"status": "FAILURE", "error": f"Tessellation failed: {type(err).__name__}"}`
  (l.162-165) — deliberately **type-only**, no detail leakage.

All NumPy values pass through `_numpy_to_list` (l.36-50) before serialisation,
because `tessellate_group` returns arrays that the JSON column cannot store.

### F8 — Cache, debounce and staleness 🟢

```
geometry_hash = sha256(json.dumps(data, sort_keys=True, default=str))[:16]
                                                 # 64 bits of a canonical digest
                "manual"  when the POST endpoint triggers without a hash

cache_tessellation : upsert on (aeroplane_id, component_type, component_name)
                     via get_cached(...).first()
invalidate         : bulk UPDATE … SET is_stale = True on the same triple,
                     returns the affected row count
is_hash_current    : the post-run gate — a changed hash DISCARDS the result

trigger_background_tessellation (l.240-300):
  key = f"{aeroplane_id}:{wing_name}"
  cancel pending threading.Timer[key]
  cancel in-flight Future[key]
  Timer(_DEBOUNCE_SECONDS = 2.0, daemon=True) → _start_tessellation_and_cache
```

🔴 Nothing calls `trigger_background_tessellation`.
`tessellation_hooks.on_wing_changed` invalidates and then stops at a TODO
referencing **GH #202** (l.52-56), so a stale entry stays stale until a client
POSTs the tessellation endpoint again. The full lifecycle is in
`state-machines.md` §10.

### F9 — Scene assembly (`GET /aeroplanes/{id}/tessellation`) 🟢

1. `get_all_cached(aeroplane.id)`; empty → **404**.
2. Per entry: `deepcopy(shapes)`, recolour — `#FF8400` when
   `component_type == "wing"`, else `#888888`.
3. `_offset_refs(shapes, len(combined_instances))` rebases every `{ref: N}` into
   the merged instance array (l.79-88).
4. `_expand_bounding_box(...)` — 🟢 deleted (`Q-CG-3`).
5. Emit

```
{"data": {"shapes": {"version": 3, "name": …, "id": …, "parts": [...],
                     "loc": [[0,0,0],[0,0,0,1]], "bb": {"min": …, "max": …}},
          "instances": [...]},
 "type": "data", "config": {...}, "count": <n>, "is_stale": <bool>}
```

### F10 — Why the merged bounding box was always `[0,0,0]`–`[0,0,0]` 🟢 (removed, `Q-CG-3`)

```
producer (tessellation_service.py):
    shapes["bb"] = combined_bb(shapes).to_dict()
    → ocp_tessellate.ocp_utils.BoundingBox.to_dict()
      returns {"xmin","xmax","ymin","ymax","zmin","zmax"}
      (verified in the installed package, ocp_utils.py:1217-1225)

consumer (cad.py:91-99):
    _expand_bounding_box returns early unless the dict has "min" AND "max"
    → the expansion loop never runs
    → the response falls back to {"min":[0,0,0],"max":[0,0,0]}  (l.130-133)
```

🟢 CONFIRMED by inspection of both sides. A re-implementation must make producer
and consumer agree on **one** key set; the fix is a one-line change on either
side, and the choice is a contract decision because the frontend reads the
merged envelope.

### F11 — Artefact filesystem 🟢

```
<ARTIFACTS_BASE_DIR>/
├── <aeroplane_id>/<plan_id>/<execution_id>/          plan runs   (accumulate)
├── _template_runs/<template_id>/<execution_id>/      template runs (rmtree'd)
└── openvsp_imports/<aeroplane_uuid>/                 owned by openvsp-import

execution_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
               + "-N" on a same-second collision, tracked in the module globals
                 _last_execution_id / _last_execution_id_suffix (l.39-58)

guards: _ensure_within_base = resolve() then relative_to(base)
                              → ValidationError on escape        (l.25-36)
        get_file_path       additionally rejects symlinks        (l.202-203)

zip_execution: tempfile.mkstemp + ZIP_DEFLATED,
               arcnames relative to the execution dir,
               an empty execution yields a VALID EMPTY ZIP, not a 404 (l.233-265)
```

`TEMPLATE_RUNS_PREFIX = "_template_runs"` (l.78).
`create_template_execution_dir` **wipes** the previous template run with
`shutil.rmtree`, so at most one execution per template survives (l.81-110).

🔴 Asymmetry: `_resolve_execution_dir` deliberately **skips** `_template_runs`
when scanning per-aeroplane directories (l.282-283), while `list_executions`
does not (l.123-142) — a template run can surface in a plan listing with
`aeroplane_id == "_template_runs"`.

Not under `ARTIFACTS_BASE_DIR`, deliberately or otherwise: `./tmp/exports` and
`./tmp/{aeroplane}.zip` (this module), `tmp/construction_parts/{aeroplane}/`
(→ `construction-plans`).

## Alternative Flows

- **Geometry kernel absent (`linux/aarch64`):** the CAD router is
  **conditionally mounted** — `app/main.py:222-223` includes it only when the
  import succeeded — so the routes do not exist rather than failing at call
  time (ADR 0017). 🟢
- **Concurrent export, same aeroplane:** `ConflictError` → 409 before any work
  is scheduled. 🟢
- **Concurrent export, different aeroplanes:** allowed, and it corrupts both
  archives via the shared `./tmp/exports` directory (F6). 🔴
- **Second tessellation POST for the same wing:** accepted; the registry entry
  is silently overwritten because `check_task_available` is not called on that
  path. 🔴
- **Worker raises:** the done-callback records `FAILURE`. For tessellation the
  message is the exception **type name** only; for exports the error and
  traceback are recorded in the registry. 🟢
- **Geometry changed while tessellating:** the finished result is discarded by
  the `is_hash_current` gate — no cache write, no error. 🟢
- **Server restarts mid-task:** the in-memory registry is lost;
  `GET /status` answers 404 while the worker may still be running. 🟡
- **Nothing cached for an aeroplane:** `GET /aeroplanes/{id}/tessellation` → 404
  rather than an empty scene. 🟢
- **Export archive stored outside `CWD/tmp`:** copied into
  `tmp/{aeroplane_id}/zip/<name>` before it is served. 🟢
- **Artefact path escapes the base or is a symlink:** `ValidationError` → 422. 🟢
- **Empty execution directory:** zipping returns a valid empty archive. 🟢

## Dependencies

- **`wing-design`** — the persisted `WingModel` and its stations/spars/TEDs are
  the export and tessellation input; `wing_model_to_asb_wing_schema` is the
  conversion used to make it picklable.
- **`aeroplane-core`** — every route resolves the aeroplane by UUID first; the
  cache row keys on the **integer** `aeroplanes.id`.
- **`cad-designer-topology`** — `WingLoftCreator`, `VaseModeWingCreator`, the
  four export Creators, `GeneralJSONDecoder`, `ServoInformation` and
  `Printer3dSettings`. The blueprint is written in that module's `$TYPE`
  dialect; renaming a Creator breaks this module's mapping (BR-71 there).
- **`construction-plans`** — consumes `artifact_service` for its execution
  directories and owns the artefact **REST routes**; it also executes the same
  Creator stack, but **in-process** (a documented architectural contradiction,
  see its spec).
- **`app/converters/model_schema_converters.py`** — the shared conversion hub.
- **`ocp_tessellate`** (`to_ocpgroup`, `tessellate_group`, `combined_bb`) — the
  tessellation backend; its `BoundingBox.to_dict()` key set is the root of F10.
- **CadQuery / OCCT** — optional heavy dependency, probed at import (ADR 0017).
- **`frontend-workbench`** — the downstream consumer of both envelopes
  (`CadViewer.tsx`: `structuredClone` → `resolveRefs` inlines
  `instances[shape.ref]` → `tcv.Display` → `tcv.Viewer` with `up: "Z"`,
  `theme: "dark"` → `viewer.addPart(rootId, shapes, {skipBounds: true})`). That
  rendering contract is specified in `frontend-workbench`, not here.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| CAD runs in a spawned process pool because OCCT is not thread-safe | ADR 0005; `cad_service.py:7-20, 66-78` | 🟢 |
| The wire format across the process boundary is a pickled `AsbWingSchema`, not the live configuration | `cad_service.py:303-307`; `tessellation_service.py:81-82` | 🟢 |
| Live geometry objects (`WingConfiguration`, `ServoInformation`) are rebuilt worker-side | `cad_service.py:319-342` | 🟢 |
| Task state is in-memory and parent-process only — no persistence, no cross-replica sharing | `cad_service.py:62-63`; `state-machines.md` §11 | 🟢 |
| `RUNNING` is derived from the future rather than written by the worker | `get_task_result` | 🟢 |
| 🟢 Export concurrency is capped **globally** (`R2-09`); exports and plan runs share the pool (`Q-CP-1`) | `cad_service.py:159-176` | 🟢 (the resulting race 🔴) |
| The export blueprint is synthesised in the same `$TYPE` dialect as stored construction plans | `cad_service.py:206-262` | 🟢 |
| Tessellation quality is a fixed constant pair, not a request parameter | `tessellation_service.py:113` | 🟢 |
| Worker error text is the exception type only | `tessellation_service.py:162-165` | 🟢 |
| The tessellation result is cached in the database rather than on disk | `app/models/tessellation_cache 🟢 (deleted, `Q-CG-4`).py`; `tessellation_cache 🟢 (deleted, `Q-CG-4`)_service.py` | 🟢 |
| A superseded tessellation is discarded rather than cached | `tessellation_service.py:366-368` | 🟢 |
| Cache invalidation marks stale; it never re-produces | `tessellation_hooks.py:52-56` (GH #202 TODO) | 🟢 |
| Artefact paths are resolved and constrained, symlinks rejected | `artifact_service.py:25-36, 202-203` (BR-68) | 🟢 |
| A template keeps only its latest execution | `artifact_service.py:81-110` | 🟢 |
| The CAD router is conditionally mounted rather than degrading per route | `app/main.py:222-223` (ADR 0017) | 🟢 |
| `3mf` maps to a class name that does not exist | `cad_service.py:185-203` vs `ExportTo3mfCreator.py:10` | 🟢 (intent 🔴) |
| The producer and consumer of the tessellation bounding box disagree on key names | `tessellation_service.py` vs `cad.py:91-99` | 🟢 (intent 🔴) |

## Internal State

Two kinds of state, neither of them request-scoped:

- **In-memory, parent process** — `cad_service.tasks` (+ `tasks_lock`), the
  debounce timer map and the in-flight future map in `tessellation_service`.
  Lost on restart, not shared across replicas, no retry and no dead-letter path.
  Lifecycle in `state-machines.md` §11.
- **Persistent, database** — `tessellation_cache 🟢 (deleted, `Q-CG-4`)` rows: the viewer envelope,
  its `geometry_hash` and the `is_stale` flag. Lifecycle in
  `state-machines.md` §10.
- **Persistent, filesystem** — `<ARTIFACTS_BASE_DIR>/…` execution directories,
  `./tmp/exports` (transient, shared) and `./tmp/{aeroplane_id}.zip`. The module
  globals `_last_execution_id` / `_last_execution_id_suffix` are the only
  in-memory part of the artefact layer.

Derived at read, never persisted: the merged scene, the derived `RUNNING`
status, and the zip archive produced by `zip_execution` (a temp file).

## Observability

- Task status is queryable by URL for the life of the process
  (`GET /aeroplanes/{id}/status`). 🟢
- 5xx are logged with `logger.exception` by the shared endpoint error mapping;
  domain errors are mapped without a stack trace (`cad.py:41-56`). 🟢
- `tessellation_hooks.on_wing_changed` logs the invalidation with a **sanitised**
  wing name (log-injection guard, l.44). 🟢
- Worker failures cross the boundary as data (`status`, `error`, and for exports
  a `traceback`), not as exceptions. 🟢
- 🔴 There are **no metrics** — no build duration, no queue depth, no cache
  hit/miss counter — and no trace context propagated into the worker process.
  A build that is slow or a cache that never hits is invisible.
- 🟡 The degraded no-CadQuery state is expressed only by the **absence** of the
  routes; nothing reports it as a capability flag.

## Risks and Gaps

- 🟢 **3MF is fixed properly and AMF is removed** (`Q-CG-1`, maintainer-answered). Previously **3MF export can never succeed.** `map_exporter_type` returns
  `"ExportTo3MFCreator"`; the class is `ExportTo3mfCreator`. The unit test
  asserts the wrong spelling, so the defect is pinned by the suite. A
  re-implementation must fix the mapping **and** the test.
- 🔴 **`amf` is advertised but unmapped**, so an enum value documented in the
  OpenAPI schema always answers 422.
- 🔴 **`./tmp/exports` is shared across concurrent exports of different
  aeroplanes**, and the worker deletes every file in it. Two simultaneous
  exports corrupt each other by construction.
- 🔴 **The merged scene bounding box is always degenerate** because producer and
  consumer disagree on the key set. Camera-fit for multi-part scenes is
  therefore wrong or silently delegated to per-part bounds.
- 🔴 **No unique constraint** backs the tessellation cache's logical key, while
  the service treats it as unique via `.first()`.
- 🔴 **Background re-tessellation is fully implemented dead code** (2 s debounce,
  timer + future cancellation, stale-hash discard) with no caller; the hook ends
  in a TODO referencing GH #202. A stale entry never refreshes itself.
- 🔴 **Fuselages are never tessellated.** `component_type = "fuselage"` is
  modelled and coloured, but there is no producer, and `start_wing_export_task`
  passes `fuselages=None`.
- 🔴 **`check_task_available` is not called on the tessellation path**, so a
  second POST for the same wing silently overwrites the registry entry.
- 🔴 **`list_executions` scans `_template_runs` as if it were an aeroplane
  directory**, unlike `_resolve_execution_dir`, so a template run can appear in
  a plan listing.
- 🟡 **The task registry does not survive a restart**, so a long build becomes
  unqueryable while its worker keeps running — and there is no way to reattach.
- 🟡 **The `execution_id` collision counter is per-process**, so two processes in
  the same second still collide.
- 🟡 **`WingLoftCreator` is used off-contract** by the tessellation worker, which
  calls the private `_create_shape` directly. If the Creator contract ever grows
  behaviour in `create_shape`, this path silently skips it.
- 🟡 **The blueprint root id is the literal `"eHawk-wing.root.root"`**, inherited
  from a legacy hand-authored plan and unrelated to the aeroplane being exported.
