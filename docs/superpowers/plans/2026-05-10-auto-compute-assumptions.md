# Auto-Compute Design Assumptions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-compute `cl_max`, `cd0`, and `cg_x` from aircraft geometry via AeroSandbox whenever geometry changes, replacing manual guesswork.

**Architecture:** A new `assumption_compute_service` runs a two-phase AeroBuildup sweep (coarse alpha → fine alpha×velocity) triggered by `GeometryChanged` events via the existing `JobTracker` debounce mechanism. Results flow into the existing dual-source assumption system. A per-aircraft config table stores sweep parameters (no magic numbers). The frontend Info Chip Row becomes dynamic.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, Alembic, AeroSandbox, React 19, SWR, Tailwind CSS

**Spec:** `docs/superpowers/specs/2026-05-10-auto-compute-assumptions-design.md`

---

### Task 1: Data Model — ComputationConfig + Context Column

**Files:**
- Create: `app/models/computation_config.py`
- Modify: `app/models/aeroplanemodel.py`
- Modify: `app/models/__init__.py` (if exists, for import)
- Create: `alembic/versions/<auto>_add_computation_config_and_context.py`
- Test: `app/tests/test_computation_config_model.py`

- [ ] **Step 1: Write failing test for ComputationConfigModel**

```python
# app/tests/test_computation_config_model.py
import pytest
from app.models.computation_config import AircraftComputationConfigModel, COMPUTATION_CONFIG_DEFAULTS


def test_defaults_dict_has_all_columns():
    expected_keys = {
        "coarse_alpha_min_deg", "coarse_alpha_max_deg", "coarse_alpha_step_deg",
        "fine_alpha_margin_deg", "fine_alpha_step_deg", "fine_velocity_count",
        "debounce_seconds",
    }
    assert set(COMPUTATION_CONFIG_DEFAULTS.keys()) == expected_keys


def test_model_tablename():
    assert AircraftComputationConfigModel.__tablename__ == "aircraft_computation_config"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest app/tests/test_computation_config_model.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models.computation_config'`

- [ ] **Step 3: Create ComputationConfigModel**

```python
# app/models/computation_config.py
from __future__ import annotations

from sqlalchemy import Column, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base_class import Base

COMPUTATION_CONFIG_DEFAULTS: dict[str, float | int] = {
    "coarse_alpha_min_deg": -5.0,
    "coarse_alpha_max_deg": 25.0,
    "coarse_alpha_step_deg": 1.0,
    "fine_alpha_margin_deg": 5.0,
    "fine_alpha_step_deg": 0.5,
    "fine_velocity_count": 8,
    "debounce_seconds": 2.0,
}


class AircraftComputationConfigModel(Base):
    __tablename__ = "aircraft_computation_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    aeroplane_id = Column(
        Integer,
        ForeignKey("aeroplanes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    coarse_alpha_min_deg = Column(Float, nullable=False, default=COMPUTATION_CONFIG_DEFAULTS["coarse_alpha_min_deg"])
    coarse_alpha_max_deg = Column(Float, nullable=False, default=COMPUTATION_CONFIG_DEFAULTS["coarse_alpha_max_deg"])
    coarse_alpha_step_deg = Column(Float, nullable=False, default=COMPUTATION_CONFIG_DEFAULTS["coarse_alpha_step_deg"])
    fine_alpha_margin_deg = Column(Float, nullable=False, default=COMPUTATION_CONFIG_DEFAULTS["fine_alpha_margin_deg"])
    fine_alpha_step_deg = Column(Float, nullable=False, default=COMPUTATION_CONFIG_DEFAULTS["fine_alpha_step_deg"])
    fine_velocity_count = Column(Integer, nullable=False, default=COMPUTATION_CONFIG_DEFAULTS["fine_velocity_count"])
    debounce_seconds = Column(Float, nullable=False, default=COMPUTATION_CONFIG_DEFAULTS["debounce_seconds"])

    aeroplane = relationship("AeroplaneModel", back_populates="computation_config")

    __table_args__ = (
        UniqueConstraint("aeroplane_id", name="uq_computation_config_aeroplane"),
    )
```

- [ ] **Step 4: Add context column and relationship to AeroplaneModel**

In `app/models/aeroplanemodel.py`, add to the `AeroplaneModel` class:

```python
# Add import at top:
from sqlalchemy import JSON  # add JSON to existing import

# Add column after existing columns (after xyz_ref):
assumption_computation_context = Column(JSON, nullable=True)

# Add relationship after existing relationships (after design_assumptions):
computation_config = relationship(
    "AircraftComputationConfigModel",
    back_populates="aeroplane",
    uselist=False,
    cascade="all, delete-orphan",
)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `poetry run pytest app/tests/test_computation_config_model.py -v`
Expected: PASS

- [ ] **Step 6: Generate Alembic migration**

Run: `poetry run alembic revision --autogenerate -m "add computation config table and assumption context column"`

Review the generated migration — it should create the `aircraft_computation_config` table and add `assumption_computation_context` column to `aeroplanes`.

- [ ] **Step 7: Apply migration**

Run: `poetry run alembic upgrade head`

- [ ] **Step 8: Commit**

```bash
git add app/models/computation_config.py app/models/aeroplanemodel.py app/tests/test_computation_config_model.py alembic/versions/*_add_computation_config*
git commit -m "feat(gh-465): add computation config table and assumption context column"
```

---

### Task 2: Pydantic Schemas for ComputationConfig

**Files:**
- Create: `app/schemas/computation_config.py`
- Test: `app/tests/test_computation_config_schema.py`

- [ ] **Step 1: Write failing test**

```python
# app/tests/test_computation_config_schema.py
import pytest
from app.schemas.computation_config import ComputationConfigRead, ComputationConfigWrite


def test_read_schema_has_all_fields():
    data = ComputationConfigRead(
        id=1,
        aeroplane_id=1,
        coarse_alpha_min_deg=-5.0,
        coarse_alpha_max_deg=25.0,
        coarse_alpha_step_deg=1.0,
        fine_alpha_margin_deg=5.0,
        fine_alpha_step_deg=0.5,
        fine_velocity_count=8,
        debounce_seconds=2.0,
    )
    assert data.coarse_alpha_step_deg == 1.0
    assert data.fine_velocity_count == 8


def test_write_schema_partial_update():
    data = ComputationConfigWrite(coarse_alpha_step_deg=0.5)
    assert data.coarse_alpha_step_deg == 0.5
    assert data.fine_velocity_count is None


def test_write_schema_validates_positive_step():
    with pytest.raises(ValueError):
        ComputationConfigWrite(coarse_alpha_step_deg=0.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest app/tests/test_computation_config_schema.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create schemas**

```python
# app/schemas/computation_config.py
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ComputationConfigRead(BaseModel):
    id: int
    aeroplane_id: int
    coarse_alpha_min_deg: float
    coarse_alpha_max_deg: float
    coarse_alpha_step_deg: float
    fine_alpha_margin_deg: float
    fine_alpha_step_deg: float
    fine_velocity_count: int
    debounce_seconds: float

    model_config = ConfigDict(from_attributes=True)


class ComputationConfigWrite(BaseModel):
    coarse_alpha_min_deg: float | None = None
    coarse_alpha_max_deg: float | None = None
    coarse_alpha_step_deg: float | None = Field(None, gt=0, description="Must be positive")
    fine_alpha_margin_deg: float | None = Field(None, gt=0)
    fine_alpha_step_deg: float | None = Field(None, gt=0, description="Must be positive")
    fine_velocity_count: int | None = Field(None, ge=2, le=50)
    debounce_seconds: float | None = Field(None, ge=0.5, le=30.0)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest app/tests/test_computation_config_schema.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/schemas/computation_config.py app/tests/test_computation_config_schema.py
git commit -m "feat(gh-465): add computation config pydantic schemas"
```

---

### Task 3: Extend `update_calculated_value` with auto-switch

**Files:**
- Modify: `app/services/design_assumptions_service.py`
- Test: `app/tests/test_design_assumptions_service.py` (add tests)

- [ ] **Step 1: Write failing tests**

Add to the existing test file (or create if not present):

```python
# app/tests/test_auto_switch_source.py
import pytest
from unittest.mock import MagicMock, patch
from app.services.design_assumptions_service import update_calculated_value
from app.models.aeroplanemodel import DesignAssumptionModel


@pytest.fixture
def mock_db_with_assumption():
    """Create a mock DB session with an assumption row."""
    db = MagicMock()
    row = MagicMock(spec=DesignAssumptionModel)
    row.parameter_name = "cl_max"
    row.estimate_value = 1.4
    row.calculated_value = None
    row.calculated_source = None
    row.active_source = "ESTIMATE"
    row.divergence_pct = None
    row.updated_at = None
    row.id = 1
    row.aeroplane_id = 1

    db.query.return_value.filter.return_value.first.return_value = row
    return db, row


def test_auto_switch_on_first_calculated_value(mock_db_with_assumption):
    db, row = mock_db_with_assumption
    with patch("app.services.design_assumptions_service._get_aeroplane") as mock_get:
        mock_aeroplane = MagicMock()
        mock_aeroplane.id = 1
        mock_get.return_value = mock_aeroplane

        update_calculated_value(db, "test-uuid", "cl_max", 1.35, "aerobuildup", auto_switch_source=True)

    assert row.calculated_value == 1.35
    assert row.active_source == "CALCULATED"


def test_no_auto_switch_when_already_has_calculated(mock_db_with_assumption):
    db, row = mock_db_with_assumption
    row.calculated_value = 1.3  # already has a value
    row.active_source = "ESTIMATE"  # user chose estimate

    with patch("app.services.design_assumptions_service._get_aeroplane") as mock_get:
        mock_aeroplane = MagicMock()
        mock_aeroplane.id = 1
        mock_get.return_value = mock_aeroplane

        update_calculated_value(db, "test-uuid", "cl_max", 1.35, "aerobuildup", auto_switch_source=True)

    assert row.calculated_value == 1.35
    assert row.active_source == "ESTIMATE"  # not overridden


def test_no_auto_switch_for_design_choice(mock_db_with_assumption):
    db, row = mock_db_with_assumption
    row.parameter_name = "g_limit"

    with patch("app.services.design_assumptions_service._get_aeroplane") as mock_get:
        mock_aeroplane = MagicMock()
        mock_aeroplane.id = 1
        mock_get.return_value = mock_aeroplane

        update_calculated_value(db, "test-uuid", "g_limit", 3.5, "computed", auto_switch_source=True)

    assert row.active_source == "ESTIMATE"  # design choices never auto-switch
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest app/tests/test_auto_switch_source.py -v`
Expected: FAIL with `TypeError: update_calculated_value() got an unexpected keyword argument 'auto_switch_source'`

- [ ] **Step 3: Add auto_switch_source parameter**

In `app/services/design_assumptions_service.py`, modify `update_calculated_value()`:

```python
def update_calculated_value(
    db: Session,
    aeroplane_uuid,
    param_name: str,
    value: float | None,
    source: str | None,
    auto_switch_source: bool = False,
) -> AssumptionRead:
    """Update the calculated value and source for a design assumption.

    Called by aggregation services (e.g. weight-item sync) to feed
    computed values back into the assumption row. Recomputes divergence.
    """
    try:
        aeroplane = _get_aeroplane(db, aeroplane_uuid)
        row = (
            db.query(DesignAssumptionModel)
            .filter(
                DesignAssumptionModel.aeroplane_id == aeroplane.id,
                DesignAssumptionModel.parameter_name == param_name,
            )
            .first()
        )
        if row is None:
            raise NotFoundError(entity="DesignAssumption", resource_id=param_name)

        should_switch = (
            auto_switch_source
            and row.calculated_value is None
            and row.active_source == "ESTIMATE"
            and param_name not in DESIGN_CHOICE_PARAMS
        )

        row.calculated_value = value
        row.calculated_source = source
        row.divergence_pct = compute_divergence_pct(row.estimate_value, value)

        if should_switch:
            row.active_source = "CALCULATED"

        db.flush()
        db.refresh(row)
        return _assumption_to_read(row)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in update_calculated_value: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest app/tests/test_auto_switch_source.py -v`
Expected: PASS

- [ ] **Step 5: Run existing assumption tests for regressions**

Run: `poetry run pytest app/tests/ -k "assumption" -v`
Expected: All PASS (new parameter has default `False`, no behavior change for existing callers)

- [ ] **Step 6: Commit**

```bash
git add app/services/design_assumptions_service.py app/tests/test_auto_switch_source.py
git commit -m "feat(gh-465): add auto_switch_source to update_calculated_value"
```

---

### Task 4: Seed ComputationConfig in `seed_defaults`

**Files:**
- Modify: `app/services/design_assumptions_service.py`
- Test: `app/tests/test_seed_computation_config.py`

- [ ] **Step 1: Write failing test**

```python
# app/tests/test_seed_computation_config.py
from app.models.computation_config import (
    AircraftComputationConfigModel,
    COMPUTATION_CONFIG_DEFAULTS,
)
from app.services.design_assumptions_service import seed_defaults
from app.tests.conftest import make_aeroplane


def test_seed_defaults_creates_computation_config(client_and_db):
    """seed_defaults seeds a per-aircraft computation config row."""
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aeroplane_id = aeroplane.id

    with SessionLocal() as db:
        config = (
            db.query(AircraftComputationConfigModel)
            .filter(AircraftComputationConfigModel.aeroplane_id == aeroplane_id)
            .first()
        )
        assert config is not None
        assert config.coarse_alpha_step_deg == COMPUTATION_CONFIG_DEFAULTS["coarse_alpha_step_deg"]
        assert config.fine_velocity_count == COMPUTATION_CONFIG_DEFAULTS["fine_velocity_count"]


def test_seed_defaults_idempotent_for_config(client_and_db):
    """Calling seed_defaults twice does not create a second config row."""
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aeroplane_id = aeroplane.id

    with SessionLocal() as db:
        configs = (
            db.query(AircraftComputationConfigModel)
            .filter(AircraftComputationConfigModel.aeroplane_id == aeroplane_id)
            .all()
        )
        assert len(configs) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest app/tests/test_seed_computation_config.py -v`
Expected: FAIL — seed_defaults does not create computation config yet

- [ ] **Step 3: Extend seed_defaults**

In `app/services/design_assumptions_service.py`, add to `seed_defaults()` after the assumption seeding loop and before `db.flush()`:

```python
from app.models.computation_config import AircraftComputationConfigModel, COMPUTATION_CONFIG_DEFAULTS

# Inside seed_defaults, after the assumption seeding loop:
existing_config = (
    db.query(AircraftComputationConfigModel)
    .filter(AircraftComputationConfigModel.aeroplane_id == aeroplane.id)
    .first()
)
if existing_config is None:
    config = AircraftComputationConfigModel(
        aeroplane_id=aeroplane.id,
        **COMPUTATION_CONFIG_DEFAULTS,
    )
    db.add(config)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest app/tests/test_seed_computation_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/design_assumptions_service.py app/tests/test_seed_computation_config.py
git commit -m "feat(gh-465): seed computation config in seed_defaults"
```

---

### Task 5: Assumption Compute Service — Core Logic

**Files:**
- Create: `app/services/assumption_compute_service.py`
- Test: `app/tests/test_assumption_compute_service.py`

- [ ] **Step 1: Write failing tests for the recompute pipeline**

The tests use a real in-memory DB via the existing `client_and_db`
fixture (see `app/tests/conftest.py`) so the assumption rows actually
persist and can be re-read. Heavy ASB calls are stubbed via the small
helpers `_stability_run_at_cruise`, `_coarse_alpha_sweep`,
`_fine_sweep_cl_max` — that keeps unit tests fast without faking the
ASB result-object surface.

```python
# app/tests/test_assumption_compute_service.py
from __future__ import annotations

from unittest.mock import patch
from types import SimpleNamespace

from app.models.computation_config import (
    AircraftComputationConfigModel,
    COMPUTATION_CONFIG_DEFAULTS,
)
from app.models.aeroplanemodel import DesignAssumptionModel
from app.services.assumption_compute_service import recompute_assumptions
from app.services.design_assumptions_service import seed_defaults
from app.tests.conftest import make_aeroplane


def _patches():
    """Stub the three ASB-bound helpers so tests don't need real ASB."""
    return (
        patch(
            "app.services.assumption_compute_service._build_asb_airplane",
            return_value=SimpleNamespace(wings=[object()], xyz_ref=[0.08, 0.0, 0.0]),
        ),
        patch(
            "app.services.assumption_compute_service._stability_run_at_cruise",
            return_value=(0.085, 0.20, 0.025),  # x_np, MAC, CD0
        ),
        patch(
            "app.services.assumption_compute_service._coarse_alpha_sweep",
            return_value=15.0,  # stall_alpha_deg
        ),
        patch(
            "app.services.assumption_compute_service._fine_sweep_cl_max",
            return_value=1.35,
        ),
        patch(
            "app.services.assumption_compute_service._load_flight_profile_speeds",
            return_value=(18.0, 28.0),
        ),
    )


def test_recompute_writes_all_three_assumptions(client_and_db):
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)
        aeroplane_id = aeroplane.id

    p1, p2, p3, p4, p5 = _patches()
    with p1, p2, p3, p4, p5:
        with SessionLocal() as db:
            recompute_assumptions(db, aeroplane_uuid)
            db.commit()

    with SessionLocal() as db:
        rows = {
            r.parameter_name: r
            for r in db.query(DesignAssumptionModel)
            .filter(DesignAssumptionModel.aeroplane_id == aeroplane_id)
            .all()
        }
        assert rows["cl_max"].calculated_value == 1.35
        assert rows["cd0"].calculated_value == 0.025
        # cg_x = x_np - target_static_margin × MAC
        #      = 0.085 - 0.12 × 0.20 = 0.061
        # (target_static_margin default is 0.12 per PARAMETER_DEFAULTS)
        assert abs(rows["cg_x"].calculated_value - 0.061) < 1e-6


def test_recompute_skips_when_no_wings(client_and_db):
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)

    with patch(
        "app.services.assumption_compute_service._build_asb_airplane",
        return_value=SimpleNamespace(wings=[], xyz_ref=[0, 0, 0]),
    ):
        with SessionLocal() as db:
            recompute_assumptions(db, aeroplane_uuid)
            db.commit()

    with SessionLocal() as db:
        cd0 = (
            db.query(DesignAssumptionModel)
            .filter_by(parameter_name="cd0")
            .first()
        )
        assert cd0.calculated_value is None  # untouched


def test_recompute_caches_context_and_publishes_cg_change(client_and_db):
    from app.core.events import AssumptionChanged, event_bus

    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)
        aeroplane_id = aeroplane.id

    captured: list = []
    handler = captured.append
    event_bus.subscribe(AssumptionChanged, handler)

    p1, p2, p3, p4, p5 = _patches()
    try:
        with p1, p2, p3, p4, p5:
            with SessionLocal() as db:
                recompute_assumptions(db, aeroplane_uuid)
                db.commit()
    finally:
        # EventBus has no public unsubscribe; remove from internal list
        event_bus._subscribers.get(AssumptionChanged, []).remove(handler)

    with SessionLocal() as db:
        from app.models.aeroplanemodel import AeroplaneModel
        a = db.query(AeroplaneModel).filter_by(id=aeroplane_id).first()
        ctx = a.assumption_computation_context
        assert ctx["v_cruise_mps"] == 18.0
        assert ctx["mac_m"] == 0.20
        assert ctx["x_np_m"] == 0.085

    cg_events = [e for e in captured if e.parameter_name == "cg_x"]
    assert len(cg_events) == 1
```


- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest app/tests/test_assumption_compute_service.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create the service**

```python
# app/services/assumption_compute_service.py
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from app.api.utils import analyse_aerodynamics
from app.converters.model_schema_converters import (
    aeroplane_model_to_aeroplane_schema_async,
    aeroplane_schema_to_asb_airplane_async,
)
from app.core.events import AssumptionChanged, event_bus
from app.models.aeroplanemodel import AeroplaneModel, DesignAssumptionModel, WeightItemModel
from app.models.computation_config import (
    AircraftComputationConfigModel,
    COMPUTATION_CONFIG_DEFAULTS,
)
from app.schemas.AeroplaneRequest import AnalysisToolUrlType
from app.schemas.aeroanalysisschema import OperatingPointSchema
from app.schemas.design_assumption import PARAMETER_DEFAULTS
from app.services.design_assumptions_service import _get_aeroplane, update_calculated_value
from app.services.mass_cg_service import aggregate_weight_items
from app.services.stability_service import _scalar

logger = logging.getLogger(__name__)


def recompute_assumptions(db: Session, aeroplane_uuid) -> None:
    """Recompute cl_max, cd0, cg_x from geometry via AeroSandbox.

    Sync function — caller MUST wrap in asyncio.to_thread() when invoked
    from async context (see app/main.py recompute wrapper).

    Skips silently if aircraft has no wings.
    """
    aircraft = _get_aeroplane(db, aeroplane_uuid)
    asb_airplane = _build_asb_airplane(aircraft)

    if not asb_airplane.wings:
        logger.info(
            "No wings on aircraft %s — skipping assumption recompute", aeroplane_uuid
        )
        return

    config = _load_or_create_config(db, aircraft.id)
    v_cruise, v_max = _load_flight_profile_speeds(db, aircraft)

    try:
        x_np, mac, cd0 = _stability_run_at_cruise(asb_airplane, v_cruise)
        stall_alpha = _coarse_alpha_sweep(asb_airplane, v_cruise, config)
        cl_max = _fine_sweep_cl_max(asb_airplane, stall_alpha, v_cruise, v_max, config)
    except Exception:
        logger.exception(
            "AeroBuildup failed during recompute for aircraft %s — aborting", aeroplane_uuid
        )
        return

    target_sm = _load_effective_assumption(db, aircraft.id, "target_static_margin")
    cg_x = x_np - target_sm * mac

    old_cg = _get_current_calculated_value(db, aircraft.id, "cg_x")

    update_calculated_value(
        db, aeroplane_uuid, "cl_max", round(cl_max, 4), "aerobuildup",
        auto_switch_source=True,
    )
    update_calculated_value(
        db, aeroplane_uuid, "cd0", round(cd0, 5), "aerobuildup",
        auto_switch_source=True,
    )
    update_calculated_value(
        db, aeroplane_uuid, "cg_x", round(cg_x, 4), "aerobuildup",
        auto_switch_source=True,
    )

    cg_agg = _load_cg_agg(db, aircraft.id)
    re = _reynolds_number(v_cruise, mac)

    _cache_context(db, aircraft, {
        "v_cruise_mps": v_cruise,
        "reynolds": round(re),
        "mac_m": round(mac, 4),
        "x_np_m": round(x_np, 4),
        "target_static_margin": target_sm,
        "cg_agg_m": round(cg_agg, 4) if cg_agg is not None else None,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    })

    if old_cg is None or abs(cg_x - old_cg) > 1e-6:
        # Mirror update_assumption: mark OPs DIRTY in the same transaction
        # before emitting AssumptionChanged. Otherwise the retrim handler
        # finds no DIRTY ops and does nothing.
        from app.services.invalidation_service import mark_ops_dirty

        mark_ops_dirty(db, aircraft.id)
        event_bus.publish(
            AssumptionChanged(aeroplane_id=aircraft.id, parameter_name="cg_x")
        )


def _build_asb_airplane(aircraft: AeroplaneModel):
    schema = aeroplane_model_to_aeroplane_schema_async(aircraft)
    return aeroplane_schema_to_asb_airplane_async(plane_schema=schema)


def _load_or_create_config(
    db: Session, aeroplane_id: int
) -> AircraftComputationConfigModel:
    config = (
        db.query(AircraftComputationConfigModel)
        .filter(AircraftComputationConfigModel.aeroplane_id == aeroplane_id)
        .first()
    )
    if config is None:
        config = AircraftComputationConfigModel(
            aeroplane_id=aeroplane_id, **COMPUTATION_CONFIG_DEFAULTS
        )
        db.add(config)
        db.flush()
    return config


def _load_flight_profile_speeds(
    db: Session, aircraft: AeroplaneModel
) -> tuple[float, float]:
    from app.services.operating_point_generator_service import (
        _load_effective_flight_profile,
    )

    profile, _ = _load_effective_flight_profile(db, aircraft)
    goals = profile.get("goals", {})
    cruise = float(goals.get("cruise_speed_mps", 18.0))
    v_max = float(
        goals.get("max_level_speed_mps") or max(1.35 * cruise, cruise + 8.0)
    )
    return cruise, v_max


def _stability_run_at_cruise(
    asb_airplane, v_cruise: float
) -> tuple[float, float, float]:
    """Returns (x_np, MAC, CD0) from a single AeroBuildup stability run.

    Uses analyse_aerodynamics → AnalysisModel — same code path as
    stability_service, so x_np / MAC / CD0 are consistent across the app.
    """
    xyz_ref = list(asb_airplane.xyz_ref) if asb_airplane.xyz_ref is not None else [0.0, 0.0, 0.0]
    op_schema = OperatingPointSchema(velocity=v_cruise, alpha=0.0, xyz_ref=xyz_ref)
    result, _ = analyse_aerodynamics(
        AnalysisToolUrlType.AEROBUILDUP, op_schema, asb_airplane
    )
    x_np = _scalar(result.reference.Xnp)
    mac = _scalar(result.reference.Cref)
    cd0 = _scalar(result.coefficients.CD)
    if x_np is None or mac is None or cd0 is None:
        raise ValueError("AeroBuildup returned NULL for x_np/MAC/CD0")
    return float(x_np), float(mac), float(cd0)


def _coarse_alpha_sweep(
    asb_airplane, v_cruise: float, config: AircraftComputationConfigModel
) -> float:
    """Returns approximate stall_alpha_deg (alpha where CL peaks)."""
    import aerosandbox as asb

    alphas = np.arange(
        config.coarse_alpha_min_deg,
        config.coarse_alpha_max_deg + 0.01,
        config.coarse_alpha_step_deg,
    )
    xyz_ref = list(asb_airplane.xyz_ref) if asb_airplane.xyz_ref is not None else [0.0, 0.0, 0.0]
    cls: list[float] = []
    for a in alphas:
        op = asb.OperatingPoint(velocity=v_cruise, alpha=float(a))
        abu = asb.AeroBuildup(airplane=asb_airplane, op_point=op, xyz_ref=xyz_ref)
        r = abu.run()
        cls.append(_extract_scalar(r, "CL", default=0.0))
    return float(alphas[int(np.argmax(cls))])


def _fine_sweep_cl_max(
    asb_airplane,
    stall_alpha_deg: float,
    v_cruise: float,
    v_max: float,
    config: AircraftComputationConfigModel,
) -> float:
    import aerosandbox as asb

    alpha_min = stall_alpha_deg - config.fine_alpha_margin_deg
    alpha_max = stall_alpha_deg + config.fine_alpha_margin_deg
    alphas = np.arange(alpha_min, alpha_max + 0.01, config.fine_alpha_step_deg)

    v_stall_approx = max(v_cruise * 0.5, 3.0)
    velocities = np.linspace(v_stall_approx, v_max, config.fine_velocity_count)

    xyz_ref = list(asb_airplane.xyz_ref) if asb_airplane.xyz_ref is not None else [0.0, 0.0, 0.0]
    cl_max = -float("inf")
    for v in velocities:
        for a in alphas:
            op = asb.OperatingPoint(velocity=float(v), alpha=float(a))
            abu = asb.AeroBuildup(airplane=asb_airplane, op_point=op, xyz_ref=xyz_ref)
            r = abu.run()
            cl = _extract_scalar(r, "CL", default=0.0)
            if cl > cl_max:
                cl_max = cl
    return float(cl_max)


def _extract_scalar(result: Any, key: str, *, default: float) -> float:
    """Extract a CL/CD scalar from raw AeroBuildup result (dict or object)."""
    if isinstance(result, dict):
        val = result.get(key)
    else:
        val = getattr(result, key, None)
    scalar = _scalar(val)
    return float(scalar) if scalar is not None else default


def _load_effective_assumption(
    db: Session, aeroplane_id: int, param_name: str
) -> float:
    row = (
        db.query(DesignAssumptionModel)
        .filter(
            DesignAssumptionModel.aeroplane_id == aeroplane_id,
            DesignAssumptionModel.parameter_name == param_name,
        )
        .first()
    )
    if row is None:
        return PARAMETER_DEFAULTS.get(param_name, 0.0)
    if row.active_source == "CALCULATED" and row.calculated_value is not None:
        return row.calculated_value
    return row.estimate_value


def _get_current_calculated_value(
    db: Session, aeroplane_id: int, param_name: str
) -> float | None:
    row = (
        db.query(DesignAssumptionModel)
        .filter(
            DesignAssumptionModel.aeroplane_id == aeroplane_id,
            DesignAssumptionModel.parameter_name == param_name,
        )
        .first()
    )
    return row.calculated_value if row else None


def _load_cg_agg(db: Session, aeroplane_id: int) -> float | None:
    rows = (
        db.query(WeightItemModel)
        .filter(WeightItemModel.aeroplane_id == aeroplane_id)
        .all()
    )
    if not rows:
        return None
    items = [
        {"mass_kg": r.mass_kg, "x_m": r.x_m, "y_m": r.y_m, "z_m": r.z_m}
        for r in rows
    ]
    _, cg_x, _, _ = aggregate_weight_items(items)
    return cg_x


def _reynolds_number(
    velocity: float, mac: float, rho: float = 1.225, mu: float = 1.81e-5
) -> float:
    """Sea-level standard atmosphere — sufficient for the UI chip; not
    altitude-aware. Operating points use their own atmosphere model."""
    return rho * velocity * mac / mu


def _cache_context(
    db: Session, aircraft: AeroplaneModel, context: dict[str, Any]
) -> None:
    aircraft.assumption_computation_context = context
    db.flush()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest app/tests/test_assumption_compute_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/assumption_compute_service.py app/tests/test_assumption_compute_service.py
git commit -m "feat(gh-465): add assumption compute service with two-phase ASB sweep"
```

---

### Task 6: Wire GeometryChanged Event to Recompute

**Files:**
- Modify: `app/services/invalidation_service.py`
- Modify: `app/core/background_jobs.py`
- Modify: `app/main.py`
- Test: `app/tests/test_invalidation_recompute.py`

- [ ] **Step 1: Write failing test**

> NOTE on patch target: the handler does a lazy
> `from app.core.background_jobs import job_tracker`. `mock.patch` must
> target the *origin* of the name (where the lazy import looks it up),
> NOT `app.services.invalidation_service` — patching the latter has no
> effect because the local binding is created at call time.

```python
# app/tests/test_invalidation_recompute.py
from unittest.mock import patch
from app.core.events import GeometryChanged


def test_geometry_changed_schedules_recompute():
    from app.services.invalidation_service import (
        _on_geometry_changed_recompute_assumptions,
    )

    event = GeometryChanged(aeroplane_id=42, source_model="WingModel")

    with patch("app.core.background_jobs.job_tracker") as mock_tracker:
        _on_geometry_changed_recompute_assumptions(event)

    mock_tracker.schedule_recompute_assumptions.assert_called_once_with(42)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest app/tests/test_invalidation_recompute.py -v`
Expected: FAIL with `ImportError` — function doesn't exist yet

- [ ] **Step 3: Add `schedule_recompute_assumptions` to JobTracker**

In `app/core/background_jobs.py`, add alongside existing `schedule_retrim`:

```python
# Add new dataclass after RetrimJob:
@dataclass
class RecomputeAssumptionsJob:
    aeroplane_id: int
    status: JobStatus = JobStatus.DEBOUNCING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
```

Add to `JobTracker.__init__`:
```python
self._recompute_jobs: dict[int, RecomputeAssumptionsJob] = {}
self._recompute_debounce_tasks: dict[int, asyncio.Task] = {}
self._recompute_function: Callable[[int], Awaitable[None]] | None = None
```

Add methods to `JobTracker`:
```python
def set_recompute_function(self, fn: Callable[[int], Awaitable[None]]) -> None:
    self._recompute_function = fn

def schedule_recompute_assumptions(self, aeroplane_id: int) -> None:
    existing_task = self._recompute_debounce_tasks.get(aeroplane_id)
    if existing_task and not existing_task.done():
        existing_task.cancel()

    self._recompute_jobs[aeroplane_id] = RecomputeAssumptionsJob(aeroplane_id=aeroplane_id)

    try:
        loop = asyncio.get_running_loop()
        self._recompute_debounce_tasks[aeroplane_id] = loop.create_task(
            self._debounced_recompute(aeroplane_id)
        )
    except RuntimeError:
        logger.debug(
            "No running event loop — skipping recompute for aeroplane %d",
            aeroplane_id,
        )

async def _debounced_recompute(self, aeroplane_id: int) -> None:
    try:
        await asyncio.sleep(self.debounce_seconds)
    except asyncio.CancelledError:
        return

    if self._recompute_function is None:
        logger.warning("No recompute function registered — cannot recompute for aeroplane %d", aeroplane_id)
        return

    job = self._recompute_jobs.get(aeroplane_id)
    if job is None:
        return

    job.status = JobStatus.COMPUTING
    job.started_at = datetime.now(timezone.utc)

    try:
        await self._recompute_function(aeroplane_id)
        job.status = JobStatus.DONE
    except Exception as exc:
        logger.exception("Recompute assumptions failed for aeroplane %d", aeroplane_id)
        job.status = JobStatus.FAILED
        job.error = str(exc)
    finally:
        job.finished_at = datetime.now(timezone.utc)
        self._recompute_debounce_tasks.pop(aeroplane_id, None)
```

Extend `shutdown()` to also cancel recompute tasks:
```python
for task in self._recompute_debounce_tasks.values():
    if not task.done():
        task.cancel()
if self._recompute_debounce_tasks:
    await asyncio.gather(*self._recompute_debounce_tasks.values(), return_exceptions=True)
self._recompute_debounce_tasks.clear()
```

- [ ] **Step 4: Add handler to invalidation_service.py**

In `app/services/invalidation_service.py`, add:

```python
def _on_geometry_changed_recompute_assumptions(event: GeometryChanged) -> None:
    logger.info(
        "GeometryChanged for aeroplane %d (source: %s) — scheduling assumption recompute",
        event.aeroplane_id,
        event.source_model,
    )
    from app.core.background_jobs import job_tracker

    job_tracker.schedule_recompute_assumptions(event.aeroplane_id)
```

In `register_handlers()`, add:
```python
event_bus.subscribe(GeometryChanged, _on_geometry_changed_recompute_assumptions)
```

- [ ] **Step 5: Wire recompute function in main.py**

In `app/main.py`, in `_combined_lifespan`, after
`job_tracker.set_trim_function(retrim_dirty_ops)`, add:

```python
import asyncio
from app.db.session import SessionLocal
from app.models.aeroplanemodel import AeroplaneModel
from app.services.assumption_compute_service import recompute_assumptions

def _recompute_sync(aeroplane_id: int) -> None:
    db = SessionLocal()
    try:
        aeroplane = (
            db.query(AeroplaneModel)
            .filter(AeroplaneModel.id == aeroplane_id)
            .first()
        )
        if aeroplane is None:
            return
        recompute_assumptions(db, str(aeroplane.uuid))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

async def _recompute_wrapper(aeroplane_id: int) -> None:
    # ASB calls are CPU-bound (~200 calls per recompute). Running them
    # directly on the event loop would block all other requests.
    await asyncio.to_thread(_recompute_sync, aeroplane_id)

job_tracker.set_recompute_function(_recompute_wrapper)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `poetry run pytest app/tests/test_invalidation_recompute.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add app/core/background_jobs.py app/services/invalidation_service.py app/main.py app/tests/test_invalidation_recompute.py
git commit -m "feat(gh-465): wire GeometryChanged to assumption recompute via job tracker"
```

---

### Task 7: API Endpoints — Computation Context and Config

**Files:**
- Modify: `app/api/v2/endpoints/aeroplane/design_assumptions.py`
- Test: `app/tests/test_computation_endpoints.py`

- [ ] **Step 1: Write failing tests**

These tests use the existing `client_and_db` fixture that wires
`override_get_db` against an in-memory SQLite (see
`app/tests/conftest.py`). That matches the rest of the assumption
endpoint test suite (`test_design_assumptions_endpoint.py`).

```python
# app/tests/test_computation_endpoints.py
from app.models.aeroplanemodel import AeroplaneModel
from app.models.computation_config import (
    AircraftComputationConfigModel,
    COMPUTATION_CONFIG_DEFAULTS,
)
from app.tests.conftest import make_aeroplane


def test_get_computation_context_returns_null_when_never_computed(client_and_db):
    client, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        aeroplane_uuid = str(aeroplane.uuid)

    resp = client.get(f"/aeroplanes/{aeroplane_uuid}/assumptions/computation-context")
    assert resp.status_code == 200
    assert resp.json() is None


def test_get_computation_context_returns_cached(client_and_db):
    client, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        aeroplane.assumption_computation_context = {
            "v_cruise_mps": 18.0,
            "reynolds": 230000,
            "mac_m": 0.21,
        }
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)

    resp = client.get(f"/aeroplanes/{aeroplane_uuid}/assumptions/computation-context")
    assert resp.status_code == 200
    body = resp.json()
    assert body["v_cruise_mps"] == 18.0
    assert body["reynolds"] == 230000


def test_get_computation_config_creates_default_when_missing(client_and_db):
    client, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        aeroplane_uuid = str(aeroplane.uuid)
        aeroplane_id = aeroplane.id

    resp = client.get(f"/aeroplanes/{aeroplane_uuid}/computation-config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["coarse_alpha_step_deg"] == COMPUTATION_CONFIG_DEFAULTS["coarse_alpha_step_deg"]

    with SessionLocal() as db:
        rows = (
            db.query(AircraftComputationConfigModel)
            .filter(AircraftComputationConfigModel.aeroplane_id == aeroplane_id)
            .all()
        )
        assert len(rows) == 1


def test_put_computation_config_updates_fields(client_and_db):
    client, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        aeroplane_uuid = str(aeroplane.uuid)

    resp = client.put(
        f"/aeroplanes/{aeroplane_uuid}/computation-config",
        json={"coarse_alpha_step_deg": 0.5, "fine_velocity_count": 12},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["coarse_alpha_step_deg"] == 0.5
    assert body["fine_velocity_count"] == 12
    # Untouched fields keep defaults
    assert body["debounce_seconds"] == COMPUTATION_CONFIG_DEFAULTS["debounce_seconds"]


def test_get_computation_context_404_for_missing_aeroplane(client_and_db):
    import uuid

    client, _ = client_and_db
    resp = client.get(
        f"/aeroplanes/{uuid.uuid4()}/assumptions/computation-context"
    )
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest app/tests/test_computation_endpoints.py -v`
Expected: FAIL — endpoint doesn't exist

- [ ] **Step 3: Add endpoints**

In `app/api/v2/endpoints/aeroplane/design_assumptions.py`, add:

```python
from app.models.computation_config import AircraftComputationConfigModel, COMPUTATION_CONFIG_DEFAULTS
from app.schemas.computation_config import ComputationConfigRead, ComputationConfigWrite


def _get_aeroplane_by_uuid(db: Session, aeroplane_id) -> AeroplaneModel:
    aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == str(aeroplane_id)).first()
    if aeroplane is None:
        raise HTTPException(status_code=404, detail="Aeroplane not found")
    return aeroplane


@router.get(
    "/aeroplanes/{aeroplane_id}/assumptions/computation-context",
    summary="Get cached computation context",
)
async def get_computation_context(
    aeroplane_id: Annotated[UUID4, Path(description="Aeroplane UUID")],
    db: Annotated[Session, Depends(get_db)],
):
    aeroplane = _get_aeroplane_by_uuid(db, aeroplane_id)
    return aeroplane.assumption_computation_context


@router.get(
    "/aeroplanes/{aeroplane_id}/computation-config",
    response_model=ComputationConfigRead,
    summary="Get computation configuration",
)
async def get_computation_config(
    aeroplane_id: Annotated[UUID4, Path(description="Aeroplane UUID")],
    db: Annotated[Session, Depends(get_db)],
):
    aeroplane = _get_aeroplane_by_uuid(db, aeroplane_id)
    config = (
        db.query(AircraftComputationConfigModel)
        .filter(AircraftComputationConfigModel.aeroplane_id == aeroplane.id)
        .first()
    )
    if config is None:
        config = AircraftComputationConfigModel(
            aeroplane_id=aeroplane.id, **COMPUTATION_CONFIG_DEFAULTS,
        )
        db.add(config)
        db.flush()
        db.refresh(config)
    return config


@router.put(
    "/aeroplanes/{aeroplane_id}/computation-config",
    response_model=ComputationConfigRead,
    summary="Update computation configuration",
)
async def update_computation_config(
    aeroplane_id: Annotated[UUID4, Path(description="Aeroplane UUID")],
    body: Annotated[ComputationConfigWrite, Body()],
    db: Annotated[Session, Depends(get_db)],
):
    aeroplane = _get_aeroplane_by_uuid(db, aeroplane_id)
    config = (
        db.query(AircraftComputationConfigModel)
        .filter(AircraftComputationConfigModel.aeroplane_id == aeroplane.id)
        .first()
    )
    if config is None:
        config = AircraftComputationConfigModel(
            aeroplane_id=aeroplane.id, **COMPUTATION_CONFIG_DEFAULTS,
        )
        db.add(config)
        db.flush()

    update_data = body.model_dump(exclude_none=True)
    for key, val in update_data.items():
        setattr(config, key, val)
    db.flush()
    db.refresh(config)
    return config
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest app/tests/test_computation_endpoints.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/api/v2/endpoints/aeroplane/design_assumptions.py app/tests/test_computation_endpoints.py
git commit -m "feat(gh-465): add computation context and config endpoints"
```

---

### Task 8: Frontend — `useComputationContext` Hook

**Files:**
- Create: `frontend/hooks/useComputationContext.ts`
- Test: `frontend/__tests__/useComputationContext.test.ts`

- [ ] **Step 1: Write failing test**

```typescript
// frontend/__tests__/useComputationContext.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useComputationContext } from "@/hooks/useComputationContext";

describe("useComputationContext", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches computation context for an aeroplane", async () => {
    const fakeContext = {
      v_cruise_mps: 18.0,
      reynolds: 230000,
      mac_m: 0.21,
      x_np_m: 0.085,
      target_static_margin: 0.12,
      cg_agg_m: 0.092,
      computed_at: "2026-05-10T14:30:00Z",
    };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(fakeContext),
    });

    const { result } = renderHook(() => useComputationContext("42"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual(fakeContext);
    const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(url.toString()).toContain("/assumptions/computation-context");
  });

  it("returns null when aeroplaneId is null", () => {
    const { result } = renderHook(() => useComputationContext(null));
    expect(result.current.data).toBeUndefined();
    expect(result.current.isLoading).toBe(false);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run __tests__/useComputationContext.test.ts`
Expected: FAIL — module not found

- [ ] **Step 3: Create the hook**

```typescript
// frontend/hooks/useComputationContext.ts
import useSWR from "swr";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8001/v2";

export interface ComputationContext {
  v_cruise_mps: number;
  reynolds: number;
  mac_m: number;
  x_np_m: number;
  target_static_margin: number;
  cg_agg_m: number | null;
  computed_at: string;
}

async function fetcher(url: string): Promise<ComputationContext | null> {
  const res = await fetch(url);
  if (!res.ok) return null;
  return res.json();
}

export function useComputationContext(aeroplaneId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<ComputationContext | null>(
    aeroplaneId
      ? `${API_BASE}/aeroplanes/${encodeURIComponent(aeroplaneId)}/assumptions/computation-context`
      : null,
    fetcher,
  );

  return { data: data ?? null, error, isLoading, mutate };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run __tests__/useComputationContext.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/hooks/useComputationContext.ts frontend/__tests__/useComputationContext.test.ts
git commit -m "feat(gh-465): add useComputationContext hook"
```

---

### Task 9: Frontend — Dynamic Info Chip Row

**Files:**
- Modify: `frontend/components/workbench/AnalysisViewerPanel.tsx`
- Test: `frontend/__tests__/InfoChipRow.test.tsx`

- [ ] **Step 1: Write failing test**

```typescript
// frontend/__tests__/InfoChipRow.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) => React.createElement("span", props);
  return { Wind: icon, SlidersHorizontal: icon, Activity: icon, Ruler: icon, Target: icon, Navigation: icon, Settings: icon };
});

vi.mock("@/hooks/useComputationContext", () => ({
  useComputationContext: vi.fn(),
}));

import { useComputationContext } from "@/hooks/useComputationContext";

describe("Info Chip Row", () => {
  it("shows dynamic values when context is available", async () => {
    (useComputationContext as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        v_cruise_mps: 18.0,
        reynolds: 230000,
        mac_m: 0.21,
        x_np_m: 0.085,
        target_static_margin: 0.12,
        cg_agg_m: 0.092,
      },
      isLoading: false,
      error: null,
    });

    // Import the InfoChipRow component (extracted in implementation)
    const { InfoChipRow } = await import("@/components/workbench/InfoChipRow");
    render(<InfoChipRow aeroplaneId="42" cgAero={0.073} />);

    expect(screen.getByText(/18\.0 m\/s/)).toBeInTheDocument();
    expect(screen.getByText(/2\.3e\+?5/i)).toBeInTheDocument();
    expect(screen.getByText(/0\.21 m/)).toBeInTheDocument();
    expect(screen.getByText(/0\.085 m/)).toBeInTheDocument();
  });

  it("shows dashes when no context", async () => {
    (useComputationContext as ReturnType<typeof vi.fn>).mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    const { InfoChipRow } = await import("@/components/workbench/InfoChipRow");
    render(<InfoChipRow aeroplaneId="42" cgAero={null} />);

    const dashes = screen.getAllByText("–");
    expect(dashes.length).toBeGreaterThanOrEqual(4);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run __tests__/InfoChipRow.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Extract InfoChipRow component**

Create `frontend/components/workbench/InfoChipRow.tsx`:

```tsx
"use client";

import { Wind, Ruler, Target, Navigation } from "lucide-react";
import { useComputationContext } from "@/hooks/useComputationContext";

interface Props {
  readonly aeroplaneId: string | null;
  readonly cgAero: number | null;
}

function Chip({ icon: Icon, label }: { readonly icon: React.ComponentType<{ size: number; className: string }>; readonly label: string }) {
  return (
    <div className="flex items-center gap-1.5 rounded-full bg-card-muted px-3 py-1.5">
      <Icon size={12} className="text-muted-foreground" />
      <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-foreground">
        {label}
      </span>
    </div>
  );
}

function cgDivergenceColor(cgAero: number, cgAgg: number, mac: number): string {
  const deltaPct = Math.abs(cgAgg - cgAero) / mac * 100;
  if (deltaPct < 5) return "text-emerald-400";
  if (deltaPct <= 15) return "text-orange-400";
  return "text-red-400";
}

export function InfoChipRow({ aeroplaneId, cgAero }: Props) {
  const { data: ctx } = useComputationContext(aeroplaneId);

  const fmt = (v: number | null | undefined, decimals: number, suffix = "") =>
    v != null ? `${v.toFixed(decimals)}${suffix}` : "–";

  const fmtRe = (v: number | null | undefined) => {
    if (v == null) return "–";
    return v.toExponential(1);
  };

  const cgLabel = (() => {
    if (cgAero == null) return "CG = –";
    const base = `CG = ${cgAero.toFixed(3)} m`;
    if (ctx?.cg_agg_m == null) return base;
    return base;
  })();

  return (
    <div className="flex items-center gap-2 border-t border-border bg-card px-4 py-3">
      <Chip icon={Wind} label={`V = ${fmt(ctx?.v_cruise_mps, 1, " m/s")}`} />
      <Chip icon={Wind} label={`Re ≈ ${fmtRe(ctx?.reynolds)}`} />
      <Chip icon={Ruler} label={`MAC = ${fmt(ctx?.mac_m, 2, " m")}`} />
      <Chip icon={Target} label={`NP = ${fmt(ctx?.x_np_m, 3, " m")}`} />
      <Chip icon={Navigation} label={`SM = ${ctx?.target_static_margin != null ? (ctx.target_static_margin * 100).toFixed(0) + "%" : "–"}`} />
      <div className="flex items-center gap-1.5 rounded-full bg-card-muted px-3 py-1.5">
        <Navigation size={12} className="text-muted-foreground" />
        <span className="font-[family-name:var(--font-geist-sans)] text-[12px] text-foreground">
          {cgLabel}
          {cgAero != null && ctx?.cg_agg_m != null && (
            <span className={`ml-1 ${cgDivergenceColor(cgAero, ctx.cg_agg_m, ctx.mac_m)}`}>
              ({ctx.cg_agg_m.toFixed(3)})
            </span>
          )}
        </span>
      </div>
      <div className="flex-1" />
    </div>
  );
}
```

- [ ] **Step 4: Replace hardcoded chips in AnalysisViewerPanel**

In `frontend/components/workbench/AnalysisViewerPanel.tsx`, replace the Info Chip Row section (lines 813–850) with:

```tsx
import { InfoChipRow } from "@/components/workbench/InfoChipRow";

// In the component JSX, replace the entire Info Chip Row div with:
<InfoChipRow
  aeroplaneId={aeroplaneId ?? null}
  cgAero={/* cg_x effective value from assumptions, passed as prop */}
/>
```

The `cgAero` prop needs to come from the assumptions data. Add it as a prop to the AnalysisViewerPanel or fetch via the existing `useDesignAssumptions` hook in the parent page.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend && npx vitest run __tests__/InfoChipRow.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/components/workbench/InfoChipRow.tsx frontend/components/workbench/AnalysisViewerPanel.tsx frontend/__tests__/InfoChipRow.test.tsx
git commit -m "feat(gh-465): dynamic Info Chip Row with computation context"
```

---

### Task 10: Frontend — Analysis Tab Wing Gate

**Files:**
- Modify: `frontend/components/workbench/AnalysisViewerPanel.tsx`
- Modify: parent page that renders `AnalysisViewerPanel` (typically
  `frontend/app/workbench/analysis/page.tsx` or equivalent)
- Test: `frontend/__tests__/AnalysisWingGate.test.tsx`

> **Why a new `hasWings` prop:** The existing `wingXSecs` prop holds
> cross-sections of *one* wing — it cannot tell us whether the aircraft
> has any wings at all. Counting components from the parent (where the
> aircraft tree is already loaded) is the correct source of truth.

- [ ] **Step 1: Write failing test**

```typescript
// frontend/__tests__/AnalysisWingGate.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) => React.createElement("span", props);
  return new Proxy({}, { get: () => icon });
});

vi.mock("@/hooks/useComputationContext", () => ({
  useComputationContext: () => ({ data: null, isLoading: false }),
}));

describe("Analysis Tab Wing Gate", () => {
  it("shows empty state for Polar tab when hasWings is false", async () => {
    const mod = await import("@/components/workbench/AnalysisViewerPanel");
    const Panel = mod.AnalysisViewerPanel;

    render(
      <Panel
        result={null}
        activeTab="Polar"
        onTabChange={() => {}}
        hasWings={false}
        wingXSecs={null}
        /* other required props default to null/empty */
      />,
    );

    expect(screen.getByText(/add a wing/i)).toBeInTheDocument();
  });

  it("shows Assumptions tab content even when hasWings is false", async () => {
    const mod = await import("@/components/workbench/AnalysisViewerPanel");
    const Panel = mod.AnalysisViewerPanel;

    render(
      <Panel
        result={null}
        activeTab="Assumptions"
        onTabChange={() => {}}
        hasWings={false}
        wingXSecs={null}
      />,
    );

    expect(screen.queryByText(/add a wing/i)).not.toBeInTheDocument();
  });

  it("shows Polar content when hasWings is true", async () => {
    const mod = await import("@/components/workbench/AnalysisViewerPanel");
    const Panel = mod.AnalysisViewerPanel;

    render(
      <Panel
        result={null}
        activeTab="Polar"
        onTabChange={() => {}}
        hasWings={true}
        wingXSecs={null}
      />,
    );

    expect(screen.queryByText(/add a wing/i)).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run __tests__/AnalysisWingGate.test.tsx`
Expected: FAIL — `hasWings` prop is unknown, gate logic missing.

- [ ] **Step 3: Add `hasWings` prop and wing gate to AnalysisViewerPanel**

In `AnalysisViewerPanel.tsx`:

1. Add `hasWings` to the `Props` interface (default-treated as
   `true` for backwards compatibility if a caller forgets the prop —
   but the parent page MUST pass it):
   ```tsx
   readonly hasWings?: boolean;  // defaults to true so callers without wings data don't see empty states accidentally
   ```
2. Destructure with default in the component signature:
   `hasWings = true,`
3. Compute the gated set of tabs:
   ```tsx
   const COMPUTATION_TABS = new Set<Tab>([
     "Polar", "Trefftz Plane", "Streamlines", "Envelope",
     "Stability", "Operating Points",
   ]);
   const showWingGate = !hasWings && COMPUTATION_TABS.has(activeTab);
   ```
4. Render the empty state once at the top of the tab-content area
   (before the per-tab branches), early-returning:
   ```tsx
   {showWingGate ? (
     <div className="flex flex-1 items-center justify-center bg-card-muted">
       <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
         Add a wing to enable aerodynamic analysis
       </span>
     </div>
   ) : (
     /* existing tab-content switch */
   )}
   ```
   `Assumptions` is not in `COMPUTATION_TABS`, so it always renders normally.

- [ ] **Step 4: Wire `hasWings` from the parent page**

The parent page that renders `AnalysisViewerPanel` already has the
aircraft tree (via `useComponents` or similar). Compute and pass:

```tsx
const hasWings = (components ?? []).some((c) => c.kind === "wing");
// or whatever the existing wing-detection convention is
<AnalysisViewerPanel hasWings={hasWings} ... />
```

Verify the actual prop names against the parent page when implementing
— do not invent component shape. Search for existing usages of
`<AnalysisViewerPanel` in the workbench pages.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend && npx vitest run __tests__/AnalysisWingGate.test.tsx`
Expected: PASS

- [ ] **Step 6: Run full frontend test suite**

Run: `cd frontend && npm run test:unit`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add frontend/components/workbench/AnalysisViewerPanel.tsx frontend/app/workbench/analysis/page.tsx frontend/__tests__/AnalysisWingGate.test.tsx
git commit -m "feat(gh-465): gate analysis tabs on wing existence"
```

---

### Task 11: Integration Test — Full Pipeline

**Files:**
- Create: `app/tests/test_assumption_compute_integration.py`

- [ ] **Step 1: Write integration test**

```python
# app/tests/test_assumption_compute_integration.py
import pytest
from unittest.mock import patch
from types import SimpleNamespace

from app.core.events import (
    AssumptionChanged,
    GeometryChanged,
    event_bus,
)
from app.models.aeroplanemodel import DesignAssumptionModel
from app.services.design_assumptions_service import seed_defaults
from app.tests.conftest import make_aeroplane


@pytest.mark.integration
def test_geometry_changed_handler_schedules_recompute():
    """Handler delegates to job_tracker.schedule_recompute_assumptions."""
    from app.services.invalidation_service import (
        _on_geometry_changed_recompute_assumptions,
    )

    # Patch the origin module — the handler does a lazy
    # `from app.core.background_jobs import job_tracker`.
    with patch("app.core.background_jobs.job_tracker") as mock_tracker:
        _on_geometry_changed_recompute_assumptions(
            GeometryChanged(aeroplane_id=42, source_model="WingModel")
        )

    mock_tracker.schedule_recompute_assumptions.assert_called_once_with(42)


@pytest.mark.integration
def test_recompute_publishes_assumption_changed_on_cg_change(client_and_db):
    """Full pipeline: recompute with seeded assumptions emits AssumptionChanged for cg_x."""
    from app.services.assumption_compute_service import recompute_assumptions

    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)

    captured: list = []
    handler = captured.append
    event_bus.subscribe(AssumptionChanged, handler)

    patches = [
        patch(
            "app.services.assumption_compute_service._build_asb_airplane",
            return_value=SimpleNamespace(wings=[object()], xyz_ref=[0.08, 0.0, 0.0]),
        ),
        patch(
            "app.services.assumption_compute_service._stability_run_at_cruise",
            return_value=(0.085, 0.20, 0.020),
        ),
        patch(
            "app.services.assumption_compute_service._coarse_alpha_sweep",
            return_value=14.0,
        ),
        patch(
            "app.services.assumption_compute_service._fine_sweep_cl_max",
            return_value=1.35,
        ),
        patch(
            "app.services.assumption_compute_service._load_flight_profile_speeds",
            return_value=(18.0, 28.0),
        ),
    ]

    try:
        for p in patches:
            p.start()
        with SessionLocal() as db:
            recompute_assumptions(db, aeroplane_uuid)
            db.commit()
    finally:
        for p in patches:
            p.stop()
        event_bus._subscribers.get(AssumptionChanged, []).remove(handler)

    cg_events = [e for e in captured if e.parameter_name == "cg_x"]
    assert len(cg_events) == 1


@pytest.mark.integration
def test_recompute_does_not_publish_when_cg_unchanged(client_and_db):
    """Second recompute with same inputs does not emit a duplicate event."""
    from app.services.assumption_compute_service import recompute_assumptions

    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)

    captured: list = []
    handler = captured.append
    event_bus.subscribe(AssumptionChanged, handler)

    patches = [
        patch(
            "app.services.assumption_compute_service._build_asb_airplane",
            return_value=SimpleNamespace(wings=[object()], xyz_ref=[0.08, 0.0, 0.0]),
        ),
        patch(
            "app.services.assumption_compute_service._stability_run_at_cruise",
            return_value=(0.085, 0.20, 0.020),
        ),
        patch(
            "app.services.assumption_compute_service._coarse_alpha_sweep",
            return_value=14.0,
        ),
        patch(
            "app.services.assumption_compute_service._fine_sweep_cl_max",
            return_value=1.35,
        ),
        patch(
            "app.services.assumption_compute_service._load_flight_profile_speeds",
            return_value=(18.0, 28.0),
        ),
    ]

    try:
        for p in patches:
            p.start()
        with SessionLocal() as db:
            recompute_assumptions(db, aeroplane_uuid)
            db.commit()
        with SessionLocal() as db:
            recompute_assumptions(db, aeroplane_uuid)
            db.commit()
    finally:
        for p in patches:
            p.stop()
        event_bus._subscribers.get(AssumptionChanged, []).remove(handler)

    cg_events = [e for e in captured if e.parameter_name == "cg_x"]
    assert len(cg_events) == 1  # Only first call emitted; second was idempotent
```

- [ ] **Step 2: Run integration test**

Run: `poetry run pytest app/tests/test_assumption_compute_integration.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add app/tests/test_assumption_compute_integration.py
git commit -m "test(gh-465): add integration tests for assumption recompute pipeline"
```

---

### Task 12: Browser Verification

- [ ] **Step 1: Start backend**

Run: `poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload`

- [ ] **Step 2: Start frontend**

Run: `cd frontend && npm run dev`

- [ ] **Step 3: Verify in browser**

1. Open the Analysis tab with an existing aircraft that has wings
2. Check the Info Chip Row — should show dynamic values (or "–" if never computed)
3. Go to Assumptions tab — values should have `calculated_value` populated
4. Modify a wing (e.g. change span) — after ~2s, assumptions should recompute
5. Check that OPs become DIRTY after CG changes
6. Delete all wings — computation tabs should show "Add a wing" message
7. Assumptions tab should still be accessible

- [ ] **Step 4: Run full test suites**

```bash
poetry run pytest -m "not slow"
cd frontend && npm run test:unit
```

- [ ] **Step 5: Commit any fixes from browser testing**

---

## File Summary

### New Files
| File | Purpose |
|------|---------|
| `app/models/computation_config.py` | SQLAlchemy model + defaults dict |
| `app/schemas/computation_config.py` | Pydantic read/write schemas |
| `app/services/assumption_compute_service.py` | Core recompute pipeline |
| `frontend/hooks/useComputationContext.ts` | SWR hook for context endpoint |
| `frontend/components/workbench/InfoChipRow.tsx` | Dynamic info chip component |

### Modified Files
| File | Change |
|------|--------|
| `app/models/aeroplanemodel.py` | Add `assumption_computation_context` column + `computation_config` relationship |
| `app/services/design_assumptions_service.py` | `auto_switch_source` param + seed computation config |
| `app/services/invalidation_service.py` | New GeometryChanged handler for recompute |
| `app/core/background_jobs.py` | `schedule_recompute_assumptions` + debounce |
| `app/main.py` | Wire recompute function to job tracker (via `asyncio.to_thread`) |
| `app/api/v2/endpoints/aeroplane/design_assumptions.py` | 3 new endpoints |
| `frontend/components/workbench/AnalysisViewerPanel.tsx` | `hasWings` prop + wing gate + InfoChipRow integration |
| Parent workbench analysis page | Pass `hasWings={...}` derived from components tree |

## Implementation Notes (Cross-Task)

- **ASB API surface:** `result.reference.Xnp`, `result.reference.Cref`,
  and `result.coefficients.CD` are accessed on the typed `AnalysisModel`
  returned by `app.api.utils.analyse_aerodynamics`. Direct ASB calls
  (`abu.run()`) return a dict-like — handle both via the `_extract_scalar`
  helper.
- **`xyz_ref` always passed:** Every `AeroBuildup` constructor in this
  feature receives `xyz_ref` so NP / CG values are referenced
  consistently with the rest of the system.
- **Sync vs async:** `recompute_assumptions` is sync. The wrapper in
  `app/main.py` invokes it via `asyncio.to_thread()` to keep the
  FastAPI event loop responsive.
- **`_get_aeroplane` reuse:** The compute service uses
  `design_assumptions_service._get_aeroplane(db, aeroplane_uuid)` —
  same UUID-resolution pattern as the rest of the assumptions code.
- **Test fixtures:** All DB-touching tests use the existing
  `client_and_db` fixture (in-memory SQLite) and the
  `make_aeroplane` factory from `app/tests/conftest.py`.
