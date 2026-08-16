# neuralfoil-analysis

> Use-case specification, nested under [`airfoil-catalog`](../requirements.md).
> Focuses on WHAT this slice does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: airfoil-catalog,
> `_reversa_sdd/data-dictionary.md` §Module: airfoil-catalog.

## Overview

`neuralfoil-analysis` is the **single-airfoil interactive surface**: listing the
catalogue, reading one airfoil's coordinates and geometry statistics, uploading
and downloading `.dat` files, and running an on-demand NeuralFoil sweep with its
rendered diagrams. It deliberately uses the **`"large"`** NeuralFoil model, not
the batch backfill's `"xxxlarge"` — the two sizes must never be collapsed. 🟢

## Responsibilities

- List airfoils available on the filesystem and airfoils present in the
  database, and read one by name. 🟢
- Answer whether a given airfoil name is known. 🟢
- Serve Re-independent geometry statistics and the raw Selig coordinates for one
  airfoil. 🟢
- Accept a `.dat` upload and serve a `.dat` download. 🟢
- Run an on-demand NeuralFoil sweep for one airfoil with
  **`model_size="large"`** and render its diagrams. 🟢
- Degrade cleanly when AeroSandbox is unavailable. 🟢

**Explicitly NOT this slice's responsibility:** the batch polar sweep, family
classification or directory import
(→ [`low-re-polar-backfill`](../low-re-polar-backfill/requirements.md)); scoring,
ranking, role tags or the caveat block
(→ [`suitability-search`](../suitability-search/requirements.md)); the
**aircraft-level** speed-band Re table (→ `polar_re_table_service`, gh-493 — a
different Re concept entirely).

## Business Rules

> Rule ids are inherited from [`../requirements.md`](../requirements.md); the
> "derives from" note names the module-level rule each row refines.

### The Reynolds concept this slice exposes

- **BR-C1 — Interactive sweeps are 2D per-airfoil, absolute Re.** 🟢
  *(module BR-C1.)* Like the backfill, this slice's Reynolds numbers are
  **absolute** and aircraft-independent (gh-821). The aircraft-level speed-band
  table (`polar_re_table_service`, gh-493) is a **different concept** in which
  "Re" is a speed proxy at the main wing's MAC for a specific flight condition.
  Both `app/models/airfoil_low_re.py:8-14` and
  `app/services/airfoil_low_re_service.py:3-9` state this explicitly.
  **Do not conflate them.**

### Model size

- **BR-C12 — Two model sizes coexist deliberately; do NOT collapse them.** 🟢
  *(module BR-C12.)* The batch backfill uses `"xxxlarge"`
  (`app/services/airfoil_low_re_service.py`, default on
  `compute_airfoil_low_re`); **this slice's interactive endpoint uses
  `"large"`** (`app/api/v2/endpoints/airfoils.py:111`). The docstring on the
  service says **"do NOT collapse"** (l.428-431).
  The rationale is a deliberate speed/fidelity trade: the interactive path must
  answer inside a request while the overnight backfill can afford the larger
  model. 🟡 INFERRED — the docstring records the instruction, not the reasoning.
- **BR-N1 — An interactive sweep result is never persisted.** 🟡 The persisted
  polars are exclusively the `"xxxlarge"` backfill's output — every
  `airfoil_low_re_polar` row records `neuralfoil_model_size` as provenance
  (`app/models/airfoil_low_re.py:65`), and mixing a `"large"` interactive result
  into that table would corrupt the backfill's idempotence check. INFERRED from
  the provenance column's purpose; no write path from the interactive endpoint
  was found.

### Naming and lookup

- **BR-C3 — Airfoils are addressed by their file stem.** 🟢 *(module BR-C3.)*
  The canonical name is the `.dat` **file stem**, not the Selig header — matching
  how the CadQuery plugin looks airfoils up
  (`app/services/airfoil_service.py:57-87`). Every `{airfoil_name}` path
  parameter in this slice is that stem.
- **BR-C4 — The filesystem listing is CWD-independent.** 🟢 *(module BR-C4.)*
  `GET /airfoils` reads
  `AIRFOILS_DIR = REPO_ROOT / "components" / "airfoils"`, an absolute path
  (`app/core/config.py:6-14`). The comment records the motivating bug:
  procedurally generated airfoils written by the OpenVSP importer landed outside
  a CWD-relative read directory and appeared missing.
- **BR-N2 — Filesystem and database listings are distinct surfaces.** 🟢
  `GET /airfoils` lists what is on disk; `GET /airfoils/db` lists what has been
  imported. They can legitimately differ — a `.dat` file present but not yet
  imported appears only in the first.

### Upload and parsing

- **BR-C2 — Selig format only.** 🟢 *(module BR-C2.)* An uploaded `.dat` file
  goes through the same `_parse_dat_file` rules: the first line is skipped as a
  header; every subsequent line must yield two parseable floats or it is
  **silently skipped**; fewer than 3 lines or fewer than 3 valid coordinates
  raises `ValueError` → 422
  (`app/services/airfoil_service.py:57-87`). No normalisation, no re-panelling.
  🟡 There is **no format sniffing** — a Lednicer-format upload would be
  mis-parsed as coordinates rather than rejected.

### Degradation

- **BR-C14 — The sweep degrades without AeroSandbox.** 🟢 *(module BR-C14.)*
  The NeuralFoil call is import-guarded; on a platform without ASB (e.g.
  `linux/aarch64`) it returns `[]` with a warning rather than raising
  (`airfoil_low_re_service.py:458-462`, ADR 0017). The geometry, coordinate and
  `.dat` routes remain fully functional. 🟡 Whether the analysis endpoint
  surfaces an empty result or a 5xx to the client was not read.

### Persistence read

- **BR-C29 — There is no ORM relationship from `AirfoilModel` to its
  children.** 🟡 *(module BR-C29.)* `/geometry-stats` joins
  `airfoil_geometry` by name in the service rather than through a relationship.
  INFERRED deliberate — it avoids loading 1 665 × 13 polar rows — but nowhere
  documented.

## Functional Requirements

> "Refines" names the module RF in [`../requirements.md`](../requirements.md).

| ID | Refines | Requirement | Priority | Acceptance criterion |
|----|---------|-------------|----------|----------------------|
| RF-21 | RF-21 | Serve interactive NeuralFoil analysis for one airfoil using the `"large"` model | Should | `GET /airfoils/{name}/neuralfoil/analysis` → 200; the model size differs from the backfill's `"xxxlarge"` |
| RF-22 | RF-22 | Serve NeuralFoil diagrams for one airfoil | Could | `GET /airfoils/{name}/neuralfoil/analysis/diagrams` → 200 |
| RF-23 | RF-23 | Serve geometry statistics and raw coordinates for one airfoil | Should | `GET /airfoils/{name}/geometry-stats` and `/coordinates` → 200; unknown name → 404 |
| RF-24 | RF-24 | Accept a `.dat` upload and serve a `.dat` download | Should | `POST /airfoils/datfile` → 201; `GET /airfoils/{name}/datfile` returns the Selig text |
| RF-25 | RF-25 | Answer whether an airfoil name is known | Could | `GET /airfoils/{name}/known` → 200 with a boolean |
| RF-N1 | — | List airfoils available on the filesystem | Should | `GET /airfoils` → 200; the listing is CWD-independent |
| RF-N2 | — | List airfoils present in the database | Should | `GET /airfoils/db` → 200 with `AirfoilSummary` items |
| RF-N3 | — | Read one airfoil from the database by name | Should | `GET /airfoils/db/{name}` → 200 `AirfoilRead`; unknown name → 404 |
| RF-N4 | RF-24 | Reject a malformed `.dat` upload | Must | A file with fewer than 3 valid coordinates → 422 `validation_error` |
| RF-N5 | RF-21 | Keep the interactive sweep out of the persisted polar table | Must | Running the analysis endpoint writes no `airfoil_low_re_polar` row |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | The interactive endpoint uses `"large"` while the backfill uses `"xxxlarge"`; the docstring forbids collapsing them | `app/api/v2/endpoints/airfoils.py:111`; `app/services/airfoil_low_re_service.py:428-431` | 🟢 |
| Correctness | The filesystem listing resolves an absolute directory, not a CWD-relative one | `app/core/config.py:6-14` | 🟢 |
| Correctness | An uploaded `.dat` is parsed by the same Selig rules as an imported one | `app/services/airfoil_service.py:57-87` | 🟢 |
| Portability | The NeuralFoil call is import-guarded and returns `[]` when AeroSandbox is missing | `airfoil_low_re_service.py:458-462` (ADR 0017) | 🟢 |
| Performance | `/geometry-stats` joins by name rather than through an ORM relationship, avoiding a 1 665 × 13 row load | `app/models/airfoil.py`, `app/models/airfoil_low_re.py` | 🟡 |
| Robustness | A single unparseable line inside an otherwise valid upload is skipped rather than failing the file | `airfoil_service.py:57-87` | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Listing and reading

  Scenario: The filesystem listing is CWD-independent
    Given the process is started from an arbitrary working directory
    When I GET /airfoils
    Then the response status is 200
    And the listing reflects components/airfoils

  Scenario: The database listing reflects imported airfoils
    Given nine airfoils have been imported
    When I GET /airfoils/db
    Then the response status is 200
    And nine AirfoilSummary items are returned

  Scenario: A file on disk that was never imported is listed only once
    Given a .dat file present on disk but not imported
    When I GET /airfoils and GET /airfoils/db
    Then the name appears in the filesystem listing
    And it is absent from the database listing

  Scenario: Reading a known airfoil returns its coordinates
    Given an imported airfoil "mh60"
    When I GET /airfoils/db/mh60
    Then the response status is 200
    And the payload carries id, name, coordinates and created_at

  Scenario: Reading an unknown airfoil returns 404
    Given no airfoil named "nosuchfoil"
    When I GET /airfoils/db/nosuchfoil
    Then the response status is 404
    And the error code is "not_found"

Feature: Known lookup

  Scenario: A known name is confirmed
    Given an imported airfoil "mh60"
    When I GET /airfoils/mh60/known
    Then the response status is 200
    And the boolean is true

  Scenario: An unknown name is denied without an error
    Given no airfoil named "nosuchfoil"
    When I GET /airfoils/nosuchfoil/known
    Then the response status is 200
    And the boolean is false

Feature: Geometry statistics and coordinates

  Scenario: Geometry statistics are served for a classified airfoil
    Given an airfoil with a stored geometry row
    When I GET /airfoils/mh60/geometry-stats
    Then the response status is 200
    And it carries max_thickness_pct, max_camber_pct, camber_at_te and family
    And camber_at_te is the camber value at x = 0.9

  Scenario: Raw coordinates are served in Selig order
    Given an imported airfoil
    When I GET /airfoils/mh60/coordinates
    Then the response status is 200
    And the coordinates are chord-normalised between 0 and 1
    And they are not re-panelled

  Scenario: Geometry statistics for an unknown airfoil return 404
    Given no airfoil named "nosuchfoil"
    When I GET /airfoils/nosuchfoil/geometry-stats
    Then the response status is 404

Feature: Dat file upload and download

  Scenario: A valid Selig upload is accepted
    Given a well-formed .dat file with a title line and twenty coordinate pairs
    When I POST it to /airfoils/datfile
    Then the response status is 201
    And the airfoil is named by the file stem

  Scenario: A malformed upload is rejected
    Given a .dat file with only two parseable coordinate lines
    When I POST it to /airfoils/datfile
    Then the response status is 422
    And the error code is "validation_error"

  Scenario: A single junk line in an upload is tolerated
    Given a .dat file with twenty coordinate lines and one line of prose
    When I POST it to /airfoils/datfile
    Then the response status is 201
    And twenty coordinate pairs are stored

  Scenario: The dat file can be downloaded again
    Given an imported airfoil "mh60"
    When I GET /airfoils/mh60/datfile
    Then the response status is 200
    And the body is Selig-format text

Feature: Interactive NeuralFoil analysis

  Scenario: An on-demand sweep uses the large model
    Given an imported airfoil with valid coordinates
    When I GET /airfoils/mh60/neuralfoil/analysis
    Then the response status is 200
    And the sweep was run with model_size "large"
    # The batch backfill uses "xxxlarge" - the two must not be collapsed

  Scenario: An interactive sweep persists nothing
    Given an imported airfoil with thirteen backfilled polar rows
    When I GET /airfoils/mh60/neuralfoil/analysis
    Then the airfoil_low_re_polar row count is still thirteen
    And no row records a model size of "large"

  Scenario: Diagrams are served for a known airfoil
    Given an imported airfoil with valid coordinates
    When I GET /airfoils/mh60/neuralfoil/analysis/diagrams
    Then the response status is 200

  Scenario: Analysis for an unknown airfoil returns 404
    Given no airfoil named "nosuchfoil"
    When I GET /airfoils/nosuchfoil/neuralfoil/analysis
    Then the response status is 404

  Scenario: The service starts without AeroSandbox
    Given AeroSandbox is not installed
    When the application starts
    Then it serves /airfoils, /airfoils/db, /geometry-stats and /coordinates
    And the NeuralFoil call returns an empty result with a warning
    And no exception propagates at import time
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Reject a malformed `.dat` upload (RF-N4) | Must | The only client-supplied content path in this slice; a silently accepted bad file corrupts every downstream metric |
| Keep the interactive sweep out of the persisted table (RF-N5) | Must | A `"large"` row in `airfoil_low_re_polar` would corrupt the backfill's provenance-based idempotence check |
| Interactive NeuralFoil analysis with the `"large"` model (RF-21) | Should | An interactive convenience distinct from the backfill; the size split is deliberate and explicitly protected by a docstring |
| Geometry statistics and coordinates (RF-23) | Should | Supporting surfaces for the editor and the viewer; read-only projections of data the backfill already produced |
| `.dat` upload and download (RF-24) | Should | The manual counterpart to the directory import; the library is usable without it |
| Filesystem and database listings (RF-N1/RF-N2/RF-N3) | Should | The entry points for every airfoil picker; the ranking surface works without them |
| Diagrams (RF-22) | Could | A rendered convenience over data the analysis endpoint already returns |
| `known` lookup (RF-25) | Could | A diagnostic convenience; a caller can infer the same from a 404 on `/airfoils/db/{name}` |
| Persisting interactive sweep results | Won't | Would break the backfill's `neuralfoil_model_size` provenance contract |
| Collapsing the two model sizes | Won't | Explicitly forbidden by the service docstring (l.428-431) |
| Lednicer-format upload support | Won't | 🟡 Measured (`Q-AF-1`): 0 Lednicer candidates among the 1 665 bundled files; the risk is confined to uploads. Not detected — a Lednicer file is mis-parsed rather than rejected |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/api/v2/endpoints/airfoils.py` (1086 l.) | `GET /airfoils`, `GET /airfoils/db`, `GET /airfoils/db/{name}`, `GET /airfoils/{name}/known`, `POST /airfoils/datfile`, `GET /airfoils/{name}/datfile`, `GET /airfoils/{name}/geometry-stats`, `GET /airfoils/{name}/coordinates`, `GET /airfoils/{name}/neuralfoil/analysis`, `.../diagrams`; interactive `model_size="large"` (l.111) | 🟢 |
| `app/services/airfoil_service.py` | `_parse_dat_file` (l.57-87) — shared with the upload path | 🟢 |
| `app/services/airfoil_low_re_service.py` (1086 l.) | `compute_airfoil_low_re` (l.406-521), model-size note (l.428-431), ASB import guard (l.458-462) | 🟢 |
| `app/services/neuralfoil_cdcl_service.py` | cd/cl surrogate helper | 🟡 read only at the module-summary level; its exact signature and call sites were not inspected |
| `app/models/airfoil.py` | `AirfoilModel` (l.6) — read | 🟢 |
| `app/models/airfoil_low_re.py` | `AirfoilGeometryModel` (l.33) — read by `/geometry-stats`; the two-Re note (l.8-14) | 🟢 |
| `app/schemas/airfoil.py` | `AirfoilSummary` (l.28), `AirfoilRead` (l.37), `AirfoilFamily` (l.69) | 🟢 |
| `app/core/config.py` | `AIRFOILS_DIR` (l.6-14) | 🟢 |
| `components/airfoils/` | 1 665 `.dat` files | 🟢 confirmed by count |
| `app/services/polar_re_table_service.py` | — | n/a — a **different** Re concept (gh-493), owned elsewhere |
