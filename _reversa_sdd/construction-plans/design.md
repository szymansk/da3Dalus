# construction-plans — Technical Design

> Module-level design. Focuses on HOW the module is built, derived from the
> legacy code. Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Endpoint contracts in full: see [`contracts.md`](contracts.md).
> Behavioural slices: [`plan-template-lifecycle/`](plan-template-lifecycle/),
> [`plan-execution/`](plan-execution/), [`creator-catalog/`](creator-catalog/),
> [`construction-parts/`](construction-parts/).

## Interface

### Plan service — `app/services/construction_plan_service.py` (1 013 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `_count_steps` | `(tree_json: dict)` | `int` | recursive successor count; tolerates **both** the dict-keyed `OrderedDict` form and the list form the frontend emits (l.38-53). The root is not counted |
| `_to_summary` | `(plan)` | `PlanSummary` | attaches `step_count` (l.56-65) |
| `_validate_tree_json` | `(tree_json: dict)` | `None` | raises `ValidationError` unless the root has `$TYPE` **and** `creator_id` (l.72-81) |
| `_migrate_tree_json` | `(plan)` | `None` | rewrites a `ConstructionStepNode` root into `ConstructionRootNode`, drops `creator`, `flag_modified` + flush — runs on **every** `get_plan` (l.113-133) |
| `list_plans` | `(db, plan_type=None)` | `list[PlanSummary]` | optional `plan_type` filter |
| `create_plan` / `update_plan` / `delete_plan` | `(db, …)` | `PlanRead` / `None` | thin CRUD over `ConstructionPlanModel` |
| `instantiate_template` | `(db, template_id, aeroplane_id, name=None)` | `PlanRead` | template → plan, `copy.deepcopy` of the tree (l.207-232) |
| `to_template` | `(db, plan_id, name=None)` | `PlanRead` | plan → template (l.235-251) |
| `list_creators` | `()` | `list[CreatorInfo]` | reflection catalog; `[]` on `ImportError` (l.483-504) |
| `_collect_creators` | `(cls, acc)` | `None` | recursive subclass walk, skipping the three tree classes (l.507-553) |
| `_type_to_str` | `(annotation)` | `str` | generics before `__name__`; strips `typing.` / `cad_designer.airplane.types.` (l.423-436) |
| `_extract_literal_values` | `(annotation)` | `list[str] \| None` | `Literal`, `Optional[Literal]`, `Annotated[Literal]`, nested unions (l.450-480) |
| `_parse_docstring_attributes` | `(docstring)` | `dict[str, str]` | `Attributes:` block, regex `(\w+)\s*\([^)]*\)\s*:\s*(.*)` (l.330-359) |
| `_parse_docstring_returns` | `(docstring)` | `list[CreatorOutput]` | `Returns:` block, keys like `{id}` / `{id}.cape` (l.362-403) |
| `_rewrite_export_paths` | `(tree_json, artifact_dir)` | `dict` | deep copy + relative→absolute `file_path` for the four export Creators, and `mkdir` (l.567-613) |
| `execute_plan` | `(db, plan_id, request)` | `ExecutionResult` | synchronous, in-process (l.616-722) |
| `execute_plan_streaming` | `(db, plan_id, request)` | `Generator[str]` | SSE frames, daemon worker thread (l.725-885) |
| `_tessellate_shapes` | `(shapes)` | `dict \| None` | best-effort; any exception → warning + `None` (l.930-981) |
| `_load_printer_settings` | `(db)` | `Printer3dSettings` | first `printer_settings` component, else `0.24 / 0.42 / 0.075` (l.984-1013) |

Module constants: `_INTERNAL_PARAMS` (l.257), `_CATEGORY_MAP` (l.406-420),
`_EXPORT_CREATOR_TYPES` (l.559-564), SSE queue timeout `300` (l.872), thread join
`5` (l.885). 🟢

### Part service — `app/services/construction_part_service.py` (350 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `_get_part_or_404` | `(db, aeroplane_id, part_id)` | `ConstructionPartModel` | filters on **both** ids (l.44-60) |
| `_validate_upload` | `(filename, content)` | `str` (suffix) | empty → 422; `> 50 MB` → `ConflictError(details.reason="file_too_large")` → 413; suffix ∉ `{.step,.stp,.stl}` → 422 (l.119-124) |
| `create_part` | `(db, aeroplane_id, filename, content, name, material_component_id=None, thumbnail_url=None)` | `ConstructionPartRead` | insert → `flush()` → `_store_file` → `_extract_geometry` |
| `_store_file` | `(aeroplane_id, part_id, content, ext)` | `Path` | `tmp/construction_parts/{aeroplane_id}/{part_id}_{uuid4().hex[:8]}{ext}` |
| `_extract_geometry` | `(path, file_format)` | `tuple[float\|None, …]` | all-`None` unless `cad_available()` **and** format is STEP; `Volume()` / `Area()` / `BoundingBox()` each guarded (l.144-198) |
| `get_part_file` | `(db, aeroplane_id, part_id, format)` | `(Path, mime)` | STL-from-STEP regeneration via `mkstemp` (l.276-280); STEP-from-STL → `ValidationError` |
| `set_locked` | `(db, aeroplane_id, part_id, locked)` | `ConstructionPartRead` | lock/unlock |
| `delete_part` | `(db, aeroplane_id, part_id)` | `None` | `ConflictError` when locked; unlink **before** commit (l.336-339) |

Constants: `ALLOWED_SUFFIXES`, `MAX_FILE_SIZE_BYTES = 52_428_800`,
`ALLOWED_DOWNLOAD_FORMATS`, `STORAGE_ROOT = Path("tmp")/"construction_parts"`
(l.38-41). 🟢

### Data model 🟢

Two independent tables — they share a prefix, not a relationship:

```
construction_plans   (id, name, description, tree_json JSON, plan_type,
                      aeroplane_id String FK → aeroplanes.id, created_at, updated_at)

construction_parts   (id, aeroplane_id String [indexed, NO FK], name,
                      volume_mm3, area_mm2, bbox_x/y/z_mm,
                      material_component_id FK → components.id,
                      locked Bool default False, thumbnail_url,
                      file_path, file_format, created_at, updated_at)
                          ▲
                          └── component_tree.construction_part_id  (aeroplane-core)
```

🟢 `construction_plans.aeroplane_id` becomes a real foreign key (`Q-CC-7`, maintainer-answered). Today a **`String`** reference to
`aeroplanes.id`, which is an **`Integer`** primary key, and carries no
`ON DELETE`. SQLite's dynamic typing tolerates it; PostgreSQL would reject the
constraint. 🔴 `construction_parts.aeroplane_id` has **no foreign key at all**,
so deleting an aeroplane orphans both the rows and their files — the same pattern
already flagged for `component_tree.aeroplane_id`. Full column tables:
`data-dictionary.md` §Module: construction-plans. 🟢

## Main Flow

### F1 — Plan CRUD and the template duality 🟢

```
POST /construction-plans            → _validate_tree_json (root $TYPE + creator_id) → insert → 201
GET  /construction-plans/{id}       → get_plan → _migrate_tree_json (silent, persists) → 200
PUT  /construction-plans/{id}       → _validate_tree_json → update → 200
DELETE /construction-plans/{id}     → delete → 204

instantiate_template(template_id, aeroplane_id):
    assert plan.plan_type == "template"          else ValidationError → 422
    assert aeroplane exists                      else NotFoundError  → 404
    new.tree_json   = copy.deepcopy(template.tree_json)
    new.name        = name_override or f"{template.name} — Plan"
    new.plan_type   = "plan"
    new.aeroplane_id = aeroplane_id              # no back-link recorded

to_template(plan_id):                            # the mirror image
    new.name = name_override or f"{plan.name} — Template"
    new.plan_type = "template" ; new.aeroplane_id = None
```

`_count_steps` walks `successors` recursively and accepts **both** shapes — an
`OrderedDict` (the `GeneralJSONEncoder` output) and a plain list (the frontend's
simplified form) — counting each dict node once (l.38-53). 🟢

### F2 — Synchronous execution (`execute_plan`, l.616-722) 🟢

```
1. effective_aeroplane_id = plan.aeroplane_id or request.aeroplane_id
   template AND neither                       → ValidationError → 422
2. artifact_dir = _template_runs/<plan_id>/<exec_id>     if plan_type == "template"
                  <aeroplane>/<plan_id>/<exec_id>        otherwise
   (template variant RMTREEs the previous run — artifact_service)
3. wing_config = { wing.name: wing_model_to_wing_config(wing, scale=1000.0) }
   per-wing failure → logger.warning + DROP that wing        (l.650-654)  🔴
4. printer_settings = first components row of type "printer_settings"
                      else Printer3dSettings(0.24, 0.42, 0.075)           (l.984-1013)
5. tree = _rewrite_export_paths(deepcopy(plan.tree_json), artifact_dir)   (l.567-613)
      for node whose creator $TYPE ∈ _EXPORT_CREATOR_TYPES:
          if not os.path.isabs(file_path):
              file_path = f"{artifact_dir}/{file_path}" ; mkdir(file_path)
      handles both  node["creator"]["file_path"]  and the flat  node["file_path"]
6. root = json.loads(tree, cls=GeneralJSONDecoder,
                     wing_config=wing_config,
                     printer_settings=printer_settings,
                     servo_information={},          # hard-coded 🔴
                     engine_information=None,       # hard-coded 🔴
                     component_information=None)    # hard-coded 🔴
   decode failure → ValidationError("Failed to decode construction plan: …") → 422
7. shapes = root.create_shape()          # REQUEST PROCESS, no chdir  🔴 (BR-CP11 — 🟢 routed through the CAD process pool, `Q-CP-1`)
      exception → ExecutionResult(status="error", error, duration_ms,
                                  artifact_dir, execution_id)   — HTTP 200
8. tessellation = _tessellate_shapes(shapes)        # best-effort, may be None
   return ExecutionResult(status="success", shape_keys, export_paths,
                          tessellation, artifact_dir, execution_id, duration_ms)
```

`_tessellate_shapes` (l.930-981):

```
candidates = [v for v in shapes.values() if hasattr(v, "val")]
solids     = flatten(s.val().Solids() for s in candidates)   # per-shape failures skipped
compound   = Compound.makeCompound(solids)  →  Workplane(compound)
group, inst = to_ocpgroup(compound, names=["result"], colors=["#FF8400"])
inst, sh, _ = tessellate_group(group, inst, {"deviation": 0.1,
                                             "angular_tolerance": 0.2})
any exception → logger.warning ; return None
```

Note the deviation/angular-tolerance pair is **identical** to the one
`cad-generation`'s tessellation worker uses (`tessellation_service.py:113`), so
plan output and wing output render at the same fidelity. 🟢

### F3 — Streaming execution (`execute_plan_streaming`, l.725-885) 🟢

```
setup identical to F2 steps 1–6
previous_env = os.environ.get("DISPLAY_CONSTRUCTION_STEP")
set_display_callback(on_display)                 # MODULE GLOBAL      🔴
os.environ["DISPLAY_CONSTRUCTION_STEP"] = "1"    # PROCESS GLOBAL     🔴

thread = threading.Thread(target=run, daemon=True).start()
    run(): shapes = root.create_shape()
           every Workplane.display(...) inside any Creator
             → on_display(name, tessellation)
             → shape_queue.put(("shape", name, _numpy_to_list(t)))
           finally: shape_queue.put(("done", result))

generator loop:
    item = shape_queue.get(timeout=300)
        queue.Empty        → yield  event: error  {"error": "Execution timed out"}
        ("shape", n, t)    → yield  event: shape  {"name": n, "tessellation": t}
        ("done", result)   → yield  event: complete {duration_ms, shape_keys,
                                                     tessellation, artifact_dir,
                                                     execution_id}
                             or     event: error   {error, duration_ms,
                                                    artifact_dir, execution_id}
    thread.join(timeout=5)

finally: restore DISPLAY_CONSTRUCTION_STEP to previous_env ; set_display_callback(None)
```

The `@conditional_execute("DISPLAY_CONSTRUCTION_STEP")` gate lives in
`cad_designer/decorators/general_decorators.py:5-21` and accepts
`"1" | "ON" | "TRUE" | "ENABLED"` case-insensitively; the plugin itself is
`Workplane.display` (owned by `cad-designer-topology`). 🟢

### F4 — Creator catalog (`list_creators` → `_collect_creators`) 🟢

```
try:  from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator
      import cad_designer.airplane.creator          # registers the subclasses
except ImportError: return []                       # aarch64 guard (ADR 0017)

walk AbstractShapeCreator.__subclasses__() recursively:
    if cls.__name__ in {ConstructionRootNode, ConstructionStepNode, JSONStepNode}:
        skip the class BUT still recurse into its subclasses
    description  = first line of cls.__doc__
    attr_docs    = _parse_docstring_attributes(cls.__doc__)
    for name, p in inspect.signature(cls.__init__).parameters.items():
        if name in _INTERNAL_PARAMS: continue
        CreatorParam(name,
                     type        = _type_to_str(p.annotation),
                     default     = None if p.default is EMPTY else p.default,
                     required    = p.default is EMPTY,
                     description = attr_docs.get(name),
                     options     = _extract_literal_values(p.annotation))
    outputs      = _parse_docstring_returns(cls.__doc__)
    suggested_id = getattr(cls, "suggested_creator_id", None)
    category     = _CATEGORY_MAP by module path, else "other"

sort by (category, class_name)
```

`_INTERNAL_PARAMS = {self, loglevel, kwargs, creator_id, wing_config,
printer_settings, servo_information, engine_information, component_information}`
— note this set is exactly *framework arguments* ∪ *decoder-injected kwargs*, so
the gallery shows only what a human must supply. 🟢

`_type_to_str` handles generics **before** falling back to `__name__`, because
`list[ShapeId].__name__` is just `"list"` and would lose the subscript that tells
the frontend it needs a multi-select. 🟢

### F5 — Construction-part upload and download 🟢

```
POST /aeroplanes/{id}/construction-parts   (multipart: file, name, material_component_id?, thumbnail_url?)
    content = await file.read()
    _validate_upload:
        empty                       → ValidationError            → 422
        len > 52_428_800            → ConflictError(reason=file_too_large) → 413
        suffix ∉ {.step,.stp,.stl}  → ValidationError            → 422
    insert row ; db.flush()                        # need part.id for the filename
    path = tmp/construction_parts/{aeroplane_id}/{part_id}_{uuid4().hex[:8]}{ext}
    write(content)
    if cad_available() and file_format == "step":
        volume_mm3  = guarded importStep(path).val().Volume()
        area_mm2    = guarded .Area()
        bbox_*_mm   = guarded .BoundingBox()
    else: all geometry fields stay NULL            # STL is a triangle soup
    → 201 ConstructionPartRead

GET  .../{part_id}/file?format=stl|step   (default "stl")
    source step + want stl → cq.exporters.export → mkstemp(".stl")   🔴 never removed
    source stl  + want step → ValidationError → 422 (not lossless)
    otherwise               → serve file_path
    FileResponse(filename=f"construction_part_{part_id}.{format}")

DELETE .../{part_id}
    locked → ConflictError → 409
    else   → db.delete(row) ; os.unlink(file)   BEFORE get_db() commits   (documented)
```

## Alternative Flows

- **Template without an aeroplane:** `ValidationError` → 422 before any artefact
  directory is created. 🟢
- **Unknown plan / aeroplane / part:** `NotFoundError` → 404. For parts the 404
  is also the answer for a valid id under the *wrong* aeroplane — deliberate
  non-enumerability. 🟢
- **Undecodable tree:** `ValidationError("Failed to decode construction plan: …")`
  → 422. Note this is the *only* place a missing `$TYPE` class surfaces; write
  time accepts it (BR-70). 🟢
- **Creator raises during `create_shape`:** captured, returned as
  `ExecutionResult(status="error", …)` with **HTTP 200**, so a client must check
  the body, not the status. 🟢
- **Wing conversion fails:** the wing is dropped from `wing_config` with a log
  warning and the execution proceeds against a partial aircraft. 🔴 The response
  carries no signal. 🟢 CONFIRMED
- **Result tessellation fails:** `tessellation` is `None`; `status` stays
  `"success"`. 🟢
- **SSE queue starvation:** `event: error {"error": "Execution timed out"}` after
  300 s, then a 5 s join on a daemon thread — the thread may still be running
  inside OCCT when the response completes. 🟡
- **`cad_designer` unimportable:** the catalog answers `200 []`; execution and
  part geometry extraction degrade separately (a part still uploads with null
  geometry). 🟢
- **`ConflictError` from a plan route:** falls through the local `status_map` and
  becomes a **500**. 🔴 (No plan-service path raises `ConflictError` today, so
  the defect is latent.) 🟢 CONFIRMED

## Dependencies

- **`cad-designer-topology`** — `GeneralJSONDecoder`, `AbstractShapeCreator` and
  the whole Creator stack, `Workplane.display` + `@conditional_execute`,
  `Printer3dSettings`. Frozen (ADR 0002); this module only consumes it.
- **`cad-generation`** — `artifact_service` (directory allocation, traversal
  guards, zip, listing, delete). The REST routes here are a thin projection over
  it.
- **`wing-design`** — `wing_service.get_aeroplane_or_raise` /
  `get_wing_or_raise`, and `model_schema_converters.wing_model_to_wing_config`
  at `scale = 1000.0`.
- **`aeroplane-core`** — the aeroplane aggregate the execution binds to;
  `component_tree.construction_part_id` points into `construction_parts`.
- **`powertrain` / components catalogue** — `ComponentModel` serves **two**
  unrelated purposes here: the `printer_settings` row consumed by executions, and
  `material_component_id` on a construction part. 🟡 The material link is not
  type-checked to be a `material` component; the frontend filters the dropdown.
- **`platform-core`** — `get_db()` transaction boundary (ADR 0009), the exception
  hierarchy, `cad_available()` (ADR 0017).
- **CadQuery / OCCT** (optional) — required for execution and for STEP geometry
  extraction; absent, both degrade rather than fail.
- **`ocp_tessellate`** — `to_ocpgroup` / `tessellate_group` for the result
  preview.
- Consumed by **`frontend-workbench`** (`workbench/construction-plans`), which is
  the only place `three-cad-viewer` is used.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| A plan is a serialised Creator tree, not a normalised step table | `construction_plans.tree_json` JSON column | 🟢 |
| Template and plan are one table discriminated by `plan_type`, not two tables | `construction_plan.py:11`; `state-machines.md` §6 | 🟢 |
| Instantiation is a deep copy with no lineage — divergence is intended | `instantiate_template:207-232` (BR-69) | 🟢 |
| Write-time validation is intentionally minimal; the decoder is the real gate | `_validate_tree_json:72-81` (BR-70) | 🟢 |
| 🟢 A one-off Alembic data migration replaces the lazy rewrite (`Q-CP-7`, `R2-02`) | `_migrate_tree_json:113-133` | 🟢 (intent 🔴) |
| Export paths are rewritten instead of `chdir`ing the executor | `_rewrite_export_paths:567-613` + in-code comment | 🟢 |
| Topology objects enter a plan only as decoder kwargs, never as serialised JSON | `execute_plan:670-678`; the `$TYPE` codec | 🟢 |
| Execution failure is data (`ExecutionResult.status`), not an HTTP error | `execute_plan:616-722` | 🟢 |
| Result tessellation is best-effort, never load-bearing | `_tessellate_shapes:930-981` | 🟢 |
| The Creator gallery is generated by reflection rather than a maintained registry | `_collect_creators:507-553` | 🟢 |
| An absent CAD kernel yields an empty catalog rather than a 503 | `list_creators:483-504` (ADR 0017) | 🟢 |
| Streaming reuses the CAD library's existing `display()` hook rather than adding progress callbacks | `set_display_callback` + `DISPLAY_CONSTRUCTION_STEP` | 🟢 |
| Part files are keyed by `{part_id}_{uuid8}` so re-uploads never collide | `_store_file` | 🟢 |
| A part delete unlinks the file before the commit, accepting a row-without-file on rollback | `construction_part_service.py:336-339` (comment) | 🟢 |
| STL carries no geometry metadata — a documented MVP limitation, not a bug | `_extract_geometry:144-198` | 🟢 |
| Plan execution runs in-process despite ADR 0005 | `execute_plan` vs `cad_service` docstring | 🟢 (resolution 🔴) |
| The plan routers use a bare `{"detail": …}` envelope and omit `ConflictError` | `construction_plans.py:37-47` | 🟢 (intent 🔴) |

## Internal State

The module is stateless between requests except for two **process-global**
switches used only while streaming:

| State | Scope | Lifetime | Risk |
|---|---|---|---|
| `construction_plan_service` display callback (`set_display_callback`) | module global | one streaming execution | 🟡 shared by concurrent streams |
| `os.environ["DISPLAY_CONSTRUCTION_STEP"]` | process global | one streaming execution, restored in `finally` | 🟡 a concurrent execution can flip it |
| the SSE `queue.Queue` + daemon worker thread | per request | until `complete`/`error` or the 300 s timeout | thread may outlive the response |

Persistent state:

- `construction_plans` — the tree, its type and its (optional) aeroplane binding.
  Mutated on read by `_migrate_tree_json`.
- `construction_parts` — one row per uploaded file, plus the file itself under
  `tmp/construction_parts/{aeroplane_id}/`.
- Artefact directories under `ARTIFACTS_BASE_DIR` — written by executions, owned
  by `cad-generation`.

Derived-at-read, never persisted: `PlanSummary.step_count`, the entire Creator
catalog, and `ExecutionResult`.

## Observability

- `logger.warning` when a wing fails `wing_model_to_wing_config` and is dropped
  (l.650-654) — the **only** trace of a partial execution. 🟢
- `logger.warning` when `_tessellate_shapes` fails; the execution still reports
  success. 🟢
- `duration_ms` on every `ExecutionResult` and on the SSE `complete`/`error`
  frames — the module's only latency signal. 🟢
- `artifact_dir` + `execution_id` on every result, which is what makes a run
  traceable to files on disk. 🟢
- No metrics, no traces, no structured events; there is no execution history
  table — the artefact directories **are** the log. 🟢
- 🟡 A failed execution leaves its artefact directory in place (it is created
  before `create_shape` runs), so orphan directories accumulate and are
  indistinguishable from successful ones without reading the response.

## Risks and Gaps

- 🔴 **In-process OCCT versus ADR 0005.** `cad_service` documents that CAD must
  run in a spawned process because OCCT is not thread-safe; `execute_plan` runs
  it on the request thread and `execute_plan_streaming` on a daemon thread. Both
  paths confirmed. Either the process pool is unnecessary or plan execution is
  exposed to the documented indefinite hang — and a 300 s SSE timeout does not
  free the thread, it only abandons it.
- 🔴 **Process-global streaming switches.** Two concurrent streams cross-deliver
  shape events and can clobber each other's `DISPLAY_CONSTRUCTION_STEP` value;
  a stream running alongside a non-streaming execution will emit that
  execution's shapes into the stream.
- 🔴 **Silent partial execution.** A wing that fails conversion is dropped with a
  log line only; the `ExecutionResult` cannot express it. Directly at odds with
  ADR 0012.
- 🔴 **Three decoder-kwarg slots are hard-coded empty** (`servo_information={}`,
  `engine_information=None`, `component_information=None`) at both execution call
  sites, so `ServoImporterCreator`, `ComponentImporterCreator` and
  `EngineMountShapeCreator` are unreachable through REST. Where that data should
  come from — the component tree, the COTS library, or the request body — is
  unspecified.
- 🔴 **`construction_plans.aeroplane_id` is a `String` FK to an `Integer` PK**
  with no `ON DELETE`; portable only by accident of SQLite's dynamic typing.
- 🔴 **`construction_parts.aeroplane_id` has no FK**, so deleting an aeroplane
  orphans rows and files with no cleanup path.
- 🔴 **Leaked temp files.** Every STL-from-STEP download creates a `mkstemp` file
  that is served and never removed.
- 🔴 **Part storage is inconsistent with every other artefact.** Files live under
  CWD-relative `tmp/construction_parts/`, not under `ARTIFACTS_BASE_DIR`, so they
  are outside the traversal-guarded tree and outside any artefact retention
  policy.
- 🔴 **`ConflictError` from a plan route becomes a 500** — the local
  `status_map` has no entry for it. Latent today, because no plan-service path
  raises it, but it is a trap for any future conflict semantics (e.g. concurrent
  execution of the same plan).
- 🔴 **Two coexisting HTTP error envelopes.** The plan routers answer
  `{"detail": "…"}`; the aeroplane routers answer
  `{"error": {"code", "message", "details"}}`. A client cannot parse errors
  uniformly across the API.
- 🟢 **`_migrate_tree_json` becomes a one-off Alembic data migration** (`Q-CP-7`, maintainer-answered). Previously mutates on read with no audit trail** and cannot be
  distinguished from a plan that was always correct.
- 🔴 **No template→plan back-link**, so a fleet of plans instantiated from one
  template cannot be found again, and a template fix cannot be propagated.
- 🟡 **`list_executions` scans `_template_runs` as if it were an aeroplane
  directory**, unlike `_resolve_execution_dir`, which skips it — a template run
  can surface in a plan listing with `aeroplane_id == "_template_runs"`. The
  asymmetry lives in `artifact_service` (`cad-generation`) but is only observable
  through this module's routes.
- 🟡 **`material_component_id` is not constrained to a `material` component** —
  the FK points at `components.id` generally, and only the frontend filters the
  dropdown.
- 🟡 **An artefact directory is created before execution begins**, so failed runs
  leave directories behind with no marker.
