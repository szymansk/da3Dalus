# neuralfoil-analysis — Implementation Tasks

> Executable sequence to re-implement this slice from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Module-level task list: [`../tasks.md`](../tasks.md); the module ids
> **T-17** (model-size split), **T-35** (routes) and **T-37** (interactive
> analysis) are refined here.

## Prerequisites

- [ ] [`low-re-polar-backfill`](../low-re-polar-backfill/tasks.md) complete —
      this slice reads `airfoils` and `airfoil_geometry`, and shares
      `_parse_dat_file` and `compute_airfoil_low_re` with it.
- [ ] `get_db()` request-scoped session (`app/db/session.py:55-64`, ADR 0009).
      Only the `.dat` upload writes.
- [ ] `app/core/exceptions.py` hierarchy plus the shared error envelope —
      `NotFoundError` → 404, `ValidationError` → 422.
- [ ] `AIRFOILS_DIR = REPO_ROOT / "components" / "airfoils"` — **absolute**, not
      CWD-relative (`app/core/config.py:6-14`).
- [ ] The 1 665 `.dat` files present under `components/airfoils/`.
- [ ] **AeroSandbox / NeuralFoil optionally** installed. Absent (e.g.
      `linux/aarch64`) the analysis and diagram routes degrade, but every other
      route in this slice must keep working and the app must still start
      (ADR 0017).
- [ ] Coordination with [`suitability-search`](../suitability-search/tasks.md) on
      the `/airfoils/db/...` route declaration order.

## Tasks

### Listing and reading

- [ ] **T-01 — `GET /airfoils` (filesystem listing).**
  Read `AIRFOILS_DIR`, an **absolute, CWD-independent** path.
  - Legacy origin: `app/api/v2/endpoints/airfoils.py`; `app/core/config.py:6-14`
  - Definition of done: the listing is identical whichever working directory the
    process was started from; a `.dat` file present but not imported still
    appears.
  - Confidence: 🟢

- [ ] **T-02 — `GET /airfoils/db` (database listing).**
  Return `AirfoilSummary` items (`id`, `name`).
  - Legacy origin: `app/api/v2/endpoints/airfoils.py`;
    `app/schemas/airfoil.py:28`
  - Definition of done: nine imported airfoils yield nine items; a file on disk
    that was never imported is absent.
  - Confidence: 🟢

- [ ] **T-03 — `GET /airfoils/db/{name}`.**
  Return `AirfoilRead` (`id`, `name`, `coordinates`, `source_file`,
  `created_at`); unknown name → **404** `not_found`.
  - Legacy origin: `app/api/v2/endpoints/airfoils.py`;
    `app/schemas/airfoil.py:37`
  - Definition of done: a known stem returns the full record; an unknown one
    returns 404 with the `not_found` envelope.
  - Confidence: 🟢

- [ ] **T-04 — `GET /airfoils/{airfoil_name}/known`.**
  A boolean lookup, **200 in both cases** — not a 404 for an unknown name.
  - Legacy origin: `app/api/v2/endpoints/airfoils.py`
  - Definition of done: a known stem returns `true`, an unknown one `false`, both
    with status 200.
  - Confidence: 🟡 INFERRED from the route's purpose; the handler body was not
    read. Confirm before relying on the 200-for-unknown behaviour.

- [ ] **T-05 — `GET /airfoils/{airfoil_name}/coordinates`.**
  Serve the stored Selig-order pairs, chord-normalised 0–1, **exactly as
  parsed** — never normalised, never re-panelled.
  - Legacy origin: `app/api/v2/endpoints/airfoils.py`;
    `app/services/airfoil_service.py:57-87`
  - Definition of done: a round-trip through import → read reproduces the source
    file's coordinates verbatim; unknown name → 404.
  - Confidence: 🟢

### Geometry statistics

- [ ] **T-06 — `GET /airfoils/{airfoil_name}/geometry-stats`.**
  Return the `airfoil_geometry` row: `max_thickness_pct`, `max_camber_pct` (both
  **percent of chord**), `camber_at_te` and `family`. Join **by name**; there is
  no ORM relationship.
  - Legacy origin: `app/api/v2/endpoints/airfoils.py`;
    `app/models/airfoil_low_re.py:33`
  - Definition of done: a classified airfoil returns all four fields; unknown
    name → 404.
  - Confidence: 🟢

- [ ] **T-07 — Document that `camber_at_te` means camber at x = 0.9.**
  The field name is historical (gh-834); it is **not** a trailing-edge value.
  Surface the semantics in the response schema description.
  - Legacy origin: gh-834; `app/models/airfoil_low_re.py:33`
  - Definition of done: the OpenAPI description for the field states "camber
    value at x = 0.9, not at the trailing edge", so a client cannot
    misinterpret it.
  - Confidence: 🟢

### Upload and download

- [ ] **T-08 — `POST /airfoils/datfile` (upload).**
  Reuse `_parse_dat_file` verbatim — **Selig only**, first line skipped as a
  header, unparseable lines silently skipped, fewer than 3 lines or 3 valid
  coordinates → `ValueError` → **422**, name from the **file stem**, no
  normalisation, no re-panelling.
  - Legacy origin: `app/services/airfoil_service.py:57-87`;
    `app/api/v2/endpoints/airfoils.py`
  - Definition of done: a well-formed file returns 201 named by its stem; a
    2-coordinate file returns 422 `validation_error`; a file with one junk line
    is accepted with the remaining coordinates.
  - Confidence: 🟢 (the absence of Lednicer detection is 🔴)

- [ ] **T-09 — Decide and pin the duplicate-upload behaviour.**
  Whether an upload whose stem already exists replaces, conflicts (409), or is
  skipped the way the directory import's case-insensitive dedup does.
  - Legacy origin: not read — `app/api/v2/endpoints/airfoils.py` upload handler
  - Definition of done: the chosen behaviour is asserted by a test and stated in
    [`../contracts.md`](../contracts.md).
  - Confidence: 🟡 — the bundle `Q-AF-5` resolved the polar and scoring edge cases
    by code lookup; anything still unread is recorded there rather than here.

- [ ] **T-10 — `GET /airfoils/{airfoil_name}/datfile` (download).**
  Serve the Selig text back; unknown name → 404.
  - Legacy origin: `app/api/v2/endpoints/airfoils.py`
  - Definition of done: the downloaded text re-imports through T-08 to an
    identical coordinate set.
  - Confidence: 🟢

### Interactive analysis

- [ ] **T-11 — `GET /airfoils/{airfoil_name}/neuralfoil/analysis` with
  `model_size="large"`.**
  Call `compute_airfoil_low_re` with the interactive model size, keeping every
  other parameter at its default (`n_crit=9.0`, `confidence_gate=0.90`,
  `alpha_start=-5.0`, `alpha_end=18.0`, `alpha_step=0.2`).
  - Legacy origin: `app/api/v2/endpoints/airfoils.py:111`;
    `app/services/airfoil_low_re_service.py:406-521`
  - Definition of done: the call site passes `"large"`; unknown airfoil → 404.
  - Confidence: 🟢

- [ ] **T-12 — Never collapse the two model sizes.**
  The backfill uses `"xxxlarge"`, this endpoint `"large"`. The service docstring
  says **"do NOT collapse"**.
  - Legacy origin: `airfoil_low_re_service.py:428-431`
  - Definition of done: a test asserts the two call sites use **different** model
    sizes, so a future refactor cannot silently unify them. (This is the same
    guard as module T-17 / backfill T-17 — implement it once, reference it from
    both slices.)
  - Confidence: 🟢

- [ ] **T-13 — Keep the interactive result out of `airfoil_low_re_polar`.**
  Every stored row records `neuralfoil_model_size` as provenance so the backfill
  can skip up-to-date rows; a `"large"` row would corrupt that check.
  - Legacy origin: `app/models/airfoil_low_re.py:65`
  - Definition of done: hitting the analysis endpoint leaves the polar row count
    unchanged, and no row ever records `"large"`.
  - Confidence: 🟡 INFERRED from the provenance column's purpose; no write path
    from this endpoint was found, but its absence was not positively confirmed.

- [ ] **T-14 — `GET /airfoils/{airfoil_name}/neuralfoil/analysis/diagrams`.**
  Render the sweep of T-11.
  - Legacy origin: `app/api/v2/endpoints/airfoils.py`
  - Definition of done: a known airfoil returns 200 with the rendered output;
    unknown → 404.
  - Confidence: 🟡 INFERRED — the rendering technology, output format and whether
    it re-runs the sweep or reuses a cached result were not read. A
    re-implementation must inspect the handler first.

- [ ] **T-15 — Degradation without AeroSandbox.**
  The NeuralFoil call is import-guarded and returns `[]` with a warning; the
  listing, geometry, coordinate and `.dat` routes stay fully functional and the
  app still starts.
  - Legacy origin: `airfoil_low_re_service.py:458-462` (ADR 0017)
  - Definition of done: with the import patched to raise, `GET /airfoils`,
    `/airfoils/db`, `/geometry-stats`, `/coordinates` and `/datfile` all return
    200, and nothing raises at import time.
  - Confidence: 🟢

- [ ] **T-16 — Pin the ASB-absent response shape for the analysis route.**
  Whether an empty sweep surfaces as 200 with an empty body or maps to a 5xx.
  - Legacy origin: not read — the analysis handler's handling of `[]`
  - Definition of done: the chosen shape is asserted by a test and stated in
    [`../contracts.md`](../contracts.md).
  - Confidence: 🟡 — the bundle `Q-AF-5` resolved the polar and scoring edge cases
    by code lookup; anything still unread is recorded there rather than here.

- [ ] **T-17 — Pin the unclassified-airfoil behaviour on `/geometry-stats`.**
  An airfoil imported but not yet classified has no `airfoil_geometry` row.
  - Legacy origin: not read — the `/geometry-stats` handler
  - Definition of done: the route's response for a missing geometry row (404 vs
    a null-filled body) is asserted by a test.
  - Confidence: 🟡 — the bundle `Q-AF-5` resolved the polar and scoring edge cases
    by code lookup; anything still unread is recorded there rather than here.

### REST layer

- [ ] **T-18 — Route declaration order with `suitability-search`.**
  `/airfoils/db/suitability` must be declared **before** `/airfoils/db/{name}`,
  otherwise `"suitability"` is captured as a name.
  - Legacy origin: route shapes in `app/api/v2/endpoints/airfoils.py`
  - Definition of done: a test hits `/airfoils/db/suitability` and asserts it
    returns a `SuitabilityResponse`, not a 404 for an airfoil named
    `"suitability"`. Owned jointly with
    [`suitability-search`](../suitability-search/tasks.md) T-36 — one test, two
    referencing slices.
  - Confidence: 🟡 INFERRED from the path shapes; the declaration order in the
    legacy file was not read.

- [ ] **T-19 — Investigate `neuralfoil_cdcl_service`.**
  Establish its signature, its call sites and its relationship to
  `compute_airfoil_low_re` before re-implementing this slice.
  - Legacy origin: `app/services/neuralfoil_cdcl_service.py`
  - Definition of done: the helper's role is documented in
    [`design.md`](design.md) with a confirmed signature, replacing the current
    🟡 module-summary-level entry.
  - Confidence: 🟡 — read at module-summary level; `Q-AF-5` resolved the specific
    edge cases by code lookup.

## Test Tasks

- [ ] **TT-01 — Happy path:** import an airfoil, read it from
      `/airfoils/db/{name}`, fetch `/geometry-stats` and `/coordinates`, then run
      `/neuralfoil/analysis` — all 200.
- [ ] **TT-02 — Failure:** every by-name route returns 404 for an unknown stem
      (`/airfoils/db/{name}`, `/geometry-stats`, `/coordinates`, `/datfile`,
      `/neuralfoil/analysis`).
- [ ] **TT-03 — Listings diverge legitimately:** a `.dat` file on disk but not
      imported appears in `GET /airfoils` and not in `GET /airfoils/db`.
- [ ] **TT-04 — CWD independence:** `GET /airfoils` returns the same listing from
      any working directory.
- [ ] **TT-05 — `known` semantics:** a known stem → `true`, unknown → `false`,
      **200 in both cases**.
- [ ] **TT-06 — Coordinates are unmodified:** import → read reproduces the source
      file's pairs verbatim, in Selig order, chord-normalised 0–1.
- [ ] **TT-07 — Upload happy path:** a well-formed `.dat` returns 201 named by
      its file stem.
- [ ] **TT-08 — Upload failure:** fewer than 3 valid coordinates → 422
      `validation_error`.
- [ ] **TT-09 — Upload tolerance:** one junk line among twenty coordinate lines
      is skipped and the file is accepted.
- [ ] **TT-10 — Download round-trip:** `GET /datfile` output re-imports to an
      identical coordinate set.
- [ ] **TT-11 — Model-size split:** the analysis endpoint uses `"large"`, the
      backfill `"xxxlarge"`; the test fails if they are unified. (Shared with
      backfill TT-16 — one test, referenced by both slices.)
- [ ] **TT-12 — No persistence from the interactive sweep:** the
      `airfoil_low_re_polar` row count is unchanged and no row records
      `"large"`.
- [ ] **TT-13 — Missing AeroSandbox:** the non-solver routes all return 200, the
      sweep returns `[]`, a warning is logged, and nothing raises at import time.
- [ ] **TT-14 — Route order:** `/airfoils/db/suitability` is not swallowed by
      `/airfoils/db/{name}`.
- [ ] **TT-15 — `camber_at_te` documentation:** the OpenAPI description states
      the x = 0.9 semantics.
- [ ] **TT-16 — Duplicate upload:** asserts whichever behaviour T-09 resolves.
- [ ] **TT-17 — Unclassified airfoil on `/geometry-stats`:** asserts whichever
      behaviour T-17 resolves.
- [ ] **TT-18 — Solver-free tier:** every route except `/neuralfoil/analysis` and
      `/diagrams` runs on the CI **fast** tier.

## Data Migration Tasks

None. This slice owns no schema — the only write is an `airfoils` row inserted by
the upload, using the same shape as the directory import. All migrations belong
to [`low-re-polar-backfill`](../low-re-polar-backfill/tasks.md). 🟢

One audit item is shared with that slice and repeated here because the upload
route is the most likely entry point for a hand-supplied file:

- [ ] **TM-01 (shared) — Audit for mis-parsed Lednicer files.** Because the
      parser does not sniff the format, any Lednicer file uploaded through
      `POST /airfoils/datfile` holds silently wrong coordinates. Detect
      candidates by a first coordinate pair whose values are integers greater
      than 1. 🟡 The **bundled** library is clean — 0 candidates among 1 665
      files (`Q-AF-1`) — so this applies only to uploads.

## Suggested Order

1. **T-19, T-09, T-16, T-17 first — the four investigation items.** Three of them
   were gaps that determine observable behaviour (duplicate upload, ASB-absent
   response shape, unclassified geometry); `Q-AF-5` resolved the polar and
   scoring edge cases by code lookup, and one is an unread service. A
   re-implementation that guesses these will diverge, so resolve them before
   writing code.
2. **T-01 → T-05** next — listing and reading. They depend only on the backfill's
   `airfoils` table, need no solver, and belong on the CI **fast** tier. T-03 is
   the prerequisite for T-18's route-ordering test.
3. **T-06 → T-07** — geometry statistics. Depends on the backfill's
   `airfoil_geometry` rows existing. T-07 is a schema-description change, not
   logic, but it prevents a real misinterpretation and is cheap.
4. **T-08 → T-10** — upload and download. T-08 blocks T-10 (the round-trip test
   needs the upload path). T-09's decision must be made before T-08 ships, since
   it changes the handler's control flow.
5. **T-11 → T-15** — the interactive analysis. Needs AeroSandbox and therefore
   belongs on the CI **slow** tier, **except T-15**, which must be verified
   *without* it. T-12 and T-13 are guards on T-11 and should land in the same
   change. T-14 depends on T-11.
6. **T-18** last — a route-declaration ordering constraint that must be
   **tested**, not assumed, and coordinated with
   [`suitability-search`](../suitability-search/tasks.md) T-36.

## Pending Gaps (🔴)

- **No Lednicer-format detection on upload.** `_parse_dat_file` assumes Selig, so
  a Lednicer file's leading surface-point counts are read as coordinates and
  produce a silently wrong airfoil. The upload route is the most likely place for
  a hand-supplied non-Selig file to enter the system. Should the parser sniff the
  format, or should non-Selig files be rejected explicitly?
- **Duplicate-upload behaviour is unspecified.** Does `POST /airfoils/datfile`
  with an existing stem replace, conflict with 409, or skip the way the directory
  import's case-insensitive dedup does?
- **The ASB-absent response shape for `/neuralfoil/analysis` is unknown.** The
  service returns `[]`; does the endpoint surface that as a 200 with an empty
  body, or map it to a 5xx?
- **The unclassified-airfoil case on `/geometry-stats` is unknown.** An airfoil
  imported but not yet classified has no `airfoil_geometry` row — 404 or a
  null-filled body?
- **`neuralfoil_cdcl_service` was only read at the module-summary level.** Its
  signature, call sites and relationship to `compute_airfoil_low_re` are
  unconfirmed, so this slice cannot be fully re-implemented from the spec alone.
- **The diagrams route is opaque.** Its rendering technology, output format, and
  whether it re-runs the sweep or reuses a cached result were not read.
- **The interactive result carries no model-size marker.** A `"large"` sweep and
  an `"xxxlarge"` stored polar can disagree, and nothing in the response explains
  why. Should the response echo the model size?
- **`/airfoils/db/{name}` and `/airfoils/db/suitability` ordering is
  unverified.** The two routes live in different slices; the declaration order
  between them must be pinned by a test.
