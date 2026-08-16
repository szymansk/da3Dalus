# construction-plans

> Module-level specification. Focuses on WHAT the module does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: construction-plans,
> `_reversa_sdd/data-dictionary.md` §Module: construction-plans,
> `_reversa_sdd/domain.md` §2.10, `_reversa_sdd/state-machines.md` §6,
> `_reversa_sdd/flowcharts/construction-plans.md`.

## Overview

`construction-plans` owns the **reusable JSON build recipe** and everything that
happens when one is run: templates and their aeroplane-bound instances, decoding
the stored tree into a live Creator graph, executing it against a real aircraft
with artefact capture, streaming shapes over SSE while it builds, the reflection
catalog that fills the frontend Creator gallery, and — a second, unrelated
concept sharing the word "construction" — the per-aeroplane store of uploaded
STEP/STL **construction parts**. 🟢

## Responsibilities

- CRUD for `construction_plans` rows, discriminated by `plan_type`
  (`"template"` | `"plan"`), with deliberately thin write-time validation. 🟢
- Instantiate a template into an aeroplane-bound plan, and lift a plan back into
  a template — both by deep copy, with no lineage recorded. 🟢
- Execute a plan: resolve the effective aeroplane, allocate an artefact
  directory, build the millimetre `wing_config` map, load printer settings,
  rewrite relative export paths into the artefact directory, decode the tree
  with injected topology kwargs, run it, and best-effort tessellate the result. 🟢
- Stream the same execution as Server-Sent Events, emitting one `shape` frame
  per `Workplane.display()` call inside any Creator. 🟢
- Reflect over the `AbstractShapeCreator` subclass tree to produce the Creator
  catalog (parameters, types, literal options, docstring-derived descriptions and
  outputs, category, suggested id). 🟢
- Serve the artefact browsing / download / delete routes over the directories
  `artifact_service` maintains. 🟢
- Own the construction-part lifecycle: upload with size and suffix limits, STEP
  geometry extraction, lock/unlock, download with on-the-fly STL regeneration,
  and aeroplane-scoped access. 🟢

**Explicitly NOT this module's responsibility:**

- **The spar-plan *solver math* is a different thing that shares only the word "plan".**
  The `spar_solver` / `spar_sizing` / `section_geometry` computation — section
  modulus formulas, station sampling, telescoping/greedy fit — is owned by
  **`wing-design`** (specified in `_reversa_sdd/wing-design/spar-sizing/`) and is
  NOT restated here. It produces a *structural* result with no `construction_plans`
  row, no `tree_json`, no artefact directory and no Creator.
  **Boundary note (gh split):** the *post-solve* half — `spar_plan_service`
  (mm→m response assembly, stock snapping) and `spar_insert_service` (dry-run +
  commit of `wing_xsec_spares` rows, pre-commit snapshot, telescoping segment
  split) — IS owned here and is specified in the nested slice
  `_reversa_sdd/construction-plans/spar-plan/`, which cross-references
  `wing-design/spar-sizing/` for the underlying math rather than duplicating it.
  (see `flowcharts/construction-plans.md` §1, "three different things called
  construction"). 🟢
- The `$TYPE` encoder/decoder internals and the `AbstractShapeCreator` base
  contract → **`cad-designer-topology`** (frozen, ADR 0002). This module is a
  *consumer* of both.
- The artefact directory *storage semantics* (`_ensure_within_base`, execution
  ids, `_template_runs` wiping, zip building) → **`cad-generation`**, which owns
  `artifact_service`. This module owns only the REST routes over it.
- The CAD process pool and the wing tessellation/export tasks →
  **`cad-generation`**.
- The component tree (`component_tree.construction_part_id` is a foreign key
  *into* this module's table, but the tree itself) → **`aeroplane-core`**.
- The `workbench/construction-plans` page and the `three-cad-viewer` embedding →
  **`frontend-workbench`**.

## Business Rules

### Plan and template model

- **BR-69 — A plan and its template diverge immediately.** 🟢
  `instantiate_template` (`construction_plan_service.py:207-232`) validates
  `plan_type == "template"`, verifies the aeroplane exists, and `copy.deepcopy`s
  `tree_json` into a new row named `"{template.name} — Plan"`.
  `to_template` (l.235-251) is the mirror image, naming the result
  `"{plan.name} — Template"`. There is **no version chain and no back-link** —
  after instantiation the two rows evolve completely independently.
- **BR-CP1 — `plan_type` is the only discriminator; there is no status column
  and no lifecycle.** 🟢 A `"template"` has `aeroplane_id IS NULL` and is
  reusable; a `"plan"` is bound to exactly one aeroplane. Neither column is an
  enum or carries a check constraint — both are free text
  (`app/models/construction_plan.py:11`). The only observable "state" is the set
  of artefact directories an execution leaves behind
  (`state-machines.md` §6).
- **BR-70 — Plan validation is deliberately thin.** 🟢 `_validate_tree_json`
  (l.72-81) requires only a `$TYPE` and a `creator_id` at the **root**;
  everything below it fails at decode time, inside `execute_plan`. A structurally
  broken plan is therefore storable and only fails when it is run.
- **BR-CP2 — Execution is not idempotent for plans and destructive for
  templates.** 🟢 Every plan run creates a fresh
  `<aeroplane_id>/<plan_id>/<execution_id>/` directory and they accumulate; a
  template run goes to `_template_runs/<plan_id>/<execution_id>/` and
  `artifact_service.create_template_execution_dir` **`shutil.rmtree`s the
  previous run first**, so at most one template execution survives.
- **BR-71 — Renaming or deleting a Creator invalidates every stored plan that
  references it.** 🟢 The decoder resolves `$TYPE` with `getattr(module, name)`,
  so a missing class is an `AttributeError` at execution time, not at write time.
  Nine removed Creator classes are still referenced by three shipped plan JSONs
  under `components/constructions/` — latent, because nothing under `app/` reads
  that directory (detail in `cad-designer-topology`).
- 🔴 **BR-CP3 — The stored root shape is silently migrated on every read.**
  `_migrate_tree_json` (l.113-133) rewrites a root whose `$TYPE` is
  `ConstructionStepNode` into `ConstructionRootNode`, drops the `creator` key,
  calls `flag_modified` on the JSON column and flushes — and it runs inside
  `get_plan`, i.e. on **every** read of every plan. There is no audit trail, no
  version marker and no way to tell a migrated row from an originally correct
  one. Documented as real behaviour; a re-implementation should do this once, as
  a data migration.

### Execution

- **BR-CP4 — The effective aeroplane is resolved before anything else.** 🟢
  `effective_aeroplane_id = plan.aeroplane_id or request.aeroplane_id`
  (`execute_plan`, l.616-722, step 1). A **template** with neither raises
  `ValidationError` → **422**. A bound plan ignores the request body's value
  only in the sense that its own `aeroplane_id` wins.
- **BR-CP5 — The execution world is millimetres.** 🟢
  `wing_config = {wing.name: wing_model_to_wing_config(wing, scale=1000.0)}`
  (step 3) — the metre database is converted at the boundary, exactly as
  `cad-generation`'s worker does (ADR 0001).
- 🔴 **BR-CP6 — A wing that fails conversion is silently dropped.** 🟢 CONFIRMED
  behaviour / 🟡 a dropped wing becomes a `DesignWarning` (`Q-CP-3`). A per-wing `wing_model_to_wing_config` failure logs a
  warning and removes that wing from the map (l.650-654); the plan then executes
  against a **partial aircraft** and the `ExecutionResult` says nothing about it.
  This sits directly against ADR 0012 ("design warnings instead of silent
  fallbacks").
- **BR-CP7 — Printer settings come from the components table, with a fixed
  fallback.** 🟢 `_load_printer_settings` (l.984-1013) takes the **first**
  `components` row whose `component_type == "printer_settings"` and reads
  `layer_height`, `wall_thickness`, `rel_gap_wall_thickness` from its `specs`
  JSON; absent any such row it falls back to `0.24 / 0.42 / 0.075` mm — the same
  defaults as `Printer3dSettings` itself.
- **BR-CP8 — Relative export paths are rewritten into the artefact directory,
  and the directory is created.** 🟢 `_rewrite_export_paths` (l.567-613)
  deep-copies the tree and, for
  `_EXPORT_CREATOR_TYPES = {ExportToStlCreator, ExportToStepCreator,
  ExportToIgesCreator, ExportTo3mfCreator}` (l.559-564), maps a **relative**
  `file_path` to `<artifact_dir>/<file_path>` and `mkdir`s it — `file_path` is a
  *directory* for exporters, not a file. Both the nested (`node.creator`) and the
  flat node shape are handled. The in-code comment records the reason: the
  executor no longer `chdir`s, so without the rewrite every export would land in
  the project root.
- **BR-CP9 — Topology objects reach a running plan only as decoder kwargs, and
  three of the five slots are hard-coded empty.** 🟢 The decode call injects
  `wing_config`, `printer_settings`, `servo_information={}`,
  `engine_information=None`, `component_information=None` (l.670-678). A decode
  failure is wrapped as
  `ValidationError("Failed to decode construction plan: …")` → **422**.
  Consequence 🟢 (resolved by `Q-CP-2` — the component tree and COTS library supply them): `ServoImporterCreator`, `ComponentImporterCreator` and
  `EngineMountShapeCreator` can never receive real data through the REST path.
- **BR-CP10 — Tessellation of the result is best-effort and never fails the
  execution.** 🟢 `_tessellate_shapes` (l.930-981) collects every value with a
  `.val` attribute, takes `s.val().Solids()` per shape (individual failures
  skipped), builds one `Compound.makeCompound` → `Workplane`, then
  `to_ocpgroup(names=["result"], colors=["#FF8400"])` and
  `tessellate_group({"deviation": 0.1, "angular_tolerance": 0.2})`. Any exception
  logs a warning and returns `None`, leaving `ExecutionResult.tessellation` null.
- 🟢 **BR-CP11 — plan execution routes through the same CAD process pool** (`Q-CP-1`, maintainer-answered). Previously it ran in the request process, contradicting
  ADR 0005.** 🟢 CONFIRMED (both code paths read) / 🔴 on resolution.
  `cad_service`'s module docstring states that CAD **must** run in a separate
  process because OCCT is not thread-safe and `.intersect().clean()` hangs
  indefinitely in a worker thread. Yet `execute_plan` (step 7) calls
  `root_node.create_shape()` **on the FastAPI request thread**, and
  `execute_plan_streaming` runs it on a `threading.Thread` — both driving the
  same CadQuery/OCCT stack. Either the process isolation is unnecessary or plan
  execution is exposed to the documented hang. This must be decided before
  re-implementation.

### Streaming

- **BR-CP12 — Streaming is armed by two process-global switches.** 🟢
  `set_display_callback(on_display)` (module global) plus
  `os.environ["DISPLAY_CONSTRUCTION_STEP"] = "1"` arm the
  `@conditional_execute`-gated `Workplane.display` plugin, so **every
  `display()` call inside any Creator emits a `shape` event**. The `finally`
  block restores the previous env-var value and clears the callback.
  🟡 Neither switch is per-execution: two concurrent streams — or a stream
  concurrent with a non-streaming execution — cross-deliver shape events and can
  re-enable or disable each other's display gate. There is no lock and no
  per-execution context.
- **BR-CP13 — The stream has a hard starvation timeout.** 🟢 The generator
  drains a `queue.Queue` with `timeout=300` s; on starvation it emits
  `event: error {"error": "Execution timed out"}` and then `thread.join(timeout=5)`
  (`construction_plan_service.py:872, :885`). The worker thread is a daemon, so a
  hung OCCT call is abandoned rather than joined.

### Creator catalog

- **BR-CP14 — The catalog is pure reflection over the live subclass tree.** 🟢
  `_collect_creators` (l.507-553) walks `AbstractShapeCreator.__subclasses__()`
  recursively and **skips but still recurses through** `ConstructionRootNode`,
  `ConstructionStepNode` and `JSONStepNode`. Results are sorted by
  `(category, class_name)`. Consequently a Creator that is not imported by its
  subpackage `__init__.py` is invisible here **and** undecodable in a plan — the
  same registration requirement, observed from two sides.
- **BR-CP15 — Internal constructor parameters are hidden from the gallery.** 🟢
  `_INTERNAL_PARAMS = {self, loglevel, kwargs, creator_id, wing_config,
  printer_settings, servo_information, engine_information, component_information}`
  (l.257-268) — the runtime-injected decoder kwargs plus the framework's own
  arguments.
- **BR-CP16 — Generic annotations are resolved before `__name__`.** 🟢
  `_type_to_str` (l.423-436) handles generics **first**, because
  `list[X].__name__ == "list"` loses the subscript; the `typing.` and
  `cad_designer.airplane.types.` prefixes are then stripped. `options` come from
  `_extract_literal_values` (l.450-480), which unwraps `Literal`,
  `Optional[Literal]`, `Annotated[Literal]` and nested unions.
- **BR-CP17 — Human-readable metadata is parsed out of docstrings.** 🟢
  `description` is the first line of the class docstring; per-parameter
  descriptions come from the `Attributes:` block via
  `_parse_docstring_attributes` (l.330-359, regex
  `(\w+)\s*\([^)]*\)\s*:\s*(.*)`); `outputs` come from the `Returns:` block via
  `_parse_docstring_returns` (l.362-403), with keys such as `{id}` and
  `{id}.cape`; `suggested_id` is the class attribute `suggested_creator_id`.
  `category` is derived from the module path by `_CATEGORY_MAP` (l.406-420):
  `.creator.wing` → `wing`, likewise `fuselage`, `cad_operations`,
  `export_import`, `components`, else `"other"`.
- **BR-CP18 — An absent CAD kernel yields an empty catalog, never an error.** 🟢
  `ImportError` on `cad_designer` returns `[]` (l.483-504) — the
  `linux/aarch64` platform guard of ADR 0017. The gallery is empty; the endpoint
  still answers 200.

### Construction parts

- **BR-72 — Upload limits are fixed constants.** 🟢
  `ALLOWED_SUFFIXES = {".step", ".stp", ".stl"}`,
  `MAX_FILE_SIZE_BYTES = 52_428_800` (50 MB),
  `ALLOWED_DOWNLOAD_FORMATS = {"step", "stl"}`,
  `STORAGE_ROOT = Path("tmp") / "construction_parts"`
  (`construction_part_service.py:38-41`). An empty file or a disallowed suffix is
  a `ValidationError` → 422; an oversize upload raises
  `ConflictError(details={"reason": "file_too_large"})`, which the endpoint maps
  to **413** (l.119-124) — the `details.reason` marker exists solely to
  distinguish it from an ordinary 409.
- **BR-CP19 — Upload is two-phase.** 🟢 Insert the row, `db.flush()` to obtain
  the id, then write the file to
  `tmp/construction_parts/{aeroplane_id}/{part_id}_{uuid4().hex[:8]}{ext}` and
  extract geometry. The generated suffix means two uploads of the same file never
  collide.
- **BR-CP20 — Geometry metadata exists only for STEP with CadQuery present.** 🟢
  `_extract_geometry` (l.144-198) returns all-`None` when `cad_available()` is
  false **or** the format is not STEP — an STL is a triangle soup and its volume
  needs a mesh library (documented MVP limitation). When it does run, `Volume()`,
  `Area()` and `BoundingBox()` are each guarded individually, so one failing call
  does not null the others.
- **BR-CP21 — Every part read is aeroplane-scoped.** 🟢 `_get_part_or_404`
  (l.44-60) filters on both `id` **and** `aeroplane_id`, so a part id belonging
  to another aeroplane cannot be reached by guessing — it answers 404, not 403.
- **BR-CP22 — A locked part cannot be deleted, and the file is unlinked before
  the commit.** 🟢 `delete_part` raises `ConflictError` → **409** when `locked`;
  otherwise it `db.delete`s the row and `os.unlink`s the file **before**
  `get_db()` commits. The trade-off is spelled out in a comment (l.336-339): a
  rollback after the unlink leaves a row pointing at a missing file.
- **BR-CP23 — STL is regenerated on demand; STEP is not.** 🟢
  `GET .../{part_id}/file?format=stl` on a STEP source re-exports via CadQuery
  into a `tempfile.mkstemp` file; `?format=step` on an STL source raises
  `ValidationError` → 422, because the conversion is not lossless.
  🔴 The regenerated temp file is served and **never cleaned up** (l.276-280).

### Transport and errors

- 🔴 **BR-CP24 — The plan routers use a different error envelope from the
  aeroplane routers, and drop `ConflictError` on the floor.** 🟢 CONFIRMED.
  `construction_plans.py:37-47`, `aeroplane_construction_plans.py:26-36` and
  `construction_templates.py:23-33` each define a local `_handle_service_error`
  that raises `HTTPException(status_code=code, detail=str(exc.message))` — a bare
  `{"detail": "…"}` body, **not** the
  `{"error": {"code", "message", "details"}}` envelope of
  `_raise_http_from_domain`. Their `status_map` contains only `NotFoundError`
  → 404, `ValidationError` → 422 and `InternalError` → 500; **`ConflictError` is
  absent**, so it falls through `status_map.get(..., 500)` and surfaces as a
  **500**. The construction-parts router (`aeroplane/construction_parts.py:44-63`)
  has its own, richer mapping including 409 and 413 — but still with a `detail`
  body.
- **BR-68 — Every artefact path is traversal-guarded.** 🟢 The artefact routes
  delegate to `artifact_service`, which resolves then `relative_to(base)` and
  additionally rejects symlinks on the single-file read. Storage semantics are
  specified in `cad-generation`.

## Design principle — minimise part count 🟢

**Every joint is a weak point in the wing.** Part count is therefore kept deliberately low
as a **structural** goal, not as a convenience (maintainer, 2026-08-16). This bounds the
component tree from above by intent: measured over all 135 tree-bearing rows, 46 carry 3
nodes and the maximum is 10.

**The consequence for this module's output model:** the tree holds the *wing*; the
manufacturing file holds the *pieces*. A wooden rib construction produces **one DXF with
many ribs nested onto a board** for the laser cutter, exactly as a printed wing produces
STL/STEP carrying many parts on one plate. Ribs are never tree nodes.

🟢 **DXF is correctly absent — it is not a gap.** The exporter enum offers
`stl`/`step`/`iges`/`3mf` (and `amf`, removed by `Q-CG-1`) and there is no DXF writer
anywhere. **The reason is ordering, not omission:** no Creator produces rib wings yet, so
there is nothing to nest onto a board and nothing to write. DXF arrives *with* that
Creator, not before it — adding the format first would produce a writer with no producer,
which is exactly the inert state `P-DEAD-0` forbids.

`ezdxf` is already available transitively (`cad_designer/__init__.py:17`), so the
capability is reachable when the Creator lands.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | List construction plans, optionally filtered by `plan_type` | Must | `GET /construction-plans?plan_type=template` → 200, only templates |
| RF-02 | Create a plan or template from a `tree_json` payload | Must | `POST /construction-plans` → **201**; a payload without a root `$TYPE` → 422 |
| RF-03 | Read, update and delete a plan by integer id | Must | `GET` → 200, `PUT` → 200, `DELETE` → **204**; unknown id → 404 |
| RF-04 | Report `step_count` on list views by recursively counting successor nodes | Should | A three-node tree reports `step_count == 2` (the root itself is not counted) |
| RF-05 | Instantiate a template into an aeroplane-bound plan by deep copy | Must | `POST /aeroplanes/{id}/construction-plans/from-template/{tid}` → **201**, name `"{template.name} — Plan"`, `plan_type == "plan"`; a source whose `plan_type != "template"` → 422 |
| RF-06 | Lift a plan back into a template by deep copy | Should | `POST .../{plan_id}/to-template` → **201**, name `"{plan.name} — Template"` |
| RF-07 | Migrate a legacy `ConstructionStepNode` root to `ConstructionRootNode` on read | Must | Reading a legacy plan returns a root whose `$TYPE` is `ConstructionRootNode` and whose `creator` key is gone |
| RF-08 | Execute a plan against an aeroplane, producing shapes and artefacts | Must | `POST /construction-plans/{id}/execute` → 200 with `status == "success"`, non-empty `shape_keys`, and an `execution_id` |
| RF-09 | Reject executing a template with no aeroplane in the plan or the request | Must | `POST` a template `/execute` with an empty body → 422 |
| RF-10 | Allocate a per-execution artefact directory, wiping the previous one for templates | Must | Two plan runs yield two directories; two template runs yield one |
| RF-11 | Rewrite relative exporter `file_path` values into the artefact directory and create it | Must | A plan whose `ExportToStepCreator.file_path` is `"out"` writes into `<artifact_dir>/out/`, not the project root |
| RF-12 | Convert every wing to a millimetre `WingConfiguration` before decoding | Must | The decoded tree receives `wing_config` keyed by wing name at `scale = 1000.0` |
| RF-13 | Load printer settings from the components table with a documented fallback | Should | With no `printer_settings` component the execution uses `0.24 / 0.42 / 0.075` |
| RF-14 | Return a structured `ExecutionResult` on failure instead of raising | Must | A Creator that raises yields `status == "error"` with `error`, `duration_ms`, `artifact_dir`, `execution_id` — HTTP 200 |
| RF-15 | Stream an execution as SSE with `shape` / `complete` / `error` frames | Should | `GET .../execute-stream` returns `text/event-stream` with `X-Accel-Buffering: no`; one `shape` frame per `display()` call |
| RF-16 | Terminate a starved stream after 300 s with an error frame | Should | A stalled execution emits `event: error {"error": "Execution timed out"}` |
| RF-17 | Serve the Creator catalog with parameters, types, options, outputs and category | Must | `GET /construction-plans/creators` → 200, sorted by `(category, class_name)`; a `Literal` parameter carries its `options` |
| RF-18 | Answer the catalog with an empty list when CadQuery is unavailable | Must | With `cad_designer` unimportable the route still answers 200 with `[]` |
| RF-19 | List, download and delete artefacts per execution | Must | `GET .../artifacts` → 200; `GET .../artifacts/{eid}/zip` → a zip; `DELETE .../artifacts/{eid}` → **204** |
| RF-20 | Upload a construction part with suffix and size validation | Must | A 60 MB file → **413** with `details.reason == "file_too_large"`; a `.iges` file → 422 |
| RF-21 | Extract STEP geometry metadata at upload time | Should | A STEP upload returns non-null `volume_mm3`, `area_mm2`, `bbox_*_mm`; an STL upload returns them all null |
| RF-22 | Scope every part read to its aeroplane | Must | A part id from another aeroplane → 404 |
| RF-23 | Lock and unlock a part, blocking deletion while locked | Must | `DELETE` a locked part → 409; after `PUT .../unlock` → **204** |
| RF-24 | Download a part as STEP or STL, regenerating STL from STEP on demand | Should | `?format=stl` on a STEP source returns an STL; `?format=step` on an STL source → 422 |
| RF-25 | Update a part's name, material and thumbnail, but never its file or geometry | Could | `PUT .../{part_id}` with a `file_path` field is rejected by the schema |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Portability | The Creator catalog degrades to an empty list rather than a 500 when `cad_designer` cannot be imported | `construction_plan_service.py:483-504` (ADR 0017) | 🟢 |
| Portability | A construction part uploads successfully on a platform without CadQuery, with null geometry | `construction_part_service.py:144-198` | 🟢 |
| Robustness | Result tessellation is best-effort; an exception logs and returns `None` rather than failing the execution | `construction_plan_service.py:930-981` | 🟢 |
| Robustness | Execution failure is a structured `ExecutionResult(status="error")`, not an HTTP 5xx | `construction_plan_service.py:616-722` | 🟢 |
| Availability | The SSE generator cannot block forever — 300 s queue starvation timeout, 5 s thread join, daemon worker | `:872, :885` | 🟢 |
| Security | Every artefact path is resolved and confined to the artefact base; the single-file read additionally rejects symlinks | `artifact_service._ensure_within_base`, `get_file_path` | 🟢 |
| Security | Part reads are scoped by `(id, aeroplane_id)` so ids from other aircraft are not enumerable | `construction_part_service.py:44-60` | 🟢 |
| Security | Upload size is capped at 50 MB before the file is written to disk | `construction_part_service.py:39, 119-124` | 🟢 |
| Performance | Export paths are rewritten once, on a deep copy, so the stored tree is never mutated by an execution | `construction_plan_service.py:567-613` | 🟢 |
| Consistency | Deleting a part unlinks the file before the transaction commits — a deliberate, documented trade-off | `construction_part_service.py:336-339` | 🟢 |
| Concurrency | 🟡 **Not met.** Streaming mutates process-global state (display callback + env var) with no lock | `construction_plan_service.py:725-885` | 🟢 |
| Isolation | 🟡 **Not met.** Execution runs OCCT in the request process, against ADR 0005 | `execute_plan` vs `cad_service` docstring | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Template and plan duality

  Scenario: A template is instantiated into a bound plan
    Given a construction plan with plan_type "template" and aeroplane_id null
    And an aeroplane that exists
    When I POST /aeroplanes/{aeroplane_id}/construction-plans/from-template/{template_id}
    Then the response status is 201
    And the new row has plan_type "plan" and the aeroplane's id
    And its name is "{template name} — Plan"
    And its tree_json is a deep copy, so editing it does not change the template

  Scenario: Instantiating a non-template is rejected
    Given a construction plan with plan_type "plan"
    When I POST from-template with that id
    Then the response status is 422

  Scenario: A legacy root is migrated on read
    Given a stored plan whose tree_json root has $TYPE "ConstructionStepNode"
    When I GET that plan
    Then the returned root has $TYPE "ConstructionRootNode"
    And the root no longer carries a "creator" key
    And the change has been persisted

Feature: Plan execution

  Scenario: A bound plan executes and captures artefacts
    Given a plan bound to an aeroplane with at least one wing
    When I POST /construction-plans/{plan_id}/execute
    Then the response status is 200
    And status is "success"
    And shape_keys is not empty
    And artifact_dir and execution_id are populated
    And a second execution creates a second directory

  Scenario: A template execution wipes the previous run
    Given a template that has been executed once
    When I execute it again with an aeroplane_id in the body
    Then only one execution directory exists under _template_runs/{plan_id}

  Scenario: A template without an aeroplane is rejected
    Given a plan with plan_type "template" and aeroplane_id null
    When I POST /construction-plans/{plan_id}/execute with an empty body
    Then the response status is 422

  Scenario: A relative export path lands in the artefact directory
    Given a plan whose ExportToStepCreator has file_path "out"
    When the plan is executed
    Then the directory <artifact_dir>/out exists
    And nothing was written to the project root

  Scenario: A failing Creator returns a structured error, not a 5xx
    Given a plan whose Creator raises during create_shape
    When I execute it
    Then the response status is 200
    And status is "error"
    And error, duration_ms, artifact_dir and execution_id are populated

  Scenario: An undecodable plan is a validation error
    Given a stored plan referencing a $TYPE that no longer exists
    When I execute it
    Then the response status is 422
    And the message starts with "Failed to decode construction plan"

Feature: Streaming execution

  Scenario: Each displayed shape produces an SSE frame
    Given a plan whose Creators call Workplane.display twice
    When I GET .../execute-stream
    Then the media type is text/event-stream
    And the response carries X-Accel-Buffering: no
    And two "shape" events arrive before one "complete" event

  Scenario: A starved stream times out rather than hanging
    Given an execution that produces nothing for 300 seconds
    When the queue starves
    Then an "error" event with "Execution timed out" is emitted
    And the worker thread is joined with a 5 second timeout

Feature: Creator catalog

  Scenario: A Literal parameter exposes its allowed values
    Given a Creator whose __init__ takes wing_side: WingSides
    When I GET /construction-plans/creators
    Then that parameter's options are ["LEFT", "RIGHT", "BOTH"]
    And its type string carries no "cad_designer.airplane.types." prefix

  Scenario: The catalog degrades on a platform without CadQuery
    Given cad_designer cannot be imported
    When I GET /construction-plans/creators
    Then the response status is 200
    And the body is an empty list

Feature: Construction parts

  Scenario: A STEP upload extracts geometry
    Given a valid .step file below 50 MB
    When I POST it to /aeroplanes/{id}/construction-parts
    Then the response status is 201
    And volume_mm3, area_mm2 and bbox_x_mm are populated
    And the file is stored under tmp/construction_parts/{aeroplane_id}/

  Scenario: An oversize upload is rejected with 413
    Given a file larger than 52428800 bytes
    When I upload it
    Then the response status is 413

  Scenario: A locked part cannot be deleted
    Given a construction part with locked true
    When I DELETE it
    Then the response status is 409
    And after PUT .../unlock the DELETE returns 204

  Scenario: A part from another aeroplane is invisible
    Given a part belonging to aeroplane A
    When I GET it under aeroplane B
    Then the response status is 404
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Plan CRUD and the `plan_type` duality (RF-01…RF-06) | Must | The whole module is a store of build recipes; nothing else works without it |
| Legacy root migration (RF-07) | Must | Without it every pre-migration plan fails at decode with a confusing error |
| Plan execution (RF-08…RF-14) | Must | The reason the module exists; the only path from a stored recipe to a manufacturable file |
| Export-path rewriting (RF-11) | Must | Without it exports escape the artefact tree into the project root — a correctness *and* containment failure |
| Millimetre `wing_config` conversion (RF-12) | Must | Wrong by 1000× when omitted (ADR 0001) |
| Creator catalog (RF-17/RF-18) | Must | The frontend plan editor cannot offer a step without it; the empty-list guard is what keeps aarch64 usable |
| Artefact browsing and download (RF-19) | Must | An execution whose output cannot be fetched is worthless |
| Construction-part upload, scoping and locking (RF-20…RF-23) | Must | Directly user-facing; the aeroplane scoping is the module's only access-control mechanism |
| SSE streaming (RF-15/RF-16) | Should | A progress affordance — the non-streaming `/execute` route delivers the same result |
| `step_count` on list views (RF-04) | Should | Presentation metadata for the gallery |
| Printer-settings lookup (RF-13) | Should | Has a documented fallback, so an execution never blocks on it |
| STL regeneration on download (RF-24) | Should | Convenience; the stored source format is always downloadable |
| Part metadata update (RF-25) | Could | Cosmetic fields only — name, material link, thumbnail |
| Injecting real `servo_information` / `engine_information` / `component_information` | **Should** (`Q-CP-2`) | previously **Won't (today)** | Hard-coded empty at both execution call sites, so three Creators are unreachable through REST. Recorded as a 🔴 capability gap, not implemented |
| Template → plan lineage / back-link | **Won't** | Deliberately absent (BR-69); adding it is a design change, not a re-implementation detail |
| Running plan execution in the CAD process pool | **Won't (undecided)** | Contradicts ADR 0005 today (BR-CP11 — 🟢 routed through the CAD process pool, `Q-CP-1`); the resolution is an open decision, so a re-implementation must not silently pick one |
| Fixing the `$TYPE` corpus under `components/constructions/` | Won't (this module) | Owned by `cad-designer-topology`; nothing under `app/` reads that directory |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/construction_plan_service.py` (1 013 l.) | `_count_steps`, `_to_summary`, `_validate_tree_json`, `_migrate_tree_json`, `get_plan`, `list_plans`, `create_plan`, `update_plan`, `delete_plan`, `instantiate_template`, `to_template`, `list_creators`, `_collect_creators`, `_type_to_str`, `_extract_literal_values`, `_parse_docstring_attributes`, `_parse_docstring_returns`, `_rewrite_export_paths`, `execute_plan`, `execute_plan_streaming`, `_tessellate_shapes`, `_load_printer_settings` | 🟢 |
| `app/services/construction_part_service.py` (350 l.) | `_get_part_or_404`, `_validate_upload`, `create_part`, `_store_file`, `_extract_geometry`, `get_part_file`, `update_part`, `set_locked`, `delete_part` | 🟢 |
| `app/api/v2/endpoints/construction_plans.py` (294 l.) | `_handle_service_error`, `list_creators`, `list_plans`, `create_plan`, `get_plan`, `update_plan`, `delete_plan`, `execute_plan`, `list_artifacts`, `list_artifact_files`, `download_execution_zip`, `download_artifact_file`, `delete_artifact_file`, `delete_execution` | 🟢 |
| `app/api/v2/endpoints/aeroplane_construction_plans.py` (150 l.) | `list_aeroplane_plans`, `instantiate_template`, `execute_plan`, `execute_plan_stream`, `plan_to_template` | 🟢 |
| `app/api/v2/endpoints/construction_templates.py` (65 l.) | `list_templates`, `create_template` | 🟢 |
| `app/api/v2/endpoints/aeroplane/construction_parts.py` (218 l.) | `_call`, `list_construction_parts`, `get_construction_part`, `upload_construction_part`, `download_construction_part_file`, `update_construction_part`, `lock_construction_part`, `unlock_construction_part`, `delete_construction_part` | 🟢 |
| `app/models/construction_plan.py` | `ConstructionPlanModel` | 🟢 |
| `app/models/construction_part.py` | `ConstructionPartModel` | 🟢 |
| `app/schemas/construction_plan.py` | `PlanCreate`, `PlanRead`, `PlanSummary`, `InstantiateRequest`, `ToTemplateRequest`, `CreatorParam`, `CreatorOutput`, `CreatorInfo`, `ExecuteRequest`, `ExecutionResult`, `ArtifactFile`, `ArtifactDirectory` | 🟢 |
| `app/schemas/construction_part.py` | `ConstructionPartRead`, `ConstructionPartUpdate`, `ConstructionPartList` | 🟢 |
| `app/services/artifact_service.py` | artefact directories — specified in `cad-generation` | 🟢 cross-reference |
| `cad_designer/airplane/**` | Creator stack + `$TYPE` codec — specified in `cad-designer-topology` (frozen, ADR 0002) | 🟢 cross-reference |
