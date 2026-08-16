# step-export-and-sewing — Technical Design

> Use-case design, nested under the module [`openvsp-import`](../design.md).
> Focuses on HOW this use case is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.

## Interface

### STEP export — `app/services/openvsp_step_export_service.py` (246 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `export_geom_step` | `(vsp, geom_id, aeroplane_uuid, name)` | `Path` | writes `openvsp_imports/<uuid>/<safe_name>.stp` |
| `_set_step_export_length_unit_metres` | `(vsp)` | `None` | sets `STEPSettings.LenUnit = LEN_M` before every export |
| `scale_geom_step` | `(path, factor)` | `Path` | rescales an already-written STEP in place |
| `cleanup_aeroplane_step_files` | `(aeroplane_uuid)` | `None` | best-effort `rmtree` of the per-aeroplane directory |

Constants: `_VSP_USER_SET = 3` (l.36) · `_STEP_SUBDIR = "openvsp_imports"`
(l.41) · `_SAFE_CHAR = re.compile(r"[^A-Za-z0-9._-]+")`,
`_MAX_NAME_LEN = 64` (l.52-53).

### Solid sewing — `app/services/openvsp_solid_sewing_service.py` (337 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| sewing entry point | `(surface_step_path)` | `Path \| None` | `<stem>_solid.stp` on success, `None` on any failure |

Constants: `_SEW_TOLERANCE_TIGHT = 0.001` · `_SEW_TOLERANCE_LOOSE = 0.005`
(l.68-69, both in the STEP's **metre** units) · `_SOLID_SUFFIX = "_solid.stp"`
(l.74).

### Slice-source selection — `app/services/openvsp_import_service.py` 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `_select_xsec_slice_source` | `(surface_path, solid_path)` | `Path` | prefers the **surface** STEP (l.562-575, gh-812) |

## Main Flow

### F1 — Per-geom STEP export 🟢

```
for each geom the handlers accepted:
    safe = _SAFE_CHAR.sub("_", geom_name)[:_MAX_NAME_LEN]
    target = <artifact base>/openvsp_imports/<aeroplane_uuid>/<safe>.stp

    _set_step_export_length_unit_metres(vsp)     # STEPSettings.LenUnit = LEN_M
    vsp.ExportFile(target, SET_USER, EXPORT_STEP)   # SET_USER = 3
```

Two properties matter and are easy to lose in a re-implementation:

1. The unit is **forced on every export**, not once at startup. VSP's export
   settings are global mutable state on the native model, and the model is
   cleared and reloaded per import (BR-OV5).
2. `SET_USER` (`_VSP_USER_SET = 3`) selects which geoms are written. Exporting
   the default set would emit a different, larger collection.

### F2 — Why the export unit is load-bearing 🟢

The unit-detection pass of the import (BR-76) works by *measuring* an exported
STEP and comparing it against the handler-derived span:

```
implied_ratio = (bb.xlen / 1000.0) / handler_span_x
                  ^^^^^^^^^^^^^^^
                  OCC normalises STEP to millimetres on read,
                  which is only meaningful because VSP wrote it in METRES
```

If the export were written in the model's display unit, the ratio would be 1.0
for every file and the whole feet/inches detection would silently no-op. 🟡 The
coupling is not expressed in code — it lives in the ordering of two services.

### F3 — Sewing a surface STEP into a solid 🟢

```
read the surface STEP                       → a set of faces

sew = BRepBuilderAPI_Sewing(_SEW_TOLERANCE_TIGHT = 0.001)   # 1 mm
sew.Add(each face); sew.Perform()
shells = shells of sew.SewedShape()

if not shells:
    sew = BRepBuilderAPI_Sewing(_SEW_TOLERANCE_LOOSE = 0.005)  # 5 mm, the CEILING
    retry once

for each shell:
    solid = make solid from shell
    if BRepCheck says invalid:  ShapeFix_Solid(solid)
    if volume(solid) < 0:       reverse(solid)

merge/compound the solids  →  write <stem>_solid.stp
```

The 5 mm ceiling is a **geometric** bound, not a tuning parameter: above it the
sewer starts matching a nose-cap edge to a tail edge, producing a topologically
closed but physically nonsensical body. 🟢

Failure at any point returns `None`; the caller stores `solid_step_path = NULL`
and the import proceeds (BR-OV30a).

### F4 — Which STEP downstream code reads 🟢

```
                        ┌── surface STEP  ──►  x-section slicing  (gh-812) ✔
export_geom_step ───────┤
                        └── sewn solid    ──►  CAD download / volume  🟢 Q-VI-4 loft fallback
```

`_select_xsec_slice_source` (l.562-575) returns the **surface** path when both
exist. The reason is recorded in gh-812: the sewn solid carries internal seam
faces at sharp fillets, and a cutting plane through such a seam returns several
disjoint wires instead of one closed section — the superellipse fit then either
fails or fits a fragment.

🟢 The download path detects an unusable solid and falls back to a loft from the stored x-secs (`Q-VI-4`). Previously bug **#814**: users could still
download a malformed solid for a fuselage with sharp fillets.

### F5 — Deferred fuselage scaling 🟢

```
import  →  export fuselage STEP (source frame)
        →  slice it, fit superellipses            # slicer stays in the STEP frame
        →  THEN scale the aeroplane (gh-765)
        →  scale_geom_step(stored STEP, factor)   # bring the artefact along
```

This ordering is why `_scale_aeroplane_lengths` deliberately excludes fuselages
(BR-75): scaling them before the slice would put the slicer in a frame that no
longer matches the file it is cutting.

## Alternative Flows

- **`openvsp` or OCC absent:** the whole use case is unreachable — the import
  itself fails earlier with `ImportError` (ADR 0017). 🟢
- **Export fails for one geom:** a warning is recorded; other geoms still
  export. 🟢
- **No shell at either tolerance:** `solid_step_path` stays NULL; the import
  returns 201. 🟢
- **`BRepCheck` reports an invalid solid:** `ShapeFix_Solid` runs; if the fix
  does not help, the result is still written only when a shell exists. 🟡
- **Negative volume:** the solid is reversed rather than discarded. 🟢
- **Multiple solids:** merged, or compounded when a merge is not possible. 🟢
- **Aeroplane deleted:** `cleanup_aeroplane_step_files` removes the directory;
  an IO failure is swallowed. 🟢
- **Aeroplane scaled after export:** `scale_geom_step` rewrites the stored
  file. 🟢

## Dependencies

- **`openvsp` (SWIG)** — `ExportFile`, `STEPSettings`, the native model. Optional
  dependency, probed once (ADR 0017).
- **OCC / `cadquery`** — `BRepBuilderAPI_Sewing`, `ShapeFix_Solid`, `BRepCheck`,
  volume computation and the STEP reader.
- **[`../vsp3-import-pipeline/`](../vsp3-import-pipeline/design.md)** — supplies
  the geom ids and the aeroplane UUID, and owns the ordering constraint in F5.
- **`fuselage-design`** — the slicer that consumes the surface STEP and fits
  superellipses.
- **`cad-generation`** — a *different* artefact tree (`<ARTIFACTS_BASE_DIR>/
  <aeroplane>/<plan>/<execution>/`); `openvsp_imports/` sits beside it, not
  inside it.
- **`aeroplane-core`** — `delete_aeroplane` calls the cleanup.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| The STEP length unit is forced to metres on every export, not configured once | `_set_step_export_length_unit_metres` | 🟢 |
| Export uses VSP's user set (3) rather than the default set | `_VSP_USER_SET = 3` (l.36) | 🟢 |
| Geom names are treated as untrusted filesystem input | `_SAFE_CHAR`, `_MAX_NAME_LEN` (l.52-53) | 🟢 |
| Sewing retries exactly once, at a documented geometric ceiling | `_SEW_TOLERANCE_TIGHT/LOOSE` (l.68-69) | 🟢 |
| A negative-volume solid is reversed instead of rejected | the volume check after `ShapeFix_Solid` | 🟢 |
| Sewing failure is a supported outcome, expressed as a NULL path | the `None` return contract | 🟢 |
| Slicing reads the surface STEP; the solid is for download/volume only | `_select_xsec_slice_source` (gh-812) | 🟢 (the download half 🔴 #814) |
| Fuselage scaling is deferred until after slicing, and the artefact is rescaled separately | `_scale_aeroplane_lengths` + `scale_geom_step` (gh-765) | 🟢 |

## Internal State

Filesystem only. No database row is owned by this use case; the import service
stores `surface_step_path` and `solid_step_path` on the fuselage record it
persists.

```
<artifact base>/openvsp_imports/<aeroplane_uuid>/
├── <geom>.stp            surface export   (always attempted)
├── <geom>_solid.stp      sewn solid       (may be absent)
└── _unitdetect_*/        throwaway, removed in a `finally` by the unit pass
```

## Observability

- Every failure path emits an `ImportWarning` that reaches the frontend banner
  (gh-648). 🟢
- 🔴 There is **no metric** for sewing success rate, no record of which tolerance
  succeeded, and no stored reason when `solid_step_path` is NULL — a user sees
  only that the solid is missing.
- 🟡 The 1 mm/5 mm decision is invisible after the fact: nothing distinguishes a
  body that sewed cleanly from one that needed the loose retry, although the two
  have materially different geometric confidence.

## Risks and Gaps

- 🟢 **Detect the unusable solid, record the state, and fall back to a solid lofted from the stored superellipse x-secs** (`Q-VI-4`, maintainer-answered). The maintainer needs a valid solid for the Creator classes — not for Fusion360 — and must be able to tell when one is defective. Previously bug #814: malformed at sharp fuselage fillets, and
  the CAD download path still consumes it. The x-section path already routes
  around the defect (gh-812); the download path was never migrated.
- 🔴 **No provenance on the sewing tolerance.** A body sewn at 5 mm may have
  merged features that are genuinely 5 mm apart; nothing records that this
  happened.
- 🟡 **The export-unit ↔ unit-detection coupling is implicit.** BR-76's
  measurement is only valid because BR-OV28 forced metres; nothing in either
  module states the dependency, and a change to the export settings would break
  unit detection silently.
- 🟡 **`scale_geom_step` and the schema can drift.** The stored STEP and the
  persisted fuselage x-sections are scaled by two different code paths; nothing
  asserts afterwards that they still agree.
- 🟡 **No size or count bound on exports.** One STEP per geom, with no cap on
  geoms or on file size.
