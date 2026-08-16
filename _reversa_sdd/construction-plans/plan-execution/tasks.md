# plan-execution — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Nested under the module [`construction-plans`](../tasks.md).
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.

## Prerequisites

- [ ] **The isolation decision (T-PE-01) is answered.** It determines whether
      `create_shape()` runs in-process, on a thread, or in a spawned process, and
      the entire streaming design follows from it.
- [ ] [`../plan-template-lifecycle/`](../plan-template-lifecycle/tasks.md)
      complete — `get_plan` is the entry point of every execution.
- [ ] `cad-generation`'s `artifact_service` — `create_execution_dir` and
      `create_template_execution_dir` (including the template `rmtree` rule).
- [ ] `wing-design` — `wing_model_to_wing_config(wing, scale=1000.0)`,
      `get_aeroplane_or_raise`.
- [ ] `cad-designer-topology` — `GeneralJSONDecoder`, the Creator subpackages,
      `Printer3dSettings`, `Workplane.display` and the
      `@conditional_execute("DISPLAY_CONSTRUCTION_STEP")` decorator.
- [ ] `components` catalogue, optionally holding a `printer_settings` row with
      `layer_height` / `wall_thickness` / `rel_gap_wall_thickness` in `specs`.
- [ ] `ocp_tessellate` (`to_ocpgroup`, `tessellate_group`) — optional, since
      tessellation is best-effort.
- [ ] A writable `ARTIFACTS_BASE_DIR`.

## Tasks

### The blocking decision

- [ ] **T-PE-01 — Decide the execution isolation model before writing step 7.**
  ADR 0005 states OCCT must run in a spawned process because it is not
  thread-safe (`.intersect().clean()` ≈100 ms on the main thread, indefinite in a
  worker thread). The legacy code runs `create_shape()` on the FastAPI request
  thread, and on a `threading.Thread` when streaming.
  - Legacy origin: `construction_plan_service.py:616-722` and `:725-885` vs
    `app/services/cad_service.py:7-20` (ADR 0005)
  - Definition of done: a recorded decision — move execution into the process
    pool, or amend ADR 0005 with evidence that in-process execution is safe.
    Every downstream task (T-PE-14, T-PE-16 to T-PE-20) depends on it. Do **not**
    re-implement the contradiction silently.
  - Confidence: 🟡 — blocking.

### Setup chain

- [ ] **T-PE-02 — Effective-aeroplane resolution.**
  `plan.aeroplane_id or request.aeroplane_id`; a `plan_type == "template"` with
  neither raises `ValidationError`. The aeroplane is then resolved (404 if
  absent).
  - Legacy origin: `construction_plan_service.py:616-722` (step 1)
  - Definition of done: a bound plan executes with an empty body; a template
    executes when the body names an aeroplane; a template with neither returns
    422 **and no artefact directory exists afterwards**.
  - Confidence: 🟢

- [ ] **T-PE-03 — Artefact-directory allocation per plan type.**
  Templates → `_template_runs/<plan_id>/<execution_id>` with the previous run
  `rmtree`d; plans → `<aeroplane_id>/<plan_id>/<execution_id>`, accumulating.
  - Legacy origin: `construction_plan_service.py` (step 2);
    `artifact_service.create_template_execution_dir` / `create_execution_dir`
    (specified in `cad-generation`)
  - Definition of done: two plan runs leave two directories; two template runs
    leave exactly one.
  - Confidence: 🟢

- [ ] **T-PE-04 — Order the template check before the allocation.**
  A rejected template must leave no directory behind.
  - Legacy origin: step 1 precedes step 2
  - Definition of done: the 422 path is asserted to create nothing on disk.
  - Confidence: 🟢

- [ ] **T-PE-05 — Millimetre wing map.**
  `{wing.name: wing_model_to_wing_config(wing, scale=1000.0)}`.
  - Legacy origin: `construction_plan_service.py:650-654`
  - Definition of done: a wing whose stored chord is `0.25` m reaches the Creator
    as `250.0` mm.
  - Confidence: 🟢

- [ ] **T-PE-06 — Survive a wing that cannot be converted.**
  A per-wing failure must not abort the execution; the wing is omitted from the
  map.
  - Legacy origin: `construction_plan_service.py:650-654`
  - Definition of done: with one of two wings failing, the execution still
    completes and the other wing is present.
  - Confidence: 🟢

- [ ] **T-PE-07 — Report the dropped wing instead of only logging it.**
  Legacy behaviour logs a warning and says nothing in the response, which
  conflicts with ADR 0012.
  - Legacy origin: `construction_plan_service.py:650-654`;
    `ExecutionResult` has no warnings field
  - Definition of done: the run stays non-fatal **and** the result carries a
    structured warning naming the wing and the reason. Do **not** reproduce the
    silent form.
  - Confidence: 🟢 on the behaviour, 🟡 on the response-shape change (it extends
    `ExecutionResult`).

- [ ] **T-PE-08 — `_load_printer_settings`.**
  First `components` row with `component_type == "printer_settings"`, reading the
  three values from `specs`; fallback `0.24 / 0.42 / 0.075`.
  - Legacy origin: `construction_plan_service.py:984-1013`
  - Definition of done: with no such component the fallback is used; with one,
    its `specs` values reach the Creators; a partially populated `specs` falls
    back per field.
  - Confidence: 🟢

- [ ] **T-PE-09 — Make the printer-settings selection deterministic.**
  Legacy uses `.first()` with no ordering, so several such components give a
  non-deterministic result.
  - Legacy origin: `construction_plan_service.py:984-1013`
  - Definition of done: an explicit ordering (or a documented uniqueness rule)
    such that two identical requests always resolve the same row.
  - Confidence: 🟡

### Export path containment

- [ ] **T-PE-10 — `_rewrite_export_paths` on a deep copy.**
  Deep-copy the tree; for
  `_EXPORT_CREATOR_TYPES = {ExportToStlCreator, ExportToStepCreator,
  ExportToIgesCreator, ExportTo3mfCreator}`, rewrite a **relative** `file_path`
  to `<artifact_dir>/<file_path>` and `os.makedirs` it. `file_path` is a
  **directory** for exporters, not a file.
  - Legacy origin: `construction_plan_service.py:559-564, 567-613`
  - Definition of done: `file_path == "out"` produces `<artifact_dir>/out/`;
    nothing lands in the project root; the **stored** `tree_json` is
    byte-identical after the run.
  - Confidence: 🟢

- [ ] **T-PE-11 — Leave absolute paths untouched.**
  - Legacy origin: the `os.path.isabs` guard in `_rewrite_export_paths`
  - Definition of done: an absolute `file_path` passes through verbatim and is
    not prefixed.
  - Confidence: 🟢

- [ ] **T-PE-12 — Handle both the nested and the flat node shape.**
  `node["creator"]["file_path"]` (encoder form) and `node["file_path"]` (the
  frontend's simplified form).
  - Legacy origin: `construction_plan_service.py:567-613`
  - Definition of done: both encodings of the same plan produce the same rewritten
    paths.
  - Confidence: 🟢

- [ ] **T-PE-13 — Take `ExportTo3mfCreator` as the canonical spelling.**
  This slice spells it correctly; `cad_service.map_exporter_type` in
  `cad-generation` returns `"ExportTo3MFCreator"` and therefore breaks 3MF export
  there. The two modules disagree and this one is right.
  - Legacy origin: `construction_plan_service.py:559-564` vs
    `cad_service.py:185-203`
  - Definition of done: a single shared constant or an explicit cross-module test
    asserting one spelling; the `cad-generation` defect is not reproduced.
  - Confidence: 🟢

### Decode and run

- [ ] **T-PE-14 — Decode with the five injected kwargs.**
  `GeneralJSONDecoder` with `wing_config`, `printer_settings`,
  `servo_information`, `engine_information`, `component_information`; a failure
  becomes `ValidationError("Failed to decode construction plan: …")`.
  - Legacy origin: `construction_plan_service.py:670-678`
  - Definition of done: a tree referencing an unknown `$TYPE` returns 422 with
    that message prefix; a valid tree yields a live `ConstructionRootNode` whose
    Creators received the wing map.
  - Confidence: 🟢

- [ ] **T-PE-15 — Decide the source of servo / engine / component information.**
  All three are hard-coded (`{}`, `None`, `None`) at **both** call sites, so
  `ServoImporterCreator`, `ComponentImporterCreator` and
  `EngineMountShapeCreator` can never receive real data through REST.
  - Legacy origin: `construction_plan_service.py:670-678` and the streaming
    equivalent
  - Definition of done: a documented source (component tree, COTS library, or
    request body) and one end-to-end test driving a `ServoImporterCreator` with
    real data.
  - Confidence: 🟡 — needs a human decision.

- [ ] **T-PE-16 — Run the graph and capture failure as data.**
  A raising Creator yields `ExecutionResult(status="error", error, duration_ms,
  artifact_dir, execution_id)` with **HTTP 200**; a success reports `shape_keys`
  and `export_paths`.
  - Legacy origin: `construction_plan_service.py:616-722` (step 7)
  - Definition of done: a deliberately failing Creator produces a 200 whose body
    has `status == "error"` and a populated `execution_id`; a successful run
    lists every produced shape key.
  - Confidence: 🟢

- [ ] **T-PE-17 — `_tessellate_shapes` (best-effort).**
  Collect values with a `.val` attribute, `s.val().Solids()` per shape (skip
  individual failures), `Compound.makeCompound` → `Workplane` →
  `to_ocpgroup(names=["result"], colors=["#FF8400"])` →
  `tessellate_group({"deviation": 0.1, "angular_tolerance": 0.2})`. Any exception
  logs a warning and returns `None`; no solids also returns `None`.
  - Legacy origin: `construction_plan_service.py:930-981`
  - Definition of done: with `tessellate_group` patched to raise, the execution
    still reports `status == "success"` and `tessellation is None`; the
    deviation/angular-tolerance pair matches `cad-generation`'s wing worker.
  - Confidence: 🟢

- [ ] **T-PE-18 — Add a capability probe to the execution routes.**
  There is none today, so a platform without CadQuery answers 200 with
  `status == "error"` (or 422 on decode) instead of a clean 503 — unlike the rest
  of the codebase's `Depends(require_*)` pattern.
  - Legacy origin: absence of a guard on
    `construction_plans.py:156-175` / `aeroplane_construction_plans.py:79-94`
    (contrast ADR 0017)
  - Definition of done: with CadQuery unavailable the execution routes return a
    clean 503 naming the missing capability.
  - Confidence: 🟡 — a behaviour change; confirm it is wanted.

### Streaming

- [ ] **T-PE-19 — SSE frame contract.**
  `event: shape data {"name", "tessellation"}`;
  `event: complete data {"duration_ms", "shape_keys", "tessellation",
  "artifact_dir", "execution_id"}`;
  `event: error data {"error", "duration_ms", "artifact_dir", "execution_id"}`.
  Response `media_type="text/event-stream"` with headers
  `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`.
  - Legacy origin: `construction_plan_service.py:725-885`;
    `aeroplane_construction_plans.py:96-133`
  - Definition of done: a contract test asserts the three event names, every
    payload key and all three headers.
  - Confidence: 🟢

- [ ] **T-PE-20 — One `shape` frame per `Workplane.display()` call.**
  Reproduce the effect of arming the `@conditional_execute` gate plus a display
  callback, and flatten NumPy values with `_numpy_to_list` before serialising.
  - Legacy origin: `construction_plan_service.py:725-885`;
    `cad_designer/decorators/general_decorators.py:5-21`
  - Definition of done: a Creator calling `display()` twice produces exactly two
    `shape` frames before `complete`; a payload containing NumPy arrays
    serialises without error.
  - Confidence: 🟢

- [ ] **T-PE-21 — Scope the display hook per execution, not per process.**
  Legacy sets a **module-global** callback and a **process-global** env var,
  restoring both in `finally`. Reproduce the observable behaviour but scope it so
  concurrent executions cannot interfere.
  - Legacy origin: `construction_plan_service.py:725-885`
  - Definition of done: two concurrent streaming executions each receive only
    their own shapes, and neither clears the other's gate; a non-streaming
    execution running alongside a stream does not leak shapes into it. Do **not**
    reproduce the global form.
  - Confidence: 🟢 on the legacy behaviour, 🟡 on the mechanism (it depends on
    T-PE-01).

- [ ] **T-PE-22 — Restore the gate in `finally`, including the unset case.**
  If `DISPLAY_CONSTRUCTION_STEP` was previously unset it must be removed, not set
  to an empty string; if it was previously set, its old value is restored.
  - Legacy origin: the `finally` block of `execute_plan_streaming`
  - Definition of done: both branches are covered by tests, including the failure
    path.
  - Confidence: 🟢

- [ ] **T-PE-23 — Starvation timeout and bounded join.**
  `queue.Queue.get(timeout=300)` → `event: error {"error": "Execution timed
  out"}`; then `thread.join(timeout=5)` on a **daemon** worker.
  - Legacy origin: `construction_plan_service.py:872, :885`
  - Definition of done: a stalled execution emits the timeout frame and the
    request completes; the test does not hang. Document explicitly that the
    thread is abandoned, not killed.
  - Confidence: 🟢

- [ ] **T-PE-24 — Raise setup errors before opening the stream.**
  An unknown plan or a template without an aeroplane must surface as an HTTP
  status, never as an `error` frame.
  - Legacy origin: `aeroplane_construction_plans.py:96-133` (the `try` wraps the
    generator construction, not the iteration)
  - Definition of done: a bad plan id returns 404 with no event stream opened.
  - Confidence: 🟢

### REST layer

- [ ] **T-PE-25 — The three execution routes.**
  `POST /construction-plans/{plan_id}/execute` (body `ExecuteRequest`),
  `POST /aeroplanes/{id}/construction-plans/{plan_id}/execute` (aeroplane from
  the path, no body needed), and
  `GET /aeroplanes/{id}/construction-plans/{plan_id}/execute-stream`.
  All answer **200** on execution failure — only setup errors are non-2xx.
  - Legacy origin: `construction_plans.py:156-175`;
    `aeroplane_construction_plans.py:79-94, 96-133`
  - Definition of done: a contract test asserts each method, path and status,
    including that a failed execution is a 200 with `status == "error"`.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-PE-01 — Happy path:** a bound plan executes with an empty body,
      returning 200, `status == "success"`, non-empty `shape_keys`, and populated
      `artifact_dir` / `execution_id`.
- [ ] **TT-PE-02 — Failure:** a template with no aeroplane in the plan or the
      request returns 422 **and leaves nothing on disk**.
- [ ] **TT-PE-03 — Idempotence matrix:** two plan runs → two directories; two
      template runs → one directory.
- [ ] **TT-PE-04 — Millimetre conversion:** a wing with DB chord `0.25` reaches
      the Creator as `250.0`.
- [ ] **TT-PE-05 — Dropped wing survives:** with one of two wings failing
      conversion the execution still succeeds and the surviving wing is present.
- [ ] **TT-PE-06 — Dropped wing is reported:** the result carries a warning
      naming the failing wing (target behaviour; the legacy code fails this).
- [ ] **TT-PE-07 — Printer settings:** no component → `0.24 / 0.42 / 0.075`;
      a component → its `specs`; a partially populated `specs` → per-field
      fallback.
- [ ] **TT-PE-08 — Export containment:** a relative `file_path` lands under
      `<artifact_dir>/`, the directory is created, an absolute path is untouched,
      and nothing is written to the project root.
- [ ] **TT-PE-09 — Plan immutability:** `tree_json` is byte-identical before and
      after an execution.
- [ ] **TT-PE-10 — Node-shape parity:** the nested and flat encodings of the same
      plan produce identical rewritten paths.
- [ ] **TT-PE-11 — Exporter spelling:** the export-creator set contains
      `ExportTo3mfCreator`, and a 3MF plan executes (the `cad-generation`
      spelling defect is not reproduced).
- [ ] **TT-PE-12 — Decode failure:** an unknown `$TYPE` returns 422 with the
      `"Failed to decode construction plan"` prefix.
- [ ] **TT-PE-13 — Creator failure:** returns HTTP 200 with `status == "error"`
      and populated `error`, `duration_ms`, `artifact_dir`, `execution_id`.
- [ ] **TT-PE-14 — Tessellation is best-effort:** patched to raise, the run still
      reports success with `tessellation is None`; with no solids, likewise.
- [ ] **TT-PE-15 — Tessellation fidelity parity:** the deviation and
      angular-tolerance values match `cad-generation`'s wing worker.
- [ ] **TT-PE-16 — SSE contract:** three event names, every payload key, and the
      three headers.
- [ ] **TT-PE-17 — Frame count:** two `display()` calls produce exactly two
      `shape` frames before `complete`.
- [ ] **TT-PE-18 — NumPy serialisation:** a tessellation payload containing NumPy
      arrays serialises cleanly.
- [ ] **TT-PE-19 — Gate restoration:** previously unset → removed afterwards;
      previously set → restored; both on the success and the failure path.
- [ ] **TT-PE-20 — Concurrent streams do not cross-deliver** (target behaviour;
      the legacy globals fail this by construction).
- [ ] **TT-PE-21 — Non-streaming execution does not leak into an open stream**
      (same, target behaviour).
- [ ] **TT-PE-22 — Starvation:** a stalled execution emits
      `{"error": "Execution timed out"}` and the test completes.
- [ ] **TT-PE-23 — Setup error precedes the stream:** a bad plan id returns 404
      and no event stream is opened.
- [ ] **TT-PE-24 — Capability probe:** with CadQuery unavailable the execution
      routes return 503, not a 200 carrying `status == "error"`.

## Data Migration Tasks

- [ ] **TM-PE-01 — Sweep orphaned artefact directories left by failed
      executions.** The directory is allocated before `create_shape()` runs, so a
      failed run's directory is indistinguishable on disk from a successful
      one. Decide a retention policy and, if a marker file is introduced,
      backfill it as "unknown" for existing directories. 🟡
- [ ] **TM-PE-02 — Audit `components` for duplicate `printer_settings` rows**
      before implementing T-PE-09. If more than one exists, the current
      `.first()` behaviour has already been non-deterministic and some past
      executions may have used different settings. 🟡

## Suggested Order

1. **T-PE-01 first, and alone.** Nothing in this slice can be designed
   responsibly before the isolation question is answered — it decides whether
   step 7 is a call, a thread or a process boundary, and whether the streaming
   design needs cross-process transport.
2. **T-PE-02 → T-PE-04** next: the setup chain in order. T-PE-04 (ordering) is a
   constraint on T-PE-02 and T-PE-03 rather than a separate step, but it deserves
   its own test.
3. **T-PE-05 → T-PE-09** — inputs. T-PE-05 blocks T-PE-06, which blocks T-PE-07.
   T-PE-08/T-PE-09 are independent and parallelisable.
4. **T-PE-10 → T-PE-13** — export containment. T-PE-10 blocks T-PE-11 and
   T-PE-12 (they are branches of the same walk). T-PE-13 is a cross-module
   agreement best settled before either module's exporter tests are written.
5. **T-PE-14 → T-PE-18** — decode and run. T-PE-14 depends on steps 3 and 4
   producing its kwargs and its rewritten tree. T-PE-15 is a 🔴 decision that can
   run in parallel. T-PE-16 blocks T-PE-17.
6. **T-PE-19 → T-PE-24** — streaming, last, because it reuses the entire setup
   chain and its isolation mechanism follows from T-PE-01. T-PE-21 blocks
   TT-PE-20/TT-PE-21.
7. **T-PE-25** — the REST layer is thin and wires only what is already tested.

## Pending Gaps

- **Should plan execution move into the CAD process pool?** ADR 0005 says OCCT
  must run in a spawned process because it is not thread-safe; this slice runs it
  on the request thread and on a daemon thread. One of the two positions is
  wrong. The 300 s SSE timeout abandons rather than kills the thread, so under
  the documented hang each stalled execution permanently consumes a thread
  (T-PE-01, T-PE-21).
- **Where should `servo_information`, `engine_information` and
  `component_information` come from?** All three are hard-coded empty at both
  call sites, so `ServoImporterCreator`, `ComponentImporterCreator` and
  `EngineMountShapeCreator` are unreachable through the REST path (T-PE-15).
- **Should a partially converted aircraft fail the execution or warn?** Today it
  does neither visibly: the wing is dropped and only a log line records it, which
  conflicts with ADR 0012. Adding a warning changes the `ExecutionResult` shape
  (T-PE-07).
- **Should the execution routes gate on CadQuery availability?** Every other
  capability-dependent route uses `Depends(require_*)` and returns 503;
  these return 200 with `status == "error"` (T-PE-18).
- **What is the retention policy for artefact directories?** They are created
  before execution and left behind on failure, with no marker distinguishing a
  failed run from a successful one, and no execution history table exists
  (TM-PE-01).
- **Which `printer_settings` component wins when several exist?** `.first()` with
  no ordering is non-deterministic today (T-PE-09, TM-PE-02).
- **Is preserving a pre-existing `DISPLAY_CONSTRUCTION_STEP=1` intended?** The
  `finally` block restores whatever was there, so a deployment that sets it
  globally leaves the display gate permanently open and every execution logs a
  warning per gated call.
