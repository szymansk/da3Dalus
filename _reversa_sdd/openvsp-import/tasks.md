# openvsp-import — Implementation Tasks

> Executable sequence to re-implement the module from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Slice-level task lists:
> [`vsp3-import-pipeline/tasks.md`](vsp3-import-pipeline/tasks.md),
> [`geom-handlers/tasks.md`](geom-handlers/tasks.md),
> [`step-export-and-sewing/tasks.md`](step-export-and-sewing/tasks.md).

## Prerequisites

- [ ] `openvsp` Python bindings installable but **optional** — the module must
      degrade to a clean 503, never a 500 (ADR 0017).
- [ ] CadQuery/OCCT **optional** — needed for source-unit detection, solid
      sewing and the fuselage slicer; absent means those stages are skipped.
- [ ] `aeroplane-core` — `aeroplane_service.create_aeroplane` and the delete
      hook that calls `cleanup_aeroplane_step_files`.
- [ ] `wing-design` — `wing_service.create_wing` plus
      `AsbWingGeometryWriteSchema` / `WingXSecGeometryWriteSchema`
      (`app/schemas/aeroplaneschema.py:592-708`) and the BR-5 terminal-station
      rule the wing handler is written against.
- [ ] `fuselage-design` — `fuselage_service.create_fuselage`, the slicer and
      `vsp_anchored_x_stations`.
- [ ] `airfoil-catalog` — a writable airfoil `.dat` directory, and
      `./components/airfoils/naca0012.dat` present as the last-resort fallback.
- [ ] `mass-and-balance` — the weight-item write path used for `BLANK` geoms.
- [ ] `settings.ARTIFACTS_BASE_DIR` resolvable and writable.
- [ ] `get_db()` request-scoped session owning the transaction (ADR 0009) — the
      service never commits.

## Tasks

### Optional dependency and process state

- [ ] **T-01 — The adapter memo.**
  Memoise `importlib.import_module("openvsp")` in three module globals
  (`_cached_module`, `_import_attempted`, `_import_error`); expose
  `is_available()` and `get_vsp()`; `get_vsp()` raises
  `ImportError(_OPENVSP_MISSING_MSG)` naming the three supported install paths.
  Provide `reset_for_tests()` as the only reset.
  - Legacy origin: `app/converters/openvsp_adapter.py:53-55, 92-97`
  - Definition of done: a failed import is attempted exactly once per process;
    `reset_for_tests()` makes a second attempt possible; `get_vsp()` never
    returns `None`.
  - Confidence: 🟢

- [ ] **T-02 — Document and enforce the restart rule (BR-OV2).**
  `_handlers_loaded`, `_HANDLERS`, `_POST_PASSES` and the SWIG module's native
  VSP model all survive `uvicorn --reload`. Record this as an operational
  constraint in the module docstring and the developer docs.
  - Legacy origin: `openvsp_importer.py:181-182, 284`; `openvsp_adapter.py:53-55`
  - Definition of done: the docstring states that importer changes require a
    process restart; a test asserts `_ensure_handlers_loaded` is idempotent.
  - Confidence: 🟢

- [ ] **T-03 — Handler registry with visible failures.**
  `_ensure_handlers_loaded` imports and registers wing, fuselage, blank and
  custom handlers, plus the `_resolve_vehicle_cg` and
  `_drop_degenerate_fuselages` post-passes.
  **Do not reproduce the silent `except ImportError: pass`** — log the failure
  at `error` and, ideally, surface it as an import warning.
  - Legacy origin: `openvsp_importer.py:287-321`
  - Definition of done: with one handler module patched to raise `ImportError`,
    the import still runs **and** a diagnostic is logged naming the module.
  - Confidence: 🟢 behaviour · 🔴 the swallow is a defect (BR-OV19)

### The import pipeline

- [ ] **T-04 — The gh-640 critical sequence.**
  In order: `_ensure_handlers_loaded()` → `vsp.ClearVSPModel()` →
  `vsp.ReadVSPFile(path)` → `_read_source_length_unit(...)` →
  `if hasattr(vsp, "SetLengthUnit"): vsp.SetLengthUnit(vsp.LEN_M)` →
  `vsp.Update()` → dispatch every `FindGeoms()` id → run every post-pass.
  - Legacy origin: `openvsp_importer.import_vsp3:324-420`
  - Definition of done: importing model A then model B in one process yields
    only B's geoms; removing `ClearVSPModel` makes that test fail.
  - Confidence: 🟢

- [ ] **T-05 — `_read_source_length_unit` and the empty-string convention.**
  `FindParm(vehicle_id, "LengthUnit", "Vehicle_Info")` **prints** `Can't Find
  Parm` to stderr but **returns `""`** rather than raising; treat `""` as "not
  found". Both the parm and `SetLengthUnit` are absent on OpenVSP 3.50+, hence
  the `hasattr` guard. Map the legacy enum with `LEN_UNIT_TO_METERS`
  (`0 mm 0.001 · 1 cm 0.01 · 2 m 1.0 · 3 in 0.0254 · 4 ft 0.3048 · 5 yd 0.9144 ·
  6 unitless 1.0`).
  - Legacy origin: `openvsp_importer.py:63-71, 352-368`
  - Definition of done: an empty return yields `None`, not an exception; a 3.50
    file without the parm imports cleanly.
  - Confidence: 🟢 (`LEN_UNITLESS → 1.0` is 🔴 — decide whether to warn)

- [ ] **T-06 — Geom type canonicalisation.**
  `GetGeomTypeName` returns Title-Case display names while `AddGeom` uses
  UPPERCASE tokens. `_DISPLAY_TO_CANONICAL` (16 entries) normalises, falling
  back to `.upper()`.
  - Legacy origin: `openvsp_importer.py:194-211`; verified on OpenVSP 3.50.4
  - Definition of done: `"BodyOfRevolution"` → `BOR`, `"Propeller"` → `PROP`,
    an unlisted `"Foo"` → `FOO`.
  - Confidence: 🟢

- [ ] **T-07 — Dispatch and the unsupported-type table.**
  `_HANDLERS.get(token)`; a miss emits `_UNSUPPORTED_REASONS[token]` (or
  `"not supported in Phase 1"`) plus `ctx.mark_lossy(gid)`. 14 types carry a
  user-facing reason: `PROP`, `DISK`, `MESH`, `CONFORMAL`, `NGON_MESH`,
  `HUMAN`, `POD`, `BOR`, `STACK`, `ELLIPSOID`, `WIRE_FRAME`, `HINGE`,
  `PT_CLOUD`, `GEAR`.
  - Legacy origin: `openvsp_importer.py:242-260`
  - Definition of done: a file with a `PROP` geom returns 201 with that warning
    and the gid in `lossy_components`.
  - Confidence: 🟢

- [ ] **T-08 — `ImportContext` / `ImportWarning` / `ImportResult`.**
  `ImportWarning` is a frozen dataclass (`component_type`, `component_name`,
  `reason`, `severity` default `"warning"`, validated against
  `{info, warning, error}`). `ImportContext` collects warnings, a
  **de-duplicated** `lossy_components`, `weight_items`, `source_length_unit`,
  `source_scale_to_meters`, `wing_geom_ids`, `fuselage_geom_ids`.
  - Legacy origin: `openvsp_importer.py:84, 98-141, 145`; data-dictionary
    §Module: openvsp-import
  - Definition of done: `mark_lossy` twice with the same gid yields one entry;
    an invalid severity is rejected.
  - Confidence: 🟢

- [ ] **T-09 — Post-pass failures become warnings.**
  A post-pass that raises produces `component_type = "POST_PASS"` rather than
  failing the import.
  - Legacy origin: `openvsp_importer.py:401-410`
  - Definition of done: a deliberately raising post-pass still yields 201 with
    the warning present.
  - Confidence: 🟢

### Wing planform

- [ ] **T-10 — `_read_section_parm` fallback.**
  Try group `XSec_{i}`, fall back to `XSec_{i-1}`, return `0.0` when absent.
  - Legacy origin: `openvsp_wing_handler.py:109-121`
  - Definition of done: a model whose parms live only on `XSec_{i-1}` still
    yields a correct planform.
  - Confidence: 🟢

- [ ] **T-11 — Root x-section and the non-positive chord guard.**
  `{xyz_le: [0,0,0], chord: XSec_1.Root_Chord, twist: 0, x_sec_type: "root"}`;
  `Root_Chord ≤ 0` warns and defaults to `1.0 m`.
  - Legacy origin: `openvsp_wing_handler.py:902-910`
  - Definition of done: `Root_Chord = 0` yields chord `1.0` and a warning.
  - Confidence: 🟢

- [ ] **T-12 — Trigonometric station advance (gh-755).**
  ```
  cum_x += Span · tan(Λ_LE)
  cum_y += Span · cos(cum_dihedral)      ← NOT `+= Span`
  cum_z += Span · sin(cum_dihedral)
  ```
  **Do not reproduce** the pre-gh-755 small-angle shortcut `cum_y += span`.
  - Legacy origin: `openvsp_wing_handler.py:985-989`
  - Definition of done: a 45° dihedral section advances y and z by
    `Span·√2/2` each; a regression test pins the winglet/V-tail case.
  - Confidence: 🟢

- [ ] **T-13 — Relative vs absolute dihedral and twist.**
  Read the per-wing `RelativeDihedralFlag` / `RelativeTwistFlag`: relative ⇒
  `cum += parm`, absolute ⇒ `cum = parm`.
  - Legacy origin: `openvsp_wing_handler.py` (gh-755)
  - Definition of done: both flag states are covered by tests on a 3-section
    wing.
  - Confidence: 🟢

- [ ] **T-14 — `sweep_at_le` reference change.**
  `tan(Λ_to) = tan(Λ_from) − (xref_to − xref_from)·(c_root − c_tip)/span`,
  returning `Λ_from` unchanged when `span ≤ 0`. Sweep is **absolute per
  section** — no flag, no accumulation.
  - Legacy origin: `openvsp_wing_handler.py`; comment cites `WingGeom.cpp:1111`
  - Definition of done: a quarter-chord sweep of 10° on a tapered panel converts
    to the expected leading-edge sweep; `span = 0` is a pass-through.
  - Confidence: 🟢

- [ ] **T-15 — Skip a degenerate section.**
  `Span ≤ 0` → warning + `mark_lossy` + skip; the cumulative state must not
  advance.
  - Legacy origin: `openvsp_wing_handler.py`
  - Definition of done: a zero-span section leaves the following stations
    unmoved.
  - Confidence: 🟢

- [ ] **T-16 — The terminal x-section carries no segment data (client of
      `wing-design` BR-5).**
  Set `x_sec_type = None` on the last x-section so
  `AsbWingSchema.validate_last_xsec_has_no_segment_details` passes.
  - Legacy origin: `openvsp_wing_handler.py:994-1005`
  - Definition of done: every imported wing validates as an `AsbWingSchema`
    without modification.
  - Confidence: 🟢

- [ ] **T-17 — Geom placement and symmetry parms.**
  `XForm` group `X/Y/Z_Location`, `X/Y/Z_Rotation`; `Sym` group
  `Sym_Planar_Flag` → `wing.symmetric`; `EndCap` group for the tip treatment.
  - Legacy origin: `openvsp_wing_handler.py`; data-dictionary §OpenVSP parms
  - Definition of done: a mirrored VSP wing imports with `symmetric = True`.
  - Confidence: 🟢

### Airfoils

- [ ] **T-18 — `import_airfoil_from_xsec` never raises.**
  Implement the full shape switch — `XS_FOUR_SERIES`, `XS_FOUR_DIGIT_MOD`,
  `XS_FIVE_DIGIT`, `XS_FIVE_DIGIT_MOD`, `XS_SIX_SERIES`, `XS_ONE_SIX_SERIES`,
  `XS_FILE_AIRFOIL`, `XS_CST_AIRFOIL`, else — exactly as tabulated in
  [`design.md`](design.md) §F3, ending at
  `./components/airfoils/naca0012.dat`.
  - Legacy origin: `openvsp_airfoil.py:963-1180`
  - Definition of done: each branch returns a readable `.dat`; a mocked
    unknown shape falls back without raising.
  - Confidence: 🟢

- [ ] **T-19 — NACA generation and its documented approximations.**
  `ensure_naca4_dat` (gh-700), `ensure_naca5_dat` (gh-733),
  `_NACA_DAT_HALF_POINTS = 80` cosine-spaced. 6-series and 16-series use an
  **a-family mean line + 4-digit thickness approximation** and must emit an
  `info` warning saying t/c and design Cl are exact while the thickness shape is
  not conformal-mapped. `-mod` variants append the suffix but reuse the base
  `.dat`.
  - Legacy origin: `openvsp_airfoil.py:41, 963-1180`
  - Definition of done: a 6-series section produces both a `.dat` and the
    caveat warning; a 16-series section is **not** treated as symmetric (the
    pre-gh-733 bug read a non-existent `Camber` parm).
  - Confidence: 🟢

- [ ] **T-20 — `write_imported_airfoil_dat`: dedup then content-hash.**
  `_dedup_consecutive_points(tol=1e-9)` (gh-789, ASB `repanel()` crash), then
  hash the coordinates and **skip the write** when unchanged.
  - Legacy origin: `openvsp_airfoil.py:712, 731-750`
  - Definition of done: two consecutive identical points collapse; re-importing
    the same model leaves every `.dat` mtime untouched.
  - Confidence: 🟢

- [ ] **T-21 — `morph_airfoils` with a raw-blend fallback.**
  Fit both ends with Kulfan/CST, blend, fall back to `_raw_blend` when the fit
  fails (gh-796). It is the `airfoil_morph_fn` seam used by `segment_split`.
  - Legacy origin: `openvsp_airfoil.py:876-901`
  - Definition of done: a deliberately unfittable pair still returns a blended
    airfoil.
  - Confidence: 🟢

### Units and scaling

- [ ] **T-22 — `_snap_to_unit_scale`.**
  Reject non-finite or non-positive ratios; accept a unit when
  `|ratio − factor| ≤ 0.02 · factor` (**relative** window), keeping the nearest
  match; return `None` for metres or no match.
  `_LENGTH_UNIT_FACTORS = {m 1.0, yd 0.9144, ft 0.3048, in 0.0254, cm 0.01,
  mm 0.001}`.
  - Legacy origin: `openvsp_import_service.py:94, 105-126`
  - Definition of done: `0.3048` → `("ft", 0.3048)`; `1.0` → `None`; `0.5` →
    `None`; `NaN` → `None`; a ratio between ft and yd picks the nearer.
  - Confidence: 🟢

- [ ] **T-23 — `_detect_source_scale_to_meters` (gh-808).**
  Pick the fuselage with the largest handler X-span, export it to STEP, read
  `bb.xlen / 1000.0` (OCC normalises STEP to mm), snap
  `metric_span / handler_span`. Best-effort: wrap in `except Exception`, log at
  `info`, and always `rmtree` the throwaway
  `_unitdetect_<stem>` directory in a `finally`.
  - Legacy origin: `openvsp_import_service.py:147-201`
  - Definition of done: a feet fixture converts ×0.3048 with a `UNITS` warning;
    a fuselage-less model returns `None` and leaves the import untouched; the
    temp STEP directory is gone afterwards.
  - Confidence: 🟢 (the fuselage-less blind spot is 🔴)

- [ ] **T-24 — `_convert_aeroplane_to_metres` vs `_scale_aeroplane_lengths`.**
  The unit conversion scales **everything** including fuselages; the user
  rescale scales wings, `xyz_ref` and weight-item positions **only**. Neither
  scales twist or masses.
  - Legacy origin: `openvsp_import_service.py:254-293` and the
    `_convert_aeroplane_to_metres` wrapper
  - Definition of done: after a unit conversion the fuselage x-secs are scaled;
    after a user rescale they are not (they are handled in `_persist_aeroplane`).
  - Confidence: 🟢

- [ ] **T-25 — `_resolve_scale_factor` bounds and the mutex split.**
  `SCALE_FACTOR ∈ (0.001, 10.0)`, `TARGET_SPAN ∈ (0.1, 50.0) m`.
  Mutex violation is rejected **at the endpoint** → 400; out-of-range and
  `target_span_m` on a wingless aeroplane raise `ScaleValidationError` → 422.
  `_compute_max_wing_span = 2·max|y_le|` symmetric, `max|y_le|` otherwise.
  - Legacy origin: `openvsp_import_service.py:78-81`; `openvsp_import.py:139-146`
  - Definition of done: the four cases (both / too big / too small / no wings)
    each produce the documented status.
  - Confidence: 🟢

- [ ] **T-26 — Always warn that masses were not scaled.**
  Any applied factor (`|factor − 1| > 1e-9`) appends an `info` `SCALING`
  warning naming the factor and stating masses were untouched.
  - Legacy origin: `_make_scaling_warning`; ADR 0018
  - Definition of done: every scaled import contains exactly one `SCALING`
    warning; an unscaled import contains none.
  - Confidence: 🟢

- [ ] **T-27 — The three-stage scaling order (gh-765).**
  1) unit conversion of the whole aeroplane, 2) `_scale_aeroplane_lengths`,
  3) fuselage x-secs **last**, inside `_persist_aeroplane`, after the slicer
  refinement, followed by `scale_geom_step` on the stored STEP files (gh-769).
  - Legacy origin: `openvsp_import_service.py:1071-1133, 960-1005`
  - Definition of done: a scaled import's fuselage x-secs match the scaled
    aeroplane **and** the stored STEP; the slicer input is the unscaled file.
  - Confidence: 🟢

### Persistence

- [ ] **T-28 — `_persist_aeroplane` per-record best-effort.**
  Each wing, fuselage and weight item is written in its own `try/except`;
  failures become warnings via `_record_persist_failure` and the rest still
  persist.
  - Legacy origin: `openvsp_import_service.py:804-1020`
  - Definition of done: with one wing forced to fail, the aeroplane, the other
    wings and every fuselage still exist and a `WING` warning is present.
  - Confidence: 🟢

- [ ] **T-29 — Aeroplane name precedence.**
  Explicit `name` (whitespace-only ignored) → uploaded filename stem → parsed
  model name. `source_filename` must be threaded through, or the persisted name
  becomes the `NamedTemporaryFile` stem.
  - Legacy origin: `_resolve_aeroplane_name`; `openvsp_import_service.py:828-834`
  - Definition of done: uploading `cessna172.vsp3` with no `name` yields
    `"cessna172"`, never `"tmpab12cd"`.
  - Confidence: 🟢

- [ ] **T-30 — Wings are persisted through the geometry-only write schema.**
  Map `AsbWingSchema` → `AsbWingGeometryWriteSchema` carrying only `xyz_le`,
  `chord`, `twist`, `airfoil`, `x_sec_type`, `tip_type`,
  `number_interpolation_points`.
  **Record the consequence explicitly**: no TED, no turbulator, no spar and no
  explicit `dihedral` can cross this boundary.
  - Legacy origin: `openvsp_import_service.py:846-865`;
    `app/schemas/aeroplaneschema.py:592-708`
  - Definition of done: a test asserts the exact field set, and a comment ties
    it to BR-OV16 so the limitation is not rediscovered.
  - Confidence: 🟢 (whether it *should* be geometry-only is 🔴)

### Control surfaces and validation — currently inert

- [ ] **T-31 — 🟢 Register the SS_CONTROL post-pass** (`Q-VI-1`).
  Add `openvsp_ss_control.register()` to `_ensure_handlers_loaded` so gh-644
  actually runs.
  - Legacy origin: `openvsp_importer.py:287-321`;
    `app/tests/test_openvsp_ss_control.py:24` is the only current caller
  - Definition of done: a test that calls the **production** entry point (not
    `register()` directly) imports a `.vsp3` with an `SS_CONTROL` sub-surface
    and observes the post-pass running.
  - Confidence: 🟢 — wired (`Q-VI-1`); the pass was not parked
    deliberately

- [ ] **T-32 — 🟢 Let a trailing-edge device survive persistence** (`Q-VI-1`, write path included).
  T-31 alone is insufficient: `WingXSecGeometryWriteSchema` has no
  `trailing_edge_device` field, so the TED is dropped at the persistence
  boundary. Either widen the import write path or persist TEDs in a second pass
  through the TED route.
  - Legacy origin: `openvsp_import_service.py:846-865`;
    `app/schemas/aeroplaneschema.py:592-630`
  - Definition of done: an imported aircraft with one `SS_CONTROL` has a
    `trailing_edge_device` on the inboard x-section of the mapped segment, with
    `rel_chord_root = 1 − Length_C_Start` and `role = OTHER`.
  - Confidence: 🟢 — the fix shape is decided (`Q-VI-4`)

- [ ] **T-33 — The SS_CONTROL mapping itself.**
  `LE_Flag ≥ 0.5` → info warning + skip; `EtaFlag ≥ 0.5` selects
  `EtaStart`/`EtaEnd` over `UStart`/`UEnd`;
  `rel_chord_root = 1 − Length_C_Start`, `rel_chord_tip = 1 − Length_C_End`
  (VSP measures from the TE, we from the LE); `deflection_deg = Deflection`;
  `role = OTHER`; `symmetric` inherited from the wing;
  `_u_to_segment_index(u_mid, n_sec) = clamp(int(u·n_sec)+1, 1, n_sec)`;
  attach to `xsec_idx = seg_idx − 1`; a second sub-surface on the same segment
  is rejected with a warning.
  - Legacy origin: `app/converters/openvsp_ss_control.py`
  - Definition of done: the chord-reference inversion and the segment mapping
    are unit-tested independently of registration.
  - Confidence: 🟢 (the code is confirmed; only its reachability is 🔴)

- [ ] **T-34 — 🟢 Wire `validate_geometry` into the pipeline** (`Q-VI-2`).
  Cross-check derived span / area / MAC against `WingGeom.TotalSpan`,
  `TotalProjectedArea` (fallback `TotalArea`), `TotalChord` (fallback `MAC`),
  and fuselage length against `Design.Length`, at
  `DEFAULT_REL_TOL = 0.01`; extend the result warnings as its own docstring
  shows.
  - Legacy origin: `app/converters/openvsp_validation.py:39, 44`
  - Definition of done: a deliberately mis-derived planform produces a warning;
    a faithful import produces none.
  - Confidence: 🟢 — wired (`Q-VI-1`/`Q-VI-2`); it was not parked deliberately

### REST and streaming

- [ ] **T-35 — The JSON endpoint and its status map.**
  503 (bindings) → 400 (not `.vsp3`) → 400 (mutex) → 413 (> 50 MB) → parse →
  500 (`FileNotFoundError`) / 503 (`ImportError`) / 422
  (`ScaleValidationError`) / 422 (anything else) → 201. Run both the temp-file
  write and the import on `asyncio.to_thread` (Sonar S7493) and unlink the temp
  file in a `finally`.
  - Legacy origin: `app/api/v2/endpoints/openvsp_import.py:50, 123-215`
  - Definition of done: contract tests cover every row of the table in
    [`contracts.md`](contracts.md); the temp file is gone on every path.
  - Confidence: 🟢

- [ ] **T-36 — The SSE endpoint.**
  Same up-front validation (so a client never opens a stream to receive an
  error), `asyncio.Queue` + `loop.call_soon_threadsafe`, `_DONE` sentinel,
  `await import_task` in the generator's `finally`, media type
  `text/event-stream`, headers `X-Accel-Buffering: no` and
  `Cache-Control: no-cache`. `_sse_format` emits compact JSON.
  - Legacy origin: `openvsp_import.py:258-385`
  - Definition of done: a full run emits the documented progress sequence
    followed by exactly one `complete`; a failing run emits exactly one `error`
    carrying `{status, detail}`.
  - Confidence: 🟢

- [ ] **T-37 — The progress vocabulary.**
  `parsing 5` → `parsing 15` → (`units 16`) → (`scaling 18`) → `aeroplane 20` →
  `wing 25 + int(5(i+1)/n)` → `fuselage 30 + int(55/n · i)` with
  `fuselage_step`/`fuselage_sew`/`fuselage_slice` at +25 %/+50 %/+75 % of the
  per-fuselage step → (`weight_items 90`) → `finalising 95`.
  - Legacy origin: `openvsp_import_service.py:834, 842, 895-960, 1009, 1071-1133`
  - Definition of done: `pct` is monotonically non-decreasing and never exceeds
    95; the three conditional steps are absent when not applicable.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Happy path:** a fixture `.vsp3` with 2 wings and 1 fuselage
      imports with 201 and the expected counts.
- [ ] **TT-02 — Failure:** a `.stl` upload → 400; a 51 MB upload → 413; both
      scaling params → 400; `scale_factor = 20` → 422; bindings absent → 503.
- [ ] **TT-03 — Model isolation:** import A then B in one process and assert B's
      aeroplane has none of A's geoms (the `ClearVSPModel` regression).
- [ ] **TT-04 — Canonicalisation matrix:** all 16 `_DISPLAY_TO_CANONICAL`
      entries plus an unlisted name falling back to `.upper()`.
- [ ] **TT-05 — Unsupported geoms:** each of the 14 `_UNSUPPORTED_REASONS`
      tokens produces a warning and a `lossy_components` entry, and the import
      still returns 201.
- [ ] **TT-06 — Dihedral regression (gh-755):** a 30° section advances
      `cos`/`sin`; a test named for winglets/V-tails pins the pre-gh-755 bug.
- [ ] **TT-07 — Sweep reference change:** `sweep_at_le` against hand-computed
      values, plus the `span ≤ 0` pass-through.
- [ ] **TT-08 — Degenerate sections:** `Span ≤ 0` skipped with a warning;
      `Root_Chord ≤ 0` defaulted to `1.0`.
- [ ] **TT-09 — Terminal x-section:** every imported wing validates against
      `AsbWingSchema.validate_last_xsec_has_no_segment_details`.
- [ ] **TT-10 — Airfoil branch matrix:** all 8 handled `XS_*` shapes plus an
      unknown shape; assert the 6-/16-series caveat warnings and that a
      16-series section is not symmetric.
- [ ] **TT-11 — `.dat` hygiene:** duplicate adjacent points collapse at `1e-9`;
      a repeat import writes no file.
- [ ] **TT-12 — Unit snap table:** `0.3048 → ft`, `0.0254 → in`, `1.0 → None`,
      `0.5 → None`, `NaN → None`, and the ±2 % boundary on both sides.
- [ ] **TT-13 — Unit detection end to end:** a feet fixture converts and warns;
      a fuselage-less fixture does not convert and does not warn (documenting
      the blind spot); the `_unitdetect_*` directory is removed.
- [ ] **TT-14 — Scaling invariants:** after any rescale, every `twist` and every
      mass is bit-identical and exactly one `SCALING` warning is present.
- [ ] **TT-15 — Scaling order:** the slicer receives the unscaled STEP; the
      persisted fuselage x-secs and the stored STEP are both scaled.
- [ ] **TT-16 — Refinement gates:** a Y-dominant geom is not refined; a budget
      of `n = 3` yields `max(15, 3 + 10) = 15`; a frame ratio of `3.0` is
      rejected and the handler schema is kept.
- [ ] **TT-17 — Sewing ladder:** a geom that fails at 1 mm succeeds at 5 mm; a
      geom that fails both leaves `solid_step_path` NULL with a 201 response;
      a negative-volume solid is reversed.
- [ ] **TT-18 — Filename sanitisation:** `"Wing #1 / Left"` → a name matching
      `[A-Za-z0-9._-]+`, truncated to 64 characters.
- [ ] **TT-19 — Per-record best-effort:** one failing wing yields a `WING`
      warning while everything else persists.
- [ ] **TT-20 — SSE sequence:** monotonic `pct`, the conditional steps absent
      when inapplicable, exactly one terminal event, and an `error` frame
      carrying `{status, detail}`.
- [ ] **TT-21 — Temp-file cleanup:** the upload is unlinked on success, on
      error, and after a mid-stream client disconnect.
- [ ] **TT-22 — 🟢 SS_CONTROL end to end** (`Q-VI-1`; expected to fail until wired):
      drive the **production** entry point and assert a `trailing_edge_device`
      lands on the mapped x-section. This test is the definition of done for
      T-31 **and** T-32 together.
- [ ] **TT-23 — 🟢 `validate_geometry` wired** (`Q-VI-2`): a mis-derived planform produces
      a warning through the production pipeline, not only in a direct unit test.
- [ ] **TT-24 — Handler-registration diagnostics:** with one handler module
      raising `ImportError`, the import still runs and the failure is logged.

## Data Migration Tasks

- [ ] **TM-01 — Aircraft imported without control surfaces.** Every aeroplane
      created by this module before T-31/T-32 land has **no** trailing-edge
      devices, regardless of what its source `.vsp3` contained. There is no
      marker on the row to identify them and no warning was recorded at import
      time. Decide: re-import, back-fill from the original file if it was kept,
      or accept and document. 🟢 Accepted and documented (`Q-VI-8`).
- [ ] **TM-02 — Terminal-rib dihedral is NULL on imported wings.** Wings are
      persisted through the geometry-only write schema, so
      `wing_xsecs.dihedral` is `NULL` (`wing-design` BR-7 / gh-951). Interior
      stations are recoverable from `xyz_le`; the terminal rib's rotation is
      not. Decide whether to back-fill the geometry-derived value or leave
      `NULL`. 🟡
- [ ] **TM-03 — Orphaned STEP artefacts.** `cleanup_aeroplane_step_files` is
      best-effort and `construction`-style directories under
      `<ARTIFACTS_BASE_DIR>/openvsp_imports/` have no FK. Sweep for directories
      whose `<aeroplane_uuid>` no longer resolves, and add a periodic
      reconciliation. 🟡
- [ ] **TM-04 — Stale `_unitdetect_*` directories.** The `finally` removes them,
      but a hard process kill during detection leaves one behind. Include the
      `_unitdetect_` prefix in the sweep of TM-03. 🟡
- [ ] **TM-05 — Aircraft imported before gh-755.** Any aeroplane imported with
      the small-angle dihedral shortcut has mis-placed stations on winglets and
      V-tails. There is no version marker; identify candidates by import date
      against the gh-755 merge. 🟡

## Suggested Order

1. **T-01 → T-03** first — the adapter and registry are what every later stage
   calls. T-03's diagnostic fix is cheap and prevents a whole class of silent
   degradation.
2. **T-04 → T-09** next — the pipeline skeleton, dispatch and the warning
   discipline. T-08 blocks everything downstream because every other task
   reports through `ImportContext`. TT-03 (model isolation) should exist before
   any handler work.
3. **T-10 → T-17** — the wing handler. T-12 and T-14 are the two places the
   module has already shipped a defect; write TT-06 and TT-07 first.
   T-16 depends on `wing-design`'s BR-5 being available.
4. **T-18 → T-21** — airfoils, independent of the wing handler and
   parallelisable with step 3. T-20 blocks nothing but should land before any
   bulk-import testing, or the airfoil directory churns.
5. **T-22 → T-27** — units and scaling. T-22 blocks T-23; T-23 and T-25 both
   block T-27, and T-27's ordering constraint is what the fuselage persistence
   in step 6 must respect.
6. **T-28 → T-30** — persistence. T-30 must be landed **consciously**: it is
   the boundary that forecloses T-32, so decide the fix shape before writing it.
7. **T-31 → T-34** — the two inert paths. T-31 and T-32 must land **together**
   (TT-22 is the joint definition of done); T-34 is independent.
8. **T-35 → T-37** last — the REST and SSE layer is thin and only wires what is
   already tested.

## Pending Gaps

- **Was the SS_CONTROL post-pass parked deliberately, or lost in a merge?**
  `register()` exists, is tested, and is called from nowhere in production. The
  answer decides whether T-31/T-32 are a bug fix or a feature.
- **Should the wing import path carry more than geometry?** The write schema is
  `extra="forbid"` and geometry-only, which silently forecloses trailing-edge
  devices, turbulators, spars and explicit dihedral. Widen it, or persist those
  in a second pass?
- **Was `validate_geometry` parked deliberately?** It is complete, tested and
  documented with its own intended call site, and is called from nowhere.
- **Should a unitless legacy file warn?** `LEN_UNIT_TO_METERS` maps
  `LEN_UNITLESS → 1.0`, silently assuming metres.
- **Is there a wing-based fallback for source-unit detection?** A flying wing —
  a core RC case — has no fuselage, so a feet model imports 3.28× too large with
  no signal. Or should the UI force an explicit unit choice?
- **What is the fallback when a user downloads a corrupt solid (#814)?** The
  x-sec path avoids the sewn solid; the CAD download path still consumes it, and
  nothing flags it.
- **Should a failed handler registration be logged, raised, or surfaced as an
  import warning?**
- **Should `n_wings` / `n_fuselages` count parsed or persisted components?**
  Today they count parsed, so a persistence failure inflates the number.
- **Is #791 (camber loss, C_L0 offset ≈0.43 on DG-101G) blocking any
  user-visible accuracy claim**, and is #792 (VLM intractability at 215 s per
  solve) acceptable given AeroBuildup is the default solver?
- **Is concurrency in scope?** The native VSP model, the adapter memo and the
  handler registry are process-global with no lock; two simultaneous imports in
  one worker would interleave.
- **Is open epic #638 still the intended direction** — B5
  (`XS_GENERAL_FUSE` / `XS_FILE_FUSE` / `XS_EDIT_CURVE` polyline sampling) and
  B6 (STEP fallback for CUSTOM / CONFORMAL / NGON_MESH)?
