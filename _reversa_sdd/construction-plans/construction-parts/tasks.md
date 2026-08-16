# construction-parts — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Parent module task list: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `aeroplane-core` available — a part is always addressed under an aeroplane
      UUID, and the component tree may reference a part.
- [ ] `get_db()` request-scoped session owning the transaction
      (`app/db/session.py`, ADR 0009). The service calls `db.flush()` but never
      `db.commit()` — this is what makes the delete ordering (T-CPT-12) a real
      decision.
- [ ] `app/core/exceptions.py` hierarchy plus the module's
      `_raise_http_from_domain` mapping.
- [ ] `components` catalogue present — `material_component_id` points into it.
- [ ] CadQuery **optionally** present; absent, uploads must still succeed with
      null geometry (`cad_available()`, ADR 0017).
- [ ] A writable working directory: storage is CWD-relative
      (`tmp/construction_parts/`).

## Tasks

### Storage and model

- [ ] **T-CPT-01 — The `construction_parts` table.**
  `id`, `aeroplane_id` (String, **indexed, no FK**), `name`, `volume_mm3`,
  `area_mm2`, `bbox_x_mm`/`bbox_y_mm`/`bbox_z_mm`, `material_component_id`
  (FK → `components.id`), `locked` (Boolean, `server_default "0"`),
  `thumbnail_url`, `file_path`, `file_format`, `created_at`, `updated_at`.
  - Legacy origin: `app/models/construction_part.py:19`;
    `alembic/versions/4a9c81984e86_add_construction_parts_table.py`,
    `1a39e098d77e_add_file_path_format_to_construction_….py`
  - Definition of done: the schema round-trips through `ConstructionPartRead`;
    `locked` defaults to false at the DB level, not only in Python.
  - Confidence: 🟢

- [ ] **T-CPT-02 — 🔴 Decide the `aeroplane_id` foreign key.**
  Legacy stores a plain indexed string, so deleting an aeroplane orphans both
  rows and files (the same pattern as `component_tree.aeroplane_id`).
  - Legacy origin: data-dictionary §Table `construction_parts` (BR-CP9)
  - Definition of done: either a real FK with `ON DELETE CASCADE` plus file
    cleanup, or an explicit, documented decision to keep orphans with a cleanup
    job. Reproducing the current silent orphaning is not acceptable.
  - Confidence: 🟡 — requires a human decision

- [ ] **T-CPT-03 — Storage layout.**
  `tmp/construction_parts/{aeroplane_id}/{part_id}_{uuid4().hex[:8]}{ext}`,
  `STORAGE_ROOT = Path("tmp") / "construction_parts"`.
  - Legacy origin: `app/services/construction_part_service.py:41`
  - Definition of done: two uploads of the same original filename produce two
    distinct paths; the per-aeroplane directory is created on demand.
  - Confidence: 🟢

- [ ] **T-CPT-04 — 🔴 Bring part paths under the artefact guards.**
  Legacy parts live outside `ARTIFACTS_BASE_DIR` and therefore outside
  `_ensure_within_base` and the symlink rejection.
  - Legacy origin: `construction_part_service.py:41` vs
    `app/services/artifact_service.py:25-36, 202-203` (BR-68)
  - Definition of done: a part path is resolved and constrained to its base, and
    symlinks are rejected — or the asymmetry is documented with a reason.
  - Confidence: 🟡 — the legacy asymmetry has no recorded justification

### Upload

- [ ] **T-CPT-05 — Extension allow-list.**
  `ALLOWED_SUFFIXES = {".step", ".stp", ".stl"}`, checked **before** anything is
  written.
  - Legacy origin: `construction_part_service.py:38`
  - Definition of done: a `.obj` upload is rejected and no file appears on disk.
  - Confidence: 🟢

- [ ] **T-CPT-06 — Size limit with the 413 marker.**
  `MAX_FILE_SIZE_BYTES = 52_428_800`; exceeding it raises
  `ConflictError(details={"reason": "file_too_large"})`, which the endpoint maps
  to **413**.
  - Legacy origin: `construction_part_service.py:39, 119-124`
  - Definition of done: a 51 MB upload returns 413 and the details marker; a
    50 MB upload succeeds. The marker string is asserted, since the endpoint keys
    on it.
  - Confidence: 🟢

- [ ] **T-CPT-07 — Two-phase upload.**
  Insert the row, `db.flush()` for the id, then write the file, then update the
  row with `file_path`, `file_format` and the extracted geometry.
  - Legacy origin: `construction_part_service.py` (the upload path)
  - Definition of done: the stored filename contains the row's own id; a write
    failure after the flush does not leave a committed row with no file (the
    request-scoped rollback covers it).
  - Confidence: 🟢

### Geometry

- [ ] **T-CPT-08 — `_extract_geometry`, STEP only.**
  Return all-`None` when `cad_available()` is false **or** the format is not
  STEP. STL is a triangle soup — a documented MVP limitation, not a bug.
  - Legacy origin: `construction_part_service.py:144-198`
  - Definition of done: an STL upload and a no-kernel STEP upload both return 201
    with null geometry and no error.
  - Confidence: 🟢

- [ ] **T-CPT-09 — Guard each measurement separately.**
  `Volume()`, `Area()` and `BoundingBox()` each in their own `try`.
  - Legacy origin: `construction_part_service.py:144-198`
  - Definition of done: with `Area()` forced to raise, `volume_mm3` and the three
    bbox fields are still populated and `area_mm2` is null.
  - Confidence: 🟢

- [ ] **T-CPT-10 — 🔴 Pin the input unit assumption.**
  The columns are named `_mm3` / `_mm2` / `_mm`, so a millimetre-scaled STEP is
  assumed. Nothing verifies it.
  - Legacy origin: the column names in
    `app/models/construction_part.py:19`; no check exists in
    `_extract_geometry`
  - Definition of done: either the unit is detected or declared on upload, or a
    plausibility check warns on a suspicious magnitude. A metre-scaled STEP must
    not silently record a volume 10⁹× too small.
  - Confidence: 🟡

### Reads and updates

- [ ] **T-CPT-11 — `_get_part_or_404`, aeroplane-scoped.**
  Filter on **both** the part id and the aeroplane id on every read, update, lock
  and delete.
  - Legacy origin: `construction_part_service.py:44-60`
  - Definition of done: a part id belonging to another aeroplane returns 404, not
    200 and not 403. Part ids are sequential integers, so add an explicit
    enumeration test.
  - Confidence: 🟢

- [ ] **T-CPT-12 — List with a total.**
  `ConstructionPartList = {aeroplane_id, items, total}`.
  - Legacy origin: `app/schemas/construction_part.py:59`
  - Definition of done: the listing is scoped to the aeroplane and `total`
    matches `len(items)`.
  - Confidence: 🟢

- [ ] **T-CPT-13 — Update restricted to three fields.**
  `ConstructionPartUpdate` carries `name`, `material_component_id`,
  `thumbnail_url` only — the file and its geometry are immutable after upload.
  - Legacy origin: `app/schemas/construction_part.py:51`
  - Definition of done: a body containing `file_path` or `volume_mm3` leaves
    those columns unchanged.
  - Confidence: 🟢

- [ ] **T-CPT-14 — 🔴 Decide whether the material link is type-checked.**
  Legacy allows any `components.id`; only the frontend filters for
  `component_type == "material"`.
  - Legacy origin: data-dictionary §Table `construction_parts` (BR-CP10)
  - Definition of done: either the service validates the component type, or the
    looseness is documented as intentional (e.g. to allow a part to reference a
    bought component).
  - Confidence: 🟡

### Lock and delete

- [ ] **T-CPT-15 — Lock and unlock routes.**
  `PUT .../{part_id}/lock` and `PUT .../{part_id}/unlock`; the flag blocks
  deletion **only** — renames, re-materialling and tree moves stay allowed.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/construction_parts.py`
  - Definition of done: a locked part can still be renamed; a delete returns 409.
  - Confidence: 🟢

- [ ] **T-CPT-16 — Delete with the documented ordering.**
  `ConflictError` when locked; otherwise unlink the file **before** the
  transaction commits.
  - Legacy origin: `construction_part_service.py:336-339` (the comment states the
    trade-off)
  - Definition of done: a normal delete removes both row and file; a forced
    commit failure after the unlink leaves a row with a dangling `file_path`, and
    a test documents that this is the accepted failure mode. Carry the comment
    forward — the ordering looks like a bug without it.
  - Confidence: 🟢

- [ ] **T-CPT-17 — Could: guard parts referenced by a tree node.**
  `component_tree.construction_part_id` may point at a part; nothing prevents
  deleting it.
  - Legacy origin: `alembic/versions/7cc3eaf27d6b_…`; no guard in
    `delete_part`
  - Definition of done: either a referential check (409 with the referencing node
    ids) or an explicit decision that `locked` is the intended protection.
  - Confidence: 🟡

### Download

- [ ] **T-CPT-18 — Download in an allowed format.**
  `ALLOWED_DOWNLOAD_FORMATS = {"step", "stl"}`; a matching format streams the
  stored file.
  - Legacy origin: `construction_part_service.py:40`
  - Definition of done: `format=iges` is rejected; `format=step` on a STEP part
    streams the stored bytes unchanged.
  - Confidence: 🟢

- [ ] **T-CPT-19 — 🔴 STL regeneration without the leak.**
  Legacy writes to `tempfile.mkstemp` and never removes it (l.276-280).
  - Legacy origin: `construction_part_service.py:276-280` (BR-CP7)
  - Definition of done: an STL download of a STEP part returns a valid STL and
    leaves no file behind — stream it, or delete it in a `finally` /
    `BackgroundTask` after the response is sent. A test asserts the temp
    directory is unchanged after N downloads.
  - Confidence: 🟢 (the defect is confirmed) — the fix is required, not optional

## Test Tasks

- [ ] **TT-CPT-01** — Happy path: a STEP upload returns 201 with non-null volume,
      area and bbox (see `requirements.md`, Acceptance Criteria).
- [ ] **TT-CPT-02** — Failure path: a 51 MB upload returns 413 with the
      `file_too_large` marker.
- [ ] **TT-CPT-03** — An unsupported extension is rejected and writes nothing.
- [ ] **TT-CPT-04** — An STL upload succeeds with all-null geometry.
- [ ] **TT-CPT-05** — With `cad_available()` false, a STEP upload still succeeds
      with null geometry (ADR 0017).
- [ ] **TT-CPT-06** — A single failing measurement does not lose the others.
- [ ] **TT-CPT-07** — Security: enumerating part ids under the wrong aeroplane
      returns 404 for every id.
- [ ] **TT-CPT-08** — A locked part returns 409 on delete and 200 on rename.
- [ ] **TT-CPT-09** — Delete removes both the row and the file.
- [ ] **TT-CPT-10** — Filename collision: two uploads of `bracket.step` produce
      two distinct paths.
- [ ] **TT-CPT-11** — Leak regression: N STL downloads leave the temp directory
      unchanged (this is the test the legacy code lacks).
- [ ] **TT-CPT-12** — Immutability: a patch containing `file_path` changes
      nothing.

## Migration Tasks

- [ ] **TM-CPT-01 — Existing rows keep their `file_path`.** The path format
      (`{part_id}_{uuid8}{ext}`) is embedded in stored values; any change to the
      naming scheme needs a data migration, not just new code.
- [ ] **TM-CPT-02 — If T-CPT-02 adds the FK,** existing rows whose
      `aeroplane_id` no longer resolves must be handled explicitly (delete with
      their files, or re-home) before the constraint can be created.

## Suggested Order

1. **T-CPT-01 / T-CPT-03** first — the model and the storage layout; every other
   task depends on the filename containing the row id.
2. **T-CPT-05 → T-CPT-07** next: validate, then insert, then write. Write
   TT-CPT-02 and TT-CPT-03 before the upload path exists so the limits cannot be
   added as an afterthought.
3. **T-CPT-08 / T-CPT-09** after upload works; stub geometry as all-null first,
   which is also the no-kernel behaviour.
4. **T-CPT-11 → T-CPT-13** — reads and updates; TT-CPT-07 (enumeration) should
   exist before the read routes do.
5. **T-CPT-15 / T-CPT-16** — lock before delete, so the 409 path can be tested.
6. **T-CPT-18 / T-CPT-19** last; T-CPT-19's leak fix needs the download path in
   place, and TT-CPT-11 must be written first.
7. **T-CPT-02, T-CPT-04, T-CPT-10, T-CPT-14, T-CPT-17** are blocked on human
   decisions and must not be guessed.

## Resolved by the validation interview

- **Should `aeroplane_id` become a real foreign key?** Today deleting an
  aeroplane orphans both rows and files, with nothing to find them by. The same
  pattern exists on `component_tree`, so the answer should be consistent across
  both.
- **Why do part files live outside `ARTIFACTS_BASE_DIR`?** They miss the
  traversal and symlink guards that every artefact path gets, and no reason is
  recorded.
- **Is `material_component_id` meant to be any component or only a material?**
  The FK is untyped and only the frontend filters.
- **What unit is an uploaded STEP assumed to be in?** The columns say
  millimetres; nothing verifies it, and a metre-scaled file records a volume 10⁹×
  too small.
- **Should a part referenced by a tree node be undeletable?** `locked` is
  user-driven and advisory, not referential.
- **Null geometry has no reason field.** STL, no kernel, a failed measurement and
  a genuinely degenerate solid are indistinguishable to the client — should the
  response say which?
