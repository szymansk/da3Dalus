# vsp3-import-pipeline

> Use-case specification, nested under the module [`openvsp-import`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: openvsp-import
> (The adapter and process-level state, Pipeline, Handler registration,
> Scaling and source-unit detection, Error policy, REST surface),
> `_reversa_sdd/data-dictionary.md` §Module: openvsp-import.

## Overview

`vsp3-import-pipeline` is the spine of the import: it owns the optional
`openvsp` dependency, the **process-global** VSP model and handler registry, the
fixed read sequence that makes a second import independent of the first, geom
dispatch, the warning discipline every other slice reports through, source-unit
detection, the optional bounded rescale, best-effort persistence, and the two
REST surfaces (JSON and SSE). It is the slice that decides **what aborts an
import** — and the answer is: almost nothing. 🟢

## Responsibilities

- Probe and memoise the optional `openvsp` binding, and answer a clean 503 when
  it is absent. 🟢
- Reset and read the process-global VSP model in a fixed, load-bearing order. 🟢
- Register handlers and post-passes lazily, once per process. 🟢
- Canonicalise every geom type token and dispatch it, warning for unsupported
  types. 🟢
- Own `ImportWarning` / `ImportContext` / `ImportResult` — the structures every
  other slice writes into. 🟢
- Detect a non-metre source length unit by measurement and convert the whole
  aeroplane before anything else runs. 🟢
- Validate and apply exactly one optional rescale, in the documented three-stage
  order. 🟢
- Persist the parsed aeroplane per record, best-effort. 🟢
- Serve `POST /api/v2/import/openvsp` and its SSE variant, including progress
  reporting and temp-file cleanup. 🟢

**Explicitly NOT this use case's responsibility:** the per-geom translation
itself — wing planform maths, fuselage x-secs, airfoil resolution, `BLANK`
weight items (→ [`../geom-handlers/`](../geom-handlers/requirements.md)); STEP
export, sewing and the artefact layout
(→ [`../step-export-and-sewing/`](../step-export-and-sewing/requirements.md));
the fuselage slicer internals it merely gates (→ `fuselage-design`); aeroplane,
wing, fuselage and weight-item persistence semantics (→ `aeroplane-core`,
`wing-design`, `fuselage-design`, `mass-and-balance`).

## Business Rules

> IDs are inherited verbatim from [`../requirements.md`](../requirements.md).

- **BR-OV1 — `ClearVSPModel()` before every `ReadVSPFile`.** 🟢 *(this slice is
  its owner.)* The `openvsp` SWIG module owns a **single native VSP model** per
  process. Without the explicit clear, `ReadVSPFile` **merges** the new file
  into whatever is already loaded, so a second import silently inherits the
  first aircraft's geoms. First step of the gh-640 critical sequence
  (`openvsp_importer.import_vsp3:324-420`).
- **BR-OV2 — Importer state survives `uvicorn --reload`.** 🟢 *(owner.)*
  `openvsp_adapter._cached_module` / `_import_attempted` / `_import_error`
  (l.53-55, reset only by `reset_for_tests()` at l.92-97),
  `openvsp_importer._handlers_loaded` / `_HANDLERS` / `_POST_PASSES`
  (l.181-182, 284), and the SWIG module's native model all persist. Editing
  importer code and relying on `--reload` tests the **old** code; the process
  must be restarted.
- **BR-OV3 — Geom types must be canonicalised before dispatch.** 🟢 *(owner.)*
  `GetGeomTypeName(gid)` returns **Title-Case display names**, `AddGeom` /
  `GetGeomTypes` use **UPPERCASE tokens**. `_DISPLAY_TO_CANONICAL`
  (`openvsp_importer.py:194-211`, 16 entries) normalises with an `.upper()`
  fallback. Verified against OpenVSP 3.50.4.
- **BR-74 — Nothing aborts an import except three errors.** 🟢 *(owner.)* Only
  `ImportError`, `FileNotFoundError` and `ScaleValidationError` propagate.
- **BR-OV4 — Every loss is a structured warning.** 🟢 *(owner.)*
  `ImportContext.add_warning` validates `severity ∈ {info, warning, error}`;
  `mark_lossy(gid)` de-duplicates. `_UNSUPPORTED_REASONS`
  (`openvsp_importer.py:242-260`) covers 14 geom types: `PROP`, `DISK`, `MESH`,
  `CONFORMAL`, `NGON_MESH`, `HUMAN`, `POD`, `BOR`, `STACK`, `ELLIPSOID`,
  `WIRE_FRAME`, `HINGE`, `PT_CLOUD`, `GEAR`. A raising post-pass becomes a
  `POST_PASS` warning (l.401-410).
- **BR-76 — Source units are measured, not trusted (gh-808).** 🟢 *(owner.)*
  OpenVSP 3.50 removed both `SetLengthUnit` and `Vehicle_Info/LengthUnit`, so
  the file carries no unit. Measure `metric_STEP_span / handler_span` and snap
  it (`openvsp_import_service.py:147-201`).
- **BR-OV10 — The two scaling options are mutually exclusive and bounded.** 🟢
  *(owner.)* `SCALE_FACTOR ∈ (0.001, 10.0)`, `TARGET_SPAN ∈ (0.1, 50.0) m`
  (`:78-81`). Mutex → **400** (request shape); out-of-range or wingless
  `target_span_m` → `ScaleValidationError` → **422**.
- **BR-75 — Scaling never touches angles or masses.** 🟢 *(owner.)*
  `_scale_aeroplane_lengths` (`:254-293`) covers wing `xyz_le` / `chord`,
  `xyz_ref` and weight-item positions only; an `info` `SCALING` warning always
  says so.
- **BR-OV11 — The scaling order is load-bearing.** 🟢 *(owner.)* Unit conversion
  of the whole aeroplane → rescale of wings/`xyz_ref`/weight positions →
  fuselage x-secs **last**, after the slicer ran in the unscaled STEP frame
  (gh-765), then `scale_geom_step` on the stored files (gh-769).
- **BR-OV15 — Persistence is per-record best-effort.** 🟢 *(owner.)*
  `_record_persist_failure` turns any per-record exception into a `WING` /
  `FUSELAGE` / weight-item warning; the remaining records still persist
  (`_persist_aeroplane:804-1020`).
- 🟡 **A failed handler registration is reported, not swallowed** (`Q-VI-7`, derived from `P-WARN-0`). *(owner.)* Previously swallowed. Each
  of the four handler imports in `_ensure_handlers_loaded` (`:287-321`) sits in
  its own `try: … except ImportError: pass`, so a broken handler module degrades
  into "every geom of that type is unsupported" with **no log line at all**.
- 🟢 **Wired fully — registration AND the write path** (`Q-VI-1`, maintainer-answered). / 🟢 **`validate_geometry` is wired in** (`Q-VI-2`, maintainer-answered): the gh-647 cross-check is what would have caught the whole class of import defects, including the unit errors. Previously two registrations were missing.
  `openvsp_ss_control.register()` and any call to
  `openvsp_validation.validate_geometry` are both absent from this slice's
  registration and pipeline code. Diagnosed here, detailed in
  [`../geom-handlers/`](../geom-handlers/requirements.md).

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-IP-01 | Memoise the optional `openvsp` import; expose `is_available()` / `get_vsp()` | Must | A failed import is attempted once; `get_vsp()` raises `ImportError` naming the three install paths |
| RF-IP-02 | Answer 503 when the bindings are absent, on both routes | Must | `POST /api/v2/import/openvsp` → 503 with a pointer to `docs/md/openvsp-import-setup.md` |
| RF-IP-03 | Clear the VSP model before every read | Must | Importing A then B in one process yields only B's geoms |
| RF-IP-04 | Read the legacy length unit tolerantly | Must | `FindParm` returning `""` yields `None`, not an exception; a 3.50 file without the parm imports cleanly |
| RF-IP-05 | Guard `SetLengthUnit` behind `hasattr` | Must | The import runs on OpenVSP 3.50+, where the function no longer exists |
| RF-IP-06 | Canonicalise geom types with an `.upper()` fallback | Must | `"BodyOfRevolution"` → `BOR`; an unlisted `"Foo"` → `FOO` |
| RF-IP-07 | Dispatch to the registered handler, else warn and mark lossy | Must | A `PROP` geom yields the `_UNSUPPORTED_REASONS["PROP"]` warning and a `lossy_components` entry, and the import still returns 201 |
| RF-IP-08 | Run every registered post-pass, converting a raise into a warning | Must | A raising post-pass yields `component_type = "POST_PASS"` and a 201 response |
| RF-IP-09 | Collect warnings with validated severity and de-duplicated lossy ids | Must | `mark_lossy` twice with one gid yields one entry; an invalid severity is rejected |
| RF-IP-10 | Detect a non-metre source unit and convert the whole aeroplane | Must | A ratio within ±2 % of `0.3048` converts ×0.3048 and emits a `UNITS` warning of severity `warning` |
| RF-IP-11 | Leave metre, unmatched and fuselage-less models untouched | Must | Ratio ≈ 1.0, an unmatched ratio, or no fuselage ⇒ no conversion, no `UNITS` warning |
| RF-IP-12 | Remove the throwaway unit-detection STEP directory | Must | `openvsp_imports/_unitdetect_<stem>/` is gone after the request, including on failure |
| RF-IP-13 | Enforce the scaling mutex as 400 and the range as 422 | Must | Both params → 400; `scale_factor = 20` → 422; `target_span_m` with no wings → 422 |
| RF-IP-14 | Compute the target-span factor from the physical span | Must | `_compute_max_wing_span` uses `2·max|y_le|` symmetric, `max|y_le|` otherwise |
| RF-IP-15 | Never scale twist or masses, and always warn when scaling | Must | After a rescale every `twist` and mass is unchanged and exactly one `info` `SCALING` warning is present |
| RF-IP-16 | Apply the three scaling stages in order | Must | The slicer receives the unscaled STEP; the persisted x-secs and the stored STEP end up scaled |
| RF-IP-17 | Persist per record, best-effort | Must | One failing wing yields a `WING` warning while the aeroplane and all other records persist |
| RF-IP-18 | Resolve the aeroplane name by precedence | Must | Uploading `cessna172.vsp3` with no `name` yields `"cessna172"`, never the temp-file stem |
| RF-IP-19 | Guard the upload: extension, size, media handling | Must | `.stl` → 400; 51 MB → 413; the parse runs off the event loop |
| RF-IP-20 | Remove the uploaded temp file on every path | Must | Unlinked on success, on error, and after a mid-stream disconnect |
| RF-IP-21 | Stream progress over SSE with the documented vocabulary | Should | Monotonic `pct` ≤ 95, conditional steps omitted when inapplicable, exactly one terminal event |
| RF-IP-22 | Carry the intended status in-band on a stream error | Should | `error` payload is `{"status": 422 \| 503, "detail": …}` |
| RF-IP-23 | Report a failed handler registration | Should (**missing**) | 🔴 Today `except ImportError: pass` is silent; a diagnostic must be logged |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Availability | The optional dependency yields a 503, never a 500 | `openvsp_import.py:123-131`; `openvsp_adapter.get_vsp` | 🟢 |
| Correctness | The native model is reset before every read because it is process-global | `import_vsp3` (`ClearVSPModel` first) | 🟢 |
| Correctness | The unit-snap window is **relative** to each factor and the factors are ≥3× apart, so no ratio can alias | `_snap_to_unit_scale:108-126` | 🟢 |
| Correctness | The scaling epsilon is `1e-9`, well below the UI step of `0.01` (Sonar S1244) | `openvsp_import_service.py:1113` | 🟢 |
| Robustness | Unit detection is wrapped in `except Exception` and logged at `info` — it must never break a valid import | `_detect_source_scale_to_meters` | 🟢 |
| Robustness | Only three exception types propagate; everything else becomes a warning | `openvsp_importer.py:401-410`; `_record_persist_failure` | 🟢 |
| Performance | The temp-file write and the blocking parse run on the thread pool (Sonar S7493) | `openvsp_import.py` (`asyncio.to_thread`) | 🟢 |
| Performance | Fuselages get 55 of the 100 progress points because they dominate wall-clock time | `_persist_aeroplane:895-905` | 🟢 |
| Usability | SSE disables proxy buffering so progress is real-time | `openvsp_import.py:377-384` | 🟢 |
| Security | 50 MB upload cap enforced before the file is written to disk | `openvsp_import.py:50` | 🟢 |
| Housekeeping | Both the upload and the `_unitdetect_*` directory are removed in `finally` blocks | `openvsp_import.py`; `_detect_source_scale_to_meters` | 🟢 |

## Acceptance Criteria

```gherkin
Feature: The critical read sequence

  Scenario: A second import is independent of the first
    Given I have imported model A in this process
    When I import model B
    Then B's aeroplane contains only B's geoms
    # ClearVSPModel() runs before ReadVSPFile; without it VSP MERGES

  Scenario: A 3.50 file without a length parm imports cleanly
    Given a .vsp3 written by OpenVSP 3.50, which stores no LengthUnit
    When I import it
    Then FindParm returns an empty string and is treated as "not found"
    And SetLengthUnit is skipped because the attribute does not exist
    And the import returns 201

Feature: Dispatch and the warning discipline

  Scenario: An unsupported geom is reported, not fatal
    Given a .vsp3 containing a Propeller geom
    When I import it
    Then the response status is 201
    And a warning with component_type "PROP" is present
    And the geom id appears once in lossy_components

  Scenario: A raising post-pass does not fail the import
    Given a registered post-pass that raises
    When I import a valid file
    Then the response status is 201
    And a warning with component_type "POST_PASS" is present

  Scenario: A broken handler module degrades silently
    Given the fuselage handler module cannot be imported
    When I import a file containing a Fuselage geom
    Then that geom is reported as unsupported
    # 🟡 **A failed handler registration is reported, not swallowed** (`Q-VI-7`, derived from `P-WARN-0`). — RF-IP-23

Feature: Source-unit detection

  Scenario: A feet model is detected and converted
    Given a fuselage whose metric STEP span is 0.3048 times its handler span
    When I import the file
    Then the whole aeroplane including fuselages is multiplied by 0.3048
    And a UNITS warning of severity "warning" names "ft"
    And the _unitdetect_ STEP directory has been removed

  Scenario: A metre model is left alone
    Given a measured ratio of 1.0
    When I import the file
    Then no conversion is applied
    And no UNITS warning is emitted

  Scenario: A wing-only model cannot be checked
    Given a flying wing with no fuselage, authored in feet
    When I import the file
    Then no conversion is applied and no warning is emitted
    # 🟡 reported, not guessed (Q-VI-3)

Feature: Optional rescaling

  Scenario: Rescaling to a target span preserves angles and masses
    Given a model whose largest wing span is 10 m
    When I import it with target_span_m=2.0
    Then every wing xyz_le and chord is multiplied by 0.2
    And every twist and every weight-item mass is unchanged
    And exactly one info SCALING warning states that masses were not scaled

  Scenario: Two scaling parameters is a request-shape error
    When I POST with target_span_m=2.0 and scale_factor=0.5
    Then the response status is 400

  Scenario: An out-of-range factor is a semantic error
    When I POST with scale_factor=20.0
    Then the response status is 422

  Scenario: A target span on a wingless model is rejected
    Given a .vsp3 with fuselages but no wings
    When I POST with target_span_m=2.0
    Then the response status is 422

Feature: Persistence and delivery

  Scenario: One failing record does not lose the rest
    Given a model with 3 wings, one of which fails validation
    When I import it
    Then the aeroplane exists with 2 wings
    And a WING warning names the third

  Scenario: The upload temp file never leaks
    Given any import outcome, success or failure
    When the request completes
    Then the NamedTemporaryFile has been unlinked

  Scenario: The stream reports progress then exactly one terminator
    When I POST to /api/v2/import/openvsp/stream with a valid file
    Then progress events arrive with non-decreasing pct not exceeding 95
    And exactly one complete event carries the same body as the JSON endpoint

  Scenario: A stream failure carries its status in-band
    Given a file with scale_factor=20.0
    When I POST to the stream endpoint
    Then no progress event is followed by complete
    And one error event carries {"status": 422, "detail": ...}
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| The critical read sequence (RF-IP-03…RF-IP-05) | Must | `ClearVSPModel` ordering is the difference between a correct import and a silently merged one |
| Canonicalisation and dispatch (RF-IP-06/RF-IP-07) | Must | Every geom in the file passes through it; a token mismatch makes everything "unsupported" |
| The warning discipline (RF-IP-08/RF-IP-09) | Must | The module's contract with the user — the entire slice set reports through these structures |
| Source-unit detection (RF-IP-10…RF-IP-12) | Must | Without it a feet model is 3.28× wrong with no signal |
| Scaling validation, invariants and order (RF-IP-13…RF-IP-16) | Must | Order errors mismatch schema against artefact; ADR 0018 forbids scaling masses |
| Best-effort persistence (RF-IP-17) | Must | Defines "an import is a lossy translation, not a transaction" |
| Upload guards and cleanup (RF-IP-19/RF-IP-20) | Must | Cheap, and they keep the optional dependency and bad uploads out of the 5xx bucket |
| Name precedence (RF-IP-18) | Should | A wrong name is annoying, not incorrect; but `tmpXXXX` would be user-hostile |
| Optional dependency memoisation (RF-IP-01/RF-IP-02) | Should | A repeated failed import is only a performance issue; the 503 is the user-visible part |
| SSE progress and in-band error status (RF-IP-21/RF-IP-22) | Should | UX for a slow operation; the JSON route is the contract of record |
| Registration diagnostics (RF-IP-23) | **Should** | 🟡 reported (`Q-VI-7`); currently absent. It changes debuggability, not behaviour |
| Concurrency safety around the process-global VSP model | Won't (this iteration) | 🟡 Unaddressed everywhere in the module; single-maintainer deployment makes it theoretical today |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/converters/openvsp_adapter.py` (97 l.) | `_attempt_import`, `is_available`, `get_vsp`, `reset_for_tests`, `_cached_module` / `_import_attempted` / `_import_error` | 🟢 |
| `app/converters/openvsp_importer.py` (420 l.) | `import_vsp3:324-420`, `_ensure_handlers_loaded:287-321`, `_canonicalize_geom_type`, `_DISPLAY_TO_CANONICAL:194-211`, `_UNSUPPORTED_REASONS:242-260`, `_read_source_length_unit`, `LEN_UNIT_TO_METERS:63-71`, `ImportWarning:84`, `ImportContext:98-141`, `ImportResult:145` | 🟢 |
| `app/services/openvsp_import_service.py` (1 150 l.) | `import_openvsp_file:1025-1145`, `_persist_aeroplane:804-1020`, `_detect_source_scale_to_meters:147-201`, `_snap_to_unit_scale:108-126`, `_convert_aeroplane_to_metres`, `_scale_aeroplane_lengths:254-293`, `_resolve_scale_factor`, `_compute_max_wing_span`, `_record_persist_failure`, `_resolve_aeroplane_name`, `ScaleValidationError` | 🟢 |
| `app/api/v2/endpoints/openvsp_import.py` (385 l.) | `import_openvsp`, `import_openvsp_stream`, `_sse_format`, `OpenVspImportResponseModel`, `ImportWarningResponse`, `_MAX_FILE_SIZE_BYTES:50` | 🟢 |
| `app/converters/openvsp_ss_control.py` / `openvsp_validation.py` | `register` / `validate_geometry` — **absent from this slice's registration** | 🟡 |
