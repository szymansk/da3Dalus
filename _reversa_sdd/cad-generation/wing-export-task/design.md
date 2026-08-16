# wing-export-task — Technical Design

> Use-case design, nested under the module [`cad-generation`](../design.md).
> Focuses on HOW this use case is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Endpoint contracts in full: [`../contracts.md`](../contracts.md) routes 3–5.
> Sibling slices: [`../wing-tessellation/`](../wing-tessellation/design.md),
> [`../artifact-serving/`](../artifact-serving/design.md).

## Interface

### Endpoint layer — `app/api/v2/endpoints/cad.py` 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `create_wing_loft` | `(aeroplane_id, wing_name, db, leading_edge_offset_factor=0.1, trailing_edge_offset_factor=0.15, aeroplane_settings=None, creator_url_type=WING_LOFT, exporter_url_type=STL)` | `CadTaskAcceptedResponse` | 202; the two factors are **query** parameters (l.262-271) |
| `get_aeroplane_task_status` | `(aeroplane_id: str, task_type=None, wing_name=None)` | `CadTaskStatusResponse` | `response_model_exclude_none=True` (l.322) |
| `download_aeroplane_zip` | `(aeroplane_id, wing_name, creator_url_type, exporter_url_type, settings, request)` | `ZipAssetResponse` | returns a **descriptor**, not bytes (l.379) |
| `_ensure_file_under_tmp` | `(file_path: str, aeroplane_id: str)` | `FilePath` | copies into `tmp/{id}/zip/<name>` when outside `CWD/tmp` (l.59-76) |

### Service layer — `app/services/cad_service.py` (581 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `tasks` / `tasks_lock` | `Dict[str, Dict[str, Any]]` / `Lock` | — | parent-process registry; export key is the bare UUID (l.62-63) |
| `check_task_available` | `(aeroplane_id)` | `None` | `ConflictError` → 409 when a task for the same aeroplane runs (l.159-176) |
| `register_pending_task` | `(key)` | `None` | `{"status": "PENDING"}` |
| `map_exporter_type` | `(exporter_url_type)` | `str` | Creator **class name**; 🔴 `3mf` typo, `amf` absent (l.185-203) |
| `build_wing_blueprint` | `(wing_name, creator_type, exporter_class, …)` | `str` (JSON) | the three-node `$TYPE` tree (l.206-262) |
| `_convert_wing_to_pickle` | `(wing_model)` | `bytes` | `wing_model_to_asb_wing_schema` → `pickle.dumps` |
| `_extract_aeroplane_settings` | `(aeroplane_settings)` | `dict` | servo dicts + pickled `Printer3dSettings` |
| `_run_construction_worker` | `(blueprint, wing_pickle, settings, wing_scale)` | `dict` | **top-level**, runs in the spawned process (l.303-377) |
| `start_wing_export_task` | `(aeroplane_id, wing, wing_name, creator_url_type, exporter_url_type, leading/trailing_edge_offset_factor, aeroplane_settings)` | `dict` | `wing_scale = 1000.0` (l.517), `fuselages=None` (l.518) |
| `get_task_result` | `(key)` | `dict` | derives `RUNNING` from `future.running()` |
| `get_export_file_path` | `(aeroplane_id)` | `str` | keyed on the **aeroplane alone** |

### State

No database table. The only state is the in-memory registry entry
(`state-machines.md` §11) plus two filesystem locations: the shared
`./tmp/exports` working directory and the per-aeroplane archive
`./tmp/{aeroplane_id}.zip`.

| Key | Value shape | Notes |
|---|---|---|
| `<aeroplane_uuid>` | `{status, future?, result?, error?, traceback?}` | export tasks |

`status ∈ {PENDING, RUNNING, SUCCESS, FAILURE}`; `RUNNING` is **derived on
read**, never stored by the worker.

## Main Flow

### F1 — Request path (`POST .../{creator_url_type}/{exporter_url_type}`) 🟢

1. `get_aeroplane_with_wings(db, aeroplane_id)` — `joinedload` of
   `xsecs → detail → spares` and `TED → servo`; unknown aeroplane → 404.
2. `get_wing_from_aeroplane(aeroplane, wing_name)` → 404 on an unknown wing.
3. `start_wing_export_task(...)`, which internally:
   1. `check_task_available(aeroplane_id)` → `ConflictError` → **409** when a
      task for the same aeroplane is `PENDING`/`RUNNING` (l.159-176);
   2. `register_pending_task(aeroplane_id)`;
   3. `map_exporter_type(exporter_url_type)` → the Creator class **name**; an
      unmapped value raises `ValidationError` → **422**;
   4. `build_wing_blueprint(...)` (F2);
   5. `_convert_wing_to_pickle(wing)` and `_extract_aeroplane_settings(...)`;
   6. `_get_executor().submit(_run_construction_worker, …, wing_scale=1000.0)`
      (l.517) with `fuselages=None` (l.518);
   7. `future.add_done_callback(_on_done)`.
4. Respond **202** with `{aeroplane_id, href}`.

🔴 The `href` is `/aeroplanes/{id}` — not the status resource the docstring
promises. A client must construct the poll URL itself.

### F2 — The blueprint 🟢

```
ConstructionRootNode  creator_id "eHawk-wing.root.root", loglevel 50
├── ConstructionStepNode  creator_id = <wing_name>, loglevel 50
│     creator: WingLoftCreator | VaseModeWingCreator
│             offset      0
│             wing_index  <wing_name>
│             wing_side   "BOTH"
│             loglevel    10
│             (vase mode only:
│                 leading_edge_offset_factor   default 0.1
│                 trailing_edge_offset_factor  default 0.15)
└── ConstructionStepNode  creator_id "output-wing", loglevel 50
      creator: <exporter class>
              file_path         "./tmp/exports"
              tolerance         0.1
              angular_tolerance 0.1
              loglevel          20
```

(`cad_service.py:206-262`; defaults `cad.py:266-271`; `wing_scale = 1000.0`
`cad_service.py:517`.)

The output is a **JSON string** in exactly the `$TYPE` dialect
`GeneralJSONDecoder` resolves — the same format stored in
`construction_plans.tree_json`, which is why a Creator rename breaks both
(see `cad-designer-topology` BR-71). The two log-level values (`10` for the
build step, `20` for the exporter) are the mechanism by which a build logs at
DEBUG while the export logs at INFO, via the root-logger mutation in
`AbstractShapeCreator.create_shape`.

🟡 The root id is the constant `"eHawk-wing.root.root"`, inherited from a legacy
hand-authored plan; it identifies nothing about the aeroplane being exported.

### F3 — Exporter mapping 🟢 (both defects decided, `Q-CG-1`)

```
map_exporter_type (cad_service.py:185-203)
  stl  → "ExportToStlCreator"     ✔
  step → "ExportToStepCreator"    ✔
  iges → "ExportToIgesCreator"    ✔
  3mf  → "ExportTo3MFCreator"     ✘  real class: ExportTo3mfCreator
  amf  → (no entry)               ✘  ExporterUrlType.AMF exists
```

The two failures land at **different times**, which matters for the contract:

| Value | Failure point | Client sees |
|---|---|---|
| `amf` | synchronously, in `map_exporter_type` | **422** at POST |
| `3mf` | asynchronously, in the worker's `getattr` | **202**, then `status = FAILURE` |

`app/tests/test_cad_service_extended.py:130` asserts the wrong spelling, so the
suite is green **because** the defect exists — a re-implementation must fix the
mapping *and* the assertion, ideally deriving it from
`ExportTo3mfCreator.__name__`. `construction_plan_service.py:563` demonstrates
the correct spelling in the sibling module.

### F4 — Worker body 🟢

```
wing_schema  = pickle.loads(wing_pickle)
wing_config  = asb_wing_schema_to_wing_config(wing_schema, scale=1000.0)  # m → mm
servo_info   = rebuild ServoInformation from the plain dicts   (l.319-342)
printer      = pickle.loads(settings["printer_settings"])

blue_print   = json.loads(blueprint, cls=GeneralJSONDecoder,
                          wing_config      = {wing_name: wing_config},
                          fuselage_config  = None,
                          servo_information= servo_info,
                          printer_settings = printer)
blue_print.create_shape()                    # the exporter writes ./tmp/exports/*

with ZipFile(f"./tmp/{aeroplane_id}.zip", "w") as zipf:
    for file in scandir("./tmp/exports"):
        zipf.write(file.path)                # keeps the tmp/exports/ prefix  🔴
for file in scandir("./tmp/exports"):
    os.unlink(file.path)                     # deletes EVERYTHING             🔴

return {"status": "SUCCESS", "result": {"zipfile": f"./tmp/{aeroplane_id}.zip"}}
```

(`cad_service.py:303-377`.) `ServoInformation` is rebuilt inside the worker
because it holds OCC handles; `Printer3dSettings` is a plain pydantic model and
crosses pickled.

### F5 — The `./tmp/exports` race 🟢 (per-execution directory, `Q-CG-2`)

```
                 ┌─ worker A (aeroplane 1) ─┐
./tmp/exports ◄──┤                          ├──► both write here
                 └─ worker B (aeroplane 2) ─┘

A finishes first:
   zip EVERYTHING in ./tmp/exports  → ./tmp/1.zip     ← captures B's partial files
   unlink EVERYTHING in ./tmp/exports                 ← deletes B's work in progress
B finishes:
   zips whatever survived (possibly nothing) → ./tmp/2.zip
```

`check_task_available` serialises **per aeroplane** only (l.159-176) while the
pool has four workers, so nothing prevents this. It is a race **by
construction**, not a timing accident: the directory is a module-level constant
shared by every worker (`cad_service.py:253` in the blueprint, l.369 in the
archive step).

The correct shape is a per-task directory — exactly the pattern
`construction-plans` already uses through `artifact_service`
(see [`../artifact-serving/`](../artifact-serving/design.md)).

### F6 — Completion callback 🟢

```
_on_done(future):
    with tasks_lock:
        if future.exception():
            tasks[key] = {"status": "FAILURE",
                          "error": str(exc),
                          "traceback": format_exc()}
        else:
            tasks[key] = future.result()      # {"status": "SUCCESS", "result": {...}}
```

Unlike the tessellation path, an export **retains its error text and
traceback** in the registry — the type-only rule (BR-CG9) applies to
tessellation only. 🟢 That asymmetry is undocumented in the code. 🟡

### F7 — Status resolution 🟢

```
task_type == "tessellation" and wing_name  →  f"{aeroplane_id}:tessellation:{wing_name}"
task_type (any other truthy value)         →  f"{aeroplane_id}:{task_type}"
otherwise                                  →  aeroplane_id            # the export task
                                              (cad.py:334-340)

status → body:
  PENDING  message "Task is pending."          result omitted
  RUNNING  message "Task is processing."       result omitted
  SUCCESS  message omitted                     result = worker result dict
  FAILURE  message = recorded error, else "An error occurred"
```

`response_model_exclude_none=True` removes the null fields rather than sending
them. The aeroplane id is stripped of `\n`/`\r` before it is logged
(`cad.py:341`). 🟢

`RUNNING` never appears in the registry — `get_task_result` derives it from
`future.running()` at read time, which is why a restart (losing the future)
makes a live build indistinguishable from an unknown one. 🟡

### F8 — Download descriptor 🟢

```
file_path        = get_export_file_path(aeroplane_id)         # ./tmp/{id}.zip
static_file_path = _ensure_file_under_tmp(file_path, aeroplane_id)
                   # copies to tmp/{id}/zip/<name> when outside CWD/tmp  (cad.py:59-76)
tmp_root         = (Path.cwd() / "tmp").resolve()
static_relative  = static_file_path.relative_to(tmp_root).as_posix()

base_url = request.base_url.rstrip("/")
           if base_url == "apiserver": base_url = settings.base_url.rstrip("/")

→ {"url": f"{base_url}/static/{static_relative}",
   "filename": basename(static_file_path),
   "mime_type": "application/zip"}
```

The `/static` mount is `app/main.py:242-245` (`/static` → `tmp/`). The
`relative_to(tmp_root)` call is what makes the URL derivation safe: a path that
escaped `tmp/` would raise rather than produce a URL. 🟢

🟡 The `"apiserver"` sentinel is a deployment work-around for a container
hostname leaking into `request.base_url`.

🔴 The handler takes `wing_name`, `creator_url_type` and `exporter_url_type` as
path parameters and **ignores all three** — the archive is keyed on the
aeroplane alone. A download URL naming a different wing or format returns the
last archive for that aeroplane, silently.

## Alternative Flows

- **Unknown aeroplane or wing:** 404 before any task is registered. 🟢
- **Concurrent export, same aeroplane:** 409, no task registered. 🟢
- **Concurrent export, different aeroplanes:** accepted, and both archives are
  corrupted through the shared working directory (F5). 🔴
- **Unmapped exporter (`amf`):** `ValidationError` → 422 at POST, no work
  scheduled. 🟢
- **Mis-mapped exporter (`3mf`):** 202, then `AttributeError` inside the worker
  → task `FAILURE`. The client cannot tell this from a genuine geometry
  failure. 🔴
- **Worker raises:** `FAILURE` with error text and traceback in the registry;
  the archive is not written. 🟢
- **Exporter wrote nothing:** the archive is created empty and the task still
  reports `SUCCESS`. 🟡 INFERRED — no emptiness check was found.
- **Server restarts mid-build:** the registry and the future are lost; the
  worker process dies with the pool. `GET /status` → 404 (or an unknown-task
  shape) while the archive may or may not exist. 🟡
- **Download before completion:** `get_export_file_path` returns the recorded
  path for the aeroplane; if no archive exists the handler raises and maps to
  404/500. 🟡 The exact behaviour was not read.
- **Archive stored outside `CWD/tmp`:** copied under `tmp/{id}/zip/` first. 🟢
- **CadQuery absent:** the router is not mounted; the routes do not exist
  (ADR 0017). 🟢

## Dependencies

- **`wing-design`** — the persisted `WingModel` with stations, spars, TEDs and
  servos; `wing_model_to_asb_wing_schema` makes it picklable.
- **`aeroplane-core`** — resolves the aeroplane by UUID and eager-loads the wing
  graph.
- **`cad-designer-topology`** — `WingLoftCreator`, `VaseModeWingCreator`, the
  four export Creators, `GeneralJSONDecoder`, `ServoInformation`,
  `Printer3dSettings`. The blueprint is written in that module's `$TYPE`
  dialect; a Creator rename invalidates this module's mapping.
- **The shared process pool** — owned at [module level](../design.md) §F1.
- **`app/main.py`** — the `/static` → `tmp/` mount that makes the download URL
  resolvable, and the conditional router mount.
- **`construction-plans`** — a sibling consumer of the same Creator stack, but
  in-process; it also demonstrates the correct `ExportTo3mfCreator` spelling and
  the per-execution directory pattern this use case lacks.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Exports are asynchronous with a 202 + polling contract, not a long-lived request | `cad.py:262`; `state-machines.md` §11 | 🟢 |
| Task state is in-memory and parent-process only — no job table, no queue | `cad_service.py:62-63` | 🟢 |
| `RUNNING` is derived from the future rather than written by the worker | `get_task_result` | 🟢 |
| 🟢 One **global** cap; the per-aeroplane limit is removed (`R2-09`) — it existed to prevent the shared-directory race that `Q-CG-2` fixes at source | `cad_service.py:159-176` | 🟢 (the resulting race 🔴) |
| The blueprint is synthesised in the same dialect as stored construction plans | `cad_service.py:206-262` | 🟢 |
| Log levels are baked into the blueprint per step (10 build / 20 export / 50 structural) | `cad_service.py:206-262` | 🟢 |
| The exporter mapping is by **class name string**, resolved late by the decoder | `cad_service.py:185-203` | 🟢 — this is why the 3MF typo fails only at runtime |
| Export errors keep their traceback, tessellation errors do not | `_on_done` vs `tessellation_service.py:162-165` | 🟢 (rationale 🔴) |
| The download route returns a `/static` URL descriptor rather than streaming bytes | `cad.py:379` | 🟢 |
| The archive is keyed on the aeroplane alone, so the route's wing/format segments are decorative | `get_export_file_path` | 🟢 (intent 🔴) |
| The working directory is a shared module constant, not per task | `cad_service.py:253, 369` | 🟢 (intent 🔴) |
| Fuselages are explicitly not routed through the export path | `cad_service.py:518` (comment) | 🟢 |

## Internal State

- **In-memory, parent process:** `tasks[<aeroplane_uuid>]` holding
  `{status, future, result | error, traceback}`, guarded by `tasks_lock`. Lost
  on restart; not shared across replicas; no retry and no dead-letter path.
- **Filesystem, shared:** `./tmp/exports` — the exporter's working directory,
  written and then emptied by **every** worker.
- **Filesystem, per aeroplane:** `./tmp/{aeroplane_id}.zip`, and its re-homed
  copy `tmp/{aeroplane_id}/zip/<name>` when the recorded path was outside
  `tmp/`.

Nothing here is under `ARTIFACTS_BASE_DIR`, unlike construction-plan
executions — see [`../artifact-serving/`](../artifact-serving/design.md).

## Observability

- Task status is queryable at `GET /aeroplanes/{id}/status` for the life of the
  process. 🟢
- The aeroplane id is stripped of `\n`/`\r` before logging in both the status and
  the download handler (`cad.py:341` and the download body). 🟢
- A failed export keeps its error **and traceback** in the registry — the richest
  diagnostic in this module. 🟢
- 5xx are logged with `logger.exception` by the shared endpoint mapping. 🟢
- 🔴 No metrics: no build duration, no queue depth, no success/failure counter.
  A 3MF export that always fails is invisible until a user complains.
- 🔴 Nothing records **which** exporter or creator a task used, so a `FAILURE`
  in the registry cannot be attributed to the 3MF defect without reading the
  traceback.

## Risks and Gaps

- 🟢 **3MF is fixed properly and AMF is removed** (`Q-CG-1`, maintainer-answered). Previously **3MF export can never succeed**, and the failure is asynchronous, so it
  looks like a geometry problem. The unit test pins the wrong spelling.
- 🔴 **`amf` is advertised in the enum and always answers 422.**
- 🔴 **Concurrent exports of different aeroplanes corrupt each other** through
  the shared `./tmp/exports`, which is zipped wholesale and then emptied.
- 🔴 **Archive entries keep the `tmp/exports/` prefix**, so extraction produces a
  nested directory rather than the exported files.
- 🔴 **The download route ignores its wing and format segments**, returning the
  last archive for the aeroplane regardless of the URL.
- 🔴 **`href` does not point at the status resource** the docstring promises.
- 🔴 **Export archives live outside `ARTIFACTS_BASE_DIR`**, unlike every other
  artefact in the system — which is precisely what makes the race possible.
- 🟡 **The registry does not survive a restart**, so a long build becomes
  unqueryable while its worker keeps running, with no way to reattach.
- 🟡 **An empty exporter output still reports `SUCCESS`** — no emptiness check
  was found.
- 🟡 **The blueprint root id is a legacy constant** (`"eHawk-wing.root.root"`).
- 🟡 **The error-verbosity asymmetry** between exports (full traceback) and
  tessellation (type name only) is undocumented; one of the two is presumably
  wrong.
- 🟡 **`fuselages=None`** is hard-coded with a "not yet routed" comment, so a
  multi-body aircraft exports only its wing without saying so.
