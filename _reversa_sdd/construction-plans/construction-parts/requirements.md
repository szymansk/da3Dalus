# construction-parts

> Use-case specification, nested under the module [`construction-plans`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: construction-plans
> (Construction parts, REST surface), `_reversa_sdd/data-dictionary.md`
> §Table `construction_parts` and §Construction constants,
> `_reversa_sdd/domain.md` §2.10 (BR-72),
> `_reversa_sdd/state-machines.md` §12.

## Overview

A **construction part** is an uploaded STEP or STL file scoped to one aeroplane —
a bought or hand-modelled component (a motor mount, a servo horn, a printed
bracket) that the builder wants to carry alongside the parametric aircraft. The
use case owns the upload, its 50 MB and extension limits, geometry extraction
from STEP, a `locked` flag that blocks deletion, the material link into the
component catalogue, and download in either format. It is **unrelated to a
construction plan** despite living in the same module: nothing here decodes a
`$TYPE` tree or runs a Creator. 🟢

## Responsibilities

- Accept a STEP or STL upload of at most 50 MB, scoped to an aeroplane. 🟢
- Store the file under a per-aeroplane directory with a collision-proof name. 🟢
- Extract volume, area and bounding box from STEP uploads; return nulls for
  STL. 🟢
- List, read, rename, re-material and delete parts, always aeroplane-scoped. 🟢
- Lock and unlock a part; a locked part cannot be deleted. 🟢
- Serve the stored file as `step` or `stl`, regenerating STL from STEP on
  demand. 🟢
- Link a part to a component-catalogue material row. 🟢

**Explicitly NOT this use case's responsibility:** construction plans, templates
and their execution (→ [`../plan-execution/`](../plan-execution/requirements.md),
[`../plan-template-lifecycle/`](../plan-template-lifecycle/requirements.md)); the
artefact filesystem used by executions, which is a different tree
(→ `cad-generation`); the component tree that may reference a part
(→ `aeroplane-core`); the component catalogue that owns materials
(→ `powertrain`).

## Business Rules

> IDs are inherited verbatim from [`../requirements.md`](../requirements.md)
> where they exist at module level; use-case-local rules carry a `CP-` prefix.

- **BR-72 — Upload limits.** 🟢 `ALLOWED_SUFFIXES = {".step", ".stp", ".stl"}`,
  `MAX_FILE_SIZE_BYTES = 50 × 1024 × 1024`,
  `ALLOWED_DOWNLOAD_FORMATS = {"step", "stl"}`,
  `STORAGE_ROOT = Path("tmp") / "construction_parts"`
  (`app/services/construction_part_service.py:38-41`). A `locked` part cannot be
  deleted (409). STL yields **no** geometry metadata — it is a triangle soup, a
  documented MVP limitation.
- **BR-CP1 — Upload is two-phase, row first.** 🟢 Insert the row, `db.flush()` to
  obtain the id, then write the file to
  `tmp/construction_parts/{aeroplane_id}/{part_id}_{uuid4hex8}{ext}` and extract
  geometry. The part id is therefore part of the filename, and the `uuid4[:8]`
  suffix prevents collisions on re-upload.
- **BR-CP2 — Geometry extraction is STEP-only and individually guarded.** 🟢
  `_extract_geometry` (l.144-198) returns **all-`None`** when `cad_available()`
  is false **or** the format is not STEP. For STEP it reads `Volume()`, `Area()`
  and `BoundingBox()` with each call wrapped separately, so one failing measure
  does not lose the others.
- **BR-CP3 — Every read is aeroplane-scoped.** 🟢 `_get_part_or_404`
  (l.44-60) filters on both the part id **and** the aeroplane id, so a part id
  belonging to another aeroplane cannot be reached by guessing. There is no
  cross-aeroplane read path.
- **BR-CP4 — A locked part cannot be deleted.** 🟢 `delete_part` raises
  `ConflictError` → **409** when `locked` is set. Lock/unlock are their own
  routes; the flag does not restrict renames, re-materialling or tree moves.
- **BR-CP5 — The file is unlinked before the transaction commits.** 🟢
  `delete_part` unlinks the file **before** `get_db()` commits, and the trade-off
  is spelled out in a comment (l.336-339): a rollback after the unlink leaves a
  row pointing at a missing file, which was judged better than an orphaned file
  with no row. 🟡 The failure mode is therefore a dangling `file_path`.
- **BR-CP6 — Oversize is a `ConflictError` carrying a marker.** 🟢
  `ConflictError(details={"reason": "file_too_large"})` (l.119-124); the endpoint
  inspects that marker and maps it to **413** rather than the default 409.
- **BR-CP7 — 🟢 **The regenerated STL is cached next to its STEP under `ARTIFACTS_BASE_DIR`** (`R2-01`), so it is a derived artefact rather than a transient view and `Q-CP-9 ②`'s containment helper covers it. The leak disappears by construction — nothing writes to `tempfile.mkstemp` any more. The cache is invalidated with its STEP, and the mesh parameters are part of its identity. Previously downloading `stl` for a
  STEP-stored part writes to a `tempfile.mkstemp` file that is returned to the
  client and **never cleaned up** (l.276-280).
- **BR-CP8 — 🟢 Part files move under `ARTIFACTS_BASE_DIR` and use the same containment helper as every other artefact (`Q-CP-9 ②`, maintainer-answered). The primary reason is operational, not security: `STORAGE_ROOT = Path("tmp")/"construction_parts"` is CWD-relative while `ARTIFACTS_BASE_DIR` is absolute and `.resolve()`d. Previously: Files land under the
  CWD-relative `tmp/construction_parts/`, **not** under `ARTIFACTS_BASE_DIR`.
  They therefore do not inherit `artifact_service`'s traversal and symlink
  guards, and are not covered by artefact cleanup.
- **BR-CP9 — `aeroplane_id` is a plain indexed string with no foreign key.** 🟢
  Deleting an aeroplane does **not** cascade to its parts (the same pattern as
  `component_tree.aeroplane_id`). 🔴 Orphan rows and orphan files accumulate.
- **BR-CP10 — The material link is not type-checked.** 🟢
  `material_component_id` is an FK to `components.id` with **no** constraint that
  the target's `component_type` is `material`; the frontend filters the dropdown
  instead.
- **BR-CP11 — File and geometry are immutable after upload.** 🟢
  `ConstructionPartUpdate` carries only `name`, `material_component_id` and
  `thumbnail_url`. There is no re-upload route — a changed file means a new part.
- **BR-CP12 — A part is a leaf a tree node may point at.** 🟢
  `component_tree.construction_part_id` (FK → `construction_parts.id`,
  migration `7cc3eaf27d6b_…`) links a tree node to one part. 🔴 Nothing prevents
  deleting a part that a tree node still references (`locked` is advisory and
  user-driven, not a referential guard).
- **BR-CP13 — There is no lifecycle beyond `locked`.** 🟢 Recorded explicitly in
  `state-machines.md` §12 as an entity that deliberately has no state machine:
  one boolean that blocks deletion, no workflow, no status.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-CP-01 | Upload a part file scoped to an aeroplane | Must | `POST /aeroplanes/{id}/construction-parts` → 201 with a `ConstructionPartRead` |
| RF-CP-02 | Reject an extension outside `.step`/`.stp`/`.stl` | Must | A `.obj` upload is rejected before any file is written |
| RF-CP-03 | Reject an upload over 50 MB with 413 | Must | A 51 MB file → 413; the response carries the `file_too_large` reason |
| RF-CP-04 | Store the file at `{aeroplane_id}/{part_id}_{uuid8}{ext}` | Must | Two uploads of the same filename produce two distinct paths |
| RF-CP-05 | Extract volume, area and bounding box from a STEP | Must | A STEP upload returns non-null `volume_mm3`, `area_mm2` and the three bbox fields |
| RF-CP-06 | Return null geometry for STL | Must | An STL upload stores the file and returns all-null geometry, with no error |
| RF-CP-07 | Return null geometry when the CAD kernel is unavailable | Must | With `cad_available()` false, a STEP upload still succeeds with null geometry |
| RF-CP-08 | Survive a single failing measurement | Should | If `Area()` raises, `volume_mm3` and the bbox are still populated |
| RF-CP-09 | List an aeroplane's parts with a total | Must | `GET /aeroplanes/{id}/construction-parts` → `{aeroplane_id, items, total}` |
| RF-CP-10 | Read one part, aeroplane-scoped | Must | A part id from another aeroplane → 404, not 200 |
| RF-CP-11 | Update name, material and thumbnail only | Must | A patch attempting to change `file_path` or geometry is rejected or ignored |
| RF-CP-12 | Lock and unlock a part | Must | `PUT .../lock` sets `locked = true`; `PUT .../unlock` clears it |
| RF-CP-13 | Refuse to delete a locked part | Must | `DELETE` on a locked part → 409 |
| RF-CP-14 | Delete an unlocked part and its file | Must | The row is gone and the file is unlinked |
| RF-CP-15 | Download the stored file as `step` or `stl` | Must | `GET .../{part_id}/file?format=step` streams the STEP; an unsupported format is rejected |
| RF-CP-16 | Regenerate **and cache** STL from a stored STEP | **Must** | 🟢 (`R2-01`) `format=stl` on a STEP part returns a valid STL (🔴 the temp file is never cleaned up) |
| RF-CP-17 | Link a part to a material component | Should | `material_component_id` round-trips; a non-material component is accepted (🔴 not type-checked) |
| RF-CP-18 | Cascade part deletion when the aeroplane is deleted | Should | 🟡 Not met — `aeroplane_id` has no foreign key, so rows and files are orphaned |
| RF-CP-19 | Prevent deleting a part a tree node references | Could | 🟡 Not met — only the user-driven `locked` flag stands in the way |
| RF-CP-20 | Guard part paths the way artefact paths are guarded | Should | 🟡 Not met — parts live outside `ARTIFACTS_BASE_DIR` and its traversal/symlink guards |
| RF-CP-21 | Re-upload a file to an existing part | Won't | No route exists; a changed file means a new part (BR-CP11 — 🟢 routed through the CAD process pool, `Q-CP-1`) |
| RF-CP-22 | Extract geometry from STL | Won't | A triangle soup carries no exact volume or area; documented MVP limitation |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Security | A part is only reachable through its own aeroplane | `_get_part_or_404` (l.44-60) | 🟢 |
| Security | Uploads are bounded by extension and by size before any processing | `ALLOWED_SUFFIXES`, `MAX_FILE_SIZE_BYTES` (l.38-39) | 🟢 |
| Security | 🟡 Part files are not covered by the artefact traversal/symlink guards | `STORAGE_ROOT = tmp/construction_parts` (l.41) vs `artifact_service._ensure_within_base` | 🟡 |
| Robustness | Each geometry measurement is guarded separately | `_extract_geometry` (l.144-198) | 🟢 |
| Robustness | A missing CAD kernel degrades to null geometry rather than a failed upload | `cad_available()` gate (ADR 0017) | 🟢 |
| Correctness | The stored filename embeds the row id plus 8 random hex chars, so it cannot collide | BR-CP1 | 🟢 |
| Consistency | The file is removed before the commit, so a rollback can leave a dangling path | comment at l.336-339 | 🟢 (the trade-off) / 🟡 (the impact) |
| Resource | 🟡 STL regeneration leaks one temp file per download | l.276-280 | 🟡 |
| Resource | 🟡 Deleting an aeroplane orphans its part rows and files | no FK on `aeroplane_id` | 🟡 |
| Portability | Storage is CWD-relative, so the working directory is part of the deployment contract | `STORAGE_ROOT` (l.41) | 🟡 |

## Acceptance Criteria

```gherkin
Feature: Upload

  Scenario: A STEP part uploads with geometry
    Given an aeroplane and a 2 MB .step file
    When I POST it to /aeroplanes/{id}/construction-parts
    Then the response status is 201
    And volume_mm3, area_mm2 and the three bbox fields are non-null
    And the file exists at tmp/construction_parts/{aeroplane_id}/{part_id}_<8 hex>.step

  Scenario: An STL part uploads without geometry
    Given a 2 MB .stl file
    When I upload it
    Then the response status is 201
    And volume_mm3, area_mm2 and the bbox fields are null
    And no error is reported

  Scenario: An unsupported extension is rejected
    Given a file named part.obj
    When I upload it
    Then the upload is rejected
    And no file is written

  Scenario: An oversize upload is rejected with 413
    Given a 51 MB .step file
    When I upload it
    Then the response status is 413
    And the error details carry reason "file_too_large"

  Scenario: Two uploads of the same filename do not collide
    Given bracket.step has already been uploaded
    When I upload bracket.step again
    Then two parts exist with distinct file paths

  Scenario: The CAD kernel is unavailable
    Given cad_available() returns false
    When I upload a .step file
    Then the response status is 201
    And every geometry field is null

  Scenario: One failing measurement does not lose the others
    Given Area() raises for a particular solid
    When the geometry is extracted
    Then volume_mm3 and the bbox are still populated
    And area_mm2 is null

Feature: Scoping

  Scenario: A part of another aeroplane is not reachable
    Given part 7 belongs to aeroplane A
    When I GET /aeroplanes/B/construction-parts/7
    Then the response status is 404

Feature: Locking and deletion

  Scenario: A locked part cannot be deleted
    Given a part with locked true
    When I DELETE it
    Then the response status is 409

  Scenario: An unlocked part is deleted with its file
    Given a part with locked false
    When I DELETE it
    Then the row is gone
    And the file no longer exists

  Scenario: Locking does not block editing
    Given a locked part
    When I rename it
    Then the rename succeeds

Feature: Download

  Scenario: A STEP part downloads as STEP
    Given a STEP-stored part
    When I GET its file with format step
    Then the stored file is streamed

  Scenario: A STEP part downloads as STL
    Given a STEP-stored part
    When I GET its file with format stl
    Then a valid STL is returned
    # BR-CP7: the temporary file created for this is never cleaned up

  Scenario: An unsupported download format is rejected
    Given a stored part
    When I GET its file with format iges
    Then the request is rejected

Feature: Updates

  Scenario: Only name, material and thumbnail are writable
    Given a stored part
    When I PUT a body containing file_path
    Then file_path is unchanged

  Scenario: A non-material component is accepted as the material link
    Given a component whose type is not "material"
    When I set it as material_component_id
    Then the write succeeds
    # BR-CP10: the type is not enforced; the frontend filters the dropdown
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Upload with extension and size limits (RF-CP-01…RF-CP-04) | Must | The entry point; both limits are the only bound on an unauthenticated-by-design deployment (ADR 0016) |
| Aeroplane scoping on every read (RF-CP-10) | Must | The only access control in the use case — part ids are sequential integers |
| STEP geometry extraction with per-measure guards (RF-CP-05/RF-CP-08) | Must | The extracted volume feeds mass estimation; a partial failure must not lose the rest |
| Null geometry for STL and for a missing kernel (RF-CP-06/RF-CP-07) | Must | Both are normal, supported states, not errors (ADR 0017) |
| Lock semantics (RF-CP-12/RF-CP-13) | Must | The user's only protection against deleting a part they have already built around |
| Delete with file cleanup (RF-CP-14) | Must | Otherwise every delete leaks a file |
| List / read / update (RF-CP-09/RF-CP-11) | Must | Basic CRUD the workbench depends on |
| Download in both formats (RF-CP-15) | Must | The reason to store the file at all |
| STL regeneration (RF-CP-16) | Should | A convenience for printers; the leak makes it a liability at volume |
| Material link (RF-CP-17) | Should | Feeds mass estimation, but a part without a material is usable |
| Cascade on aeroplane delete (RF-CP-18) | Should | Currently orphans rows and files; a re-implementation should add the FK |
| Path guards equivalent to artefacts (RF-CP-20) | Should | The asymmetry with `artifact_service` is not justified anywhere |
| Referential guard for tree references (RF-CP-19) | Could | `locked` covers the common case by convention |
| Re-upload to an existing part (RF-CP-21) | Won't | Deliberately absent — geometry and file are immutable after upload |
| STL geometry extraction (RF-CP-22) | Won't | A triangle soup has no exact volume; documented MVP limitation |
| Reproducing the leaked temp file (BR-CP7) | Won't | A confirmed defect; a re-implementation must stream and clean up |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/construction_part_service.py` (350 l.) | `_get_part_or_404` (l.44-60), upload (two-phase, l.119-124 for the size marker), `_extract_geometry` (l.144-198), STL regeneration (l.276-280), `delete_part` (l.336-339), `ALLOWED_SUFFIXES`/`MAX_FILE_SIZE_BYTES`/`ALLOWED_DOWNLOAD_FORMATS`/`STORAGE_ROOT` (l.38-41) | 🟢 |
| `app/api/v2/endpoints/aeroplane/construction_parts.py` (218 l.) | list/create, read/update/delete, lock, unlock, file download; the 413 mapping | 🟢 |
| `app/models/construction_part.py` | `ConstructionPartModel` (l.19) | 🟢 |
| `app/schemas/construction_part.py` | `ConstructionPartRead` (l.11), `ConstructionPartUpdate` (l.51), `ConstructionPartList` (l.59) | 🟢 |
| `alembic/versions/4a9c81984e86_add_construction_parts_table.py` | base table | 🟢 |
| `alembic/versions/1a39e098d77e_add_file_path_format_to_construction_….py` | `file_path`, `file_format` | 🟢 |
| `alembic/versions/7cc3eaf27d6b_add_construction_part_id_to_component_….py` | `component_tree.construction_part_id` FK | 🟢 |
| `app/core/config.py` | `cad_available()` probe (ADR 0017) | 🟢 |
