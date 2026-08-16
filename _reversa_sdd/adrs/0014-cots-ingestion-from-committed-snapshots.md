# ADR 0014 — COTS data is ingested from committed snapshots, never from a live source

- **Status:** Accepted — in force
- **Decided:** 2026-06/07 across gh-986, gh-995, gh-999, gh-1000, gh-1012
- **Deciders:** Marc Szymanski (maintainer)
- **Confidence:** 🟢 CONFIRMED (pipeline, committed artefacts, CLI scripts); the *licensing* rationale is 🟡 (project memory, not in-repo)

## Context

Without real hardware data — motor KV and no-load current, propeller thrust and
power coefficients, battery capacity and C-rate, material allowable stress — the
powertrain model, the endurance estimate and the spar sizer all reduce to guesses.
That data lives on vendor sites and in vendor PDFs. Three constraints shaped the
approach: **legal/ethical scope** (eCalc is explicitly off-limits and the D-Power
catalogue was to be used without crawling); **reproducibility** (the APC PER3
archive is ~58 MB of `.dat` plus 455 `.PE0` files, so a build that fetches them is
neither reproducible nor offline-capable); and **volume**.

## Decision

**The durable, version-controlled source of truth is a *committed snapshot*. Raw
vendor files are gitignored and never required; the network is never touched at
import time.**

```
data/apc_raw/**/PER3_*.dat        (gitignored, ~58 MB — the raw archive)
        │  scripts/parse_apc_props.py
        ▼
data/cots/apc_props.json.gz       (COMMITTED, ~8 MB, 454 props — the reimport source)
        │  scripts/enrich_apc_snapshot_pe0.py     (+ PE0 weight / inertia / geometry)
        ▼
        │  scripts/import_apc_props.py → prop_polar_import.import_prop_polars
        ▼
propeller_polars + propeller_polar_samples
        │  scripts/seed_propeller_components.py → prop_component_seed
        ▼
components (component_type = 'propeller', keyed on model_ref)
```

The same shape applies to `data/cots/{dpower, spektrum_avian, carbon_tubes,
hoellein_wood, generic_batteries}`.

1. **Parse from the data, not the filename.** Diameter, pitch and variant come from
   **header line 1** of the PER3 file — the only way to read `PER3_105x45` as
   10.5 × 4.5 in and to catch variant suffixes. Filename parsing is a logged
   fallback.
2. **Keep SI, discard imperial.** Only `PWR` (W), `Torque` (N·m), `Thrust` (N) and
   the dimensionless `J, Pe, Ct, Cp` are retained.
3. **`model_ref` is the join key** between polar and component:
   `"apc/<designation>"` with `.` → `p` (`10.5x4.5` → `apc/10p5x4p5`).
4. **Import is an idempotent upsert with a freshness proxy.** `_records_equal`
   compares `source_version`, `source_url`, `variant`, and "the row lacks
   `weight_g` but the snapshot has one" — **not** deep equality. *If the vendor
   corrects data without bumping `source_version`, the change is skipped; run with
   `force=True`.* Samples are deleted and re-inserted wholesale.
5. **Implausible values are rejected, not written.** `MIN_PLAUSIBLE_WEIGHT_G = 1.0`
   treats a sub-gram propeller weight as a kg→g conversion error and counts it in
   `unit_warnings`. Unmatched PE0 rows are logged, never dropped silently.
6. **User-entered mass always wins.** `mass_g` is populated from `weight_g` on
   create, a **NULL** `mass_g` is backfilled when the polar later gains a weight,
   and a **non-null** `mass_g` is never clobbered.
7. **Reimport is an operator action, not an API.** There is no HTTP endpoint. After
   merging an importer PR, run the matching reimport **and restart the backend** —
   *"migrations move keys, reimport moves values"*.

## Consequences

- Fully offline and reproducible; provenance is in Git, so a catalogue change is a
  reviewable diff; the snapshot is small enough to commit while the raw archive
  stays out; vendor terms are respected.
- **Data goes stale silently** — no freshness check, no "last synced" surface, no
  alert — and the freshness proxy can skip real corrections.
- **Reimport is a manual, easily forgotten step**, which is why the operational
  rule had to be written down.
- **Binary-ish artefacts live in Git** — `apc_props.json.gz` regenerates as a
  full-file diff.
- 🔴 **Path-filtered CI skips the lint/fast job for scripts-only changes**, so
  unlinted parser code can land on `main` and break the next PR's fast job.
- The pipeline is multi-stage and undocumented outside the scripts themselves.

**Rejected:** scraping vendor sites at import time (legal/ethical grounds for the
sources in question, plus non-reproducible imports); fetch-on-first-use with a cache
(reintroduces the network dependency and breaks the offline Docker build).

## Related

[ADR 0013](0013-one-components-table-with-a-data-driven-type-schema.md) ·
[ADR 0015](0015-tiered-ci-fast-full-nightly.md) (the scripts-only lint skip) ·
domain rules BR-62 … BR-66.
Evidence: commits `9c9e6b2b` (gh-999), `8a80f723` (gh-995), `f8bb248a` (gh-1000);
project memories `project_cots_data_ingestion`,
`feedback_reimport_after_importer_merge`.
