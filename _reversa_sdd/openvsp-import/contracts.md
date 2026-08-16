# openvsp-import — External Contracts

> REST contract exactly as captured in `code-analysis.md` §Module: openvsp-import
> and re-verified against `app/api/v2/endpoints/openvsp_import.py` (385 l.).
> ⚠ **Unlike the aeroplane routers, these two routes DO carry the `/api/v2`
> prefix.** 🟢 The router is mounted with that prefix and the paths are
> `/import/openvsp` and `/import/openvsp/stream`.
> There is no aeroplane id in the request — the import **creates** one.

## Availability gate 🟢

Both routes begin with `openvsp_import_service.is_importer_available()`. When
the optional `openvsp` package is absent the route answers **503** with a detail
pointing at `docs/md/openvsp-import-setup.md` — it is **not** conditionally
unmounted the way the CAD router is (ADR 0017 uses both patterns; this module
uses the in-handler probe).

## Error contract 🟢

This module does **not** use the `_raise_http_from_domain` envelope of the
aeroplane routers. It raises `HTTPException` directly, so the body is FastAPI's
`{"detail": "…"}` shape.

| Condition | HTTP | Where |
|---|---|---|
| `openvsp` bindings not installed (pre-check) | **503** | `openvsp_import.py:123-131` |
| `ImportError` raised during the import | **503** | endpoint `except ImportError` |
| Filename does not end `.vsp3` (case-insensitive) | **400** | `"Expected a .vsp3 file upload."` |
| `target_span_m` **and** `scale_factor` both supplied (mutex — a request-shape error) | **400** | `"…are mutually exclusive; specify at most one."` |
| Upload larger than `_MAX_FILE_SIZE_BYTES = 50 × 1024 × 1024` | **413** | `"Upload exceeds the 50 MB size limit."` |
| `ScaleValidationError` — out-of-range value, or `target_span_m` on a wingless aeroplane | **422** | raised by `_resolve_scale_factor` |
| Any other parse/import exception | **422** | `"Failed to parse OpenVSP file: {exc}"`, logged with `logger.exception` |
| `FileNotFoundError` — the temp file vanished mid-import | **500** | `"Temp file vanished during import: {exc}"` |
| Success | **201** | `OpenVspImportResponseModel` |

> ⚠ **The mutex/range split is deliberate.** Supplying two contradictory
> parameters is a *request shape* problem (400); a single well-formed but
> unusable value is a *semantic* problem (422). A re-implementation that
> collapses both into 422 changes the contract. 🟢

> 🟡 Note the asymmetry: `FileNotFoundError` is the only condition in this module
> that produces a 5xx. Every other failure is either a 4xx or a warning.

## Unit contract 🟢

| Quantity | Wire unit | Note |
|---|---|---|
| `target_span_m` | metres | `(0.1, 50.0)`, exclusive-ish bounds enforced by `_resolve_scale_factor` |
| `scale_factor` | dimensionless | `(0.001, 10.0)` |
| persisted wing `xyz_le`, `chord` | metres | the DB world (ADR 0001) |
| persisted wing `twist` | degrees | **never scaled** |
| persisted fuselage x-secs | metres | scaled last, after slicer refinement (gh-765) |
| weight-item `x_m` / `y_m` / `z_m` | metres | scaled |
| weight-item mass | kg | **never scaled** (ADR 0018) |
| exported STEP files | **metres** in the file (`STEPSettings.LenUnit = LEN_M`); OCC normalises to **mm** on read | this is what makes source-unit detection possible |

The source file itself carries **no unit** on OpenVSP 3.50+. The importer
measures it (gh-808) and emits a `UNITS` warning when it converts. 🟢

## `POST /api/v2/import/openvsp` 🟢

| | |
|---|---|
| Handler | `import_openvsp` |
| `operation_id` | `import_openvsp_vsp3` |
| Tags | `import` |
| Success status | **201 CREATED** |
| Response model | `OpenVspImportResponseModel` |

### Request

| Part | Kind | Type | Required | Constraint |
|---|---|---|---|---|
| `file` | multipart `File(...)` | `UploadFile` | yes | filename must end `.vsp3`; body ≤ 50 MB |
| `target_span_m` | **query** | `float \| None` | no | `(0.1, 50.0)` m; mutually exclusive with `scale_factor` |
| `scale_factor` | **query** | `float \| None` | no | `(0.001, 10.0)`; mutually exclusive with `target_span_m` |
| `name` | **query** | `str \| None` | no | `max_length=200`; whitespace-only is treated as "no override" |

Only `file` is multipart — the three tuning parameters are **query
parameters**, not form fields. 🟢

**Name resolution precedence:** explicit `name` → uploaded filename stem →
the name parsed from the model. `source_filename` is passed explicitly so the
persisted name is never the `NamedTemporaryFile` stem (`tmpXXXX`). 🟢

### Response — `OpenVspImportResponseModel`

| Field | Type | Notes |
|---|---|---|
| `aeroplane_uuid` | `str` | public UUID of the created aeroplane |
| `aeroplane_name` | `str` | resolved per the precedence above |
| `n_wings` | `int` | wings **parsed** (a wing that failed to persist still counts, and appears as a warning) 🟡 |
| `n_fuselages` | `int` | fuselages parsed |
| `n_weight_items` | `int` | weight items parsed |
| `warnings` | `list[ImportWarningResponse]` | see the vocabulary below |
| `lossy_components` | `list[str]` | de-duplicated geom **ids** that were dropped or partially imported |

`ImportWarningResponse`:

| Field | Type | Notes |
|---|---|---|
| `component_type` | `str` | see the vocabulary below |
| `component_name` | `str` | geom or sub-surface name (for `UNITS`, the detected unit name) |
| `reason` | `str` | user-facing text rendered by the frontend banner (gh-648) |
| `severity` | `str` | `info` \| `warning` \| `error` |

## `POST /api/v2/import/openvsp/stream` (SSE) 🟢

| | |
|---|---|
| Handler | `import_openvsp_stream` |
| `operation_id` | `import_openvsp_vsp3_stream` |
| Success status | **200** (not 201 — it is a stream) |
| Media type | `text/event-stream` |
| Headers | `X-Accel-Buffering: no`, `Cache-Control: no-cache` (so nginx does not buffer) |

Same request contract and the same up-front validation as the JSON route
(503 / 400 / 413 are raised **before** the stream opens, so a client never opens
a stream just to receive an error frame). Documented `responses` on the route:
200 (stream), 400, 413, 503. 🟢

### Frame format

`_sse_format` emits `event: <type>\ndata: <compact JSON>\n\n`, always
JSON-serialised because a `data:` line may not contain newlines. 🟢

| Event | Payload |
|---|---|
| `progress` | `{"step": str, "pct": int, "detail": str}` |
| `complete` | the same body as the JSON endpoint: `{aeroplane_uuid, aeroplane_name, n_wings, n_fuselages, n_weight_items, warnings, lossy_components}` |
| `error` | `{"status": 422 \| 503, "detail": str}` |

> ⚠ The `error` payload carries a **`status` field** alongside `detail` — the
> stream cannot use an HTTP status once the response has begun, so the intended
> status is carried in-band. `ScaleValidationError` → `422`, `ImportError` →
> `503`, anything else → `422`. 🟢

Exactly one `complete` **or** one `error` is emitted, then the stream ends.

### Progress vocabulary 🟢

| `step` | `pct` | Emitted when |
|---|---|---|
| `parsing` | `5` | before `import_vsp3` — "Reading .vsp3 file" |
| `parsing` | `15` | after parsing — "Parsed N wing(s), M fuselage(s)" |
| `units` | `16` | only when a non-metre source unit was detected — "Source unit ft → metres" |
| `scaling` | `18` | only when `|factor − 1| > 1e-9` — "Scaling by 0.2" |
| `aeroplane` | `20` | the aeroplane row was created |
| `wing` | `25 + int(5·(i+1)/n_wings)` | per wing, so wings occupy `25…30` |
| `fuselage` | `30 + int(55/n_fuselages · i)` | per fuselage; fuselages occupy the `30…85` band (`fuselage_span_pct = 55`) |
| `fuselage_step` | base `+ 0.25 · step` | "exporting STEP" |
| `fuselage_sew` | base `+ 0.5 · step` | "sewing closed Solid" |
| `fuselage_slice` | base `+ 0.75 · step` | "slicing for finer xsecs" |
| `weight_items` | `90` | only when there are weight items |
| `finalising` | `95` | just before the response is built |

`units`, `scaling` and `weight_items` are **conditional** — a client must not
assume a fixed sequence. `pct` never reaches 100; the `complete` event is the
terminator. 🟢

Mechanism: `ProgressCallback = Callable[[str, int, str], None]` is invoked
**synchronously from the worker thread** and hops onto the event loop with
`loop.call_soon_threadsafe(queue.put_nowait, …)`; the generator drains the queue
until a private `_DONE` sentinel and then awaits the import task in its
`finally`. 🟢

## Warning vocabulary 🟢

`component_type` values observed in the code:

| Value | Meaning |
|---|---|
| `WING` | a wing handler or wing persistence failure |
| `WING_XSEC` | a degenerate or skipped wing section (`Span ≤ 0`, non-positive root chord) |
| `WING_SS_CONTROL` | a control-surface sub-surface issue (LE device skipped, duplicate on a segment) — 🔴 unreachable today |
| `FUSELAGE` | a fuselage handler or persistence failure |
| `SCALING` | the always-emitted `info` note that masses were not scaled, plus the applied factor |
| `UNITS` | a detected non-metre source unit was converted; `component_name` is the unit name (`ft`, `in`, …), severity `warning` |
| `POST_PASS` | a post-pass raised |
| *(geom type token)* | one of the 14 `_UNSUPPORTED_REASONS` entries: `PROP`, `DISK`, `MESH`, `CONFORMAL`, `NGON_MESH`, `HUMAN`, `POD`, `BOR`, `STACK`, `ELLIPSOID`, `WIRE_FRAME`, `HINGE`, `PT_CLOUD`, `GEAR` |

`severity ∈ {info, warning, error}` is validated in `ImportContext.add_warning`.
🟢

## Side effects 🟢

A successful import is **not** side-effect-free:

- A new `aeroplanes` row (via `aeroplane_service.create_aeroplane`), plus
  `wings` + `wing_xsecs` (via `wing_service.create_wing`), `fuselages` +
  `fuselage_xsecs` (via `fuselage_service.create_fuselage`) and `weight_items`.
- Persisted wings carry `design_model = 'asb'` and `wing_xsecs.dihedral = NULL`,
  because they are written through the geometry-only
  `AsbWingGeometryWriteSchema`. 🟡 The terminal-rib dihedral (`wing-design`
  BR-7) is therefore not recoverable for an imported wing.
- Per-geom STEP artefacts under
  `<ARTIFACTS_BASE_DIR>/openvsp_imports/<aeroplane_uuid>/`, recorded on the
  fuselage row as `step_path` and (when sewing succeeded) `solid_step_path`.
  Deleted best-effort by `cleanup_aeroplane_step_files` from
  `aeroplane_service.delete_aeroplane`.
- Generated or exported airfoil `.dat` files in the airfoil directory
  (content-hashed, so a repeat import writes nothing new).
- The uploaded temp file and the throwaway
  `openvsp_imports/_unitdetect_<stem>/` directory are always removed in
  `finally` blocks.
- Transaction ownership stays with `get_db()` (ADR 0009) — the service never
  commits.

## Known contract defects

- 🔴 **Imported aircraft have no control surfaces.** `openvsp_ss_control.register()`
  is never called from `_ensure_handlers_loaded` (only from
  `app/tests/test_openvsp_ss_control.py:24`), **and** the persistence write
  schema `WingXSecGeometryWriteSchema` has no `trailing_edge_device` field. Both
  must change for gh-644 to work. The response gives no hint that control
  surfaces were dropped — there is not even a `WING_SS_CONTROL` warning, because
  the code that would emit it never runs.
- 🔴 **`validate_geometry` never runs**, so the gh-647 span/area/MAC/length
  cross-check (`DEFAULT_REL_TOL = 0.01`) contributes no warnings to the
  response.
- 🟡 **No silent scale — unit resolution follows the declared unit; a wing-only model without one is reported, not guessed** (`Q-VI-3`, derived). Previously a wing-only model got no unit detection: `_detect_source_scale_to_meters`
  returns `None` without a fuselage, so a feet-unit flying wing imports 3.28×
  too large with no `UNITS` warning at all.
- 🔴 **`n_wings` / `n_fuselages` count parsed, not persisted, components.** A
  component that failed to persist is still counted; only the accompanying
  warning reveals it. 🟡 impact.
- 🟢 **Detect the unusable solid, record the state, and fall back to a solid lofted from the stored superellipse x-secs** (`Q-VI-4`, maintainer-answered). The maintainer needs a valid solid for the Creator classes — not for Fusion360 — and must be able to tell when one is defective. Previously a downloadable `solid_step_path` could be malformed at sharp fuselage
  fillets (#814). The x-sec path avoids the solid (gh-812); the download path
  does not, and nothing in the response flags it.
- 🟡 **A client that disconnects mid-stream still causes a full import** — the
  generator's `finally` awaits the task, so the aeroplane is created regardless.

## Not part of this contract

- The fuselage slicer and superellipse fitting it feeds → `fuselage-design`.
- The wing station/segment model, the terminal-station rule (BR-5) and the
  `AsbWingGeometryWriteSchema` definition itself → `wing-design`.
- Airfoil catalogue ingestion, classification and scoring of the `.dat` files
  this module writes → `airfoil-catalog`.
- Aeroplane, weight-item and component-tree persistence semantics →
  `aeroplane-core`, `mass-and-balance`.
- Consumption of the STEP artefacts by the CAD pipeline → `cad-generation`,
  `construction-plans`.
- Any aerodynamic analysis of the imported aircraft → `aero-analysis`.
- `scripts/vspaero_benchmark/` — an offline harness, not a runtime surface.
