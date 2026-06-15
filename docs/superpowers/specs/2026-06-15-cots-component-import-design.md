# COTS Component Import & Reimport — Design

**Date:** 2026-06-15
**Status:** Design — awaiting review
**Related:** epic #199 (PropFinder / Data Ingestion Layer, Phase 1), #38 (initiale Befüllung
der Bauteildatenbank), #615 (Powertrain Performance Model — consumes this data later)

## 1. Goal

Populate the parts catalog (`components` table) with real **motor and ESC** data so the
Powertrain sizing tools have actual components to match against, and make that data
**reimport-safe**: a versioned snapshot in the repo is the durable source of truth from
which the database can be rebuilt offline at any time.

First slice: **D-Power motors + ESCs**, ingested from official **PDF datasheets** the user
provides. Propellers (APC/UIUC) and batteries are explicit follow-up slices reusing the
same importer.

## 2. Decisions (from brainstorming, 2026-06-15)

| Topic | Decision | Rationale |
|---|---|---|
| Primary source | **Official D-Power PDF datasheets** (user-provided manuals) for motors+ESCs | Clean structured tables; user owns/uses these parts; no crawling needed. |
| Web scraping | **Dropped for this slice** | The PDFs cover the catalog; avoids robots.txt/ClaudeBot/`ai-train=no` concerns entirely. Category-page crawl may return as a *later* option for parts not published as PDF. |
| **eCalc** | **Never a source** | Proprietary/unpublished; ToS forbids extraction; contradicts #615. |
| Data depth | Scalar **metadata into DB now**; raw propeller polars saved (not DB) in a later slice | `specs` JSON holds scalars only; `C_T(J)`/`C_P(J)` need the #199 model. |
| Snapshot storage | **Factual numbers as JSON committed to the (public) repo** = reimport source | Facts are not copyrightable; reproducible, offline, versioned. |
| Source PDFs & drawings | **Local, gitignored**; never committed to the public repo | D-Power PDFs are copyrighted ("Jeder Nachdruck bedarf Genehmigung"). DB stores only `model_ref`/`source_url`. |
| Pipeline shape | **Two stages**: PDF parse → versioned JSON snapshot → idempotent importer → DB | Snapshot decouples the (manual, local) extraction from the offline, CI-able import. |

## 3. Source data inventory (the 5 provided PDFs)

Local source PDFs (gitignored; user-provided, currently in `~/Downloads/`):

| PDF | Type | Parts | Fields available |
|---|---|---|---|
| `V3_AL-Manual_print_A5_Max.pdf` | `brushless_motor` | ~23 (AL 28-… / 35-… / 42–80) | name, dims (Ø×L), **KV**, shaft mm, LiPo range, **Io** (Leerlaufstrom), continuous A (empf.), **peak A** (kurzz.), weight, thrust, Art.-Nr., prop recommendations per cell |
| `D-Drive-Manual.pdf` | `brushless_motor` (geared) | IL36 3.7:1, IL36 5:1 (+ IL28 variants on site) | shaft, weight, dims, gearbox dims, KV, peak A, recommended A, η%, LiPo range, prop+thrust per cell, Art.-Nr., **gear ratio** |
| `Avicon Anleitung_web.pdf` | `esc` | 7 (20–100 A) | PN, cont./burst A, cell range (NiXX/LiPo), weight, BEC output, dims, programmable |
| `Avicon PRO Anleitung_web.pdf` | `esc` | 3 (65/125/130 A HV) | PN, cont./burst A, input-voltage cells, weight, BEC, dims |
| `manual_Antares_V3.pdf` | `esc` | 9 (6–150 A; BEC/SBEC/OPTO) | name, cont./burst A, LiPo/NiXX cells, weight, BEC output, dims |

≈ **25 motors + 19 ESCs** from these five documents.

## 4. Architecture

Two decoupled stages, mirroring the proven `scripts/backfill_airfoil_low_re.py` pattern.

```
[user-provided] D-Power PDF datasheets  (local, gitignored)
                      │
            parse_dpower_pdfs.py  (pdfplumber table extraction; manual, local run)
                      │
                      └──► data/cots/dpower.json   (factual snapshot — REIMPORT SOURCE, committed)

            import_cots.py / cots_import.py
                      │  read snapshot → validate vs component_type schema → upsert by (manufacturer, name)
                      ▼
              components table   (single commit, Result report: imported/updated/skipped/errors)
```

### 4.1 New files

| File | Purpose | Template |
|---|---|---|
| `scripts/parse_dpower_pdfs.py` | Parse the provided D-Power PDFs (per-document table extractors) → write/refresh `data/cots/dpower.json`. Manual, local run. | — |
| `data/cots/dpower.json` | Versioned factual snapshot = **reimport source**. | `components/airfoils/` precedent |
| `app/services/cots_import.py` | Pure import logic: snapshot dict → validate → upsert by `(manufacturer, name)`. Reusable in CLI + tests. | `backfill_airfoil_low_re.py` |
| `scripts/import_cots.py` | Thin CLI around the service (`--force` updates existing). | airfoil CLI |
| `components/cots-assets/dpower/manuals/` | The source PDFs (gitignored). | — |
| alembic migration | Additively extend `brushless_motor` + `esc` `component_type` schemas (see §6). | mission-preset migration |

### 4.2 Snapshot format

One JSON list; `component_type` per record. Fields not in a datasheet are omitted/null.

```json
[
  {
    "manufacturer": "D-Power",
    "name": "AL 42-06",
    "component_type": "brushless_motor",
    "mass_g": 199,
    "bbox_x_mm": 42, "bbox_y_mm": 42, "bbox_z_mm": 40,
    "model_ref": "dpower/al-42-06",
    "source_url": "https://www.d-power-modellbau.com/...",
    "source_version": "AL manual 01/2021",
    "specs": {
      "kv_rpm_per_volt": 540,
      "io_no_load_a": 1.5,
      "continuous_current_a": 40,
      "max_current_a": 45,
      "cells_lipo_min": 3,
      "cells_lipo_max": 6,
      "shaft_diameter_mm": 5.0,
      "static_thrust_g": 3500,
      "art_no": "AL4206"
    }
  }
]
```

## 5. Data flow & idempotency

- **Upsert key:** `(manufacturer, name)` — re-running the importer on an updated snapshot
  updates existing rows instead of duplicating. Default run skips unchanged; `--force`
  overwrites all fields.
- **Single transaction:** the importer collects all changes and commits once (airfoil
  pattern), so a failure leaves the DB untouched.
- **Result report:** `imported / updated / skipped / errors` returned by the service and
  printed by the CLI.
- **Rebuild guarantee:** dropping all D-Power rows and re-running the importer on the
  committed snapshot reproduces the catalog exactly — no network, no PDFs needed.

## 6. Schema reconciliation (friction found during design)

A pre-existing inconsistency must be resolved for the data to be usable:

- `brushless_motor` seed schema today: `kv_rpm_per_volt`, `max_current_a`,
  `shaft_diameter_mm`.
- The solver (`powertrain_solution_space_service`) reads `max_power_w` /
  `max_continuous_power_w` (motor) and `max_current_a` / `continuous_current_a` (ESC).
- D-Power datasheets publish **currents + cell range** (and KV, Io, weight, dims, thrust)
  — **not power and not `Rm`**.

**Action:** additively extend the `brushless_motor` and `esc` `component_type` schemas to a
superset matching what D-Power provides, using the solver's field names where they overlap.
Additive only — existing components stay valid because `specs` is a JSON column. Implemented
via a new Alembic migration plus an update to `seed_default_types` (component types are
seeded in both places by convention).

Proposed additions:
- `brushless_motor`: `continuous_current_a`, `io_no_load_a`, `cells_lipo_min`,
  `cells_lipo_max`, `static_thrust_g`, `art_no` (keep existing fields); `max_power_w` /
  `max_continuous_power_w` added as **optional** (left null for D-Power).
- `esc`: `continuous_current_a`, `cells_lipo_min`, `cells_lipo_max`, `bec_output`,
  `art_no` (keep `max_current_a`).

**Modeling note (follow-up, not this slice):** D-Power gives currents, not `max_power_w`.
Store currents faithfully and leave power fields null. A small **solver follow-up** should
let `powertrain_solution_space_service` derive power from `max_current_a × representative
pack voltage` (or read currents directly) when power fields are absent. Tracked separately,
out of scope here.

## 7. Source documents & copyright

- The D-Power PDFs are **copyrighted** and kept **local/gitignored**
  (`components/cots-assets/dpower/manuals/`) — never committed to the public repo.
- Only the **factual extracted numbers** are committed (`data/cots/dpower.json`).
- Parsing runs **locally and manually** (not in CI; CI runs only the importer against the
  committed JSON snapshot).
- (No website crawling in this slice → no robots.txt / `ai-train` interaction.)

## 8. Error handling

- **PDF parser:** unparseable row/table → logged warning, record skipped, no partial write.
  Snapshot written atomically (temp file + rename). Per-document extractors so one bad PDF
  doesn't fail the others.
- **Importer:** each record validated against its `component_type` schema; invalid records
  collected into `errors` and reported; valid records still committed (one transaction).

## 9. Testing (target >80%)

- `app/tests/test_cots_import.py` — pure import logic against fixture JSON + in-memory DB:
  happy path, validation failure, **idempotency** (run twice → no duplicates), `--force`
  update.
- `app/tests/test_parse_dpower_pdfs.py` — parser against the provided PDFs (or small saved
  page fixtures) asserting a few known rows (e.g. AL 42-06: KV 540, Io 1.5 A, peak 45 A,
  199 g; Avicon 60 A: 60/80 A, 50 g). **No network in tests.**
- Validate the committed `data/cots/dpower.json` against the extended schemas in a test.

## 10. Out of scope (explicit)

- Website crawling of d-power-modellbau.com (dropped; PDFs suffice for this slice).
- Propeller performance polars `C_T(J)`/`C_P(J)` and the #199 Performance-Dataset/Fit-Model
  tables (later slice; raw polars only *saved* then, not modeled).
- 3-parameter motor model (`Rm`) and performance curves (#615); current→power solver
  follow-up (tracked separately, see §6).
- Batteries and propellers (follow-up slices on the same importer).
- A REST bulk-import endpoint (single-item `POST /components` already exists; seeding is
  CLI-driven).
- eCalc integration of any kind.

## 11. Follow-up slices (same importer)

1. Propellers via **APC** (`PER3_*.dat`, license-free) + **UIUC** — metadata into DB, raw
   polar files saved to the snapshot store for the future fit model.
2. Batteries (D-Power / manufacturer datasheets).
3. Solver follow-up: consume current-based motor specs / derive power (§6).
4. (Later, #199/#615) Performance-Dataset + Fit-Model tables consuming the saved raw polars.
5. (Optional) website category-page importer for parts not published as PDF.
