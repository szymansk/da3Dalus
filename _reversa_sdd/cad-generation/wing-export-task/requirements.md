# wing-export-task

> Use-case specification, nested under the module [`cad-generation`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: cad-generation
> (Execution model, The export blueprint, R1–R4), `_reversa_sdd/data-dictionary.md`
> §CAD task registry / §CAD schemas, `_reversa_sdd/state-machines.md` §11.

## Overview

`wing-export-task` is the asynchronous manufacturing-output path: a client asks
for a wing in STL, STEP, IGES or 3MF; the service synthesises a three-node
construction blueprint, ships it plus a pickled wing schema into a worker
process, builds the solid, writes the exporter's output, zips it, and hands back
a downloadable archive descriptor. The whole exchange is mediated by an
**in-memory task registry** — there is no job table, no queue and no
persistence. 🟢

## Responsibilities

- Accept an export request for one wing, one creator type and one exporter
  type, and answer 202 immediately. 🟢
- Refuse a second export while one is already running **for the same
  aeroplane**. 🟢
- Map an exporter URL type to the Creator class name the decoder must resolve. 🟢
- Synthesise the three-node `$TYPE` blueprint that drives the loft (or vase-mode
  build) and the exporter step. 🟢
- Convert the wing to a picklable schema and extract the aeroplane settings
  (servos, printer settings) into picklable form. 🟢
- Build and export inside a worker process, then archive the exporter's output. 🟢
- Record `SUCCESS` (with the archive path) or `FAILURE` (with error and
  traceback) in the task registry. 🟢
- Answer status queries, deriving `RUNNING` from the future. 🟢
- Return a static download URL for the finished archive, re-homing the file
  under `tmp/` when necessary. 🟢

**Explicitly NOT this use case's responsibility:** tessellation, the viewer
envelope and the tessellation cache (→ [`../wing-tessellation/`](../wing-tessellation/requirements.md));
the artefact directory layout used by construction plans
(→ [`../artifact-serving/`](../artifact-serving/requirements.md)); the shared
process pool, specified at [module level](../design.md) §F1; the Creator classes
and the `$TYPE` decoder (→ `cad-designer-topology`, frozen per ADR 0002); the
wing persistence that supplies the input (→ `wing-design`); construction-plan
execution, which drives the same Creators **in-process**
(→ `construction-plans`).

## Business Rules

> IDs are inherited verbatim from [`../requirements.md`](../requirements.md).

- **BR-67 — CAD runs in a spawned worker process.** 🟢 *(module-level rule.)*
  `_run_construction_worker` is a **top-level** function so
  `ProcessPoolExecutor.submit` can pickle it.
- **BR-CG1 — Everything crossing the process boundary must be picklable.** 🟢
  The parent ships `pickle.dumps(AsbWingSchema)`; the worker rebuilds
  `asb_wing_schema_to_wing_config(schema, scale=1000.0)`
  (`cad_service.py:303-307`). `ServoInformation` is rebuilt worker-side from
  plain dicts (l.319-342), and `Printer3dSettings` crosses pickled.
- **BR-CG2 — The task registry is parent-process, in-memory only.** 🟢 The key
  for this path is the bare **aeroplane UUID** (`cad_service.py:62-63`);
  `status ∈ {PENDING, RUNNING, SUCCESS, FAILURE}` with `RUNNING` derived on read
  from `future.running()`. Lifecycle in `state-machines.md` §11.
- **BR-CG3 — Export tasks are serialised per aeroplane, nothing else is.** 🟢
  `check_task_available` raises `ConflictError` → **409** when a task for the
  same aeroplane is already `PENDING`/`RUNNING` (`cad_service.py:159-176`).
  *This use case is its owner.*
- **BR-CG4 — The export blueprint is a fixed three-node `$TYPE` tree.** 🟢
  *(this use case is its owner)*

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

  (`cad_service.py:206-262`.) Defaults `leading_edge_offset_factor = 0.1`,
  `trailing_edge_offset_factor = 0.15` — **query parameters** on the endpoint
  (`cad.py:266-271`) — and `wing_scale = 1000.0` (`cad_service.py:517`).
  🟡 The root id is the literal `"eHawk-wing.root.root"`, inherited from a
  legacy hand-authored plan and unrelated to the aeroplane being exported.
- **BR-CG5 — 🟢 3MF is fixed properly and AMF is removed from the enum** (`Q-CG-1`, maintainer-answered). Previously the exporter enum and mapping disagreed:
  *(this use case is its owner)*
  1. `map_exporter_type` returns `"ExportTo3MFCreator"`; the real class is
     `ExportTo3mfCreator` (lower-case `mf`,
     `cad_designer/airplane/creator/export_import/ExportTo3mfCreator.py:10`).
     The decoder resolves `$TYPE` with `getattr(module, name)`, so a 3MF export
     is accepted with 202 and then fails **asynchronously** with
     `AttributeError` → task `FAILURE`. The unit test at
     `app/tests/test_cad_service_extended.py:130` asserts the wrong spelling and
     therefore pins the defect; `construction_plan_service.py:563` uses the
     correct one.
  2. `ExporterUrlType.AMF = "amf"` (`app/schemas/AeroplaneRequest.py:58`) has no
     mapping entry, so an advertised enum value always answers **422**.
- **BR-CG6 — 🟢 Exports move to a per-execution directory under `ARTIFACTS_BASE_DIR` (`Q-CG-2`), the pattern construction plans already use. Previously a shared mutable directory: The worker zips
  *everything* in `./tmp/exports` into `./tmp/{aeroplane_id}.zip` and then
  `os.unlink`s *every* file in it (`cad_service.py:368-377`). Because BR-CG3
  serialises per aeroplane only while the pool runs four workers, two concurrent
  exports for **different** aeroplanes capture and delete each other's files.
  `zipf.write(file.path)` additionally stores the `tmp/exports/` prefix inside
  the archive rather than a flat arcname.
- **BR-CG7 — The download path re-homes files under `tmp/`.** 🟢
  `_ensure_file_under_tmp` (`cad.py:59-76`) resolves the recorded path and, when
  it is not already under `CWD/tmp`, copies it to
  `tmp/{aeroplane_id}/zip/<name>`. The response is a **descriptor** carrying a
  `/static` URL (`app/main.py:242-245` maps `/static` → `tmp/`), not the file
  bytes.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-WE-01 | Accept an export request and answer 202 | Must | `POST /aeroplanes/{id}/wings/{name}/{creator}/{exporter}` → 202 + `CadTaskAcceptedResponse`; unknown aeroplane or wing → 404 |
| RF-WE-02 | Refuse a concurrent export for the same aeroplane | Must | A second POST while one is `PENDING`/`RUNNING` → 409 `conflict` |
| RF-WE-03 | Accept the two vase-mode offset factors as query parameters | Must | `leading_edge_offset_factor` defaults to `0.1`, `trailing_edge_offset_factor` to `0.15` |
| RF-WE-04 | Accept optional aeroplane settings in the body | Should | `AeroplaneSettings` with printer settings and a servo map; absent for a simple loft |
| RF-WE-05 | Map every advertised exporter to a resolvable Creator class | Must | All five `ExporterUrlType` values resolve to a class the decoder can `getattr`; today `3mf` and `amf` do not |
| RF-WE-06 | Reject an unmapped exporter before scheduling work | Must | An unmapped value → 422, with no task registered |
| RF-WE-07 | Synthesise the three-node blueprint with the documented defaults | Must | A golden-file comparison matches field for field, including all three log levels and both exporter tolerances |
| RF-WE-08 | Convert the wing into a picklable schema | Must | The worker receives bytes; no `WingConfiguration` is ever pickled |
| RF-WE-09 | Extract aeroplane settings into picklable form | Must | Servo entries cross as plain dicts and are rebuilt as `ServoInformation` worker-side |
| RF-WE-10 | Build and export at millimetre scale | Must | The worker rebuilds the configuration with `scale = 1000.0` |
| RF-WE-11 | Archive the exporter's output | Must | The archive contains the files the exporter wrote and nothing belonging to another task |
| RF-WE-12 | Isolate each export's output directory | Must | Two concurrent exports for different aeroplanes produce complete, disjoint archives (🔴 legacy shares `./tmp/exports`) |
| RF-WE-13 | Store flat arcnames in the archive | Should | No entry carries a `tmp/exports/` path prefix |
| RF-WE-14 | Record task completion | Must | `SUCCESS` carries the archive path in `result`; `FAILURE` carries the error text and a traceback |
| RF-WE-15 | Answer status queries with a derived `RUNNING` | Must | A task in flight reports `RUNNING` without the worker writing it; `message`/`result` are omitted when null |
| RF-WE-16 | Resolve the status key from the query parameters | Must | `task_type=tessellation` + `wing_name` → the tessellation key; no `task_type` → the bare aeroplane id |
| RF-WE-17 | Return a download descriptor for a finished export | Must | `GET .../zip` → `{url, filename, mime_type}` with `mime_type == "application/zip"` |
| RF-WE-18 | Re-home an archive stored outside `tmp/` | Must | A recorded path outside `CWD/tmp` is copied to `tmp/{id}/zip/<name>` before the URL is derived |
| RF-WE-19 | Key the download on the request's wing and format | Should | A download URL naming a different wing or format must not return the previous archive (🔴 legacy ignores those segments) |
| RF-WE-20 | Point `href` at the status resource | Should | Following `href` reaches the poll URL (🔴 legacy returns `/aeroplanes/{id}`) |
| RF-WE-21 | Export fuselages alongside the wing | Won't (today) | `start_wing_export_task` passes `fuselages=None` — "not yet routed through the REST path" |
| RF-WE-22 | Survive a restart with the task still queryable | Could | The registry is in memory; a restart makes a running build unqueryable |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | The build never runs on the request thread — OCCT hangs in a worker thread | `cad_service.py:7-20, 66-78` (ADR 0005) | 🟢 |
| Correctness | Only picklable payloads cross the boundary; live geometry is rebuilt worker-side | `cad_service.py:303-307, 319-342` | 🟢 |
| Correctness | The blueprint is emitted in the exact dialect `GeneralJSONDecoder` resolves | `cad_service.py:206-262` | 🟢 |
| Performance | At most four concurrent builds, bounding memory and OCCT process count | `cad_service.py:77` | 🟢 |
| Performance | The request returns 202 immediately; a build may take minutes | endpoint returns before the future resolves | 🟢 |
| Isolation | Concurrent exports must not observe each other's output | 🟢 per-execution directory (`Q-CG-2`); previously violated by the shared `./tmp/exports` (`cad_service.py:368-377`) | 🟡 |
| Security | The download URL is derived by `relative_to` against the resolved `tmp/` root, so only files under `tmp/` are addressable | `cad.py:59-76` | 🟢 |
| Security | The aeroplane id is stripped of `\n`/`\r` before logging | `cad.py:341`, download handler | 🟢 |
| Availability | A worker crash degrades to task `FAILURE`; the parent is unaffected | done-callback | 🟢 |
| Availability | The CAD router is absent rather than failing when CadQuery is missing | `app/main.py:222-223` (ADR 0017) | 🟢 |
| Scalability | Task state is per-process and in memory — single-replica by construction | `cad_service.py:62-63` | 🟡 |
| Observability | A failed export retains its traceback in the registry, unlike tessellation | done-callback vs `tessellation_service.py:162-165` | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Starting an export

  Scenario: A STEP export is accepted
    Given an aeroplane with a wing named "main"
    When I POST /aeroplanes/{id}/wings/main/wing_loft/step
    Then the response status is 202
    And the body carries the aeroplane id and an href
    And a task is registered under the aeroplane id with status PENDING

  Scenario: A concurrent export for the same aeroplane is refused
    Given an export task for aeroplane A is PENDING
    When I POST a second export for aeroplane A
    Then the response status is 409
    And the error code is "conflict"
    And no second task is registered

  Scenario: An export for a different aeroplane is accepted
    Given an export task for aeroplane A is PENDING
    When I POST an export for aeroplane B
    Then the response status is 202

  Scenario: An unmapped exporter is rejected before any work is scheduled
    Given the exporter url type "amf"
    When I POST the export
    Then the response status is 422
    And no task is registered

  Scenario: An unknown wing is rejected
    Given an aeroplane with no wing named "ghost"
    When I POST an export for "ghost"
    Then the response status is 404

Feature: The blueprint

  Scenario: A wing-loft blueprint is synthesised
    Given creator url type "wing_loft" and exporter url type "step"
    When the blueprint is built
    Then the root node is a ConstructionRootNode with loglevel 50
    And the build step carries WingLoftCreator with wing_side "BOTH" and loglevel 10
    And the output step carries the exporter with file_path "./tmp/exports"
    And both exporter tolerances are 0.1
    And the output step's loglevel is 20

  Scenario: Vase mode adds the offset factors
    Given creator url type "vase_mode_wing"
    When the blueprint is built with default query parameters
    Then the build step carries leading_edge_offset_factor 0.1
    And trailing_edge_offset_factor 0.15

  Scenario: Every advertised exporter resolves
    Given each member of ExporterUrlType
    When the mapped class name is resolved through the decoder's namespace
    Then no member raises AttributeError
    # BR-CG5: "3mf" maps to ExportTo3MFCreator, which does not exist

Feature: The worker

  Scenario: A wing exports end to end
    Given an accepted STEP export
    When the worker runs
    Then the configuration is rebuilt at scale 1000.0
    And the blueprint decodes and builds
    And the archive contains the exporter's output
    And the task status becomes SUCCESS with the archive path in result

  Scenario: A failing build is recorded, not raised
    Given a wing whose loft raises inside the worker
    When the task completes
    Then the status is FAILURE
    And the error text and a traceback are recorded in the registry

  Scenario: Concurrent exports do not corrupt each other
    Given exports for aeroplane A and aeroplane B running at the same time
    When both workers finish
    Then each archive contains exactly its own exporter output
    And neither archive is missing files
    # BR-CG6: the shared ./tmp/exports makes this fail by construction

Feature: Status and download

  Scenario: A running task reports RUNNING
    Given an export whose future is executing
    When I GET /aeroplanes/{id}/status
    Then status is RUNNING
    And message is "Task is processing."
    And result is omitted from the body

  Scenario: A pending task reports a message, not a result
    Given an export that has not started
    When I GET the status
    Then status is PENDING and message is "Task is pending."

  Scenario: The status key is resolved from the query
    Given task_type "tessellation" and wing_name "main"
    When the status is requested
    Then the key "{id}:tessellation:main" is used
    And with no task_type the bare aeroplane id is used

  Scenario: A finished export yields a download descriptor
    Given a SUCCESS export task
    When I GET the zip route
    Then the body carries url, filename and mime_type "application/zip"
    And the url is under the /static mount

  Scenario: An archive outside tmp is re-homed
    Given the recorded export path is outside CWD/tmp
    When the download descriptor is built
    Then the file is copied to tmp/{aeroplane_id}/zip/<name> first
    And the original file is left in place
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Async accept + task registry + status (RF-WE-01/RF-WE-14/RF-WE-15) | Must | A build takes minutes; the registry is the only channel through which a client learns the outcome |
| Per-aeroplane conflict guard (RF-WE-02) | Must | Two builds for one aeroplane would race on the same archive path |
| The three-node blueprint (RF-WE-07) | Must | It is the contract with the frozen Creator stack; a changed field silently changes the exported geometry |
| Exporter mapping correctness (RF-WE-05/RF-WE-06) | Must | Two of five advertised formats are broken; the enum is the published contract |
| Picklable boundary (RF-WE-08/RF-WE-09/RF-WE-10) | Must | The process split is non-negotiable (ADR 0005) and an unpicklable payload fails at submit time |
| Output isolation per task (RF-WE-12) | Must | Concurrent exports currently corrupt each other's archives — a silent data-loss defect |
| Archiving (RF-WE-11) | Must | The archive is the deliverable |
| Download descriptor + re-homing (RF-WE-17/RF-WE-18) | Must | Without re-homing the file is not reachable through the `/static` mount |
| Vase-mode offset factors (RF-WE-03) | Should | Only meaningful for one of two creator types |
| Optional aeroplane settings (RF-WE-04) | Should | Absent for a simple loft; needed for servo and printer-aware builds |
| Flat arcnames (RF-WE-13) | Should | Cosmetic for the consumer, but surprising on extraction |
| Download keyed on wing and format (RF-WE-19) | Should | Today the path segments are decorative; a wrong URL returns the last archive |
| `href` pointing at the status resource (RF-WE-20) | Should | A documented affordance that does not work |
| Persisting task state across restarts (RF-WE-22) | Could | Single-maintainer deployment; a restart loses in-flight tasks |
| Fuselage export (RF-WE-21) | Won't (today) | `fuselages=None` with an explicit "not yet routed" comment |
| Reproducing `"ExportTo3MFCreator"` | Won't | A confirmed defect pinned by a test that must also be fixed |
| Reproducing the shared `./tmp/exports` | Won't | A confirmed defect; each task needs its own directory |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/api/v2/endpoints/cad.py` | `create_wing_loft` (l.262), `get_aeroplane_task_status` (l.322), `download_aeroplane_zip` (l.379), `_ensure_file_under_tmp` (l.59-76) | 🟢 |
| `app/services/cad_service.py` | `tasks`/`tasks_lock` (l.62-63), `_get_executor` (l.72-78), `check_task_available` (l.159-176), `register_pending_task`, `map_exporter_type` (l.185-203), `build_wing_blueprint` (l.206-262), `_convert_wing_to_pickle`, `_extract_aeroplane_settings`, `_run_construction_worker` (l.303-377), `start_wing_export_task` (l.517-518), `get_task_result`, `get_export_file_path` | 🟢 |
| `app/schemas/api_responses.py` | `CadTaskAcceptedResponse` (l.19), `CadTaskStatusResponse` (l.24), `ZipAssetResponse` (l.32), `AeroplaneSettings` (l.39) | 🟢 |
| `app/schemas/AeroplaneRequest.py` | `CreatorUrlType` (l.44), `ExporterUrlType` (l.55, incl. the unmapped `amf`) | 🟢 |
| `app/tests/test_cad_service_extended.py` | l.130 — the assertion that pins the 3MF defect | 🟢 |
| `app/converters/model_schema_converters.py` | `wing_model_to_asb_wing_schema`, `asb_wing_schema_to_wing_config` | 🟢 |
| `cad_designer/airplane/creator/wing/` | `WingLoftCreator`, `VaseModeWingCreator` | 🟢 read-only (ADR 0002) |
| `cad_designer/airplane/creator/export_import/` | `ExportToStlCreator`, `ExportToStepCreator`, `ExportToIgesCreator`, `ExportTo3mfCreator` (l.10 — the real spelling) | 🟢 read-only (ADR 0002) |
| `cad_designer/airplane/GeneralJSONEncoderDecoder.py` | `GeneralJSONDecoder` — resolves `$TYPE` via `getattr` | 🟢 read-only; contract in `cad-designer-topology` |
| `app/main.py` | conditional router mount (l.222-223), `/static` → `tmp/` (l.242-245) | 🟢 |
