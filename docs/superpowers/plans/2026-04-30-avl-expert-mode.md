# AVL Expert Mode — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an Expert Mode that lets users view, edit, and persist AVL geometry files (`.avl`) via a Monaco Editor, with dirty-flag tracking and diff-view for geometry changes.

**Architecture:** New `AvlGeometryFileModel` table with SQLAlchemy event hooks on geometry models to auto-set a dirty flag. New service + 4 REST endpoints. Frontend: Monaco Editor in a fullscreen-capable dialog, with AVL syntax highlighting and DiffEditor for dirty files. AVL analyses check for user-edited geometry before running.

**Tech Stack:** SQLAlchemy, Alembic, FastAPI, Pydantic v2, aerosandbox, `@monaco-editor/react`, Next.js App Router, Tailwind CSS

---

## File Structure

### Backend — New Files

| File | Responsibility |
|------|---------------|
| `app/models/avl_geometry_file.py` | SQLAlchemy model for `avl_geometry_files` table |
| `app/models/avl_geometry_events.py` | SQLAlchemy event listeners for dirty-flag propagation |
| `app/schemas/avl_geometry.py` | Pydantic request/response schemas |
| `app/services/avl_geometry_service.py` | Business logic: CRUD + AVL file generation |
| `app/api/v2/endpoints/aeroplane/avl_geometry.py` | REST endpoints (GET/PUT/POST/DELETE) |
| `alembic/versions/xxxx_add_avl_geometry_files.py` | Migration for the new table |

### Backend — Modified Files

| File | Change |
|------|--------|
| `app/api/v2/endpoints/aeroplane/__init__.py` | Include `avl_geometry` router |
| `app/services/avl_strip_forces.py` | Accept optional pre-built `.avl` content |
| `app/services/analysis_service.py` | Check for user-edited geometry before AVL runs |
| `app/api/utils.py` | Accept optional `.avl` content in `_run_avl` |

### Frontend — New Files

| File | Responsibility |
|------|---------------|
| `frontend/components/workbench/AvlGeometryEditor.tsx` | Monaco Editor dialog with save/reset/fullscreen |
| `frontend/components/workbench/AvlDirtyWarning.tsx` | Warning dialog: "View Diff" / "Regenerate" |
| `frontend/components/workbench/avlLanguage.ts` | Monarch tokenizer for AVL syntax highlighting |
| `frontend/hooks/useAvlGeometry.ts` | SWR hook for GET + mutation helpers (PUT/POST/DELETE) |

### Frontend — Modified Files

| File | Change |
|------|--------|
| `frontend/app/workbench/analysis/page.tsx` | Wire up editor dialog state + pass aeroplaneId |
| `frontend/components/workbench/AnalysisViewerPanel.tsx` | Add "Edit AVL Geometry" button in header |
| `frontend/package.json` | Add `@monaco-editor/react` dependency |

---

## Task 1: Database Model & Migration

**Files:**
- Create: `app/models/avl_geometry_file.py`
- Create: `alembic/versions/xxxx_add_avl_geometry_files.py`
- Test: `app/tests/test_avl_geometry.py`

- [ ] **Step 1: Write failing test for model creation**

```python
# app/tests/test_avl_geometry.py
import uuid
import pytest
from sqlalchemy.orm import Session
from app.models.avl_geometry_file import AvlGeometryFileModel
from app.models.aeroplanemodel import AeroplaneModel


class TestAvlGeometryFileModel:
    def test_create_avl_geometry_file(self, db: Session):
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        geom = AvlGeometryFileModel(
            aeroplane_id=aeroplane.id,
            content="SURFACE\nWing\n",
        )
        db.add(geom)
        db.flush()

        assert geom.id is not None
        assert geom.content == "SURFACE\nWing\n"
        assert geom.is_dirty is False
        assert geom.is_user_edited is False
        assert geom.created_at is not None
        assert geom.updated_at is not None

    def test_unique_aeroplane_constraint(self, db: Session):
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        geom1 = AvlGeometryFileModel(aeroplane_id=aeroplane.id, content="v1")
        db.add(geom1)
        db.flush()

        geom2 = AvlGeometryFileModel(aeroplane_id=aeroplane.id, content="v2")
        db.add(geom2)
        with pytest.raises(Exception):
            db.flush()

    def test_cascade_delete(self, db: Session):
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        geom = AvlGeometryFileModel(aeroplane_id=aeroplane.id, content="data")
        db.add(geom)
        db.flush()
        geom_id = geom.id

        db.delete(aeroplane)
        db.flush()

        assert db.get(AvlGeometryFileModel, geom_id) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest app/tests/test_avl_geometry.py -v -x`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.avl_geometry_file'`

- [ ] **Step 3: Create the SQLAlchemy model**

```python
# app/models/avl_geometry_file.py
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class AvlGeometryFileModel(Base):
    __tablename__ = "avl_geometry_files"
    __table_args__ = (
        UniqueConstraint("aeroplane_id", name="uq_avl_geometry_files_aeroplane_id"),
    )

    aeroplane_id = Column(
        Integer,
        ForeignKey("aeroplanes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content = Column(Text, nullable=False)
    is_dirty = Column(Boolean, default=False, nullable=False)
    is_user_edited = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False,
    )

    aeroplane = relationship("AeroplaneModel", backref="avl_geometry_file")
```

- [ ] **Step 4: Generate Alembic migration**

Run: `poetry run alembic revision --autogenerate -m "add avl_geometry_files table"`
Review the generated migration, ensure it has `op.create_table` with all columns and the unique constraint.

- [ ] **Step 5: Run migration**

Run: `poetry run alembic upgrade head`

- [ ] **Step 6: Run tests to verify they pass**

Run: `poetry run pytest app/tests/test_avl_geometry.py -v -x`
Expected: All 3 tests PASS

- [ ] **Step 7: Commit**

```bash
git add app/models/avl_geometry_file.py alembic/versions/*avl_geometry* app/tests/test_avl_geometry.py
git commit -m "feat(gh-381): add AvlGeometryFileModel and migration"
```

---

## Task 2: Pydantic Schemas

**Files:**
- Create: `app/schemas/avl_geometry.py`
- Test: `app/tests/test_avl_geometry.py` (extend)

- [ ] **Step 1: Write failing test for schemas**

```python
# Append to app/tests/test_avl_geometry.py
from app.schemas.avl_geometry import AvlGeometryResponse, AvlGeometryUpdateRequest


class TestAvlGeometrySchemas:
    def test_response_schema(self):
        resp = AvlGeometryResponse(
            content="SURFACE\nWing\n",
            is_dirty=False,
            is_user_edited=True,
        )
        assert resp.content == "SURFACE\nWing\n"
        assert resp.is_dirty is False
        assert resp.is_user_edited is True

    def test_update_request_schema(self):
        req = AvlGeometryUpdateRequest(content="SURFACE\nWing\nSECTION\n")
        assert req.content == "SURFACE\nWing\nSECTION\n"

    def test_update_request_empty_content_rejected(self):
        with pytest.raises(Exception):
            AvlGeometryUpdateRequest(content="")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest app/tests/test_avl_geometry.py::TestAvlGeometrySchemas -v -x`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create schemas**

```python
# app/schemas/avl_geometry.py
from pydantic import BaseModel, Field, field_validator


class AvlGeometryResponse(BaseModel):
    content: str = Field(..., description="The .avl geometry file content")
    is_dirty: bool = Field(..., description="True if airplane geometry changed since last edit")
    is_user_edited: bool = Field(..., description="True if the user has manually edited this file")


class AvlGeometryUpdateRequest(BaseModel):
    content: str = Field(..., description="The edited .avl geometry file content", min_length=1)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest app/tests/test_avl_geometry.py::TestAvlGeometrySchemas -v -x`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/schemas/avl_geometry.py app/tests/test_avl_geometry.py
git commit -m "feat(gh-381): add Pydantic schemas for AVL geometry"
```

---

## Task 3: AVL Geometry Service

**Files:**
- Create: `app/services/avl_geometry_service.py`
- Test: `app/tests/test_avl_geometry.py` (extend)

- [ ] **Step 1: Write failing tests for service functions**

```python
# Append to app/tests/test_avl_geometry.py
from unittest.mock import patch, MagicMock
from app.services.avl_geometry_service import (
    get_avl_geometry,
    save_avl_geometry,
    regenerate_avl_geometry,
    delete_avl_geometry,
    generate_avl_content,
)
from app.core.exceptions import NotFoundError


class TestAvlGeometryService:
    def test_get_avl_geometry_no_saved_file_generates(self, db: Session):
        """When no saved file exists, generate content on the fly."""
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        with patch(
            "app.services.avl_geometry_service.generate_avl_content",
            return_value="GENERATED\nCONTENT\n",
        ):
            result = get_avl_geometry(db, aeroplane.uuid)

        assert result.content == "GENERATED\nCONTENT\n"
        assert result.is_user_edited is False
        assert result.is_dirty is False

    def test_get_avl_geometry_returns_saved(self, db: Session):
        """When a saved file exists, return it."""
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        geom = AvlGeometryFileModel(
            aeroplane_id=aeroplane.id,
            content="USER CONTENT",
            is_user_edited=True,
        )
        db.add(geom)
        db.flush()

        result = get_avl_geometry(db, aeroplane.uuid)
        assert result.content == "USER CONTENT"
        assert result.is_user_edited is True

    def test_save_avl_geometry_creates_new(self, db: Session):
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        result = save_avl_geometry(db, aeroplane.uuid, "NEW CONTENT")
        assert result.content == "NEW CONTENT"
        assert result.is_user_edited is True
        assert result.is_dirty is False

    def test_save_avl_geometry_updates_existing(self, db: Session):
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        geom = AvlGeometryFileModel(
            aeroplane_id=aeroplane.id,
            content="OLD",
            is_dirty=True,
        )
        db.add(geom)
        db.flush()

        result = save_avl_geometry(db, aeroplane.uuid, "UPDATED")
        assert result.content == "UPDATED"
        assert result.is_dirty is False
        assert result.is_user_edited is True

    def test_regenerate_returns_fresh_content(self, db: Session):
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        with patch(
            "app.services.avl_geometry_service.generate_avl_content",
            return_value="FRESH\nGENERATED\n",
        ):
            result = regenerate_avl_geometry(db, aeroplane.uuid)

        assert result.content == "FRESH\nGENERATED\n"
        assert result.is_user_edited is False

    def test_delete_avl_geometry(self, db: Session):
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        geom = AvlGeometryFileModel(aeroplane_id=aeroplane.id, content="DATA")
        db.add(geom)
        db.flush()

        delete_avl_geometry(db, aeroplane.uuid)
        assert (
            db.query(AvlGeometryFileModel)
            .filter_by(aeroplane_id=aeroplane.id)
            .first()
            is None
        )

    def test_delete_avl_geometry_not_found(self, db: Session):
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        with pytest.raises(NotFoundError):
            delete_avl_geometry(db, aeroplane.uuid)

    def test_get_avl_geometry_aeroplane_not_found(self, db: Session):
        with pytest.raises(NotFoundError):
            get_avl_geometry(db, uuid.uuid4())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest app/tests/test_avl_geometry.py::TestAvlGeometryService -v -x`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement the service**

```python
# app/services/avl_geometry_service.py
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import InternalError, NotFoundError
from app.db.exceptions import NotFoundInDbException
from app.db.repository import get_aeroplane_by_id
from app.models.avl_geometry_file import AvlGeometryFileModel
from app.models.aeroplanemodel import AeroplaneModel
from app.schemas.avl_geometry import AvlGeometryResponse

logger = logging.getLogger(__name__)


def _get_aeroplane_or_raise(db: Session, aeroplane_uuid) -> AeroplaneModel:
    try:
        aeroplane = (
            db.query(AeroplaneModel)
            .filter(AeroplaneModel.uuid == aeroplane_uuid)
            .first()
        )
    except SQLAlchemyError as e:
        logger.error("Database error looking up aeroplane: %s", e)
        raise InternalError(message=f"Database error: {e}")
    if aeroplane is None:
        raise NotFoundError(entity="Aeroplane", resource_id=aeroplane_uuid)
    return aeroplane


def generate_avl_content(db: Session, aeroplane_uuid) -> str:
    import aerosandbox as asb

    from app.converters.model_schema_converters import aeroplane_schema_to_asb_airplane_async
    from app.services.analysis_service import get_aeroplane_schema_or_raise

    plane_schema = get_aeroplane_schema_or_raise(db, aeroplane_uuid)
    asb_airplane = aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)

    op_point = asb.OperatingPoint(velocity=10, alpha=0)
    avl = asb.AVL(airplane=asb_airplane, op_point=op_point)

    with tempfile.TemporaryDirectory() as tmp_dir:
        avl_path = Path(tmp_dir) / "airplane.avl"
        avl.write_avl(avl_path)
        return avl_path.read_text()


def get_avl_geometry(db: Session, aeroplane_uuid) -> AvlGeometryResponse:
    aeroplane = _get_aeroplane_or_raise(db, aeroplane_uuid)

    geom = (
        db.query(AvlGeometryFileModel)
        .filter_by(aeroplane_id=aeroplane.id)
        .first()
    )
    if geom is not None:
        return AvlGeometryResponse(
            content=geom.content,
            is_dirty=geom.is_dirty,
            is_user_edited=geom.is_user_edited,
        )

    content = generate_avl_content(db, aeroplane_uuid)
    return AvlGeometryResponse(
        content=content,
        is_dirty=False,
        is_user_edited=False,
    )


def save_avl_geometry(db: Session, aeroplane_uuid, content: str) -> AvlGeometryResponse:
    aeroplane = _get_aeroplane_or_raise(db, aeroplane_uuid)

    geom = (
        db.query(AvlGeometryFileModel)
        .filter_by(aeroplane_id=aeroplane.id)
        .first()
    )
    if geom is None:
        geom = AvlGeometryFileModel(aeroplane_id=aeroplane.id, content=content)
        db.add(geom)
    else:
        geom.content = content

    geom.is_user_edited = True
    geom.is_dirty = False
    db.flush()

    return AvlGeometryResponse(
        content=geom.content,
        is_dirty=geom.is_dirty,
        is_user_edited=geom.is_user_edited,
    )


def regenerate_avl_geometry(db: Session, aeroplane_uuid) -> AvlGeometryResponse:
    _get_aeroplane_or_raise(db, aeroplane_uuid)
    content = generate_avl_content(db, aeroplane_uuid)
    return AvlGeometryResponse(
        content=content,
        is_dirty=False,
        is_user_edited=False,
    )


def delete_avl_geometry(db: Session, aeroplane_uuid) -> None:
    aeroplane = _get_aeroplane_or_raise(db, aeroplane_uuid)

    geom = (
        db.query(AvlGeometryFileModel)
        .filter_by(aeroplane_id=aeroplane.id)
        .first()
    )
    if geom is None:
        raise NotFoundError(entity="AVL geometry file", resource_id=aeroplane_uuid)

    db.delete(geom)
    db.flush()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest app/tests/test_avl_geometry.py::TestAvlGeometryService -v -x`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/avl_geometry_service.py app/tests/test_avl_geometry.py
git commit -m "feat(gh-381): add AVL geometry service with CRUD + generation"
```

---

## Task 4: SQLAlchemy Event Hooks for Dirty Flag

**Files:**
- Create: `app/models/avl_geometry_events.py`
- Modify: `app/models/__init__.py` or `app/main.py` (import to register)
- Test: `app/tests/test_avl_geometry.py` (extend)

- [ ] **Step 1: Write failing test for dirty-flag propagation**

```python
# Append to app/tests/test_avl_geometry.py
from app.models.aeroplanemodel import WingModel, WingXSecModel, FuselageModel
import app.models.avl_geometry_events  # noqa: F401 — registers event listeners


class TestAvlGeometryDirtyFlag:
    def test_wing_insert_sets_dirty(self, db: Session):
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        geom = AvlGeometryFileModel(
            aeroplane_id=aeroplane.id,
            content="ORIGINAL",
            is_user_edited=True,
            is_dirty=False,
        )
        db.add(geom)
        db.flush()

        wing = WingModel(name="Main Wing", aeroplane_id=aeroplane.id)
        db.add(wing)
        db.flush()

        db.refresh(geom)
        assert geom.is_dirty is True

    def test_wing_update_sets_dirty(self, db: Session):
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        wing = WingModel(name="Main Wing", aeroplane_id=aeroplane.id)
        db.add(wing)
        db.flush()

        geom = AvlGeometryFileModel(
            aeroplane_id=aeroplane.id,
            content="ORIGINAL",
            is_user_edited=True,
            is_dirty=False,
        )
        db.add(geom)
        db.flush()

        wing.name = "Updated Wing"
        db.flush()

        db.refresh(geom)
        assert geom.is_dirty is True

    def test_wing_delete_sets_dirty(self, db: Session):
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        wing = WingModel(name="Main Wing", aeroplane_id=aeroplane.id)
        db.add(wing)
        db.flush()

        geom = AvlGeometryFileModel(
            aeroplane_id=aeroplane.id,
            content="ORIGINAL",
            is_user_edited=True,
            is_dirty=False,
        )
        db.add(geom)
        db.flush()

        db.delete(wing)
        db.flush()

        db.refresh(geom)
        assert geom.is_dirty is True

    def test_no_geom_file_no_error(self, db: Session):
        """Event fires but no geometry file exists — should be a no-op."""
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        wing = WingModel(name="Main Wing", aeroplane_id=aeroplane.id)
        db.add(wing)
        db.flush()  # Should not raise
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest app/tests/test_avl_geometry.py::TestAvlGeometryDirtyFlag -v -x`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement event listeners**

```python
# app/models/avl_geometry_events.py
"""SQLAlchemy event listeners that mark AVL geometry files as dirty
when the airplane's wing or fuselage geometry changes."""

from __future__ import annotations

import logging

from sqlalchemy import event, update
from sqlalchemy.orm import Session

from app.models.aeroplanemodel import FuselageModel, WingModel, WingXSecModel
from app.models.avl_geometry_file import AvlGeometryFileModel

logger = logging.getLogger(__name__)

_GEOMETRY_MODELS = (WingModel, WingXSecModel, FuselageModel)


def _mark_dirty(session: Session, aeroplane_id: int | None) -> None:
    if aeroplane_id is None:
        return
    session.execute(
        update(AvlGeometryFileModel)
        .where(AvlGeometryFileModel.aeroplane_id == aeroplane_id)
        .values(is_dirty=True)
    )


def _resolve_aeroplane_id(target) -> int | None:
    if isinstance(target, (WingModel, FuselageModel)):
        return target.aeroplane_id
    if isinstance(target, WingXSecModel) and target.wing is not None:
        return target.wing.aeroplane_id
    return None


def _on_geometry_change(mapper, connection, target):
    session = Session.object_session(target)
    if session is None:
        return
    aeroplane_id = _resolve_aeroplane_id(target)
    _mark_dirty(session, aeroplane_id)


for _model in _GEOMETRY_MODELS:
    for _event_name in ("after_insert", "after_update", "after_delete"):
        event.listen(_model, _event_name, _on_geometry_change)
```

- [ ] **Step 4: Register the event module**

The events must be imported at application startup. Add the import to `app/main.py`:

Find the existing import block in `app/main.py` and add:

```python
import app.models.avl_geometry_events  # noqa: F401 — register dirty-flag listeners
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `poetry run pytest app/tests/test_avl_geometry.py::TestAvlGeometryDirtyFlag -v -x`
Expected: All 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add app/models/avl_geometry_events.py app/main.py app/tests/test_avl_geometry.py
git commit -m "feat(gh-381): add SQLAlchemy event hooks for AVL dirty flag"
```

---

## Task 5: REST API Endpoints

**Files:**
- Create: `app/api/v2/endpoints/aeroplane/avl_geometry.py`
- Modify: `app/api/v2/endpoints/aeroplane/__init__.py`
- Test: `app/tests/test_avl_geometry.py` (extend)

- [ ] **Step 1: Write failing endpoint tests**

```python
# Append to app/tests/test_avl_geometry.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestAvlGeometryEndpoints:
    def _create_aeroplane(self) -> str:
        resp = client.post("/aeroplanes", params={"name": "TestPlane"})
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_get_avl_geometry_generates_on_first_access(self):
        aeroplane_id = self._create_aeroplane()
        with patch(
            "app.services.avl_geometry_service.generate_avl_content",
            return_value="GENERATED\n",
        ):
            resp = client.get(f"/aeroplanes/{aeroplane_id}/avl-geometry")
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == "GENERATED\n"
        assert data["is_user_edited"] is False

    def test_put_saves_geometry(self):
        aeroplane_id = self._create_aeroplane()
        resp = client.put(
            f"/aeroplanes/{aeroplane_id}/avl-geometry",
            json={"content": "EDITED CONTENT"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == "EDITED CONTENT"
        assert data["is_user_edited"] is True

    def test_put_then_get_returns_saved(self):
        aeroplane_id = self._create_aeroplane()
        client.put(
            f"/aeroplanes/{aeroplane_id}/avl-geometry",
            json={"content": "SAVED"},
        )
        resp = client.get(f"/aeroplanes/{aeroplane_id}/avl-geometry")
        assert resp.status_code == 200
        assert resp.json()["content"] == "SAVED"

    def test_regenerate_returns_fresh(self):
        aeroplane_id = self._create_aeroplane()
        with patch(
            "app.services.avl_geometry_service.generate_avl_content",
            return_value="REGENERATED\n",
        ):
            resp = client.post(f"/aeroplanes/{aeroplane_id}/avl-geometry/regenerate")
        assert resp.status_code == 200
        assert resp.json()["content"] == "REGENERATED\n"

    def test_delete_removes_file(self):
        aeroplane_id = self._create_aeroplane()
        client.put(
            f"/aeroplanes/{aeroplane_id}/avl-geometry",
            json={"content": "TO DELETE"},
        )
        resp = client.delete(f"/aeroplanes/{aeroplane_id}/avl-geometry")
        assert resp.status_code == 204

    def test_delete_not_found(self):
        aeroplane_id = self._create_aeroplane()
        resp = client.delete(f"/aeroplanes/{aeroplane_id}/avl-geometry")
        assert resp.status_code == 404

    def test_get_not_found_aeroplane(self):
        resp = client.get(f"/aeroplanes/00000000-0000-0000-0000-000000000000/avl-geometry")
        assert resp.status_code == 404

    def test_put_empty_content_rejected(self):
        aeroplane_id = self._create_aeroplane()
        resp = client.put(
            f"/aeroplanes/{aeroplane_id}/avl-geometry",
            json={"content": ""},
        )
        assert resp.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest app/tests/test_avl_geometry.py::TestAvlGeometryEndpoints -v -x`
Expected: FAIL — 404 on `/aeroplanes/{id}/avl-geometry` (endpoint doesn't exist yet)

- [ ] **Step 3: Create endpoint module**

```python
# app/api/v2/endpoints/aeroplane/avl_geometry.py
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.core.exceptions import ServiceException
from app.db.session import get_db
from app.schemas.avl_geometry import AvlGeometryResponse, AvlGeometryUpdateRequest
from app.services import avl_geometry_service

from .base import _raise_http_from_domain

router = APIRouter()


@router.get(
    "/aeroplanes/{aeroplane_id}/avl-geometry",
    status_code=status.HTTP_200_OK,
    tags=["avl-geometry"],
    operation_id="get_avl_geometry",
)
async def get_avl_geometry(
    aeroplane_id: UUID4,
    db: Annotated[Session, Depends(get_db)],
) -> AvlGeometryResponse:
    try:
        return avl_geometry_service.get_avl_geometry(db, aeroplane_id)
    except ServiceException as exc:
        _raise_http_from_domain(exc)


@router.put(
    "/aeroplanes/{aeroplane_id}/avl-geometry",
    status_code=status.HTTP_200_OK,
    tags=["avl-geometry"],
    operation_id="save_avl_geometry",
)
async def save_avl_geometry(
    aeroplane_id: UUID4,
    body: AvlGeometryUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AvlGeometryResponse:
    try:
        return avl_geometry_service.save_avl_geometry(db, aeroplane_id, body.content)
    except ServiceException as exc:
        _raise_http_from_domain(exc)


@router.post(
    "/aeroplanes/{aeroplane_id}/avl-geometry/regenerate",
    status_code=status.HTTP_200_OK,
    tags=["avl-geometry"],
    operation_id="regenerate_avl_geometry",
)
async def regenerate_avl_geometry(
    aeroplane_id: UUID4,
    db: Annotated[Session, Depends(get_db)],
) -> AvlGeometryResponse:
    try:
        return avl_geometry_service.regenerate_avl_geometry(db, aeroplane_id)
    except ServiceException as exc:
        _raise_http_from_domain(exc)


@router.delete(
    "/aeroplanes/{aeroplane_id}/avl-geometry",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["avl-geometry"],
    operation_id="delete_avl_geometry",
)
async def delete_avl_geometry(
    aeroplane_id: UUID4,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    try:
        avl_geometry_service.delete_avl_geometry(db, aeroplane_id)
    except ServiceException as exc:
        _raise_http_from_domain(exc)
```

- [ ] **Step 4: Register the router**

In `app/api/v2/endpoints/aeroplane/__init__.py`, add:

```python
from .avl_geometry import router as avl_geometry_router
```

And:

```python
router.include_router(avl_geometry_router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `poetry run pytest app/tests/test_avl_geometry.py::TestAvlGeometryEndpoints -v -x`
Expected: All 9 tests PASS

- [ ] **Step 6: Commit**

```bash
git add app/api/v2/endpoints/aeroplane/avl_geometry.py app/api/v2/endpoints/aeroplane/__init__.py app/tests/test_avl_geometry.py
git commit -m "feat(gh-381): add AVL geometry REST endpoints"
```

---

## Task 6: AVL Analysis Integration

**Files:**
- Modify: `app/services/avl_strip_forces.py`
- Modify: `app/services/analysis_service.py`
- Modify: `app/api/utils.py`
- Test: `app/tests/test_avl_geometry.py` (extend)

- [ ] **Step 1: Write failing test for analysis integration**

```python
# Append to app/tests/test_avl_geometry.py
from app.services.avl_geometry_service import _get_aeroplane_or_raise


class TestAvlAnalysisIntegration:
    def test_strip_forces_uses_saved_geometry(self, db: Session):
        """When is_user_edited=True, the saved content should be used."""
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        geom = AvlGeometryFileModel(
            aeroplane_id=aeroplane.id,
            content="CUSTOM AVL CONTENT",
            is_user_edited=True,
            is_dirty=False,
        )
        db.add(geom)
        db.flush()

        from app.services.avl_geometry_service import get_user_avl_content
        content = get_user_avl_content(db, aeroplane.uuid)
        assert content == "CUSTOM AVL CONTENT"

    def test_strip_forces_returns_none_when_not_edited(self, db: Session):
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        from app.services.avl_geometry_service import get_user_avl_content
        content = get_user_avl_content(db, aeroplane.uuid)
        assert content is None

    def test_strip_forces_returns_none_when_dirty(self, db: Session):
        """Dirty files should not be used — fall back to generation."""
        aeroplane = AeroplaneModel(name="TestPlane")
        db.add(aeroplane)
        db.flush()

        geom = AvlGeometryFileModel(
            aeroplane_id=aeroplane.id,
            content="STALE CONTENT",
            is_user_edited=True,
            is_dirty=True,
        )
        db.add(geom)
        db.flush()

        from app.services.avl_geometry_service import get_user_avl_content
        content = get_user_avl_content(db, aeroplane.uuid)
        assert content is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest app/tests/test_avl_geometry.py::TestAvlAnalysisIntegration -v -x`
Expected: FAIL — `ImportError: cannot import name 'get_user_avl_content'`

- [ ] **Step 3: Add helper function to the service**

Append to `app/services/avl_geometry_service.py`:

```python
def get_user_avl_content(db: Session, aeroplane_uuid) -> str | None:
    """Return the user-edited AVL content if it exists and is not dirty.

    Used by analysis functions to decide whether to use saved geometry
    or generate fresh.
    """
    aeroplane = _get_aeroplane_or_raise(db, aeroplane_uuid)
    geom = (
        db.query(AvlGeometryFileModel)
        .filter_by(aeroplane_id=aeroplane.id)
        .first()
    )
    if geom is None or not geom.is_user_edited or geom.is_dirty:
        return None
    return geom.content
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest app/tests/test_avl_geometry.py::TestAvlAnalysisIntegration -v -x`
Expected: All 3 tests PASS

- [ ] **Step 5: Modify `AVLWithStripForces.run()` to accept pre-built content**

In `app/services/avl_strip_forces.py`, modify the `AVLWithStripForces` class to accept an optional `avl_file_content` parameter:

In the `__init__` method (or add one), store the content:

```python
def __init__(self, *args, avl_file_content: str | None = None, **kwargs):
    super().__init__(*args, **kwargs)
    self._avl_file_content = avl_file_content
```

In the `run()` method, replace the `self.write_avl(directory / airplane_file)` line (line 188):

```python
if self._avl_file_content is not None:
    (directory / airplane_file).write_text(self._avl_file_content)
else:
    self.write_avl(directory / airplane_file)
```

- [ ] **Step 6: Modify `analyze_airplane_strip_forces` in `analysis_service.py`**

In `app/services/analysis_service.py`, at line ~1415 (after getting the plane schema), add the geometry file lookup:

```python
from app.services.avl_geometry_service import get_user_avl_content

# After: plane_schema = get_aeroplane_schema_or_raise(db, aeroplane_uuid)
user_avl_content = get_user_avl_content(db, aeroplane_uuid)
```

Then pass it to `AVLWithStripForces` at line ~1436:

```python
avl = AVLWithStripForces(
    airplane=asb_airplane,
    op_point=op_point,
    xyz_ref=operating_point.xyz_ref,
    avl_command=avl_command,
    timeout=60,
    avl_file_content=user_avl_content,
)
```

- [ ] **Step 7: Modify `_run_avl` in `app/api/utils.py`**

Add an `avl_file_content` parameter to `_run_avl`:

```python
def _run_avl(asb_airplane, op_point, operating_point, avl_file_content=None):
```

When `avl_file_content` is not None, write it to a temp file and pass `working_directory` to `asb.AVL`:

```python
if avl_file_content is not None:
    import tempfile
    from pathlib import Path

    tmp_dir = tempfile.mkdtemp()
    avl_path = Path(tmp_dir) / "airplane.avl"
    avl_path.write_text(avl_file_content)
    avl = asb.AVL(
        airplane=asb_airplane,
        op_point=op_point,
        xyz_ref=operating_point.xyz_ref,
        working_directory=tmp_dir,
    )
else:
    avl = asb.AVL(airplane=asb_airplane, op_point=op_point, xyz_ref=operating_point.xyz_ref)
```

Update `analyse_aerodynamics` to accept and pass through `avl_file_content`:

```python
def analyse_aerodynamics(
    analysis_tool, operating_point, asb_airplane,
    draw_streamlines=False, backend="plotly", avl_file_content=None,
):
```

And pass it in the AVL branch:

```python
if analysis_tool == AnalysisToolUrlType.AVL:
    return _run_avl(asb_airplane, op_point, operating_point, avl_file_content)
```

- [ ] **Step 8: Modify `analyze_airplane` in `analysis_service.py`**

In the `analyze_airplane` function (line ~317), add the geometry lookup and pass-through:

```python
user_avl_content = None
if analysis_tool == AnalysisToolUrlType.AVL:
    from app.services.avl_geometry_service import get_user_avl_content
    user_avl_content = get_user_avl_content(db, aeroplane_uuid)

result, _ = analyse_aerodynamics(
    analysis_tool, operating_point, asb_airplane,
    avl_file_content=user_avl_content,
)
```

- [ ] **Step 9: Run full test suite to verify no regressions**

Run: `poetry run pytest app/tests/test_avl_geometry.py -v -x && poetry run pytest -x -q --timeout=30 -m "not slow"`
Expected: All tests PASS

- [ ] **Step 10: Commit**

```bash
git add app/services/avl_strip_forces.py app/services/analysis_service.py app/api/utils.py app/services/avl_geometry_service.py app/tests/test_avl_geometry.py
git commit -m "feat(gh-381): integrate saved AVL geometry into analysis pipeline"
```

---

## Task 7: Frontend — Install Monaco & AVL Language Definition

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/components/workbench/avlLanguage.ts`
- Test: `frontend/__tests__/avlLanguage.test.ts`

- [ ] **Step 1: Install `@monaco-editor/react`**

Run: `cd frontend && npm install @monaco-editor/react`

- [ ] **Step 2: Write failing test for AVL language tokenizer**

```typescript
// frontend/__tests__/avlLanguage.test.ts
import { describe, it, expect } from "vitest";
import { avlLanguage, avlTheme } from "@/components/workbench/avlLanguage";

describe("avlLanguage", () => {
  it("exports a Monarch language definition", () => {
    expect(avlLanguage.tokenizer).toBeDefined();
    expect(avlLanguage.tokenizer.root).toBeDefined();
    expect(avlLanguage.tokenizer.root.length).toBeGreaterThan(0);
  });

  it("defines keywords", () => {
    expect(avlLanguage.keywords).toContain("SURFACE");
    expect(avlLanguage.keywords).toContain("SECTION");
    expect(avlLanguage.keywords).toContain("BODY");
    expect(avlLanguage.keywords).toContain("CONTROL");
  });

  it("exports a dark theme", () => {
    expect(avlTheme.base).toBe("vs-dark");
    expect(avlTheme.rules.length).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd frontend && npm run test:unit -- --run avlLanguage`
Expected: FAIL — module not found

- [ ] **Step 4: Create AVL language definition**

```typescript
// frontend/components/workbench/avlLanguage.ts
import type { languages, editor } from "monaco-editor";

export const avlLanguage: languages.IMonarchLanguage & { keywords: string[] } = {
  keywords: [
    "SURFACE",
    "SECTION",
    "YDUPLICATE",
    "AFIL",
    "AFILE",
    "CLAF",
    "CDCL",
    "CONTROL",
    "BODY",
    "BFIL",
    "BFILE",
    "COMPONENT",
    "ANGLE",
    "SCALE",
    "TRANSLATE",
    "NOWAKE",
    "NOALBE",
    "NOLOAD",
    "NACA",
    "DESIGN",
    "INDEX",
  ],
  tokenizer: {
    root: [
      [/[!#].*$/, "comment"],
      [
        /[A-Z][A-Z_]+/,
        { cases: { "@keywords": "keyword", "@default": "identifier" } },
      ],
      [/-?\d+\.?\d*([eE][+-]?\d+)?/, "number"],
      [/[a-zA-Z_]\w*/, "identifier"],
    ],
  },
};

export const avlTheme: editor.IStandaloneThemeData = {
  base: "vs-dark",
  inherit: true,
  rules: [
    { token: "keyword", foreground: "FF8400", fontStyle: "bold" },
    { token: "comment", foreground: "7A7B78", fontStyle: "italic" },
    { token: "number", foreground: "30A46C" },
    { token: "identifier", foreground: "B8B9B6" },
  ],
  colors: {
    "editor.background": "#1A1A1A",
    "editor.foreground": "#FFFFFF",
    "editor.lineHighlightBackground": "#2A2A30",
    "editorLineNumber.foreground": "#7A7B78",
    "editor.selectionBackground": "#FF840033",
    "editorCursor.foreground": "#FF8400",
  },
};
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npm run test:unit -- --run avlLanguage`
Expected: All 3 tests PASS

- [ ] **Step 6: Commit**

```bash
cd frontend && git add package.json package-lock.json components/workbench/avlLanguage.ts __tests__/avlLanguage.test.ts
git commit -m "feat(gh-381): add Monaco dependency and AVL language definition"
```

---

## Task 8: Frontend — `useAvlGeometry` Hook

**Files:**
- Create: `frontend/hooks/useAvlGeometry.ts`
- Test: `frontend/__tests__/useAvlGeometry.test.ts`

- [ ] **Step 1: Write failing test for the hook**

```typescript
// frontend/__tests__/useAvlGeometry.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useAvlGeometry } from "@/hooks/useAvlGeometry";

const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("useAvlGeometry", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches geometry on mount", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          content: "SURFACE\n",
          is_dirty: false,
          is_user_edited: false,
        }),
    });

    const { result } = renderHook(() => useAvlGeometry("test-id"));

    await waitFor(() => {
      expect(result.current.content).toBe("SURFACE\n");
    });
    expect(result.current.isDirty).toBe(false);
    expect(result.current.isUserEdited).toBe(false);
  });

  it("does not fetch when aeroplaneId is null", () => {
    renderHook(() => useAvlGeometry(null));
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("save sends PUT request", async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({ content: "OLD", is_dirty: false, is_user_edited: false }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({ content: "NEW", is_dirty: false, is_user_edited: true }),
      });

    const { result } = renderHook(() => useAvlGeometry("test-id"));

    await waitFor(() => expect(result.current.content).toBe("OLD"));

    await act(async () => {
      await result.current.save("NEW");
    });

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/aeroplanes/test-id/avl-geometry"),
      expect.objectContaining({ method: "PUT" }),
    );
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test:unit -- --run useAvlGeometry`
Expected: FAIL — module not found

- [ ] **Step 3: Create the hook**

```typescript
// frontend/hooks/useAvlGeometry.ts
"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE } from "@/lib/fetcher";

interface AvlGeometryState {
  content: string | null;
  isDirty: boolean;
  isUserEdited: boolean;
  isLoading: boolean;
  error: string | null;
  save: (content: string) => Promise<void>;
  regenerate: () => Promise<string>;
  remove: () => Promise<void>;
  refresh: () => Promise<void>;
}

export function useAvlGeometry(aeroplaneId: string | null): AvlGeometryState {
  const [content, setContent] = useState<string | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const [isUserEdited, setIsUserEdited] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchGeometry = useCallback(async () => {
    if (!aeroplaneId) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/avl-geometry`,
      );
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const data = await res.json();
      setContent(data.content);
      setIsDirty(data.is_dirty);
      setIsUserEdited(data.is_user_edited);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  }, [aeroplaneId]);

  useEffect(() => {
    fetchGeometry();
  }, [fetchGeometry]);

  const save = useCallback(
    async (newContent: string) => {
      if (!aeroplaneId) return;
      setError(null);
      const res = await fetch(
        `${API_BASE}/aeroplanes/${aeroplaneId}/avl-geometry`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content: newContent }),
        },
      );
      if (!res.ok) throw new Error(`Save failed: ${res.status}`);
      const data = await res.json();
      setContent(data.content);
      setIsDirty(data.is_dirty);
      setIsUserEdited(data.is_user_edited);
    },
    [aeroplaneId],
  );

  const regenerate = useCallback(async () => {
    if (!aeroplaneId) return "";
    setError(null);
    const res = await fetch(
      `${API_BASE}/aeroplanes/${aeroplaneId}/avl-geometry/regenerate`,
      { method: "POST" },
    );
    if (!res.ok) throw new Error(`Regenerate failed: ${res.status}`);
    const data = await res.json();
    return data.content as string;
  }, [aeroplaneId]);

  const remove = useCallback(async () => {
    if (!aeroplaneId) return;
    setError(null);
    const res = await fetch(
      `${API_BASE}/aeroplanes/${aeroplaneId}/avl-geometry`,
      { method: "DELETE" },
    );
    if (!res.ok && res.status !== 404)
      throw new Error(`Delete failed: ${res.status}`);
    setContent(null);
    setIsDirty(false);
    setIsUserEdited(false);
  }, [aeroplaneId]);

  return {
    content,
    isDirty,
    isUserEdited,
    isLoading,
    error,
    save,
    regenerate,
    remove,
    refresh: fetchGeometry,
  };
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm run test:unit -- --run useAvlGeometry`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
cd frontend && git add hooks/useAvlGeometry.ts __tests__/useAvlGeometry.test.ts
git commit -m "feat(gh-381): add useAvlGeometry hook for geometry CRUD"
```

---

## Task 9: Frontend — `<AvlGeometryEditor>` Dialog

**Files:**
- Create: `frontend/components/workbench/AvlGeometryEditor.tsx`
- Create: `frontend/components/workbench/AvlDirtyWarning.tsx`

- [ ] **Step 1: Create the dirty warning component**

```typescript
// frontend/components/workbench/AvlDirtyWarning.tsx
"use client";

import { useDialog } from "@/hooks/useDialog";
import { AlertTriangle } from "lucide-react";

interface Props {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly onViewDiff: () => void;
  readonly onRegenerate: () => void;
}

export function AvlDirtyWarning({ open, onClose, onViewDiff, onRegenerate }: Props) {
  const { dialogRef, handleClose } = useDialog(open, onClose);

  return (
    <dialog
      ref={dialogRef}
      className="m-auto bg-transparent backdrop:bg-black/60"
      onClose={handleClose}
      aria-label="Geometry changed warning"
    >
      <div className="w-[420px] rounded-xl border border-border bg-card p-6 shadow-2xl">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-full bg-primary/10">
            <AlertTriangle size={20} className="text-primary" />
          </div>
          <div>
            <h3 className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-foreground">
              Geometry Changed
            </h3>
            <p className="text-[12px] text-muted-foreground">
              The airplane geometry has changed since you last edited the AVL file.
            </p>
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <button
            onClick={onRegenerate}
            className="rounded-full border border-border bg-card-muted px-4 py-2 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground transition-colors hover:bg-sidebar-accent"
          >
            Regenerate
          </button>
          <button
            onClick={onViewDiff}
            className="rounded-full bg-primary px-4 py-2 font-[family-name:var(--font-geist-sans)] text-[13px] text-primary-foreground transition-colors hover:opacity-90"
          >
            View Diff
          </button>
        </div>
      </div>
    </dialog>
  );
}
```

- [ ] **Step 2: Create the main editor component**

```typescript
// frontend/components/workbench/AvlGeometryEditor.tsx
"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { X, Maximize2, Minimize2, Save, RotateCcw } from "lucide-react";
import dynamic from "next/dynamic";
import { useDialog } from "@/hooks/useDialog";
import { useAvlGeometry } from "@/hooks/useAvlGeometry";
import { AvlDirtyWarning } from "./AvlDirtyWarning";

const MonacoEditor = dynamic(() => import("@monaco-editor/react").then((m) => m.default), {
  ssr: false,
  loading: () => (
    <div className="flex flex-1 items-center justify-center text-[13px] text-muted-foreground">
      Loading editor…
    </div>
  ),
});

const MonacoDiffEditor = dynamic(
  () => import("@monaco-editor/react").then((m) => m.DiffEditor),
  {
    ssr: false,
    loading: () => (
      <div className="flex flex-1 items-center justify-center text-[13px] text-muted-foreground">
        Loading diff editor…
      </div>
    ),
  },
);

interface Props {
  readonly aeroplaneId: string;
  readonly open: boolean;
  readonly onClose: () => void;
}

type EditorMode = "edit" | "diff";

export function AvlGeometryEditor({ aeroplaneId, open, onClose }: Props) {
  const { dialogRef, handleClose } = useDialog(open, onClose);
  const geometry = useAvlGeometry(open ? aeroplaneId : null);

  const [localContent, setLocalContent] = useState("");
  const [regeneratedContent, setRegeneratedContent] = useState<string | null>(null);
  const [mode, setMode] = useState<EditorMode>("edit");
  const [fullscreen, setFullscreen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showDirtyWarning, setShowDirtyWarning] = useState(false);
  const monacoRef = useRef<unknown>(null);

  useEffect(() => {
    if (geometry.content !== null && localContent === "") {
      setLocalContent(geometry.content);
    }
  }, [geometry.content, localContent]);

  useEffect(() => {
    if (open && geometry.isDirty && geometry.isUserEdited) {
      setShowDirtyWarning(true);
    }
  }, [open, geometry.isDirty, geometry.isUserEdited]);

  useEffect(() => {
    if (!open) {
      setLocalContent("");
      setRegeneratedContent(null);
      setMode("edit");
      setFullscreen(false);
      setShowDirtyWarning(false);
    }
  }, [open]);

  function handleEditorDidMount(editor: unknown, monaco: unknown) {
    monacoRef.current = monaco;
    const m = monaco as typeof import("monaco-editor");
    import("./avlLanguage").then(({ avlLanguage, avlTheme }) => {
      m.languages.register({ id: "avl" });
      m.languages.setMonarchTokensProvider("avl", avlLanguage);
      m.editor.defineTheme("avl-dark", avlTheme);
      m.editor.setTheme("avl-dark");
    });
  }

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      const contentToSave = mode === "diff" && regeneratedContent !== null
        ? regeneratedContent
        : localContent;
      await geometry.save(contentToSave);
      onClose();
    } catch {
      // error is set in hook
    } finally {
      setSaving(false);
    }
  }, [geometry, localContent, regeneratedContent, mode, onClose]);

  const handleRegenerate = useCallback(async () => {
    setShowDirtyWarning(false);
    try {
      const fresh = await geometry.regenerate();
      setLocalContent(fresh);
      setMode("edit");
    } catch {
      // error is set in hook
    }
  }, [geometry]);

  const handleViewDiff = useCallback(async () => {
    setShowDirtyWarning(false);
    try {
      const fresh = await geometry.regenerate();
      setRegeneratedContent(fresh);
      setMode("diff");
    } catch {
      // error is set in hook
    }
  }, [geometry]);

  const handleReset = useCallback(async () => {
    try {
      const fresh = await geometry.regenerate();
      setLocalContent(fresh);
      setMode("edit");
    } catch {
      // error is set in hook
    }
  }, [geometry]);

  const sizeClasses = fullscreen
    ? "fixed inset-4 z-50"
    : "w-[900px] h-[650px]";

  return (
    <>
      <AvlDirtyWarning
        open={showDirtyWarning}
        onClose={() => setShowDirtyWarning(false)}
        onViewDiff={handleViewDiff}
        onRegenerate={handleRegenerate}
      />

      <dialog
        ref={dialogRef}
        className="m-auto bg-transparent backdrop:bg-black/60"
        onClose={handleClose}
        aria-label="AVL Geometry Editor"
      >
        <div
          className={`flex flex-col rounded-xl border border-border bg-card shadow-2xl ${sizeClasses}`}
        >
          {/* Header */}
          <div className="flex items-center gap-3 border-b border-border px-4 py-3">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-foreground">
              {mode === "diff" ? "AVL Geometry — Diff View" : "AVL Geometry Editor"}
            </span>
            {geometry.isUserEdited && (
              <span className="rounded-full bg-primary/15 px-2 py-0.5 text-[10px] text-primary">
                User Edited
              </span>
            )}
            <div className="flex-1" />
            {mode === "diff" && (
              <button
                onClick={() => setMode("edit")}
                className="rounded-full border border-border bg-card-muted px-3 py-1.5 text-[12px] text-foreground hover:bg-sidebar-accent"
              >
                Back to Editor
              </button>
            )}
            <button
              onClick={() => setFullscreen((f) => !f)}
              className="flex size-7 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
              title={fullscreen ? "Exit fullscreen" : "Fullscreen"}
            >
              {fullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            </button>
            <button
              onClick={onClose}
              className="flex size-7 items-center justify-center rounded-full text-muted-foreground hover:bg-sidebar-accent"
            >
              <X size={14} />
            </button>
          </div>

          {/* Editor Body */}
          <div className="flex-1 overflow-hidden">
            {geometry.isLoading ? (
              <div className="flex h-full items-center justify-center text-[13px] text-muted-foreground">
                Loading AVL geometry…
              </div>
            ) : mode === "diff" && regeneratedContent !== null ? (
              <MonacoDiffEditor
                original={localContent}
                modified={regeneratedContent}
                language="avl"
                theme="avl-dark"
                onMount={handleEditorDidMount}
                options={{
                  readOnly: false,
                  renderSideBySide: true,
                  fontFamily: "var(--font-jetbrains-mono), monospace",
                  fontSize: 13,
                  minimap: { enabled: false },
                  lineNumbers: "on",
                  scrollBeyondLastLine: false,
                }}
              />
            ) : (
              <MonacoEditor
                value={localContent}
                onChange={(v) => setLocalContent(v ?? "")}
                language="avl"
                theme="avl-dark"
                onMount={handleEditorDidMount}
                options={{
                  fontFamily: "var(--font-jetbrains-mono), monospace",
                  fontSize: 13,
                  minimap: { enabled: false },
                  lineNumbers: "on",
                  scrollBeyondLastLine: false,
                  wordWrap: "off",
                  automaticLayout: true,
                }}
              />
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center gap-2 border-t border-border px-4 py-3">
            {geometry.error && (
              <p className="text-[12px] text-destructive">{geometry.error}</p>
            )}
            <div className="flex-1" />
            <button
              onClick={handleReset}
              className="flex items-center gap-1.5 rounded-full border border-border bg-card-muted px-3.5 py-2 font-[family-name:var(--font-geist-sans)] text-[13px] text-foreground transition-colors hover:bg-sidebar-accent"
            >
              <RotateCcw size={12} />
              Reset to Generated
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-1.5 rounded-full bg-primary px-4 py-2 font-[family-name:var(--font-geist-sans)] text-[13px] text-primary-foreground transition-colors hover:opacity-90 disabled:opacity-60"
            >
              <Save size={12} />
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </div>
      </dialog>
    </>
  );
}
```

- [ ] **Step 3: Commit**

```bash
cd frontend && git add components/workbench/AvlGeometryEditor.tsx components/workbench/AvlDirtyWarning.tsx
git commit -m "feat(gh-381): add AvlGeometryEditor and AvlDirtyWarning components"
```

---

## Task 10: Frontend — Integration into Analysis Page

**Files:**
- Modify: `frontend/components/workbench/AnalysisViewerPanel.tsx`
- Modify: `frontend/app/workbench/analysis/page.tsx`

- [ ] **Step 1: Add "Edit AVL Geometry" button to AnalysisViewerPanel**

In `frontend/components/workbench/AnalysisViewerPanel.tsx`:

Add to the `Props` interface:

```typescript
readonly onEditAvlGeometry?: () => void;
readonly showAvlGeometryButton?: boolean;
```

In the header (after the "Configure & Run" button at line ~555), add:

```tsx
{showAvlGeometryButton && onEditAvlGeometry && (
  <button
    onClick={onEditAvlGeometry}
    className="flex items-center gap-1.5 rounded-full border border-border bg-card-muted px-3 py-1.5 text-[12px] text-foreground hover:bg-sidebar-accent"
  >
    <Settings size={12} />
    Edit AVL Geometry
  </button>
)}
```

Update the destructured props to include the new fields:

```typescript
onEditAvlGeometry,
showAvlGeometryButton,
```

- [ ] **Step 2: Wire up in the analysis page**

In `frontend/app/workbench/analysis/page.tsx`:

Add imports:

```typescript
import { AvlGeometryEditor } from "@/components/workbench/AvlGeometryEditor";
```

Add state:

```typescript
const [avlEditorOpen, setAvlEditorOpen] = useState(false);
```

Determine when to show the button (AVL-based tabs):

```typescript
const showAvlGeometryButton = activeTab === "Trefftz Plane" || activeTab === "Streamlines";
```

Pass to `AnalysisViewerPanel`:

```tsx
<AnalysisViewerPanel
  // ... existing props ...
  showAvlGeometryButton={showAvlGeometryButton}
  onEditAvlGeometry={() => setAvlEditorOpen(true)}
/>
```

Add the editor dialog after the config modal:

```tsx
{aeroplaneId && (
  <AvlGeometryEditor
    aeroplaneId={aeroplaneId}
    open={avlEditorOpen}
    onClose={() => setAvlEditorOpen(false)}
  />
)}
```

- [ ] **Step 3: Run frontend type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 4: Commit**

```bash
cd frontend && git add components/workbench/AnalysisViewerPanel.tsx app/workbench/analysis/page.tsx
git commit -m "feat(gh-381): wire AVL geometry editor into analysis page"
```

---

## Task 11: Push & Run Full Test Suite

- [ ] **Step 1: Run backend tests**

Run: `poetry run pytest -x -q --timeout=30 -m "not slow"`
Expected: All tests PASS

- [ ] **Step 2: Run frontend tests**

Run: `cd frontend && npm run test:unit`
Expected: All tests PASS

- [ ] **Step 3: Run linter**

Run: `poetry run ruff check . && poetry run ruff format --check .`
Expected: No errors

- [ ] **Step 4: Push to remote**

Run: `git push github feat/gh-381-avl-expert-mode`
