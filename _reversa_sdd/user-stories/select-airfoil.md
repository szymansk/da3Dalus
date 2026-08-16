# Selecting an Airfoil

> **Personas:** RC/UAV designer · Hobbyist · MCP-agent client
> **Modules:** `airfoil-catalog` (+ `suitability-search`, `neuralfoil-analysis`, `low-re-polar-backfill` slices)
> **Primary surface:** `/airfoils/...` (REST v2, mounted at the application root — the catalogue is aircraft-independent; no `/api/v2` segment)

## Context

Before a wing station can be finished, its airfoil must be chosen from a library of 1 665 Selig `.dat` sections, each with precomputed low-Reynolds polars over a 13-point absolute Re grid (40 k–750 k). Selecting an airfoil means ranking that library against a mission or an explicit operating CL, reading the honesty caveats the ranking always carries, optionally running an interactive NeuralFoil sweep on a shortlisted candidate, and — for a designer with their own section — uploading or bulk-importing new `.dat` files into the catalogue. Nothing in this module knows about a specific aeroplane's wing station; assigning the chosen airfoil to a station is `wing-design`'s job.

## US-AIRFOIL-01 — Rank candidate airfoils for a mission

**As an** RC/UAV designer, **I want** to rank the airfoil library for my chord and cruise speed against a named mission, **so that** I get a shortlist instead of manually comparing 1 665 sections.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| GET | `/airfoils/db/suitability` | ranked suitability query |

**Acceptance criteria**

- **AC-1 — A mission ranks by the mission lens automatically**
  - **Given** `chord_m = 0.25`, `speed_ms = 15`, `mission_type = "trainer"`
  - **When** I `GET /airfoils/db/suitability?chord_m=0.25&speed_ms=15&mission_type=trainer`
  - **Then** the response is **200** `SuitabilityResponse`; the query Reynolds number is computed as `Re = ρ·V·c/μ` (ρ=1.225 kg/m³, μ=1.81e-5 Pa·s) and echoed in `query.reynolds`; `active_lens` is `"mission"` because a `mission_type` resolved — the server picks the lens itself by priority `mission > target_cl_cruise > re_agnostic`, there is no `active_lens` request parameter; results are ranked using the trainer mission band (`t_min=11%`, `t_max=14%`, `cl_max_weight=0.70`, preferred families `flat_bottom`/`semi_symmetric`).
- **AC-2 — Out-of-range Reynolds is clamped, never extrapolated**
  - **Given** `chord_m` and `speed_ms` that compute to a query Re below `40 000`
  - **When** I run the same query
  - **Then** `query.reynolds` is clamped to `40000` and `query.re_clamped = true`.
- **AC-3 — Missing required parameters**
  - **Given** `chord_m` or `speed_ms` is omitted, or either is `≤ 0`
  - **When** I call the endpoint
  - **Then** the response is **422** `validation_error` (both fields require `gt=0.0`).

**Confidence:** 🟢 CONFIRMED

## US-AIRFOIL-02 — Narrow the field with family, role-tag and thickness filters

**As an** RC/UAV designer, **I want** to further filter the ranked list by airfoil family, role tag (e.g. `winglet`, `acro`) and thickness range, **so that** I only see sections that fit my structural and role constraints, without losing my mission ranking.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| GET | `/airfoils/db/suitability?family=...&tags=...&thickness_min_pct=...&thickness_max_pct=...&include=...&limit=...` | the same ranked query, filtered (gh-835) |

**Acceptance criteria**

- **AC-1 — Family and tag filters use OR-within-dimension, AND-across-dimensions**
  - **Given** `family=reflexed,cambered` and `tags=acro,winglet`
  - **When** I run the query
  - **Then** results include any airfoil whose family is `reflexed` **or** `cambered` **and** whose tags include `acro` **or** `winglet` — the two dimensions combine with AND; `thickness_min_pct` / `thickness_max_pct` are inclusive bounds on `max_thickness_pct` and combine as an additional AND with the other dimensions.
- **AC-2 — `include` guarantees named airfoils are scored even outside the top-N**
  - **Given** `include=s1223,ag35` and `limit=50`
  - **Then** `s1223` and `ag35` are scored and returned even if they would otherwise rank below the top 50 — but an included name with no low-Re polar rows is **not** fabricated a score; an old client that omits `include` sees identical behaviour to before the filter existed.
- **AC-3 — `limit` bounds the result set**
  - **Given** `limit=200` (the maximum) or `limit=0`
  - **When** I run the query
  - **Then** `limit=200` is accepted (`le=200`) and `limit=0` is rejected with **422** (`ge=1`).
- **AC-4 — Route-ordering hazard is avoided**
  - **Given** the literal path segment `suitability`
  - **When** I `GET /airfoils/db/suitability`
  - **Then** it resolves to the suitability query, **not** to `GET /airfoils/db/{name}` with `name="suitability"` — the suitability route must be declared first in the router (unverified from the declaration order itself, but consistent with observed behaviour).

**Confidence:** 🟢 CONFIRMED for the filter semantics; 🟡 INFERRED for AC-4 (declaration order was not read directly).

## US-AIRFOIL-03 — Trust the caveat before committing to an airfoil

**As a** Hobbyist with no aerodynamics background, **I want** the suitability response to tell me plainly when a top-ranked airfoil is untrustworthy or risks tip stall, **so that** I don't build a wing around a number I don't understand the limits of.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| GET | `/airfoils/db/suitability` | same ranked query; this story reads the caveat and per-item risk fields |

**Acceptance criteria**

- **AC-1 — The tip-stall caveat is always present**
  - **Given** any suitability response
  - **When** I inspect `caveat`
  - **Then** `ignores_tip_re_clmax_collapse` is **always `true`** — the score treats section CL as whole-wing CL (ideal, untwisted elliptic wing) and never models the tip-Reynolds CL_max collapse that governs real tip-stall onset — alongside `relative_ranking_only = true` (the scores rank, they do not predict) and a human-readable `text` summary.
- **AC-2 — A negative CL_max margin signals stall risk explicitly**
  - **Given** a target cruise CL of `1.4` and a candidate airfoil with `cl_max = 1.2`
  - **When** I read that item's `cl_max_margin`
  - **Then** it is `-0.2` — a negative value is the explicit stall-risk signal, not a value the caller must derive.
- **AC-3 — A confident, mediocre airfoil outranks an excellent but unreliable one**
  - **Given** airfoil A scores `0.95` in a low-confidence tier and airfoil B scores `0.80` in a high-confidence tier
  - **When** results are ranked
  - **Then** B precedes A — sorting is `(confidence tier, −score)`, confidence tier first.
- **AC-4 — A low-Reynolds tip is flagged**
  - **Given** a tip chord (`tip_chord_m`) whose Reynolds number is `70 000`
  - **When** the query resolves
  - **Then** `tip_re_flag = true` (`Re_tip < 80 000`, or a root→tip Re drop `> 50 000` — either condition fires it).
  - **And** `high_re` role tags are explicitly marked approximate in the module contract, since the underlying grid tops out at `750 000`.

**Confidence:** 🟢 CONFIRMED

## US-AIRFOIL-04 — Run an interactive NeuralFoil sweep on a candidate

**As an** RC/UAV designer, **I want** to run a fresh NeuralFoil alpha sweep on one shortlisted airfoil at Reynolds numbers of my choosing, **so that** I can see CL/CD/CM curves for exactly the conditions I care about, beyond the 13 precomputed grid points.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/airfoils/{airfoil_name}/neuralfoil/analysis` | interactive alpha × Re sweep |
| POST | `/airfoils/{airfoil_name}/neuralfoil/analysis/diagrams` | the same sweep, rendered as CL/CD/CM/polar diagram URLs |

**Acceptance criteria**

- **AC-1 — A sweep runs with sensible defaults**
  - **Given** an airfoil name that exists on the filesystem
  - **When** I `POST .../neuralfoil/analysis` with an empty body (all fields default: `reynolds_numbers = [10000, 30000, 50000, 100000, 200000, 500000]`, `alpha_start_deg = -10`, `alpha_end_deg = 16`, `alpha_step_deg = 1.0`, `model_size = "large"`)
  - **Then** the response is **200** with `alpha_deg` (the shared alpha grid) and one `reynolds_results` entry per requested Re, each carrying `cl`/`cd`/`cm`/`cl_over_cd`/`analysis_confidence` arrays plus `cl_max`, `alpha_at_cl_max_deg`, `cd_min`, `alpha_at_cd_min_deg`.
- **AC-2 — The interactive model size is deliberately smaller than the backfill's**
  - **Given** the same airfoil has precomputed polars from the overnight low-Re backfill (which uses `model_size = "xxxlarge"`)
  - **When** I run the interactive sweep at the default `model_size = "large"`
  - **Then** the two can legitimately disagree slightly — this is a documented, deliberate speed/fidelity trade ("do NOT collapse" is written directly into the backfill's docstring), not a bug; nothing in the interactive response marks which model size produced it, so a caller comparing the two has no in-band way to see why they differ.
- **AC-3 — Invalid alpha range is rejected**
  - **Given** `alpha_end_deg < alpha_start_deg`
  - **When** I call the endpoint
  - **Then** the response is **422** (the request schema's own validator rejects it before the sweep runs).
- **AC-4 — Unknown airfoil**
  - **Given** an airfoil name not present under `components/airfoils/`
  - **When** I call either the analysis or the diagrams endpoint
  - **Then** the response is **404** `not_found`.

**Confidence:** 🟢 CONFIRMED (verified directly against `app/api/v2/endpoints/airfoils.py`; this is a distinct, richer request/response contract than the backfill's `compute_airfoil_low_re` call, sharing only the underlying NeuralFoil model).

## US-AIRFOIL-05 — Upload a custom airfoil

**As a** Hobbyist with a hand-digitised or downloaded `.dat` file, **I want** to upload it directly, **so that** I can use my own section without editing server-side directories.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/airfoils/datfile` | multipart upload of one `.dat` file, filesystem-only |

**Acceptance criteria**

- **AC-1 — A new file is accepted**
  - **Given** a multipart upload with a `.dat`-suffixed filename and non-empty content, `overwrite` omitted (defaults `false`)
  - **When** I `POST /airfoils/datfile`
  - **Then** the response is **201** with `overwritten = false`, and the file is written under `components/airfoils/` — it now appears in `GET /airfoils` (the filesystem listing) but **not yet** in `GET /airfoils/db` (the database listing) until a subsequent directory import pulls it in.
- **AC-2 — Re-uploading the same name without `overwrite` is a conflict**
  - **Given** a file with that name already exists on disk
  - **When** I `POST` again with `overwrite` omitted or `false`
  - **Then** the response is **409** `conflict` — a status this route can return that the module's own route table only lists as 201/422/500.
- **AC-3 — Re-uploading with `overwrite=true` succeeds with 200, not 201**
  - **Given** the same existing file
  - **When** I `POST ?overwrite=true`
  - **Then** the response status is manually overridden to **200** (not the route's default 201) and `overwritten = true`.
- **AC-4 — Content is not structurally validated on this path**
  - **Given** a non-empty file whose content is **not** valid Selig-format coordinates (e.g. a Lednicer-format file, or arbitrary text)
  - **When** I upload it
  - **Then** the upload still succeeds — `_save_airfoil_dat` only checks that the filename ends in `.dat` and that the byte content is non-empty; it does **not** call the Selig parser used by the directory-import path. An empty file, a missing filename, or a non-`.dat` suffix are the only rejected cases, each **422** `validation_error`.

**Confidence:** 🟢 CONFIRMED (verified directly against `app/api/v2/endpoints/airfoils.py::_save_airfoil_dat` — this diverges from the module's general narrative that uploads "reuse the import parser"; the multipart route in the current code does not).

## US-AIRFOIL-06 — Import a directory of airfoils in bulk

**As an** RC/UAV designer with a folder of `.dat` files (e.g. from an OpenVSP import batch), **I want** to import the whole directory into the catalogue at once, **so that** every valid file becomes a ranked, searchable airfoil without uploading one at a time.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/airfoils/import` | recursive, idempotent directory import into the database |

**Acceptance criteria**

- **AC-1 — A batch of ten files, one corrupt, imports the other nine**
  - **Given** a directory of ten `.dat` files under `components/airfoils/`, one of which is malformed (fewer than 3 valid coordinate pairs)
  - **When** I `POST /airfoils/import` with `{"directory": "components/airfoils/my_batch"}`
  - **Then** the response is **200** `AirfoilImportResult` with `imported = 9`, `errors = 1`, and the corrupt filename listed in `error_files` — a per-file `try/except` rolls back only that file's insert and the loop continues.
- **AC-2 — Directory traversal is refused before any file is read**
  - **Given** a `directory` value that resolves outside `<project_root>/components`
  - **When** I call the endpoint
  - **Then** the response is **422** `validation_error`, raised before any file is opened.
- **AC-3 — Re-importing the same directory is idempotent**
  - **Given** a directory already fully imported
  - **When** I import it again
  - **Then** `skipped` equals the file count and `imported = 0` — matching is case-insensitive against existing names.
- **AC-4 — The canonical name is the file stem, matching the CadQuery lookup**
  - **Given** a file `mh60.dat` whose first line is a title header
  - **When** it is imported
  - **Then** the stored airfoil name is `"mh60"` (the file stem), not anything parsed from the header — this is the same convention the CadQuery plugin uses to resolve airfoils by name.

**Confidence:** 🟢 CONFIRMED

## US-AIRFOIL-07 — Check airfoil availability from an MCP agent

**As an** MCP-agent client, **I want** to check whether an airfoil name is known and upload a new one through MCP tools, **so that** I can prepare an airfoil before asking a wing-design tool to use it — while understanding that ranking and analysis are out of reach from this transport.

**Endpoints exercised** (MCP tools on the `da3dalus-cad-tools` server; only 2 of the airfoil module's REST routes have an MCP tool)

| Tool | Purpose |
|---|---|
| `is_airfoil_known(airfoil_name)` | boolean filesystem check |
| `upload_airfoil_datfile(file_name, dat_content, overwrite=False)` | upload by inline string content, not multipart |

**Acceptance criteria**

- **AC-1 — Known-check works identically to REST**
  - **Given** an airfoil name
  - **When** the agent calls `is_airfoil_known`
  - **Then** it gets the same boolean `GET /airfoils/{airfoil_name}/known` would return.
- **AC-2 — Upload takes inline content, not a file handle**
  - **Given** the agent has the `.dat` text as a string (it cannot attach a multipart file over MCP)
  - **When** it calls `upload_airfoil_datfile(file_name="my_wing.dat", dat_content="<selig text>")`
  - **Then** the tool delegates to `upload_airfoil_dat_content`, a distinct code path from the REST multipart handler, with the same empty-content → `ValidationError` and existing-name-without-overwrite → `ConflictError` behaviour.
- **AC-3 — Suitability search and NeuralFoil analysis are unreachable via MCP**
  - **Given** the agent needs to rank airfoils for a mission, or run an interactive NeuralFoil sweep
  - **When** it searches the 76-tool registry
  - **Then** it finds no tool for `/airfoils/db/suitability`, `/airfoils/db/{name}`, `/airfoils/{name}/geometry-stats`, `/airfoils/{name}/coordinates`, or either `neuralfoil/analysis` route — the MCP surface is frozen at a pre-copilot geometry/analysis core, and every airfoil-catalog capability added since (gh-821, gh-834, gh-835) has no tool. The agent must call these REST endpoints directly, outside the tool registry.

**Confidence:** 🟢 CONFIRMED (`app/mcp_server.py`; `mcp-server/contracts.md` tool inventory).

## Open questions 🔴

- Whether an airfoil present in `airfoils` but with no `airfoil_geometry` row (imported but not yet classified) makes `/geometry-stats` 404 or return nulls was not confirmed.
- Whether a duplicate `.dat` upload via the multipart route without `overwrite` is meant to be a hard conflict, or whether a softer skip-like behaviour (matching the directory import's dedup) was intended, is unconfirmed beyond the observed 409.
- Two settings modules (`app/settings.py` for scoring/backfill knobs, `app/core/config.py` for `AIRFOILS_DIR`) overlap in responsibility; which is the canonical configuration home is unresolved.
