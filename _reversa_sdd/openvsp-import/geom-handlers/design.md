# geom-handlers — Technical Design

> Use-case design, nested under the module [`openvsp-import`](../design.md).
> Focuses on HOW this use case is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.

## Interface

### Registration — `app/converters/openvsp_importer.py` 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `_ensure_handlers_loaded` | `()` | `None` | lazy, once per process; each module in its own `try/except ImportError` (l.287-321) |
| `_HANDLERS` | `dict[str, Callable]` | — | keyed by the canonical UPPERCASE geom token |
| `_POST_PASSES` | `list[Callable]` | — | `(aeroplane, ctx, vsp)`; a raise becomes a `POST_PASS` warning |

Registered: handlers `WING`, `FUSELAGE`, `BLANK`, `CUSTOM`; post-passes
`openvsp_blank_handler._resolve_vehicle_cg`,
`openvsp_fuselage_handler._drop_degenerate_fuselages`.
🟢 Registered (`Q-VI-1`, `Q-VI-2`). Previously not: `openvsp_ss_control.register()`,
`openvsp_validation.validate_geometry`.

### Wing handler — `app/converters/openvsp_wing_handler.py` (1 069 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `_read_section_parm` | `(vsp, geom_id, i, name)` | `float` | `XSec_{i}` → `XSec_{i-1}` → `0.0` (l.109-121) |
| `sweep_at_le` | `(sweep, sweep_location, span, c_root, c_tip)` | `float` | reference-location conversion; identity when `span ≤ 0` |
| `segment_split` | `(…, airfoil_morph_fn)` | sections | uses `morph_airfoils` as the seam |

### Airfoil resolution — `app/converters/openvsp_airfoil.py` (1 180 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `import_airfoil_from_xsec` | `(vsp, xs_id, ctx, …)` | `str` (path/name) | switches on `GetXSecShape`; **never raises** (l.963-1180) |
| `naca_4series_name` / `naca_5series_name` / `naca_6series_name` / `naca_16series_name` | `(parms…)` | `str` | the canonical designation |
| `ensure_naca4_dat` / `ensure_naca5_dat` | `(name)` | `Path` | generate on demand (gh-700 / gh-733) |
| `_export_selig` | `(vsp, xs_id, tag)` | `Path` | verbatim coordinate export |
| `write_imported_airfoil_dat` | `(name, points)` | `Path` | dedup → hash → skip-if-unchanged (l.731-750) |
| `_dedup_consecutive_points` | `(points, tol=1e-9)` | points | the gh-789 ASB `repanel()` guard (l.712) |
| `morph_airfoils` | `(root, tip, frac)` | points | Kulfan/CST fit + blend, `_raw_blend` fallback (l.876-901, gh-796) |

Constant: `_NACA_DAT_HALF_POINTS = 80` (l.41).

### Fuselage / blank / control — 🟢

| Symbol | File | Note |
|---|---|---|
| FUSELAGE handler | `openvsp_fuselage_handler.py` (477 l.) | superellipse x-secs |
| `_drop_degenerate_fuselages` | same | registered post-pass |
| BLANK handler | `openvsp_blank_handler.py` (159 l.) | `WeightItemWrite` records |
| `_resolve_vehicle_cg` | same | registered post-pass |
| CUSTOM handler | `openvsp_custom_handler.py` (155 l.) | |
| `_u_to_segment_index` | `openvsp_ss_control.py` (172 l.) | `clamp(int(u·n_sec)+1, 1, n_sec)` |

Refinement gates live in the service, not the handler:
`_is_x_dominant_fuselage` (l.494-520), `_select_xsec_slice_source` (l.562-575),
`_slicer_frame_matches_handler` (l.543-559), `_MM_TO_M = 0.001` (l.491).

## Main Flow

### F1 — Wing planform derivation 🟢

For a WING geom with `n_sec` sections, section `i ∈ 1..n_sec` describes the
segment **outboard** of `XSec[i-1]`:

```
# station 0 — synthetic root
station[0] = {xyz_le: [0,0,0],
              chord:  XSec_1.Root_Chord   (≤ 0 → warn, use 1.0),
              twist:  0,
              x_sec_type: "root"}

cum_x = cum_y = cum_z = 0
cum_dihedral = cum_twist = 0

for i in 1..n_sec:
    Span, Tip_Chord, Sweep, Sweep_Location, Dihedral, Twist = read XSec_{i}

    if Span <= 0:
        warn(); ctx.mark_lossy(geom_id); continue

    # gh-755 — relative vs absolute
    cum_dihedral = cum_dihedral + Dihedral  if RelativeDihedralFlag else Dihedral
    cum_twist    = cum_twist    + Twist     if RelativeTwistFlag    else Twist

    # sweep is ABSOLUTE per section in VSP (WingGeom.cpp:1111) — no accumulation
    Λ_LE = sweep_at_le(Sweep, Sweep_Location, Span,
                       c_root = prev_chord, c_tip = Tip_Chord)

    cum_x += Span * tan(Λ_LE)
    cum_y += Span * cos(cum_dihedral)      # NOT  += Span
    cum_z += Span * sin(cum_dihedral)

    station[i] = {xyz_le: [cum_x, cum_y, cum_z],
                  chord:  Tip_Chord,
                  twist:  cum_twist,
                  airfoil: import_airfoil_from_xsec(...)}
    prev_chord = Tip_Chord

station[last].x_sec_type = None      # terminal-station rule (wing-design BR-5)
```

The sweep conversion itself:

```
tan(Λ_to) = tan(Λ_from) − (xref_to − xref_from) · (c_root − c_tip) / span
```

i.e. moving the reference station from `Sweep_Location` to the leading edge
(`xref = 0`) adds back the taper-induced sweep difference. It returns `Λ_from`
unchanged when `span ≤ 0`, so the guard is inside the function as well as at the
call site.

Other parm groups: `XForm` (`X/Y/Z_Location`, `X/Y/Z_Rotation`), `Sym`
(`Sym_Planar_Flag` → `wing.symmetric`), `EndCap` (tip caps).

### F2 — Why `cos(dihedral)` and not `span` 🟢

```
pre-gh-755:   cum_y += Span                 # small-angle approximation
post-gh-755:  cum_y += Span * cos(dihedral) # VSP's own rad·cos(angle)
```

Below ~5° the two agree to within a fraction of a percent, which is why the
defect survived: it was invisible on conventional wings and obvious on winglets
and V-tails, whose panels sit at 45–90° (l.985-989).

### F3 — Airfoil resolution, by VSP shape 🟢

```
GetXSecShape(xs_id):

  XS_FOUR_SERIES      → naca_4series_name(Camber, CamberLoc, ThickChord)
                        + ensure_naca4_dat                            (gh-700)
  XS_FOUR_DIGIT_MOD   → same name + "-mod", plain 4-digit .dat
                        (verified on 3.50: no MeanLine_a parm exists)
  XS_FIVE_DIGIT       → naca_5series_name(Camber, CamberLoc, Reflex, ThickChord)
                        + ensure_naca5_dat                            (gh-733)
  XS_FIVE_DIGIT_MOD   → same + "-mod", base 5-digit .dat
  XS_SIX_SERIES       → naca_6series_name(Series, IdealCl, ThickChord, A)
                        a-family mean line + 4-digit thickness  ← APPROXIMATION
                        + info warning
  XS_ONE_SIX_SERIES   → naca_16series_name(IdealCl, ThickChord), a = 1.0
                        same approximation
  XS_FILE_AIRFOIL     → _export_selig verbatim
  XS_CST_AIRFOIL      → info warning + sampled Selig (tag "vsp_imported_cst")
  otherwise           → warning + Selig (tag "vsp_imported_unknown")
                        last resort: ./components/airfoils/naca0012.dat
```

The function has no `raise` on any branch. That is deliberate: an aircraft with
one exotic section must still import, because the user's next action is to
re-assign the airfoil in the UI anyway.

🟡 Before gh-733 the 16-series branch read a `Camber` parm that does not exist on
that curve type, so every 16-series section came in symmetric.

### F4 — Writing a generated `.dat` 🟢

```
write_imported_airfoil_dat(name, points):
    points = _dedup_consecutive_points(points, tol = 1e-9)   # gh-789
    digest = hash(points)
    if existing file has the same digest:  return path       # skip the write
    write Selig format, _NACA_DAT_HALF_POINTS = 80 per surface
```

The dedup exists because AeroSandbox's `repanel()` raises on duplicate adjacent
points, and the crash surfaces during an aerodynamic analysis — far from the
import that caused it (F2 in the benchmark findings).

### F5 — Fuselage derivation and the four refinement gates 🟢

```
handler  →  superellipse x-sections (the always-available baseline)

refine only if ALL of:
  1. x-dominance, judged on the HANDLER positions:
         extent_x ≥ 1.2·extent_y  AND  extent_x ≥ 1.2·extent_z   (l.494-520)
     ── judging on the STEP bbox would fail: a symmetric=True geom's STEP
        contains BOTH halves and therefore looks Y-dominant
  2. station budget:  min(80, max(15, n + 5·(n−1)))              (l.653)
         fed to vsp_anchored_x_stations — VSP stations are mandatory anchors,
         intermediates weighted by shape change                   (gh-732)
  3. slice source = the SURFACE STEP, not the sewn solid          (gh-812)
  4. frame ratio:  0.5 ≤ x_span(refined) / x_span(handler) ≤ 2.0  (gh-803)

else: keep the handler schema
_MM_TO_M = 0.001 converts the slicer's millimetre output           (l.491)
```

Each gate is an independent veto and each has a recorded incident behind it.
Then `_drop_degenerate_fuselages` runs as a post-pass.

### F6 — BLANK → weight items → vehicle CG 🟢

```
BLANK handler   →  ctx.weight_items.append(WeightItemWrite(...))
post-pass       →  _resolve_vehicle_cg(aeroplane, ctx, vsp)
```

Masses are **never scaled** (BR-75), and a scaling run always appends an `info`
warning saying so.

### F7 — SS_CONTROL → TrailingEdgeDevice 🟢 (unreachable)

```
for each SS_Control_{index+1} group on the wing container:

    if LE_Flag ≥ 0.5:          info warning + skip     # LE devices out of scope
    span extent:  EtaStart/EtaEnd   if EtaFlag ≥ 0.5   else UStart/UEnd

    rel_chord_root = 1 − Length_C_Start     # VSP measures from the TE, we from LE
    rel_chord_tip  = 1 − Length_C_End
    deflection_deg = Deflection
    role           = ControlSurfaceRole.OTHER          # the user re-tags in the UI
    symmetric      = wing.symmetric

    seg_idx  = _u_to_segment_index(u_mid, n_sec) = clamp(int(u·n_sec)+1, 1, n_sec)
    xsec_idx = seg_idx − 1                             # the INBOARD station
    if that segment already has a TED:  warn + skip
```

🟢 `register()` is wired (`Q-VI-1`). Previously never called outside the test module, so none of this ran in
production. `ctx.wing_geom_ids` — the geom-id → schema-name map the pass consumes
— is populated regardless, which is what makes the omission so easy to miss.

## Alternative Flows

- **Unknown geom type:** a warning from `_UNSUPPORTED_REASONS` (14 named types)
  or a generic one; the import continues. 🟢
- **Handler module import fails:** that type is simply unregistered; the others
  are unaffected. 🟢
- **`Span ≤ 0`:** warning, `mark_lossy`, section skipped. 🟢
- **`Root_Chord ≤ 0`:** warning, chord defaults to 1.0 m. 🟢
- **Missing section parm:** one-index fallback, then `0.0`. 🟢
- **Unknown airfoil shape:** Selig export, then `naca0012.dat`. 🟢
- **CST fit failure during morphing:** `_raw_blend`. 🟢
- **Any refinement gate fails:** the handler schema is kept, with a warning. 🟢
- **Degenerate fuselage:** dropped by the post-pass. 🟢
- **Second SS_CONTROL on one segment:** warning, skipped. 🟢
- **Leading-edge sub-surface:** info warning, skipped (ADR 0018). 🟢

## Dependencies

- **[`../vsp3-import-pipeline/`](../vsp3-import-pipeline/design.md)** — owns
  loading, canonicalisation, dispatch and the post-pass loop; the handlers are
  callbacks into it and share its `ImportContext`.
- **[`../step-export-and-sewing/`](../step-export-and-sewing/design.md)** —
  supplies the surface STEP that gate 3 selects.
- **`fuselage-design`** — the slicer and the superellipse definition.
- **`wing-design`** — the target schema (`AsbWingSchema`, `WingXSecSchema`,
  `TrailingEdgeDeviceDetailSchema`) and the terminal-station rule the handler
  must satisfy.
- **`mass-and-balance`** — `WeightItemWrite` and the aeroplane CG.
- **`airfoil-catalog`** — the `.dat` files this use case generates land in
  `AIRFOILS_DIR` and are read back by every aerodynamic path.
- **AeroSandbox** — not called here, but `repanel()`'s duplicate-point
  intolerance is why `_dedup_consecutive_points` exists.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Handlers are registered lazily, once per process, each behind its own import guard | `_ensure_handlers_loaded` (l.287-321) | 🟢 |
| A missing parm degrades to `0.0` rather than raising | `_read_section_parm` (l.109-121) | 🟢 |
| The root station is synthesised rather than read | `openvsp_wing_handler.py:902-910` | 🟢 |
| Dihedral is applied trigonometrically | gh-755 (l.985-989) | 🟢 |
| Sweep is absolute per section, matching VSP's model | comment citing `WingGeom.cpp:1111` | 🟢 |
| Airfoil resolution never raises and has a terminal fallback | `openvsp_airfoil.py:963-1180` | 🟢 |
| 6-/16-series fidelity is traded for availability, and disclosed | the info warnings | 🟢 |
| Generated `.dat` writes are content-addressed and skipped when unchanged | l.731-750 | 🟢 |
| Duplicate adjacent points are removed at write time, not at read time | `_dedup_consecutive_points` (gh-789) | 🟢 |
| Fuselage refinement is gated on the handler frame, not the STEP | `_is_x_dominant_fuselage` (l.494-520) | 🟢 |
| Refined output is rejected outside a 0.5–2.0 frame ratio | gh-803 (l.543-559) | 🟢 |
| An imported control surface gets role `OTHER` for the user to re-tag | `openvsp_ss_control.py` | 🟢 |
| The SS_CONTROL and validation modules exist but are never registered 🟢 both are registered (`Q-VI-1`, `Q-VI-2`) | grep: only the test modules call them | 🟡 |

## Internal State

The handlers own no persistent state. They mutate the shared `ImportContext`:

| Field | Written by | Consumed by |
|---|---|---|
| `warnings` | every handler | the response / the frontend banner |
| `lossy_components` | `mark_lossy` on skipped sections | the response |
| `weight_items` | the BLANK handler | `_resolve_vehicle_cg`, persistence |
| `wing_geom_ids` | the WING handler | the SS_CONTROL pass (🟢 wired (`Q-VI-1`)) |
| `fuselage_geom_ids` | the FUSELAGE handler | the STEP-export pass |

Module-level state (`_HANDLERS`, `_POST_PASSES`, `_handlers_loaded`) is
process-global and is the reason `uvicorn --reload` does not pick up changes
here.

## Observability

- Every degradation is an `ImportWarning` naming the component, and the frontend
  renders them in a banner (gh-648). 🟢
- Sections dropped for `Span ≤ 0` are additionally recorded in
  `lossy_components`, so a user can see *which* geom lost fidelity. 🟢
- 🔴 **The two unregistered modules are invisible.** Nothing logs "SS_CONTROL
  handling is not installed"; the absence of control surfaces looks exactly like
  a file that had none. This is the single most damaging observability gap in the
  module.
- 🔴 No counter of how many sections/airfoils fell back, so accuracy erosion
  (e.g. #791's camber loss) is only detectable by comparing polars.

## Risks and Gaps

- 🔴 **SS_CONTROL is never registered** (BR-OV7). Every real import silently
  drops control surfaces while the unit tests pass, because the tests register
  the pass themselves. A re-implementation must wire it **and** keep a test that
  asserts registration from the production entry point, not from the test.
- 🔴 **`validate_geometry` is never called** (BR-OV8). gh-647 shipped inert; the
  intended wiring is documented in its own module docstring.
- 🔴 **Issue #791 — camber is lost**, giving a `C_L0` offset of ≈ 0.43 on the
  DG-101G. Confirmed by cross-validation against a measured polar.
- 🟡 **6-/16-series thickness shapes are not conformal-mapped.** Disclosed by a
  warning, but the resulting section is not the airfoil the user drew.
- 🟡 **The one-index parm fallback can mask a real absence.** `XSec_{i}` missing
  and `XSec_{i-1}` present is indistinguishable from a deliberate inheritance;
  `0.0` for a missing parm is a legal value for several of them.
- 🟡 **Role `OTHER` on every imported control surface** means trim and mixing
  cannot use them until a human re-tags each one — correct, but it makes an
  imported aircraft non-analysable in one respect until edited.
- 🟡 **`_u_to_segment_index` clamps.** A sub-surface spanning the tip resolves to
  the last segment rather than being reported as out of range.
