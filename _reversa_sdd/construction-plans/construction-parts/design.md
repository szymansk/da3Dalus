# construction-parts — Technical Design

> Use-case design, nested under the module [`construction-plans`](../design.md).
> Focuses on HOW this use case is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Endpoint contracts in full: [`../contracts.md`](../contracts.md).

## Interface

### Service — `app/services/construction_part_service.py` (350 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `_get_part_or_404` | `(db, aeroplane_id, part_id)` | row | filters on **both** ids; `NotFoundError` otherwise (l.44-60) |
| upload | `(db, aeroplane_id, filename, stream)` | row | two-phase: row + `flush()` → write → extract (BR-CP1) |
| `_extract_geometry` | `(path, file_format)` | `dict` of `float \| None` | all-`None` unless `cad_available()` **and** STEP (l.144-198) |
| list | `(db, aeroplane_id)` | `ConstructionPartList` | `{aeroplane_id, items, total}` |
| update | `(db, aeroplane_id, part_id, patch)` | row | `name`, `material_component_id`, `thumbnail_url` only |
| lock / unlock | `(db, aeroplane_id, part_id)` | row | sets/clears `locked` |
| `delete_part` | `(db, aeroplane_id, part_id)` | `None` | `ConflictError` when locked; unlinks **before** commit (l.336-339) |
| download | `(db, aeroplane_id, part_id, fmt)` | `Path` | `step` verbatim; `stl` regenerated from STEP (l.276-280) 🔴 leaks |

Constants (l.38-41):

```
ALLOWED_SUFFIXES        = {".step", ".stp", ".stl"}
MAX_FILE_SIZE_BYTES     = 52_428_800          # 50 MB  → HTTP 413
ALLOWED_DOWNLOAD_FORMATS= {"step", "stl"}
STORAGE_ROOT            = Path("tmp") / "construction_parts"    # CWD-relative
```

### Data model — `construction_parts` 🟢

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `id` | Integer PK | yes | autoincrement | embedded in the stored filename |
| `aeroplane_id` | String | yes | — | indexed, **no foreign key** — no cascade (BR-CP9) |
| `name` | String | yes | — | |
| `volume_mm3` | Float | no | `NULL` | STEP only; `≥ 0` in the schema |
| `area_mm2` | Float | no | `NULL` | STEP only |
| `bbox_x_mm` / `bbox_y_mm` / `bbox_z_mm` | Float | no | `NULL` | STEP only |
| `material_component_id` | Integer FK → `components.id` | no | `NULL` | 🟡 type not enforced to be `material` |
| `locked` | Boolean | yes | `False` (`server_default "0"`) | blocks delete only |
| `thumbnail_url` | String | no | `NULL` | |
| `file_path` | String | no | `NULL` | `tmp/construction_parts/{aeroplane_id}/{part_id}_{uuid8}{ext}` |
| `file_format` | String | no | `NULL` | `"step"` \| `"stl"` |
| `created_at` / `updated_at` | DateTime(tz) | yes | `now()` / `onupdate` | |

Migrations: `4a9c81984e86_add_construction_parts_table.py`,
`1a39e098d77e_add_file_path_format_to_construction_….py`,
`7cc3eaf27d6b_add_construction_part_id_to_component_….py` (adds
`component_tree.construction_part_id` FK → `construction_parts.id`).

Schemas (`app/schemas/construction_part.py`): `ConstructionPartRead` (l.11),
`ConstructionPartUpdate` (l.51 — `name`, `material_component_id`,
`thumbnail_url` only), `ConstructionPartList` (l.59).

## Main Flow

### F1 — Upload 🟢

```
1. validate suffix ∈ ALLOWED_SUFFIXES                    → reject early
2. validate size  ≤ MAX_FILE_SIZE_BYTES                  → ConflictError(
                                                             reason="file_too_large")
                                                           → endpoint maps to 413
3. INSERT ConstructionPartModel(aeroplane_id, name, …)
   db.flush()                                            # ← the id is needed for
                                                         #   the filename
4. path = tmp/construction_parts/{aeroplane_id}/{part_id}_{uuid4().hex[:8]}{ext}
   write the stream to `path`
5. geometry = _extract_geometry(path, file_format)
   UPDATE the row with file_path, file_format and the geometry
   (get_db() commits at the end of the request — ADR 0009)
```

The ordering matters: the row is created **first** because the id is part of the
filename, and the `uuid4[:8]` suffix makes a re-upload of the same original
filename non-colliding.

The size rejection reuses `ConflictError` — a 409-shaped exception — with a
`details.reason` marker the endpoint inspects to emit **413** instead
(l.119-124). 🟡 A slightly awkward reuse: the domain layer has no
"payload too large" exception, so the marker is the contract.

### F2 — Geometry extraction 🟢

```
_extract_geometry(path, fmt):
    if not cad_available():   return {all None}      # ADR 0017 — aarch64 etc.
    if fmt != "step":         return {all None}      # STL is a triangle soup

    guarded:  volume_mm3 = solid.Volume()
    guarded:  area_mm2   = solid.Area()
    guarded:  bbox       = solid.BoundingBox()  → bbox_x/y/z_mm
```

Each measurement sits in its **own** guard, so a solid whose `Area()` raises
still yields a volume and a bounding box. Both "no kernel" and "STL" are normal
outcomes, not errors — an upload always succeeds if the file was written.

🟡 The units are millimetres by column name (`volume_mm3`, `bbox_x_mm`), which
means the STEP is assumed to be millimetre-scaled. Nothing verifies that; a
metre-scaled STEP would be recorded 10⁹× small in volume. See
[`../../questions.md`](../../questions.md).

### F3 — Scoping 🟢

```
_get_part_or_404(db, aeroplane_id, part_id):
    row = query(ConstructionPartModel)
            .filter(id == part_id, aeroplane_id == aeroplane_id)
            .first()
    if row is None: raise NotFoundError
```

Every read, update, lock and delete goes through it. Part ids are sequential
integers, so this filter is the only thing preventing enumeration across
aeroplanes.

### F4 — Delete, and the unlink-before-commit trade-off 🟢

```
delete_part:
    row = _get_part_or_404(...)
    if row.locked:  raise ConflictError            → 409
    unlink(row.file_path)          # ← BEFORE the commit; documented at l.336-339
    db.delete(row)
    # get_db() commits on success, rolls back on exception (ADR 0009)
```

The comment records the reasoning: if the commit later fails, the row survives
with a `file_path` pointing at nothing. The alternative — commit first, then
unlink — risks an orphaned file with no row to find it by. The team chose the
dangling reference. 🟡 Neither state is repaired by any code path.

### F5 — Download 🟢

```
fmt must be in ALLOWED_DOWNLOAD_FORMATS = {"step", "stl"}

fmt == file_format          → stream the stored file
fmt == "stl", stored "step" → regenerate:
        tempfile.mkstemp() → export STL → return that path   (l.276-280)
        🔴 nothing ever removes it
```

Every STL download of a STEP part leaves a file in the system temp directory. On
a long-running instance this is unbounded.

### F6 — What this use case is *not* 🟢

Despite sharing a module, a construction **part** and a construction **plan**
have no relationship: no `$TYPE` decoding, no Creator execution, no artefact
directory, no SSE. The only link into the rest of the system is
`component_tree.construction_part_id`, which lets a tree node point at a part.

## Alternative Flows

- **Unsupported extension:** rejected before any write. 🟢
- **Oversize:** `ConflictError(details.reason = "file_too_large")` → **413**. 🟢
- **STL upload:** stored, geometry all-null, no error. 🟢
- **CAD kernel absent:** STEP stored, geometry all-null, no error (ADR 0017). 🟢
- **One measurement raises:** the other two are still recorded. 🟢
- **Part id from another aeroplane:** 404 via `_get_part_or_404`. 🟢
- **Delete a locked part:** `ConflictError` → 409. 🟢
- **Commit fails after the unlink:** the row survives with a dangling
  `file_path`. 🟡 No repair path.
- **STL requested for a STEP part:** 🟢 served from the cache beside the STEP (`R2-01`); regenerated once, never into a temp file.
- **Aeroplane deleted:** parts are **not** cascaded — rows and files are
  orphaned. 🔴
- **Tree node references a deleted part:** nothing prevents it; only the
  user-driven `locked` flag stands in the way. 🔴

## Dependencies

- **`aeroplane-core`** — the owning aeroplane (by UUID string, without an FK) and
  the component tree that may reference a part.
- **`powertrain`** — the `components` catalogue that supplies material rows for
  `material_component_id` (untyped link, BR-CP10).
- **CadQuery / OCCT** — optional; used only for STEP measurement and STL
  regeneration, probed via `cad_available()` (ADR 0017).
- **`app/db/session.py` `get_db()`** — owns the transaction boundary; the service
  never commits (ADR 0009). This is what makes F4's ordering a real trade-off.
- **`mass-and-balance`** — the consumer of `volume_mm3` × material density, 🟡
  inferred from the presence of the material link rather than read.
- **Not** `cad-generation`'s `artifact_service`: parts deliberately (or
  accidentally) live in a different tree without its guards (BR-CP8).

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Upload is row-first so the id can be part of the filename | BR-CP1; the `flush()` before the write | 🟢 |
| A `uuid4[:8]` suffix makes re-uploads non-colliding | the filename pattern | 🟢 |
| Geometry is STEP-only; STL is accepted but not measured | `_extract_geometry` (l.144-198) | 🟢 |
| Each measurement is guarded individually rather than as a block | l.144-198 | 🟢 |
| A missing CAD kernel is a normal state, not an upload failure | `cad_available()` gate (ADR 0017) | 🟢 |
| Access control is a two-column filter, not a separate authorisation layer | `_get_part_or_404` (l.44-60) | 🟢 |
| `locked` guards deletion only, not editing or tree moves | `delete_part` | 🟢 |
| The file is unlinked before the commit, accepting a dangling reference over an orphaned file | comment at l.336-339 | 🟢 |
| Oversize is signalled through a `ConflictError` marker rather than a dedicated exception | l.119-124 | 🟢 |
| The file and its geometry are immutable after upload | `ConstructionPartUpdate` (l.51) | 🟢 |
| 🟢 `aeroplane_id` becomes a real FK, as does `component_tree`'s (`Q-CC-7`) | data-dictionary §Table `construction_parts` | 🟢 (intent 🔴) |
| The material link is not constrained to material components | same | 🟡 (`Q-CP-9`) |
| Parts move under `ARTIFACTS_BASE_DIR` (`Q-CP-9 ②`) 🟢 | previously CWD-relative `tmp/` | `STORAGE_ROOT` (l.41) | 🟢 (intent 🔴) |

## Internal State

- **Database:** one `construction_parts` row per part. The only mutable state is
  `locked`, plus the three editable metadata fields. No status column, no
  workflow — recorded in `state-machines.md` §12 as a deliberate non-machine.
- **Filesystem:** `tmp/construction_parts/{aeroplane_id}/{part_id}_{uuid8}{ext}`,
  CWD-relative. Not covered by artefact cleanup, not covered by the traversal and
  symlink guards, not removed when the aeroplane goes away.
- **Transient:** the `tempfile.mkstemp` STL produced per download — never
  reclaimed (🔴 BR-CP7).

## Observability

- Domain errors map through the module's shared `_raise_http_from_domain`; the
  413 is the one endpoint-level special case. 🟢
- 🔴 There is **no metric or log** for storage consumption, orphaned rows,
  orphaned files or leaked temp files — precisely the three unbounded quantities
  in this use case.
- 🟡 A geometry extraction that returns nulls is indistinguishable in the
  response from an STL upload, a missing kernel and a failed measurement. The
  client sees `null` in all four cases with no reason field.

## Risks and Gaps

- 🔴 **The STL regeneration temp file is never cleaned up** (l.276-280). Every
  STL download of a STEP part leaks; unbounded on a long-running instance.
- 🔴 **No cascade from `aeroplanes`.** `aeroplane_id` is an unconstrained string,
  so deleting an aeroplane orphans both rows and files, with nothing to find them
  by afterwards.
- 🔴 **Part files sit outside `ARTIFACTS_BASE_DIR`** and therefore outside
  `_ensure_within_base` and the symlink rejection that protect every artefact
  path. The asymmetry is not justified anywhere in the code.
- 🔴 **`material_component_id` is not type-checked**; only the frontend filters
  the dropdown, so an API client can link a part to a motor.
- 🔴 **Nothing protects a part a tree node points at.** `locked` is advisory and
  user-driven, not referential.
- 🟡 **Null geometry has no reason.** Four different causes produce the same
  response shape.
- 🟡 **The millimetre assumption on STEP input is unverified.** Column names say
  mm; nothing checks the file's unit, and a metre-scaled STEP would record a
  volume 10⁹× too small.
- 🟡 **A dangling `file_path` after a failed commit is never repaired**, and no
  read path tolerates it explicitly — a download of such a row will fail at the
  filesystem.
