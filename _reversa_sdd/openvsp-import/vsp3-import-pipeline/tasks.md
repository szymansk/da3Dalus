# vsp3-import-pipeline — Implementation Tasks

> Use-case task list, nested under the module
> [`openvsp-import`](../tasks.md). Every task cites the legacy file it was
> extracted from, a definition of done, and a confidence marker.
> Sibling slices: [`../geom-handlers/tasks.md`](../geom-handlers/tasks.md),
> [`../step-export-and-sewing/tasks.md`](../step-export-and-sewing/tasks.md).

## Prerequisites

- [ ] `openvsp` bindings installable but **optional** (ADR 0017).
- [ ] CadQuery/OCCT optional — only F2's bounding-box measurement needs it.
- [ ] `export_geom_step` / `step_storage_dir` available from
      [`../step-export-and-sewing/`](../step-export-and-sewing/tasks.md) —
      source-unit detection borrows them.
- [ ] The four persistence entry points: `aeroplane_service.create_aeroplane`,
      `wing_service.create_wing`, `fuselage_service.create_fuselage`, and the
      weight-item write path.
- [ ] `AsbWingGeometryWriteSchema` / `WingXSecGeometryWriteSchema`
      (`app/schemas/aeroplaneschema.py:592-708`).
- [ ] `settings.ARTIFACTS_BASE_DIR` resolvable and writable.
- [ ] `get_db()` owning the transaction (ADR 0009).

## Tasks

### Optional dependency and process state

- [ ] **T-IP-01 — The adapter memo.**
  Memoise `importlib.import_module("openvsp")` in `_cached_module`,
  `_import_attempted`, `_import_error`; expose `is_available()` and
  `get_vsp()`; `get_vsp()` raises `ImportError(_OPENVSP_MISSING_MSG)` naming the
  three supported install paths; `reset_for_tests()` is the only reset.
  - Legacy origin: `app/converters/openvsp_adapter.py:53-55, 92-97`
  - Definition of done: a failed import is attempted exactly once per process;
    `get_vsp()` never returns `None`; `reset_for_tests()` allows a retry.
  - Confidence: 🟢

- [ ] **T-IP-02 — Handler registry with a visible failure path.**
  Register the wing, fuselage, blank and custom handlers plus the
  `_resolve_vehicle_cg` and `_drop_degenerate_fuselages` post-passes, once per
  process. **Do not reproduce the silent `except ImportError: pass`** — log at
  `error` naming the module, and consider surfacing an import warning.
  - Legacy origin: `openvsp_importer.py:287-321`
  - Definition of done: `_ensure_handlers_loaded` is idempotent; with one
    handler module patched to raise `ImportError`, the import still runs **and**
    a diagnostic names the module.
  - Confidence: 🟢 behaviour · 🔴 the swallow is a defect (BR-OV19)

- [ ] **T-IP-03 — Document the restart rule (BR-OV2).**
  `_handlers_loaded`, `_HANDLERS`, `_POST_PASSES`, the adapter memo and the SWIG
  native model all survive `uvicorn --reload`.
  - Legacy origin: `openvsp_importer.py:181-182, 284`; `openvsp_adapter.py:53-55`
  - Definition of done: the module docstring states that importer changes need a
    process restart, and the developer docs repeat it.
  - Confidence: 🟢

### The critical read sequence

- [ ] **T-IP-04 — `import_vsp3` in order.**
  `_ensure_handlers_loaded()` → `ClearVSPModel()` → `ReadVSPFile(path)` →
  `_read_source_length_unit(...)` →
  `if hasattr(vsp, "SetLengthUnit"): SetLengthUnit(LEN_M)` → `Update()` →
  dispatch every `FindGeoms()` id → run every post-pass.
  - Legacy origin: `openvsp_importer.import_vsp3:324-420`
  - Definition of done: importing A then B in one process yields only B's geoms;
    removing `ClearVSPModel` makes that test fail.
  - Confidence: 🟢

- [ ] **T-IP-05 — `_read_source_length_unit` and the empty-string convention.**
  `FindParm(vehicle_id, "LengthUnit", "Vehicle_Info")` prints `Can't Find Parm`
  to stderr but returns `""`; treat `""` as "not found". Guard `SetLengthUnit`
  behind `hasattr` because 3.50+ removed it. Map the legacy enum with
  `LEN_UNIT_TO_METERS` (`0 mm 0.001 · 1 cm 0.01 · 2 m 1.0 · 3 in 0.0254 ·
  4 ft 0.3048 · 5 yd 0.9144 · 6 unitless 1.0`).
  - Legacy origin: `openvsp_importer.py:63-71, 352-368`
  - Definition of done: an empty return yields `None`, not an exception; a 3.50
    fixture imports cleanly.
  - Confidence: 🟢 (`LEN_UNITLESS → 1.0` is 🔴 — decide whether to warn)

- [ ] **T-IP-06 — Geom type canonicalisation.**
  `_DISPLAY_TO_CANONICAL`, 16 entries, `.upper()` fallback.
  - Legacy origin: `openvsp_importer.py:194-211`; verified on OpenVSP 3.50.4
  - Definition of done: all 16 entries plus an unlisted name are covered by a
    parametrised test.
  - Confidence: 🟢

- [ ] **T-IP-07 — Dispatch and the unsupported-type table.**
  `_HANDLERS.get(token)`; a miss emits `_UNSUPPORTED_REASONS[token]` (or
  `"not supported in Phase 1"`) plus `ctx.mark_lossy(gid)`. 14 tokens carry a
  reason: `PROP`, `DISK`, `MESH`, `CONFORMAL`, `NGON_MESH`, `HUMAN`, `POD`,
  `BOR`, `STACK`, `ELLIPSOID`, `WIRE_FRAME`, `HINGE`, `PT_CLOUD`, `GEAR`.
  - Legacy origin: `openvsp_importer.py:242-260`
  - Definition of done: each token produces its warning and the import still
    returns 201.
  - Confidence: 🟢

- [ ] **T-IP-08 — `ImportWarning` / `ImportContext` / `ImportResult`.**
  Frozen `ImportWarning(component_type, component_name, reason,
  severity="warning")` validated against `{info, warning, error}`;
  `ImportContext` with `add_warning`, de-duplicating `mark_lossy`,
  `weight_items`, `source_length_unit`, `source_scale_to_meters`,
  `wing_geom_ids`, `fuselage_geom_ids`; `ImportResult` carrying all of it plus
  the `AeroplaneSchema`.
  - Legacy origin: `openvsp_importer.py:84, 98-141, 145`; data-dictionary
    §Module: openvsp-import
  - Definition of done: `mark_lossy` twice with one gid yields one entry; an
    invalid severity is rejected; `wing_geom_ids` / `fuselage_geom_ids` reach
    the post-passes.
  - Confidence: 🟢

- [ ] **T-IP-09 — Post-pass failures become warnings.**
  A raising post-pass yields `component_type = "POST_PASS"`.
  - Legacy origin: `openvsp_importer.py:401-410`
  - Definition of done: a deliberately raising post-pass still yields 201 with
    the warning present.
  - Confidence: 🟢

- [ ] **T-IP-10 — 🟢 Register the SS_CONTROL post-pass** (`Q-VI-1`).
  Add `openvsp_ss_control.register()` to `_ensure_handlers_loaded`. **This is
  only half the fix** — see `../geom-handlers/tasks.md` T-GH-13 for the
  persistence half; landing either alone changes nothing observable.
  - Legacy origin: `openvsp_importer.py:287-321`;
    `app/tests/test_openvsp_ss_control.py:24` is the only current caller
  - Definition of done: a test driving the **production** entry point observes
    the post-pass running.
  - Confidence: 🟢 — wired (`Q-VI-1`/`Q-VI-2`); it was not parked deliberately

- [ ] **T-IP-11 — 🟢 Call `validate_geometry`** (`Q-VI-2`).
  Wire the gh-647 cross-check into `import_vsp3` as its own docstring shows
  (`result.warnings.extend(mismatches)`).
  - Legacy origin: `app/converters/openvsp_validation.py:39, 44`
  - Definition of done: a mis-derived planform produces a warning through the
    production pipeline.
  - Confidence: 🟢 — wired (`Q-VI-1`/`Q-VI-2`); it was not parked deliberately

### Units and scaling

- [ ] **T-IP-12 — `_snap_to_unit_scale`.**
  Reject non-finite and non-positive ratios; accept when
  `|ratio − factor| ≤ 0.02 · factor` (**relative** window), keeping the nearest
  match; return `None` for metres or no match.
  `_LENGTH_UNIT_FACTORS = {m 1.0, yd 0.9144, ft 0.3048, in 0.0254, cm 0.01,
  mm 0.001}`.
  - Legacy origin: `openvsp_import_service.py:94, 105-126`
  - Definition of done: `0.3048 → ("ft", 0.3048)`; `1.0 → None`; `0.5 → None`;
    `NaN → None`; both ±2 % boundaries are covered.
  - Confidence: 🟢

- [ ] **T-IP-13 — `_detect_source_scale_to_meters` (gh-808).**
  Reference fuselage = largest handler X-span; export it under
  `detect_uuid = f"_unitdetect_{path.stem}"`; measure `bb.xlen / 1000.0` (OCC
  normalises STEP to mm); snap the ratio. Bail out on no fuselages, unknown gid,
  `handler_span ≤ 1e-6`, or a falsy export. Wrap everything in
  `except Exception` logged at `info`, and `rmtree` the detect directory in a
  `finally`.
  - Legacy origin: `openvsp_import_service.py:147-201`
  - Definition of done: a feet fixture converts ×0.3048 with a `UNITS` warning;
    a fuselage-less fixture returns `None`; the detect directory is gone
    afterwards even when the measurement raised.
  - Confidence: 🟢 (the fuselage-less blind spot is 🔴)

- [ ] **T-IP-14 — `_convert_aeroplane_to_metres` vs `_scale_aeroplane_lengths`.**
  The unit conversion scales **everything** including fuselage x-secs; the user
  rescale scales wing `xyz_le` / `chord`, `xyz_ref` and weight-item positions
  **only**. Neither touches twist or masses.
  - Legacy origin: `openvsp_import_service.py:254-293` + the
    `_convert_aeroplane_to_metres` wrapper
  - Definition of done: after a unit conversion the fuselage x-secs are scaled;
    after a user rescale they are not.
  - Confidence: 🟢

- [ ] **T-IP-15 — `_resolve_scale_factor` and the 400/422 split.**
  `SCALE_FACTOR ∈ (0.001, 10.0)`, `TARGET_SPAN ∈ (0.1, 50.0) m`. Mutex is
  rejected at the endpoint → 400; out-of-range and wingless `target_span_m`
  raise `ScaleValidationError` → 422.
  `_compute_max_wing_span = 2·max|y_le|` symmetric, `max|y_le|` otherwise.
  - Legacy origin: `openvsp_import_service.py:78-81`;
    `openvsp_import.py:139-146`
  - Definition of done: all four cases produce the documented status.
  - Confidence: 🟢

- [ ] **T-IP-16 — Apply the scale with an epsilon and always warn.**
  Apply only when `|factor − 1.0| > 1e-9` (Sonar S1244; the UI step is `0.01`),
  and append exactly one `info` `SCALING` warning naming the factor and stating
  that masses were not scaled.
  - Legacy origin: `openvsp_import_service.py:1113-1120`; `_make_scaling_warning`
  - Definition of done: a scaled import has one `SCALING` warning; an unscaled
    import has none; `twist` and masses are bit-identical either way.
  - Confidence: 🟢

- [ ] **T-IP-17 — The three-stage order (gh-765 / gh-769).**
  1) unit conversion of the whole aeroplane, 2) `_scale_aeroplane_lengths`,
  3) fuselage x-secs last inside `_persist_aeroplane` after the slicer, then
  `scale_geom_step` on the stored STEP files.
  - Legacy origin: `openvsp_import_service.py:1071-1133, 960-1005`
  - Definition of done: the slicer input is unscaled; the persisted x-secs and
    the stored STEP are both scaled and agree.
  - Confidence: 🟢

### Persistence

- [ ] **T-IP-18 — `_persist_aeroplane` per-record best-effort.**
  Each wing, fuselage and weight item in its own `try/except`; failures become
  warnings via `_record_persist_failure` and the rest still persist.
  - Legacy origin: `openvsp_import_service.py:804-1020`
  - Definition of done: with one wing forced to fail, the aeroplane, the other
    wings and every fuselage exist and a `WING` warning is present.
  - Confidence: 🟢

- [ ] **T-IP-19 — Aeroplane name precedence.**
  Explicit `name` (whitespace-only ignored) → uploaded filename stem → parsed
  model name; thread `source_filename` through so the persisted name is never
  the `NamedTemporaryFile` stem.
  - Legacy origin: `_resolve_aeroplane_name`; `openvsp_import_service.py:828-834`
  - Definition of done: `cessna172.vsp3` with no `name` yields `"cessna172"`.
  - Confidence: 🟢

- [ ] **T-IP-20 — Wings persist through the geometry-only write schema.**
  Map to `AsbWingGeometryWriteSchema` with exactly `xyz_le`, `chord`, `twist`,
  `airfoil`, `x_sec_type`, `tip_type`, `number_interpolation_points`. Record the
  consequence in a comment tied to BR-OV16: no TED, turbulator, spar or explicit
  `dihedral` can cross this boundary.
  - Legacy origin: `openvsp_import_service.py:846-865`;
    `app/schemas/aeroplaneschema.py:592-708`
  - Definition of done: a test pins the exact field set and links it to
    BR-OV16 so the limitation is not rediscovered.
  - Confidence: 🟢 (whether it *should* be geometry-only is 🔴)

### REST and streaming

- [ ] **T-IP-21 — The JSON endpoint and its status ladder.**
  503 (bindings) → 400 (not `.vsp3`) → 400 (mutex) → 413 (> 50 MB) → parse →
  500 (`FileNotFoundError`) / 503 (`ImportError`) / 422 (`ScaleValidationError`)
  / 422 (anything else, logged with `logger.exception`) → 201. Run both the
  temp-file write and the import on `asyncio.to_thread` (Sonar S7493).
  - Legacy origin: `app/api/v2/endpoints/openvsp_import.py:50, 123-215`
  - Definition of done: contract tests cover every row of the table in
    [`../contracts.md`](../contracts.md).
  - Confidence: 🟢

- [ ] **T-IP-22 — Temp-file cleanup on every path.**
  `finally: await asyncio.to_thread(tmp_path.unlink, missing_ok=True)`, with a
  `logger.warning` when the unlink fails.
  - Legacy origin: `openvsp_import.py` (both routes)
  - Definition of done: no temp file remains after success, after any error, or
    after a mid-stream disconnect.
  - Confidence: 🟢

- [ ] **T-IP-23 — The SSE endpoint.**
  Same up-front validation so a client never opens a stream to receive an error.
  `asyncio.Queue` + `loop.call_soon_threadsafe` from the worker thread, a
  private `_DONE` sentinel, `await import_task` in the generator's `finally`,
  `media_type="text/event-stream"`, headers `X-Accel-Buffering: no` and
  `Cache-Control: no-cache`. `_sse_format` emits compact JSON because a `data:`
  line may not contain newlines.
  - Legacy origin: `openvsp_import.py:258-385`
  - Definition of done: a successful run emits progress then exactly one
    `complete`; a failure emits exactly one `error` carrying
    `{"status": 422 | 503, "detail": …}`.
  - Confidence: 🟢

- [ ] **T-IP-24 — The progress vocabulary.**
  `parsing 5` → `parsing 15` → (`units 16`) → (`scaling 18`) → `aeroplane 20` →
  `wing 25 + int(5(i+1)/n)` → `fuselage 30 + int(55/n · i)` (the three
  `fuselage_*` sub-steps are owned by the STEP slice) → (`weight_items 90`) →
  `finalising 95`.
  - Legacy origin: `openvsp_import_service.py:834, 842, 895-905, 1009,
    1071-1133`
  - Definition of done: `pct` is non-decreasing and never exceeds 95; `units`,
    `scaling` and `weight_items` are absent when inapplicable.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-IP-01 — Happy path:** a fixture with 2 wings and 1 fuselage imports
      with 201 and the expected counts.
- [ ] **TT-IP-02 — Status ladder:** `.stl` → 400; both scale params → 400; 51 MB
      → 413; `scale_factor = 20` → 422; wingless `target_span_m` → 422; bindings
      absent → 503; patched `FileNotFoundError` → 500.
- [ ] **TT-IP-03 — Model isolation:** import A then B in one process; B's
      aeroplane has none of A's geoms.
- [ ] **TT-IP-04 — Canonicalisation matrix:** all 16 entries plus an `.upper()`
      fallback.
- [ ] **TT-IP-05 — Unsupported geoms:** each of the 14 tokens yields a warning
      plus one `lossy_components` entry, with a 201 response.
- [ ] **TT-IP-06 — Context invariants:** duplicate `mark_lossy` collapses; an
      invalid severity is rejected.
- [ ] **TT-IP-07 — Post-pass failure:** a raising post-pass yields a
      `POST_PASS` warning and a 201.
- [ ] **TT-IP-08 — Unit snap table:** `0.3048 → ft`, `0.0254 → in`,
      `1.0 → None`, `0.5 → None`, `NaN → None`, `−1 → None`, and both ±2 %
      boundaries.
- [ ] **TT-IP-09 — Unit detection end to end:** a feet fixture converts and
      warns; a fuselage-less fixture is reported (`Q-VI-3`); the
      `_unitdetect_*` directory is removed even when the measurement raises.
- [ ] **TT-IP-10 — Scaling invariants:** every `twist` and mass bit-identical
      after a rescale; exactly one `SCALING` warning; no warning when
      `|factor − 1| ≤ 1e-9`.
- [ ] **TT-IP-11 — Scaling order:** the slicer receives the unscaled STEP; the
      persisted x-secs and the stored STEP both end up scaled.
- [ ] **TT-IP-12 — Per-record best-effort:** one failing wing yields a `WING`
      warning while everything else persists.
- [ ] **TT-IP-13 — Name precedence:** explicit name wins; whitespace-only is
      ignored; the filename stem beats the parsed name; `tmpXXXX` never appears.
- [ ] **TT-IP-14 — Write-schema field set:** assert exactly the seven fields, so
      the BR-OV16 boundary is visible in the test suite.
- [ ] **TT-IP-15 — SSE sequence:** non-decreasing `pct` ≤ 95, conditional steps
      omitted, exactly one terminal event, `error` carrying `{status, detail}`.
- [ ] **TT-IP-16 — Temp-file cleanup** on success, error and disconnect.
- [ ] **TT-IP-17 — 🟡 Registration diagnostics** (`Q-VI-7`): with one handler module
      raising `ImportError`, the import still runs and the failure is logged.
- [ ] **TT-IP-18 — 🟢 SS_CONTROL reaches the pipeline** (`Q-VI-1`) *(expected to fail until
      T-IP-10 **and** `../geom-handlers/` T-GH-13 both land)*: drive the
      production entry point and observe the post-pass running.
- [ ] **TT-IP-19 — 🟢 `validate_geometry` wired** (`Q-VI-2`): a mis-derived planform warns
      through the production pipeline.

## Suggested Order

1. **T-IP-01 → T-IP-03** — the adapter and registry; everything else calls
   them. T-IP-02's diagnostic fix is cheap and prevents a whole class of silent
   degradation.
2. **T-IP-08** early — every other task reports through `ImportContext`, so the
   structures must exist before the sequence work.
3. **T-IP-04 → T-IP-07, T-IP-09** — the critical sequence and dispatch. Write
   TT-IP-03 (model isolation) before any handler work begins.
4. **T-IP-12 → T-IP-17** — units and scaling. T-IP-12 blocks T-IP-13; T-IP-13
   and T-IP-15 both block T-IP-17. T-IP-13 depends on `export_geom_step` from
   the STEP slice, so that slice's T-SE-01 must land first.
5. **T-IP-18 → T-IP-20** — persistence, which must respect T-IP-17's ordering.
   Land T-IP-20 **consciously**: it is the boundary that forecloses control
   surfaces.
6. **T-IP-21 → T-IP-24** — the REST and SSE layer, thin and last.
7. **T-IP-10 / T-IP-11** — the two inert registrations, once a decision exists.
   T-IP-10 must land together with `../geom-handlers/` T-GH-13.

## Pending Gaps

- **Was the SS_CONTROL post-pass parked deliberately, or lost in a merge?** It
  is complete and tested and called from nowhere in production.
- **Was `validate_geometry` parked deliberately?** Same shape of problem, same
  question.
- **Should a failed handler registration be logged, raised, or surfaced as an
  import warning?**
- **Should a unitless legacy file warn?** `LEN_UNITLESS → 1.0` silently assumes
  metres.
- **Is there a wing-based fallback for source-unit detection**, or should the UI
  force an explicit unit choice for fuselage-less models?
- **Should `n_wings` / `n_fuselages` count parsed or persisted components?**
- **Should the wing import path carry more than geometry?** The `extra="forbid"`
  write schema silently forecloses TEDs, turbulators, spars and explicit
  dihedral.
- **Is concurrency in scope?** The native VSP model, the adapter memo and the
  handler registry are process-global with no lock.
- **Should a mid-stream disconnect abort the import?** Today the generator's
  `finally` awaits the task, so an aeroplane is created for a client that has
  gone away.
