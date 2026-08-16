# cad-generation — Implementation Tasks

> Executable sequence to re-implement the module from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Slice-level task lists: [`wing-tessellation/tasks.md`](wing-tessellation/tasks.md),
> [`wing-export-task/tasks.md`](wing-export-task/tasks.md),
> [`artifact-serving/tasks.md`](artifact-serving/tasks.md).
> Tasks marked **DO NOT REPRODUCE** describe a confirmed legacy defect that a
> re-implementation must fix rather than copy.

## Prerequisites

- [ ] `wing-design` available — the export and tessellation paths read a
      persisted `WingModel` with its stations, spars, TEDs and servos.
- [ ] `aeroplane-core` available — every route resolves an aeroplane by UUID;
      the cache row keys on the **integer** `aeroplanes.id`.
- [ ] `cad_designer` importable, with `WingLoftCreator`, `VaseModeWingCreator`,
      the four export Creators, `GeneralJSONDecoder`, `ServoInformation` and
      `Printer3dSettings` (millimetre world, frozen — ADR 0002).
- [ ] `app/converters/model_schema_converters.py` —
      `wing_model_to_asb_wing_schema` and `asb_wing_schema_to_wing_config`.
- [ ] `ocp_tessellate` — `to_ocpgroup`, `tessellate_group`, `combined_bb`.
- [ ] `get_db()` request-scoped session owning the transaction
      (ADR 0009). The tessellation done-callback runs **outside** a request and
      therefore opens its own `SessionLocal` and commits explicitly.
- [ ] `app/core/exceptions.py` hierarchy plus the `_raise_http_from_domain`
      mapping (`cad.py:41-56`).
- [ ] `ARTIFACTS_BASE_DIR` configured and `.resolve()`d by a validator
      (`app/core/config.py:24-32`); `tmp/` present and mounted at `/static`
      (`app/main.py:242-245`).
- [ ] CadQuery **optionally** present. Absent (e.g. `linux/aarch64`) the CAD
      router must not be mounted at all (ADR 0017).

## Tasks

### Execution model

- [ ] **T-01 — The spawned process pool.**
  `ProcessPoolExecutor(max_workers=4,
  mp_context=multiprocessing.get_context("spawn"))`, created lazily by
  `_get_executor()` and torn down by `shutdown_executor()` from the application
  lifespan and the test fixture. Record the rationale in the module docstring:
  OCCT is not thread-safe; `.intersect().clean()` takes ~100 ms on the main
  thread and hangs indefinitely in a worker thread; `fork` is unsafe with OCCT
  already loaded.
  - Legacy origin: `app/services/cad_service.py:7-20, 66-78, 81-95`;
    `app/main.py:193`; ADR 0005
  - Definition of done: no CAD call executes on the request thread; a second
    `shutdown_executor()` is a no-op; the pool is recreated on the next request.
  - Confidence: 🟢

- [ ] **T-02 — Picklable worker entry points.**
  Every function submitted to the pool is a **module-level** function. Nothing
  that holds `cq.Vector` / OCCT `gp_Vec` crosses the boundary.
  - Legacy origin: `cad_service.py` (`_run_construction_worker`),
    `tessellation_service.py` (`_run_tessellation_worker`)
  - Definition of done: a test pickles each worker callable and its arguments
    successfully; pickling a `WingConfiguration` is asserted to fail (documenting
    why the schema hop exists).
  - Confidence: 🟢

- [ ] **T-03 — The schema hop across the boundary.**
  Parent: `wing_model_to_asb_wing_schema` → `pickle.dumps`. Worker:
  `pickle.loads` → `asb_wing_schema_to_wing_config(schema, scale=1000.0)`
  (metres → millimetres). `ServoInformation` is rebuilt in the worker from plain
  dicts plus a pickled `Printer3dSettings`.
  - Legacy origin: `cad_service.py:303-307, 319-342`;
    `tessellation_service.py:81-82`
  - Definition of done: the worker receives only bytes and primitives; a
    round-trip test asserts the rebuilt configuration is in millimetres.
  - Confidence: 🟢

- [ ] **T-04 — The task registry.**
  `tasks: Dict[str, Dict[str, Any]]` guarded by `tasks_lock`. Keys: the
  aeroplane **UUID** for exports, `f"{uuid}:tessellation:{wing_name}"` for
  tessellation. `status ∈ {PENDING, RUNNING, SUCCESS, FAILURE}` with `RUNNING`
  **derived on read** from `future.running()`.
  - Legacy origin: `cad_service.py:62-63`; `tessellation_service.py:180`;
    `state-machines.md` §11
  - Definition of done: a task in flight reports `RUNNING` without the worker
    ever writing that value; an unknown key answers 404.
  - Confidence: 🟢

- [ ] **T-05 — Per-aeroplane export serialisation.**
  `check_task_available` raises `ConflictError` (→ 409) when a task for the same
  aeroplane is `PENDING`/`RUNNING`.
  - Legacy origin: `cad_service.py:159-176`
  - Definition of done: a second export POST for the same aeroplane returns 409;
    an export for a different aeroplane is accepted.
  - Confidence: 🟢

- [ ] **T-06 — Call `check_task_available` on the tessellation path too.**
  **DO NOT REPRODUCE** the legacy omission: today a second tessellation POST for
  the same wing silently overwrites the registry entry, losing the first task's
  result.
  - Legacy origin: `tessellation_service.py:180` (no guard);
    `state-machines.md` §11
  - Definition of done: a second tessellation POST for the same wing either
    returns 409 or is de-duplicated onto the running future — never silently
    overwrites.
  - Confidence: 🟢 (defect) / 🔴 (which of the two behaviours is wanted)

### Export

- [ ] **T-07 — `build_wing_blueprint`.**
  Emit the exact three-node `$TYPE` tree: `ConstructionRootNode` (`creator_id
  "eHawk-wing.root.root"`, `loglevel 50`) → `ConstructionStepNode` (`creator_id
  = <wing_name>`, `loglevel 50`) carrying `WingLoftCreator | VaseModeWingCreator`
  with `offset 0`, `wing_index <wing_name>`, `wing_side "BOTH"`, `loglevel 10`
  (+ `leading/trailing_edge_offset_factor` in vase mode) → `ConstructionStepNode`
  (`creator_id "output-wing"`, `loglevel 50`) carrying the exporter with
  `file_path "./tmp/exports"`, `tolerance 0.1`, `angular_tolerance 0.1`,
  `loglevel 20`.
  - Legacy origin: `cad_service.py:206-262`; defaults `cad.py:266-271`
  - Definition of done: a golden-file test compares the emitted JSON field for
    field, including log levels; the blueprint decodes through
    `GeneralJSONDecoder` without error.
  - Confidence: 🟢

- [ ] **T-08 — `map_exporter_type`, corrected.**
  `stl → ExportToStlCreator`, `step → ExportToStepCreator`,
  `iges → ExportToIgesCreator`, `3mf → ExportTo3mfCreator` (**lower-case `mf`**).
  Either map `amf` to a real Creator or remove `ExporterUrlType.AMF` from the
  enum. **DO NOT REPRODUCE** the legacy `"ExportTo3MFCreator"` string.
  - Legacy origin: `cad_service.py:185-203`;
    `cad_designer/airplane/creator/export_import/ExportTo3mfCreator.py:10`;
    `app/schemas/AeroplaneRequest.py:58`;
    counter-example `construction_plan_service.py:563`
  - Definition of done: every value of `ExporterUrlType` resolves to a class that
    `getattr(GeneralJSONEncoderDecoder, name)` returns; a parametrised test
    covers all five.
  - Confidence: 🟢

- [ ] **T-09 — Fix the test that pins the 3MF defect.**
  `app/tests/test_cad_service_extended.py:130` asserts the wrong spelling and
  therefore locks the bug in. The corrected test must assert against the **real
  class name**, ideally by importing the class rather than hard-coding a string.
  - Legacy origin: `app/tests/test_cad_service_extended.py:130`
  - Definition of done: the assertion is derived from
    `ExportTo3mfCreator.__name__`, so a future rename fails the test instead of
    passing it.
  - Confidence: 🟢

- [ ] **T-10 — Per-task export directory.**
  **DO NOT REPRODUCE** the shared `./tmp/exports`. Give each task its own
  directory (the pattern `construction-plans` already uses via
  `ARTIFACTS_BASE_DIR`), zip only that directory's contents with **flat**
  arcnames, and delete only that directory.
  - Legacy origin: `cad_service.py:253, 368-377, 369`
  - Definition of done: two exports for different aeroplanes running
    concurrently produce two archives whose contents are disjoint and complete;
    no archive carries a `tmp/exports/` path prefix.
  - Confidence: 🟢 (the defect) / 🟡 (the exact replacement layout)

- [ ] **T-11 — Export worker body.**
  Unpickle → rebuild the configuration and servos → `json.loads(blueprint,
  cls=GeneralJSONDecoder, wing_config=…, fuselage_config=…, servo_information=…,
  printer_settings=…)` → `blue_print.create_shape()` → archive → return
  `{status, result: {zipfile}}`. `wing_scale = 1000.0`.
  - Legacy origin: `cad_service.py:303-377, 517`
  - Definition of done: a wing exports to STEP end to end in a worker process and
    the archive contains the exporter's output.
  - Confidence: 🟢

- [ ] **T-12 — Done-callback and failure recording.**
  `future.add_done_callback` writes `SUCCESS` + result, or `FAILURE` + error and
  traceback, into the registry under the lock.
  - Legacy origin: `cad_service.py` (`_on_done`)
  - Definition of done: a worker that raises leaves the task queryable as
    `FAILURE` and never leaves it `PENDING`.
  - Confidence: 🟢

- [ ] **T-13 — Download with re-homing.**
  `_ensure_file_under_tmp` resolves the recorded path and, when it is not already
  under `CWD/tmp`, copies it to `tmp/{aeroplane_id}/zip/<name>` before serving.
  - Legacy origin: `cad.py:59-76`
  - Definition of done: a file recorded outside `tmp/` is served from a copy
    inside `tmp/`; the original is untouched.
  - Confidence: 🟢

### Tessellation

- [ ] **T-14 — The tessellation worker.**
  Rebuild the configuration at `scale=1000.0`; build
  `WingLoftCreator(creator_id="tessellation", wing_index=wing_name,
  wing_side="BOTH", wing_config={wing_name: wing_config})`; produce shapes;
  `to_ocpgroup(names=[wing_name], colors=["#FF8400"], alphas=[1.0])`;
  `tessellate_group(params={"deviation": 0.1, "angular_tolerance": 0.2})`;
  `shapes["bb"] = combined_bb(shapes).to_dict()`; flatten NumPy via
  `_numpy_to_list`; return
  `{"data": {"instances", "shapes"}, "type": "data",
  "config": {"theme": "dark", "control": "orbit"}, "count": n}`.
  - Legacy origin: `tessellation_service.py:36-50, 53-165, 108, 113`
  - Definition of done: the envelope validates against the documented key set and
    contains no NumPy scalar or array.
  - Confidence: 🟢

- [ ] **T-15 — Use the public Creator contract.**
  The legacy worker calls the **private** `_create_shape` hook directly, skipping
  `return_needed_shapes` and the log-level handling of the public
  `create_shape` template method. Prefer `create_shape` unless a documented
  reason forbids it.
  - Legacy origin: `tessellation_service.py` (worker body);
    `cad_designer/airplane/AbstractShapeCreator.py:49-61`
  - Definition of done: the tessellation path uses the public entry point, or a
    comment records why the private hook is required.
  - Confidence: 🟡 INFERRED — harmless today (no upstream shapes), but off-contract.

- [ ] **T-16 — Type-only failure text.**
  `{"status": "FAILURE", "error": f"Tessellation failed: {type(err).__name__}"}`
  — no message, no traceback, no path.
  - Legacy origin: `tessellation_service.py:162-165`
  - Definition of done: a worker raising `ValueError("secret /abs/path")` yields
    exactly `"Tessellation failed: ValueError"`.
  - Confidence: 🟢

- [ ] **T-17 — The cache table and its logical key.**
  `tessellation_cache 🟢 (deleted, `Q-CG-4`)(id, aeroplane_id FK ON DELETE CASCADE, component_type,
  component_name, geometry_hash, tessellation_json, is_stale, created_at,
  updated_at)`, indexed on `id` and `aeroplane_id`.
  - Legacy origin: `app/models/tessellation_cache 🟢 (deleted, `Q-CG-4`).py:8`;
    `alembic/versions/04b8c856eab9_add_tessellation_cache 🟢 (deleted, `Q-CG-4`)_table.py:24-38`;
    data-dictionary §Module: cad-generation
  - Definition of done: deleting an aeroplane removes its cache rows; both
    indexes exist.
  - Confidence: 🟢

- [ ] **T-18 — Add the missing unique constraint.**
  **DO NOT REPRODUCE** the legacy schema: `get_cached(...).first()` treats
  `(aeroplane_id, component_type, component_name)` as unique while nothing
  enforces it, so two concurrent inserts create duplicates and `.first()` picks
  one arbitrarily.
  - Legacy origin: `tessellation_cache 🟢 (deleted, `Q-CG-4`)_service.py` (`get_cached`, `cache_tessellation`);
    the migration above
  - Definition of done: a unique constraint on the triple exists and the upsert
    is expressed against it; a concurrent-insert test raises rather than
    duplicating. See **TM-01** for the data migration.
  - Confidence: 🟢

- [ ] **T-19 — `compute_geometry_hash`.**
  `sha256(json.dumps(data, sort_keys=True, default=str)).hexdigest()[:16]`; the
  literal `"manual"` when a run is triggered by the POST endpoint without a hash.
  - Legacy origin: `tessellation_cache 🟢 (deleted, `Q-CG-4`)_service.py:22-29`
  - Definition of done: key order and non-JSON types do not change the digest;
    the `"manual"` sentinel round-trips.
  - Confidence: 🟢

- [ ] **T-20 — Discard a superseded result.**
  After the worker finishes, re-check `is_hash_current` and drop the result when
  the stored hash changed meanwhile.
  - Legacy origin: `tessellation_service.py:366-368`
  - Definition of done: mutating the stored hash mid-run leaves the cache
    untouched and logs nothing alarming.
  - Confidence: 🟢

- [ ] **T-21 — Invalidation hook.**
  `on_wing_changed` resolves the aeroplane, calls
  `invalidate(aeroplane.id, "wing", wing_name)` and **sanitises the wing name
  before logging** (log-injection guard).
  - Legacy origin: `tessellation_hooks.py:17-56`, guard at l.44
  - Definition of done: a wing write flips `is_stale`; a wing name containing
    `\n` or ANSI escapes cannot forge a log line.
  - Confidence: 🟢

- [ ] **T-22 — Debounced background re-tessellation, wired up.**
  `_DEBOUNCE_SECONDS = 2.0`; a new request cancels both the pending
  `threading.Timer` and the in-flight `Future` for
  `f"{aeroplane_id}:{wing_name}"`; the stale-hash gate (T-20) applies. The
  legacy implementation is complete but **has no caller** — the hook ends in a
  TODO referencing GH #202.
  - Legacy origin: `tessellation_service.py:237, 240-300`;
    `tessellation_hooks.py:52-56`
  - Definition of done: two writes within 2 s produce one worker run, and a
    stale entry becomes fresh without a client POST.
  - Confidence: 🟢 (`Q-CG-4`: both blockers named in GH #202 are resolved by deleting the subsystem)

### Scene assembly

- [ ] **T-23 — `_merge_tessellation_entries`.**
  Deep-copy each cached `shapes`; recolour `#FF8400` for
  `component_type == "wing"`, `#888888` otherwise; rebase every `{ref: N}` via
  `_offset_refs(shapes, len(combined_instances))`; accumulate the bounding box;
  emit the merged envelope with `version: 3`, `parts[]`,
  `loc: [[0,0,0],[0,0,0,1]]` and `is_stale`.
  - Legacy origin: `cad.py:79-88, 101-135`
  - Definition of done: two cached wings render as two parts whose `ref` indices
    resolve inside the merged instance array; the source cache rows are
    unmodified.
  - Confidence: 🟢

- [ ] **T-24 — Make the bounding box agree end to end.**
  **DO NOT REPRODUCE** the key mismatch: the worker writes
  `{xmin,xmax,ymin,ymax,zmin,zmax}` (`BoundingBox.to_dict()`), while
  `_expand_bounding_box` requires `{"min","max"}` and returns early, so the
  merged scene always answers `{"min":[0,0,0],"max":[0,0,0]}`.
  - Legacy origin: `tessellation_service.py` (worker `bb`);
    `cad.py:91-99, 130-133`; `ocp_tessellate/ocp_utils.py:1217-1225`
  - Definition of done: for a wing spanning a known extent, the merged `bb`
    reproduces that extent; a regression test asserts the producer's key set
    against the consumer's expectation.
  - Confidence: 🟢

- [ ] **T-25 — 404 on an empty cache.**
  `GET /aeroplanes/{id}/tessellation` answers 404 when no entry exists, rather
  than an empty scene.
  - Legacy origin: `cad.py` (scene route)
  - Definition of done: an aeroplane with no cache rows returns 404 with the
    standard error envelope.
  - Confidence: 🟢

### Artefacts

- [ ] **T-26 — Directory layout and execution ids.**
  `<ARTIFACTS_BASE_DIR>/<aeroplane_id>/<plan_id>/<execution_id>/` for plan runs;
  `<ARTIFACTS_BASE_DIR>/_template_runs/<template_id>/<execution_id>/` for
  templates (`TEMPLATE_RUNS_PREFIX = "_template_runs"`).
  `execution_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")` with a `-N`
  suffix on same-second collisions.
  - Legacy origin: `artifact_service.py:39-58, 78`
  - Definition of done: two executions created in the same second differ by the
    suffix; the base directory is `.resolve()`d once at config time.
  - Confidence: 🟢 (🟡 the counter is per-process — two processes still collide)

- [ ] **T-27 — Template runs keep exactly one execution.**
  `create_template_execution_dir` `shutil.rmtree`s the previous run first.
  - Legacy origin: `artifact_service.py:81-110`
  - Definition of done: after two template runs exactly one execution directory
    exists, and it is the newer one.
  - Confidence: 🟢

- [ ] **T-28 — Path guards (BR-68).**
  `_ensure_within_base` = `resolve()` then `relative_to(base)`, raising
  `ValidationError` on escape; `get_file_path` additionally rejects symlinks.
  - Legacy origin: `artifact_service.py:25-36, 202-203`
  - Definition of done: `../` traversal, an absolute path outside the base, and a
    symlink pointing outside all raise; the tests cover each.
  - Confidence: 🟢

- [ ] **T-29 — Listing, zipping and deletion.**
  `list_executions`, `list_files(subpath, recursive)`, `zip_execution`
  (`tempfile.mkstemp`, `ZIP_DEFLATED`, arcnames relative to the execution
  directory, empty → valid empty zip), `delete_file`, `delete_execution`.
  - Legacy origin: `artifact_service.py:123-142, 233-265`
  - Definition of done: an empty execution yields a valid empty archive rather
    than a 404; every listed entry carries `name`, `is_dir`, `size_bytes` and an
    ISO `modified`.
  - Confidence: 🟢

- [ ] **T-30 — Make the two directory scans agree on `_template_runs`.**
  **DO NOT REPRODUCE** the asymmetry: `_resolve_execution_dir` skips the prefix
  (l.282-283) while `list_executions` does not (l.123-142), so a template run can
  surface in a plan listing with `aeroplane_id == "_template_runs"`.
  - Legacy origin: `artifact_service.py:123-142, 282-283`
  - Definition of done: one predicate decides what counts as an aeroplane
    directory, used by both scans; a template run never appears in a plan
    listing under a fake aeroplane id.
  - Confidence: 🟢

### REST layer and mounting

- [ ] **T-31 — The five routes.**
  Exactly as listed in [`contracts.md`](contracts.md), with the shared
  domain→HTTP mapping (`NotFoundError`→404, `ValidationError`→422,
  `ConflictError`→409, else 500) and `response_model_exclude_none` on the status
  route.
  - Legacy origin: `app/api/v2/endpoints/cad.py:41-56` and the route definitions
  - Definition of done: contract tests assert every status code in
    `contracts.md`, including the 409 on a concurrent export and the 404 on an
    empty cache.
  - Confidence: 🟢

- [ ] **T-32 — Conditional router mount.**
  Include the CAD router only when the `cad_designer`/CadQuery import succeeded,
  so a platform without a geometry kernel serves the rest of the API normally.
  - Legacy origin: `app/main.py:222-223`; ADR 0017
  - Definition of done: with CadQuery uninstalled the application starts and the
    CAD paths answer 404 (absent), not 500.
  - Confidence: 🟢

- [ ] **T-33 — Configuration surface.**
  `max_workers = 4`; mp context `"spawn"`; `_DEBOUNCE_SECONDS = 2.0`;
  tessellation `deviation 0.1` / `angular_tolerance 0.2`; exporter
  `tolerance 0.1` / `angular_tolerance 0.1`; `wing_scale = 1000.0`; colours
  `#FF8400` (wing) and `#888888` (other); `ARTIFACTS_BASE_DIR` default
  `/tmp/da3dalus_artifacts`, `.resolve()`d by a validator; export dir
  `./tmp/exports` (CWD-relative); static mount `/static` → `tmp/`.
  - Legacy origin: `cad_service.py:67, 77, 253-255, 517`;
    `tessellation_service.py:108, 113, 173, 237`; `cad.py:121`;
    `app/core/config.py:24-32`; `app/main.py:242-245`
  - Definition of done: every constant is a named module-level value, not a
    literal at the call site, and the table above is reproduced in the code
    documentation.
  - Confidence: 🟢

- [ ] **T-34 — Route fuselages through the export and tessellation paths.**
  `component_type = "fuselage"` is modelled and coloured but has no producer, and
  `start_wing_export_task` passes `fuselages=None` with the comment "not yet
  routed through the REST path".
  - Legacy origin: `cad_service.py:518`; `cad.py:121`;
    `tessellation_hooks.py` (no `on_fuselage_changed`)
  - Definition of done: a fuselage tessellates and appears in the merged scene
    coloured `#888888`, and a fuselage write invalidates its cache entry.
  - Confidence: 🟡 GAP — planned or to be removed; see `questions.md`.

## Test Tasks

- [ ] **TT-01 — Happy path, export:** POST an export, poll `GET /status` until
      `SUCCESS`, download the zip, and assert it contains the exporter's output.
- [ ] **TT-02 — Failure, concurrent export:** a second POST for the same
      aeroplane returns 409 with `error.code == "conflict"`.
- [ ] **TT-03 — Exporter mapping matrix:** all five `ExporterUrlType` values
      resolve to a class that the decoder can `getattr`; the assertion derives
      from `__name__`, not a hard-coded string.
- [ ] **TT-04 — Blueprint golden file:** the emitted tree matches field for
      field, including `wing_side "BOTH"`, both tolerances and every log level.
- [ ] **TT-05 — Picklability:** each worker callable and its arguments pickle;
      a `WingConfiguration` does not (documenting the schema hop).
- [ ] **TT-06 — Concurrent exports of different aeroplanes** produce two
      archives with disjoint, complete contents (regression for the shared
      `./tmp/exports` race).
- [ ] **TT-07 — Happy path, tessellation:** POST, wait, assert a cache row and a
      valid envelope with `type == "data"` and a non-zero `count`.
- [ ] **TT-08 — Failure, tessellation:** a raising worker yields exactly
      `"Tessellation failed: <ExceptionClassName>"` and no other detail.
- [ ] **TT-09 — Envelope is JSON-clean:** no NumPy scalar or array survives
      `_numpy_to_list`.
- [ ] **TT-10 — Hash stability:** `compute_geometry_hash` is invariant to key
      order and tolerant of non-JSON types; the `"manual"` sentinel round-trips.
- [ ] **TT-11 — Superseded result discarded:** mutate the stored hash mid-run;
      assert the cache is untouched.
- [ ] **TT-12 — Invalidation:** a wing write flips `is_stale` and reports the
      affected row count; a name containing a newline cannot forge a log line.
- [ ] **TT-13 — Debounce:** two triggers within 2.0 s produce one run; the
      pending timer and the in-flight future are both cancelled.
- [ ] **TT-14 — Cache uniqueness:** two concurrent inserts for the same triple
      raise instead of producing duplicate rows.
- [ ] **TT-15 — Scene merge:** two cached wings produce two parts whose `{ref}`
      indices resolve inside the merged instance array; the cache rows are
      unchanged (deep copy).
- [ ] **TT-16 — Bounding box:** for a wing of known extent the merged `bb`
      reproduces it — the regression test for the producer/consumer key
      mismatch.
- [ ] **TT-17 — Empty cache:** `GET /aeroplanes/{id}/tessellation` → 404.
- [ ] **TT-18 — Traversal and symlink guards:** `../` escape, an absolute
      outside path, and a symlink each raise `ValidationError` → 422.
- [ ] **TT-19 — Template run replacement:** after two runs exactly one execution
      directory exists and it is the newer one.
- [ ] **TT-20 — Empty zip:** an execution with no files yields a valid, readable,
      empty archive.
- [ ] **TT-21 — Execution-id collision:** two executions created within the same
      second differ by the `-N` suffix.
- [ ] **TT-22 — `_template_runs` never appears in a plan listing** with a fake
      aeroplane id.
- [ ] **TT-23 — Degraded platform:** with CadQuery uninstalled the app starts and
      the CAD routes are absent (404), not 500.
- [ ] **TT-24 — Download re-homing:** a recorded path outside `CWD/tmp` is served
      from a copy under `tmp/{aeroplane_id}/zip/`.

## Data Migration Tasks

- [ ] **TM-01 — De-duplicate `tessellation_cache 🟢 (deleted, `Q-CG-4`)` before adding the unique
      constraint.** Because nothing enforced
      `(aeroplane_id, component_type, component_name)`, existing databases may
      hold duplicate rows. Keep the most recent `updated_at` per triple, delete
      the rest, then add the constraint (T-18). 🟢 (the risk) / 🟡 (whether any
      real database actually contains duplicates)
- [ ] **TM-02 — Decide the fate of orphaned `./tmp/exports` content.** Files
      left there by an interrupted worker are indistinguishable from a live
      export's output. A migration to per-task directories (T-10) should treat
      the legacy directory as disposable and document that any residue is
      discarded. 🟡
- [ ] **TM-03 — Re-tessellate or invalidate everything once the bounding-box fix
      lands.** Cached envelopes written by the old worker carry the
      `xmin/xmax/…` key set. If the fix moves the key set to `min`/`max` in the
      **producer**, every existing row becomes unreadable by the new consumer;
      either migrate the stored JSON or mark every row stale. 🔴 Needs a decision
      on which side of the contract changes.

## Suggested Order

1. **T-01 → T-04** first — the pool, the picklable boundary and the registry are
   the substrate everything else runs on. T-02 constrains the signature of every
   worker written later; T-03 fixes the unit hop (m → mm) that the whole module
   depends on.
2. **T-17 → T-19** next, in parallel with step 1 — the cache table, its unique
   constraint (T-18, with TM-01) and the hash function have no dependency on the
   pool and unblock both the tessellation and the scene paths.
3. **T-05 → T-06** — the concurrency guards. T-06 is a behaviour decision
   (409 vs de-duplicate) and should be settled before T-14 is wired to a route.
4. **T-07 → T-13** — the export path. T-08 blocks T-07 (the blueprint embeds the
   exporter class name), T-09 goes with T-08, and T-10 should land **before**
   T-11 so the worker is written against per-task directories from the start.
5. **T-14 → T-16, T-20 → T-22** — the tessellation path. T-14 depends on T-03;
   T-20 depends on T-19; T-22 depends on T-20 and on the GH #202 decision.
   T-15 is a contract question that can be answered independently.
6. **T-23 → T-25** — scene assembly, which depends on T-17 (rows to read) and
   T-14 (envelopes to merge). T-24 must be decided together with **TM-03**,
   because fixing the producer invalidates every stored envelope.
7. **T-26 → T-30** — the artefact layer, fully independent of steps 3–6 and
   parallelisable. `construction-plans` cannot be re-implemented until this is
   done, so start it early if that module is on the critical path.
8. **T-31 → T-33** last — the REST layer is thin and only wires what is already
   tested. T-32 is a startup concern and should be verified on an aarch64-like
   environment.
9. **T-34** is deferred until the fuselage question in `questions.md` is
   answered.

## Pending Gaps

- **Should the merged scene's bounding box be fixed in the producer or the
  consumer?** Both sides are one line; the choice determines whether every
  cached envelope must be migrated (TM-03) and whether the frontend contract
  changes.
- **Is GH #202 (background re-tessellation) still the plan?** The mechanism is
  fully implemented and unreachable. If it is wanted, what supplies the wing
  schema pickle from a write path that has only a `WingModel`?
- **What should a second tessellation POST for the same wing do** — 409 like
  exports, or attach to the running future?
- **Are fuselages meant to be tessellated?** `component_type = "fuselage"` is
  modelled, coloured and invalidatable in principle, but has no producer and the
  export path passes `fuselages=None`.
- **Should `ExporterUrlType.AMF` be implemented or removed?** It is part of the
  published enum and always answers 422.
- **Where should export archives live?** Every other artefact is under
  `ARTIFACTS_BASE_DIR`; exports use CWD-relative `./tmp/exports` and
  `./tmp/{aeroplane}.zip`, which is what makes the concurrency race possible.
- **Should CAD task state survive a restart?** Today a long build becomes
  unqueryable while its worker keeps running, and there is no way to reattach.
- **Is the literal blueprint root id `"eHawk-wing.root.root"` significant?** It
  is inherited from a legacy hand-authored plan and is unrelated to the
  aeroplane being exported.
