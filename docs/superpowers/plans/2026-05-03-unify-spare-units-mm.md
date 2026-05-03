# Unify DB Spare Units to mm — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make all 6 dimensional fields in `wing_xsec_spares` consistently store mm, eliminating the current mix where `spare_origin`/`spare_vector` are in meters while the other 4 fields are in mm.

**Architecture:** Post-computation scaling in `_sync_spares_for_xsec`. After `_recompute_spare_vectors` computes origin/vector in meters (via `scale=1.0`), multiply each component by `_M_TO_MM` (1000) before writing to DB. `_convert_spare_to_meters` gains origin/vector conversion so the API contract (meters) is preserved.

**Tech Stack:** Python 3.11+, SQLAlchemy, Alembic, pytest, SQLite

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `app/services/wing_service.py` | Modify | Scale origin/vector in `_sync_spares_for_xsec`; extend `_convert_spare_to_meters`; update docstrings |
| `app/schemas/aeroplaneschema.py` | Modify | Add "in meters" to `spare_vector` description |
| `alembic/versions/<new>_unify_spare_units_mm.py` | Create | Data migration: multiply existing origin/vector by 1000 |
| `app/tests/test_wing_service_extended.py` | Modify | Update assertions for origin/vector; add round-trip + DB verification tests |
| `app/tests/test_model_schema_converters.py` | Modify | Update gh-352 regression test expectations |

---

### Task 1: Update `_convert_spare_to_meters` to convert origin/vector

**Files:**
- Modify: `app/services/wing_service.py:44-58`
- Test: `app/tests/test_wing_service_extended.py`

- [ ] **Step 1: Write failing test for origin/vector conversion**

In `app/tests/test_wing_service_extended.py`, add a new test to the `TestGetWingSpareFieldUnits` class (after `test_get_wing_units_schema_reports_meters_for_all` around line 1358). This test creates a spare with mm-valued origin/vector in the DB and asserts the API returns them converted to meters:

```python
def test_get_wing_returns_spare_origin_vector_in_meters(self, db):
    """After gh-402, spare_origin/spare_vector are stored in mm and must be converted to meters."""
    plane, wing = self._make_plane_with_spares_mm(db)

    result = wing_service.get_wing(db, plane.uuid, "main")

    spare = result.x_secs[0].spare_list[0]
    # spare_origin stored as [40.5, 0.0, 3.45] mm -> expect [0.0405, 0.0, 0.00345] m
    assert abs(spare.spare_origin[0] - 0.0405) < 1e-9
    assert abs(spare.spare_origin[1] - 0.0) < 1e-9
    assert abs(spare.spare_origin[2] - 0.00345) < 1e-9
    # spare_vector stored as [0.0, 1.0, 0.0] mm -> expect [0.0, 0.001, 0.0] m
    assert abs(spare.spare_vector[0] - 0.0) < 1e-9
    assert abs(spare.spare_vector[1] - 0.001) < 1e-9
    assert abs(spare.spare_vector[2] - 0.0) < 1e-9
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/gh-402 && poetry run pytest app/tests/test_wing_service_extended.py::TestGetWingSpareFieldUnits::test_get_wing_returns_spare_origin_vector_in_meters -xvs`

Expected: FAIL — `_convert_spare_to_meters` currently passes origin/vector through unchanged, so the test will see `[40.5, 0.0, 3.45]` instead of `[0.0405, 0.0, 0.00345]`.

- [ ] **Step 3: Implement the conversion**

In `app/services/wing_service.py`, modify `_convert_spare_to_meters` (line 44-58):

```python
def _convert_spare_to_meters(spare: schemas.SpareDetailSchema) -> schemas.SpareDetailSchema:
    """Convert all SpareDetailSchema dimensional fields from mm (DB storage) to meters (API response)."""
    return spare.model_copy(
        update={
            "spare_support_dimension_width": spare.spare_support_dimension_width * _MM_TO_M,
            "spare_support_dimension_height": spare.spare_support_dimension_height * _MM_TO_M,
            "spare_length": spare.spare_length * _MM_TO_M if spare.spare_length is not None else None,
            "spare_start": spare.spare_start * _MM_TO_M,
            "spare_origin": [v * _MM_TO_M for v in spare.spare_origin] if spare.spare_origin is not None else None,
            "spare_vector": [v * _MM_TO_M for v in spare.spare_vector] if spare.spare_vector is not None else None,
        }
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/gh-402 && poetry run pytest app/tests/test_wing_service_extended.py::TestGetWingSpareFieldUnits::test_get_wing_returns_spare_origin_vector_in_meters -xvs`

Expected: PASS

- [ ] **Step 5: Update the existing test that now breaks**

The existing test `test_get_wing_returns_spare_fields_in_meters` (line 1319) asserts `spare.spare_origin == [40.5, 0.0, 3.45]` — expecting pass-through. After our change, origin/vector are now also converted mm→m. Update lines 1334-1337:

```python
        # spare_origin stored as [40.5, 0.0, 3.45] mm -> converted to meters (gh-402)
        assert abs(spare.spare_origin[0] - 0.0405) < 1e-9
        assert abs(spare.spare_origin[1] - 0.0) < 1e-9
        assert abs(spare.spare_origin[2] - 0.00345) < 1e-9
```

- [ ] **Step 6: Run the full test class to verify no regressions**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/gh-402 && poetry run pytest app/tests/test_wing_service_extended.py::TestGetWingSpareFieldUnits -xvs`

Expected: All tests in the class PASS.

- [ ] **Step 7: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/gh-402
git add app/services/wing_service.py app/tests/test_wing_service_extended.py
git commit -m "refactor(gh-402): convert spare origin/vector mm→m in _convert_spare_to_meters

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Scale origin/vector to mm in `_sync_spares_for_xsec`

**Files:**
- Modify: `app/services/wing_service.py:837-849`
- Modify: `app/services/wing_service.py:852-872` (docstring only)
- Test: `app/tests/test_wing_service_extended.py`

- [ ] **Step 1: Write failing test for mm-valued DB storage after recompute**

Add a new test class in `app/tests/test_wing_service_extended.py` (at the end of the file). This test creates a spare via the API (meters), triggers `_recompute_spare_vectors`, then reads the raw DB record to verify origin/vector are stored in mm:

```python
class TestSpareDbStorageUnitsMm:
    """Verify that spare_origin/spare_vector are stored in mm in the DB (gh-402)."""

    def test_recompute_stores_origin_vector_in_mm(self, db):
        """After _recompute_spare_vectors, DB spare_origin/spare_vector must be in mm."""
        plane = make_aeroplane(db, name=f"db-units-{uuid.uuid4().hex[:8]}")
        wing = WingModel(name="main", symmetric=True, design_model="wc", aeroplane_id=plane.id)

        xsec0 = WingXSecModel(
            sort_index=0,
            xyz_le=[0.0, 0.0, 0.0],
            chord=0.2,
            twist=0.0,
            airfoil="naca0012",
        )
        detail = WingXSecDetailModel(x_sec_type="root")
        spare = WingXSecSpareModel(
            sort_index=0,
            spare_support_dimension_width=4.42,
            spare_support_dimension_height=6.0,
            spare_position_factor=0.25,
            spare_length=70.0,
            spare_start=5.0,
            spare_mode="standard",
            spare_vector=[0.0, 0.0, 0.0],
            spare_origin=[0.0, 0.0, 0.0],
        )
        detail.spares.append(spare)
        xsec0.detail = detail

        xsec1 = WingXSecModel(
            sort_index=1,
            xyz_le=[0.0, 0.5, 0.0],
            chord=0.15,
            twist=0.0,
            airfoil="naca0012",
        )

        wing.x_secs.append(xsec0)
        wing.x_secs.append(xsec1)
        db.add(wing)
        db.commit()

        wing_service._recompute_spare_vectors(wing)
        db.commit()

        db.refresh(spare)
        # At scale=1.0, position_factor=0.25 on chord=0.2m gives origin.x ≈ 0.05m
        # After scaling to mm, DB should store ≈ 50.0 mm
        assert spare.spare_origin is not None
        assert spare.spare_origin[0] > 1.0, (
            f"spare_origin[0]={spare.spare_origin[0]} looks like meters, expected mm (>1.0)"
        )
        assert spare.spare_vector is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/gh-402 && poetry run pytest app/tests/test_wing_service_extended.py::TestSpareDbStorageUnitsMm::test_recompute_stores_origin_vector_in_mm -xvs`

Expected: FAIL — `_sync_spares_for_xsec` currently writes meter values, so `spare_origin[0]` will be ~0.05 (meters), which is < 1.0.

- [ ] **Step 3: Implement mm scaling in `_sync_spares_for_xsec`**

In `app/services/wing_service.py`, modify `_sync_spares_for_xsec` (line 837-849):

```python
def _sync_spares_for_xsec(db_xsec, segment) -> None:
    """Copy computed spare_vector/spare_origin from a WingConfiguration segment
    back to the corresponding DB cross-section's spar records.

    The WingConfiguration computes origin/vector in meters (built with scale=1.0).
    Values are scaled to mm for consistent DB storage (gh-402).
    """
    for spare_idx, spare in enumerate(segment.spare_list or []):
        if spare_idx >= len(db_xsec.detail.spares):
            break
        db_spare = db_xsec.detail.spares[spare_idx]
        if spare.spare_vector is not None:
            vec = spare.spare_vector.toTuple() if hasattr(spare.spare_vector, "toTuple") else spare.spare_vector
            db_spare.spare_vector = [float(v) * _M_TO_MM for v in vec]
        if spare.spare_origin is not None:
            orig = spare.spare_origin.toTuple() if hasattr(spare.spare_origin, "toTuple") else spare.spare_origin
            db_spare.spare_origin = [float(v) * _M_TO_MM for v in orig]
```

Also update the docstring of `_recompute_spare_vectors` (line 852-859):

```python
def _recompute_spare_vectors(wing: WingModel) -> None:
    """Rebuild WingConfiguration to compute spare_vector/spare_origin for all spars,
    then persist the computed values back to the DB spar records in mm.

    Uses ``scale=1.0`` to compute in metres, then ``_sync_spares_for_xsec``
    converts to mm for consistent DB storage (gh-402).
    """
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/gh-402 && poetry run pytest app/tests/test_wing_service_extended.py::TestSpareDbStorageUnitsMm::test_recompute_stores_origin_vector_in_mm -xvs`

Expected: PASS — `spare_origin[0]` should now be ~50.0 mm.

- [ ] **Step 5: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/gh-402
git add app/services/wing_service.py app/tests/test_wing_service_extended.py
git commit -m "refactor(gh-402): scale spare origin/vector to mm in _sync_spares_for_xsec

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Add round-trip test (API meters → DB mm → API meters)

**Files:**
- Test: `app/tests/test_wing_service_extended.py`

- [ ] **Step 1: Write the round-trip test**

Add to `TestSpareDbStorageUnitsMm` in `app/tests/test_wing_service_extended.py`:

```python
def test_spare_round_trip_api_meters_db_mm_api_meters(self, db):
    """Round-trip: create via API (m) → DB stores mm → read via API returns same m."""
    plane = make_aeroplane(db, name=f"roundtrip-{uuid.uuid4().hex[:8]}")
    wing = WingModel(name="main", symmetric=True, design_model="wc", aeroplane_id=plane.id)

    xsec0 = WingXSecModel(
        sort_index=0,
        xyz_le=[0.0, 0.0, 0.0],
        chord=0.2,
        twist=0.0,
        airfoil="naca0012",
    )
    detail = WingXSecDetailModel(x_sec_type="root")
    xsec0.detail = detail

    xsec1 = WingXSecModel(
        sort_index=1,
        xyz_le=[0.0, 0.5, 0.0],
        chord=0.15,
        twist=0.0,
        airfoil="naca0012",
    )

    wing.x_secs.append(xsec0)
    wing.x_secs.append(xsec1)
    db.add(wing)
    db.commit()
    db.refresh(plane)

    # Create spare via service (API input in meters)
    spare_input = schemas.SpareDetailSchema(
        spare_support_dimension_width=0.00442,
        spare_support_dimension_height=0.006,
        spare_position_factor=0.25,
        spare_length=0.07,
        spare_start=0.005,
        spare_mode="standard",
        spare_vector=[0.0, 1.0, 0.0],
        spare_origin=[0.0, 0.0, 0.0],
    )
    wing_service.create_spare(db, plane.uuid, "main", 0, spare_input)
    db.commit()

    # Read back via service (API output in meters)
    spares = wing_service.get_spares(db, plane.uuid, "main", 0)
    assert len(spares) == 1
    result = spares[0]

    # Dimensional fields: API input → DB (mm) → API output (m)
    assert abs(result.spare_support_dimension_width - 0.00442) < 1e-9
    assert abs(result.spare_support_dimension_height - 0.006) < 1e-9
    assert abs(result.spare_length - 0.07) < 1e-9
    assert abs(result.spare_start - 0.005) < 1e-9

    # origin/vector are recomputed by _recompute_spare_vectors,
    # so API output won't match API input exactly — but they must be in meters
    assert result.spare_origin is not None
    assert all(isinstance(v, float) for v in result.spare_origin)
    assert result.spare_vector is not None
    assert all(isinstance(v, float) for v in result.spare_vector)

    # Verify DB stores mm: read raw DB record
    db.refresh(wing)
    db_spare = wing.x_secs[0].detail.spares[0]
    # width stored in mm (0.00442 m * 1000 = 4.42 mm)
    assert abs(db_spare.spare_support_dimension_width - 4.42) < 1e-6
    # origin should be in mm (values > 1.0 for a 200mm chord wing)
    assert db_spare.spare_origin is not None
    assert db_spare.spare_origin[0] > 1.0, (
        f"DB spare_origin[0]={db_spare.spare_origin[0]} looks like meters, expected mm"
    )
```

- [ ] **Step 2: Run test to verify it passes**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/gh-402 && poetry run pytest app/tests/test_wing_service_extended.py::TestSpareDbStorageUnitsMm::test_spare_round_trip_api_meters_db_mm_api_meters -xvs`

Expected: PASS (the production code from Tasks 1-2 already handles this).

- [ ] **Step 3: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/gh-402
git add app/tests/test_wing_service_extended.py
git commit -m "test(gh-402): add round-trip test for spare unit conversion

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Update `_convert_spare_to_mm` docstring

**Files:**
- Modify: `app/services/wing_service.py:61-75`

- [ ] **Step 1: Update the docstring**

The docstring at line 62-66 references "correct meter values" — update it to reflect the new mm storage:

```python
def _convert_spare_to_mm(spare: schemas.SpareDetailSchema) -> schemas.SpareDetailSchema:
    """Convert a SpareDetailSchema dimensional fields from meters (API input) to mm (DB storage).

    Only converts width, height, length, start. The spare_origin and spare_vector
    are passed through unchanged because _recompute_spare_vectors will overwrite
    them with correct mm values (gh-402).
    """
```

- [ ] **Step 2: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/gh-402
git add app/services/wing_service.py
git commit -m "docs(gh-402): update _convert_spare_to_mm docstring for mm storage

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Update schema documentation

**Files:**
- Modify: `app/schemas/aeroplaneschema.py:187`

- [ ] **Step 1: Update the `spare_vector` field description**

In `app/schemas/aeroplaneschema.py` line 187, add "in meters" to match the other fields:

```python
    spare_vector: Optional[list[float]] = Field(None, description="Spar direction vector [x, y, z] in meters")
```

- [ ] **Step 2: Run a quick sanity check**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/gh-402 && poetry run python -c "from app.schemas.aeroplaneschema import SpareDetailSchema; print(SpareDetailSchema.model_json_schema()['properties']['spare_vector']['description'])"`

Expected: `Spar direction vector [x, y, z] in meters`

- [ ] **Step 3: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/gh-402
git add app/schemas/aeroplaneschema.py
git commit -m "docs(gh-402): add unit to spare_vector schema description

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 6: Create Alembic data migration

**Files:**
- Create: `alembic/versions/<hash>_unify_spare_units_mm.py`

- [ ] **Step 1: Generate Alembic revision**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/gh-402 && poetry run alembic revision -m "unify spare origin vector units to mm gh402"`

This creates a new migration file. Note the generated filename.

- [ ] **Step 2: Write the migration**

Open the generated file and replace the empty `upgrade()` and `downgrade()` with:

```python
def upgrade() -> None:
    op.execute("""
        UPDATE wing_xsec_spares
        SET spare_origin = json_array(
              json_extract(spare_origin, '$[0]') * 1000,
              json_extract(spare_origin, '$[1]') * 1000,
              json_extract(spare_origin, '$[2]') * 1000
            )
        WHERE spare_origin IS NOT NULL
    """)
    op.execute("""
        UPDATE wing_xsec_spares
        SET spare_vector = json_array(
              json_extract(spare_vector, '$[0]') * 1000,
              json_extract(spare_vector, '$[1]') * 1000,
              json_extract(spare_vector, '$[2]') * 1000
            )
        WHERE spare_vector IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE wing_xsec_spares
        SET spare_origin = json_array(
              json_extract(spare_origin, '$[0]') * 0.001,
              json_extract(spare_origin, '$[1]') * 0.001,
              json_extract(spare_origin, '$[2]') * 0.001
            )
        WHERE spare_origin IS NOT NULL
    """)
    op.execute("""
        UPDATE wing_xsec_spares
        SET spare_vector = json_array(
              json_extract(spare_vector, '$[0]') * 0.001,
              json_extract(spare_vector, '$[1]') * 0.001,
              json_extract(spare_vector, '$[2]') * 0.001
            )
        WHERE spare_vector IS NOT NULL
    """)
```

Note: the issue's original SQL combined both fields in a single `WHERE` with `OR`. Splitting into two separate statements is safer — it avoids multiplying `spare_vector` when only `spare_origin` is non-null and vice versa.

- [ ] **Step 3: Verify the migration runs**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/gh-402 && poetry run alembic upgrade head`

Expected: Migration applies without errors.

- [ ] **Step 4: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/gh-402
git add alembic/versions/*unify_spare*
git commit -m "refactor(gh-402): add Alembic migration to convert spare origin/vector to mm

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 7: Update converter regression test expectations

**Files:**
- Modify: `app/tests/test_model_schema_converters.py`

- [ ] **Step 1: Verify gh-352 and gh-362 regression tests still pass**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/gh-402 && poetry run pytest app/tests/test_model_schema_converters.py::test_spare_origin_recomputed_when_scaled_gh352 app/tests/test_model_schema_converters.py::test_spare_origin_roundtrip_consistency_gh362 app/tests/test_model_schema_converters.py::test_spare_origin_at_scale_1_matches_geometry_gh362 app/tests/test_model_schema_converters.py::test_follow_mode_spare_roundtrip_consistency_gh362 -xvs`

Expected: These tests operate on the converter layer (`wing_model_to_wing_config`) which is NOT changing. They should all PASS without modifications. The converter always recomputes from geometry — it doesn't go through `_sync_spares_for_xsec` or `_convert_spare_to_meters`.

If any test fails, investigate and fix — these are regression guards.

- [ ] **Step 2: Run the full test suite**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/gh-402 && poetry run pytest -x -q --timeout=60 -m "not slow"`

Expected: All tests pass. No regressions.

- [ ] **Step 3: Commit (only if test changes were needed)**

If any tests needed updating:

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/gh-402
git add app/tests/test_model_schema_converters.py
git commit -m "test(gh-402): update converter test expectations for mm DB storage

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```
