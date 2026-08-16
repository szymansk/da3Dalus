# wing-export-task — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Nested under the module [`cad-generation`](../tasks.md).
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Tasks marked **DO NOT REPRODUCE** describe a confirmed legacy defect that a
> re-implementation must fix rather than copy.

## Prerequisites

- [ ] Module-level tasks **T-01 → T-05** (the spawned pool, picklable worker
      entry points, the schema hop, the task registry, the per-aeroplane
      conflict guard) are in place.
- [ ] `wing-design` supplies a persisted `WingModel` with its stations, spars,
      trailing-edge devices and servos, eager-loadable in one query.
- [ ] `cad_designer` importable with `WingLoftCreator`, `VaseModeWingCreator`,
      `ExportToStlCreator`, `ExportToStepCreator`, `ExportToIgesCreator`,
      `ExportTo3mfCreator`, `GeneralJSONDecoder`, `ServoInformation`,
      `Printer3dSettings` (millimetre world, frozen — ADR 0002).
- [ ] `app/converters/model_schema_converters.py` provides
      `wing_model_to_asb_wing_schema` and `asb_wing_schema_to_wing_config`.
- [ ] A writable working root and a `/static` mount over it
      (`app/main.py:242-245`).
- [ ] `ExporterUrlType` / `CreatorUrlType` enums agreed as the public contract.

## Tasks

### Request path

- [ ] **T-WE-01 — The export endpoint.**
  `POST /aeroplanes/{aeroplane_id}/wings/{wing_name}/{creator_url_type}/{exporter_url_type}`
  → **202**. Resolve the aeroplane with the wing graph eager-loaded (404),
  resolve the wing (404), delegate to `start_wing_export_task`.
  - Legacy origin: `app/api/v2/endpoints/cad.py:262`
  - Definition of done: unknown aeroplane and unknown wing both answer 404; a
    valid request answers 202 with `{aeroplane_id, href}`.
  - Confidence: 🟢

- [ ] **T-WE-02 — Query and body parameters.**
  `leading_edge_offset_factor` (query, default `0.1`),
  `trailing_edge_offset_factor` (query, default `0.15`), `aeroplane_settings`
  (optional body, `AeroplaneSettings`). `creator_url_type` defaults to
  `wing_loft`, `exporter_url_type` to `stl`.
  - Legacy origin: `cad.py:262-277`
  - Definition of done: the two factors are query parameters with those
    defaults; a simple loft works with no body at all.
  - Confidence: 🟢

- [ ] **T-WE-03 — Per-aeroplane conflict guard.**
  `check_task_available(aeroplane_id)` raises `ConflictError` → **409** when a
  task for the same aeroplane is `PENDING`/`RUNNING`, **before** any work is
  scheduled.
  - Legacy origin: `cad_service.py:159-176`
  - Definition of done: a second POST for the same aeroplane returns 409 and
    registers nothing; a POST for a different aeroplane is accepted.
  - Confidence: 🟢

- [ ] **T-WE-04 — Register and submit.**
  `register_pending_task(aeroplane_id)` → `PENDING`, then submit
  `_run_construction_worker` with `wing_scale = 1000.0` and attach the
  done-callback.
  - Legacy origin: `cad_service.py:517`
  - Definition of done: the registry entry exists immediately after the 202 and
    transitions without any further client action.
  - Confidence: 🟢

- [ ] **T-WE-05 — Make `href` point at the status resource.**
  **DO NOT REPRODUCE**: the response carries `href = "/aeroplanes/{id}"` while
  the docstring promises `GET /status`.
  - Legacy origin: `cad.py:262` (response construction)
  - Definition of done: following `href` reaches the poll URL for this task.
  - Confidence: 🟢

### Blueprint and exporter mapping

- [ ] **T-WE-06 — `build_wing_blueprint`.**
  Emit exactly: `ConstructionRootNode` (`creator_id "eHawk-wing.root.root"`,
  `loglevel 50`) → `ConstructionStepNode` (`creator_id = <wing_name>`,
  `loglevel 50`) carrying `WingLoftCreator | VaseModeWingCreator` with
  `offset 0`, `wing_index <wing_name>`, `wing_side "BOTH"`, `loglevel 10`
  (+ the two offset factors in vase mode) → `ConstructionStepNode`
  (`creator_id "output-wing"`, `loglevel 50`) carrying the exporter with
  `file_path`, `tolerance 0.1`, `angular_tolerance 0.1`, `loglevel 20`.
  - Legacy origin: `cad_service.py:206-262`; defaults `cad.py:266-271`
  - Definition of done: a golden-file test compares the emitted JSON field for
    field, including all three log levels; the result decodes through
    `GeneralJSONDecoder` without error.
  - Confidence: 🟢

- [ ] **T-WE-07 — Decide the blueprint root id.**
  The literal `"eHawk-wing.root.root"` is inherited from a legacy hand-authored
  plan and identifies nothing about the aeroplane. Either derive it from the
  aeroplane/wing or document it as an intentional constant.
  - Legacy origin: `cad_service.py:206-262`
  - Definition of done: the id is either derived and asserted, or a comment
    records why it is fixed.
  - Confidence: 🟡 INFERRED — no functional dependency on the value was found.

- [ ] **T-WE-08 — `map_exporter_type`, corrected.**
  `stl → ExportToStlCreator`, `step → ExportToStepCreator`,
  `iges → ExportToIgesCreator`, `3mf → ExportTo3mfCreator` (**lower-case `mf`**).
  Either map `amf` to a real Creator or remove `ExporterUrlType.AMF`.
  **DO NOT REPRODUCE** the `"ExportTo3MFCreator"` string.
  - Legacy origin: `cad_service.py:185-203`;
    `cad_designer/airplane/creator/export_import/ExportTo3mfCreator.py:10`;
    `app/schemas/AeroplaneRequest.py:58`; correct usage at
    `construction_plan_service.py:563`
  - Definition of done: a parametrised test resolves **every** `ExporterUrlType`
    member through the decoder's namespace without `AttributeError`.
  - Confidence: 🟢

- [ ] **T-WE-09 — Fix the test that pins the 3MF defect.**
  `app/tests/test_cad_service_extended.py:130` asserts the wrong spelling, which
  is why the suite is green while the feature is broken. Derive the expectation
  from `ExportTo3mfCreator.__name__` so a future rename fails the test.
  - Legacy origin: `app/tests/test_cad_service_extended.py:130`
  - Definition of done: the assertion imports the class rather than hard-coding
    a string; renaming the class breaks the test.
  - Confidence: 🟢

- [ ] **T-WE-10 — Fail fast on an unmapped exporter.**
  Raise `ValidationError` → **422** during request handling, before a task is
  registered — never let an unresolvable class name reach the worker.
  - Legacy origin: `cad_service.py:185-203` (the `amf` path)
  - Definition of done: an unmapped exporter answers 422 synchronously and
    leaves the registry untouched; no exporter failure is deferred to the worker.
  - Confidence: 🟢

### Picklable payload

- [ ] **T-WE-11 — `_convert_wing_to_pickle`.**
  `wing_model_to_asb_wing_schema(wing)` → `pickle.dumps`.
  - Legacy origin: `cad_service.py` (`_convert_wing_to_pickle`)
  - Definition of done: the payload pickles; a test asserts that pickling a
    `WingConfiguration` fails, documenting why the schema hop exists.
  - Confidence: 🟢

- [ ] **T-WE-12 — `_extract_aeroplane_settings`.**
  Servo entries cross as plain dicts; `Printer3dSettings` crosses pickled.
  - Legacy origin: `cad_service.py` (`_extract_aeroplane_settings`)
  - Definition of done: the settings payload pickles and reconstructs to
    equivalent objects worker-side.
  - Confidence: 🟢

- [ ] **T-WE-13 — Rebuild live objects worker-side.**
  `asb_wing_schema_to_wing_config(schema, scale=1000.0)` and
  `ServoInformation` reconstruction inside the worker.
  - Legacy origin: `cad_service.py:303-307, 319-342`
  - Definition of done: the worker never receives an OCC-backed object; a known
    1 m chord appears as 1000 units in the built configuration.
  - Confidence: 🟢

### Worker and archiving

- [ ] **T-WE-14 — The construction worker.**
  Decode the blueprint with `GeneralJSONDecoder`, injecting `wing_config`,
  `fuselage_config`, `servo_information` and `printer_settings`; call
  `create_shape()`; archive the exporter's output; return
  `{"status": "SUCCESS", "result": {"zipfile": …}}`.
  - Legacy origin: `cad_service.py:303-377`
  - Definition of done: a wing exports to STEP end to end in a worker process
    and the archive contains the exporter's files.
  - Confidence: 🟢

- [ ] **T-WE-15 — Per-task output directory.**
  **DO NOT REPRODUCE** the shared `./tmp/exports`. Give each task its own
  directory, zip only that directory, and delete only that directory. Use the
  per-execution pattern `construction-plans` already has via `artifact_service`.
  - Legacy origin: `cad_service.py:253` (blueprint `file_path`),
    l.368-377 (zip-everything + unlink-everything)
  - Definition of done: two exports for different aeroplanes running
    concurrently produce complete, disjoint archives.
  - Confidence: 🟢 (the defect) / 🟡 (the exact replacement layout — see the
    module-level question about `ARTIFACTS_BASE_DIR`)

- [ ] **T-WE-16 — Flat arcnames.**
  **DO NOT REPRODUCE** `zipf.write(file.path)`, which stores the
  `tmp/exports/` prefix inside the archive. Write each entry with a basename
  arcname.
  - Legacy origin: `cad_service.py:369`
  - Definition of done: extracting the archive yields the exported files
    directly, with no nested directory.
  - Confidence: 🟢

- [ ] **T-WE-17 — Detect an empty export.**
  The legacy worker reports `SUCCESS` even when the exporter wrote nothing.
  - Legacy origin: `cad_service.py:368-377` (no emptiness check)
  - Definition of done: an export that produced no file is reported as a
    failure, or the response carries an explicit file count.
  - Confidence: 🟡 INFERRED — no check was found; the desired behaviour is a
    product decision.

- [ ] **T-WE-18 — Done-callback with error retention.**
  Record `SUCCESS` + result, or `FAILURE` + error text **and traceback**, under
  the registry lock. Note the deliberate asymmetry with tessellation, which
  records the exception **type only**.
  - Legacy origin: `cad_service.py` (`_on_done`);
    contrast `tessellation_service.py:162-165`
  - Definition of done: a raising worker leaves the task queryable as `FAILURE`
    with a traceback, and never leaves it `PENDING`. The asymmetry is either
    justified in a comment or resolved.
  - Confidence: 🟢 (the behaviour) / 🔴 (whether the asymmetry is intended)

- [ ] **T-WE-19 — Record the creator and exporter on the task.**
  Nothing in the registry says which formats a task used, so a `FAILURE` cannot
  be attributed without reading the traceback.
  - Legacy origin: `cad_service.py:62-63` (registry value shape)
  - Definition of done: the task entry carries the creator and exporter types,
    and the status response can surface them.
  - Confidence: 🟡 INFERRED — an observability improvement, not legacy behaviour.

### Status and download

- [ ] **T-WE-20 — Status endpoint and key resolution.**
  Three branches: `task_type == "tessellation"` **and** `wing_name` →
  `f"{id}:tessellation:{wing}"`; any other truthy `task_type` →
  `f"{id}:{task_type}"`; otherwise the bare aeroplane id.
  - Legacy origin: `cad.py:322, 334-340`
  - Definition of done: each branch is covered by a test; the aeroplane id is
    stripped of `\n`/`\r` before logging.
  - Confidence: 🟢

- [ ] **T-WE-21 — Status body mapping.**
  `PENDING → message "Task is pending."`; `RUNNING → "Task is processing."`;
  `SUCCESS → result` (no message); `FAILURE → message = error, else "An error
  occurred"`. `response_model_exclude_none=True` so nulls are omitted.
  - Legacy origin: `cad.py:330-360`
  - Definition of done: each status yields the documented body, and null fields
    are absent rather than `null`.
  - Confidence: 🟢

- [ ] **T-WE-22 — Derived `RUNNING`.**
  `get_task_result` computes `RUNNING` from `future.running()`; the worker never
  writes it.
  - Legacy origin: `cad_service.py` (`get_task_result`)
  - Definition of done: a task whose future is executing reports `RUNNING`
    without any worker-side write.
  - Confidence: 🟢

- [ ] **T-WE-23 — Download descriptor.**
  `get_export_file_path` → `_ensure_file_under_tmp` →
  `relative_to((cwd / "tmp").resolve())` → `{url, filename, mime_type}` with
  `url = f"{base_url}/static/{relative}"` and
  `mime_type = "application/zip"`. `base_url` comes from `request.base_url`,
  falling back to `settings.base_url` when it is the literal `"apiserver"`.
  - Legacy origin: `cad.py:379-412`; `_ensure_file_under_tmp` l.59-76;
    `app/main.py:242-245`
  - Definition of done: a finished export yields a resolvable `/static` URL; a
    path outside `tmp/` raises rather than producing a URL.
  - Confidence: 🟢 (🟡 for the `"apiserver"` sentinel, which is deployment-specific)

- [ ] **T-WE-24 — Re-homing.**
  Copy an archive that is not already under `CWD/tmp` into
  `tmp/{aeroplane_id}/zip/<name>` before deriving the URL; leave the original in
  place.
  - Legacy origin: `cad.py:59-76`
  - Definition of done: a recorded path outside `tmp/` is served from the copy;
    the original file still exists.
  - Confidence: 🟢

- [ ] **T-WE-25 — Key the download on wing and format.**
  **DO NOT REPRODUCE**: the handler accepts `wing_name`, `creator_url_type` and
  `exporter_url_type` as path parameters and ignores all three, so a URL naming
  a different wing or format returns the last archive for that aeroplane.
  - Legacy origin: `cad.py:379` (signature) vs `get_export_file_path`
  - Definition of done: the download resolves the archive produced by **that**
    wing and format, or the route drops the unused segments.
  - Confidence: 🟢

- [ ] **T-WE-26 — Route fuselages through the export path.**
  `start_wing_export_task` passes `fuselages=None` with the comment "not yet
  routed through the REST path", so a multi-body aircraft exports only its wing.
  - Legacy origin: `cad_service.py:518`
  - Definition of done: an aeroplane with a fuselage exports both bodies, or the
    response states that only the wing was exported.
  - Confidence: 🟡 GAP — blocked on the module-level fuselage decision (T-34).

## Test Tasks

- [ ] **TT-WE-01 — Happy path:** POST a STEP export, poll until `SUCCESS`,
      fetch the descriptor, and assert the archive contains the exporter output.
- [ ] **TT-WE-02 — Failure, concurrent same aeroplane:** the second POST returns
      409 with `error.code == "conflict"` and registers nothing.
- [ ] **TT-WE-03 — Different aeroplanes are accepted** concurrently.
- [ ] **TT-WE-04 — Failure, unmapped exporter:** `amf` → 422 synchronously, no
      task registered.
- [ ] **TT-WE-05 — Exporter matrix:** every `ExporterUrlType` member resolves
      through the decoder namespace; the expectation derives from `__name__`.
- [ ] **TT-WE-06 — Blueprint golden file:** field-for-field comparison including
      `wing_side "BOTH"`, both tolerances and all three log levels.
- [ ] **TT-WE-07 — Vase mode:** the build step carries both offset factors with
      their defaults `0.1` / `0.15`.
- [ ] **TT-WE-08 — Blueprint decodes:** the emitted JSON round-trips through
      `GeneralJSONDecoder` and yields a runnable tree.
- [ ] **TT-WE-09 — Picklability:** the worker callable, the wing payload and the
      settings payload all pickle; a `WingConfiguration` does not.
- [ ] **TT-WE-10 — Millimetre scale:** a known 1 m chord becomes 1000 units in
      the worker-side configuration.
- [ ] **TT-WE-11 — Isolation:** two concurrent exports for different aeroplanes
      produce complete, disjoint archives (regression for the shared directory).
- [ ] **TT-WE-12 — Flat arcnames:** no archive entry carries a `tmp/exports/`
      prefix.
- [ ] **TT-WE-13 — Empty export:** an exporter that wrote nothing does not report
      a bare `SUCCESS`.
- [ ] **TT-WE-14 — Failure recording:** a raising worker leaves `FAILURE` with an
      error and a traceback, never `PENDING`.
- [ ] **TT-WE-15 — Derived `RUNNING`:** a running future reports `RUNNING`
      without a worker write.
- [ ] **TT-WE-16 — Status key branches:** all three resolution branches covered.
- [ ] **TT-WE-17 — Status body matrix:** each status yields the documented
      `message`/`result` pair, with nulls omitted.
- [ ] **TT-WE-18 — Log injection:** an aeroplane id containing `\n` cannot forge
      a log line in the status or download handler.
- [ ] **TT-WE-19 — Download descriptor:** `mime_type == "application/zip"`, the
      URL sits under `/static`, and the filename is the archive basename.
- [ ] **TT-WE-20 — Re-homing:** a path outside `CWD/tmp` is copied under
      `tmp/{id}/zip/` and the original survives.
- [ ] **TT-WE-21 — Path escape:** a recorded path that escapes `tmp/` raises
      rather than producing a URL.
- [ ] **TT-WE-22 — Download keyed correctly:** a URL naming a different wing or
      format does not return the previous archive.

## Suggested Order

1. **T-WE-08 → T-WE-10** first — the exporter mapping is the smallest change
   with the largest correctness payoff, and T-WE-06 embeds its output in the
   blueprint. T-WE-09 lands with T-WE-08 or the suite keeps hiding the defect.
2. **T-WE-06 → T-WE-07** next — the blueprint, which depends on T-WE-08 for the
   exporter class name. T-WE-07 is an independent naming decision.
3. **T-WE-11 → T-WE-13** — the picklable payload. These depend on module-level
   T-03 and block the worker.
4. **T-WE-15 before T-WE-14** — decide the per-task directory layout *first*, so
   the worker is written against it rather than retro-fitted. T-WE-16 and
   T-WE-17 go with T-WE-14.
5. **T-WE-18 → T-WE-19** — completion recording; T-WE-18 depends on module-level
   T-04 (the registry).
6. **T-WE-01 → T-WE-05** — the request path, once there is something to submit.
   T-WE-03 depends on module-level T-05.
7. **T-WE-20 → T-WE-22** — status, which needs T-WE-18 for the values it reports.
8. **T-WE-23 → T-WE-25** — the download path, which needs T-WE-14 to have
   produced an archive. T-WE-25 may change the route signature and should be
   settled before the contract is published.
9. **T-WE-26** last, blocked on the module-level fuselage decision.

## Pending Gaps

- **Should `ExporterUrlType.AMF` be implemented or removed?** It is part of the
  published enum and always answers 422.
- **Where should export output live?** Every other artefact is under
  `ARTIFACTS_BASE_DIR`; exports use CWD-relative `./tmp/exports` and
  `./tmp/{aeroplane}.zip`, which is exactly what makes the concurrency race
  possible.
- **Is the error-verbosity asymmetry intended?** Exports keep a full traceback;
  tessellation deliberately keeps only the exception type. One of the two is
  presumably wrong.
- **Should the download route keep its wing/creator/exporter segments?** They are
  currently ignored, so the URL is misleading; either honour them or drop them.
- **Should an export that produced no files report `SUCCESS`?** No emptiness
  check exists today.
- **Should CAD task state survive a restart?** A long build becomes unqueryable
  while its worker keeps running, and there is no way to reattach.
- **Is the blueprint root id `"eHawk-wing.root.root"` significant?** It is a
  legacy constant unrelated to the aeroplane being exported.
- **Are fuselages meant to be exported?** `fuselages=None` is hard-coded with an
  explicit "not yet routed through the REST path" comment.
