# Design: Unify DB Storage Units to mm in `wing_xsec_spares`

**Issue:** #402
**Date:** 2026-05-03
**Status:** Approved

## Problem

The `wing_xsec_spares` table has mixed units: 4 dimensional fields
(`width`, `height`, `length`, `start`) are stored in **mm**, while
2 computed fields (`spare_origin`, `spare_vector`) are stored in
**meters**. This inconsistency forces anyone touching the conversion
layer to know which field uses which unit, with no model-level
documentation.

## Target State

| Layer | Unit |
|-------|------|
| DB: all 6 spar fields | mm (unified) |
| API (request + response) | m (unchanged) |
| cad_designer / WingConfig | mm (unchanged) |

## Approach

Post-computation scaling in `_sync_spares_for_xsec`. After the
WingConfiguration computes origin/vector in meters (via `scale=1.0`),
multiply each component by 1000 before writing to DB. This is
targeted and doesn't affect the geometry pipeline.

Rejected alternative: changing `scale=1.0` to `scale=1000.0` in
`_recompute_spare_vectors` — affects the entire WingConfiguration
build for a 2-field change.

## Changes

### 1. Alembic Data Migration

New migration that converts existing `spare_origin` and
`spare_vector` JSON arrays from meters to mm (multiply each element
by 1000). SQLite JSON syntax:

```sql
UPDATE wing_xsec_spares
SET spare_origin = json_array(
      json_extract(spare_origin, '$[0]') * 1000,
      json_extract(spare_origin, '$[1]') * 1000,
      json_extract(spare_origin, '$[2]') * 1000
    ),
    spare_vector = json_array(
      json_extract(spare_vector, '$[0]') * 1000,
      json_extract(spare_vector, '$[1]') * 1000,
      json_extract(spare_vector, '$[2]') * 1000
    )
WHERE spare_origin IS NOT NULL OR spare_vector IS NOT NULL;
```

Downgrade reverses with `* 0.001`.

### 2. `_sync_spares_for_xsec` — `wing_service.py:837`

Multiply the computed origin/vector values by `_M_TO_MM` (1000)
before writing to the DB spare records. The values come from
`_resolve_spare_vectors_and_origins` which computes in meters
(since the WingConfiguration is built with `scale=1.0`).

### 3. `_convert_spare_to_meters` — `wing_service.py:44`

Add `spare_origin` and `spare_vector` to the conversion dict.
Both fields are `Optional[list[float]]` so None guards are required:

```python
"spare_origin": [v * _MM_TO_M for v in spare.spare_origin] if spare.spare_origin is not None else None,
"spare_vector": [v * _MM_TO_M for v in spare.spare_vector] if spare.spare_vector is not None else None,
```

Update the docstring to reflect that all 6 fields are now converted.

### 4. `_convert_spare_to_mm` — `wing_service.py:61`

No change. `_recompute_spare_vectors` always runs immediately after
spare creation/update and overwrites origin/vector with correct mm
values. The brief window where API-provided meter values sit in DB
is harmless.

### 5. Schema Documentation — `aeroplaneschema.py:187`

Add "in meters" to `spare_vector` field description for consistency.
The other fields already document their unit correctly.

Note: the issue originally targeted `wing.py:100-124`, but that is
the WingConfig `Spare` class which correctly uses mm. The API-facing
schema is `SpareDetailSchema` in `aeroplaneschema.py`.

### 6. Converter Layer — `model_schema_converters.py`

No changes needed. `_resolve_spare_vectors_and_origins` clears and
recomputes origin/vector from geometry on every conversion (gh-352,
gh-362). The scale parameter on `wing_model_to_wing_config`
determines the output unit. The converter is unaffected by what
unit the DB stores.

### 7. Tests

- Update `test_wing_service_extended.py`: assertions for
  `spare_origin`/`spare_vector` must expect mm-stored values that
  get converted to meters via `_convert_spare_to_meters`
- Update `test_model_schema_converters.py`: the gh-352 regression
  test may need adjusted expectations
- Add round-trip test: API create (m) → DB stores (mm) → API read
  returns same (m)
- Add direct DB verification: read DB record and assert all 6 fields
  are in mm

## Not Changing

- `cad_designer/` — read-only per project rules
- Frontend — consumes API meters, no direct DB access
- API contract — all spar endpoints continue to deliver meters
- `_convert_spare_to_mm` — origin/vector are always overwritten by
  `_recompute_spare_vectors`
- `spare_position_factor` — dimensionless (0.0-1.0)

## Acceptance Criteria

1. Alembic migration converts existing `spare_origin`/`spare_vector`
   from m to mm
2. All 6 fields in `wing_xsec_spares` are consistently mm after
   migration
3. `_recompute_spare_vectors` writes origin/vector in mm
4. `_convert_spare_to_meters` converts all 6 fields (incl.
   origin/vector) from mm to m
5. API contract unchanged: all spar endpoints deliver meters
6. Round-trip test: create via API (m) → DB stores mm → read via
   API returns same m
7. Schema descriptions match API contract
8. All existing tests green
