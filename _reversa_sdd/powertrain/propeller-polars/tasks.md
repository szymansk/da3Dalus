# propeller-polars — Implementation Tasks

> Executable sequence to re-implement the use case from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker. Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `components` table + the `propeller` seeded type — see
      [`../cots-powertrain-components/tasks.md`](../cots-powertrain-components/tasks.md)
      T-01, T-05. The mirror (T-08 below) writes into it.
- [ ] `get_db()` session for the service path; the CLIs manage their own session
      and commit once at the end (ADR 0009 applies to the request path only).
- [ ] The committed snapshot `data/cots/apc_props.json.gz`. The gitignored
      `data/apc_raw/**/PER3_*.dat` is needed **only** to regenerate it (T-03).
- [ ] APC PE0 files for the enrichment stage (T-04) — likewise only for
      regeneration.

## Tasks

- [ ] **T-01 — `propeller_polars` header table.**
  `manufacturer` (indexed), `name` (indexed), `model_ref`, `source_url`,
  `source_version`, `diameter_in`, `pitch_in` (**inches**), `variant`
  (default `""`), `blades` (default `2`), `weight_g` (**grams**),
  `inertia_kg_m2`, `geometry` (JSON), timestamps. Relationship `samples` with
  `cascade="all, delete-orphan"`.
  - Legacy origin: `app/models/prop_polar.py:21`
  - Definition of done: deleting a header removes its samples in one operation;
    `variant` defaults to the empty string, not `NULL`.
  - Confidence: 🟢

- [ ] **T-02 — `propeller_polar_samples` table.**
  `propeller_id` (FK, indexed), `rpm` (indexed), `J`, `Ct`, `Cp` (required),
  `Pe`, `PWR_W`, `Torque_Nm`, `Thrust_N` (nullable). Carry the physics
  definitions in the model docstring.
  - Legacy origin: `app/models/prop_polar.py:71-82`
  - Definition of done: `Pe` is nullable; the docstring states
    `J = V/(n·D)`, `Ct = T/(ρn²D⁴)`, `Cp = P/(ρn³D⁵)`, `Pe = Ct·J/Cp`.
    Reproduce the **absence** of a unique constraint on `(propeller_id, rpm, J)`
    and record it as a gap.
  - Confidence: 🟢

- [ ] **T-03 — The PER3 parser.**
  Geometry from **header line 1**, filename only as a logged fallback; SI
  columns at `J=1, Pe=2, Ct=3, Cp=4, PWR_W=8, Torque_Nm=9, Thrust_N=10`; rows
  with `< 11` fields skipped; blades from `_BLADE_COUNT_RE = -([3-9])$` on the
  **variant** with `DEFAULT_BLADES = 2`; `model_ref = "apc/" +
  designation.replace(".", "p")`.
  - Legacy origin: `scripts/parse_apc_props.py:162-168, 302-304`
  - Definition of done: a fixture table covering `105x45` (⇒ 10.5 × 4.5),
    `10x10E` (variant `E`, 2 blades), `10x10M-JK` (variant `M-JK`, **2**
    blades), `10x10E-3` (3 blades), a 10-field row (skipped) and a header-less
    file (fallback + log).
  - Confidence: 🟢

- [ ] **T-04 — PE0 enrichment with the kg→g guard.**
  Match on `(diameter, pitch, variant)`; write `weight_g` (PE0 reports kg —
  normalise), `inertia_kg_m2` (PE0's own unit, unconverted) and the per-station
  `geometry`; reject `weight_g < MIN_PLAUSIBLE_WEIGHT_G = 1.0` into
  `unit_warnings`; log unmatched records.
  - Legacy origin: `app/services/prop_polar_enrich.py:29`
  - Definition of done: a 0.043 g parse is counted and **not** written; an
    unmatched record is logged and the run still completes; the matcher uses
    geometry, not the filename.
  - Confidence: 🟢

- [ ] **T-05 — `import_prop_polars` — the upsert.**
  Reject `component_type != "propeller"` into `ImportResult.errors`; upsert the
  header on `(manufacturer, name)`; count `imported` / `updated` / `skipped`.
  - Legacy origin: `app/services/prop_polar_import.py`
  - Definition of done: 454 records import into 454 headers; a re-import creates
    no duplicates; a battery record lands in `errors` and the run continues.
  - Confidence: 🟢

- [ ] **T-06 — `_records_equal`, the freshness proxy.**
  Compare `source_version`, `source_url`, `variant`, and the case *"the row
  lacks `weight_g` but the snapshot has one"*. **Do not** compare samples.
  Carry the limitation in the docstring and honour `force=True`.
  - Legacy origin: `app/services/prop_polar_import.py`
  - Definition of done: four tests — unchanged ⇒ skipped; bumped version ⇒
    updated; changed samples with an unchanged version ⇒ **skipped** (this test
    *documents* the limitation); `force=True` ⇒ updated.
  - Confidence: 🟢

- [ ] **T-07 — `_upsert_samples` — delete-all then re-insert.**
  No per-sample diff.
  - Legacy origin: `app/services/prop_polar_import.py`
  - Definition of done: re-importing a propeller whose sample count drops from
    120 to 80 leaves exactly 80 rows; a skipped record's samples are **not**
    touched (assert with a query counter, since deleting them would be an
    expensive no-op).
  - Confidence: 🟢

- [ ] **T-08 — `seed_propeller_components` — the mirror.**
  Idempotent on `(component_type='propeller', model_ref)`; skip polars without
  a `model_ref`; `_specs_from_polar` writes `diameter_in`, `pitch_in`, `blades`
  and `variant`. Three mass rules: populate from `weight_g` on create; backfill
  a **NULL** `mass_g`; **never** clobber a non-null one.
  - Legacy origin: `app/services/prop_component_seed.py`
  - Definition of done: one test per mass rule, plus an idempotence test. A test
    must fail if a user-edited 41.0 g is replaced by the polar's 43.3 g.
  - Confidence: 🟢

- [ ] **T-09 — Characterise the two mirror deviations.**
  The seed writes `ComponentModel` rows **directly**, bypassing
  `validate_specs`, and writes `specs["variant"]`, which the `propeller` schema
  does not declare.
  - Legacy origin: `app/services/prop_component_seed.py` vs
    `component_type_service.py:240-271`
  - Definition of done: a test creates a polar with a NULL `diameter_in`, runs
    the seed, and asserts (a) the component **is** created and (b) a subsequent
    API `PUT` of that component returns **422**. The test's docstring names the
    gap; do not fix it here.
  - Confidence: 🟢

- [ ] **T-10 — The three reimport CLIs.**
  `scripts/import_apc_props.py` (snapshot → tables),
  `scripts/seed_propeller_components.py` (tables → components), and the
  regeneration pair `parse_apc_props.py` / `enrich_apc_snapshot_pe0.py`.
  Each commits once at the end.
  - Legacy origin: the four scripts
  - Definition of done: each CLI is idempotent across two runs and opens **no**
    socket (assert with a socket guard). Running the import before the seed is
    the required order — the seed reads the polars.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Parser matrix:** `105x45` · `10x10E` · `10x10M-JK` ·
      `10x10E-3` · `10x10-4` · short row · header-less file.
- [ ] **TT-02 — `model_ref` slug:** `10.5x4.5` ⇒ `apc/10p5x4p5`; a
      designation without a decimal point is unchanged.
- [ ] **TT-03 — SI-only columns:** the imperial values in the source row never
      appear in any stored column.
- [ ] **TT-04 — Import counts:** `imported + updated + skipped + len(errors)`
      equals the record count.
- [ ] **TT-05 — Non-propeller rejection:** the record is in `errors`, no header
      is written, and the run continues to the next record.
- [ ] **TT-06 — Freshness proxy matrix:** unchanged · bumped `source_version` ·
      changed `source_url` · gained `variant` · gained `weight_g` · changed
      samples only (**skipped**) · `force=True`.
- [ ] **TT-07 — Sample replacement:** count changes correctly; a skipped record
      issues no DELETE.
- [ ] **TT-08 — Cascade:** deleting a header removes its samples.
- [ ] **TT-09 — PE0 guard:** sub-gram rejected + counted; a plausible weight
      written; an unmatched record logged.
- [ ] **TT-10 — Mirror mass rules:** create-from-`weight_g` · NULL backfill ·
      non-null preserved · idempotent re-run · polar without `model_ref` skipped.
- [ ] **TT-11 — Mirror deviation (characterisation):** a NULL-geometry polar
      yields a component that 422s on its first `PUT`.
- [ ] **TT-12 — Offline guard:** every CLI opens no socket.
- [ ] **TT-13 — Round-trip:** parse a fixture `.dat` → snapshot → import →
      seed, and assert the resulting component's `specs` match the source file's
      header values.
- [ ] **TT-14 — Interpolation input sanity:** after an import, every
      propeller's samples are sortable by `J` within each `rpm` group with no
      duplicate `(rpm, J)` pair — this is the guard the missing unique
      constraint does not provide.

## Data Migration Tasks

- [ ] **TM-01 — Initial import** of `data/cots/apc_props.json.gz` via
      `scripts/import_apc_props.py` (454 propellers).
- [ ] **TM-02 — Mirror into components** via
      `scripts/seed_propeller_components.py`. Must run **after** TM-01.
- [ ] **TM-03 — Backfill `variant` on pre-gh-999 rows** — automatic, because
      `_records_equal` compares `variant` and therefore forces an update for
      rows that predate the field.
- [ ] **TM-04 — Backfill `weight_g` / `inertia_kg_m2` on pre-gh-1000 rows** —
      automatic, via the "row lacks `weight_g` but the snapshot has one" clause.
- [ ] **TM-05 — Backfill `components.mass_g` (gh-1017)** for propeller
      components whose mass is still `NULL`, **never** overwriting a non-null
      value. This is TM-02's second rule, so re-running the seed is the
      migration.
- [ ] **TM-06 — After any of the above, restart the API.** Module-level state in
      the importer path is not covered by `uvicorn --reload`.

## Suggested Order

1. **T-01 → T-02** — the two tables. They are the contract every later stage
   writes into.
2. **T-03** next: the parser is a pure function over a text file and carries
   three of the use case's four "easy to get subtly wrong" rules (header
   geometry, blade regex, `model_ref` slug). Pin it with fixtures before
   anything touches the database.
3. **T-04** — PE0 enrichment operates on the snapshot, not the database, so it
   can be built and tested entirely offline alongside T-03.
4. **T-05 → T-07** the importer, in that order: the upsert first, then the
   freshness proxy (which only decides *whether* to run the upsert), then the
   sample replacement.
5. **T-08 → T-09** the mirror, which needs both the polars (T-05) and the
   `components` table from the sibling use case.
6. **T-10** last — the CLIs are thin wrappers, and their idempotence test is the
   end-to-end proof of everything above.

## Pending Gaps (🔴)

- **Should the reimport detect data drift?** `_records_equal` compares metadata
  only, so a corrected polar with an unchanged `source_version` is skipped. A
  content hash of the sample block would close it — at the cost of parsing every
  record on every run.
- **Should `(propeller_id, rpm, J)` carry a unique constraint**, or is
  delete-then-insert the intended protection?
- **Should the mirror go through `validate_specs`**, so it cannot create
  components that violate the `propeller` schema?
- **Should `variant` be declared** in the `propeller` type schema?
- **Should skipped records be enumerated** in `ImportResult`, so a stale import
  is auditable rather than only countable?
- **Should the snapshot be checksummed?** A hand-edited `apc_props.json.gz`
  imports without complaint.
- **Should `inertia_kg_m2` get a plausibility guard** like the 1 g weight floor?
- **Should short/malformed rows be counted per file**, so a systematically
  broken source looks like an error rather than a smaller propeller?
- **Who owns `Torque_Nm` / `Thrust_N`?** They are stored, never used, and their
  presence invites a future consumer to read the low-precision column the
  physics deliberately avoids.
</content>
