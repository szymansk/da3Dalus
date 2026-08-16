# openvsp-import — Technical Design

> Module-level design. Focuses on HOW the module is built, derived from the
> legacy code. Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Endpoint contracts in full: see [`contracts.md`](contracts.md).
> Behavioural slices: [`vsp3-import-pipeline/`](vsp3-import-pipeline/),
> [`geom-handlers/`](geom-handlers/),
> [`step-export-and-sewing/`](step-export-and-sewing/).

## Interface

### Optional-dependency shim — `app/converters/openvsp_adapter.py` (97 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `_attempt_import` | `()` | module \| `None` | `importlib.import_module("openvsp")`, memoised |
| `is_available` | `()` | `bool` | `True` when the memoised module is not `None` |
| `get_vsp` | `()` | module | raises `ImportError(_OPENVSP_MISSING_MSG)` naming the three supported install paths |
| `reset_for_tests` | `()` | `None` | l.92-97 — the **only** way to clear the memo |

Module globals `_cached_module`, `_import_attempted`, `_import_error`
(l.53-55). 🟢

### Pipeline skeleton — `app/converters/openvsp_importer.py` (420 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `import_vsp3` | `(path)` | `ImportResult` | l.324-420 — the gh-640 critical sequence |
| `_ensure_handlers_loaded` | `()` | `None` | l.287-321 — lazy, once per process; four `try/except ImportError: pass` blocks |
| `register_handler` / `register_post_pass` | `(token, fn)` / `(fn)` | `None` | populate `_HANDLERS` / `_POST_PASSES` (l.181-182, 284) |
| `_canonicalize_geom_type` | `(display_name)` | `str` | `_DISPLAY_TO_CANONICAL` (l.194-211, 16 entries), else `.upper()` |
| `_read_source_length_unit` | `(vsp, vehicle_id)` | `int \| None` | `FindParm(..., "LengthUnit", "Vehicle_Info")`; `""` means "not found" |
| `ImportWarning` | frozen dataclass, l.84 | — | `component_type`, `component_name`, `reason`, `severity` |
| `ImportContext` | mutable collector, l.98-141 | — | `add_warning`, `mark_lossy`, `weight_items`, `wing_geom_ids`, `fuselage_geom_ids` |
| `ImportResult` | dataclass, l.145 | — | `aeroplane`, `warnings`, `lossy_components`, `weight_items`, `source_length_unit`, `source_scale_to_meters`, `fuselage_geom_ids` |

### Service surface — `app/services/openvsp_import_service.py` (1 150 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `import_openvsp_file` | `(db, path, *, target_span_m=None, scale_factor=None, name=None, source_filename=None, progress_cb=_noop_progress)` | `OpenVspImportResponse` | l.1025-1145 — the top-level orchestrator |
| `is_importer_available` | `()` | `bool` | the endpoint's 503 gate |
| `_detect_source_scale_to_meters` | `(vsp, aeroplane, fuselage_geom_ids, detect_uuid)` | `(unit, factor) \| None` | l.147-201, best-effort, `finally: rmtree` |
| `_snap_to_unit_scale` | `(raw_ratio)` | `(unit, factor) \| None` | l.108-126 — **relative** ±2 % window, nearest match, `None` for metres |
| `_convert_aeroplane_to_metres` | `(aeroplane, factor, weight_items=None)` | `None` | scales **everything incl. fuselages** — unlike `_scale_aeroplane_lengths` |
| `_scale_aeroplane_lengths` | `(aeroplane, factor, weight_items=None)` | `None` | l.254-293 — wings, `xyz_ref`, weight positions only |
| `_resolve_scale_factor` | `(aeroplane, target_span_m, scale_factor)` | `float \| None` | raises `ScaleValidationError` |
| `_compute_max_wing_span` | `(aeroplane)` | `float` | `2·max|y_le|` symmetric, `max|y_le|` otherwise |
| `_persist_aeroplane` | `(db, result, *, name, source_filename, progress_cb, scale_factor)` | `(uuid, name)` | l.804-1020 |
| `_is_x_dominant_fuselage` | `(xsecs)` | `bool` | l.494-520 — `extent_x ≥ 1.2·extent_y` and `≥ 1.2·extent_z` |
| `_select_xsec_slice_source` | `(rel_step, rel_solid)` | `str \| None` | l.562-575 — prefers the **surface** STEP (gh-812) |
| `_slicer_frame_matches_handler` | `(refined, handler)` | `bool` | l.543-559 — `0.5 ≤ ratio ≤ 2.0` (gh-803) |
| `_record_persist_failure` | `(result, *, component_type, component_name, exc)` | `None` | turns any persistence exception into a warning |
| `ScaleValidationError` | `ValueError` subclass | — | 400 (mutex, raised at the endpoint) / 422 (range, raised here) |

### STEP surface 🟢

| Symbol | File | Purpose |
|---|---|---|
| `export_geom_step` | `openvsp_step_export_service.py` | per-geom surface STEP, `LenUnit = LEN_M`, `SET_USER = 3` |
| `scale_geom_step` | `openvsp_step_export_service.py` | rescale a stored STEP **in place**, returns the same relative path |
| `step_storage_dir` | `openvsp_step_export_service.py` | `<ARTIFACTS_BASE_DIR>/openvsp_imports/<aeroplane_uuid>/` |
| `cleanup_aeroplane_step_files` | `openvsp_step_export_service.py` | best-effort delete, called from `aeroplane_service.delete_aeroplane` |
| `sew_imported_geom_to_solid` | `openvsp_solid_sewing_service.py` | two-tolerance sewing ladder → `<stem>_solid.stp` or `None` |

### Airfoil surface — `app/converters/openvsp_airfoil.py` (1 180 l.) 🟢

| Symbol | Purpose |
|---|---|
| `import_airfoil_from_xsec` (l.963-1180) | shape switch, never raises |
| `naca_4series_name` / `naca_5series_name` / `naca_6series_name` / `naca_16series_name` | canonical names from VSP parms |
| `ensure_naca4_dat` (gh-700) / `ensure_naca5_dat` (gh-733) | generate the `.dat` if absent |
| `_export_selig` | dump VSP's own coordinates |
| `write_imported_airfoil_dat` (l.731-750) | dedup + content-hash + conditional write |
| `_dedup_consecutive_points` (tol `1e-9`, l.712) | the gh-789 ASB `repanel()` fix |
| `morph_airfoils` (l.876-901) / `_raw_blend` | Kulfan/CST blend with fallback (gh-796) |

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

Every line is load-bearing:

1. **`_ensure_handlers_loaded`** (l.287-321) imports and registers exactly four
   modules — wing, fuselage, blank, custom — **each inside its own
   `try: … except ImportError: pass`**. 🟡 **A failed handler registration is reported, not swallowed** (`Q-VI-7`, derived from `P-WARN-0`). Previously a broken handler module
   degrades into "every geom of that type is unsupported" with no diagnostic.
   Registered post-passes: `openvsp_blank_handler._resolve_vehicle_cg` and
   `openvsp_fuselage_handler._drop_degenerate_fuselages`.
2. **`ClearVSPModel()`** — the SWIG module owns one native model per process.
3. **`_read_source_length_unit`** does
   `FindParm(vehicle_id, "LengthUnit", "Vehicle_Info")` and treats `""` as "not
   found". OpenVSP prints `Can't Find Parm` to **stderr** but returns an empty
   string rather than raising, so the empty-string check is the only reliable
   test. On OpenVSP 3.50+ both the parm and `SetLengthUnit` are gone — hence the
   `hasattr` guard (l.352-368 and the module docstring). `LEN_UNIT_TO_METERS`
   (l.63-71) maps the legacy enum:
   `0 mm 0.001 · 1 cm 0.01 · 2 m 1.0 · 3 in 0.0254 · 4 ft 0.3048 · 5 yd 0.9144 ·
   6 unitless 1.0`. 🟡 Reported, not assumed (`Q-VI-3`). Previously `LEN_UNITLESS → 1.0` silently treated a unitless legacy
   file as metres.
4. **Dispatch** — `GetGeomTypeName(gid)` → `_canonicalize_geom_type` →
   `_HANDLERS.get(token)`; a miss produces
   `_UNSUPPORTED_REASONS[token]` (or `"not supported in Phase 1"`) plus
   `ctx.mark_lossy(gid)`.
5. **Post-passes** — a post-pass that raises becomes a warning with
   `component_type = "POST_PASS"` rather than a failed import (l.401-410).

**The canonicalisation table** (`_DISPLAY_TO_CANONICAL`, l.194-211, 16 entries):
`Wing→WING`, `Fuselage→FUSELAGE`, `Custom→CUSTOM`, `Pod→POD`, `Stack→STACK`,
`Blank→BLANK`, `Ellipsoid→ELLIPSOID`, `BodyOfRevolution→BOR`, `Human→HUMAN`,
`Propeller→PROP`, `Gear→GEAR`, `Hinge→HINGE`, `Conformal→CONFORMAL`,
`Routing→ROUTING`, `Auxiliary→AUXILIARY`, `Cobra→COBRA`; fallback `.upper()`.
Verified against OpenVSP 3.50.4. 🟢

### F2 — Wing planform derivation 🟢

`_read_section_parm` (`openvsp_wing_handler.py:109-121`) tries group `XSec_{i}`
first, falls back to `XSec_{i-1}`, and returns `0.0` when the parm is absent.

Root x-section:
`{xyz_le: [0,0,0], chord: XSec_1.Root_Chord, twist: 0, x_sec_type: "root"}`;
`Root_Chord ≤ 0` warns and defaults to `1.0 m` (l.902-910).

Per section `i ∈ 1..n_sec` — **each describes the segment outboard of
`XSec[i-1]`** — reading `Span`, `Tip_Chord`, `Sweep`, `Sweep_Location`,
`Dihedral`, `Twist`:

```
Span ≤ 0                → warning + mark_lossy + skip the section

dihedral (gh-755): relative flag → cum_dihedral += Dihedral
                    absolute      → cum_dihedral  = Dihedral
twist    (gh-755): relative flag → cum_twist    += Twist
                    absolute      → cum_twist     = Twist

Λ_LE = sweep_at_le(Sweep, Sweep_Location, Span, c_root=prev_chord, c_tip=Tip_Chord)
       tan(Λ_to) = tan(Λ_from) − (xref_to − xref_from)·(c_root − c_tip)/span
       (returns Λ_from unchanged when span ≤ 0)

cum_x += Span · tan(Λ_LE)
cum_y += Span · cos(cum_dihedral)      ← NOT `+= Span`
cum_z += Span · sin(cum_dihedral)

xsec[i] = {xyz_le: [cum_x, cum_y, cum_z], chord: Tip_Chord,
           twist: cum_twist, x_sec_type: "segment" | None on the last}
```

Three things a re-implementation must get right:

- The **small-angle shortcut `cum_y += span` was the pre-gh-755 bug**, visible
  on winglets and V-tails above ~5° dihedral (l.985-989). It must not return.
- **Sweep is absolute per section** in VSP — no flag, no accumulation (the code
  comment cites `WingGeom.cpp:1111`).
- The last x-section gets `x_sec_type = None` so
  `AsbWingSchema.validate_last_xsec_has_no_segment_details` passes
  (l.994-1005). This module is a **client** of `wing-design`'s BR-5, not its
  owner.

Other parms read: `XForm` group `X/Y/Z_Location`, `X/Y/Z_Rotation`; `Sym` group
`Sym_Planar_Flag` → `wing.symmetric`; `EndCap` group for the tip treatment.

### F3 — Airfoil resolution 🟢

`import_airfoil_from_xsec` switches on `vsp.GetXSecShape(xs_id)` and **never
raises**:

| VSP shape | Result |
|---|---|
| `XS_FOUR_SERIES` | `naca_4series_name(Camber, CamberLoc, ThickChord)` + `ensure_naca4_dat` (gh-700) |
| `XS_FOUR_DIGIT_MOD` | same name + `-mod`; plain 4-digit `.dat` — verified on 3.50 that no `MeanLine_a` parm exists |
| `XS_FIVE_DIGIT` | `naca_5series_name(Camber, CamberLoc, Reflex, ThickChord)` + `ensure_naca5_dat` (gh-733) |
| `XS_FIVE_DIGIT_MOD` | same + `-mod`, base 5-digit `.dat` |
| `XS_SIX_SERIES` | `naca_6series_name(Series, IdealCl, ThickChord, A)`; **a-family mean line + 4-digit thickness approximation**, `info` warning that t/c and design Cl are exact but the thickness shape is not conformal-mapped |
| `XS_ONE_SIX_SERIES` | `naca_16series_name(IdealCl, ThickChord)`, `a = 1.0` mean line, same approximation. The pre-gh-733 code read a **non-existent `Camber` parm**, so 16-series sections were always treated as symmetric |
| `XS_FILE_AIRFOIL` | `_export_selig` verbatim |
| `XS_CST_AIRFOIL` | `info` warning + sampled Selig export (`tag="vsp_imported_cst"`) |
| anything else | warning + Selig export (`tag="vsp_imported_unknown"`); last resort `./components/airfoils/naca0012.dat` |

`_NACA_DAT_HALF_POINTS = 80` (l.41) — a cosine-spaced half surface.
`write_imported_airfoil_dat` (l.731-750) runs
`_dedup_consecutive_points(tol=1e-9)` — the gh-789 fix for AeroSandbox's
`repanel()` duplicate-point crash — then hashes the coordinates and **skips the
write** when the content is unchanged. `morph_airfoils` (l.876-901) fits both
ends with Kulfan/CST, blends, and falls back to `_raw_blend` when the fit fails
(gh-796); it is the `airfoil_morph_fn` seam used by `segment_split`.

### F4 — SS_CONTROL → `TrailingEdgeDevice` 🟢 code read · 🟢 wired (`Q-VI-1`)

Per `SS_Control_{index+1}` group on the wing container:
`LE_Flag ≥ 0.5` → `info` warning and skip (leading-edge devices are out of
scope per ADR 0018); `EtaFlag ≥ 0.5` selects `EtaStart`/`EtaEnd` over
`UStart`/`UEnd`.

```
rel_chord_root = 1 − Length_C_Start      # VSP measures from the TE, we from the LE
rel_chord_tip  = 1 − Length_C_End
deflection_deg = Deflection
role           = ControlSurfaceRole.OTHER      # user re-tags in the UI
symmetric      = wing.symmetric
segment index  = _u_to_segment_index(u_mid, n_sec) = clamp(int(u·n_sec)+1, 1, n_sec)
xsec_idx       = seg_idx − 1                   # attach to the INBOARD x-section
```

A second `SS_CONTROL` landing on the same segment is rejected with a warning —
only the first is imported.

> 🔴 **This flow never runs.** `openvsp_ss_control.register()` is absent from
> `_ensure_handlers_loaded`; the only caller in the repository is
> `app/tests/test_openvsp_ss_control.py:24`, which is why the unit tests pass
> while production imports arrive with no control surfaces.
>
> 🔴 **And wiring it in would not be sufficient.** `_persist_aeroplane` writes
> each wing through `AsbWingGeometryWriteSchema`
> (`app/schemas/aeroplaneschema.py:695-708`, `extra="forbid"`), whose
> `WingXSecGeometryWriteSchema` (l.592-630) exposes only `xyz_le`, `chord`,
> `twist`, `airfoil`, `x_sec_type`, `tip_type` and
> `number_interpolation_points`. There is **no `trailing_edge_device` field**,
> so a TED produced by the post-pass would be dropped at the persistence
> boundary (`openvsp_import_service.py:846-865`). Both must be fixed together.

### F5 — Source-unit detection (gh-808) 🟢

```
fuselages present?            no → return None (import unchanged)
ref  = fuselage with the largest handler X-span
gid  = fuselage_geom_ids inverted by schema name;  handler_span ≤ 1e-6 → None
rel  = export_geom_step(vsp, gid, ref_name, aeroplane_uuid=f"_unitdetect_{path.stem}")
bb   = cq.importers.importStep(ARTIFACTS_BASE_DIR / rel).val().BoundingBox()
metric_span = bb.xlen / 1000.0            # OCC normalises STEP to millimetres
return _snap_to_unit_scale(metric_span / handler_span)

finally: shutil.rmtree(step_storage_dir("_unitdetect_…"))
```

`_snap_to_unit_scale` (l.108-126):

```
not finite or ≤ 0                    → None
for name, factor in _LENGTH_UNIT_FACTORS:      # m 1.0, yd 0.9144, ft 0.3048,
    if |ratio − factor| ≤ 0.02 · factor:       # in 0.0254, cm 0.01, mm 0.001
        keep the NEAREST match
best is None or best is "m"          → None    # metres ⇒ nothing to convert
else                                 → (name, factor)
```

The window is **relative to each factor**, and the factors are ≥3× apart
(nearest pair ft/yd), so ±2 % absorbs slicer and bounding-box noise without ever
aliasing between units. 🟢

On a hit, `_convert_aeroplane_to_metres` scales the **whole** aeroplane — wings,
fuselages, `xyz_ref` and weight-item positions — and a `UNITS` warning of
severity `warning` says *"converted to metres (×f). Verify the scale before
use."* The entire detection is wrapped in `except Exception` and logged at
`info` — 🟢 by design, it must never break an otherwise valid import.

🟡 Detection **requires a fuselage**; a wing-only model is reported (`Q-VI-3`). Today it returns `None`, so a
feet-unit flying wing imports 3.28× too large with no warning at all.

### F6 — Scaling resolution and order 🟢

```
factor = _resolve_scale_factor(aeroplane, target_span_m, scale_factor)
   both supplied            → (rejected earlier at the endpoint → 400)
   out of range             → ScaleValidationError → 422
       SCALE_FACTOR ∈ (0.001, 10.0)  ·  TARGET_SPAN ∈ (0.1, 50.0) m
   target_span_m, no wings  → ScaleValidationError → 422
   target_span_m            → factor = target / _compute_max_wing_span(aeroplane)
       _compute_max_wing_span = 2·max|y_le| (symmetric) else max|y_le|

if factor is not None and |factor − 1.0| > 1e-9:      # S1244 epsilon
    _scale_aeroplane_lengths(aeroplane, factor, weight_items)
    warnings.append(_make_scaling_warning(...))       # ALWAYS: masses not scaled
```

`_scale_aeroplane_lengths` (l.254-293) scales wing `xyz_le` and `chord`,
`aeroplane.xyz_ref`, and weight-item `x_m/y_m/z_m`. It deliberately does **not**
scale twist (angular), masses (ADR 0018), or fuselages.

**The three-stage order is load-bearing** (gh-765):

```
1. unit conversion — WHOLE aeroplane incl. fuselages   (_convert_aeroplane_to_metres)
2. rescale         — wings, xyz_ref, weight positions  (_scale_aeroplane_lengths)
3. fuselage x-secs — LAST, inside _persist_aeroplane, AFTER slicer refinement,
   then the stored STEP files are rescaled with scale_geom_step (gh-769)
```

Stage 3 exists so the slicer keeps working in the **unscaled** OpenVSP/STEP
frame; the scale is applied once, afterwards, to both the schema and the stored
artefact.

### F7 — `_persist_aeroplane` 🟢

```
resolved_name = _resolve_aeroplane_name(explicit_name, source_filename, parsed_name)
aeroplane     = aeroplane_service.create_aeroplane(db, resolved_name)     # pct 20

per wing:                                                                 # pct 25…30
    AsbWingSchema → AsbWingGeometryWriteSchema (geometry ONLY)
    wing_service.create_wing(db, aeroplane.uuid, wing_name, write)
    on exception → _record_persist_failure(component_type="WING")

per fuselage:                                    # pct 30…85, 55 points total
    fuselage_service.create_fuselage(...)         → on exception: warn + continue
    if vsp and gid:
        rel_step  = export_geom_step(...)                       # "fuselage_step"
        if rel_step:
            _set_fuselage_step_path(...)
            rel_solid = sew_imported_geom_to_solid(...)         # "fuselage_sew"
            if rel_solid: _set_fuselage_solid_step_path(...)
            src = _select_xsec_slice_source(rel_step, rel_solid) # "fuselage_slice"
            if src: refined = _try_slicer_refinement(src, fuse, fuse_name)
    scaling = |scale_factor − 1.0| > 1e-9
    if scaling:  _replace_fuselage_xsecs(scale(refined or fuse.x_secs))
    elif refined is not None: _replace_fuselage_xsecs(refined)
    if scaling:  scale_geom_step(rel_step / rel_solid, scale_factor)

per weight item: persist via the mass-properties entry point            # pct 90
```

Notes a re-implementation needs:

- The name precedence is **explicit `name` → uploaded filename stem → parsed
  model name**; without `source_filename` the persisted name would be the
  `NamedTemporaryFile` stem (`tmpXXXX`). Whitespace-only `name` counts as "no
  override". 🟢
- Sewing and slicing are **nested inside a successful surface export** — no
  surface STEP means no solid and no refinement. 🟢
- `scale_geom_step` overwrites in place and returns the same relative path, so
  the DB row already points at the scaled file; the setter is only re-run
  defensively should the path ever relocate. 🟢
- Because wings go through the geometry-only write schema, the persisted wing
  carries `design_model = 'asb'` (`wing-design` BR-8) and
  `wing_xsecs.dihedral = NULL`. 🟡 The dihedral is implicit in the derived
  `xyz_le` for interior stations, but the **terminal rib's** rotation
  (`wing-design` BR-7 / gh-951) is unrecoverable from positions and is therefore
  lost on every import.

### F8 — STEP export and sewing 🟢

**Export** (`openvsp_step_export_service.py`):

```
_VSP_USER_SET   = 3
subdirectory    = openvsp_imports/<aeroplane_uuid>/
filename        = re.sub(r"[^A-Za-z0-9._-]+", …, geom_name)[:_MAX_NAME_LEN = 64]
_set_step_export_length_unit_metres()        # STEPSettings.LenUnit = LEN_M
vsp.ExportFile(target, SET_USER, EXPORT_STEP)
```

**Sewing** (`openvsp_solid_sewing_service.py`):

```
BRepBuilderAPI_Sewing @ _SEW_TOLERANCE_TIGHT = 0.001   # 1 mm in the STEP's metre units
    no shells → retry @ _SEW_TOLERANCE_LOOSE = 0.005   # 5 mm — documented ceiling
                                                       #   before the nose cap would
                                                       #   stitch itself to the tail
ShapeFix_Solid behind a BRepCheck gate
    volume < 0 → reverse
    multiple solids → merge or compound
write <stem>_solid.stp                                  # _SOLID_SUFFIX
failure → return None → solid_step_path stays NULL, import continues
```

### F9 — REST and SSE 🟢

Both routes validate up front — bindings present (503), filename ends `.vsp3`
(400), scaling mutex (400), size ≤ 50 MB (413) — then write the upload to a
`NamedTemporaryFile` and run the blocking import on
`asyncio.to_thread` (Sonar S7493), unlinking the temp file in a `finally`.

The stream endpoint drives an `asyncio.Queue`: `progress_cb(step, pct, detail)`
is called **synchronously from the worker thread** and hops onto the loop with
`loop.call_soon_threadsafe(queue.put_nowait, …)`; the generator drains the queue
until a `_DONE` sentinel, then `await`s the import task in its `finally`.
Full event vocabulary in [`contracts.md`](contracts.md).

## Alternative Flows

- **`openvsp` not installed:** `is_importer_available()` is false → **503**
  before any file is read; an `ImportError` raised later also maps to 503. 🟢
- **Upload is not `.vsp3` / both scale params / > 50 MB:** 400 / 400 / 413,
  each before parsing. 🟢
- **Temp file vanished during import:** `FileNotFoundError` → **500** with
  `"Temp file vanished during import"`. 🟢 (Note the asymmetry: this is the one
  error path that produces a 5xx rather than a warning.)
- **Any other parse failure:** logged with `logger.exception` and translated to
  **422** `"Failed to parse OpenVSP file: …"`. 🟢
- **Unsupported geom type:** warning from `_UNSUPPORTED_REASONS` +
  `mark_lossy`; the import continues. 🟢
- **Handler raises:** warning keyed on the geom type + `mark_lossy`. 🟢
- **Post-pass raises:** warning with `component_type = "POST_PASS"`. 🟢
- **Handler module fails to import:** silently absent from `_HANDLERS`, so every
  geom of that type reports "unsupported". 🟡 **A failed handler registration is reported, not swallowed** (`Q-VI-7`, derived from `P-WARN-0`).
- **Unit detection impossible** (no fuselage, no CadQuery, export or measure
  failure, unmatched ratio): skipped silently, import unchanged. 🟢 — but see
  🟡 **No silent scale — unit resolution follows the declared unit; a wing-only model without one is reported, not guessed** (`Q-VI-3`, derived).
- **Slicer unavailable, or its output rejected by the frame-ratio gate:** the
  handler-built x-secs are retained. 🟢
- **Sewing fails at both tolerances:** `solid_step_path` stays NULL. 🟢
- **A single record fails to persist:** `_record_persist_failure` records it and
  the remaining records still persist. 🟢
- **Client disconnects mid-stream:** the generator's `finally` still awaits the
  import task, so the import completes and the temp file is removed. 🟡 The
  aeroplane is created even though nobody is listening.

## Dependencies

- **`openvsp` (optional, SWIG)** — probed once by `openvsp_adapter`; absent on
  any platform without the wheel. ADR 0017.
- **CadQuery / OCCT (optional)** — needed by `_detect_source_scale_to_meters`
  (bounding box), the solid sewing service and the fuselage slicer. Absent ⇒
  those stages are skipped, not fatal.
- **`aeroplane-core`** — `aeroplane_service.create_aeroplane`; also the caller
  of `cleanup_aeroplane_step_files` on delete.
- **`wing-design`** — `wing_service.create_wing`, `AsbWingGeometryWriteSchema`
  and the BR-5 terminal-station rule the wing handler is written against.
- **`fuselage-design`** — `fuselage_service.create_fuselage` and the slicer
  (`cad_designer/aerosandbox/slicing.py`, `vsp_anchored_x_stations`,
  superellipse fitting) that this module gates and consumes.
- **`airfoil-catalog`** — the `.dat` directory the generated and exported
  airfoils are written into.
- **`mass-and-balance`** — the weight-item write path used for `BLANK` geoms.
- **`cad-generation` / `construction-plans`** — downstream consumers of the STEP
  artefacts (and the victims of #814).
- **`platform-core`** — `settings.ARTIFACTS_BASE_DIR`, `get_db()` transaction
  ownership (ADR 0009), the `NonFiniteSafeJSONResponse` envelope.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Import the airframe, not the aircraft — geometry and mass positions only | ADR 0018; module docstrings; the scaling and warning policy | 🟢 |
| Nothing aborts an import except three exception types; everything else is a warning | `openvsp_importer.py:401-410`; `_record_persist_failure`; gh-648 | 🟢 |
| Measure the source unit instead of trusting the file, because OpenVSP 3.50 stores none | gh-808; `openvsp_import_service.py:147-201` | 🟢 |
| Snap the measured ratio to a known unit with a **relative** ±2 % window rather than accepting any ratio | `_snap_to_unit_scale:108-126` | 🟢 |
| Run the fuselage slicer in the unscaled STEP frame and apply the scale once afterwards | gh-765; `_persist_aeroplane` ordering | 🟢 |
| Slice the **surface** STEP, not the sewn solid | gh-812; `_select_xsec_slice_source:562-575` | 🟢 |
| Gate slicer output on a frame-ratio sanity check instead of trusting it | gh-803; `_slicer_frame_matches_handler:543-559` | 🟢 |
| Decide x-dominance from the **handler** schema, not the STEP bounding box | `_is_x_dominant_fuselage:494-520` (a symmetric geom's STEP looks Y-dominant) | 🟢 |
| Keep the sewn solid even though slicing prefers the surface | `openvsp_solid_sewing_service`; the construction download needs a closed solid | 🟢 |
| Accumulate dihedral with `cos`/`sin` rather than the small-angle shortcut | gh-755; `openvsp_wing_handler.py:985-989` | 🟢 |
| Tag every imported control surface `role = OTHER` and let the user re-tag | `openvsp_ss_control.py` | 🟢 |
| Persist wings through the geometry-only write schema | `_persist_aeroplane:846-865`; `aeroplaneschema.py:695-708` | 🟢 (intent 🔴 — it silently forecloses TED import) |
| Memoise the optional import in module globals with a test-only reset | `openvsp_adapter.py:53-55, 92-97` | 🟢 |
| Register handlers lazily, tolerating individual import failures | `_ensure_handlers_loaded:287-321` | 🟢 (swallowing the error 🔴) |
| Allocate 55 % of the progress range to fuselages with per-stage sub-events | `_persist_aeroplane:895-905` | 🟢 |

## Internal State

The module is **not** stateless between requests, and that is its most
surprising property.

**Process-global, surviving `--reload`:**

- `openvsp_adapter._cached_module` / `_import_attempted` / `_import_error`
  (l.53-55) — cleared only by `reset_for_tests()`.
- `openvsp_importer._handlers_loaded` / `_HANDLERS` / `_POST_PASSES`
  (l.181-182, 284) — populated once per process.
- The `openvsp` SWIG module's **own native VSP model** — the reason
  `ClearVSPModel()` is mandatory before every read, and the reason two
  concurrent imports in one process would corrupt each other. 🟡 There is no
  lock; concurrency safety is not addressed anywhere in the module.

**Per-request:**

- `ImportContext` — warnings, `lossy_components`, `weight_items`,
  `source_length_unit`, `source_scale_to_meters`, `wing_geom_ids`,
  `fuselage_geom_ids`. Discarded once `ImportResult` is built.

**Persistent side effects:** a new `aeroplanes` row with its wings, fuselages
and weight items, plus files under
`<ARTIFACTS_BASE_DIR>/openvsp_imports/<aeroplane_uuid>/` and generated `.dat`
files in the airfoil directory. The throwaway `_unitdetect_*` STEP directory is
always removed.

## Observability

- **Structured warnings are the primary channel.** `ImportWarning` records reach
  the response body and the frontend banner (gh-648) — this module's expression
  of ADR 0012 ("design warnings instead of silent fallbacks"). 🟢
- **SSE progress** (gh-737) — `progress_cb(step, pct, detail)` at
  `parsing 5` → `parsing 15` → `units 16` → `scaling 18` → `aeroplane 20` →
  `wing 25…30` → `fuselage 30…85` (with `fuselage_step`, `fuselage_sew`,
  `fuselage_slice` sub-events) → `weight_items 90` → `finalising 95`. 🟢
- `logger.exception("OpenVSP import failed")` on the 422 catch-all;
  `logger.info(..., exc_info=True)` on best-effort unit detection;
  `logger.warning` when a temp file cannot be removed. 🟢
- 🔴 **No metric, trace or event** distinguishes "imported cleanly" from
  "imported with 40 warnings"; the counts exist only in the response body.
- 🔴 A handler module that fails to import produces **no log line at all**.

## Verification evidence — `scripts/vspaero_benchmark/`

An **offline** cross-validation harness (`run_all.py`, `pipeline_asb.py`,
`pipeline_vspaero.py`, `compare.py`, `build_dashboard.py`, plus `PLAN.md` /
`FINDINGS.md` / `VSPAERO_API.md`) that runs the app's AeroSandbox path and
VSPAERO over the same `.vsp3` models. It is **not** part of the runtime
contract. Note that the PyPI `openvsp` wheel ships **without** VSPAERO binaries;
the README documents symlinking them from a full OpenVSP distribution. 🟢

| Finding | Status today |
|---|---|
| F1 #788 — `s_ref` taken from `wings[0]`, so a tail-first import made every coefficient ≈8× wrong | **fixed** — `model_schema_converters.py:761-817` now picks the largest-planform wing |
| F2 #789 — duplicate adjacent points in a generated `.dat` crash ASB `repanel()` | **fixed** — `_dedup_consecutive_points` |
| F3 #790 — AeroBuildup divide-by-zero on the Stratos boxwing fuselage | issue **closed**; no guard found in the importer |
| F4 #791 — importer loses airfoil camber (C_L0 offset ≈0.43 on DG-101G, only 0.07 on Titan Falcon → geometry-specific) | **open** |
| F5 #792 — x-sec augmentation makes ASB VLM intractable at default resolution (215 s per solve on a 31-xsec Cessna) | **open**; AeroBuildup, the app default, is unaffected |

Validated well: AeroBuildup against the measured DG-101G polar (max L/D ≈ 39 vs
38.3), ASB-VLM against VSPAERO lift slope within 2–3 %, and Titan Falcon V2
C_Lmax ≈ 1.42 against the manufacturer's CFD. 🟢

## Configuration surface

| Constant | Value | Where |
|---|---|---|
| `SCALE_FACTOR_MIN` / `MAX` | `0.001` / `10.0` | `openvsp_import_service.py:78-79` |
| `TARGET_SPAN_MIN` / `MAX` | `0.1` / `50.0` m | `:80-81` |
| `_LENGTH_UNIT_FACTORS` | `m 1.0 · yd 0.9144 · ft 0.3048 · in 0.0254 · cm 0.01 · mm 0.001` | `:94` |
| `_UNIT_SNAP_TOL` | `0.02` (±2 %, **relative to each factor**) | `:105` |
| `_MM_TO_M` | `0.001` | `:491` |
| x-dominance margin | `1.2` | `:520` |
| `_SLICER_FRAME_RATIO_MIN` / `MAX` | `0.5` / `2.0` | `:534-535` |
| station budget | `min(80, max(15, n + 5(n−1)))` | `:653` |
| fuselage progress band | `30 → 85` (`fuselage_span_pct = 55`) | `:895-905` |
| `LEN_UNIT_TO_METERS` | `0 mm … 6 unitless` | `openvsp_importer.py:63-71` |
| `_DISPLAY_TO_CANONICAL` | 16 entries | `openvsp_importer.py:194-211` |
| `_UNSUPPORTED_REASONS` | 14 geom types | `openvsp_importer.py:242-260` |
| `_SEW_TOLERANCE_TIGHT` / `LOOSE` | `0.001` / `0.005` (metres) | `openvsp_solid_sewing_service.py:68-69` |
| `_SOLID_SUFFIX` | `_solid.stp` | `:74` |
| `_VSP_USER_SET` | `3` | `openvsp_step_export_service.py:36` |
| `_STEP_SUBDIR` | `openvsp_imports` | `:41` |
| `_SAFE_CHAR` / `_MAX_NAME_LEN` | `[^A-Za-z0-9._-]+` / `64` | `:52-53` |
| `_NACA_DAT_HALF_POINTS` | `80` | `openvsp_airfoil.py:41` |
| dedup tolerance | `1e-9` | `openvsp_airfoil.py:712` |
| `DEFAULT_REL_TOL` | `0.01` (1 %) | `openvsp_validation.py:39` |
| `_MAX_FILE_SIZE_BYTES` | `50 × 1024 × 1024` → 413 | `openvsp_import.py:50` |
| SSE headers | `X-Accel-Buffering: no`, `Cache-Control: no-cache` | `openvsp_import.py:377-384` |

### OpenVSP parms read, by group 🟢

| Container / group | Parms | Mapped to |
|---|---|---|
| `Vehicle_Info` | `LengthUnit` | advisory only; absent on OpenVSP 3.50+ |
| WING `XSec_{i}` | `Root_Chord`, `Span`, `Tip_Chord`, `Sweep`, `Sweep_Location`, `Dihedral`, `Twist` | x-sec `xyz_le`, `chord`, `twist` |
| WING (geom) | `RelativeDihedralFlag`, `RelativeTwistFlag` | absolute vs. incremental accumulation (gh-755) |
| `XForm` | `X/Y/Z_Location`, `X/Y/Z_Rotation` | geom placement |
| `Sym` | `Sym_Planar_Flag` | `wing.symmetric` |
| `EndCap` | cap flags | tip treatment |
| `SS_Control_{n}` | `LE_Flag`, `EtaFlag`, `EtaStart`, `EtaEnd`, `UStart`, `UEnd`, `Length_C_Start`, `Length_C_End`, `Deflection` | `TrailingEdgeDeviceDetailSchema` (🔴 never reached) |
| XSecCurve | `Camber`, `CamberLoc`, `ThickChord`, `Reflex`, `Series`, `IdealCl`, `A` | NACA name + generated `.dat` |
| `WingGeom` | `TotalSpan`, `TotalProjectedArea`/`TotalArea`, `TotalChord`/`MAC` | validation only (🔴 inert) |
| `Design` | `Length` | fuselage validation only (🟢 wired (`Q-VI-2`)) |

## Risks and Gaps

- 🔴 **The control-surface path is dead twice over.** The SS_CONTROL post-pass
  is never registered, *and* the persistence write schema has no
  `trailing_edge_device` field. Fixing either alone changes nothing. Imported
  aircraft silently arrive with no control surfaces, and the unit tests pass
  because they register the pass themselves.
- 🔴 **`validate_geometry` is shipped, tested and never called.** gh-647 is
  inert; its own docstring shows the intended `result.warnings.extend(...)`
  wiring that does not exist.
- 🔴 **Handler-registration failures are invisible.** `except ImportError: pass`
  turns a broken handler module into "every geom of that type is unsupported"
  with no log line.
- 🔴 **Unit detection requires a fuselage.** A wing-only model (a flying wing —
  a core RC use case) in feet imports 3.28× too large with no warning.
- 🔴 **`LEN_UNITLESS → 1.0`** silently treats a unitless legacy file as metres.
- 🟢 **Detect the unusable solid, record the state, and fall back to a solid lofted from the stored superellipse x-secs** (`Q-VI-4`, maintainer-answered). The maintainer needs a valid solid for the Creator classes — not for Fusion360 — and must be able to tell when one is defective. Previously #814: the sewn solid is malformed at sharp fuselage fillets. The x-sec
  path already routes around it (gh-812), but the CAD construction/download path
  still consumes `solid_step_path`, so a user can download a corrupt solid.
- 🟢 **#791: ship — the camber loss is acceptable at RC/UAV scale; #792 accepted** (`Q-VI-8`, expert consensus endorsed by the maintainer). Previously open, and nothing
  in the response tells a user that an imported aircraft's C_L0 may be off.
- 🟡 **The terminal-rib dihedral is lost on import.** Wings are persisted via
  the geometry-only write schema, so `wing_xsecs.dihedral` is `NULL`; interior
  stations are recoverable from `xyz_le`, but the terminal rotation
  (`wing-design` BR-7, gh-951) is not.
- 🟡 **Concurrency is unaddressed.** The native VSP model, the adapter memo and
  the handler registry are all process-global with no lock; two simultaneous
  imports in one worker would interleave.
- 🟡 **A client that disconnects mid-stream still gets an aeroplane** — the
  generator's `finally` awaits the import task to completion.
- 🟡 **Open epic #638** — B5 (`XS_GENERAL_FUSE` / `XS_FILE_FUSE` /
  `XS_EDIT_CURVE` polyline sampling) and B6 (STEP fallback for
  CUSTOM / CONFORMAL / NGON_MESH) remain unimplemented.
