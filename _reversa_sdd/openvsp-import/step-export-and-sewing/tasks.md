# step-export-and-sewing — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Parent module task list: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] The `openvsp` SWIG module is importable through the memoised adapter
      (`app/converters/openvsp_adapter.py`, ADR 0017).
- [ ] OCC / CadQuery available — `BRepBuilderAPI_Sewing`, `ShapeFix_Solid`,
      `BRepCheck`, `BRepGProp` and a STEP reader/writer.
- [ ] An artefact base directory exists and is writable; this use case writes to
      `<base>/openvsp_imports/<aeroplane_uuid>/`.
- [ ] The import pipeline has already produced geom ids and the aeroplane UUID
      (→ [`../vsp3-import-pipeline/tasks.md`](../vsp3-import-pipeline/tasks.md)).

## Tasks

### STEP export

- [ ] **T-SE-01 — Per-aeroplane artefact directory.**
  `<artifact base>/openvsp_imports/<aeroplane_uuid>/`, created on demand.
  - Legacy origin: `app/services/openvsp_step_export_service.py:41`
    (`_STEP_SUBDIR`)
  - Definition of done: two imports of different aeroplanes never share a
    directory; the directory is created if missing.
  - Confidence: 🟢

- [ ] **T-SE-02 — Filename sanitisation.**
  `_SAFE_CHAR = re.compile(r"[^A-Za-z0-9._-]+")` substitution, then truncate to
  `_MAX_NAME_LEN = 64`.
  - Legacy origin: `openvsp_step_export_service.py:52-53`
  - Definition of done: a geom named `../../wing #1` produces a name matching
    `^[A-Za-z0-9._-]+$`, at most 64 characters, whose resolved path is inside the
    per-aeroplane directory. Cover the traversal case with a test.
  - Confidence: 🟢

- [ ] **T-SE-03 — Force the export length unit to metres.**
  Set `STEPSettings.LenUnit = LEN_M` immediately before **every**
  `vsp.ExportFile(...)`, not once at startup — the native model is cleared and
  reloaded per import.
  - Legacy origin: `openvsp_step_export_service.py`
    (`_set_step_export_length_unit_metres`)
  - Definition of done: a model whose display unit is feet still exports a STEP
    whose bounding box, read back through OCC, matches the metre dimensions.
  - Confidence: 🟢

- [ ] **T-SE-04 — Export from the VSP user set.**
  `vsp.ExportFile(target, SET_USER, EXPORT_STEP)` with `_VSP_USER_SET = 3`.
  - Legacy origin: `openvsp_step_export_service.py:36`
  - Definition of done: only the geoms in set 3 appear in the exported file; a
    test asserts the set constant rather than the literal `3` at the call site.
  - Confidence: 🟢

- [ ] **T-SE-05 — `scale_geom_step`.**
  Rescale an already-written STEP by a factor and rewrite it.
  - Legacy origin: `openvsp_step_export_service.py` (`scale_geom_step`);
    the ordering rationale is gh-765
  - Definition of done: after a scaled import, the stored STEP's bounding box
    matches the persisted fuselage x-section extent within float tolerance.
  - Confidence: 🟢

- [ ] **T-SE-06 — `cleanup_aeroplane_step_files`.**
  Best-effort removal of the per-aeroplane directory, called from
  `aeroplane_service.delete_aeroplane`.
  - Legacy origin: `openvsp_step_export_service.py`;
    `app/services/aeroplane_service.py` (`delete_aeroplane`)
  - Definition of done: deleting an aeroplane removes the directory; with the
    directory made unremovable, the aeroplane delete still succeeds.
  - Confidence: 🟢

### Solid sewing

- [ ] **T-SE-07 — Sew at the tight tolerance.**
  `BRepBuilderAPI_Sewing(_SEW_TOLERANCE_TIGHT = 0.001)`, add every face from the
  surface STEP, `Perform()`, collect shells.
  - Legacy origin: `app/services/openvsp_solid_sewing_service.py:68`
  - Definition of done: a gap-free surface set produces at least one shell at
    0.001; the tolerance is expressed in the STEP's metre units (1 mm).
  - Confidence: 🟢

- [ ] **T-SE-08 — Retry once at the loose tolerance.**
  Only when the tight pass produced **no** shell, retry at
  `_SEW_TOLERANCE_LOOSE = 0.005`. Never go higher.
  - Legacy origin: `openvsp_solid_sewing_service.py:69`
  - Definition of done: a surface set with a 3 mm gap sews on the second
    attempt; a test pins 0.005 as the maximum and documents why (above it the
    nose cap stitches to the tail).
  - Confidence: 🟢

- [ ] **T-SE-09 — Fix and orient.**
  `ShapeFix_Solid` behind a `BRepCheck` gate; reverse the solid when its computed
  volume is negative.
  - Legacy origin: `openvsp_solid_sewing_service.py`
  - Definition of done: an inverted-orientation shell yields a positive-volume
    solid; the fix step is skipped when `BRepCheck` reports a valid solid.
  - Confidence: 🟢

- [ ] **T-SE-10 — Merge or compound multiple solids.**
  A multi-lobe body must yield one output file.
  - Legacy origin: `openvsp_solid_sewing_service.py`
  - Definition of done: a two-lobe surface set produces exactly one
    `<stem>_solid.stp`.
  - Confidence: 🟢

- [ ] **T-SE-11 — Write `<stem>_solid.stp` and return the path.**
  `_SOLID_SUFFIX = "_solid.stp"`.
  - Legacy origin: `openvsp_solid_sewing_service.py:74`
  - Definition of done: the solid sits beside its surface STEP with the exact
    suffix; the returned path is what the import persists.
  - Confidence: 🟢

- [ ] **T-SE-12 — Failure returns `None`, never raises.**
  Any exception, or no shell at either tolerance, yields `None`; the caller
  stores `solid_step_path = NULL` and the import continues.
  - Legacy origin: `openvsp_solid_sewing_service.py`; BR-74 / BR-OV30a
  - Definition of done: with a deliberately unsewable surface set, the import
    returns 201, `solid_step_path` is NULL, and a warning is present.
  - Confidence: 🟢

### Slice-source selection

- [ ] **T-SE-13 — Prefer the surface STEP for slicing.**
  `_select_xsec_slice_source` returns the surface path when both exist.
  - Legacy origin: `app/services/openvsp_import_service.py:562-575` (gh-812)
  - Definition of done: with both files present, the slicer receives the surface
    path; a test documents the reason (seam faces fragment a section cut).
  - Confidence: 🟢

- [ ] **T-SE-14 — 🟢 Detect the unusable solid and loft a fallback from the x-secs** (`Q-VI-4`).
  The CAD download still serves the sewn solid, which is malformed at sharp
  fillets. Either fix the sewing for filleted bodies or serve the surface STEP
  for download too.
  - Legacy origin: open bug #814; `openvsp_import_service.py:562-575` for the
    half that was already fixed
  - Definition of done: a fuselage with sharp fillets downloads a body whose
    volume and closedness are verified, **or** the download contract is
    explicitly changed to a surface STEP and the frontend copy updated.
  - Confidence: 🟢 — decided in the validation interview

### Ordering constraints

- [ ] **T-SE-15 — Export, slice, then scale.**
  Fuselage STEP export and slicing happen in the **source** frame; the aeroplane
  is scaled afterwards, and `scale_geom_step` brings the artefact along.
  - Legacy origin: gh-765; `openvsp_import_service.py:254-293`
    (`_scale_aeroplane_lengths` deliberately excludes fuselages)
  - Definition of done: a scaled import produces fuselage x-sections and a STEP
    that agree; reordering the steps in a test reproduces the frame mismatch and
    fails.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-SE-01** — Happy path: a clean fuselage exports a metric STEP and sews
      into a positive-volume solid (see `requirements.md`, Acceptance Criteria).
- [ ] **TT-SE-02** — Failure path: an unsewable surface set leaves
      `solid_step_path` NULL and does not fail the import.
- [ ] **TT-SE-03** — Retry path: a 3 mm gap sews only at the loose tolerance, and
      0.005 is asserted as the ceiling.
- [ ] **TT-SE-04** — Security: a geom named `../../wing #1` cannot escape the
      per-aeroplane directory.
- [ ] **TT-SE-05** — Unit: a feet-authored model exports a STEP whose measured
      bounding box is metric (this is what makes BR-76 detection work).
- [ ] **TT-SE-06** — Orientation: a negative-volume shell is reversed.
- [ ] **TT-SE-07** — Source selection: with both files present the slicer gets
      the surface STEP.
- [ ] **TT-SE-08** — Cleanup: an unremovable directory does not block an
      aeroplane delete.
- [ ] **TT-SE-09** — Ordering: scaling before slicing is caught by an assertion
      on the frame ratio.

## Suggested Order

1. **T-SE-01 → T-SE-04** first: nothing can be sewn before a correctly united
   STEP exists, and the unit forcing (T-SE-03) is what the import's unit
   detection depends on.
2. **T-SE-07 → T-SE-12** next, in order — the tight pass, then the retry, then
   fix/orient, then the merge, then the failure contract. Write T-SE-12's test
   before T-SE-07 so the never-raise contract is pinned from the start.
3. **T-SE-13** can be done any time after export exists; **T-SE-15** must be
   verified once both slicing and scaling are in place.
4. **T-SE-05 / T-SE-06** are independent housekeeping.
5. **T-SE-14** is blocked on a human decision and must not be guessed.

## Resolved by the validation interview (🟢/🟡)

- **Bug #814 — which body does the CAD download serve?** The sewn solid is
  malformed at sharp fillets. The x-section path already avoids it; the download
  path does not. Fixing the sewing and changing the download contract are
  different products, and the choice is not derivable from the code.
- **No provenance on which sewing tolerance succeeded.** A body sewn at 5 mm has
  materially lower geometric confidence than one sewn at 1 mm, and nothing
  records the difference. Should the loose retry emit a warning?
- **No sewing success metric.** There is no counter, no reason string when
  `solid_step_path` is NULL, and therefore no way to know how often this fails in
  practice.
- **The export-unit ↔ unit-detection coupling is undocumented in code.** BR-76's
  measurement is only valid because BR-OV28 forces metres. Should this be
  asserted at runtime rather than relied upon?
