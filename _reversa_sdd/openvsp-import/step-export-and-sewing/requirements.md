# step-export-and-sewing

> Use-case specification, nested under the module [`openvsp-import`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: openvsp-import
> (STEP export and sewing, Fuselage refinement gates),
> `_reversa_sdd/data-dictionary.md` §Module: openvsp-import (OpenVSP constants),
> `_reversa_sdd/domain.md` §2.11 (BR-77).

## Overview

`step-export-and-sewing` is the artefact half of an OpenVSP import: it writes one
**metric** STEP file per imported geom under a sanitised per-aeroplane directory,
then tries to sew each fuselage surface STEP into a **closed solid** so the CAD
download and the volume/mass consumers have a watertight body. Both halves are
best-effort — a failed export or a failed sew degrades to a warning and a NULL
path, never to a failed import. 🟢

## Responsibilities

- Export each geom to STEP from VSP's user set, with the export length unit
  forced to metres. 🟢
- Place artefacts in a per-aeroplane subdirectory with sanitised, length-capped
  filenames. 🟢
- Rescale an already-stored STEP when the aeroplane is scaled after export. 🟢
- Sew a surface STEP into a closed solid at a tight tolerance, retrying once at a
  loose tolerance, and fix/orient the result. 🟢
- Choose which STEP a downstream consumer slices — the surface, not the solid. 🟢
- Delete an aeroplane's STEP artefacts when the aeroplane is deleted. 🟢

**Explicitly NOT this use case's responsibility:** parsing the `.vsp3`
(→ [`../vsp3-import-pipeline/`](../vsp3-import-pipeline/requirements.md)), the
geom → schema handlers (→ [`../geom-handlers/`](../geom-handlers/requirements.md)),
the superellipse fitting the slicer performs (→ `fuselage-design`), and the
artefact directories used by construction-plan executions, which are a different
tree owned by `cad-generation`.

## Business Rules

> **ID provenance.** `BR-73`–`BR-77` and `BR-OV1`–`BR-OV19` are inherited
> verbatim from [`../requirements.md`](../requirements.md). Ids from `BR-OV20`
> upward are **defined here**: they extend the module's numbering for behaviour
> only this use case covers, and are not (yet) restated at module level.

- **BR-OV28 — Exported STEP is always metric.** 🟢
  `_set_step_export_length_unit_metres` sets `STEPSettings.LenUnit = LEN_M`
  **before** `vsp.ExportFile(target, SET_USER, EXPORT_STEP)`, with
  `_VSP_USER_SET = 3` (`app/services/openvsp_step_export_service.py:36`). VSP
  would otherwise write the file in the model's own display unit, and every
  downstream measurement (unit detection, slicing, volume) would inherit that
  error.
- **BR-OV29 — Artefact filenames are sanitised and truncated.** 🟢
  Subdirectory `openvsp_imports/<aeroplane_uuid>/` (`_STEP_SUBDIR`, l.41); names
  filtered through `_SAFE_CHAR = re.compile(r"[^A-Za-z0-9._-]+")` and truncated
  to `_MAX_NAME_LEN = 64` (l.52-53). Geom names come from a user-authored file
  and are therefore untrusted input on a filesystem path.
- **BR-OV30 — Sewing is a two-tolerance attempt with a hard ceiling.** 🟢
  `BRepBuilderAPI_Sewing` at `_SEW_TOLERANCE_TIGHT = 0.001`; if the result
  contains no shell, retry once at `_SEW_TOLERANCE_LOOSE = 0.005`
  (`app/services/openvsp_solid_sewing_service.py:68-69`). Both values are in the
  STEP's **metre** units, i.e. 1 mm and 5 mm. 5 mm is documented as the ceiling:
  above it a nose cap would stitch itself to the tail. Then `ShapeFix_Solid`
  behind a `BRepCheck` gate, **reversing** the solid when the computed volume is
  negative, merging or compounding multiple solids, and writing
  `<stem>_solid.stp` (`_SOLID_SUFFIX`, l.74).
- **BR-OV30a — A failed sew is a supported outcome.** 🟢 The import leaves
  `solid_step_path` NULL and continues; nothing raises.
- **BR-77 — Slice the surface STEP, not the sewn solid (gh-812).** 🟢
  `_select_xsec_slice_source` (`openvsp_import_service.py:562-575`) prefers the
  surface STEP: the sewn solid carries internal seam faces at sharp fillets, and
  a section plane through one of them fragments the cut into disjoint wires.
  🟢 **Detect the unusable solid, record the state, and fall back to a solid lofted from the stored superellipse x-secs** (`Q-VI-4`, maintainer-answered). The maintainer needs a valid solid for the Creator classes — not for Fusion360 — and must be able to tell when one is defective. Previously the CAD **download** path consumed the malformed solid, so
  the malformed body is still reachable by users.
- **BR-OV31 — STEP files are cleaned up with the aeroplane.** 🟢
  `cleanup_aeroplane_step_files` is a best-effort delete called from
  `aeroplane_service.delete_aeroplane`; a failure must not fail the delete.
- **BR-OV31a — A stored STEP can be rescaled in place.** 🟢 `scale_geom_step`
  rescales an already-written file, which is what makes the deferred fuselage
  scaling of BR-75 possible: the fuselage STEP is exported in the source frame,
  sliced there, and only then brought to the target scale.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-SE-01 | Export one STEP per imported geom | Must | Each WING and FUSELAGE geom yields a file under `openvsp_imports/<uuid>/` |
| RF-SE-02 | Force the STEP length unit to metres before export | Must | `STEPSettings.LenUnit` is set to `LEN_M` prior to every `ExportFile` call |
| RF-SE-03 | Export from the VSP user set | Must | `ExportFile` is called with set `_VSP_USER_SET = 3` |
| RF-SE-04 | Sanitise and cap artefact filenames | Must | A geom named `../wing #1` produces a name matching `[A-Za-z0-9._-]+` of at most 64 characters and stays inside the subdirectory |
| RF-SE-05 | Sew a surface STEP into a closed solid at 1 mm | Must | A clean surface set yields `<stem>_solid.stp` |
| RF-SE-06 | Retry sewing once at 5 mm when no shell results | Must | A surface set with sub-5 mm gaps sews on the second attempt; the tolerance never exceeds 0.005 |
| RF-SE-07 | Fix and orient the sewn solid | Must | `ShapeFix_Solid` runs behind a `BRepCheck` gate; a negative volume is reversed |
| RF-SE-08 | Merge or compound multiple resulting solids | Should | A multi-lobe body yields one file rather than several |
| RF-SE-09 | Leave `solid_step_path` NULL on failure and continue | Must | An unsewable surface set does not raise and does not fail the import |
| RF-SE-10 | Prefer the surface STEP as the slicing source | Must | `_select_xsec_slice_source` returns the surface path when both exist |
| RF-SE-11 | Rescale a stored STEP after the fact | Should | `scale_geom_step` on a written file produces geometry at the requested scale |
| RF-SE-12 | Delete an aeroplane's STEP directory with the aeroplane | Should | `DELETE /aeroplanes/{id}` removes `openvsp_imports/<uuid>/`; an IO error is swallowed |
| RF-SE-13 | Serve a watertight solid to the CAD download path | Should | 🔴 Not met today — bug #814: the solid is malformed at sharp fillets and the download path consumes it anyway |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | The export unit is forced rather than inherited, so downstream measurement is frame-independent | `openvsp_step_export_service.py` (`_set_step_export_length_unit_metres`) | 🟢 |
| Correctness | Sewing tolerance has a documented upper bound derived from the geometry, not from convenience | `openvsp_solid_sewing_service.py:68-69` | 🟢 |
| Correctness | A negative-volume solid is reversed rather than shipped | `openvsp_solid_sewing_service.py` (`ShapeFix_Solid` + volume check) | 🟢 |
| Security | Geom names are untrusted user input on a filesystem path and are filtered and truncated | `openvsp_step_export_service.py:52-53` | 🟢 |
| Availability | Every step is best-effort; the import completes with partial artefacts | `openvsp_solid_sewing_service.py`; BR-74 | 🟢 |
| Availability | Artefact cleanup failure never blocks an aeroplane delete | `cleanup_aeroplane_step_files` | 🟢 |
| Portability | The whole use case is inert without the `openvsp` module and OCC; both are optional dependencies | ADR 0017 | 🟢 |

## Acceptance Criteria

```gherkin
Feature: STEP export

  Scenario: A geom is exported in metres
    Given an imported FUSELAGE geom
    When the STEP is exported
    Then STEPSettings.LenUnit was set to LEN_M before ExportFile
    And the file exists under openvsp_imports/<aeroplane_uuid>/

  Scenario: A hostile geom name is sanitised
    Given a geom named "../../wing #1"
    When the STEP is exported
    Then the filename contains only characters from [A-Za-z0-9._-]
    And its length is at most 64 characters
    And the resolved path is inside openvsp_imports/<aeroplane_uuid>/

Feature: Solid sewing

  Scenario: A clean surface set sews at the tight tolerance
    Given a fuselage surface STEP with no gaps
    When sewing runs
    Then BRepBuilderAPI_Sewing is used with tolerance 0.001
    And <stem>_solid.stp is written
    And its volume is positive

  Scenario: A gapped surface set sews on retry
    Given a surface set whose largest gap is 3 mm
    When sewing at 0.001 produces no shell
    Then sewing is retried once at 0.005
    And the solid is produced

  Scenario: A negative-volume solid is reversed
    Given a sewn solid whose computed volume is negative
    When the fix step runs
    Then the solid is reversed
    And the stored volume is positive

  Scenario: An unsewable body does not fail the import
    Given a surface set that produces no shell at either tolerance
    When sewing runs
    Then no exception propagates
    And solid_step_path is NULL
    And the import response is still 201

Feature: Slice source selection

  Scenario: The surface STEP wins over the solid
    Given both a surface STEP and a sewn solid exist for a fuselage
    When the slicing source is selected
    Then the surface STEP is returned
    # gh-812: seam faces in the solid fragment a section cut at sharp fillets

Feature: Cleanup

  Scenario: Deleting an aeroplane removes its STEP artefacts
    Given an imported aeroplane with STEP files
    When the aeroplane is deleted
    Then openvsp_imports/<uuid>/ no longer exists

  Scenario: A cleanup failure does not block the delete
    Given the STEP directory cannot be removed
    When the aeroplane is deleted
    Then the delete still succeeds
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Metric STEP export (RF-SE-01/RF-SE-02/RF-SE-03) | Must | The unit-detection pass, the slicer and the CAD download all measure these files; a wrong unit is silent and global |
| Filename sanitisation (RF-SE-04) | Must | The only filesystem guard on user-authored geom names in this module |
| Sewing at the two documented tolerances (RF-SE-05/RF-SE-06/RF-SE-07) | Must | The solid is the only watertight body the import produces; the tolerance ceiling is a geometric constraint, not a tuning knob |
| Best-effort failure with a NULL path (RF-SE-09) | Must | Consistent with BR-74 — sewing is the most fragile step in the module |
| Surface-STEP slicing preference (RF-SE-10) | Must | gh-812; without it fuselage x-sections fragment at fillets |
| Multi-solid merge (RF-SE-08) | Should | Cosmetic for single-lobe bodies, necessary for multi-lobe ones |
| Post-hoc rescale (RF-SE-11) | Should | The enabling mechanism for deferred fuselage scaling (BR-75) |
| Artefact cleanup (RF-SE-12) | Should | Housekeeping; orphaned files are wasteful but harmless |
| A watertight solid for the download path (RF-SE-13) | Should (open) | Bug #814 — the x-section path already routes around the defect; the download path does not |
| Raising the loose tolerance above 5 mm | Won't | Documented ceiling: the nose cap would stitch to the tail |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/openvsp_step_export_service.py` (246 l.) | `export_geom_step`, `_set_step_export_length_unit_metres`, `scale_geom_step`, `cleanup_aeroplane_step_files`, `_VSP_USER_SET`, `_STEP_SUBDIR`, `_SAFE_CHAR`, `_MAX_NAME_LEN` | 🟢 |
| `app/services/openvsp_solid_sewing_service.py` (337 l.) | the sewing pipeline, `_SEW_TOLERANCE_TIGHT`, `_SEW_TOLERANCE_LOOSE`, `_SOLID_SUFFIX` | 🟢 |
| `app/services/openvsp_import_service.py` | `_select_xsec_slice_source` (l.562-575), the deferred fuselage scaling (l.254-293) | 🟢 |
| `app/services/aeroplane_service.py` | `delete_aeroplane` → `cleanup_aeroplane_step_files` | 🟢 |
