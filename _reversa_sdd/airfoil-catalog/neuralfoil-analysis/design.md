# neuralfoil-analysis — Technical Design

> Use-case design, nested under [`airfoil-catalog`](../design.md).
> Focuses on HOW this slice is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Endpoint contracts in full: see [`../contracts.md`](../contracts.md).

## Interface

### Routes owned by this slice — `app/api/v2/endpoints/airfoils.py` (1086 l.) 🟢

| Method | Path | Operation | Status |
|---|---|---|---|
| GET | `/airfoils` | list airfoils available on the **filesystem** | 200 · 500 |
| GET | `/airfoils/db` | list airfoils in the **database** (`AirfoilSummary`) | 200 · 500 |
| GET | `/airfoils/db/{name}` | read one airfoil (`AirfoilRead`) | 200 · 404 · 500 |
| GET | `/airfoils/{airfoil_name}/known` | is this name known? | 200 · 500 |
| POST | `/airfoils/datfile` | upload a `.dat` file | 201 · 422 · 500 |
| GET | `/airfoils/{airfoil_name}/datfile` | download the `.dat` file | 200 · 404 · 500 |
| GET | `/airfoils/{airfoil_name}/geometry-stats` | thickness / camber / family | 200 · 404 · 500 |
| GET | `/airfoils/{airfoil_name}/coordinates` | raw Selig coordinates | 200 · 404 · 500 |
| GET | `/airfoils/{airfoil_name}/neuralfoil/analysis` | interactive sweep, **`model_size="large"`** (l.111) | 200 · 404 · 500 |
| GET | `/airfoils/{airfoil_name}/neuralfoil/analysis/diagrams` | rendered diagrams for the sweep | 200 · 404 · 500 |

`GET /airfoils/db/{name}` is shared ownership with
[`suitability-search`](../suitability-search/design.md), which declares
`/airfoils/db/suitability` — that route must be declared **first** or
`"suitability"` is captured as a name. 🟡

### Services consumed 🟢

| Symbol | File | Purpose |
|---|---|---|
| `_parse_dat_file` | `app/services/airfoil_service.py:57-87` | shared with the import path; parses an uploaded `.dat` |
| `compute_airfoil_low_re` | `app/services/airfoil_low_re_service.py:406-521` | the sweep, invoked here with `model_size="large"` |
| ASB import guard | `airfoil_low_re_service.py:458-462` | returns `[]` with a warning when AeroSandbox is missing |
| model-size note | `airfoil_low_re_service.py:428-431` | **"do NOT collapse"** |
| `neuralfoil_cdcl_service` | `app/services/neuralfoil_cdcl_service.py` | cd/cl surrogate helper 🟡 — read only at the module-summary level; its signature and call sites were not inspected |

### Data read (never written, except the upload) 🟢

| Table | Used for |
|---|---|
| `airfoils` | the db listing, `AirfoilRead`, `known`, `/coordinates`, `/datfile` |
| `airfoil_geometry` | `/geometry-stats` — joined **by name**, not through a relationship |

`airfoil_low_re_polar` is **not** written by this slice. 🟡 See F5.

## Main Flow

### F1 — List the catalogue 🟢

Two distinct surfaces that can legitimately disagree:

1. `GET /airfoils` reads the filesystem at
   `AIRFOILS_DIR = REPO_ROOT / "components" / "airfoils"` — an **absolute,
   CWD-independent** path (`app/core/config.py:6-14`). The comment records the
   motivating bug: procedurally generated airfoils written by the OpenVSP
   importer landed outside a CWD-relative read directory and appeared missing.
2. `GET /airfoils/db` reads the `airfoils` table and returns `AirfoilSummary`
   items (`id`, `name`).

A `.dat` file present on disk but not yet imported appears only in the first.

### F2 — Read one airfoil 🟢

- `GET /airfoils/db/{name}` → `AirfoilRead` (`id`, `name`, `coordinates`,
  `source_file`, `created_at`); unknown name → **404**.
- `GET /airfoils/{name}/known` → a boolean, **200 in both cases**. 🟡 The
  200-for-unknown behaviour is inferred from the route's purpose; the handler
  body was not read.
- `GET /airfoils/{name}/coordinates` → the stored Selig-order pairs,
  chord-normalised 0–1, exactly as parsed — **no normalisation and no
  re-panelling** was ever applied (`airfoil_service.py:57-87`).

The `{airfoil_name}` path parameter is always the **file stem**, matching how the
CadQuery plugin resolves airfoils. 🟢

### F3 — Geometry statistics 🟢

`GET /airfoils/{name}/geometry-stats` returns the Re-independent
`airfoil_geometry` row: `max_thickness_pct`, `max_camber_pct` (both **percent of
chord**), `camber_at_te` and `family`.

⚠ `camber_at_te` is **the camber value at x = 0.9**, not at the trailing edge
(gh-834) — the field name is historical. A consumer that reads it as a
trailing-edge value will misinterpret every airfoil.

The join is done **by name** in the service; there is no ORM relationship from
`AirfoilModel` to `AirfoilGeometryModel`. 🟡 INFERRED deliberate — it avoids
loading 1 665 × 13 polar rows — but undocumented.

### F4 — `.dat` upload and download 🟢

**Upload** (`POST /airfoils/datfile`) runs the same `_parse_dat_file` rules as
the directory import (`airfoil_service.py:57-87`):

1. **Selig format only.** The first line is skipped as a header.
2. Every subsequent line must yield two parseable floats; anything else is
   **silently skipped**.
3. Fewer than 3 lines, **or** fewer than 3 valid coordinates → `ValueError`
   → **422**.
4. The canonical name is the **file stem**.
5. No normalisation, no re-panelling.

🟡 There is **no format sniffing** — a Lednicer-format upload, whose first data
line is a pair of surface-point counts rather than a coordinate, would be
mis-parsed as coordinates rather than rejected.

**Download** (`GET /airfoils/{name}/datfile`) serves the Selig text back;
unknown name → 404.

### F5 — Interactive NeuralFoil analysis 🟢

`GET /airfoils/{name}/neuralfoil/analysis` calls the same
`compute_airfoil_low_re` machinery as the backfill but with
**`model_size="large"`** (`app/api/v2/endpoints/airfoils.py:111`):

```python
compute_airfoil_low_re(name, coords, re_grid, *,
                       model_size="large",       # <-- interactive
                       n_crit=9.0,
                       confidence_gate=0.90,
                       alpha_start=-5.0, alpha_end=18.0,
                       alpha_step=0.2) -> list[dict]
```

versus the backfill's `model_size="xxxlarge"` (the service default). The
docstring says **"do NOT collapse"** (`airfoil_low_re_service.py:428-431`).

🟡 **The rationale is a deliberate speed/fidelity trade** — the interactive path
must answer inside a request while the overnight backfill can afford the larger
model. INFERRED: the docstring records the instruction, not the reasoning.

🟡 **The result is not persisted.** Every `airfoil_low_re_polar` row records
`neuralfoil_model_size` as provenance so the backfill can skip up-to-date rows
(`app/models/airfoil_low_re.py:65`); writing a `"large"` result into that table
would corrupt the idempotence check. No write path from this endpoint was found.

### F6 — Diagrams 🟢

`GET /airfoils/{name}/neuralfoil/analysis/diagrams` renders the sweep of F5.
🟡 The rendering technology, output format and whether it re-runs the sweep or
reuses a cached result were not read.

### F7 — Degradation without AeroSandbox 🟢

The NeuralFoil call is import-guarded: on a platform without ASB (e.g.
`linux/aarch64`) `compute_airfoil_low_re` returns `[]` with a warning rather than
raising (`airfoil_low_re_service.py:458-462`, ADR 0017). The listing, geometry,
coordinate and `.dat` routes remain fully functional.

🟡 Whether F5 surfaces the empty result as a 200 with an empty body or maps it to
a 5xx was not read.

### F8 — The two Reynolds concepts 🟢

Like the backfill, this slice's Reynolds numbers are **absolute** and
aircraft-independent (gh-821). The aircraft-level speed-band table
(`polar_re_table_service`, gh-493) re-bins aircraft fine-sweep data into
speed-band labels where "Re" is a speed proxy at the main wing's MAC for a
specific flight condition. Both `app/models/airfoil_low_re.py:8-14` and
`app/services/airfoil_low_re_service.py:3-9` warn against conflating them.

## Alternative Flows

- **Unknown airfoil name** on `/airfoils/db/{name}`, `/geometry-stats`,
  `/coordinates`, `/datfile` or `/neuralfoil/analysis` → **404**
  `not_found`. 🟢
- **Unknown name on `/known`** → **200** with `false`, not a 404. 🟡 INFERRED
  from the route's purpose.
- **Airfoil present in `airfoils` but with no `airfoil_geometry` row**
  (imported but not yet classified) → 🟡 whether `/geometry-stats` returns 404 or
  a null-filled body was not read.
- **Malformed `.dat` upload:** `ValueError` → **422** `validation_error`. 🟢
- **Upload with one junk line:** the line is skipped; the file is accepted. 🟢
- **Lednicer-format upload:** 🟡 **not detected.** The leading surface-point
  counts are read as a coordinate pair and the airfoil is persisted with silently
  wrong geometry.
- **Duplicate upload name:** 🟡 whether the upload replaces, conflicts (409) or
  is skipped like the directory import's case-insensitive dedup was not read.
- **AeroSandbox unavailable:** the sweep returns `[]` with a warning; nothing
  raises at import time and the non-solver routes keep working. 🟢
- **Route collision:** if `/airfoils/db/{name}` is declared before
  `/airfoils/db/suitability`, the suitability route resolves to a lookup for an
  airfoil literally named `"suitability"` and returns 404. 🟡 Cross-slice hazard,
  owned jointly with
  [`suitability-search`](../suitability-search/design.md).

## Dependencies

- **[`low-re-polar-backfill`](../low-re-polar-backfill/design.md)** — produces
  the `airfoils` and `airfoil_geometry` rows this slice reads, and shares
  `_parse_dat_file` with the upload path and `compute_airfoil_low_re` with the
  analysis path.
- **AeroSandbox / NeuralFoil** (optional, absent on `linux/aarch64`) — required
  only by F5/F6; import-guarded (ADR 0017).
- **`app/core/config.py`** — `AIRFOILS_DIR` for the filesystem listing.
- **`components/airfoils/`** — 1 665 `.dat` files, the source of truth for
  `GET /airfoils` and the download route.
- **`app/db/session.py`** — the `get_db()` request-scoped transaction
  (ADR 0009); only the upload writes.
- **`app/services/neuralfoil_cdcl_service.py`** — the cd/cl surrogate helper.
  🟡 Read only at the module-summary level.
- **`polar_re_table_service`** — explicitly **not** a dependency; it implements
  the other, aircraft-level Re concept (gh-493).

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| The interactive endpoint uses `"large"` while the backfill uses `"xxxlarge"`, explicitly not collapsed | `app/api/v2/endpoints/airfoils.py:111`; `airfoil_low_re_service.py:428-431` | 🟢 |
| The filesystem and database listings are separate routes rather than one merged view | `GET /airfoils` vs `GET /airfoils/db` | 🟢 |
| The filesystem listing resolves an absolute, CWD-independent directory | `app/core/config.py:6-14` | 🟢 |
| Airfoils are addressed by **file stem** throughout, matching the CadQuery plugin's lookup | `airfoil_service.py:57-87` | 🟢 |
| An uploaded `.dat` reuses the import parser rather than a lenient variant | `airfoil_service.py:57-87` | 🟢 |
| Coordinates are served exactly as parsed — never normalised or re-panelled | `airfoil_service.py:57-87` | 🟢 |
| `camber_at_te` keeps its historical name while meaning "camber at x = 0.9" | gh-834; `app/models/airfoil_low_re.py:33` | 🟢 |
| `/geometry-stats` joins by name rather than through an ORM relationship | `app/models/airfoil.py` | 🟡 |
| The interactive sweep is not persisted, keeping the polar table's provenance single-sourced | `app/models/airfoil_low_re.py:65` | 🟡 |
| The solver is import-guarded so the non-solver routes survive its absence | `airfoil_low_re_service.py:458-462`; ADR 0017 | 🟢 |

## Internal State

Almost entirely stateless. The only write is the `.dat` upload, which inserts an
`airfoils` row (name from the file stem, Selig coordinates, `source_file`
provenance).

Read-only state:

- `airfoils` — the db listing, `AirfoilRead`, `known`, coordinates, `.dat`
  download.
- `airfoil_geometry` — `/geometry-stats`.
- `components/airfoils/*.dat` — the filesystem listing and download source.

Per-request transient state: the interactive sweep result of F5 and the rendered
diagrams of F6, both discarded after the response. 🟡 Whether the diagrams are
cached anywhere was not read.

## Observability

- `logger.warning` when AeroSandbox is unavailable and the sweep returns `[]`
  (`airfoil_low_re_service.py:458-462`). 🟢
- 4xx/5xx go through the shared error envelope; a 404 carries the requested name
  in `details`. 🟡 INFERRED from the module-wide envelope shape.
- No metrics, traces or per-route logging specific to this slice were found. 🟢
- 🟡 There is **no in-band signal of which model size produced an interactive
  result**. A consumer comparing an interactive sweep against a stored
  `"xxxlarge"` polar has no way to see the discrepancy's cause from the response
  alone.

## Risks and Gaps

- 🟡 **No Lednicer-format detection on upload.** `_parse_dat_file` assumes
  Selig, so a Lednicer file's leading surface-point counts are read as
  coordinates and produce a silently wrong airfoil. The upload route is the most
  likely place for a hand-supplied non-Selig file to enter the system.
- 🟡 **The interactive result carries no model-size marker.** A `"large"` sweep
  and an `"xxxlarge"` stored polar can disagree, and nothing in the response
  explains why.
- 🟡 **Duplicate-upload behaviour is unknown.** Whether `POST /airfoils/datfile`
  replaces an existing airfoil, conflicts with 409, or skips it the way the
  directory import's case-insensitive dedup does, was not read.
- 🟡 **The unclassified-airfoil case on `/geometry-stats` is unknown.** An
  airfoil imported but not yet classified has no `airfoil_geometry` row; whether
  the route 404s or returns nulls was not read.
- 🟡 **The ASB-absent response shape for `/neuralfoil/analysis` is unknown.**
  The service returns `[]`; whether the endpoint surfaces that as a 200 with an
  empty body or maps it to a 5xx was not read.
- 🟡 **`neuralfoil_cdcl_service` was only read at the module-summary level.** Its
  signature, call sites and relationship to `compute_airfoil_low_re` are
  unconfirmed.
- 🟡 **The diagrams route is opaque.** Its rendering technology, output format,
  and whether it re-runs the sweep or reuses a cached result were not read — a
  re-implementation cannot reproduce it from this spec alone.
- 🟡 **Route ordering is a shared hazard.** `/airfoils/db/{name}` lives in this
  slice while `/airfoils/db/suitability` lives in
  [`suitability-search`](../suitability-search/design.md); the declaration order
  between them must be pinned by a test.
- 🟡 **`/geometry-stats` exposes `camber_at_te` under a misleading name.** The
  value is measured at x = 0.9; a client reading it as a trailing-edge camber
  will misinterpret every airfoil, and nothing in the payload says otherwise.
