# COTS Component Import & Reimport — Design

**Date:** 2026-06-15
**Status:** Design — awaiting review
**Related:** epic #199 (PropFinder / Data Ingestion Layer, Phase 1), #38 (Webscraping
für initiale Befüllung der Bauteildatenbank), #615 (Powertrain Performance Model —
consumes this data later)

## 1. Goal

Populate the parts catalog (`components` table) with real **motor and ESC** data so the
Powertrain sizing tools have actual components to match against, and make that data
**reimport-safe**: a versioned snapshot in the repo is the durable source of truth from
which the database can be rebuilt offline at any time.

First slice: **D-Power motors + ESCs**. Propellers (APC/UIUC) and batteries are explicit
follow-up slices reusing the same pipeline.

## 2. Decisions (from brainstorming, 2026-06-15)

| Topic | Decision | Rationale |
|---|---|---|
| Primary source | Manufacturer/open sources, **D-Power** for motors+ESCs first | User builds with these parts; published spec data; legitimate. |
| **eCalc** | **NOT a scrape target** | Proprietary/unpublished; ToS forbids extraction; contradicts #615. eCalc only as UX inspiration. |
| Data depth | Scalar **metadata into DB now**; raw propeller polars saved (not DB) in a later slice | Current `specs` JSON holds scalars only; `C_T(J)`/`C_P(J)` need the #199 model. |
| Snapshot storage | **Factual numbers as JSON committed to the (public) repo** = reimport source | Reproducible, offline, versioned. |
| Drawings/images | **Local, gitignored**; DB stores only `model_ref`/`source_url` | Technical drawings are copyrighted — do not re-host in the public repo. |
| Crawl by Claude | **Claude does NOT bulk-crawl D-Power** | robots.txt disallows ClaudeBot + `ai-train=no`. Parser developed against user-provided sample HTML. |
| URL discovery | Derive product links from **category index pages** (paginated), persisted to a versioned list before detail fetch | User chose breadth; mitigated by persisting/reviewing the URL list and a polite-crawl policy. |
| Pipeline shape | **Two stages**: scrape → versioned JSON snapshot → idempotent importer → DB | Snapshot decouples fragile online scrape from offline, CI-able import. |

## 3. Architecture

Two decoupled stages, mirroring the proven `scripts/backfill_airfoil_low_re.py` pattern.

```
[user] category URLs ─┐
                      ▼
            scrape_dpower.py ──► data/cots/dpower_sources.txt  (discovered product URLs, versioned)
                      │
                      ├──► data/cots/dpower.json               (factual snapshot — REIMPORT SOURCE, committed)
                      └──► components/cots-assets/dpower/…      (drawings/images — gitignored, local only)

            import_cots.py / cots_import.py
                      │  read snapshot → validate vs component_type schema → upsert by (manufacturer, name)
                      ▼
              components table  (single commit, Result report: imported/updated/skipped/errors)
```

### 3.1 New files

| File | Purpose | Template |
|---|---|---|
| `scripts/scrape_dpower.py` | Polite scraper+parser. Discovers product URLs from configured category index pages, persists them to `dpower_sources.txt`, fetches+parses each, updates the snapshot, downloads drawings locally. **Manual trigger only.** | — |
| `data/cots/dpower_sources.txt` | Versioned list of discovered product URLs (reviewable before detail fetch). | — |
| `data/cots/dpower.json` | Versioned factual snapshot = **reimport source**. | `components/airfoils/` precedent |
| `app/services/cots_import.py` | Pure import logic: snapshot dict → validate → upsert by `(manufacturer, name)`. Reusable in CLI + tests. | `backfill_airfoil_low_re.py` |
| `scripts/import_cots.py` | Thin CLI around the service (`--force` updates existing). | airfoil CLI |
| `components/cots-assets/` | Downloaded drawings/images (gitignored). | — |
| alembic migration | Additively extend `brushless_motor` + `esc` `component_type` schemas (see §5). | mission-preset migration |

### 3.2 Snapshot format

One JSON list; `component_type` per record.

```json
[
  {
    "manufacturer": "D-Power",
    "name": "AL 42-06",
    "component_type": "brushless_motor",
    "mass_g": 120,
    "bbox_x_mm": 42, "bbox_y_mm": 42, "bbox_z_mm": 36,
    "model_ref": "dpower/al-42-06",
    "source_url": "https://www.d-power-modellbau.com/...",
    "source_version": "scraped 2026-06-15",
    "specs": {
      "kv_rpm_per_volt": 670,
      "max_current_a": 45,
      "continuous_current_a": 40,
      "cells_lipo_min": 3,
      "cells_lipo_max": 4,
      "efficiency_pct": 81
    }
  }
]
```

## 4. Data flow & idempotency

- **Upsert key:** `(manufacturer, name)` — re-running the importer on an updated snapshot
  updates existing rows instead of duplicating. Default run skips unchanged; `--force`
  overwrites all fields.
- **Single transaction:** the importer collects all changes and commits once (airfoil
  pattern), so a failure leaves the DB untouched.
- **Result report:** `imported / updated / skipped / errors` returned by the service and
  printed by the CLI.
- **Rebuild guarantee:** dropping all D-Power rows and re-running the importer on the
  committed snapshot reproduces the catalog exactly — no network needed.

## 5. Schema reconciliation (friction found during design)

A pre-existing inconsistency must be resolved for the data to be usable:

- `brushless_motor` seed schema today: `kv_rpm_per_volt`, `max_current_a`,
  `shaft_diameter_mm`.
- The solver (`powertrain_solution_space_service`) reads `max_power_w` /
  `max_continuous_power_w` (motor) and `max_current_a` / `continuous_current_a` (ESC).
- D-Power publishes: KV, efficiency %, peak/continuous current, LiPo cell range,
  weight, dimensions — **but not `Rm`/`Io`** (those belong to the #615 3-parameter motor
  model and stay out of scope here).

**Action:** additively extend the `brushless_motor` and `esc` `component_type` schemas to a
superset that (a) matches what D-Power provides and (b) uses the field names the solver
reads. Additive only — existing components stay valid because `specs` is a JSON column.
Implemented via a new Alembic migration plus an update to `seed_default_types`
(component types are seeded in both places by convention).

Proposed additions:
- `brushless_motor`: `max_power_w`, `max_continuous_power_w`, `continuous_current_a`,
  `cells_lipo_min`, `cells_lipo_max`, `efficiency_pct` (keep existing fields).
- `esc`: `continuous_current_a`, `cells_lipo_min`, `cells_lipo_max` (keep `max_current_a`).

## 6. Crawl policy (responsible scraping)

- **Manual trigger only** — Claude does not run the bulk scrape. Claude develops the
  parser against 1–2 sample HTML pages the user provides.
- Discover only the relevant **category index pages** (paginated); no whole-site
  spidering. Persist discovered URLs to `dpower_sources.txt` for review before detail fetch.
- Skip robots.txt-disallowed directories (`/administrator/`, `/images/`, …).
- Rate-limit (~1 request / 2–3 s), honest descriptive User-Agent, honor HTTP
  errors / `Retry-After`, cache responses.
- `ai-train=no` is respected: the data is used to build the user's personal parts
  catalog, not for model training.

## 7. Error handling

- **Scraper:** unparseable product page → logged warning, record skipped, no partial
  write. Snapshot is written atomically (temp file + rename).
- **Importer:** each record validated against its `component_type` schema; invalid records
  collected into `errors` and reported; valid records still committed (one transaction).

## 8. Testing (target >80%)

- `app/tests/test_cots_import.py` — pure import logic against fixture JSON + in-memory DB:
  happy path, validation failure, **idempotency** (run twice → no duplicates), `--force`
  update.
- `app/tests/test_scrape_dpower.py` — parser against saved sample HTML fixtures (the
  user-provided pages). **No network in tests.**
- URL-discovery parser tested against a saved sample category-index HTML.

## 9. Out of scope (explicit)

- Propeller performance polars `C_T(J)`/`C_P(J)` and the #199 Performance-Dataset/Fit-Model
  tables (later slice — raw polars only *saved* then, not modeled).
- 3-parameter motor model (`Rm`, `Io`) and motor/prop performance curves (#615).
- Batteries and propellers (follow-up slices on the same pipeline).
- A REST bulk-import endpoint (single-item `POST /components` already exists; seeding is
  CLI-driven).
- eCalc integration of any kind.

## 10. Follow-up slices (same pipeline)

1. Propellers via **APC** (`PER3_*.dat`, license-free) + **UIUC** — metadata into DB,
   raw polar files saved to the snapshot store for the future fit model.
2. Batteries (D-Power / manufacturer data).
3. (Later, #199/#615) Performance-Dataset + Fit-Model tables consuming the saved raw polars.
