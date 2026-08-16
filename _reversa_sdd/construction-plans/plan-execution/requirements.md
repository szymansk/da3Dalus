# plan-execution

> Use-case specification, nested under the module
> [`construction-plans`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: construction-plans
> (Execution, Streaming execution), `_reversa_sdd/domain.md` §2.10,
> `_reversa_sdd/flowcharts/construction-plans.md` §2–3, ADR 0005, ADR 0012.

## Overview

`plan-execution` turns a stored recipe into geometry: it resolves the target
aeroplane, allocates an artefact directory, builds the millimetre wing map,
rewrites relative export paths into that directory, decodes the tree into a live
Creator graph with injected topology objects, runs it, and best-effort
tessellates the result. A streaming variant emits one SSE frame per displayed
shape. Execution runs **in the request process** — which contradicts ADR 0005 and
is the single most important open question in this module. 🟢

## Responsibilities

- Resolve the effective aeroplane from the plan or the request, rejecting a
  template that names neither. 🟢
- Allocate a per-execution artefact directory, destructively for templates. 🟢
- Convert every wing of the aeroplane into a millimetre `WingConfiguration`. 🟢
- Load printer settings from the components catalogue with a fixed fallback. 🟢
- Rewrite relative exporter `file_path` values into the artefact directory and
  create it, on a **copy** of the tree. 🟢
- Decode the tree with `GeneralJSONDecoder`, injecting five topology kwargs. 🟢
- Execute the Creator graph and return the outcome as **data**, not as an HTTP
  error. 🟢
- Best-effort tessellate the produced shapes for the viewer. 🟢
- Stream the same execution as SSE `shape` / `complete` / `error` frames, bounded
  by a starvation timeout. 🟢

**Explicitly NOT this use case's responsibility:** storing or converting plans
(→ [`../plan-template-lifecycle/`](../plan-template-lifecycle/requirements.md)),
the Creator reflection catalog (→
[`../creator-catalog/`](../creator-catalog/requirements.md)), uploaded part files
(→ [`../construction-parts/`](../construction-parts/requirements.md)), the
`$TYPE` decoder and the Creator base contract (→ `cad-designer-topology`, frozen
per ADR 0002), artefact directory *storage semantics* (→ `cad-generation`), the
metre↔millimetre converter itself (→ `wing-design`), and the spar plan, which
shares only the word "plan" (→ `wing-design`).

## Business Rules

> IDs are inherited verbatim from [`../requirements.md`](../requirements.md).

- **BR-CP4 — The effective aeroplane is resolved before anything else.** 🟢
  `effective_aeroplane_id = plan.aeroplane_id or request.aeroplane_id`
  (`construction_plan_service.py:616-722`, step 1). The plan's own binding wins.
  A **template** with neither raises `ValidationError` → **422**, before any
  directory is created.
- **BR-CP2 — Execution is not idempotent for plans and destructive for
  templates.** 🟢 A plan run allocates
  `<aeroplane_id>/<plan_id>/<execution_id>/` and these accumulate; a template run
  allocates `_template_runs/<plan_id>/<execution_id>/` and
  `artifact_service.create_template_execution_dir` `shutil.rmtree`s the previous
  run first, so **at most one template execution survives**.
- **BR-CP5 — The execution world is millimetres.** 🟢
  `wing_config = {wing.name: wing_model_to_wing_config(wing, scale=1000.0)}`
  (step 3). The metre database is converted exactly at this boundary — the same
  scale `cad-generation`'s worker uses (ADR 0001).
- 🔴 **BR-CP6 — A wing that fails conversion is silently dropped.** 🟢 CONFIRMED
  behaviour / 🟡 a dropped wing becomes a `DesignWarning` (`Q-CP-3`). A per-wing `wing_model_to_wing_config` failure logs a
  warning and removes that wing from the map (l.650-654); the plan then executes
  against a **partial aircraft** and `ExecutionResult` has no field able to say
  so. Directly against ADR 0012.
- **BR-CP7 — Printer settings come from the components table with a fixed
  fallback.** 🟢 `_load_printer_settings` (l.984-1013) reads the **first**
  `components` row whose `component_type == "printer_settings"`, taking
  `layer_height`, `wall_thickness` and `rel_gap_wall_thickness` from its `specs`
  JSON; absent such a row it falls back to `0.24 / 0.42 / 0.075` mm — the same
  defaults `Printer3dSettings` itself declares.
- **BR-CP8 — Relative export paths are rewritten into the artefact directory,
  and the directory is created.** 🟢

  ```
  _EXPORT_CREATOR_TYPES = {ExportToStlCreator, ExportToStepCreator,
                           ExportToIgesCreator, ExportTo3mfCreator}   (l.559-564)

  _rewrite_export_paths(tree_json, artifact_dir):                     (l.567-613)
      tree = copy.deepcopy(tree_json)          # the stored tree is never mutated
      for node in walk(tree):
          if node creator $TYPE in _EXPORT_CREATOR_TYPES:
              fp = node["file_path"]
              if not os.path.isabs(fp):
                  fp = f"{artifact_dir}/{fp}"
                  os.makedirs(fp, exist_ok=True)   # file_path is a DIRECTORY
                  node["file_path"] = fp
      # both node["creator"]["file_path"] and the flat node["file_path"] are handled
  ```

  The in-code comment records the reason: the executor no longer `chdir`s, so
  without this rewrite every export would land in the project root.
- **BR-CP9 — Topology objects reach a running plan only as decoder kwargs, and
  three of the five slots are hard-coded empty.** 🟢

  ```
  json.loads(tree, cls=GeneralJSONDecoder,
             wing_config          = {name: WingConfiguration(mm)},
             printer_settings     = Printer3dSettings(...),
             servo_information    = {},     # hard-coded  🔴
             engine_information   = None,   # hard-coded  🔴
             component_information= None)   # hard-coded  🔴          (l.670-678)
  ```

  A decode failure becomes
  `ValidationError("Failed to decode construction plan: …")` → **422**.
  Consequence 🟢 (resolved by `Q-CP-2` — the component tree and COTS library supply them): `ServoImporterCreator`, `ComponentImporterCreator` and
  `EngineMountShapeCreator` can never receive real data through the REST path.
- **BR-CP10 — Result tessellation is best-effort and never fails the
  execution.** 🟢 `_tessellate_shapes` (l.930-981) collects every value with a
  `.val` attribute, takes `s.val().Solids()` per shape (individual failures
  skipped), builds one `Compound.makeCompound` → `Workplane`, then
  `to_ocpgroup(names=["result"], colors=["#FF8400"])` and
  `tessellate_group({"deviation": 0.1, "angular_tolerance": 0.2})`. Any exception
  logs a warning and returns `None`.
- **BR-CP10a — Execution failure is data, not an HTTP error.** 🟢 A Creator that
  raises yields `ExecutionResult(status="error", error, duration_ms,
  artifact_dir, execution_id)` with **HTTP 200**. Only *setup* failures (unknown
  plan → 404, template without an aeroplane → 422, undecodable tree → 422) use a
  non-2xx status. A client must inspect the body.
- 🟢 **BR-CP11 — plan execution routes through the same CAD process pool** (`Q-CP-1`, maintainer-answered). Previously it ran in the request process, contradicting
  ADR 0005.** 🟢 CONFIRMED (both code paths read) / 🔴 on resolution.
  `cad_service`'s docstring states CAD **must** run in a spawned process because
  OCCT is not thread-safe and `.intersect().clean()` — ~100 ms on the main
  thread — hangs indefinitely in a worker thread. Yet `execute_plan` calls
  `root_node.create_shape()` on the **FastAPI request thread**, and
  `execute_plan_streaming` runs it on a `threading.Thread`. Both drive the same
  CadQuery/OCCT stack. Either the process isolation is unnecessary or plan
  execution is exposed to the documented hang.

### Streaming

- **BR-CP12 — Streaming is armed by two process-global switches.** 🟢
  `set_display_callback(on_display)` (a module global) plus
  `os.environ["DISPLAY_CONSTRUCTION_STEP"] = "1"` arm the
  `@conditional_execute`-gated `Workplane.display` plugin
  (`cad_designer/decorators/general_decorators.py:5-21`, accepting
  `"1" | "ON" | "TRUE" | "ENABLED"` case-insensitively), so **every `display()`
  call inside any Creator emits a `shape` frame**. The `finally` block restores
  the previous env-var value and clears the callback.
  🟡 Neither switch is per-execution: two concurrent streams — or a stream
  concurrent with a non-streaming execution — cross-deliver shape frames and can
  re-enable or disable each other's gate. There is no lock and no per-execution
  context.
- **BR-CP13 — The stream has a hard starvation timeout.** 🟢 The generator drains
  a `queue.Queue` with `timeout=300` s; on starvation it emits
  `event: error {"error": "Execution timed out"}` and then
  `thread.join(timeout=5)` (l.872, l.885). The worker is a **daemon** thread, so a
  hung OCCT call is abandoned rather than awaited — the response completes while
  the thread may still be running.
- **BR-CP13a — Setup errors precede the stream.** 🟢 An unknown plan or a
  template without an aeroplane raises **before** the `StreamingResponse` is
  constructed, so it surfaces as an ordinary HTTP status, never as an `error`
  frame (`aeroplane_construction_plans.py:96-133`).

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-PE-01 | Resolve the effective aeroplane from the plan, else the request | Must | A bound plan executes with an empty body; a template with an `aeroplane_id` in the body executes |
| RF-PE-02 | Reject a template naming no aeroplane anywhere | Must | → 422, and no artefact directory is created |
| RF-PE-03 | Allocate a fresh artefact directory per plan execution | Must | Two runs of one plan leave two directories |
| RF-PE-04 | Wipe the previous template run before a new one | Must | Two runs of one template leave exactly one directory under `_template_runs/{plan_id}` |
| RF-PE-05 | Build the wing map in millimetres | Must | A wing whose DB chord is `0.25` reaches the Creator as `250.0` |
| RF-PE-06 | Survive a wing that cannot be converted | Must | The execution completes; the failing wing is absent from `wing_config` |
| RF-PE-07 | Report a dropped wing in the response | Should | 🟡 **Not met today** — the target behaviour is a structured warning naming the wing (ADR 0012) |
| RF-PE-08 | Load printer settings, falling back to `0.24 / 0.42 / 0.075` | Should | With no `printer_settings` component the fallback is used; with one, its `specs` win |
| RF-PE-09 | Rewrite relative exporter paths into the artefact directory and create it | Must | `file_path == "out"` produces `<artifact_dir>/out/`; nothing is written to the project root |
| RF-PE-10 | Leave absolute exporter paths untouched | Should | An absolute `file_path` is passed through verbatim |
| RF-PE-11 | Never mutate the stored tree during an execution | Must | `tree_json` is byte-identical before and after a run |
| RF-PE-12 | Handle both the nested and the flat node shape when rewriting | Should | A frontend-authored flat node is rewritten as well as an encoder-authored nested one |
| RF-PE-13 | Decode with the five injected kwargs | Must | The decoded Creator receives `wing_config` and `printer_settings`; an unknown `$TYPE` → 422 with the `"Failed to decode construction plan"` prefix |
| RF-PE-14 | Execute the graph and return `shape_keys` and `export_paths` | Must | A successful run reports every produced key |
| RF-PE-15 | Return a failing execution as `status == "error"` with HTTP 200 | Must | A raising Creator yields 200 with `error`, `duration_ms`, `artifact_dir`, `execution_id` |
| RF-PE-16 | Best-effort tessellate the result | Should | Tessellation failure leaves `tessellation is None` and `status == "success"` |
| RF-PE-17 | Stream `shape` / `complete` / `error` frames over SSE | Should | `text/event-stream` with `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no` |
| RF-PE-18 | Emit one `shape` frame per `Workplane.display()` call | Should | Two `display()` calls produce two frames before `complete` |
| RF-PE-19 | Terminate a starved stream after 300 s | Should | `event: error {"error": "Execution timed out"}`, then a 5 s join |
| RF-PE-20 | Restore the display gate after every stream | Must | `DISPLAY_CONSTRUCTION_STEP` returns to its prior value and the callback is cleared, even on failure |
| RF-PE-21 | Isolate concurrent streams from one another | Must | 🟡 **Not met today** — target: two concurrent streams each receive only their own shapes |
| RF-PE-22 | Serialise NumPy values in a tessellation payload to plain JSON | Must | A payload containing NumPy arrays serialises without a JSON encoder error |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Robustness | An execution failure must not become a 5xx — the artefact directory and timing are still reported | `execute_plan:616-722` | 🟢 |
| Robustness | Result tessellation is best-effort; an exception logs and returns `None` | `_tessellate_shapes:930-981` | 🟢 |
| Robustness | A single unconvertible wing must not abort the run | `:650-654` | 🟢 |
| Containment | Exports must land inside the artefact directory, never in the process CWD | `_rewrite_export_paths:567-613` + comment | 🟢 |
| Immutability | The rewrite works on a deep copy so the stored plan is never modified by running it | `_rewrite_export_paths:567-613` | 🟢 |
| Availability | The SSE generator cannot block indefinitely — 300 s starvation timeout, 5 s join, daemon worker | `:872, :885` | 🟢 |
| Availability | Setup errors surface as HTTP status codes before the stream opens | `aeroplane_construction_plans.py:96-133` | 🟢 |
| Consistency | Plan tessellation uses the same `deviation 0.1` / `angular_tolerance 0.2` as wing tessellation, so both render at one fidelity | `:930-981` vs `tessellation_service.py:113` | 🟢 |
| Isolation | 🟡 **Not met.** OCCT runs in the request process against ADR 0005 | `execute_plan` vs `cad_service` docstring | 🟢 |
| Concurrency | 🟡 **Not met.** The display callback and env var are process-global with no lock | `:725-885` | 🟢 |
| Transparency | 🟡 **Not met.** A partially converted aircraft is reported as a plain success | `:650-654`; `ExecutionResult` has no warnings field | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Execution setup

  Scenario: A bound plan executes without a request body
    Given a plan whose aeroplane_id is set
    When I POST /construction-plans/{plan_id}/execute with an empty body
    Then the response status is 200
    And status is "success"
    And artifact_dir and execution_id are populated

  Scenario: A template executes when the request names an aeroplane
    Given a plan with plan_type "template"
    When I POST /construction-plans/{plan_id}/execute with {"aeroplane_id": "<uuid>"}
    Then the response status is 200

  Scenario: A template naming no aeroplane is rejected before any side effect
    Given a plan with plan_type "template" and aeroplane_id null
    When I POST /construction-plans/{plan_id}/execute with an empty body
    Then the response status is 422
    And no artifact directory was created

  Scenario: Plan runs accumulate, template runs do not
    Given a plan and a template that have each been executed once
    When each is executed a second time
    Then the plan has two execution directories
    And the template has exactly one

Feature: Geometry and settings input

  Scenario: Wings arrive in millimetres
    Given an aeroplane with a wing whose stored chord is 0.25
    When the plan is executed
    Then the Creator receives that wing with chord 250.0

  Scenario: An unconvertible wing does not abort the run
    Given an aeroplane with two wings, one of which fails conversion
    When the plan is executed
    Then the response status is 200
    And status is "success"
    And the failing wing is absent from the wing configuration
    And a warning naming that wing is present in the result
    # the last step is the target behaviour — the legacy code only logs it

  Scenario: Printer settings fall back to documented defaults
    Given no component of type "printer_settings"
    When the plan is executed
    Then layer_height is 0.24, wall_thickness 0.42 and rel_gap_wall_thickness 0.075

Feature: Export path containment

  Scenario: A relative export path is confined to the artefact directory
    Given a plan whose ExportToStepCreator has file_path "out"
    When the plan is executed
    Then the directory <artifact_dir>/out exists
    And nothing was written to the project root

  Scenario: An absolute export path is left alone
    Given a plan whose exporter file_path is already absolute
    When the plan is executed
    Then that path is unchanged

  Scenario: Running a plan never modifies it
    Given a stored plan with relative export paths
    When the plan is executed
    Then the stored tree_json is byte-identical to before the run

Feature: Decoding and running

  Scenario: An unknown Creator fails at execution, not at storage
    Given a stored plan referencing a $TYPE that no longer exists
    When I execute it
    Then the response status is 422
    And the message begins with "Failed to decode construction plan"

  Scenario: A raising Creator returns a structured error
    Given a plan whose Creator raises during create_shape
    When I execute it
    Then the response status is 200
    And status is "error"
    And error, duration_ms, artifact_dir and execution_id are populated

  Scenario: Tessellation failure does not fail the execution
    Given an execution whose shapes cannot be tessellated
    When it completes
    Then status is "success"
    And tessellation is null

Feature: Streaming

  Scenario: Each displayed shape produces a frame
    Given a plan whose Creators call Workplane.display twice
    When I GET .../execute-stream
    Then the media type is text/event-stream
    And the headers include X-Accel-Buffering: no and Cache-Control: no-cache
    And two "shape" events arrive before one "complete" event

  Scenario: The display gate is restored after the stream
    Given DISPLAY_CONSTRUCTION_STEP was unset before the request
    When the stream completes or fails
    Then the variable is unset again
    And the display callback is cleared

  Scenario: A starved stream times out instead of hanging
    Given an execution that produces nothing for 300 seconds
    When the queue starves
    Then an "error" event carrying "Execution timed out" is emitted
    And the worker thread is joined with a 5 second timeout

  Scenario: A setup error is an HTTP status, not a frame
    Given a plan id that does not exist
    When I GET .../execute-stream
    Then the response status is 404
    And no event stream is opened
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Aeroplane resolution and its rejection (RF-PE-01/RF-PE-02) | Must | Everything downstream needs a target; the rejection must precede side effects |
| Artefact directory allocation (RF-PE-03/RF-PE-04) | Must | Without it exports have nowhere to go; the template-wipe rule is user-visible behaviour |
| Millimetre wing map (RF-PE-05) | Must | Wrong by 1000× when omitted (ADR 0001) |
| Export path rewriting and containment (RF-PE-09/RF-PE-11) | Must | Without it exports escape into the project root — a correctness *and* containment failure, and the deep copy is what keeps a plan reusable |
| Decoding with injected kwargs (RF-PE-13) | Must | The only way a Creator sees real geometry |
| Running and reporting (RF-PE-14/RF-PE-15) | Must | The reason the module exists; failure-as-data is what makes the frontend usable |
| Surviving an unconvertible wing (RF-PE-06) | Must | A single bad wing must not block the whole aircraft |
| Stream gate restoration (RF-PE-20) | Must | A leaked `DISPLAY_CONSTRUCTION_STEP` changes the behaviour of every later execution in the process |
| NumPy serialisation (RF-PE-22) | Must | Without it the frame simply fails to serialise |
| Concurrent-stream isolation (RF-PE-21) | Must | 🟡 Not met today; correctness under any concurrency at all |
| Reporting a dropped wing (RF-PE-07) | Should | 🟡 Not met today; required by ADR 0012, but the run itself is correct without it |
| Printer settings lookup (RF-PE-08) | Should | Has a documented fallback, so an execution never blocks on it |
| SSE streaming (RF-PE-17…RF-PE-19) | Should | A progress affordance — `/execute` returns the same result without it |
| Best-effort tessellation (RF-PE-16) | Should | A preview, not an output; the exported files are the deliverable |
| Absolute-path pass-through and flat-node handling (RF-PE-10/RF-PE-12) | Should | Compatibility with hand-written and frontend-authored trees |
| Injecting real servo / engine / component information | **Should** (`Q-CP-2`) | previously hard-coded empty at both call sites; three Creators are unreachable through REST. A 🔴 capability gap, not implemented |
| Moving execution into the CAD process pool | **Won't (undecided)** | Contradicts ADR 0005 today (BR-CP11 — 🟢 routed through the CAD process pool, `Q-CP-1`); the resolution is an open decision and must not be picked silently |
| A persisted execution history | **Won't** | There is no execution table; the artefact directories are the only record |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/construction_plan_service.py` | `execute_plan` (l.616-722), `execute_plan_streaming` (l.725-885), `_rewrite_export_paths` (l.567-613), `_EXPORT_CREATOR_TYPES` (l.559-564), `_tessellate_shapes` (l.930-981), `_load_printer_settings` (l.984-1013), `_numpy_to_list` | 🟢 |
| `app/api/v2/endpoints/construction_plans.py` | `execute_plan` (l.156-175) | 🟢 |
| `app/api/v2/endpoints/aeroplane_construction_plans.py` | `execute_plan` (l.79-94), `execute_plan_stream` (l.96-133) | 🟢 |
| `app/schemas/construction_plan.py` | `ExecuteRequest` (l.106), `ExecutionResult` (l.120) | 🟢 |
| `app/services/artifact_service.py` | `create_execution_dir`, `create_template_execution_dir` — specified in `cad-generation` | 🟢 cross-reference |
| `app/converters/model_schema_converters.py` | `wing_model_to_wing_config(scale=1000.0)` — specified in `wing-design` | 🟢 cross-reference |
| `cad_designer/airplane/GeneralJSONEncoderDecoder.py` | `GeneralJSONDecoder` — specified in `cad-designer-topology` (frozen) | 🟢 cross-reference |
| `cad_designer/decorators/general_decorators.py` | `@conditional_execute("DISPLAY_CONSTRUCTION_STEP")` (l.5-21) — specified in `cad-designer-topology` | 🟢 cross-reference |
| `app/services/cad_service.py` | module docstring (l.7-20) — the ADR 0005 rationale this slice contradicts | 🟢 cross-reference |
