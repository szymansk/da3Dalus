# GH-298: Transactional get_db — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move transaction boundaries from services into the `get_db` FastAPI dependency, eliminating `with db.begin():` from all services and endpoints and unblocking ~49 xfailed tests.

**Architecture:** Make `get_db()` commit on successful request completion and rollback on exception. Remove all `with db.begin():` wrappers from `wing_service`, `aeroplane_service`, and `fuselages` endpoints. Remove the `db.rollback()` workaround in `get_wing_design_model()`. Existing explicit `db.commit()`/`db.rollback()` in other services are redundant but harmless — leave them for a separate cleanup ticket.

**Tech Stack:** SQLAlchemy 2.0, FastAPI, pytest

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `app/db/session.py` | Add commit/rollback to `get_db()` |
| Modify | `app/tests/conftest.py` | Mirror transactional pattern in test `override_get_db` |
| Modify | `app/services/wing_service.py` | Remove 22x `with db.begin():`, clean up `get_wing_design_model()` |
| Modify | `app/services/aeroplane_service.py` | Remove 3x `with db.begin():` |
| Modify | `app/api/v2/endpoints/aeroplane/fuselages.py` | Remove 7x `with db.begin():` |
| Modify | `app/api/v2/endpoints/operating_points.py` | Remove 6x explicit `db.commit()` (endpoint-level, same pattern) |
| Modify | `app/tests/test_wing_service_extended.py` | Remove all `@pytest.mark.xfail` gh-298 markers |

---

### Task 1: Make `get_db()` transactional

**Files:**
- Modify: `app/db/session.py:14-19`
- Test: `app/tests/test_session_dependency.py` (create)

- [ ] **Step 1: Write the failing test**

Create `app/tests/test_session_dependency.py`:

```python
"""Tests for the get_db dependency's transaction management."""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db


@pytest.fixture()
def _patched_session(monkeypatch):
    """Patch SessionLocal to use in-memory SQLite."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    patched = sessionmaker(
        bind=engine, class_=Session, expire_on_commit=False,
        autocommit=False, autoflush=False,
    )
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr("app.db.session.SessionLocal", patched)
    yield engine
    Base.metadata.drop_all(bind=engine)


class TestGetDbTransactionManagement:
    def test_commits_on_success(self, _patched_session):
        gen = get_db()
        db = next(gen)
        db.execute(text(
            "CREATE TABLE _txn_test (id INTEGER PRIMARY KEY)"
        ))
        db.execute(text("INSERT INTO _txn_test (id) VALUES (1)"))
        try:
            gen.send(None)
        except StopIteration:
            pass
        # Verify data persisted
        with _patched_session.connect() as conn:
            row = conn.execute(text("SELECT id FROM _txn_test")).fetchone()
            assert row is not None
            assert row[0] == 1

    def test_rollbacks_on_exception(self, _patched_session):
        gen = get_db()
        db = next(gen)
        db.execute(text(
            "CREATE TABLE _txn_test2 (id INTEGER PRIMARY KEY)"
        ))
        db.execute(text("INSERT INTO _txn_test2 (id) VALUES (99)"))
        with pytest.raises(ValueError, match="boom"):
            gen.throw(ValueError("boom"))
        # Verify data was rolled back — table may not exist or row absent
        with _patched_session.connect() as conn:
            try:
                row = conn.execute(text("SELECT id FROM _txn_test2")).fetchone()
                assert row is None
            except Exception:
                pass  # table itself was rolled back
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest app/tests/test_session_dependency.py -v`
Expected: `test_commits_on_success` FAILS (no commit happens), `test_rollbacks_on_exception` may pass or fail.

- [ ] **Step 3: Implement the transactional `get_db()`**

In `app/db/session.py`, replace `get_db`:

```python
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest app/tests/test_session_dependency.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite to check for regressions**

Run: `poetry run pytest -x -q`
Expected: All previously-passing tests still pass. xfailed tests may now pass (xpass) — that's expected and will be cleaned up in Task 6.

- [ ] **Step 6: Commit**

```
git add app/db/session.py app/tests/test_session_dependency.py
git commit -m "feat(gh-298): make get_db() transactional — commit on success, rollback on error"
```

---

### Task 2: Mirror transactional pattern in test conftest

**Files:**
- Modify: `app/tests/conftest.py:73-78`

- [ ] **Step 1: Update `override_get_db` in conftest**

In `app/tests/conftest.py`, replace the `override_get_db` function inside `client_and_db`:

```python
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
```

- [ ] **Step 2: Run test suite to verify no regressions**

Run: `poetry run pytest -x -q`
Expected: All previously-passing tests still pass.

- [ ] **Step 3: Commit**

```
git add app/tests/conftest.py
git commit -m "feat(gh-298): mirror transactional get_db pattern in test conftest"
```

---

### Task 3: Remove `with db.begin():` from `wing_service.py`

**Files:**
- Modify: `app/services/wing_service.py` (22 occurrences at lines 237, 281, 395, 440, 488, 543, 630, 690, 761, 856, 888, 919, 978, 1013, 1060, 1086, 1149, 1177, 1246, 1293, 1346, 1388)

- [ ] **Step 1: Remove all `with db.begin():` wrappers**

For each of the 22 write functions, unwrap `with db.begin():` — remove the context manager line and dedent the body one level. The try/except structure around it stays.

**Pattern — before:**
```python
    try:
        with db.begin():
            plane = get_aeroplane_or_raise(db, aeroplane_uuid)
            # ... work ...
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(...)
        raise InternalError(...)
```

**Pattern — after:**
```python
    try:
        plane = get_aeroplane_or_raise(db, aeroplane_uuid)
        # ... work ...
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error(...)
        raise InternalError(...)
```

Apply this transformation to all 22 functions listed above.

- [ ] **Step 2: Clean up `get_wing_design_model()` (lines 98–133)**

Remove all three `db.rollback()` calls and the docstring reference to rolling back implicit transactions. The function becomes a simple read:

```python
def get_wing_design_model(db: Session, aeroplane_uuid, wing_name: str) -> str | None:
    """Return the design_model of an existing wing, or None if the wing does not exist."""
    from sqlalchemy import select

    try:
        plane_exists = db.execute(
            select(AeroplaneModel.id).filter(AeroplaneModel.uuid == aeroplane_uuid)
        ).scalar_one_or_none()
        if plane_exists is None:
            raise NotFoundError(
                message="Aeroplane not found",
                details={"aeroplane_id": str(aeroplane_uuid)},
            )

        return db.execute(
            select(WingModel.design_model)
            .join(AeroplaneModel, WingModel.aeroplane_id == AeroplaneModel.id)
            .filter(AeroplaneModel.uuid == aeroplane_uuid, WingModel.name == wing_name)
        ).scalar_one_or_none()
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting wing design_model: {e}")
        raise InternalError(message="Failed to query wing design model")
```

- [ ] **Step 3: Run test suite**

Run: `poetry run pytest -x -q`
Expected: All previously-passing tests still pass.

- [ ] **Step 4: Commit**

```
git add app/services/wing_service.py
git commit -m "refactor(gh-298): remove with db.begin() from wing_service — transactions handled by get_db"
```

---

### Task 4: Remove `with db.begin():` from `aeroplane_service.py`

**Files:**
- Modify: `app/services/aeroplane_service.py` (3 occurrences: `create_aeroplane` line 65, `delete_aeroplane` line 149, `set_aeroplane_mass` line 198)

- [ ] **Step 1: Unwrap `create_aeroplane` (line 65)**

Before:
```python
    try:
        aeroplane = AeroplaneModel(name=name)
        with db.begin():
            db.add(aeroplane)
            db.flush()
            db.refresh(aeroplane)
        return aeroplane
```

After:
```python
    try:
        aeroplane = AeroplaneModel(name=name)
        db.add(aeroplane)
        db.flush()
        db.refresh(aeroplane)
        return aeroplane
```

- [ ] **Step 2: Unwrap `delete_aeroplane` (line 149) and `set_aeroplane_mass` (line 198)**

Same pattern: remove `with db.begin():` line, dedent body.

- [ ] **Step 3: Run test suite**

Run: `poetry run pytest -x -q`
Expected: All previously-passing tests still pass.

- [ ] **Step 4: Commit**

```
git add app/services/aeroplane_service.py
git commit -m "refactor(gh-298): remove with db.begin() from aeroplane_service"
```

---

### Task 5: Remove `with db.begin():` from fuselages endpoint and `db.commit()` from operating_points

**Files:**
- Modify: `app/api/v2/endpoints/aeroplane/fuselages.py` (7 occurrences at lines 89, 143, 232, 320, 414, 480, 530)
- Modify: `app/api/v2/endpoints/operating_points.py` (6 occurrences: lines 106, 149, 160, 171, 207, 218)

- [ ] **Step 1: Unwrap all `with db.begin():` in fuselages.py**

Same pattern as Tasks 3–4: remove the context manager line, dedent the body. Keep the try/except structure.

- [ ] **Step 2: Remove explicit `db.commit()` calls from operating_points.py**

These 6 endpoints use bare `db.commit()` without try/except — `get_db()` now handles this. Remove each `db.commit()` line. Keep `db.refresh()` calls since they're needed before returning the object.

**Example — before:**
```python
def create_operating_point(op_data, db):
    op = OperatingPointModel(**op_data.model_dump())
    db.add(op)
    db.commit()
    db.refresh(op)
    return op
```

**After:**
```python
def create_operating_point(op_data, db):
    op = OperatingPointModel(**op_data.model_dump())
    db.add(op)
    db.flush()
    db.refresh(op)
    return op
```

Note: Replace `db.commit()` with `db.flush()` (not just delete) when followed by `db.refresh()`, because `refresh` needs the row to exist in the DB. `flush()` sends the INSERT without committing — `get_db()` commits at request end.

- [ ] **Step 3: Run test suite**

Run: `poetry run pytest -x -q`
Expected: All previously-passing tests still pass.

- [ ] **Step 4: Commit**

```
git add app/api/v2/endpoints/aeroplane/fuselages.py app/api/v2/endpoints/operating_points.py
git commit -m "refactor(gh-298): remove db.begin/commit from fuselages and operating_points endpoints"
```

---

### Task 6: Remove xfail markers and verify all tests pass

**Files:**
- Modify: `app/tests/test_wing_service_extended.py` (remove ~50 `@pytest.mark.xfail` decorators)

- [ ] **Step 1: Remove all xfail markers referencing gh-298**

Search for all lines matching:
```
@pytest.mark.xfail(reason="service uses db.begin() — needs autobegin=False session fixture (gh-298)", strict=False)
```

Delete each matching line.

- [ ] **Step 2: Run the previously-xfailed tests**

Run: `poetry run pytest app/tests/test_wing_service_extended.py -v`
Expected: All tests PASS (no xfail, no failures).

- [ ] **Step 3: Run full test suite**

Run: `poetry run pytest -x -q`
Expected: All tests pass, zero xfail remaining for gh-298.

- [ ] **Step 4: Commit**

```
git add app/tests/test_wing_service_extended.py
git commit -m "test(gh-298): remove xfail markers — all wing_service tests now pass"
```

---

### Task 7: Update CLAUDE.md and verify end-to-end

**Files:**
- Modify: `CLAUDE.md` (remove the `wing_service` db.begin() note)

- [ ] **Step 1: Remove the obsolete note from CLAUDE.md**

Find and remove:
```
- **`wing_service` uses `with db.begin():`** in all write
  operations. Direct service-level tests must use a session with
  `autobegin=False` or go through the REST API via `TestClient`.
  See gh-298.
```

Replace with:
```
- **Transaction management** is handled by the `get_db()` dependency
  in `app/db/session.py` — it commits on success and rollbacks on
  exception. Services must not call `db.begin()`.
```

- [ ] **Step 2: Run full test suite one final time**

Run: `poetry run pytest -q`
Expected: All tests pass.

- [ ] **Step 3: Commit**

```
git add CLAUDE.md
git commit -m "docs(gh-298): update CLAUDE.md — document transactional get_db pattern"
```

---

## Verification

After all tasks are complete:

1. `poetry run pytest -q` — all tests pass, no xfail for gh-298
2. `poetry run pytest app/tests/test_wing_service_extended.py -v` — all ~100 tests pass
3. `poetry run pytest app/tests/test_session_dependency.py -v` — transaction tests pass
4. `grep -r "db.begin()" app/` — zero results
5. `grep -r "gh-298" app/tests/` — zero results
6. Start the dev server: `poetry run uvicorn app.main:app --port 8001` — create/update/delete a wing via Swagger UI to verify end-to-end
