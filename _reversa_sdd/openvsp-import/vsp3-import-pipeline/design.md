# vsp3-import-pipeline — Technical Design

> Use-case design, nested under the module
> [`openvsp-import`](../design.md). Focuses on HOW this slice is built.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Endpoint contract in full: [`../contracts.md`](../contracts.md).
> Sibling slices: [`../geom-handlers/`](../geom-handlers/design.md),
> [`../step-export-and-sewing/`](../step-export-and-sewing/design.md).

## Interface

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `openvsp_adapter.is_available` | `()` | `bool` | memoised |
| `openvsp_adapter.get_vsp` | `()` | module | raises `ImportError(_OPENVSP_MISSING_MSG)` |
| `openvsp_adapter.reset_for_tests` | `()` | `None` | l.92-97, the only memo reset |
| `openvsp_importer.import_vsp3` | `(path)` | `ImportResult` | l.324-420 |
| `openvsp_importer._ensure_handlers_loaded` | `()` | `None` | l.287-321 |
| `openvsp_importer._canonicalize_geom_type` | `(display_name)` | `str` | l.194-211 + `.upper()` |
| `openvsp_importer._read_source_length_unit` | `(vsp, vehicle_id)` | `int \| None` | `""` ⇒ `None` |
| `openvsp_import_service.import_openvsp_file` | `(db, path, *, target_span_m=None, scale_factor=None, name=None, source_filename=None, progress_cb=_noop_progress)` | `OpenVspImportResponse` | l.1025-1145 |
| `openvsp_import_service.is_importer_available` | `()` | `bool` | the 503 gate |
| `openvsp_import_service._snap_to_unit_scale` | `(raw_ratio)` | `(str, float) \| None` | l.108-126 |
| `openvsp_import_service._detect_source_scale_to_meters` | `(vsp, aeroplane, fuselage_geom_ids, detect_uuid)` | `(str, float) \| None` | l.147-201 |
| `openvsp_import_service._convert_aeroplane_to_metres` | `(aeroplane, factor, weight_items=None)` | `None` | scales **everything** |
| `openvsp_import_service._scale_aeroplane_lengths` | `(aeroplane, factor, weight_items=None)` | `None` | l.254-293, **no fuselages** |
| `openvsp_import_service._resolve_scale_factor` | `(aeroplane, target_span_m, scale_factor)` | `float \| None` | raises `ScaleValidationError` |
| `openvsp_import_service._persist_aeroplane` | `(db, result, *, name, source_filename, progress_cb, scale_factor)` | `(uuid, name)` | l.804-1020 |
| `ProgressCallback` | `Callable[[str, int, str], None]` | — | default `_noop_progress` (l.50) |

### Data structures 🟢

`ImportWarning` (frozen dataclass, `openvsp_importer.py:84`):

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `component_type` | `str` | yes | — | `WING`, `FUSELAGE`, `WING_XSEC`, `WING_SS_CONTROL`, `SCALING`, `UNITS`, `POST_PASS`, or a geom token |
| `component_name` | `str` | yes | — | geom / sub-surface name; the unit name for `UNITS` |
| `reason` | `str` | yes | — | user-facing text, rendered by the frontend banner (gh-648) |
| `severity` | `Literal["info","warning","error"]` | no | `"warning"` | validated in `ImportContext.add_warning` |

`ImportContext` (mutable collector, l.99): `warnings`, `lossy_components`
(de-duplicated by `mark_lossy`), `weight_items`, `source_length_unit`,
`source_scale_to_meters`, `wing_geom_ids` (gid → schema name, consumed by the
SS_CONTROL pass), `fuselage_geom_ids` (gid → schema name, consumed by the
STEP-export pass).

`ImportResult` (l.145): `aeroplane: AeroplaneSchema`, `warnings`,
`lossy_components`, `weight_items`, `source_length_unit`,
`source_scale_to_meters`, `fuselage_geom_ids`.

## Main Flow

### F1 — `import_vsp3` — the gh-640 critical sequence 🟢

```
_ensure_handlers_loaded()          # lazy, once per process
vsp.ClearVSPModel()                # without this, ReadVSPFile MERGES into current state
vsp.ReadVSPFile(path)
source_unit = _read_source_length_unit(vsp, vsp.GetVehicleID())
if hasattr(vsp, "SetLengthUnit"): vsp.SetLengthUnit(vsp.LEN_M)   # legacy only
vsp.Update()
for gid in vsp.FindGeoms(): dispatch or warn
for fn in _POST_PASSES: fn(aeroplane, ctx, vsp)
```

1. **`_ensure_handlers_loaded`** (l.287-321) imports and registers exactly four
   modules — wing, fuselage, blank, custom — each inside its own
   `try: … except ImportError: pass`. Registered post-passes:
   `openvsp_blank_handler._resolve_vehicle_cg` and
   `openvsp_fuselage_handler._drop_degenerate_fuselages`.
   🟡 **A failed handler registration is reported, not swallowed** (`Q-VI-7`, derived from `P-WARN-0`).
   🟢 **Wired fully — registration AND the write path** (`Q-VI-1`, maintainer-answered).
2. **`ClearVSPModel()`** — mandatory; see BR-OV1.
3. **`_read_source_length_unit`** — `FindParm(vehicle_id, "LengthUnit",
   "Vehicle_Info")`. OpenVSP prints `Can't Find Parm` to **stderr** but returns
   `""` rather than raising, so the empty-string test is the only reliable
   check. On 3.50+ the parm and `SetLengthUnit` are both gone (l.352-368 and the
   module docstring). `LEN_UNIT_TO_METERS` (l.63-71):
   `0 mm 0.001 · 1 cm 0.01 · 2 m 1.0 · 3 in 0.0254 · 4 ft 0.3048 · 5 yd 0.9144 ·
   6 unitless 1.0`. 🟡 `LEN_UNITLESS → 1.0` is reported, not assumed (`Q-VI-3`).
4. **Dispatch** — `GetGeomTypeName(gid)` → `_canonicalize_geom_type` →
   `_HANDLERS.get(token)`; a miss emits `_UNSUPPORTED_REASONS[token]` (or
   `"not supported in Phase 1"`) plus `ctx.mark_lossy(gid)`.
5. **Post-passes** — a raise becomes a `POST_PASS` warning (l.401-410), never a
   failed import.

`_DISPLAY_TO_CANONICAL` (l.194-211, 16 entries): `Wing→WING`,
`Fuselage→FUSELAGE`, `Custom→CUSTOM`, `Pod→POD`, `Stack→STACK`,
`Blank→BLANK`, `Ellipsoid→ELLIPSOID`, `BodyOfRevolution→BOR`, `Human→HUMAN`,
`Propeller→PROP`, `Gear→GEAR`, `Hinge→HINGE`, `Conformal→CONFORMAL`,
`Routing→ROUTING`, `Auxiliary→AUXILIARY`, `Cobra→COBRA`; fallback `.upper()`.
🟢

### F2 — Source-unit detection (gh-808) 🟢

```
fuselages present?             no → None (import unchanged)
ref  = fuselage with the largest handler X-span
gid  = invert fuselage_geom_ids by schema name
gid is None or handler_span ≤ 1e-6            → None
rel  = export_geom_step(vsp, gid, ref_name, aeroplane_uuid=f"_unitdetect_{path.stem}")
rel falsy                                     → None
bb   = cq.importers.importStep(ARTIFACTS_BASE_DIR / rel).val().BoundingBox()
metric_span = bb.xlen / 1000.0                # OCC normalises STEP to millimetres
return _snap_to_unit_scale(metric_span / handler_span)

except Exception: log at info, return None    # best-effort, never fatal
finally:          shutil.rmtree(step_storage_dir("_unitdetect_…")) if it exists
```

`_snap_to_unit_scale` (l.108-126):

```
not finite or ratio ≤ 0                       → None
for name, factor in _LENGTH_UNIT_FACTORS:                # m 1.0, yd 0.9144,
    if |ratio − factor| ≤ _UNIT_SNAP_TOL · factor:       # ft 0.3048, in 0.0254,
        keep the NEAREST match                           # cm 0.01, mm 0.001
best is None or best name == "m"              → None     # metres: nothing to do
else                                          → (name, factor)
```

The window is **relative to each factor** (`_UNIT_SNAP_TOL = 0.02`). Because the
factors are ≥3× apart (nearest pair ft/yd), ±2 % absorbs slicer and
bounding-box noise without ever aliasing between units. 🟢

On a hit, `_convert_aeroplane_to_metres` scales the **whole** aeroplane —
including fuselage x-secs, unlike `_scale_aeroplane_lengths` — and appends:

```
ImportWarning(component_type="UNITS", component_name=<unit>,
              reason="Source model detected as '<unit>' (no length unit is stored
                      in OpenVSP 3.50 files); converted to metres (×f).
                      Verify the scale before use.",
              severity="warning")
```

🟡 Detection **requires a fuselage**; a wing-only model is reported rather than silently scaled (`Q-VI-3`). Today it returns `None` and a
feet-unit flying wing imports 3.28× too large in silence.

### F3 — Scaling resolution and the three-stage order 🟢

```
factor = _resolve_scale_factor(aeroplane, target_span_m, scale_factor)
    (mutex is rejected earlier, at the endpoint → 400)
    out of range → ScaleValidationError → 422
        SCALE_FACTOR ∈ (0.001, 10.0) · TARGET_SPAN ∈ (0.1, 50.0) m
    target_span_m with no wings → ScaleValidationError → 422
    target_span_m → factor = target / _compute_max_wing_span(aeroplane)
        _compute_max_wing_span = 2·max|y_le| (symmetric) else max|y_le|

if factor is not None and |factor − 1.0| > 1e-9:      # S1244 epsilon,
    progress_cb("scaling", 18, f"Scaling by {factor:g}")   # UI step is 0.01
    _scale_aeroplane_lengths(aeroplane, factor, weight_items)
    warnings.append(_make_scaling_warning(factor, target_span_m, scale_factor))
```

**The order across the whole request** (gh-765):

```
1. unit conversion    — WHOLE aeroplane incl. fuselages  (_convert_aeroplane_to_metres)
2. rescale            — wings, xyz_ref, weight positions (_scale_aeroplane_lengths)
3. fuselage x-secs    — LAST, inside _persist_aeroplane, AFTER the slicer ran in
                        the UNSCALED STEP frame; then scale_geom_step rescales
                        the stored STEP files (gh-769)
```

Stage 3 exists so the slicer never sees a scaled frame. Reordering silently
mismatches the persisted x-secs against the downloadable STEP.

### F4 — `_persist_aeroplane` 🟢

```
resolved_name = _resolve_aeroplane_name(explicit_name, source_filename, parsed_name)
aeroplane     = aeroplane_service.create_aeroplane(db, resolved_name)   # pct 20

per wing i of n:                                                        # pct 25…30
    progress_cb("wing", 25 + int(5*(i+1)/max(n,1)), f"Wing {i+1}/{n}: {name}")
    write = AsbWingGeometryWriteSchema(name, symmetric, x_secs=[{
        xyz_le, chord, twist, airfoil, x_sec_type, tip_type,
        number_interpolation_points }])
    wing_service.create_wing(db, aeroplane.uuid, wing_name, write)
    except → _record_persist_failure(component_type="WING")

per fuselage i of n:            # pct 30…85, fuselage_span_pct = 55
    base = 30 + int(55/max(n,1) * i)
    fuselage_service.create_fuselage(...)   except → warn + continue
    (STEP export / sewing / slicing — see ../step-export-and-sewing/)
    scaling = |scale_factor − 1.0| > 1e-9
    if scaling:               _replace_fuselage_xsecs(scale(refined or handler))
    elif refined is not None: _replace_fuselage_xsecs(refined)
    if scaling:               scale_geom_step(rel_step / rel_solid, scale_factor)

per weight item:                                                        # pct 90
    persist via the mass-properties entry point   except → warn
```

Details a re-implementation needs:

- **Name precedence** — explicit `name` (whitespace-only ignored) → uploaded
  filename stem → parsed model name. Without `source_filename` the persisted
  name would be the `NamedTemporaryFile` stem (`tmpXXXX`). 🟢
- **Wings go through the geometry-only write schema**
  (`AsbWingGeometryWriteSchema`, `extra="forbid"`, whose
  `WingXSecGeometryWriteSchema` has exactly the seven fields listed above). This
  is the boundary that forecloses trailing-edge devices, turbulators, spars and
  explicit `dihedral` — see BR-OV16. 🟢
- Consequently every imported wing carries `design_model = 'asb'` and
  `wing_xsecs.dihedral = NULL`. 🟡 Interior dihedral is implicit in `xyz_le`;
  the terminal rib's rotation (`wing-design` BR-7 / gh-951) is lost.
- Weight items are written through the same entry point the manual
  mass-properties UI uses, so categories, CG-recompute hooks and validation stay
  aligned. 🟢

### F5 — REST and SSE 🟢

Both routes share the up-front validation ladder:

```
is_importer_available()          false → 503
filename.lower().endswith(".vsp3") no  → 400
target_span_m and scale_factor both    → 400   (request shape)
len(raw) > 50 MB                       → 413
tmp_path = await asyncio.to_thread(_write_temp)     # NamedTemporaryFile(".vsp3")
```

**JSON route** — `await asyncio.to_thread(import_openvsp_file, …)` with
`except FileNotFoundError → 500`, `except ImportError → 503`,
`except ScaleValidationError → 422`, `except Exception → 422` (logged with
`logger.exception`), and `finally: await asyncio.to_thread(tmp_path.unlink,
missing_ok=True)`. Returns 201 + `OpenVspImportResponseModel`. 🟢

**SSE route** — an `asyncio.Queue` with a private `_DONE` sentinel:

```
progress_cb(step, pct, detail)          # called SYNCHRONOUSLY from the worker thread
    → loop.call_soon_threadsafe(queue.put_nowait, ("progress", {...}))

run_import()  (asyncio.create_task)
    ok        → queue.put_nowait(("complete", {…same body as the JSON route…}))
    Scale…    → ("error", {"status": 422, "detail": …})
    ImportErr → ("error", {"status": 503, "detail": …})
    other     → ("error", {"status": 422, "detail": f"Failed to parse …"})
    finally   → unlink the temp file, then put _DONE

generator: drain the queue, yield _sse_format(type, payload) until _DONE
    finally: await import_task
```

`_sse_format` emits `event: <type>\ndata: <compact JSON>\n\n` — always
JSON-serialised because a `data:` line may not contain newlines.
`StreamingResponse(media_type="text/event-stream")` with
`X-Accel-Buffering: no` and `Cache-Control: no-cache`. 🟢

> 🟡 The generator's `finally` **awaits** the import task, so a client that
> disconnects mid-stream still causes the aeroplane to be created.

## Alternative Flows

- **Bindings absent:** 503 before any file is read; a later `ImportError` also
  maps to 503. 🟢
- **Bad extension / mutex / oversize:** 400 / 400 / 413, all before parsing. 🟢
- **Temp file vanished:** `FileNotFoundError` → **500** — the only 5xx path in
  the module. 🟢
- **Any other parse failure:** `logger.exception` + **422**. 🟢
- **Unsupported geom / handler raises:** warning + `mark_lossy`, import
  continues. 🟢
- **Post-pass raises:** `POST_PASS` warning. 🟢
- **Handler module fails to import:** absent from `_HANDLERS`; every geom of
  that type reports "unsupported". 🟡 **A failed handler registration is reported, not swallowed** (`Q-VI-7`, derived from `P-WARN-0`).
- **Unit detection impossible** (no fuselage, no CadQuery, export/measure
  failure, unmatched ratio): skipped, import unchanged. 🟢
- **Factor within `1e-9` of 1.0:** no scaling, no `SCALING` warning. 🟢
- **A single record fails to persist:** warning, the rest persists. 🟢
- **Client disconnects mid-stream:** the import still completes. 🟡

## Dependencies

- **`openvsp` (optional, SWIG)** — probed by `openvsp_adapter`; ADR 0017.
- **CadQuery/OCCT (optional)** — only for the bounding-box measurement in F2.
- **`app.services.openvsp_step_export_service`** — F2 borrows `export_geom_step`
  and `step_storage_dir` (→ [`../step-export-and-sewing/`](../step-export-and-sewing/design.md)).
- **`aeroplane-core`, `wing-design`, `fuselage-design`, `mass-and-balance`** —
  the four persistence entry points.
- **`platform-core`** — `settings.ARTIFACTS_BASE_DIR`, `get_db()` transaction
  ownership (ADR 0009).
- **The geom handlers** — registered by this slice, specified in
  [`../geom-handlers/`](../geom-handlers/design.md).

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Reset the native model before every read rather than isolating per request | `import_vsp3` (`ClearVSPModel` first) — the SWIG model is process-global and cannot be instanced | 🟢 |
| Memoise the optional import with a test-only reset | `openvsp_adapter.py:53-55, 92-97` | 🟢 |
| Register handlers lazily and tolerate individual failures | `_ensure_handlers_loaded:287-321` | 🟢 (silence 🔴) |
| Treat `FindParm`'s empty string as "not found" instead of trusting stderr | `_read_source_length_unit` | 🟢 |
| Measure the source unit rather than trusting the file | gh-808; `:147-201` | 🟢 |
| Use a **relative** ±2 % snap window and reject unmatched ratios | `_snap_to_unit_scale:108-126` | 🟢 |
| Convert units for the whole aeroplane but rescale only lengths | `_convert_aeroplane_to_metres` vs `_scale_aeroplane_lengths:254-293` | 🟢 |
| Defer fuselage x-secs to the persist path so the slicer stays unscaled | gh-765 | 🟢 |
| Split mutex (400) from range (422) | `openvsp_import.py:139-146` vs `_resolve_scale_factor` | 🟢 |
| Persist per record rather than transactionally | `_persist_aeroplane`; `_record_persist_failure` | 🟢 |
| Persist wings through the geometry-only write schema | `:846-865`; `aeroplaneschema.py:695-708` | 🟢 (intent 🔴) |
| Carry the intended HTTP status in-band on SSE errors | `openvsp_import.py` `run_import` | 🟢 |
| Allocate 55 of 100 progress points to fuselages | `:895-905` | 🟢 |

## Internal State

**Process-global and surviving `--reload`** — the defining property of this
slice:

| State | Where | Reset by |
|---|---|---|
| `_cached_module`, `_import_attempted`, `_import_error` | `openvsp_adapter.py:53-55` | `reset_for_tests()` only |
| `_handlers_loaded`, `_HANDLERS`, `_POST_PASSES` | `openvsp_importer.py:181-182, 284` | nothing |
| the native VSP model | the `openvsp` SWIG module | `ClearVSPModel()` per read |

🟡 There is **no lock**. Two concurrent imports in one process would interleave
on the native model; concurrency safety is not addressed anywhere.

**Per-request:** `ImportContext` → `ImportResult`, discarded after the response
is built. The `asyncio.Queue` of the SSE route lives for the request only.

## Observability

- **Structured warnings** are the primary channel (ADR 0012) — they reach the
  response body and the frontend banner (gh-648). 🟢
- **SSE progress**: `parsing 5` → `parsing 15` → (`units 16`) → (`scaling 18`)
  → `aeroplane 20` → `wing 25…30` → `fuselage 30…85` (+ the three sub-steps
  owned by the STEP slice) → (`weight_items 90`) → `finalising 95`. Three steps
  are conditional; `pct` never reaches 100. 🟢
- `logger.exception("OpenVSP import failed")` / `"OpenVSP import (stream)
  failed"` on the 422 catch-all; `logger.info(..., exc_info=True)` on
  best-effort unit detection; `logger.warning` when a temp file cannot be
  removed. 🟢
- 🔴 No metric or event distinguishes a clean import from one with 40 warnings.
- 🔴 A handler module that fails to import logs nothing at all.

## Risks and Gaps

- 🔴 **`except ImportError: pass` on handler registration** turns a broken
  module into "unsupported geom type" with no diagnostic.
- 🔴 **`openvsp_ss_control.register()` is missing from this slice**, which is
  the root cause of imported aircraft having no control surfaces (BR-OV16). The
  fix belongs here; the second half of the fix belongs to the persistence write
  schema.
- 🔴 **`validate_geometry` is never called from `import_vsp3`** (BR-OV17).
- 🔴 **Unit detection needs a fuselage** — a flying wing in feet imports 3.28×
  too large, silently.
- 🔴 **`LEN_UNITLESS → 1.0`** assumes metres without a warning.
- 🔴 **`n_wings` / `n_fuselages` count parsed, not persisted, components**, so a
  persistence failure inflates them; only the warning reveals it.
- 🟡 **Concurrency** on the process-global VSP model, adapter memo and handler
  registry is unguarded.
- 🟡 **A mid-stream disconnect still creates an aeroplane** because the
  generator's `finally` awaits the task.
- 🟡 **`FileNotFoundError → 500` is the module's only 5xx**, which sits oddly
  beside a policy where everything else degrades to a warning or a 4xx.
