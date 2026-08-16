# propeller-polars — Technical Design

> Use-case design, nested under the module [`powertrain`](../design.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Full endpoint contract: [`../contracts.md`](../contracts.md).

## Interface

### `propeller_polars` — header 🟢

| Column | Type | Req. | Default | Unit / note |
|---|---|---|---|---|
| `manufacturer` | String INDEXED | yes | — | `"APC"` for the shipped snapshot |
| `name` | String INDEXED | yes | — | e.g. `"APC 10x10E"` |
| `model_ref` | String | no | `NULL` | `apc/<slug>`, `.` → `p`; join key to `components.model_ref` |
| `source_url` | String | no | `NULL` | `https://www.apcprop.com/files/<file>.dat` |
| `source_version` | String | no | `NULL` | APC `vYYYY-NN`; the **freshness proxy** |
| `diameter_in` / `pitch_in` | Float | no | `NULL` | **inches**, from header line 1 |
| `variant` | String | no | `""` | `""` · `E` · `M-JK` · `E-3` … |
| `blades` | Integer | no | `2` | from a trailing `-[3-9]` in `variant` (gh-1004) |
| `weight_g` | Float | no | `NULL` | **grams**, from PE0 (gh-1000); PE0 reports kg and is normalised |
| `inertia_kg_m2` | Float | no | `NULL` | kg·m², kept in PE0's own unit |
| `geometry` | JSON | no | `NULL` | per-station blade rows |

Upsert key **`(manufacturer, name)`**. Relationship `samples` with
`cascade="all, delete-orphan"`.

### `propeller_polar_samples` — measurements 🟢

| Column | Type | Req. | Note |
|---|---|---|---|
| `propeller_id` | Integer FK INDEXED | yes | |
| `rpm` | Integer INDEXED | yes | the RPM block this row belongs to |
| `J`, `Ct`, `Cp` | Float | yes | the three the physics actually uses |
| `Pe` | Float | no | nullable "for safety"; **recomputed** on read |
| `PWR_W` | Float | no | shaft power [W] |
| `Torque_Nm` | Float | no | stored, **deliberately unused** (3-dp precision loss) |
| `Thrust_N` | Float | no | stored, not used for physics |

🔴 No unique constraint on `(propeller_id, rpm, J)`.

### Services and scripts 🟢

| Symbol | File | Role |
|---|---|---|
| `parse_apc_props` | `scripts/parse_apc_props.py` | PER3 `.dat` → snapshot records |
| `parse_apc_pe0` / `enrich_apc_snapshot_pe0` | `scripts/` | PE0 → weight / inertia / geometry |
| `import_prop_polars` | `app/services/prop_polar_import.py` | snapshot → tables |
| `_records_equal` | idem | the freshness proxy |
| `_upsert_samples` | idem | delete-all + re-insert |
| `enrich(...)` | `app/services/prop_polar_enrich.py` | the PE0 matcher + guard |
| `seed_propeller_components` / `_specs_from_polar` | `app/services/prop_component_seed.py` | polar → component mirror |

## Main Flow

### F0 — The pipeline 🟢

```
data/apc_raw/**/PER3_*.dat        gitignored, ~58 MB
        │ scripts/parse_apc_props.py
        ▼
data/cots/apc_props.json.gz       COMMITTED, ~8 MB   ← the reimport source
        │ scripts/enrich_apc_snapshot_pe0.py  (+ PE0 weight/inertia/geometry)
        ▼
        │ scripts/import_apc_props.py → prop_polar_import.import_prop_polars
        ▼
propeller_polars + propeller_polar_samples
        │ scripts/seed_propeller_components.py → prop_component_seed
        ▼
components (component_type='propeller', keyed on model_ref)
```

Each arrow is independently re-runnable and idempotent. 🟢

### F1 — Parsing (`scripts/parse_apc_props.py`) 🟢

```
header line 1  ->  diameter_in, pitch_in, variant        (authoritative)
filename       ->  the same, ONLY as a logged fallback

variant suffix ->  blades:  _BLADE_COUNT_RE = -([3-9])$   applied to the VARIANT
                            no match -> DEFAULT_BLADES = 2

designation    ->  model_ref = "apc/" + designation.replace(".", "p")

per RPM block, per data row:
    len(fields) < 11        -> skip
    keep indices  J=1 Pe=2 Ct=3 Cp=4 PWR_W=8 Torque_Nm=9 Thrust_N=10
    discard the Hp / In-Lbf / Lbf columns
```

Two subtleties that a re-implementation must not "simplify":

- reading geometry from the **header** is the only way `PER3_105x45` becomes
  10.5 × 4.5 in rather than 105 × 45;
- the blade regex is anchored to a **digit** so `M-JK`, `MRF-RH`, `P-LH` and
  `R-RH` — marine and rotation suffixes — stay at 2 blades. 🟢

### F2 — PE0 enrichment (`prop_polar_enrich.py`) 🟢

```
match PE0 record to snapshot record on (diameter, pitch, variant)

weight parsed from PE0 (which reports kg) -> grams
    grams < MIN_PLAUSIBLE_WEIGHT_G (1.0)  -> REJECT, unit_warnings += 1
    otherwise                             -> record["specs"]["weight_g"]

also writes inertia_kg_m2 (PE0's own unit, unconverted)
and a per-station geometry list

unmatched PE0 records -> logged, never silently dropped
```

The 1 g floor is a **unit-error detector**: a propeller weighing 0.043 g is
almost certainly 43 g misread as kilograms, and writing it would put a
weightless propeller on the aircraft. 🟢

### F3 — Import (`import_prop_polars`) 🟢

```
for record in snapshot:
    record["component_type"] != "propeller"  -> ImportResult.errors, continue

    row = SELECT … WHERE manufacturer = ? AND name = ?

    row is None:
        INSERT header ; _upsert_samples(...)          imported += 1
    else:
        _records_equal(row, record) and not force:
            skipped += 1                              # NO sample touch
        else:
            UPDATE header ; _upsert_samples(...)      updated += 1
```

`_records_equal` compares:

| Field | Why |
|---|---|
| `source_version` | the primary freshness signal |
| `source_url` | a moved file implies a new source |
| `variant` | so pre-gh-999 rows gain their variant |
| "row lacks `weight_g` but the snapshot has one" | so the gh-1000 PE0 enrichment is not skipped |

It deliberately does **not** compare the samples. The docstring says so and
names `force=True` as the escape hatch. 🔴 A silent upstream data correction is
therefore invisible.

`_upsert_samples` deletes every sample of the propeller and re-inserts — no
per-sample diff, and the only protection against duplicates. 🟢

### F4 — The component mirror (`prop_component_seed`) 🟢

```
for polar in propeller_polars:
    polar.model_ref is None  ->  skip

    comp = SELECT … WHERE component_type = 'propeller' AND model_ref = polar.model_ref

    comp is None:
        INSERT ComponentModel(
            component_type = "propeller",
            model_ref      = polar.model_ref,
            mass_g         = polar.weight_g,          # grams -> grams, NO conversion
            specs          = _specs_from_polar(polar) # diameter_in, pitch_in, blades, variant
        )                                             created += 1
    else:
        comp.mass_g is None and polar.weight_g is not None
              -> comp.mass_g = polar.weight_g          # backfill once   updated += 1
        comp.mass_g is not None
              -> leave it alone                        # user wins       skipped += 1
```

The three mass rules are the whole point: an importer may **fill** a gap, never
**overwrite** a decision. 🟢

Two consequences the code accepts:

- the write bypasses `validate_specs`, so a polar with a NULL `diameter_in`
  produces a component that violates the seeded `propeller` schema and 422s on
  its first API `PUT`; 🔴
- `specs["variant"]` is written although the schema does not declare it —
  legal only because unknown keys are accepted (BR-60). 🔴

## Alternative Flows

- **Header line unreadable:** filename parsing takes over, with a log line. 🟢
- **Row with fewer than 11 fields:** skipped silently within the file's parse.
  🟡 counted only in aggregate.
- **Variant with a letter suffix:** 2 blades (BR-PT8). 🟢
- **Record whose `component_type` ≠ `"propeller"`:** into `errors`; the import
  continues. 🟢
- **Unchanged record:** `skipped`; **no** sample deletion, so a reimport of an
  unchanged snapshot is cheap. 🟢
- **Changed samples, unchanged `source_version`:** skipped — data drift is
  invisible without `force=True`. 🔴
- **PE0 weight below 1 g:** rejected into `unit_warnings`; the previous
  `weight_g` (if any) stands. 🟢
- **Unmatched PE0 record:** logged; the enrichment completes. 🟢
- **Polar without `model_ref`:** skipped by the mirror, no error. 🟢
- **Component with a user-edited mass:** preserved. 🟢
- **Header deleted:** samples cascade. 🟢
- **Duplicate `(rpm, J)` rows in a snapshot:** both inserted — nothing rejects
  them, and the interpolation would then see a non-monotonic `J` sequence after
  sorting. 🔴

## Dependencies

- **[`cots-powertrain-components`](../cots-powertrain-components/design.md)** —
  the mirror writes into `components`; `_resolve_polar_id` reads back the other
  way. The two are joined **only** by `model_ref`.
- **[`performance-model`](../performance-model/design.md)** — the sole consumer
  of the samples; it recomputes `Pe` and derives torque rather than reading the
  stored columns.
- **`app/db/session.py` (`get_db`)** for the service path; the CLIs manage their
  own session and commit once at the end.
- **ADR 0014** — the snapshot-driven, network-free ingestion decision.
- **gh-999 / gh-1000 / gh-1004 / gh-1012 / gh-1017** — the increments that added
  `variant`, PE0 weight/inertia, the blade count, the component mirror and the
  mass backfill respectively.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| The durable source is a committed, compressed snapshot rather than the vendor files | ADR 0014; `apc_props.json.gz` | 🟢 |
| Geometry is read from the file header, with the filename only as a logged fallback | `parse_apc_props.py` | 🟢 |
| Only SI columns are stored; the imperial duplicates are discarded at parse time | `_COL_*` indices | 🟢 |
| The blade regex is anchored to a digit so letter suffixes are not blade counts | `_BLADE_COUNT_RE`; gh-1004 | 🟢 |
| Freshness is decided by metadata, not by comparing the data — with the limitation documented in the code | `_records_equal` | 🟢 (a 🔴 limitation) |
| Samples are replaced wholesale rather than diffed | `_upsert_samples` | 🟢 |
| An implausible parsed weight is rejected and counted rather than written | `MIN_PLAUSIBLE_WEIGHT_G = 1.0` | 🟢 |
| PE0 records are matched on geometry, not on a filename or slug | `prop_polar_enrich` | 🟢 |
| The mirror may fill a NULL mass but never overwrite a user's value | `prop_component_seed`; BR-63 | 🟢 |
| The mirror writes ORM rows directly, bypassing the type-schema validation | `prop_component_seed` | 🟢 (a 🔴 consequence) |
| `Torque_Nm` and `Thrust_N` are archived, not used | `prop_polar.py:71-82`; BR-PP4 | 🟢 |

## Internal State

Both tables are **installation-global**: shared by every aircraft, excluded from
the versioning clone, and written only by the importers. There is no per-request
mutation and no cache.

The snapshot file itself is the pipeline's real state — it is version-controlled,
so the database can always be rebuilt to a known point, and a data change is
visible as a diff in the repository. 🟢

## Observability

- `ImportResult{imported, updated, skipped, errors[]}` from the polar import.
  🟢
- `SeedResult{created, updated, skipped, errors[]}` from the mirror. 🟢
- `unit_warnings` from the PE0 enricher — the count of rejected implausible
  weights. 🟢
- Log lines for the filename fallback and for unmatched PE0 records. 🟢
- Nothing records **which** records were skipped, so a reimport that silently
  misses a corrected dataset leaves no trace beyond the aggregate count. 🔴

## Risks and Gaps

- 🔴 **Data drift is invisible.** `_records_equal` compares metadata only; APC
  correcting a polar without bumping `source_version` is skipped, and only a
  manual `force=True` recovers it.
- 🔴 **No unique constraint on `(propeller_id, rpm, J)`.** Duplicate protection
  is `_upsert_samples`'s delete-first; a direct insert or a duplicated snapshot
  row would corrupt the interpolation input.
- 🔴 **The mirror bypasses `validate_specs`**, so it can create components that
  violate their own type schema and fail on the first API edit.
- 🔴 **`specs["variant"]` is undeclared** in the `propeller` schema.
- 🔴 **Skipped records are not enumerated**, so a partial or stale import cannot
  be audited after the fact.
- 🟡 **Short rows are skipped without an individual counter**, so a systematically
  malformed file looks like a smaller propeller rather than an error.
- 🟡 **`inertia_kg_m2` is stored in PE0's unit without a conversion check** —
  the 1 g floor guards the weight but nothing guards the inertia.
- 🟡 **The snapshot is the only integrity boundary.** A hand-edited
  `apc_props.json.gz` would import without complaint; nothing checksums it.
</content>
