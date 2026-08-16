# propeller-polars

> Use-case specification, nested under the module
> [`powertrain`](../requirements.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Sources: `app/models/prop_polar.py`, `app/services/prop_polar_import.py`,
> `prop_polar_enrich.py`, `prop_component_seed.py`,
> `scripts/parse_apc_props.py`, `parse_apc_pe0.py`,
> `enrich_apc_snapshot_pe0.py`, ADR 0014.
> Endpoint contract: [`../contracts.md`](../contracts.md).

## Overview

The **APC propeller polar database** and the three-stage, network-free pipeline
that fills it: raw PER3 files → a *committed* snapshot → the
`propeller_polars` / `propeller_polar_samples` tables → mirrored `components`
rows. 454 propellers, each with per-RPM measurement blocks, PE0 mass and
inertia, and per-station blade geometry. 🟢

Everything downstream — the performance curves, `η_prop(J)`, the thrust
model — reads these rows. The pipeline's job is to make that data
**reproducible without network access** and **safe to reimport**. 🟢

## Responsibilities

- Own `propeller_polars` (header) and `propeller_polar_samples` (measurements).
  🟢
- Parse APC PER3 `.dat` files into a committed JSON snapshot. 🟢
- Enrich the snapshot with PE0 weight, inertia and blade geometry, rejecting
  implausible values. 🟢
- Import the snapshot into the database, upserting on `(manufacturer, name)`
  with a documented freshness proxy. 🟢
- Mirror each polar into a `components` row keyed on `model_ref`, with three
  explicit mass rules. 🟢

**NOT this use case:** the `components` table and its type schema
(→ [`cots-powertrain-components`](../cots-powertrain-components/requirements.md)),
interpolation and the thrust model
(→ [`performance-model`](../performance-model/requirements.md)).

## Business Rules

> Global ids from [`../../domain.md`](../../domain.md); `BR-PT*` from
> [`../requirements.md`](../requirements.md); `BR-PP*` are new here.

- **BR-PT5 — The physics definitions live on the model.** 🟢
  (`prop_polar.py:71-82`)
  ```
  J  = V / (n·D)      Ct = T / (ρ·n²·D⁴)
  Cp = P / (ρ·n³·D⁵)  Pe = Ct·J / Cp        (0 at J = 0)
  ```
- **BR-62 / ADR 0014 — The durable source is a committed snapshot.** 🟢
  `data/apc_raw/**/PER3_*.dat` is gitignored (~58 MB);
  `data/cots/apc_props.json.gz` is committed (~8 MB) and is what every reimport
  reads. No live fetch, ever.
- **BR-PT6 — Geometry comes from header line 1.** 🟢 The only way to read
  `PER3_105x45` as 10.5 × 4.5 in and to catch variant suffixes. Filename
  parsing is the **logged** fallback.
- **BR-PT7 — SI columns only, at fixed indices.** 🟢
  `J=1, Pe=2, Ct=3, Cp=4, PWR_W=8, Torque_Nm=9, Thrust_N=10`; imperial
  Hp/In-Lbf/Lbf discarded; rows with `< 11` fields skipped.
- **BR-PT8 — Blade count is a trailing digit, not a letter.** 🟢
  `_BLADE_COUNT_RE = -([3-9])$` applied to the **variant**, `DEFAULT_BLADES = 2`
  (gh-1004): `""`→2, `"E"`→2, `"-4"`→4, `"E-3"`→3, `"M-JK"`→**2**. Marine and
  rotation suffixes (`M-JK`, `MRF-RH`, `P-LH`, `R-RH`) are not blade counts.
- **BR-PT9 — `model_ref` is the join key, `.` → `p`.** 🟢
  `apc/<designation>`; `10.5x4.5` → `apc/10p5x4p5`. It links the polar to its
  mirrored component.
- **BR-PP1 — The header upsert key is `(manufacturer, name)`.** 🟢 A record
  whose `component_type` is not `"propeller"` is rejected into
  `ImportResult.errors` rather than imported.
- **BR-PT10 — Freshness is a proxy, not deep equality.** 🟢 `_records_equal`
  compares `source_version`, `source_url`, `variant`, and the case *"the row
  lacks `weight_g` but the snapshot has one"* — the first two so an upstream
  revision is picked up, the third so pre-gh-999 rows gain their variant, the
  fourth so the gh-1000 PE0 enrichment is not skipped. The docstring states the
  limitation explicitly: **if APC corrects polar data without bumping
  `source_version`, the change is skipped; run with `force=True`.** 🔴
- **BR-PT11 — Samples are replaced wholesale.** 🟢 `_upsert_samples` deletes
  every sample of the propeller and re-inserts; there is no per-sample diff.
  🔴 There is also **no unique constraint** on `(propeller_id, rpm, J)` — the
  delete-first is the only duplicate protection.
- **BR-64 — Implausible parsed data is rejected, not written.** 🟢
  `MIN_PLAUSIBLE_WEIGHT_G = 1.0` (`prop_polar_enrich.py:29`): a parsed weight
  below 1 g is treated as a kg→g conversion error, counted in `unit_warnings`,
  and **not** written. Unmatched PE0 rows are logged, never dropped silently.
- **BR-PP2 — PE0 records are matched by `(diameter, pitch, variant)`.** 🟢 Not
  by filename and not by `model_ref`.
- **BR-63 — User-entered mass always wins.** 🟢 `prop_component_seed`:
  1. on **create**, `mass_g` is populated from `weight_g` (both grams — no
     conversion);
  2. a **NULL** `mass_g` is backfilled once the polar gains a weight;
  3. a **non-null** `mass_g` is never clobbered.
  Polars without a `model_ref` are skipped.
- **BR-PP3 — The mirror is idempotent on `model_ref`.** 🟢 Re-running the seed
  creates nothing new.
- **BR-PP4 — `Torque_Nm` and `Thrust_N` are stored but not used for physics.**
  🟢 The performance model derives torque as `P/(2π·n)` because the stored
  column loses precision at 3 decimals for low-RPM rows.
- **BR-PP5 — `Pe` is nullable in storage and recomputed on read.** 🟢 The
  column exists "for safety"; the performance model recomputes `Ct·J/Cp`.
- **BR-PP6 — Samples cascade-delete with their header.** 🟢
  `cascade="all, delete-orphan"`.
- **BR-CC3 — Both tables are shared library data.** 🟢 They are per-installation,
  not per-aircraft, and the `versioning` clone leaves them alone.
- 🟢 The `component_types` schema is the complete binding contract for every writer including the seeds (`Q-PT-5`). Previously `prop_component_seed` bypassed `validate_specs`, — a polar with a NULL
  `diameter_in` / `pitch_in` produces a component that violates the seeded
  `propeller` schema (both are `required`) and 422s on its first API `PUT`.
- 🔴 **`specs["variant"]` is written by the seed but not declared** in the
  `propeller` type schema; it survives only because unknown keys are accepted.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Store a per-propeller header keyed `(manufacturer, name)` with `model_ref`, source metadata, geometry, variant, blades, weight and inertia | Must | The 454-record snapshot imports into 454 headers |
| RF-02 | Store per-RPM measurement rows with `J, Ct, Cp, Pe, PWR_W, Torque_Nm, Thrust_N` | Must | A header's samples are retrievable by `propeller_id` and grouped by `rpm` |
| RF-03 | Cascade-delete samples with their header | Must | Deleting a header leaves no orphan samples |
| RF-04 | Parse diameter, pitch and variant from PER3 header line 1 | Must | `PER3_105x45` ⇒ 10.5 × 4.5 in |
| RF-05 | Fall back to filename parsing, with a log line | Should | A header-less file still yields a record and logs the fallback |
| RF-06 | Keep only the SI columns, skipping short rows | Must | A row with 10 fields is skipped; the imperial columns never reach the database |
| RF-07 | Derive the blade count from a trailing `-[3-9]` on the variant | Must | `E-3` ⇒ 3; `M-JK` ⇒ 2; `""` ⇒ 2 |
| RF-08 | Build `model_ref` as `apc/<designation>` with `.` → `p` | Must | `10.5x4.5` ⇒ `apc/10p5x4p5` |
| RF-09 | Upsert headers on `(manufacturer, name)` | Must | A second import creates no duplicate headers |
| RF-10 | Reject a record whose `component_type` is not `"propeller"` | Must | The record appears in `ImportResult.errors`; no row is written |
| RF-11 | Skip an unchanged record based on the freshness proxy | Must | Unchanged snapshot ⇒ every record `skipped`; bumped `source_version` ⇒ `updated` |
| RF-12 | Force a full reimport on demand | Must | `force=True` updates every record regardless of the proxy |
| RF-13 | Replace all samples of a propeller on update | Must | Re-importing a propeller whose sample count changed leaves exactly the new count |
| RF-14 | Enrich with PE0 weight, inertia and geometry, matched on `(diameter, pitch, variant)` | Must | A matched record gains `weight_g`, `inertia_kg_m2` and a `geometry` list |
| RF-15 | Reject a parsed weight below 1 g into `unit_warnings` | Must | 0.043 g is counted, not written |
| RF-16 | Log unmatched PE0 rows without failing the run | Must | An unmatched record is logged and the run completes |
| RF-17 | Mirror each polar into a `components` row, idempotent on `model_ref` | Must | Re-running the seed creates nothing new |
| RF-18 | Populate `mass_g` from `weight_g` on create | Must | A new propeller component has `mass_g == weight_g` |
| RF-19 | Backfill a NULL `mass_g` when the polar gains a weight | Must | A component whose `mass_g` was NULL is filled on the next seed |
| RF-20 | Never clobber a non-null `mass_g` | Must | A user-edited 41.0 g survives a seed whose polar says 43.3 g |
| RF-21 | Skip polars without a `model_ref` | Must | Such a polar produces no component and no error |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Reproducibility | The entire dataset can be rebuilt offline from a committed artefact (ADR 0014) | `data/cots/apc_props.json.gz`, `scripts/import_apc_props.py` | 🟢 |
| Idempotence | Every stage of the pipeline can be re-run without duplicating data | upsert keys + `_upsert_samples` + the mirror's `model_ref` key | 🟢 |
| Data safety | Implausible parsed values are rejected and counted, never written | `MIN_PLAUSIBLE_WEIGHT_G = 1.0` | 🟢 |
| Data safety | User-entered data is never overwritten by an importer | `prop_component_seed` mass rules | 🟢 |
| Traceability | Every record carries `source_url` and `source_version` | `propeller_polars` columns | 🟢 |
| Honesty | The freshness proxy documents its own limitation in the code | `_records_equal` docstring | 🟢 |
| Robustness | A malformed row is skipped, not fatal; an unmatched PE0 row is logged, not dropped | `parse_apc_props.py`, `prop_polar_enrich.py` | 🟢 |
| Performance | The snapshot is gzip-compressed (~8 MB vs ~58 MB raw) so it is committable | `apc_props.json.gz` | 🟢 |
| Integrity | Duplicate samples are prevented procedurally, not by a constraint | `_upsert_samples`; no unique index | 🔴 |

## Acceptance Criteria

```gherkin
Feature: PER3 parsing

  Scenario: Geometry comes from the header, not the filename
    Given the file PER3_105x45.dat whose header line 1 says 10.5 x 4.5
    When I parse it
    Then diameter_in is 10.5
    And pitch_in is 4.5

  Scenario Outline: Blade count from the variant
    Given a propeller with variant "<variant>"
    When I derive the blade count
    Then blades is <blades>
    Examples:
      | variant | blades |
      |         | 2      |
      | E       | 2      |
      | -4      | 4      |
      | E-3     | 3      |
      | M-JK    | 2      |
      | MRF-RH  | 2      |

  Scenario: model_ref replaces the decimal point
    Given the designation 10.5x4.5
    When I build the model_ref
    Then it is "apc/10p5x4p5"

  Scenario: A short row is skipped
    Given a data row with only 10 fields
    When I parse the file
    Then that row produces no sample
    And the remaining rows are parsed

Feature: Import semantics

  Scenario: An unchanged snapshot is skipped
    Given the polars have been imported
    When I import the same snapshot again without force
    Then every record is counted as skipped
    And no samples are deleted

  Scenario: A bumped source_version triggers an update
    Given an imported polar with source_version "v2022-01"
    When I import a snapshot with source_version "v2023-01"
    Then the record is counted as updated
    And all of its samples are replaced

  Scenario: Silent upstream corrections are missed
    Given an imported polar
    When I import a snapshot whose Ct values changed but whose source_version did not
    Then the record is skipped
    And running with force True updates it

  Scenario: A non-propeller record is an error
    Given a snapshot record with component_type "battery"
    When I run the import
    Then it appears in ImportResult.errors
    And no propeller_polars row is created

  Scenario: Samples are replaced, not merged
    Given a propeller with 120 samples
    When I import a snapshot version with 80 samples
    Then the propeller has exactly 80 samples

Feature: PE0 enrichment

  Scenario: A matched record gains mass and inertia
    Given a PE0 record matching (10.0, 10.0, "E")
    When I enrich the snapshot
    Then the record gains weight_g, inertia_kg_m2 and a geometry list

  Scenario: A sub-gram weight is a unit warning
    Given a PE0 record whose parsed weight is 0.043 g
    When I enrich the snapshot
    Then weight_g is not written
    And unit_warnings is incremented

  Scenario: An unmatched PE0 record is logged
    Given a PE0 record with no matching snapshot record
    When I enrich the snapshot
    Then the record is logged
    And the run completes successfully

Feature: The component mirror

  Scenario: A new polar becomes a component
    Given a polar with model_ref "apc/10x10E" and weight_g 43.3
    And no component with that model_ref
    When I run seed_propeller_components
    Then a propeller component is created with mass_g 43.3

  Scenario: A NULL mass is backfilled
    Given a propeller component with mass_g null
    And its polar has gained weight_g 43.3
    When I run the seed
    Then mass_g becomes 43.3

  Scenario: A user-entered mass is preserved
    Given a propeller component whose mass_g was edited to 41.0
    And its polar says 43.3
    When I run the seed
    Then mass_g is still 41.0

  Scenario: A polar without a model_ref is skipped
    Given a polar with model_ref null
    When I run the seed
    Then no component is created
    And no error is raised
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| The two tables + cascade (RF-01…RF-03) | Must | Every performance curve reads them |
| Header-line parsing + blade count + `model_ref` (RF-04, RF-07, RF-08) | Must | Three places where a plausible shortcut produces silently wrong data |
| SI-only columns, short-row skip (RF-06) | Must | Mixing unit systems in one table would be unrecoverable |
| Upsert + wholesale sample replacement (RF-09, RF-13) | Must | The reimport story depends on both |
| Non-propeller rejection (RF-10) | Must | A battery in the polar table would break every consumer |
| Freshness proxy + `force` (RF-11/RF-12) | Must | Makes a 454-record reimport cheap; `force` is the documented escape hatch |
| PE0 guards (RF-15/RF-16) | Must | A kg→g error puts a 43 kg propeller on a 1.5 kg aircraft |
| Mirror + the three mass rules (RF-17…RF-21) | Must | The bridge that makes a propeller placeable; the never-clobber rule protects user data |
| PE0 enrichment itself (RF-14) | Should | The polars are usable without mass and inertia; the QPROP model and the mass roll-up are not |
| Filename fallback (RF-05) | Should | A safety net for malformed files, always logged |
| A unique constraint on `(propeller_id, rpm, J)` | Won't | 🔴 not implemented — protection is procedural |
| Deep data comparison on reimport | Won't | 🔴 explicitly out of scope; `force=True` is the answer |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/models/prop_polar.py:21` | `PropellerPolarModel` | 🟢 |
| `app/models/prop_polar.py:71-82` | `PropellerPolarSampleModel` + the physics docstring | 🟢 |
| `app/services/prop_polar_import.py` | `import_prop_polars`, `_records_equal`, `_upsert_samples` | 🟢 |
| `app/services/prop_polar_enrich.py:29` | PE0 enrichment, `MIN_PLAUSIBLE_WEIGHT_G` | 🟢 |
| `app/services/prop_component_seed.py` | `seed_propeller_components`, `_specs_from_polar` | 🟢 |
| `scripts/parse_apc_props.py:162-168, 302-304` | column indices, `DEFAULT_BLADES`, `_BLADE_COUNT_RE` | 🟢 |
| `scripts/parse_apc_pe0.py`, `enrich_apc_snapshot_pe0.py` | PE0 parsing and snapshot enrichment | 🟢 |
| `scripts/import_apc_props.py`, `seed_propeller_components.py` | reimport CLIs | 🟢 |
| `app/services/component_service.py` | `_resolve_polar_id` — the read-side bridge | 🟢 owned by [`cots-powertrain-components`](../cots-powertrain-components/design.md) |
</content>
