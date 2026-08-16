# plan-execution — Technical Design

> Use-case design, nested under the module
> [`construction-plans`](../design.md).
> Focuses on HOW this use case is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Endpoint and SSE contracts in full: [`../contracts.md`](../contracts.md).

## Interface

### Service surface — `app/services/construction_plan_service.py` 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `execute_plan` | `(db, plan_id: int, request: ExecuteRequest)` | `ExecutionResult` | synchronous, **in the request process** (l.616-722) |
| `execute_plan_streaming` | `(db, plan_id: int, request: ExecuteRequest)` | `Generator[str, None, None]` | SSE frames; work on a daemon thread (l.725-885) |
| `_rewrite_export_paths` | `(tree_json: dict, artifact_dir: str)` | `dict` | deep copy; relative → `<artifact_dir>/…` for the four export Creators; `mkdir` (l.567-613) |
| `_tessellate_shapes` | `(shapes: dict)` | `dict \| None` | best-effort; any exception → warning + `None` (l.930-981) |
| `_load_printer_settings` | `(db)` | `Printer3dSettings` | first `printer_settings` component, else `0.24 / 0.42 / 0.075` (l.984-1013) |
| `_numpy_to_list` | `(obj)` | JSON-safe | flattens NumPy scalars/arrays before serialisation |

Constants: `_EXPORT_CREATOR_TYPES` (l.559-564), SSE queue timeout `300` (l.872),
thread join `5` (l.885), tessellation `{"deviation": 0.1,
"angular_tolerance": 0.2}` (l.930-981). 🟢

### Endpoint surface 🟢

| Method | Path | Handler | Note |
|---|---|---|---|
| POST | `/construction-plans/{plan_id}/execute` | `execute_plan` | body `ExecuteRequest`; **200** even on execution failure |
| POST | `/aeroplanes/{aeroplane_id}/construction-plans/{plan_id}/execute` | `execute_aeroplane_construction_plan` | builds `ExecuteRequest(aeroplane_id=<path>)` internally, so a template needs no body |
| GET | `/aeroplanes/{aeroplane_id}/construction-plans/{plan_id}/execute-stream` | `execute_aeroplane_construction_plan_stream` | `StreamingResponse(media_type="text/event-stream")` |

## Main Flow

### F1 — Synchronous execution (`execute_plan`, l.616-722) 🟢

```
t0 = now()
plan = get_plan(db, plan_id)                    # 404; also runs the legacy
                                                # root migration (sibling slice)

# ── 1. effective aeroplane ────────────────────────────────────────────────
effective_aeroplane_id = plan.aeroplane_id or request.aeroplane_id
if plan.plan_type == "template" and not effective_aeroplane_id:
    raise ValidationError(...)                              → 422
aeroplane = get_aeroplane_or_raise(db, effective_aeroplane_id)   # 404

# ── 2. artefact directory ─────────────────────────────────────────────────
if plan.plan_type == "template":
    artifact_dir, execution_id = artifact_service.create_template_execution_dir(plan.id)
    # RMTREEs the previous _template_runs/<plan_id> first
else:
    artifact_dir, execution_id = artifact_service.create_execution_dir(
        effective_aeroplane_id, plan.id)

# ── 3. wing map, in MILLIMETRES ───────────────────────────────────────────
wing_config = {}
for wing in aeroplane.wings:
    try:
        wing_config[wing.name] = wing_model_to_wing_config(wing, scale=1000.0)
    except Exception as err:
        logger.warning(...)          # 🔴 the wing is DROPPED, silently  (l.650-654)

# ── 4. printer settings ───────────────────────────────────────────────────
printer_settings = _load_printer_settings(db)          # fallback 0.24/0.42/0.075

# ── 5. export paths ───────────────────────────────────────────────────────
tree = _rewrite_export_paths(plan.tree_json, artifact_dir)   # DEEP COPY

# ── 6. decode ─────────────────────────────────────────────────────────────
try:
    root_node = json.loads(json.dumps(tree), cls=GeneralJSONDecoder,
                           wing_config=wing_config,
                           printer_settings=printer_settings,
                           servo_information={},          # 🔴 hard-coded
                           engine_information=None,       # 🔴 hard-coded
                           component_information=None)    # 🔴 hard-coded
except Exception as err:
    raise ValidationError(f"Failed to decode construction plan: {err}")   → 422

# ── 7. run — IN THE REQUEST PROCESS, no chdir ─────────────────────────────
try:
    shapes = root_node.create_shape()
except Exception as err:
    return ExecutionResult(status="error", error=str(err),
                           duration_ms=elapsed(t0),
                           artifact_dir=artifact_dir, execution_id=execution_id)

# ── 8. best-effort preview ────────────────────────────────────────────────
tessellation = _tessellate_shapes(shapes)      # may be None
return ExecutionResult(status="success",
                       shape_keys=list(shapes.keys()),
                       export_paths=[…],
                       tessellation=tessellation,
                       duration_ms=elapsed(t0),
                       artifact_dir=artifact_dir, execution_id=execution_id)
```

Two ordering facts are load-bearing:

- The **template check precedes directory allocation**, so a rejected template
  leaves no trace. 🟢
- The **directory is allocated before `create_shape()`**, so a failed execution
  still leaves a directory behind — indistinguishable on disk from a successful
  one. 🟡

### F2 — `_rewrite_export_paths` (l.567-613) 🟢

```
tree = copy.deepcopy(tree_json)          # the stored plan is never mutated

def visit(node):
    # the node may carry its creator nested or flattened:
    creator = node.get("creator") if isinstance(node.get("creator"), dict) else node
    if creator.get("$TYPE") in _EXPORT_CREATOR_TYPES:
        fp = creator.get("file_path")
        if fp and not os.path.isabs(fp):
            target = os.path.join(artifact_dir, fp)
            os.makedirs(target, exist_ok=True)      # file_path is a DIRECTORY
            creator["file_path"] = target
    for succ in (node.get("successors") or {}).values() | list-form:
        visit(succ)

visit(tree) ; return tree

_EXPORT_CREATOR_TYPES = {"ExportToStlCreator", "ExportToStepCreator",
                         "ExportToIgesCreator", "ExportTo3mfCreator"}   (l.559-564)
```

Note that this set uses the **correct** `ExportTo3mfCreator` spelling — unlike
`cad_service.map_exporter_type`, which returns `"ExportTo3MFCreator"` and
therefore breaks the 3MF path in `cad-generation`. The two modules disagree, and
this one is right. 🟢

### F3 — Streaming execution (`execute_plan_streaming`, l.725-885) 🟢

```
# setup identical to F1 steps 1–6, raised BEFORE the generator starts producing
previous = os.environ.get("DISPLAY_CONSTRUCTION_STEP")
shape_queue = queue.Queue()

def on_display(name, tessellation):                      # module-global callback
    shape_queue.put(("shape", name, _numpy_to_list(tessellation)))

set_display_callback(on_display)                         # 🔴 MODULE GLOBAL
os.environ["DISPLAY_CONSTRUCTION_STEP"] = "1"            # 🔴 PROCESS GLOBAL

def run():
    try:    shapes = root_node.create_shape()
            shape_queue.put(("done", ok_result(shapes)))
    except Exception as err:
            shape_queue.put(("done", err_result(err)))

thread = threading.Thread(target=run, daemon=True); thread.start()

try:
    while True:
        try:    item = shape_queue.get(timeout=300)              # l.872
        except queue.Empty:
                yield sse("error", {"error": "Execution timed out"}); break
        kind = item[0]
        if kind == "shape":
                yield sse("shape", {"name": item[1], "tessellation": item[2]})
        else:   # "done"
                yield sse("complete" | "error", item[1]); break
    thread.join(timeout=5)                                        # l.885
finally:
    if previous is None: os.environ.pop("DISPLAY_CONSTRUCTION_STEP", None)
    else:                os.environ["DISPLAY_CONSTRUCTION_STEP"] = previous
    set_display_callback(None)
```

Frame shapes:

```
event: shape     data {"name": "<shape id>", "tessellation": { … }}
event: complete  data {"duration_ms", "shape_keys", "tessellation",
                       "artifact_dir", "execution_id"}
event: error     data {"error", "duration_ms", "artifact_dir", "execution_id"}
```

The mechanism reuses the CAD library's existing debug hook rather than adding a
progress API: `Workplane.display` is decorated with
`@conditional_execute("DISPLAY_CONSTRUCTION_STEP")`
(`cad_designer/decorators/general_decorators.py:5-21`), which runs the wrapped
function only when the env var is one of `"1" | "ON" | "TRUE" | "ENABLED"`
(case-insensitive) and otherwise logs a warning and returns `self`. Every
`display()` call a Creator author left in the code therefore becomes a progress
event. 🟢

### F4 — `_tessellate_shapes` (l.930-981) 🟢

```
candidates = [v for v in shapes.values() if hasattr(v, "val")]
solids = []
for s in candidates:
    try:    solids.extend(s.val().Solids())
    except Exception: continue                    # per-shape failures skipped
if not solids: return None
compound      = Compound.makeCompound(solids)
wp            = Workplane(obj=compound)
group, inst   = to_ocpgroup(wp, names=["result"], colors=["#FF8400"])
inst, sh, _   = tessellate_group(group, inst, {"deviation": 0.1,
                                               "angular_tolerance": 0.2})
return _numpy_to_list({... instances, shapes ...})
# any exception → logger.warning ; return None
```

The `deviation` / `angular_tolerance` pair is identical to the one
`cad-generation`'s wing tessellation worker uses
(`tessellation_service.py:113`), so a plan preview and a wing preview render at
the same fidelity in the same viewer. 🟢

### F5 — `_load_printer_settings` (l.984-1013) 🟢

```
row = db.query(ComponentModel).filter(
          ComponentModel.component_type == "printer_settings").first()
if row and row.specs:
    return Printer3dSettings(
        layer_height           = specs.get("layer_height",           0.24),
        wall_thickness         = specs.get("wall_thickness",         0.42),
        rel_gap_wall_thickness = specs.get("rel_gap_wall_thickness", 0.075))
return Printer3dSettings(0.24, 0.42, 0.075)
```

`.first()` with no ordering: with several `printer_settings` components the
choice is whichever the database returns first. 🟡

## Alternative Flows

- **Template without an aeroplane:** `ValidationError` → 422 **before** the
  artefact directory is allocated. 🟢
- **Unknown plan or aeroplane:** `NotFoundError` → 404. 🟢
- **One wing fails conversion:** logged, dropped, execution proceeds against a
  partial aircraft; the response carries no signal. 🔴 🟢 CONFIRMED
- **All wings fail conversion:** `wing_config` is empty; the decode still
  succeeds and the Creators fail at geometry time, surfacing as
  `status == "error"`. 🟡
- **Undecodable tree:** `ValidationError("Failed to decode construction plan: …")`
  → 422 — the only place a dangling `$TYPE` surfaces, since write-time validation
  covers the root only. 🟢
- **Creator raises:** captured as `ExecutionResult(status="error", …)` with
  **HTTP 200**; the artefact directory (already created) is still reported. 🟢
- **Tessellation fails:** `tessellation is None`, `status` stays `"success"`. 🟢
- **SSE queue starvation:** `event: error {"error": "Execution timed out"}` after
  300 s, then a 5 s join on a daemon thread — which may still be inside OCCT when
  the response completes. 🟡
- **Two concurrent streams:** shape frames are delivered to whichever callback is
  currently installed; the second stream's `set_display_callback` replaces the
  first's, and the first stream's `finally` clears the second's gate. 🔴
- **A non-streaming execution running during a stream:** its `display()` calls
  fire the installed callback, so its shapes appear in the stream. 🔴
- **`DISPLAY_CONSTRUCTION_STEP` already set to `"1"` process-wide:** every
  execution emits display calls; the `finally` restores that prior value, so the
  gate stays open. 🟡

## Dependencies

- **`plan-template-lifecycle`** (sibling) — `get_plan`, which also runs the
  legacy root migration; execution therefore inherits a write on the read path.
- **`cad-generation`** — `artifact_service.create_execution_dir` /
  `create_template_execution_dir` (the `rmtree` rule for templates lives there).
- **`wing-design`** — `wing_model_to_wing_config(wing, scale=1000.0)` and
  `get_aeroplane_or_raise` / `get_wing_or_raise`.
- **`cad-designer-topology`** — `GeneralJSONDecoder`, the whole Creator stack,
  `Printer3dSettings`, `Workplane.display` and `@conditional_execute`. Frozen
  (ADR 0002).
- **`powertrain` / components catalogue** — the `printer_settings` component row.
- **`ocp_tessellate`** — `to_ocpgroup` / `tessellate_group`.
- **CadQuery / OCCT** — required; there is **no capability probe** on these
  routes, so an absent kernel surfaces as a decode error or an execution error
  rather than a 503. 🟡
- **`platform-core`** — `get_db()` (ADR 0009), the exception hierarchy.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| The plan's own `aeroplane_id` wins over the request body | `execute_plan` step 1 | 🟢 |
| The template check precedes directory allocation, so a rejection leaves no trace | step 1 before step 2 | 🟢 |
| Template runs are destructive by design — at most one survives | `create_template_execution_dir` | 🟢 |
| Export paths are rewritten instead of `chdir`ing the executor | `_rewrite_export_paths` + in-code comment | 🟢 |
| The rewrite operates on a deep copy, keeping a plan reusable | `copy.deepcopy` at l.567 | 🟢 |
| Both nested and flat node shapes are tolerated, because the frontend emits a simplified form | `_rewrite_export_paths:567-613` | 🟢 |
| Topology objects enter only as decoder kwargs, never as serialised JSON | l.670-678 | 🟢 |
| Three kwarg slots are filled from the component tree and COTS library | l.670-678 | 🟢 (`Q-CP-2`) |
| Execution failure is data (`status`), not an HTTP error | l.616-722 | 🟢 |
| Result tessellation is best-effort and shares the wing-tessellation fidelity | `:930-981` vs `tessellation_service.py:113` | 🟢 |
| Streaming reuses the library's existing `display()` debug hook rather than a new progress API | `set_display_callback` + `@conditional_execute` | 🟢 |
| The streaming worker is a daemon thread with a bounded join — a hung OCCT call is abandoned | `:885` | 🟢 |
| 🟢 A single unconvertible wing **fails the run** (`R2-03`) — a construction plan produces physical parts, so a complete-looking part set with a wing missing is worse than an error | `:650-654` | 🟢 (silence 🔴) |
| `_load_printer_settings` takes `.first()` with no ordering | `:984-1013` | 🟢 (intent 🟡) |
| Execution runs in-process despite ADR 0005 | `execute_plan` vs `cad_service` docstring | 🟢 (resolution 🔴) |

## Internal State

Stateless between requests, except while streaming:

| State | Scope | Lifetime | Risk |
|---|---|---|---|
| display callback (`set_display_callback`) | module global | one stream | 🟡 replaced by a concurrent stream; cleared by whichever finishes first |
| `os.environ["DISPLAY_CONSTRUCTION_STEP"]` | process global | one stream, restored in `finally` | 🟡 a concurrent execution can flip it; a pre-existing `"1"` is preserved and keeps the gate open |
| `shape_queue` (`queue.Queue`) | per request | until `complete` / `error` / 300 s | bounded only by the timeout |
| daemon worker thread | per request | may outlive the response | 🟡 an OCCT hang is abandoned, not killed |

No persistent state of its own. Side effects on disk: the artefact directory (and
whatever the exporters write into it) and, for templates, the removal of the
previous run.

## Observability

- `logger.warning` when a wing fails conversion and is dropped (l.650-654) — the
  **only** trace of a partial execution. 🔴
- `logger.warning` when `_tessellate_shapes` fails; the execution still reports
  success. 🟢
- `duration_ms` on every result and on the SSE `complete` / `error` frames — the
  only latency signal. 🟢
- `artifact_dir` + `execution_id` on every result, which is what makes a run
  traceable to files on disk. 🟢
- No execution history table, no metrics, no traces. The artefact directories
  **are** the log — and because the directory is created before `create_shape()`
  runs, a failed run's directory is indistinguishable from a successful one. 🟡
- `@conditional_execute` logs a warning on every gated-off `display()` call, so a
  non-streaming execution of a display-heavy plan produces one log line per
  call. 🟡

## Risks and Gaps

- 🔴 **In-process OCCT versus ADR 0005.** The strongest architectural
  contradiction in the codebase: `cad_service` documents an indefinite hang when
  OCCT runs off the main thread, and this slice runs it on the request thread
  (and on a worker thread when streaming). A 300 s SSE timeout does not free the
  thread — it abandons it, so a hung execution permanently consumes a thread.
- 🔴 **Process-global streaming switches.** Concurrent streams cross-deliver
  frames and clobber each other's gate; a non-streaming execution running
  alongside a stream leaks its shapes into that stream. There is no lock and no
  per-execution context.
- 🔴 **Silent partial execution.** A dropped wing is logged only, and
  `ExecutionResult` has no field able to express it — a direct conflict with
  ADR 0012.
- 🔴 **Three decoder-kwarg slots hard-coded empty**, making
  `ServoImporterCreator`, `ComponentImporterCreator` and
  `EngineMountShapeCreator` unreachable through REST. The intended data source is
  unspecified.
- 🔴 **No capability probe.** On a platform without CadQuery these routes answer
  200 with `status == "error"` (or 422 on decode) rather than a clean 503, unlike
  the rest of the codebase's `Depends(require_*)` pattern (ADR 0017).
- 🟡 **A failed execution leaves an artefact directory** with no marker, so
  orphan directories accumulate and cannot be told apart from successful runs
  without the response body.
- 🟡 **`_load_printer_settings` uses `.first()` with no ordering**, so with
  multiple `printer_settings` components the selection is non-deterministic.
- 🟡 **`json.dumps`/`json.loads` round-trip on the tree** costs a full
  serialisation pass per execution; harmless for small plans, but it means the
  rewritten tree is materialised twice.
- 🟡 **A pre-existing `DISPLAY_CONSTRUCTION_STEP=1` is preserved** by the
  `finally` block, so a deployment that sets it globally makes every execution
  emit display calls and log warnings.
- 🟢 **Worth preserving:** this slice spells `ExportTo3mfCreator` correctly,
  unlike `cad_service.map_exporter_type` in `cad-generation`, which returns
  `"ExportTo3MFCreator"` and breaks 3MF export there. A re-implementation should
  take **this** spelling as canonical.
