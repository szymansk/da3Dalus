# geom-handlers

> Use-case specification, nested under the module [`openvsp-import`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: openvsp-import
> (Handler registration, Wing planform derivation, Airfoil resolution,
> SS_CONTROL → TrailingEdgeDevice, Fuselage refinement gates),
> `_reversa_sdd/data-dictionary.md` §Module: openvsp-import (OpenVSP parms read),
> `_reversa_sdd/domain.md` §2.11.

## Overview

`geom-handlers` is the translation layer of the import: one handler per OpenVSP
geom type, each turning VSP parm groups into a piece of `AeroplaneSchema`. It
owns the wing planform maths (cumulative dihedral, twist and leading-edge sweep),
airfoil resolution for every `XS_*` shape, the fuselage superellipse derivation
and its refinement gates, the BLANK → weight-item mapping, and the SS_CONTROL →
trailing-edge-device pass. Every handler is written to **degrade rather than
raise**: an unreadable parm becomes a default plus a warning, an unrecognised
airfoil becomes a fallback `.dat`. 🟢

## Responsibilities

- Register exactly the handlers and post-passes the pipeline dispatches to. 🟢
- Derive a wing's stations from its per-section parms, honouring VSP's
  relative/absolute flags and its per-section-absolute sweep convention. 🟢
- Resolve every x-section's airfoil to a usable `.dat`, without ever raising. 🟢
- Derive fuselage superellipse cross-sections and, behind four gates, refine them
  from the exported STEP. 🟢
- Drop degenerate fuselages in a post-pass. 🟢
- Map BLANK geoms to weight items and resolve a vehicle CG in a post-pass. 🟢
- Map CUSTOM geoms as far as the RC scope allows. 🟢
- Map SS_CONTROL sub-surfaces to trailing-edge devices on the correct inboard
  station. 🟢 code / 🟢 **Wired fully — registration AND the write path** (`Q-VI-1`, maintainer-answered).
- Record a typed reason for every geom type without a handler. 🟢

**Explicitly NOT this use case's responsibility:** loading the file, clearing the
native model, type canonicalisation and the post-pass loop
(→ [`../vsp3-import-pipeline/`](../vsp3-import-pipeline/requirements.md)); STEP
export and sewing
(→ [`../step-export-and-sewing/`](../step-export-and-sewing/requirements.md));
unit detection and scaling (→ the pipeline use case); the persistence of the
resulting schema (→ `wing-design`, `fuselage-design`, `mass-and-balance`).

## Business Rules

> **ID provenance.** `BR-73`–`BR-77` and `BR-OV1`–`BR-OV19` are inherited
> verbatim from [`../requirements.md`](../requirements.md). Ids from `BR-OV20`
> upward are **defined here**: they extend the module's numbering for behaviour
> only this use case covers, and are not (yet) restated at module level.

### Registration

- **BR-OV7 — Four handlers, two post-passes, and two modules that are never
  wired.** 🟢 **Wired fully — registration AND the write path** (`Q-VI-1`, maintainer-answered). `_ensure_handlers_loaded` (`app/converters/openvsp_importer.py:287-321`)
  imports and registers exactly four modules — wing, fuselage, blank, custom —
  each inside its own `try: … except ImportError: pass`. Registered handlers:
  `WING`, `FUSELAGE`, `BLANK`, `CUSTOM`. Registered post-passes:
  `openvsp_blank_handler._resolve_vehicle_cg` and
  `openvsp_fuselage_handler._drop_degenerate_fuselages`.

  **`openvsp_ss_control.register()` is never called in production.** A
  repository-wide grep finds exactly one caller,
  `app/tests/test_openvsp_ss_control.py:24`. The gh-644 post-pass therefore never
  runs during a real import: imported aircraft silently arrive with **no control
  surfaces**, while the unit tests pass because they register it themselves.
- **BR-OV8 — 🟢 **`validate_geometry` is wired in** (`Q-VI-2`, maintainer-answered): the gh-647 cross-check is what would have caught the whole class of import defects, including the unit errors.**
  `app/converters/openvsp_validation.py` (gh-647, `DEFAULT_REL_TOL = 0.01`) is
  referenced only from its own test module. Its docstring shows the intended
  wiring (`result.warnings.extend(mismatches)`), which does not exist.
- **BR-OV9 — An unsupported geom type gets a named reason.** 🟢
  `_UNSUPPORTED_REASONS` (l.242-260) covers 14 types: PROP, DISK, MESH,
  CONFORMAL, NGON_MESH, HUMAN, POD, BOR, STACK, ELLIPSOID, WIRE_FRAME, HINGE,
  PT_CLOUD, GEAR.

### Wing planform

- **BR-OV10 — Section parms fall back one index.** 🟢 `_read_section_parm`
  (`app/converters/openvsp_wing_handler.py:109-121`) tries group `XSec_{i}`,
  then `XSec_{i-1}`, and returns `0.0` when neither exists.
- **BR-OV11 — The root x-section is synthetic.** 🟢
  `{xyz_le: [0,0,0], chord: XSec_1.Root_Chord, twist: 0, x_sec_type: "root"}`; a
  `Root_Chord ≤ 0` warns and defaults to **1.0 m** (l.902-910).
- **BR-OV12 — Dihedral and twist honour VSP's relative flags (gh-755).** 🟢
  `RelativeDihedralFlag` / `RelativeTwistFlag` on the geom select accumulation
  (`+=`) or replacement (`=`) per section.
- **BR-OV13 — Sweep is absolute per section.** 🟢 VSP has no relative-sweep flag
  (the code comment cites `WingGeom.cpp:1111`). The leading-edge sweep is
  recovered from the reference location:

  ```
  tan(Λ_to) = tan(Λ_from) − (xref_to − xref_from) · (c_root − c_tip) / span
  Λ_LE = sweep_at_le(Sweep, Sweep_Location, Span,
                     c_root = prev_chord, c_tip = Tip_Chord)
         # returns Λ_from unchanged when span ≤ 0
  ```

- **BR-OV14 — Span walks the dihedral, not the y axis (gh-755).** 🟢

  ```
  cum_x += Span · tan(Λ_LE)
  cum_y += Span · cos(cum_dihedral)      # NOT  cum_y += Span
  cum_z += Span · sin(cum_dihedral)
  ```

  The small-angle shortcut was the pre-gh-755 defect, visible on winglets and
  V-tails above roughly 5° of dihedral (l.985-989).
- **BR-OV15 — `Span ≤ 0` skips the section.** 🟢 Warning + `mark_lossy` + skip.
- **BR-OV16 — The last x-section carries no segment data.** 🟢 Emitted with
  `x_sec_type = None` so `AsbWingSchema.validate_last_xsec_has_no_segment_details`
  passes (l.994-1005) — the terminal-station rule owned by `wing-design` (BR-5).
- **BR-OV32 — Placement and symmetry come from separate groups.** 🟢 `XForm`
  group → `X/Y/Z_Location`, `X/Y/Z_Rotation`; `Sym` group → `Sym_Planar_Flag` →
  `wing.symmetric`; `EndCap` group → tip caps.

### Airfoils

- **BR-OV17 — Airfoil resolution never raises.** 🟢
  `import_airfoil_from_xsec` (`app/converters/openvsp_airfoil.py:963-1180`)
  switches on `vsp.GetXSecShape(xs_id)`:

  | VSP shape | Result |
  |---|---|
  | `XS_FOUR_SERIES` | `naca_4series_name(Camber, CamberLoc, ThickChord)` + `ensure_naca4_dat` (gh-700) |
  | `XS_FOUR_DIGIT_MOD` | same name + `-mod`; plain 4-digit `.dat` — verified on 3.50 that no `MeanLine_a` parm exists |
  | `XS_FIVE_DIGIT` | `naca_5series_name(Camber, CamberLoc, Reflex, ThickChord)` + `ensure_naca5_dat` (gh-733) |
  | `XS_FIVE_DIGIT_MOD` | same + `-mod`, base 5-digit `.dat` |
  | `XS_SIX_SERIES` | `naca_6series_name(Series, IdealCl, ThickChord, A)`; a-family mean line + 4-digit thickness **approximation** + info warning |
  | `XS_ONE_SIX_SERIES` | `naca_16series_name(IdealCl, ThickChord)`, `a = 1.0`, same approximation |
  | `XS_FILE_AIRFOIL` | `_export_selig` verbatim |
  | `XS_CST_AIRFOIL` | info warning + sampled Selig export (`tag="vsp_imported_cst"`) |
  | anything else | warning + Selig export (`tag="vsp_imported_unknown"`); last resort `./components/airfoils/naca0012.dat` |

- **BR-OV18 — 6- and 16-series are approximations, and say so.** 🟢 t/c and
  design C_L are exact; the thickness shape is not conformal-mapped. Before
  gh-733 the 16-series path read a non-existent `Camber` parm and therefore
  always produced a symmetric section.
- **BR-OV19 — Generated `.dat` files are de-duplicated and content-addressed.** 🟢
  `write_imported_airfoil_dat` (l.731-750) runs `_dedup_consecutive_points`
  (`tol = 1e-9`, the gh-789 fix for AeroSandbox `repanel()` crashing on duplicate
  points), hashes the coordinates, and **skips the write** when unchanged.
  `_NACA_DAT_HALF_POINTS = 80` (l.41).
- **BR-OV20 — Airfoil morphing falls back to a raw blend.** 🟢 `morph_airfoils`
  (l.876-901) fits both ends with Kulfan/CST and blends; on a fit failure it
  falls back to `_raw_blend` (gh-796). It is the `airfoil_morph_fn` seam used by
  `segment_split`.
- 🔴 **F4 / issue #791 — camber is lost.** The importer produces a `C_L0` offset
  of about 0.43 against the measured DG-101G polar. Confirmed open by the
  `scripts/vspaero_benchmark/` cross-validation.

### Fuselage

- **BR-OV25 — Refinement is gated on the handler schema, not the STEP.** 🟢
  `_is_x_dominant_fuselage` (`app/services/openvsp_import_service.py:494-520`)
  refines only when the **handler** x-section positions give
  `extent_x ≥ 1.2·extent_y` **and** `≥ 1.2·extent_z`. Using the STEP bounding box
  would misjudge a `symmetric=True` geom, whose STEP contains both halves and
  therefore looks Y-dominant.
- **BR-OV26 — The station budget is bounded and VSP-anchored (gh-732).** 🟢
  `min(80, max(15, n + 5·(n−1)))` for `n` handler x-secs, fed to
  `vsp_anchored_x_stations`: VSP stations are mandatory anchors, intermediates
  are distributed weighted by shape change.
- **BR-OV27 — A refined frame that disagrees with the handler is rejected
  (gh-803).** 🟢 `_slicer_frame_matches_handler` (l.543-559) accepts the refined
  result only when `0.5 ≤ x_span(refined)/x_span(handler) ≤ 2.0`. Otherwise the
  handler schema wins. `_MM_TO_M = 0.001` converts the slicer's output.
- **BR-OV33 — Degenerate fuselages are dropped in a post-pass.** 🟢
  `_drop_degenerate_fuselages` is one of the two registered post-passes.

### Mass

- **BR-OV34 — BLANK geoms become weight items.** 🟢
  `app/converters/openvsp_blank_handler.py` (159 l.) appends `WeightItemWrite`
  records to `ImportContext.weight_items`; `_resolve_vehicle_cg` is the
  registered post-pass that turns them into the aeroplane's CG.
- **BR-75 — Masses are never scaled.** 🟢 See the module spec; a scaling run
  always appends an `info` warning saying so.

### Control surfaces

- **BR-OV21 — SS_CONTROL maps trailing-edge devices only.** 🟢 (never reached —
  BR-OV7)

  ```
  LE_Flag ≥ 0.5   → info warning + skip           (LE devices are out of scope)
  EtaFlag ≥ 0.5   → use EtaStart/EtaEnd, else UStart/UEnd
  rel_chord_root  = 1 − Length_C_Start            # VSP measures from the TE
  rel_chord_tip   = 1 − Length_C_End
  deflection_deg  = Deflection
  role            = ControlSurfaceRole.OTHER      # the user re-tags in the UI
  symmetric       = wing.symmetric
  segment index   = _u_to_segment_index(u_mid, n_sec)
                  = clamp(int(u · n_sec) + 1, 1, n_sec)
  xsec index      = segment index − 1             # the INBOARD station
  ```

  A second SS_CONTROL landing on the same segment is rejected with a warning.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-GH-01 | Register handlers for WING, FUSELAGE, BLANK and CUSTOM, and the two post-passes | Must | The registry contains exactly those four keys after `_ensure_handlers_loaded` |
| RF-GH-02 | Register the SS_CONTROL post-pass | Must | An imported wing with a trailing-edge sub-surface carries a TED (🔴 not met — the legacy `register()` is never called) |
| RF-GH-03 | Tolerate a handler module that cannot be imported | Should | A missing optional handler module leaves the other registrations intact |
| RF-GH-04 | Read a section parm with a one-index fallback | Must | `XSec_{i}` is tried first, then `XSec_{i-1}`, then `0.0` |
| RF-GH-05 | Emit a synthetic root x-section | Must | The first station is at the origin with `x_sec_type "root"` and the VSP root chord |
| RF-GH-06 | Default a non-positive root chord to 1.0 m with a warning | Must | `Root_Chord = 0` yields chord 1.0 and a warning |
| RF-GH-07 | Accumulate or replace dihedral and twist per the VSP flags | Must | Both flag states are covered by tests |
| RF-GH-08 | Convert the section sweep to a leading-edge sweep | Must | `sweep_at_le` reproduces the documented tangent relation; `span ≤ 0` returns the input unchanged |
| RF-GH-09 | Advance the station position along the dihedral | Must | A 10° panel of span `s` advances `y` by `s·cos 10°` and `z` by `s·sin 10°` |
| RF-GH-10 | Skip a non-positive-span section with a warning and mark it lossy | Must | The section is absent; a warning exists; the geom id is in `lossy_components` |
| RF-GH-11 | Emit the terminal x-section without segment data | Must | `AsbWingSchema` validation passes |
| RF-GH-12 | Read placement, symmetry and end caps from their own parm groups | Should | `Sym_Planar_Flag` drives `wing.symmetric`; `XForm` drives geom placement |
| RF-GH-13 | Resolve every documented `XS_*` shape to a `.dat` | Must | Each row of the BR-OV17 table produces the named result |
| RF-GH-14 | Never raise from airfoil resolution | Must | An unknown shape falls back to `naca0012.dat` and warns |
| RF-GH-15 | Warn that 6- and 16-series thickness shapes are approximated | Must | An `info` warning accompanies both |
| RF-GH-16 | De-duplicate consecutive points and skip unchanged writes | Must | No two consecutive points within `1e-9`; a re-import rewrites nothing |
| RF-GH-17 | Blend segment airfoils with a raw-blend fallback | Should | A CST fit failure still yields a blended section |
| RF-GH-18 | Derive fuselage superellipse x-sections | Must | A FUSELAGE geom yields ≥ 2 x-sections |
| RF-GH-19 | Refine from the STEP only when all gates pass | Should | X-dominance on the handler schema, the station budget, the surface-STEP source and the 0.5–2.0 frame ratio all hold |
| RF-GH-20 | Drop degenerate fuselages | Should | A degenerate geom is absent from the persisted aeroplane |
| RF-GH-21 | Map BLANK geoms to weight items and resolve the vehicle CG | Should | Each BLANK yields a weight item; the post-pass sets the CG |
| RF-GH-22 | Map SS_CONTROL to a TED on the inboard station of the covered segment | Must | `xsec_idx = seg_idx − 1`; `rel_chord_root = 1 − Length_C_Start` (🔴 unreachable today) |
| RF-GH-23 | Skip a leading-edge sub-surface with an info warning | Must | `LE_Flag ≥ 0.5` creates nothing and explains why |
| RF-GH-24 | Reject a second SS_CONTROL on the same segment | Should | The second one warns and is skipped |
| RF-GH-25 | Preserve airfoil camber through the import | Should | 🔴 Not met — issue #791: a `C_L0` offset of ≈ 0.43 on the DG-101G |
| RF-GH-26 | Import propulsion, inertia or CS-group gains from any geom | Won't | Out of scope (ADR 0018) |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Robustness | A handler module that fails to import does not break registration | `_ensure_handlers_loaded` — per-module `try/except ImportError` | 🟢 |
| Robustness | Airfoil resolution has a terminal fallback and never raises | `openvsp_airfoil.py:963-1180` | 🟢 |
| Robustness | An unreadable parm returns `0.0` rather than raising | `_read_section_parm` (l.109-121) | 🟢 |
| Correctness | Dihedral is applied trigonometrically, not by small-angle approximation | `openvsp_wing_handler.py:985-989` (gh-755) | 🟢 |
| Correctness | Sweep is treated as absolute per section, matching VSP's own model | comment citing `WingGeom.cpp:1111` | 🟢 |
| Correctness | Generated `.dat` files carry no duplicate consecutive points | `_dedup_consecutive_points`, `tol = 1e-9` (gh-789) | 🟢 |
| Correctness | Refinement is judged on the handler frame, because a symmetric geom's STEP looks Y-dominant | `_is_x_dominant_fuselage` (l.494-520) | 🟢 |
| Correctness | Refined slicer output is rejected outside a 0.5–2.0 frame ratio | `_slicer_frame_matches_handler` (l.543-559, gh-803) | 🟢 |
| Performance | An unchanged airfoil `.dat` is not rewritten | content hash gate (l.731-750) | 🟢 |
| Performance | The fuselage station budget is capped at 80 | `min(80, max(15, n + 5(n−1)))` | 🟢 |
| Observability | Every degradation is a typed `ImportWarning` naming the component | `ImportContext.add_warning` | 🟢 |
| Testability | The handlers are pure schema producers — no DB, no HTTP | the handler signatures | 🟡 |

## Acceptance Criteria

```gherkin
Feature: Handler registration

  Scenario: The four production handlers are registered
    Given a fresh process
    When the handlers are loaded
    Then WING, FUSELAGE, BLANK and CUSTOM are registered
    And the blank CG and degenerate-fuselage post-passes are registered

  Scenario: The SS_CONTROL post-pass is registered
    Given a fresh process
    When the handlers are loaded
    Then the SS_CONTROL post-pass is registered
    # BR-OV7: it is NOT — only the test module registers it, so control surfaces
    # are silently dropped from every real import

  Scenario: A missing handler module is tolerated
    Given the custom handler module cannot be imported
    When the handlers are loaded
    Then WING, FUSELAGE and BLANK are still registered

Feature: Wing planform

  Scenario: A section parm falls back one index
    Given XSec_2 has no Span parm but XSec_1 does
    When the section is read
    Then XSec_1's value is used

  Scenario: A missing parm reads as zero
    Given neither XSec_2 nor XSec_1 has the parm
    When the section is read
    Then the value is 0.0

  Scenario: A non-positive root chord defaults
    Given XSec_1.Root_Chord is 0
    When the wing is derived
    Then the root chord is 1.0
    And a warning records the substitution

  Scenario: Dihedral walks the span
    Given a section with Span 1.0 and cumulative dihedral 10 degrees
    When the station position is advanced
    Then y increases by cos(10 degrees)
    And z increases by sin(10 degrees)

  Scenario: Relative flags accumulate
    Given RelativeDihedralFlag is set and two sections of 5 degrees
    When the wing is derived
    Then the second section's cumulative dihedral is 10 degrees

  Scenario: Absolute flags replace
    Given RelativeDihedralFlag is cleared and sections of 5 then 8 degrees
    When the wing is derived
    Then the second section's cumulative dihedral is 8 degrees

  Scenario: Sweep is converted to the leading edge
    Given Sweep 20 degrees at Sweep_Location 0.25 over span 1.0
    When the LE sweep is computed
    Then tan of the result equals tan(20 degrees) minus 0.25 times (c_root - c_tip) / 1.0

  Scenario: A zero-span section is dropped
    Given a section whose Span is 0
    When the wing is derived
    Then that section is absent
    And the geom is marked lossy

Feature: Airfoil resolution

  Scenario: A four-series section is generated
    Given an XS_FOUR_SERIES x-section
    When the airfoil is resolved
    Then the name matches naca_4series_name for its parms
    And the .dat has 80 points per half

  Scenario: A six-series section warns
    Given an XS_SIX_SERIES x-section
    When the airfoil is resolved
    Then an info warning states the thickness shape is approximated

  Scenario: An unknown shape falls back without raising
    Given an unrecognised x-section shape
    When the airfoil is resolved
    Then a Selig export tagged "vsp_imported_unknown" is attempted
    And the last resort is ./components/airfoils/naca0012.dat
    And no exception is raised

  Scenario: An unchanged .dat is not rewritten
    Given an airfoil whose coordinate hash is unchanged
    When it is resolved again
    Then the file is not written

  Scenario: Consecutive duplicate points are removed
    Given generated coordinates containing two points 1e-12 apart
    When the .dat is written
    Then only one of them remains

Feature: Fuselage

  Scenario: Refinement is judged on the handler frame
    Given a symmetric fuselage whose STEP contains both halves
    When x-dominance is evaluated
    Then the handler x-section positions are used, not the STEP bounding box

  Scenario: A disagreeing refined frame is rejected
    Given a refined x_span 3.5 times the handler x_span
    When the refinement is evaluated
    Then the handler schema is kept
    And a warning records the rejection

  Scenario: The station budget is bounded
    Given a fuselage with 20 handler x-sections
    When stations are planned
    Then the count is at most 80 and at least 15

Feature: Control surfaces

  Scenario: A trailing-edge sub-surface becomes a TED
    Given SS_Control_1 with LE_Flag 0 and Length_C_Start 0.25
    When the post-pass runs
    Then a TED exists on the inboard station of the covered segment
    And its rel_chord_root is 0.75
    And its role is OTHER

  Scenario: A leading-edge sub-surface is skipped
    Given SS_Control_1 with LE_Flag 1
    When the post-pass runs
    Then nothing is created
    And an info warning explains that LE devices are out of scope

  Scenario: A duplicate sub-surface on one segment is rejected
    Given two SS_CONTROLs whose midpoints fall in the same segment
    When the post-pass runs
    Then only the first creates a TED
    And a warning records the second
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Wing planform maths (RF-GH-04…RF-GH-11) | Must | This is the product of the import; the gh-755 dihedral defect produced visibly wrong V-tails and winglets |
| Airfoil resolution and its never-raise contract (RF-GH-13/RF-GH-14) | Must | One unrecognised x-section would otherwise abort an entire aircraft |
| Duplicate-point removal (RF-GH-16) | Must | AeroSandbox `repanel()` crashes on duplicates — the failure surfaces far from the cause (gh-789) |
| Handler registration (RF-GH-01) | Must | Nothing is imported without it |
| SS_CONTROL registration and mapping (RF-GH-02/RF-GH-22) | Must | The highest-value defect in the module: the code is written and tested but never runs |
| The approximation warnings (RF-GH-15) | Must | The user is told which numbers are exact and which are not — consistent with ADR 0012 |
| Fuselage derivation (RF-GH-18) | Must | Layout, drag and the slicer all depend on it |
| Fuselage refinement gates (RF-GH-19/RF-GH-20) | Should | The handler schema is a usable fallback; refinement only improves fidelity |
| BLANK → weight items and CG (RF-GH-21) | Should | Mass positions are in scope, but an aircraft imports without them |
| Placement/symmetry/end caps (RF-GH-12) | Should | Affects assembly, not the wing's own shape |
| Airfoil morphing with fallback (RF-GH-17) | Should | Only used by `segment_split`; a raw blend is an acceptable degradation |
| Duplicate-sub-surface rejection (RF-GH-24) | Should | Defensive; VSP files rarely contain overlaps |
| Camber preservation (RF-GH-25) | Should (open) | Issue #791 — a real accuracy defect, quantified at `C_L0` ≈ 0.43 on the DG-101G |
| Geometry validation against VSP totals (BR-OV8) | Should (intended) / Won't (as-built) | gh-647 shipped inert |
| Leading-edge devices, propulsion, inertia, CS-group gains (RF-GH-26) | Won't | Out of scope (ADR 0018) |
| Reproducing `cum_y += span` | Won't | A confirmed defect with a documented visible symptom |
| Reproducing the pre-gh-733 16-series `Camber` read | Won't | A confirmed defect: it always produced a symmetric section |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/converters/openvsp_importer.py` | `_ensure_handlers_loaded`, `_HANDLERS`, `_POST_PASSES`, `_UNSUPPORTED_REASONS` | 🟢 |
| `app/converters/openvsp_wing_handler.py` (1 069 l.) | `_read_section_parm`, `sweep_at_le`, the accumulation loop, `segment_split`, root/terminal x-section construction | 🟢 |
| `app/converters/openvsp_fuselage_handler.py` (477 l.) | FUSELAGE → superellipse x-secs, `_drop_degenerate_fuselages` | 🟢 |
| `app/converters/openvsp_blank_handler.py` (159 l.) | BLANK → `WeightItemWrite`, `_resolve_vehicle_cg` | 🟢 |
| `app/converters/openvsp_custom_handler.py` (155 l.) | CUSTOM geoms | 🟢 |
| `app/converters/openvsp_ss_control.py` (172 l.) | `register`, `_u_to_segment_index`, SS_CONTROL → TED | 🟢 code / 🔴 never wired |
| `app/converters/openvsp_airfoil.py` (1 180 l.) | `import_airfoil_from_xsec`, `naca_4/5/6/16series_name`, `ensure_naca4_dat`, `ensure_naca5_dat`, `_export_selig`, `write_imported_airfoil_dat`, `_dedup_consecutive_points`, `morph_airfoils`, `_raw_blend`, `_NACA_DAT_HALF_POINTS` | 🟢 |
| `app/converters/openvsp_validation.py` (264 l.) | `GeometryMetrics`, `validate_geometry`, `DEFAULT_REL_TOL` | 🟢 code / 🔴 never called |
| `app/services/openvsp_import_service.py` | `_is_x_dominant_fuselage`, `_select_xsec_slice_source`, `_slicer_frame_matches_handler`, the station budget | 🟢 |
