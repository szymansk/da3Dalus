# construction-plans — Implementation Tasks

> Executable sequence to re-implement the module from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Slice-level task lists:
> [`plan-template-lifecycle/tasks.md`](plan-template-lifecycle/tasks.md),
> [`plan-execution/tasks.md`](plan-execution/tasks.md),
> [`creator-catalog/tasks.md`](creator-catalog/tasks.md),
> [`construction-parts/tasks.md`](construction-parts/tasks.md).

## Prerequisites

- [ ] `aeroplane-core` available — every aeroplane-scoped route resolves an
      aeroplane by UUID before touching a plan or a part.
- [ ] `get_db()` request-scoped session owning the transaction
      (`app/db/session.py`, ADR 0009). Services call `db.flush()` but never
      `commit()`. Note `autoflush=False`, which is why `create_part` flushes
      explicitly to obtain the id.
- [ ] `app/core/exceptions.py` hierarchy (`NotFoundError`, `ValidationError`,
      `ConflictError`, `InternalError`, `ServiceException`).
- [ ] `cad-designer-topology` package importable **or** cleanly absent —
      `GeneralJSONDecoder`, `AbstractShapeCreator` and the Creator subpackages
      (`ImportError` must be a supported state, ADR 0017).
- [ ] `cad-generation`'s `artifact_service` — execution-directory allocation,
      traversal guards, listing, zip and delete.
- [ ] `wing-design` — `wing_model_to_wing_config(wing, scale=1000.0)` and the
      aeroplane/wing lookup helpers.
- [ ] `components` catalogue with an optional `printer_settings` row carrying
      `layer_height` / `wall_thickness` / `rel_gap_wall_thickness` in `specs`,
      and `material` rows for part links.
- [ ] `ocp_tessellate` (`to_ocpgroup`, `tessellate_group`) for the result
      preview — optional, since tessellation is best-effort.
- [ ] A writable CWD-relative `tmp/` (construction-part storage) **and** a
      writable `ARTIFACTS_BASE_DIR`. These are two different roots today.

## Tasks

### Persistence

- [ ] **T-01 — The `construction_plans` table.**
  `id` PK, `name` (not unique), `description`, `tree_json` JSON,
  `plan_type` String with `server_default "template"`, `aeroplane_id` FK →
  `aeroplanes.id` (nullable), `created_at`, `updated_at` (`onupdate`).
  Neither `plan_type` nor `aeroplane_id` carries an enum or check constraint.
  - Legacy origin: `app/models/construction_plan.py:11`;
    `alembic/versions/b3e2f1a4c7d9_add_construction_plans_table.py`,
    `c4d5e6f7a8b9_add_plan_type_and_aeroplane_id.py`
  - Definition of done: a template row stores `aeroplane_id IS NULL`; a plan row
    stores an aeroplane reference; both survive a round-trip of `tree_json`
    without key reordering damage.
  - Confidence: 🟢

- [ ] **T-02 — Fix the `aeroplane_id` column type before writing any code.**
  The legacy column is a **`String`** FK pointing at the **`Integer`**
  `aeroplanes.id`, with no `ON DELETE`. Decide whether it should reference the
  integer PK or the public `uuid`, then make the type match.
  - Legacy origin: `app/models/construction_plan.py`; data-dictionary
    §Table `construction_plans`
  - Definition of done: the schema is creatable on PostgreSQL, not only SQLite;
    deleting an aeroplane has a defined effect on its plans.
  - Confidence: 🟡 — needs a human decision (see § Pending Gaps).

- [ ] **T-03 — The `construction_parts` table.**
  `id` PK, `aeroplane_id` String **indexed**, `name`, `volume_mm3`, `area_mm2`,
  `bbox_x/y/z_mm` (all nullable, `ge=0` in the schema),
  `material_component_id` FK → `components.id` (nullable, **not** type-checked
  to be a `material`), `locked` Bool `server_default "0"`, `thumbnail_url`,
  `file_path`, `file_format`, timestamps.
  - Legacy origin: `app/models/construction_part.py:19`;
    `alembic/versions/4a9c81984e86_…`, `1a39e098d77e_…`, `7cc3eaf27d6b_…`
  - Definition of done: a row round-trips through `ConstructionPartRead`; the
    `component_tree.construction_part_id` FK resolves.
  - Confidence: 🟢

- [ ] **T-04 — Decide the `construction_parts.aeroplane_id` orphan policy.**
  There is no foreign key today, so deleting an aeroplane leaves both rows and
  files behind.
  - Legacy origin: data-dictionary §Table `construction_parts`
  - Definition of done: either an FK with `ON DELETE CASCADE` plus file cleanup,
    or a documented, tested orphan-reaping job.
  - Confidence: 🟡 — needs a human decision.

### Plan CRUD and the template duality

- [ ] **T-05 — `_validate_tree_json`.**
  Require `$TYPE` **and** `creator_id` at the root; nothing deeper.
  - Legacy origin: `construction_plan_service.py:72-81`
  - Definition of done: a payload missing either key returns 422 with a message
    naming the missing field; a payload whose *children* are malformed is
    accepted at write time and fails only at execution.
  - Confidence: 🟢

- [ ] **T-06 — `_count_steps` tolerating both successor shapes.**
  Recursive count over `successors`, accepting an `OrderedDict` (encoder form)
  **and** a list (frontend form); the root itself is not counted.
  - Legacy origin: `construction_plan_service.py:38-53`
  - Definition of done: a root with two children, one of which has one child,
    reports `step_count == 3`; a tree with list successors reports the same
    number as the equivalent dict tree.
  - Confidence: 🟢

- [ ] **T-07 — `instantiate_template`.**
  Assert `plan_type == "template"` (else 422), assert the aeroplane exists
  (else 404), `copy.deepcopy` the tree, name it
  `"{template.name} — Plan"` unless overridden, set `plan_type = "plan"` and the
  aeroplane id. Record **no** back-link.
  - Legacy origin: `construction_plan_service.py:207-232`
  - Definition of done: mutating the new plan's tree leaves the template's tree
    untouched; instantiating a `"plan"` returns 422.
  - Confidence: 🟢

- [ ] **T-08 — `to_template`.**
  The mirror operation, naming the result `"{plan.name} — Template"` and
  clearing `aeroplane_id`.
  - Legacy origin: `construction_plan_service.py:235-251`
  - Definition of done: the produced row has `plan_type == "template"` and
    `aeroplane_id IS NULL`.
  - Confidence: 🟢

- [ ] **T-09 — Legacy root migration — as a one-off, not on every read.**
  The legacy behaviour rewrites a `ConstructionStepNode` root into
  `ConstructionRootNode`, drops the `creator` key, `flag_modified`s the column
  and flushes, **inside `get_plan`**. Reproduce the *transformation* exactly, but
  move it to a data migration.
  - Legacy origin: `construction_plan_service.py:113-133`
  - Definition of done: the transformation is covered by a unit test against a
    real legacy tree; after the migration, `get_plan` performs no writes and a
    read of a plan issues no `UPDATE`.
  - Confidence: 🟢 on the transformation, and 🟢 on disposition (`R2-02`): after `Q-CP-7`'s Alembic migration the lazy path is **dead and deleted** (`P-DEAD-0`). Previously open whether it may be
    dropped (see § Pending Gaps).

### Execution

- [ ] **T-10 — Effective-aeroplane resolution.**
  `plan.aeroplane_id or request.aeroplane_id`; a template with neither raises
  `ValidationError`.
  - Legacy origin: `construction_plan_service.py:616-722` (step 1)
  - Definition of done: executing a template with an empty body returns 422
    **before** any artefact directory is created.
  - Confidence: 🟢

- [ ] **T-11 — Artefact-directory allocation per plan type.**
  `_template_runs/<plan_id>/<execution_id>` for templates (previous run
  `rmtree`d), `<aeroplane_id>/<plan_id>/<execution_id>` for plans (accumulating).
  - Legacy origin: `construction_plan_service.py` step 2;
    `artifact_service.create_template_execution_dir` /
    `create_execution_dir` (specified in `cad-generation`)
  - Definition of done: two plan runs leave two directories; two template runs
    leave one.
  - Confidence: 🟢

- [ ] **T-12 — Millimetre `wing_config` map.**
  `{wing.name: wing_model_to_wing_config(wing, scale=1000.0)}`.
  - Legacy origin: `construction_plan_service.py:650-654`
  - Definition of done: a wing whose DB chord is `0.25` m reaches the Creator as
    `250.0` mm.
  - Confidence: 🟢

- [ ] **T-13 — Surface a dropped wing instead of only logging it.**
  Legacy behaviour: a per-wing conversion failure logs a warning and removes the
  wing from the map, so the plan runs against a partial aircraft silently.
  - Legacy origin: `construction_plan_service.py:650-654`
  - Definition of done: the failure is still non-fatal, **and** the
    `ExecutionResult` carries a structured warning naming the wing and the
    reason (ADR 0012). Do **not** reproduce the silent form.
  - Confidence: 🟢 on the behaviour, 🟡 on the response-shape change.

- [ ] **T-14 — `_load_printer_settings`.**
  First `components` row with `component_type == "printer_settings"`, reading
  `layer_height`, `wall_thickness`, `rel_gap_wall_thickness` from `specs`;
  fallback `0.24 / 0.42 / 0.075`.
  - Legacy origin: `construction_plan_service.py:984-1013`
  - Definition of done: with no such component the execution uses the three
    fallback values; with one, its values reach the Creators.
  - Confidence: 🟢

- [ ] **T-15 — `_rewrite_export_paths`.**
  Deep-copy the tree; for
  `_EXPORT_CREATOR_TYPES = {ExportToStlCreator, ExportToStepCreator,
  ExportToIgesCreator, ExportTo3mfCreator}` rewrite a **relative** `file_path`
  to `<artifact_dir>/<file_path>` and `mkdir` it. Handle both the nested
  (`node["creator"]["file_path"]`) and the flat node shape. Absolute paths pass
  through untouched.
  - Legacy origin: `construction_plan_service.py:559-564, 567-613`
  - Definition of done: a plan with `file_path == "out"` writes into
    `<artifact_dir>/out/` and nothing lands in the project root; the **stored**
    `tree_json` is unchanged after the execution.
  - Confidence: 🟢

- [ ] **T-16 — Decode with injected kwargs.**
  `json.loads(tree, cls=GeneralJSONDecoder, wing_config=…,
  printer_settings=…, servo_information={}, engine_information=None,
  component_information=None)`; a failure becomes
  `ValidationError("Failed to decode construction plan: …")`.
  - Legacy origin: `construction_plan_service.py:670-678`
  - Definition of done: a tree referencing an unknown `$TYPE` returns 422 with
    that message prefix; a valid tree yields a live `ConstructionRootNode`.
  - Confidence: 🟢 (the three slots are filled from the component tree — `Q-CP-2` — T-17)

- [ ] **T-17 — Decide where servo / engine / component information comes from.**
  All three decoder slots are hard-coded empty at **both** execution call sites,
  so `ServoImporterCreator`, `ComponentImporterCreator` and
  `EngineMountShapeCreator` can never receive real data through REST.
  - Legacy origin: `construction_plan_service.py:670-678` and the streaming
    equivalent
  - Definition of done: a documented source (component tree, COTS library, or
    request body) and at least one end-to-end test that drives a
    `ServoImporterCreator` with real data.
  - Confidence: 🟡 — needs a human decision.

- [ ] **T-18 — Run `create_shape()` and capture failure as data.**
  A raising Creator yields `ExecutionResult(status="error", error, duration_ms,
  artifact_dir, execution_id)` with **HTTP 200**.
  - Legacy origin: `construction_plan_service.py:616-722` (step 7)
  - Definition of done: a deliberately failing Creator produces a 200 whose body
    has `status == "error"` and a populated `execution_id`.
  - Confidence: 🟢

- [ ] **T-19 — Decide the execution isolation model before implementing step 7.**
  ADR 0005 states OCCT must run in a spawned process; the legacy code runs
  `create_shape()` on the request thread (and on a daemon thread when
  streaming).
  - Legacy origin: `execute_plan` / `execute_plan_streaming` vs
    `app/services/cad_service.py:7-20` (ADR 0005)
  - Definition of done: an explicit, recorded decision — move execution into the
    process pool, or amend ADR 0005 with the evidence that in-process execution
    is safe. Do not re-implement the contradiction silently.
  - Confidence: 🟡 — blocking design decision.

- [ ] **T-20 — `_tessellate_shapes` (best-effort).**
  Collect values with a `.val` attribute, `s.val().Solids()` per shape (skip
  individual failures), `Compound.makeCompound` → `Workplane` →
  `to_ocpgroup(names=["result"], colors=["#FF8400"])` →
  `tessellate_group({"deviation": 0.1, "angular_tolerance": 0.2})`. Any
  exception logs a warning and returns `None`.
  - Legacy origin: `construction_plan_service.py:930-981`
  - Definition of done: an execution whose shapes cannot be tessellated still
    reports `status == "success"` with `tessellation is None`.
  - Confidence: 🟢

### Streaming

- [ ] **T-21 — SSE frame contract.**
  `event: shape data {"name", "tessellation"}`,
  `event: complete data {"duration_ms", "shape_keys", "tessellation",
  "artifact_dir", "execution_id"}`,
  `event: error data {"error", "duration_ms", "artifact_dir", "execution_id"}`.
  Response headers `Cache-Control: no-cache`, `Connection: keep-alive`,
  `X-Accel-Buffering: no`; media type `text/event-stream`.
  - Legacy origin: `construction_plan_service.py:725-885`;
    `app/api/v2/endpoints/aeroplane_construction_plans.py:96-133`
  - Definition of done: a contract test asserts the three event names, the
    payload keys and all three headers.
  - Confidence: 🟢

- [ ] **T-22 — Arm the display hook per execution, not per process.**
  Legacy behaviour sets a **module-global** callback plus
  `os.environ["DISPLAY_CONSTRUCTION_STEP"] = "1"`, restoring both in `finally`.
  Reproduce the *effect* — one `shape` frame per `Workplane.display()` call —
  but scope it so two concurrent streams cannot cross-deliver.
  - Legacy origin: `construction_plan_service.py:725-885`;
    `cad_designer/decorators/general_decorators.py:5-21`
  - Definition of done: two concurrent streaming executions each receive only
    their own shapes; neither clears the other's gate. Do **not** reproduce the
    global form.
  - Confidence: 🟢 on the legacy behaviour, 🟡 on the isolation mechanism (it
    depends on T-19's outcome).

- [ ] **T-23 — Starvation timeout and thread join.**
  `queue.Queue.get(timeout=300)` → `event: error {"error": "Execution timed
  out"}`; then `thread.join(timeout=5)` on a daemon worker.
  - Legacy origin: `construction_plan_service.py:872, :885`
  - Definition of done: a stalled execution emits the timeout frame and the
    request completes; the test does not hang.
  - Confidence: 🟢

### Creator catalog

- [ ] **T-24 — Subclass walk with the three skips.**
  Recurse `AbstractShapeCreator.__subclasses__()`; skip
  `ConstructionRootNode`, `ConstructionStepNode`, `JSONStepNode` **but still
  recurse into their subclasses**. Sort by `(category, class_name)`.
  - Legacy origin: `construction_plan_service.py:507-553`
  - Definition of done: the three tree classes never appear in the catalog; a
    Creator that subclasses one of them still does.
  - Confidence: 🟢

- [ ] **T-25 — `_INTERNAL_PARAMS` filtering.**
  Hide `self, loglevel, kwargs, creator_id, wing_config, printer_settings,
  servo_information, engine_information, component_information`.
  - Legacy origin: `construction_plan_service.py:257-268`
  - Definition of done: a Creator taking `wing_config` exposes no such parameter
    in the gallery.
  - Confidence: 🟢

- [ ] **T-26 — `_type_to_str` with generics first.**
  Handle generic aliases before `__name__`, because `list[X].__name__ == "list"`;
  strip the `typing.` and `cad_designer.airplane.types.` prefixes.
  - Legacy origin: `construction_plan_service.py:423-436`
  - Definition of done: `list[ShapeId]` renders as `list[ShapeId]`, not `list`;
    `Optional[float]` carries no `typing.` prefix.
  - Confidence: 🟢

- [ ] **T-27 — `_extract_literal_values`.**
  Unwrap `Literal`, `Optional[Literal]`, `Annotated[Literal]` and nested unions
  into a flat `options` list.
  - Legacy origin: `construction_plan_service.py:450-480`
  - Definition of done: a `WingSides` parameter reports
    `["LEFT", "RIGHT", "BOTH"]`; a non-literal parameter reports `None`.
  - Confidence: 🟢

- [ ] **T-28 — Docstring parsers.**
  `description` = first docstring line; per-parameter descriptions from the
  `Attributes:` block via the regex `(\w+)\s*\([^)]*\)\s*:\s*(.*)`; `outputs`
  from the `Returns:` block with keys like `{id}` / `{id}.cape`;
  `suggested_id` from the class attribute `suggested_creator_id`.
  - Legacy origin: `construction_plan_service.py:330-359, 362-403`
  - Definition of done: a Creator documented per `_creator_template.py`
    round-trips every field; a Creator with no docstring yields `None`
    descriptions rather than raising.
  - Confidence: 🟢

- [ ] **T-29 — `_CATEGORY_MAP` and the platform guard.**
  Category from the module path (`.creator.wing` → `wing`, likewise `fuselage`,
  `cad_operations`, `export_import`, `components`, else `"other"`);
  `ImportError` on `cad_designer` returns `[]`.
  - Legacy origin: `construction_plan_service.py:406-420, 483-504` (ADR 0017)
  - Definition of done: with `cad_designer` unimportable the route answers
    `200 []`, never a 500 or a 503.
  - Confidence: 🟢

### Construction parts

- [ ] **T-30 — Upload validation.**
  Empty → 422; `len > 52_428_800` →
  `ConflictError(details={"reason": "file_too_large"})` mapped to **413**;
  suffix ∉ `{.step, .stp, .stl}` → 422.
  - Legacy origin: `construction_part_service.py:38-41, 119-124`;
    `app/api/v2/endpoints/aeroplane/construction_parts.py:44-63`
  - Definition of done: each of the three rejections is covered by a test
    asserting the exact status code, including the 413 marker path.
  - Confidence: 🟢

- [ ] **T-31 — Two-phase upload.**
  Insert the row, `db.flush()` for the id, write to
  `tmp/construction_parts/{aeroplane_id}/{part_id}_{uuid4().hex[:8]}{ext}`,
  then extract geometry.
  - Legacy origin: `construction_part_service.py` (`create_part`, `_store_file`)
  - Definition of done: two uploads of byte-identical files produce two distinct
    paths; the stored `file_path` matches the file on disk.
  - Confidence: 🟢

- [ ] **T-32 — `_extract_geometry` with individual guards.**
  All-`None` when `cad_available()` is false **or** the format is not STEP;
  otherwise `Volume()`, `Area()` and `BoundingBox()` each wrapped separately.
  - Legacy origin: `construction_part_service.py:144-198`
  - Definition of done: an STL upload stores null geometry and still returns
    201; a STEP whose `Volume()` raises still yields an area and a bounding box.
  - Confidence: 🟢

- [ ] **T-33 — Aeroplane-scoped reads.**
  `_get_part_or_404` filters on `id` **and** `aeroplane_id`.
  - Legacy origin: `construction_part_service.py:44-60`
  - Definition of done: a valid part id requested under the wrong aeroplane
    returns 404, not 403 and not the row.
  - Confidence: 🟢

- [ ] **T-34 — Lock, unlock and the delete ordering.**
  `PUT .../lock` / `.../unlock` → 200; `DELETE` on a locked part →
  `ConflictError` → 409; otherwise delete the row and unlink the file **before**
  the commit.
  - Legacy origin: `construction_part_service.py:336-339`
  - Definition of done: the 409 path is tested; the unlink-before-commit
    trade-off is retained *and* documented in the code, or replaced by a
    deliberate alternative.
  - Confidence: 🟢

- [ ] **T-35 — Download with STL regeneration, and clean up the temp file.**
  `?format=stl` on a STEP source re-exports via CadQuery; `?format=step` on an
  STL source → 422. Filename `construction_part_{part_id}.{format}`.
  - Legacy origin: `construction_part_service.py:276-280`;
    `aeroplane/construction_parts.py:167-190`
  - Definition of done: the regenerated file is removed after the response is
    sent (legacy leaks it — do **not** reproduce the leak); the 422 path is
    tested.
  - Confidence: 🟢

- [ ] **T-36 — Part metadata update.**
  `ConstructionPartUpdate` accepts only `name` (`min_length=1`),
  `material_component_id` and `thumbnail_url`; file and geometry are never
  updatable.
  - Legacy origin: `app/schemas/construction_part.py:51`
  - Definition of done: a payload containing `file_path` or `volume_mm3` is
    rejected by the schema.
  - Confidence: 🟢

### REST layer

- [ ] **T-37 — The four routers.**
  All routes exactly as listed in [`contracts.md`](contracts.md), including the
  status codes that differ from the module norm: `POST /construction-plans` →
  **201**, `DELETE` routes → **204**, `POST .../execute` → **200**,
  `from-template` and `to-template` → **201**, part upload → **201**.
  - Legacy origin: `construction_plans.py` (294 l.),
    `aeroplane_construction_plans.py` (150 l.),
    `construction_templates.py` (65 l.),
    `aeroplane/construction_parts.py` (218 l.)
  - Definition of done: a contract test asserts every method, path and status
    code in `contracts.md`.
  - Confidence: 🟢

- [ ] **T-38 — Route ordering: `/creators` before `/{plan_id}`.**
  `GET /construction-plans/creators` must be declared **before**
  `GET /construction-plans/{plan_id}`, or the literal `"creators"` is captured
  as a plan id.
  - Legacy origin: `construction_plans.py:51-59` (the in-code comment says so)
  - Definition of done: a test pins the ordering by calling `/creators` and
    asserting a list, not a 422 int-parse failure.
  - Confidence: 🟢

- [ ] **T-39 — Unify the error contract.**
  The three plan routers each define a local `_handle_service_error` producing a
  bare `{"detail": …}` body with a `status_map` of only
  `{NotFoundError: 404, ValidationError: 422, InternalError: 500}` — so a
  `ConflictError` becomes a **500**. The parts router has a fuller mapping
  including 409 and 413, still with a `detail` body. Neither matches the
  `{"error": {...}}` envelope of `_raise_http_from_domain`.
  - Legacy origin: `construction_plans.py:37-47`,
    `aeroplane_construction_plans.py:26-36`,
    `construction_templates.py:23-33`,
    `aeroplane/construction_parts.py:44-63`
  - Definition of done: one shared mapping including `ConflictError` → 409 and
    the 413 marker; one envelope shape across the API. Do **not** reproduce the
    `ConflictError` fall-through.
  - Confidence: 🟢 on the defect, 🔴 on which envelope wins (see § Pending Gaps).

## Test Tasks

- [ ] **TT-01 — Happy path:** create a template, instantiate it against an
      aeroplane, execute the resulting plan, and assert `status == "success"`
      with a populated `execution_id` and at least one `shape_key`.
- [ ] **TT-02 — Failure:** executing a template with no aeroplane in the plan
      **or** the request returns 422 and creates no artefact directory.
- [ ] **TT-03 — Deep-copy independence:** mutating an instantiated plan's
      `tree_json` leaves the source template byte-identical, and vice versa.
- [ ] **TT-04 — Legacy migration:** a `ConstructionStepNode` root becomes a
      `ConstructionRootNode` with the `creator` key removed, and the change
      persists.
- [ ] **TT-05 — Thin validation:** a root missing `$TYPE` is rejected at write
      time (422); a root whose *child* references an unknown `$TYPE` is accepted
      at write time and fails at execution with
      `"Failed to decode construction plan"`.
- [ ] **TT-06 — `step_count` parity:** the dict-successor and list-successor
      forms of the same tree report the same count.
- [ ] **TT-07 — Export-path rewriting:** a relative `file_path` lands under
      `<artifact_dir>/`, the directory is created, an absolute path is left
      alone, and the stored `tree_json` is unchanged afterwards.
- [ ] **TT-08 — Template run is destructive:** two template executions leave
      exactly one directory under `_template_runs/{plan_id}`; two plan
      executions leave two.
- [ ] **TT-09 — Millimetre conversion:** a wing with DB chord `0.25` reaches the
      Creator as `250.0`.
- [ ] **TT-10 — Dropped wing is reported:** with one wing failing conversion the
      execution still succeeds **and** the result carries a warning naming that
      wing (the target behaviour, not the legacy silent form).
- [ ] **TT-11 — Printer settings:** with no `printer_settings` component the
      execution uses `0.24 / 0.42 / 0.075`; with one, its `specs` values win.
- [ ] **TT-12 — Failing Creator:** returns HTTP 200 with `status == "error"` and
      populated `error`, `duration_ms`, `artifact_dir`, `execution_id`.
- [ ] **TT-13 — Tessellation is best-effort:** with `tessellate_group` patched to
      raise, the execution still reports success and `tessellation is None`.
- [ ] **TT-14 — SSE contract:** the three event names, their payload keys, and
      the `Cache-Control` / `Connection` / `X-Accel-Buffering` headers.
- [ ] **TT-15 — SSE shape count:** a Creator calling `display()` twice produces
      exactly two `shape` frames before `complete`.
- [ ] **TT-16 — SSE starvation:** a stalled execution emits
      `{"error": "Execution timed out"}` and the test completes without hanging.
- [ ] **TT-17 — Concurrent streams do not cross-deliver** (the target behaviour;
      the legacy globals fail this test by construction).
- [ ] **TT-18 — Catalog skips the three tree classes** but still surfaces a
      Creator subclassing one of them.
- [ ] **TT-19 — Catalog types:** `list[ShapeId]` keeps its subscript;
      `WingSides` reports `["LEFT","RIGHT","BOTH"]`; no `typing.` or
      `cad_designer.airplane.types.` prefixes leak.
- [ ] **TT-20 — Catalog platform guard:** with `cad_designer` unimportable the
      route answers `200 []`.
- [ ] **TT-21 — Route ordering:** `GET /construction-plans/creators` returns the
      catalog, not a plan-id parse error.
- [ ] **TT-22 — Upload matrix:** empty → 422, 60 MB → 413, `.iges` → 422,
      valid `.step` → 201.
- [ ] **TT-23 — Geometry extraction:** STEP populates volume/area/bbox; STL
      leaves all three null; a raising `Volume()` still yields area and bbox.
- [ ] **TT-24 — Part scoping:** a part id from another aeroplane returns 404.
- [ ] **TT-25 — Lock semantics:** `DELETE` on a locked part → 409; after
      `unlock` → 204 and the file is gone from disk.
- [ ] **TT-26 — Download matrix:** STEP source + `format=stl` → an STL and **no
      leaked temp file**; STL source + `format=step` → 422.
- [ ] **TT-27 — Error envelope:** a `ConflictError` raised from a plan route maps
      to 409, not 500 (the legacy code fails this test).

## Data Migration Tasks

- [ ] **TM-01 — Repair `construction_plans.aeroplane_id`.** The column is a
      `String` FK against the `Integer` `aeroplanes.id`, with no `ON DELETE`.
      Decide the target (integer `id` or public `uuid`), migrate existing values
      accordingly, and add the delete behaviour. Until then the schema is
      SQLite-only. 🔴
- [ ] **TM-02 — Add a foreign key to `construction_parts.aeroplane_id`** (or a
      documented reaping job). Existing rows must be checked for orphans first —
      there is no constraint today, so dangling `aeroplane_id` values are
      possible, and each orphan row also owns a file under
      `tmp/construction_parts/`. 🔴
- [ ] **TM-03 — Run `_migrate_tree_json` once as an Alembic data migration**
      over every `construction_plans` row whose `tree_json["$TYPE"]` is
      `ConstructionStepNode`, then delete the read-path migration. Record the
      count of rewritten rows in the migration output, since the lazy path
      leaves no audit trail. 🟡
- [ ] **TM-04 — Relocate construction-part files under `ARTIFACTS_BASE_DIR`**
      (or explicitly ratify `tmp/construction_parts/` as a second root).
      Migrating means moving files **and** rewriting every `file_path` — 🟡 part of the `Q-CP-9 ②` migration.
- [ ] **TM-05 — Sweep orphaned artefact directories** left by failed executions:
      the directory is created before `create_shape` runs, so a failed run is
      indistinguishable from a successful one on disk. Decide a retention
      policy. 🟡

## Suggested Order

1. **T-01 → T-04** first — the two tables. T-02 and T-04 are 🔴 decisions that
   change the schema, so settling them before any service code is written avoids
   a second migration.
2. **T-05 → T-09** next: plan CRUD is the substrate everything else manipulates,
   and T-09's migration decision affects whether `get_plan` may write at all.
3. **T-37 → T-39** can start in parallel with step 2 — the REST layer is thin.
   T-38 (route ordering) is a one-line constraint that is expensive to discover
   later; T-39 should be settled before any route is written, because it changes
   every error assertion in the suite.
4. **T-19 blocks T-18, T-20, T-21 and T-22.** The execution isolation decision
   determines whether `create_shape()` runs in-process, in a thread or in the
   process pool, and the streaming design depends on it. Do not start the
   execution slice before it is answered.
5. **T-10 → T-16** — the execution setup chain, in order: T-10 blocks T-11
   (no aeroplane, no directory), T-11 blocks T-15 (no directory, nothing to
   rewrite into), T-12 and T-14 feed T-16. T-13 and T-17 are behaviour changes
   layered on top.
6. **T-18 → T-20** — running and post-processing, then **T-21 → T-23** for the
   streaming variant.
7. **T-24 → T-29** — the Creator catalog, fully independent of execution and
   parallelisable with steps 4–6. T-26 and T-27 block T-24's output shape.
8. **T-30 → T-36** — construction parts, independent of everything above; only
   T-03/T-04 gate it.

## Pending Gaps

- **Should plan execution move into the CAD process pool?** ADR 0005 says OCCT
  must run in a spawned process because it is not thread-safe; `execute_plan`
  runs it on the request thread and `execute_plan_streaming` on a daemon thread.
  One of the two positions is wrong, and the answer determines the whole
  execution and streaming design (T-19, T-22).
- **Where should `servo_information`, `engine_information` and
  `component_information` come from?** All three are hard-coded empty at both
  call sites, making `ServoImporterCreator`, `ComponentImporterCreator` and
  `EngineMountShapeCreator` unreachable through the REST path (T-17).
- **Which column is `construction_plans.aeroplane_id` meant to reference —
  `aeroplanes.id` (Integer) or `aeroplanes.uuid` (String)?** The current
  `String` → `Integer` FK is only valid under SQLite's dynamic typing (T-02,
  TM-01).
- **Is orphaning construction parts on aeroplane delete acceptable?** There is no
  FK and no cleanup, so both rows and files survive their aeroplane (T-04,
  TM-02).
- **May the read-path `_migrate_tree_json` be dropped after a one-off data
  migration**, or are plans still arriving with legacy roots from an external
  source? Today it rewrites on **every** read with no audit trail (T-09, TM-03).
- **Which HTTP error envelope is canonical?** The plan routers answer
  `{"detail": …}`; the aeroplane routers answer `{"error": {...}}`. Until this is
  settled a client cannot parse errors uniformly (T-39).
- **Should a `ConflictError` from a plan route be a 409?** Today it falls through
  the local `status_map` and becomes a 500. Latent — no plan path raises it yet —
  but it forecloses any future conflict semantics such as "this plan is already
  executing" (T-39).
- **Should a partially converted aircraft fail the execution or warn?** Today it
  does neither visibly: the wing is dropped and only a log line records it
  (T-13).
- **Should construction-part files live under `ARTIFACTS_BASE_DIR`?** They are
  the only artefact class stored outside it, and therefore outside the
  traversal-guarded tree (TM-04).
- **Who cleans up the STL regeneration temp files?** Every download of an STL
  from a STEP source leaks one `mkstemp` file (T-35).
- **Should a plan record the template it came from?** BR-69 makes divergence
  deliberate, but with no back-link a template fix cannot be propagated and its
  instances cannot be found.
- **Is `material_component_id` meant to be constrained to `material`
  components?** The FK points at `components.id` generally; only the frontend
  filters the dropdown.
- **What is the retention policy for artefact directories?** They are created
  before execution and left behind on failure, with no marker distinguishing a
  failed run from a successful one (TM-05).
