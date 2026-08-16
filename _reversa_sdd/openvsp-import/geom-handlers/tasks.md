# geom-handlers — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Parent module task list: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] The import pipeline exists and can dispatch by canonical geom token
      (→ [`../vsp3-import-pipeline/tasks.md`](../vsp3-import-pipeline/tasks.md)).
- [ ] `ImportContext` with `warnings`, `lossy_components`, `weight_items`,
      `wing_geom_ids`, `fuselage_geom_ids` (`openvsp_importer.py:99`).
- [ ] Target schemas available: `AsbWingSchema`, `WingXSecSchema`,
      `TrailingEdgeDeviceDetailSchema` (→ `wing-design`), the fuselage
      superellipse schema (→ `fuselage-design`), `WeightItemWrite`
      (→ `mass-and-balance`).
- [ ] `AIRFOILS_DIR` writable — generated `.dat` files land there and are read
      back by every aerodynamic path.
- [ ] The fuselage slicer available for the refinement path
      (→ `fuselage-design`); absent, the handler schema must still be produced.

## Tasks

### Registration

- [ ] **T-GH-01 — Lazy, once-per-process handler registration.**
  `_ensure_handlers_loaded` imports wing, fuselage, blank and custom, each inside
  its own `try: … except ImportError: pass`, and registers the two post-passes
  `_resolve_vehicle_cg` and `_drop_degenerate_fuselages`.
  - Legacy origin: `app/converters/openvsp_importer.py:287-321`
  - Definition of done: after loading, the registry holds exactly `WING`,
    `FUSELAGE`, `BLANK`, `CUSTOM`; making one module unimportable leaves the
    other three registered.
  - Confidence: 🟢

- [ ] **T-GH-02 — 🟢 Register the SS_CONTROL post-pass** (`Q-VI-1`).
  `openvsp_ss_control.register()` must be called from the **production** loader,
  not only from a test.
  - Legacy origin: the omission is at `openvsp_importer.py:287-321`; the only
    caller today is `app/tests/test_openvsp_ss_control.py:24`
  - Definition of done: a test that imports a real `.vsp3` containing an
    SS_CONTROL through the production entry point finds a trailing-edge device on
    the aeroplane. A test that registers the pass itself does **not** satisfy
    this — that is exactly how the defect stayed hidden.
  - Confidence: 🟢 (the defect) / 🔴 (whether wiring it changes any stored data
    expectations downstream — see `questions.md`)

- [ ] **T-GH-03 — 🟢 Wire it in** (`Q-VI-2`).
  gh-647's checker is complete and tested but never called. Its docstring shows
  the intended wiring (`result.warnings.extend(mismatches)`).
  - Legacy origin: `app/converters/openvsp_validation.py`;
    `DEFAULT_REL_TOL = 0.01`
  - Definition of done: either it runs at the end of every import and its
    mismatches appear in the response warnings, or the module is deleted. Shipping
    it inert a second time is not acceptable.
  - Confidence: 🟢 — decided in the validation interview

- [ ] **T-GH-04 — Named reasons for unsupported geom types.**
  `_UNSUPPORTED_REASONS` covering PROP, DISK, MESH, CONFORMAL, NGON_MESH, HUMAN,
  POD, BOR, STACK, ELLIPSOID, WIRE_FRAME, HINGE, PT_CLOUD, GEAR.
  - Legacy origin: `openvsp_importer.py:242-260`
  - Definition of done: each listed type produces its own reason text; an unlisted
    type still produces a generic warning rather than silence.
  - Confidence: 🟢

### Wing planform

- [ ] **T-GH-05 — `_read_section_parm` with a one-index fallback.**
  Try group `XSec_{i}`, then `XSec_{i-1}`, then return `0.0`.
  - Legacy origin: `app/converters/openvsp_wing_handler.py:109-121`
  - Definition of done: all three branches are covered by unit tests.
  - Confidence: 🟢

- [ ] **T-GH-06 — The synthetic root x-section.**
  `{xyz_le: [0,0,0], chord: XSec_1.Root_Chord, twist: 0, x_sec_type: "root"}`;
  `Root_Chord ≤ 0` warns and defaults to **1.0 m**.
  - Legacy origin: `openvsp_wing_handler.py:902-910`
  - Definition of done: a file with `Root_Chord = 0` imports with chord 1.0 and a
    warning naming the geom.
  - Confidence: 🟢

- [ ] **T-GH-07 — Relative/absolute dihedral and twist (gh-755).**
  `RelativeDihedralFlag` / `RelativeTwistFlag` select `+=` or `=` per section.
  - Legacy origin: `openvsp_wing_handler.py` (the accumulation loop)
  - Definition of done: both flag states covered; two 5° sections give 10°
    relative and 5° absolute.
  - Confidence: 🟢

- [ ] **T-GH-08 — `sweep_at_le`.**
  `tan(Λ_to) = tan(Λ_from) − (xref_to − xref_from)·(c_root − c_tip)/span`, and
  the input is returned unchanged when `span ≤ 0`. Sweep is **absolute per
  section** — never accumulate it.
  - Legacy origin: `openvsp_wing_handler.py` (`sweep_at_le`); the comment cites
    `WingGeom.cpp:1111`
  - Definition of done: a tapered panel at `Sweep_Location 0.25` reproduces the
    closed form; a zero-span call returns the input; a test asserts that sweep is
    not accumulated across sections.
  - Confidence: 🟢

- [ ] **T-GH-09 — Station advance along the dihedral.**
  ```
  cum_x += Span·tan(Λ_LE)
  cum_y += Span·cos(cum_dihedral)
  cum_z += Span·sin(cum_dihedral)
  ```
  - Legacy origin: `openvsp_wing_handler.py:985-989` (gh-755)
  - Definition of done: a 45° panel of span 1.0 advances y and z by `√2/2` each.
    Add a regression test at 60–90° — the pre-gh-755 `cum_y += Span` shortcut
    passes at small angles and must fail here.
  - Confidence: 🟢

- [ ] **T-GH-10 — Skip a non-positive-span section.**
  Warning + `ctx.mark_lossy(geom_id)` + skip.
  - Legacy origin: `openvsp_wing_handler.py` (the section loop)
  - Definition of done: the section is absent from the schema, a warning exists,
    and the geom id appears once in `lossy_components` even for two bad sections.
  - Confidence: 🟢

- [ ] **T-GH-11 — Terminal x-section carries no segment data.**
  Emit the last station with `x_sec_type = None`.
  - Legacy origin: `openvsp_wing_handler.py:994-1005`; the rule is `wing-design`
    BR-5
  - Definition of done: `AsbWingSchema.validate_last_xsec_has_no_segment_details`
    passes for every imported wing.
  - Confidence: 🟢

- [ ] **T-GH-12 — Placement, symmetry and end caps.**
  `XForm` → `X/Y/Z_Location`, `X/Y/Z_Rotation`; `Sym.Sym_Planar_Flag` →
  `wing.symmetric`; `EndCap` → tip treatment.
  - Legacy origin: `openvsp_wing_handler.py`; data-dictionary §OpenVSP parms read
  - Definition of done: a mirrored wing imports with `symmetric = True`, and the
    geom offset is applied to every station.
  - Confidence: 🟢

### Airfoils

- [ ] **T-GH-13 — `import_airfoil_from_xsec`, all branches, never raising.**
  Implement the full `XS_*` table from `requirements.md` BR-OV17, ending in the
  `naca0012.dat` fallback.
  - Legacy origin: `app/converters/openvsp_airfoil.py:963-1180`
  - Definition of done: every listed shape yields the documented result; an
    unknown shape yields the fallback; a property test asserts the function never
    raises for any shape id.
  - Confidence: 🟢

- [ ] **T-GH-14 — NACA name builders and `.dat` generation.**
  `naca_4series_name`, `naca_5series_name` (gh-733), `naca_6series_name`,
  `naca_16series_name`; `ensure_naca4_dat` (gh-700), `ensure_naca5_dat`;
  `_NACA_DAT_HALF_POINTS = 80`.
  - Legacy origin: `openvsp_airfoil.py:41, 963-1180`
  - Definition of done: names match the canonical designations for known parm
    sets; generated files have 80 points per surface. Pin the gh-733 regression:
    a 16-series section must **not** come out symmetric.
  - Confidence: 🟢

- [ ] **T-GH-15 — Disclose the 6-/16-series approximation.**
  An `info` warning stating that t/c and design C_L are exact but the thickness
  shape is a 4-digit approximation, not conformal-mapped.
  - Legacy origin: `openvsp_airfoil.py` (the six/one-six branches)
  - Definition of done: both branches emit the warning; the text names the
    affected x-section.
  - Confidence: 🟢

- [ ] **T-GH-16 — `_dedup_consecutive_points` at `tol = 1e-9`.**
  - Legacy origin: `openvsp_airfoil.py:712` (gh-789)
  - Definition of done: coordinates containing a `1e-12` duplicate come out with
    one point; a test feeds the result to AeroSandbox `repanel()` (or an
    equivalent assertion) to pin why this exists.
  - Confidence: 🟢

- [ ] **T-GH-17 — Content-addressed `.dat` writes.**
  Hash the coordinates and skip the write when unchanged.
  - Legacy origin: `openvsp_airfoil.py:731-750`
  - Definition of done: re-importing the same file does not change any `.dat`
    mtime.
  - Confidence: 🟢

- [ ] **T-GH-18 — `morph_airfoils` with `_raw_blend` fallback.**
  Kulfan/CST fit at both ends, blend, fall back on fit failure. It is the
  `airfoil_morph_fn` seam used by `segment_split`.
  - Legacy origin: `openvsp_airfoil.py:876-901` (gh-796)
  - Definition of done: a deliberately unfittable section still produces a
    blended result via `_raw_blend`.
  - Confidence: 🟢

- [ ] **T-GH-19 — 🟢 Ship as is; the camber loss is acceptable at RC/UAV scale** (`Q-VI-8`).
  The importer currently loses camber, producing a `C_L0` offset of ≈ 0.43 on the
  DG-101G.
  - Legacy origin: `scripts/vspaero_benchmark/FINDINGS.md` finding F4; issue #791
    open
  - Definition of done: the imported DG-101G's `C_L0` matches the measured polar
    within a stated tolerance. The root cause is not identified in the analysed
    code — investigate before implementing.
  - Confidence: 🟡

### Fuselage

- [ ] **T-GH-20 — Superellipse x-section derivation.**
  - Legacy origin: `app/converters/openvsp_fuselage_handler.py` (477 l.)
  - Definition of done: a FUSELAGE geom yields ≥ 2 x-sections that satisfy the
    `fuselage-design` schema (`min_length=2`).
  - Confidence: 🟢

- [ ] **T-GH-21 — Gate 1: x-dominance on the handler frame.**
  `extent_x ≥ 1.2·extent_y` **and** `≥ 1.2·extent_z`, computed from the
  **handler** x-section positions — never from the STEP bounding box.
  - Legacy origin: `app/services/openvsp_import_service.py:494-520`
  - Definition of done: a `symmetric=True` fuselage whose STEP contains both
    halves still passes x-dominance; a test documents why the STEP bbox is the
    wrong input.
  - Confidence: 🟢

- [ ] **T-GH-22 — Gate 2: the station budget.**
  `min(80, max(15, n + 5·(n−1)))`, fed to `vsp_anchored_x_stations` with VSP
  stations as mandatory anchors and intermediates weighted by shape change.
  - Legacy origin: `openvsp_import_service.py:653` (gh-732)
  - Definition of done: `n = 2` gives 15, `n = 20` is capped at 80, and every VSP
    station appears in the output.
  - Confidence: 🟢

- [ ] **T-GH-23 — Gate 4: the frame-ratio check.**
  Accept the refined result only when
  `0.5 ≤ x_span(refined)/x_span(handler) ≤ 2.0`; otherwise keep the handler
  schema and warn. `_MM_TO_M = 0.001` converts the slicer output.
  - Legacy origin: `openvsp_import_service.py:543-559` (gh-803), `:491`
  - Definition of done: a refined span 3× the handler span is rejected with a
    warning; a 1.2× refinement is accepted.
  - Confidence: 🟢
  - *(Gate 3 — slicing the surface STEP rather than the solid — belongs to
    [`../step-export-and-sewing/tasks.md`](../step-export-and-sewing/tasks.md)
    T-SE-13.)*

- [ ] **T-GH-24 — `_drop_degenerate_fuselages` post-pass.**
  - Legacy origin: `openvsp_fuselage_handler.py`; registered in
    `_ensure_handlers_loaded`
  - Definition of done: a degenerate geom is absent from the persisted aeroplane
    and a warning explains the drop.
  - Confidence: 🟢

### Mass and control surfaces

- [ ] **T-GH-25 — BLANK → weight items, and `_resolve_vehicle_cg`.**
  - Legacy origin: `app/converters/openvsp_blank_handler.py` (159 l.)
  - Definition of done: each BLANK yields one weight item at its geom position;
    the post-pass sets the aeroplane CG. Masses are **never** scaled (BR-75).
  - Confidence: 🟢

- [ ] **T-GH-26 — SS_CONTROL → TrailingEdgeDevice mapping.**
  ```
  LE_Flag ≥ 0.5   → info warning + skip
  EtaFlag ≥ 0.5   → EtaStart/EtaEnd  else UStart/UEnd
  rel_chord_root  = 1 − Length_C_Start
  rel_chord_tip   = 1 − Length_C_End
  role            = ControlSurfaceRole.OTHER
  symmetric       = wing.symmetric
  seg_idx  = clamp(int(u_mid·n_sec)+1, 1, n_sec)
  xsec_idx = seg_idx − 1                        # the INBOARD station
  ```
  A second SS_CONTROL on the same segment is rejected with a warning.
  - Legacy origin: `app/converters/openvsp_ss_control.py` (172 l.),
    `_u_to_segment_index`
  - Definition of done: `Length_C_Start = 0.25` gives `rel_chord_root = 0.75`;
    the device lands on the inboard station; a duplicate is refused. Depends on
    **T-GH-02** to be reachable at all.
  - Confidence: 🟢

- [ ] **T-GH-27 — CUSTOM geom handling.**
  - Legacy origin: `app/converters/openvsp_custom_handler.py` (155 l.)
  - Definition of done: a CUSTOM geom imports as far as the RC scope allows and
    warns about anything it cannot represent.
  - Confidence: 🟡 — the module was read at summary level only

## Test Tasks

- [ ] **TT-GH-01** — Happy path: a two-panel dihedral wing imports with correct
      station positions (see `requirements.md`, Acceptance Criteria).
- [ ] **TT-GH-02** — Failure path: a zero-span section is dropped, warned and
      marked lossy.
- [ ] **TT-GH-03** — Regression (gh-755): a 60° panel; the small-angle shortcut
      must fail this test.
- [ ] **TT-GH-04** — Regression (gh-733): a 16-series section is not symmetric.
- [ ] **TT-GH-05** — Regression (gh-789): no duplicate adjacent points survive.
- [ ] **TT-GH-06** — Contract: `import_airfoil_from_xsec` never raises, for every
      shape id including unknown ones.
- [ ] **TT-GH-07** — Registration from the **production** entry point finds the
      SS_CONTROL pass (this is the test whose absence hid the defect).
- [ ] **TT-GH-08** — Gate: a `symmetric=True` fuselage passes x-dominance on the
      handler frame.
- [ ] **TT-GH-09** — Gate: a 3× refined frame is rejected and the handler schema
      is kept.
- [ ] **TT-GH-10** — Terminal station: `AsbWingSchema` validation passes for
      every imported wing.
- [ ] **TT-GH-11** — Idempotence: a second import of the same file rewrites no
      `.dat` file.

## Suggested Order

1. **T-GH-05 → T-GH-12** first — the wing planform is the module's product, and
   every other handler is simpler. Write TT-GH-03 (the 60° regression) before
   T-GH-09 so the small-angle shortcut cannot creep back in.
2. **T-GH-13 → T-GH-18** next; the wing handler calls into airfoil resolution per
   station, so stub it during step 1 and fill it here. TT-GH-06's never-raise
   property test should exist before the branches do.
3. **T-GH-01 / T-GH-04** at any point, but **T-GH-02** (SS_CONTROL registration)
   must land together with **T-GH-26**, and with TT-GH-07 written first.
4. **T-GH-20 → T-GH-24** after the STEP export exists
   (→ `../step-export-and-sewing/`), because gates 3 and 4 need a file to slice.
5. **T-GH-25 / T-GH-27** are independent.
6. **T-GH-03** and **T-GH-19** are blocked on human decisions / investigation and
   must not be guessed.

## Resolved by the validation interview (🟢/🟡)

- **Wiring SS_CONTROL changes what an import produces.** Every aircraft imported
  so far arrived without control surfaces. Turning the pass on will start
  creating TEDs with role `OTHER` — does anything downstream (trim, operating
  points, the copilot) assume their absence?
- **`validate_geometry`: wire it or delete it?** Shipping a complete, tested
  checker that never runs is worse than not having it.
- **Issue #791 — where is camber lost?** The symptom is quantified
  (`C_L0` ≈ 0.43 on the DG-101G) but the responsible branch was not identified in
  the analysed code.
- **Is the one-index parm fallback intentional inheritance or a bug workaround?**
  `XSec_{i}` missing with `XSec_{i-1}` present is indistinguishable from a
  deliberate default, and `0.0` is a legal value for several of these parms.
- **Should `_u_to_segment_index` clamp or report?** A sub-surface that runs past
  the tip currently resolves silently to the last segment.
- **The CUSTOM handler was read at summary level only** — its parm coverage and
  degradation behaviour are unconfirmed.
