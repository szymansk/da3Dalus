# cad-generation

> Module-level specification. Focuses on WHAT the module does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: cad-generation,
> `_reversa_sdd/data-dictionary.md` §Module: cad-generation,
> `_reversa_sdd/domain.md` §2.10, `_reversa_sdd/state-machines.md` §10–11,
> ADR 0005, ADR 0017.

## Overview

`cad-generation` is the app-side CAD orchestration layer: it turns a persisted
wing into a CadQuery solid **in a separate worker process**, tessellates that
solid into the JSON envelope the three-cad-viewer consumes, caches the result
per component, assembles a multi-part scene from the cache, and exports
STEP/STL/IGES/3MF archives. It owns no geometry algorithm of its own — every
shape comes from a `cad_designer` Creator — but it owns the **process boundary**,
the **task lifecycle**, the **tessellation cache** and the **artefact
filesystem**. 🟢

## Responsibilities

- Run every CAD build in a spawned worker process with its own OCCT state, and
  tear that pool down cleanly on application shutdown. 🟢
- Convert a persisted `WingModel` into a picklable `AsbWingSchema`, ship it
  across the process boundary, and rebuild the millimetre `WingConfiguration`
  inside the worker. 🟢
- Synthesise the three-node construction blueprint (`$TYPE` dialect) that drives
  a wing loft or vase-mode build plus an exporter step. 🟢
- Track asynchronous CAD tasks in an in-memory registry and answer status
  queries with a derived `RUNNING` state. 🟢
- Tessellate a wing into the viewer envelope
  (`{data:{instances,shapes}, type, config, count}`) with fixed deviation and
  angular tolerance. 🟢
- Cache a tessellation per `(aeroplane, component_type, component_name)` with a
  content hash, and mark entries stale when the wing geometry changes. 🟢
- Merge every cached entry of one aeroplane into a single scene, rebasing
  instance references and recolouring by component type. 🟢
- Own the artefact filesystem: execution directories, path-traversal and symlink
  guards, listing, zipping and deletion. 🟢
- Serve the export archive as a file download, re-homing it under `tmp/` first. 🟢

**Explicitly NOT this module's responsibility:** the geometry algorithms
themselves and the Creator contract (→ `cad-designer-topology`, frozen per
ADR 0002); the construction-plan CRUD, its execution and the SSE stream that
also drives Creators (→ `construction-plans`, which additionally owns the
artefact **REST routes** that call into this module's storage layer); the spar
and section pipeline (→ `wing-design`); the fuselage slicer (→
`fuselage-design`); the wing/station/spar persistence the export path reads
(→ `wing-design`); the component tree (→ `aeroplane-core`); the viewer's
client-side rendering (→ `frontend-workbench`); MCP tool wrappers that re-enter
these handlers in-process (→ `mcp-server`).

## Business Rules

### Execution model

- **BR-67 — CAD runs in a spawned worker process.** 🟢 The pool is
  `ProcessPoolExecutor(max_workers=4, mp_context=multiprocessing.get_context("spawn"))`,
  lazily created by `_get_executor()` (`app/services/cad_service.py:72-78`) and
  torn down by `shutdown_executor()` (l.81-95) from the FastAPI lifespan
  (`app/main.py:193`) and from the test fixture. The module docstring (l.7-20)
  records the root cause verbatim: **OCCT is not thread-safe.** The same
  `.intersect().clean()` call that takes ~100 ms on the main thread hangs
  indefinitely in a worker *thread*, because OCCT holds global state (BRepCheck
  messaging, memory pools, interrupt handlers). `spawn` is chosen for
  platform-consistent behaviour; `fork` is unsafe because it would fork an
  interpreter with OCCT already loaded. ADR 0005.
- **BR-CG1 — Everything crossing the process boundary must be picklable.** 🟢
  `WingConfiguration` holds `cq.Vector` / OCCT `gp_Vec` instances and cannot
  cross. The parent therefore converts `WingModel → AsbWingSchema`, ships the
  schema **pickled**, and the worker rebuilds the live object with
  `asb_wing_schema_to_wing_config(schema, scale=1000.0)`
  (`cad_service.py:303-307`, `tessellation_service.py:81-82`).
  `ServoInformation` is rebuilt inside the worker for the same reason
  (`cad_service.py:319-342`). The worker function is a **top-level** function so
  the pool's `submit` API can pickle it.
- **BR-CG2 — The task registry is parent-process, in-memory only.** 🟢
  `tasks: Dict[str, Dict[str, Any]]` guarded by `tasks_lock`
  (`cad_service.py:62-63`). Keys are the aeroplane **UUID** for exports and
  `f"{uuid}:tessellation:{wing_name}"` for tessellation
  (`tessellation_service.py:180`). `status ∈ {PENDING, RUNNING, SUCCESS,
  FAILURE}`; **`RUNNING` is derived on read** from `future.running()` and is
  never written by the worker. The registry does not survive a restart and is
  not shared across replicas. 🟡 Consequence: a task started before a reload
  becomes unqueryable (`GET /status` → 404) even though its worker may still be
  running.
- **BR-CG3 — Export tasks are serialised per aeroplane, nothing else is.** 🟢
  `check_task_available` (`cad_service.py:159-176`) raises `ConflictError` (409)
  when a task for the **same** aeroplane is already running. It is **not**
  called on the tessellation path, so a second tessellation POST for the same
  wing silently overwrites the registry entry (`state-machines.md` §11). 🔴

### Export

- **BR-CG4 — The export blueprint is a fixed three-node `$TYPE` tree.** 🟢
  `build_wing_blueprint` (`cad_service.py:206-262`) synthesises exactly the
  dialect `GeneralJSONDecoder` expects — the same format stored in
  `construction_plans.tree_json`:

  ```
  ConstructionRootNode  creator_id "eHawk-wing.root.root", loglevel 50
  ├── ConstructionStepNode  creator_id = <wing_name>, loglevel 50
  │     creator: WingLoftCreator | VaseModeWingCreator
  │             offset 0, wing_index <wing_name>, wing_side "BOTH", loglevel 10
  │             (+ leading/trailing_edge_offset_factor in vase mode)
  └── ConstructionStepNode  creator_id "output-wing", loglevel 50
        creator: <exporter class>, file_path "./tmp/exports",
                 tolerance 0.1, angular_tolerance 0.1, loglevel 20
  ```

  Defaults: `leading_edge_offset_factor = 0.1`,
  `trailing_edge_offset_factor = 0.15` (`app/api/v2/endpoints/cad.py:266-271`),
  `wing_scale = 1000.0` — metres → millimetres (`cad_service.py:517`).
- **BR-CG5 — 🟢 3MF is fixed properly and AMF is removed from the enum** (`Q-CG-1`, maintainer-answered). Previously the exporter enum and mapping disagreed: Two
  confirmed defects in `map_exporter_type` (`cad_service.py:185-203`):
  1. **3MF is broken.** The mapping returns the string `"ExportTo3MFCreator"`,
     but the real class is `ExportTo3mfCreator` (lower-case `mf`,
     `cad_designer/airplane/creator/export_import/ExportTo3mfCreator.py:10`).
     The decoder resolves `$TYPE` with `getattr(module, name)`, so a 3MF export
     raises `AttributeError` inside the worker and the task ends `FAILURE`.
     The existing test asserts the **wrong** string
     (`app/tests/test_cad_service_extended.py:130`), which locks the defect in.
     `construction_plan_service.py:563` uses the correct spelling.
  2. **`amf` is advertised but unsupported.** `ExporterUrlType.AMF = "amf"`
     exists (`app/schemas/AeroplaneRequest.py:58`) with no entry in the mapping,
     so the request fails with `ValidationError` → **422**.
- **BR-CG6 — 🟢 Exports move to a per-execution directory under `ARTIFACTS_BASE_DIR` (`Q-CG-2`), the pattern construction plans already use. Previously a shared mutable directory: The worker zips
  *everything* in `./tmp/exports` into `./tmp/{aeroplane_id}.zip` and then
  `os.unlink`s *every* file in it (`cad_service.py:368-377`). Because
  `check_task_available` only serialises per aeroplane (BR-CG3) while the pool
  runs four workers, two concurrent exports for **different** aeroplanes capture
  each other's files and delete them. `zipf.write(file.path)` additionally keeps
  the `tmp/exports/` prefix inside the archive.
- **BR-CG7 — The download path re-homes files under `tmp/`.** 🟢
  `_ensure_file_under_tmp` (`cad.py:59-76`) resolves the recorded path and, when
  it is not already under `CWD/tmp`, copies it to `tmp/{aeroplane_id}/zip/<name>`
  before serving it.

### Tessellation

- **BR-CG8 — The tessellation envelope is fixed and self-describing.** 🟢
  `_run_tessellation_worker` (`tessellation_service.py:53-165`) returns

  ```
  {"data": {"instances": [...], "shapes": {...}},
   "type": "data",
   "config": {"theme": "dark", "control": "orbit"},
   "count": <part_group.count_shapes()>}
  ```

  with fixed parameters `deviation = 0.1`, `angular_tolerance = 0.2`
  (l.113) and colour `#FF8400` for the wing. Every NumPy value is flattened by
  `_numpy_to_list` (l.36-50) before serialisation.
- **BR-CG9 — Tessellation failures report a type name only.** 🟢
  `{"status": "FAILURE", "error": f"Tessellation failed: {type(err).__name__}"}`
  (l.162-165) — deliberately no message, no traceback, no detail leakage across
  the process boundary.
- **BR-CG10 — The geometry hash is 64 bits of canonical JSON.** 🟢
  `geometry_hash = sha256(json.dumps(data, sort_keys=True, default=str))[:16]`
  (`tessellation_cache 🟢 (deleted, `Q-CG-4`)_service.py:22-29`). The literal string `"manual"` is
  stored instead when a tessellation is triggered by the POST endpoint without a
  hash.
- **BR-CG11 — A result whose geometry changed while it computed is discarded.** 🟢
  When the worker finishes, `is_hash_current` re-checks the stored
  `geometry_hash` and drops the result rather than caching it
  (`tessellation_service.py:366-368`).
- **BR-CG12 — Re-tessellation is debounced and cancellable — but nothing calls
  it.** 🟢 `trigger_background_tessellation` (l.240-300) uses
  `_DEBOUNCE_SECONDS = 2.0`; a new request cancels both the pending
  `threading.Timer` and any in-flight `Future` for the key
  `f"{aeroplane_id}:{wing_name}"`. 🔴 It is fully implemented **dead code**:
  `tessellation_hooks.on_wing_changed` ends in a TODO referencing **GH #202**
  (`tessellation_hooks.py:52-56`), so a stale entry stays stale until someone
  POSTs the tessellation endpoint again.
- **BR-CG13 — 🟢 Moot: the cache is deleted with the wing-tessellation subsystem (`Q-CG-4`/`Q-CG-5`). Previously:
  `cache_tessellation` upserts on `(aeroplane_id, component_type,
  component_name)` via `get_cached(...).first()`, and `invalidate` is a bulk
  `UPDATE ... SET is_stale = True` on the same triple returning the row count.
  The DDL creates only the FK and two indexes
  (`alembic/versions/04b8c856eab9_add_tessellation_cache 🟢 (deleted, `Q-CG-4`)_table.py:24-38`) — there
  is **no unique constraint**, so two concurrent inserts can produce duplicate
  rows and `.first()` silently picks one. 🟢 (schema) / 🟡 (impact)
- **BR-CG14 — 🟢 Moot: the tessellation cache is deleted (`Q-CG-4`/`Q-CG-5`). Previously:
  `tessellation_hooks.on_wing_changed` (l.17-56) resolves the aeroplane, calls
  `cache_svc.invalidate(..., "wing", wing_name)` and sanitises the wing name
  before logging (log-injection guard, l.44). There is no `on_fuselage_changed`;
  `component_type = "fuselage"` is modelled and coloured by the scene assembler
  but **has no producer at all**, and `start_wing_export_task` passes
  `fuselages=None` with the comment "not yet routed through the REST path"
  (`cad_service.py:518`).

### Scene assembly

- **BR-CG15 — The merged scene rebases every instance reference.** 🟢
  `_merge_tessellation_entries` (`cad.py:101-135`) deep-copies each cached
  `shapes` blob, recolours it (`#FF8400` when `component_type == "wing"`, else
  `#888888`), rebases every `{ref: N}` into the merged instance array via
  `_offset_refs` (l.79-88), and accumulates a bounding box. An aeroplane with no
  cached entry answers **404**.
- **BR-CG16 — 🟢 `bb` is removed from the response and `_expand_bounding_box` deleted (`Q-CG-3`, maintainer-answered). Previously degenerate: the worker
  writes `shapes["bb"] = combined_bb(shapes).to_dict()`, and
  `ocp_tessellate.ocp_utils.BoundingBox.to_dict()` returns
  `{"xmin","xmax","ymin","ymax","zmin","zmax"}` (verified in the installed
  package, `ocp_utils.py:1217-1225`). `_expand_bounding_box` (`cad.py:91-99`)
  returns early unless the dict carries `"min"` **and** `"max"`, so the loop
  never runs and the response always falls back to
  `{"min": [0,0,0], "max": [0,0,0]}` (l.130-133). 🟢 CONFIRMED by inspection of
  both sides.

### Artefacts

- **BR-68 — Every artefact path is traversal-guarded.** 🟢 `_ensure_within_base`
  resolves the candidate then calls `relative_to(base)`, raising
  `ValidationError` on escape (`app/services/artifact_service.py:25-36`).
  `get_file_path` additionally rejects symlinks (l.202-203).
- **BR-CG17 — A template keeps exactly one execution.** 🟢
  `create_template_execution_dir` **`shutil.rmtree`s** the previous run before
  creating the new one, so at most one execution per template survives
  (`artifact_service.py:81-110`). Plan runs accumulate instead.
- **BR-CG18 — `execution_id` is a UTC second stamp with a per-process collision
  suffix.** 🟢 `execution_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")`,
  with a `-N` suffix on same-second collisions tracked in the module globals
  `_last_execution_id` / `_last_execution_id_suffix` (l.39-58). 🟡 The counter is
  per-process, so two processes in the same second can still collide.
- **BR-CG19 — An empty execution zips to a valid empty archive.** 🟢
  `zip_execution` writes to a `tempfile.mkstemp` archive with `ZIP_DEFLATED` and
  arcnames relative to the execution directory; an execution with no files yields
  a valid empty zip rather than a 404 (l.233-265).
- **BR-CG20 — 🟢 `list_executions` applies the same reserved-prefix skip; the prefix becomes one module constant (`Q-CG-6`). Previously skipped in one scan and not the other:
  `_resolve_execution_dir` deliberately skips the `_template_runs` prefix when
  scanning per-aeroplane directories (l.282-283), but `list_executions` does not
  (l.123-142) — a template run can therefore surface in a plan listing with
  `aeroplane_id == "_template_runs"`.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Run every CAD build in a spawned worker process, four at a time | Must | The executor is a `ProcessPoolExecutor` with `mp_context="spawn"` and `max_workers=4`; no CAD call runs on the request thread |
| RF-02 | Tear the pool down from the application lifespan | Must | `shutdown_executor()` is called on shutdown; a second call is a no-op |
| RF-03 | Ship only picklable payloads across the boundary and rebuild the configuration in the worker | Must | The parent pickles an `AsbWingSchema`; the worker calls `asb_wing_schema_to_wing_config(schema, scale=1000.0)`; no `WingConfiguration` is ever pickled |
| RF-04 | Accept a wing export request and answer 202 with a status href | Must | `POST /aeroplanes/{id}/wings/{name}/{creator}/{exporter}` → 202 + `CadTaskAcceptedResponse` |
| RF-05 | Reject a concurrent export for the same aeroplane | Must | A second export POST while one is `PENDING`/`RUNNING` → 409 `conflict` |
| RF-06 | Build the three-node export blueprint with the documented defaults | Must | The emitted tree matches BR-CG4 field for field, including `wing_side "BOTH"` and the exporter's `tolerance`/`angular_tolerance` of `0.1` |
| RF-07 | Map an exporter URL type to its Creator class name | Must | `stl`/`step`/`iges` resolve to existing classes; `3mf` resolves to `ExportTo3mfCreator`; `amf` is either mapped or removed from the enum (BR-CG5 — the legacy behaviour is a defect) |
| RF-08 | Report task status, deriving `RUNNING` from the future | Must | `GET /aeroplanes/{id}/status` → `CadTaskStatusResponse`; an unknown id → 404 |
| RF-09 | Serve the export archive as a download | Must | `GET /aeroplanes/{id}/zip` streams the file; a path outside `CWD/tmp` is copied under `tmp/{id}/zip/` first |
| RF-10 | Tessellate a wing into the viewer envelope | Must | `POST /aeroplanes/{id}/wings/{name}/tessellation` → 202; the stored envelope carries `data.instances`, `data.shapes`, `type == "data"`, `config`, `count` |
| RF-11 | Report a tessellation failure without leaking detail | Must | A raising worker yields `status == "FAILURE"` and `error == "Tessellation failed: <ExceptionClassName>"` — no message, no traceback |
| RF-12 | Cache one tessellation per component with a content hash | Must | A second tessellation of the same wing updates the existing row instead of inserting a second one |
| RF-13 | Discard a result whose geometry changed while it computed | Must | With the stored hash mutated mid-run, the finished result is **not** written to the cache |
| RF-14 | Mark cached entries stale when the wing changes | Must | A wing geometry write sets `is_stale = True` for every entry of that wing and returns the affected row count |
| RF-15 | Debounce and cancel background re-tessellation | Should | Two requests within 2.0 s produce one run; the pending timer and the in-flight future are both cancelled (🔴 currently unreachable — no caller) |
| RF-16 | Assemble every cached entry of one aeroplane into one scene | Must | `GET /aeroplanes/{id}/tessellation` merges parts, rebases `{ref: N}`, colours wings `#FF8400` and everything else `#888888`, and reports `is_stale` |
| RF-17 | Answer 404 when nothing is cached for the aeroplane | Must | An aeroplane with no cache rows → 404 |
| RF-18 | ~~Report a correct scene bounding box~~ | **Won't** | 🟢 `bb` is removed from the response entirely (`Q-CG-3`). Previously the merged `bb` reflected the parts' real extent (🔴 the legacy key mismatch always yields `{min:[0,0,0],max:[0,0,0]}`) |
| RF-19 | Create per-execution artefact directories under a resolved base | Must | Plan runs land in `<base>/<aeroplane_id>/<plan_id>/<execution_id>/`; template runs in `<base>/_template_runs/<template_id>/<execution_id>/` |
| RF-20 | Keep at most one template execution | Must | A second template run removes the previous directory tree first |
| RF-21 | Reject every path that escapes the artefact base | Must | `../` traversal and symlinked files raise `ValidationError` → 422 |
| RF-22 | List, zip and delete artefacts of an execution | Must | Listing is recursive; zipping an empty execution yields a valid empty archive |
| RF-23 | Mount the CAD router only when the geometry kernel is importable | Must | On a platform without CadQuery the routes are absent rather than failing at call time (ADR 0017) |
| RF-24 | Tessellate fuselages | Won't (today) | `component_type = "fuselage"` is modelled and coloured but has no producer 🟡 |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | CAD must never run on a thread that shares the process's OCCT state | `cad_service.py:7-20, 66-78` (ADR 0005) | 🟢 |
| Correctness | Only picklable objects cross the process boundary; live geometry objects are rebuilt worker-side | `cad_service.py:303-307, 319-342`; `tessellation_service.py:81-82` | 🟢 |
| Correctness | A tessellation result is only cached when it still matches the geometry that produced it | `tessellation_service.py:366-368` | 🟢 |
| Performance | Four concurrent CAD builds maximum, bounding memory and OCCT process count | `cad_service.py:77` | 🟢 |
| Performance | Re-tessellation is debounced by 2.0 s and supersedes its predecessor | `tessellation_service.py:237, 240-300` | 🟢 |
| Performance | Tessellation quality is fixed (`deviation 0.1`, `angular_tolerance 0.2`) rather than negotiated per request | `tessellation_service.py:113` | 🟢 |
| Performance | The viewer reads from a DB cache instead of re-running CadQuery per page load | `tessellation_cache 🟢 (deleted, `Q-CG-4`)_service.py`; `cad.py` scene assembly | 🟢 |
| Security | Every artefact path is resolved and constrained to the base directory, and symlinks are rejected | `artifact_service.py:25-36, 202-203` | 🟢 |
| Security | Worker error text is the exception **type only**, so internal paths and payloads never reach the client | `tessellation_service.py:162-165` | 🟢 |
| Security | The wing name is sanitised before it is logged (log-injection guard) | `tessellation_hooks.py:44` | 🟢 |
| Availability | The CAD router is conditionally mounted, so a platform without CadQuery serves the rest of the API normally | `app/main.py:222-223` (ADR 0017) | 🟢 |
| Availability | A worker crash degrades to task `FAILURE`; the parent process is unaffected | `cad_service.py` done-callback; `state-machines.md` §11 | 🟢 |
| Portability | `spawn` is used on every platform rather than the faster `fork` | `cad_service.py:67` | 🟢 |
| Observability | Task state is queryable by URL while a build runs | `GET /aeroplanes/{id}/status` | 🟢 |
| Scalability | Task state is per-process and in memory — the module is single-replica by construction | `cad_service.py:62-63`; `state-machines.md` §11 | 🟡 |

## Acceptance Criteria

```gherkin
Feature: Process isolation

  Scenario: A CAD build runs in a worker process
    Given a persisted wing with at least two stations
    When I request a STEP export
    Then the build runs in a spawned worker process, not on the request thread
    And the parent ships a pickled AsbWingSchema rather than a WingConfiguration

  Scenario: The pool is torn down on shutdown
    Given the executor has been created lazily by a first request
    When the application lifespan shuts down
    Then shutdown_executor is called and the pool is closed

Feature: Export task lifecycle

  Scenario: An export is accepted asynchronously
    Given an aeroplane with a wing named "main"
    When I POST /aeroplanes/{id}/wings/main/wing_loft/step
    Then the response status is 202
    And the body carries the aeroplane id and a status href
    And the task is registered as PENDING

  Scenario: A concurrent export for the same aeroplane is rejected
    Given an export task for aeroplane A is already running
    When I POST a second export for aeroplane A
    Then the response status is 409
    And the error code is "conflict"

  Scenario: An unsupported exporter is rejected
    Given the exporter url type "amf"
    When I POST the export
    Then the response status is 422
    # BR-CG5: the enum advertises a value the mapping does not carry

  Scenario: A 3MF export completes
    Given the exporter url type "3mf"
    When the worker decodes the blueprint
    Then the exporter class resolves to ExportTo3mfCreator
    And the task ends SUCCESS
    # BR-CG5: the legacy mapping returns "ExportTo3MFCreator" and the task ends FAILURE

  Scenario: Status of an unknown task
    Given no task exists for aeroplane B
    When I GET /aeroplanes/B/status
    Then the response status is 404

Feature: Tessellation

  Scenario: A wing is tessellated and cached
    Given a persisted wing named "main"
    When I POST the tessellation endpoint and the worker finishes
    Then a cache row exists for (aeroplane, "wing", "main")
    And the stored envelope has type "data" and a non-zero count
    And config equals {"theme": "dark", "control": "orbit"}

  Scenario: A failing tessellation leaks no detail
    Given the worker raises a ValueError with a sensitive message
    When the task completes
    Then the status is FAILURE
    And the error text is exactly "Tessellation failed: ValueError"

  Scenario: A superseded result is discarded
    Given a tessellation is in flight for wing "main"
    When the wing geometry changes before the worker finishes
    Then the finished result is discarded
    And no cache row is written for that run

Feature: Cache invalidation

  Scenario: A wing write marks its tessellation stale
    Given a fresh cache entry for wing "main"
    When the wing geometry is written
    Then the entry's is_stale becomes true
    And the invalidate call reports one affected row

  Scenario: A stale entry is never refreshed automatically
    Given a stale cache entry
    When no further request is made
    Then it stays stale indefinitely
    # BR-CG12: background re-tessellation is implemented but unreachable (GH #202)

Feature: Scene assembly

  Scenario: Two cached wings merge into one scene
    Given cached tessellations for wings "main" and "htail"
    When I GET /aeroplanes/{id}/tessellation
    Then both parts appear in one shapes tree
    And every {ref: N} points into the merged instance array
    And both parts are coloured #FF8400

  Scenario: Nothing cached
    Given an aeroplane with no cached tessellation
    When I GET /aeroplanes/{id}/tessellation
    Then the response status is 404

  Scenario: The scene reports a real bounding box
    Given cached tessellations whose parts span 2 metres
    When I GET the merged scene
    Then bb.min and bb.max describe that extent
    # BR-CG16: the legacy key mismatch always answers {min:[0,0,0],max:[0,0,0]}

Feature: Artefact storage

  Scenario: A plan execution directory is created under the base
    Given ARTIFACTS_BASE_DIR is set
    When an execution starts for plan 7 of aeroplane A
    Then the directory <base>/A/7/<execution_id>/ exists
    And execution_id matches the UTC pattern %Y%m%dT%H%M%SZ

  Scenario: A template run replaces its predecessor
    Given template 3 already has one execution directory
    When a new template execution starts
    Then the previous directory tree is removed first
    And exactly one execution remains

  Scenario: A traversal attempt is rejected
    Given an artefact filename of "../../etc/passwd"
    When the file is requested
    Then a ValidationError is raised
    And the response status is 422

  Scenario: A symlinked artefact is rejected
    Given a symlink inside an execution directory
    When the file is requested
    Then a ValidationError is raised

  Scenario: An empty execution zips successfully
    Given an execution directory with no files
    When the zip is requested
    Then a valid empty archive is returned rather than a 404
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Process isolation for every CAD build (RF-01/RF-02/RF-03) | Must | The documented failure mode is an **indefinite hang**, not an error; without it the whole API thread pool is at risk (ADR 0005) |
| Export task lifecycle and status (RF-04/RF-05/RF-08) | Must | The only way a client learns that a multi-minute build finished |
| The three-node blueprint (RF-06) | Must | It is the contract between this module and the frozen Creator stack; a field change silently changes the exported geometry |
| Exporter mapping correctness (RF-07) | Must | Two of five advertised formats are broken today — the enum is the public contract |
| Tessellation + envelope (RF-10/RF-11) | Must | The workbench viewer cannot render without it, and the error contract is a security boundary |
| Cache + hash + staleness (RF-12/RF-13/RF-14) | Must | Rendering a solid takes seconds; the cache is what makes the workbench usable, and the hash is what keeps it honest |
| Scene assembly (RF-16/RF-17) | Must | The single read path the frontend uses for the 3D view |
| Artefact directories and guards (RF-19…RF-22) | Must | `construction-plans` depends on this storage layer for every execution; the guards are the only defence on a filesystem-serving path |
| Conditional router mount (RF-23) | Must | Without it the whole application fails to import on `linux/aarch64` (ADR 0017) |
| Correct scene bounding box (RF-18) | Should | Camera-fit quality only; parts still render from their own bounds |
| Debounced background re-tessellation (RF-15) | Should | A convenience over the explicit POST; fully implemented but unreachable |
| Persisting task state across restarts | Could | Single-maintainer deployment; today a restart loses the registry |
| Fuselage tessellation (RF-24) | Won't (today) | Modelled and coloured, but no producer exists and the export path passes `fuselages=None` |
| Reproducing the `"ExportTo3MFCreator"` spelling | Won't | A confirmed defect; a re-implementation must fix the mapping **and** the test that pins it |
| Reproducing the `bb` key mismatch | Won't | A confirmed defect; the producer and the consumer must agree on one key set |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/cad_service.py` (581 l.) | `_get_executor`, `shutdown_executor`, `tasks`/`tasks_lock`, `check_task_available`, `register_pending_task`, `map_exporter_type`, `build_wing_blueprint`, `_convert_wing_to_pickle`, `_extract_aeroplane_settings`, `_run_construction_worker`, `start_wing_export_task`, `get_task_result`, `get_export_file_path` | 🟢 |
| `app/services/tessellation_service.py` (385 l.) | `_numpy_to_list`, `_run_tessellation_worker`, `start_tessellation_task`, `trigger_background_tessellation`, `_start_tessellation_and_cache` | 🟢 |
| `app/services/tessellation_cache 🟢 (deleted, `Q-CG-4`)_service.py` (134 l.) | `compute_geometry_hash`, `cache_tessellation`, `get_cached`, `get_all_cached`, `invalidate`, `is_hash_current` | 🟢 |
| `app/services/tessellation_hooks.py` (56 l.) | `on_wing_changed` (+ the GH #202 TODO) | 🟢 |
| `app/services/artifact_service.py` (294 l.) | `_ensure_within_base`, `create_execution_dir`, `create_template_execution_dir`, `list_executions`, `list_files`, `get_file_path`, `zip_execution`, `delete_file`, `delete_execution`, `_resolve_execution_dir` | 🟢 |
| `app/models/tessellation_cache 🟢 (deleted, `Q-CG-4`).py` | `TessellationCacheModel` | 🟢 |
| `app/api/v2/endpoints/cad.py` (412 l.) | `_raise_http_from_domain`, `_ensure_file_under_tmp`, `_offset_refs`, `_expand_bounding_box`, `_merge_tessellation_entries`, the five routes | 🟢 |
| `app/schemas/api_responses.py` | `CadTaskAcceptedResponse`, `CadTaskStatusResponse`, `ZipAssetResponse`, `AeroplaneSettings` | 🟢 |
| `app/schemas/AeroplaneRequest.py` | `CreatorUrlType`, `ExporterUrlType` | 🟢 |
| `app/schemas/construction_plan.py` | `ArtifactFile`, `ArtifactDirectory` | 🟢 |
| `alembic/versions/04b8c856eab9_add_tessellation_cache 🟢 (deleted, `Q-CG-4`)_table.py` | the cache DDL (FK + two indexes, **no unique constraint**) | 🟢 |
| `app/main.py` | conditional CAD router mount (l.222-223), lifespan `shutdown_executor` (l.193), `/static` → `tmp/` mount (l.242-245) | 🟢 |
| `cad_designer/airplane/creator/**` | `WingLoftCreator`, `VaseModeWingCreator`, the four exporters | 🟢 read-only (ADR 0002) — see `cad-designer-topology` |
