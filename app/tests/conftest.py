"""Shared pytest fixtures for the cad-modelling-service test suite.

Everything that more than one test file needs lives here. New tests should
prefer these fixtures over reinventing the pattern.

Scope choices:
- `client_and_db` is function-scoped: each test gets a fresh in-memory SQLite
  and a fresh FastAPI TestClient. Max isolation, cheapest to reason about.
- `clean_cad_task_state` is function-scoped and autouse: every test starts
  with an empty cad_service.tasks dict so the global state stops leaking
  between tests.

Factory helpers return ORM instances that are already committed to the
session, so tests can rely on `.id` being populated.

gh-504: ``pytest_collection_modifyitems`` auto-tags tests by file name so
the CI tiering does not require hand-marking every file. The mapping is
unit-tested in ``test_marker_auto_tagging.py``.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.aeroplanemodel import (
    AeroplaneModel,
    DesignAssumptionModel,
    FuselageModel,
    WeightItemModel,
    WingModel,
    WingXSecDetailModel,
    WingXSecModel,
    WingXSecTrailingEdgeDeviceModel,
)
from app.models.analysismodels import OperatingPointModel
from app.services import cad_service
from app.services.component_type_service import seed_default_types


# --------------------------------------------------------------------------- #
# Auto-tagging by filename (gh-504)
# --------------------------------------------------------------------------- #
# The CI tiers (fast / full / nightly) filter tests via pytest markers, but
# hand-marking ~2500 tests is unrealistic. We derive the marker set from the
# test file name. The mapping is unit-tested in
# ``test_marker_auto_tagging.py`` so a rename can never silently move a
# test between tiers without the test catching it.


def _markers_for_path(path: str) -> list[str]:
    """Return marker names that should auto-apply to a test file at ``path``.

    Heuristics, in order of conservativeness:
    - ``_e2e`` / ``_smoke`` → ``e2e`` (heaviest tier, nightly only)
    - ``_integration`` → ``integration``
    - ``tessellation`` / ``fuselage_slice`` → ``requires_cadquery``
    - ``test_avl_*`` with ``generator`` / ``runner`` / ``strip_forces``
      in the name → ``requires_avl`` (real binary invocation, not just
      dataclass / geometry helpers)

    Note: ``requires_aerosandbox`` is intentionally NOT auto-tagged. The
    AeroSandbox-dependent files (e.g. ``test_analysis_smoke.py``,
    ``test_wingconfig_roundtrip.py``) use ``pytest.importorskip`` at the
    module level or per-test hand markers, so file-level tagging would
    double-mark. Add a heuristic here only if those files stop using
    importorskip.
    """
    name = os.path.basename(path)
    markers: list[str] = []

    if "_e2e" in name or "_smoke" in name:
        markers.append("e2e")
    if "_integration" in name:
        markers.append("integration")
    if "tessellation" in name or "fuselage_slice" in name:
        markers.append("requires_cadquery")
    if name.startswith("test_avl") and any(
        token in name for token in ("generator", "runner", "strip_forces")
    ):
        markers.append("requires_avl")

    return markers


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]  # noqa: ARG001
) -> None:
    """Apply markers derived from file name to every collected test item.

    ``config`` is required by the pluggy hookspec even though we do not
    use it; renaming to ``_config`` would fail plugin validation.
    """
    del config  # silence unused-arg linters; required by hookspec
    for item in items:
        for marker_name in _markers_for_path(str(item.path)):
            item.add_marker(getattr(pytest.mark, marker_name))


# --------------------------------------------------------------------------- #
# Core fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture()
def client_and_db() -> Tuple[TestClient, sessionmaker]:
    """Fresh FastAPI TestClient + in-memory SQLite session factory per test.

    Yields a tuple of (TestClient, SessionLocal). SessionLocal is a
    sessionmaker that test code can use to create extra sessions outside
    of the FastAPI dependency chain (e.g. for direct setup via factory
    helpers).
    """
    app = create_app()
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )
    Base.metadata.create_all(bind=engine)

    # gh#83: seed the default component types so tests see the same registry
    # shape that a migrated prod DB would have.
    _seed_session = TestingSessionLocal()
    try:
        seed_default_types(_seed_session)
        _seed_session.commit()
    finally:
        _seed_session.close()

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

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, TestingSessionLocal

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_cad_task_state():
    """Clear cad_service task state + process pool around every test.

    cad_service keeps task state in a module-level dict guarded by a Lock.
    Without this fixture, tasks from one test leak into the next and
    polling-based assertions become flaky.

    We also shut down the ProcessPoolExecutor both before and after each
    test so that no worker process outlives its test. The executor is
    lazily re-created by ``_get_executor`` when the next test actually
    submits CAD work, so tests that never touch the CAD path pay no
    spawn cost.
    """
    with cad_service.tasks_lock:
        cad_service.tasks.clear()
    cad_service.shutdown_executor()
    yield
    with cad_service.tasks_lock:
        cad_service.tasks.clear()
    cad_service.shutdown_executor()


# --------------------------------------------------------------------------- #
# Factory helpers
# --------------------------------------------------------------------------- #
# Direct-ORM style: the helpers talk to the session, not the REST API.
# The REST API itself is exercised in the test bodies, not in the setup.


def make_aeroplane(
    session: Session,
    *,
    name: str = "test-aeroplane",
    total_mass_kg: float | None = None,
) -> AeroplaneModel:
    """Create and commit a minimal AeroplaneModel."""
    aeroplane = AeroplaneModel(
        name=name,
        uuid=uuid.uuid4(),
        total_mass_kg=total_mass_kg,
    )
    session.add(aeroplane)
    session.commit()
    session.refresh(aeroplane)
    return aeroplane


def make_wing(
    session: Session,
    *,
    aeroplane_id: int,
    name: str = "main_wing",
    symmetric: bool = True,
) -> WingModel:
    """Create and commit a minimal WingModel tied to an existing aeroplane."""
    wing = WingModel(
        name=name,
        symmetric=symmetric,
        aeroplane_id=aeroplane_id,
    )
    session.add(wing)
    session.commit()
    session.refresh(wing)
    return wing


def make_fuselage(
    session: Session,
    *,
    aeroplane_id: int,
    name: str = "main_fuselage",
) -> FuselageModel:
    """Create and commit a minimal FuselageModel tied to an existing aeroplane."""
    fuselage = FuselageModel(
        name=name,
        aeroplane_id=aeroplane_id,
    )
    session.add(fuselage)
    session.commit()
    session.refresh(fuselage)
    return fuselage


def make_operating_point(
    session: Session,
    *,
    aircraft_id: int,
    name: str = "op_test",
    description: str = "",
    velocity: float = 20.0,
    alpha: float = 0.05,
    beta: float = 0.0,
    p: float = 0.0,
    q: float = 0.0,
    r: float = 0.0,
    xyz_ref: list[float] | None = None,
    altitude: float = 0.0,
    status: str = "TRIMMED",
    control_deflections: dict[str, float] | None = None,
) -> OperatingPointModel:
    """Create and commit a minimal OperatingPointModel tied to an aircraft."""
    op = OperatingPointModel(
        name=name,
        description=description,
        aircraft_id=aircraft_id,
        velocity=velocity,
        alpha=alpha,
        beta=beta,
        p=p,
        q=q,
        r=r,
        xyz_ref=xyz_ref or [0.0, 0.0, 0.0],
        altitude=altitude,
        status=status,
        control_deflections=control_deflections,
    )
    session.add(op)
    session.commit()
    session.refresh(op)
    return op


def _add_xsec(
    session: Session,
    wing: WingModel,
    *,
    xyz_le: list[float],
    chord: float,
    twist: float,
    airfoil: str,
    sort_index: int,
    x_sec_type: str | None = None,
    ted_kwargs: dict | None = None,
) -> WingXSecModel:
    """Create a WingXSecModel with optional detail and trailing edge device."""
    xsec = WingXSecModel(
        wing_id=wing.id,
        xyz_le=xyz_le,
        chord=chord,
        twist=twist,
        airfoil=airfoil,
        sort_index=sort_index,
    )
    session.add(xsec)
    session.flush()

    if x_sec_type or ted_kwargs:
        detail = WingXSecDetailModel(
            wing_xsec_id=xsec.id,
            x_sec_type=x_sec_type,
        )
        session.add(detail)
        session.flush()
        if ted_kwargs:
            ted = WingXSecTrailingEdgeDeviceModel(
                wing_xsec_detail_id=detail.id,
                **ted_kwargs,
            )
            session.add(ted)
            session.flush()

    return xsec


def seed_integration_aeroplane(session: Session) -> AeroplaneModel:
    """Create a complete aeroplane with main wing, htail, and vtail for integration tests.

    All geometry uses metres (DB convention). The plane has control surfaces
    on each wing root segment: aileron, elevator, and rudder.
    """
    aeroplane = AeroplaneModel(
        name="integration-test-plane",
        uuid=uuid.uuid4(),
        total_mass_kg=1.5,
        xyz_ref=[0.15, 0.0, 0.0],
    )
    session.add(aeroplane)
    session.flush()

    # --- main wing ---
    main_wing = WingModel(name="main_wing", symmetric=True, aeroplane_id=aeroplane.id)
    session.add(main_wing)
    session.flush()
    _add_xsec(
        session,
        main_wing,
        xyz_le=[0, 0, 0],
        chord=0.2,
        twist=2.0,
        airfoil="naca2412",
        sort_index=0,
        x_sec_type="segment",
        ted_kwargs={
            "name": "MainAileron",
            "role": "aileron",
            "rel_chord_root": 0.75,
            "rel_chord_tip": 0.75,
            "positive_deflection_deg": 25.0,
            "negative_deflection_deg": 25.0,
            "deflection_deg": 0.0,
            "symmetric": False,
        },
    )
    _add_xsec(
        session,
        main_wing,
        xyz_le=[0.0, 0.5, 0.0],
        chord=0.15,
        twist=0.0,
        airfoil="naca2412",
        sort_index=1,
    )

    # --- horizontal tail ---
    htail = WingModel(name="horizontal_tail", symmetric=True, aeroplane_id=aeroplane.id)
    session.add(htail)
    session.flush()
    _add_xsec(
        session,
        htail,
        xyz_le=[0.5, 0.0, 0.0],
        chord=0.1,
        twist=0.0,
        airfoil="naca0012",
        sort_index=0,
        x_sec_type="segment",
        ted_kwargs={
            "name": "Elevator",
            "role": "elevator",
            "rel_chord_root": 0.5,
            "rel_chord_tip": 0.5,
            "positive_deflection_deg": 25.0,
            "negative_deflection_deg": 25.0,
            "deflection_deg": 0.0,
            "symmetric": True,
        },
    )
    _add_xsec(
        session,
        htail,
        xyz_le=[0.5, 0.2, 0.0],
        chord=0.08,
        twist=0.0,
        airfoil="naca0012",
        sort_index=1,
    )

    # --- vertical tail ---
    vtail = WingModel(name="vertical_tail", symmetric=False, aeroplane_id=aeroplane.id)
    session.add(vtail)
    session.flush()
    _add_xsec(
        session,
        vtail,
        xyz_le=[0.5, 0.0, 0.0],
        chord=0.1,
        twist=0.0,
        airfoil="naca0009",
        sort_index=0,
        x_sec_type="segment",
        ted_kwargs={
            "name": "Rudder",
            "role": "rudder",
            "rel_chord_root": 0.5,
            "rel_chord_tip": 0.5,
            "positive_deflection_deg": 25.0,
            "negative_deflection_deg": 25.0,
            "deflection_deg": 0.0,
            "symmetric": True,
        },
    )
    _add_xsec(
        session,
        vtail,
        xyz_le=[0.5, 0.0, 0.15],
        chord=0.07,
        twist=0.0,
        airfoil="naca0009",
        sort_index=1,
    )

    session.commit()
    session.refresh(aeroplane)
    return aeroplane


def seed_design_assumptions(session: Session, aeroplane_id: int) -> list[DesignAssumptionModel]:
    """Seed the minimal set of design assumptions needed for analysis endpoints."""
    params = {
        "mass": 1.5,
        "cg_x": 0.15,
        "cl_max": 1.4,
        "g_limit": 3.0,
        "cd0": 0.03,
        "target_static_margin": 0.12,
    }
    rows = []
    for name, value in params.items():
        row = DesignAssumptionModel(
            aeroplane_id=aeroplane_id,
            parameter_name=name,
            estimate_value=value,
            active_source="ESTIMATE",
            updated_at=datetime.now(timezone.utc),
        )
        session.add(row)
        rows.append(row)
    session.commit()
    for r in rows:
        session.refresh(r)
    return rows


# --------------------------------------------------------------------------- #
# Smoke-plane shared helpers
# --------------------------------------------------------------------------- #

def _ted(name: str, role: str, *, symmetric: bool = False) -> dict:
    """Build a TED kwargs dict. All smoke TEDs use 75% hinge, ±25° deflection."""
    return {
        "name": name,
        "role": role,
        "rel_chord_root": 0.75,
        "rel_chord_tip": 0.75,
        "positive_deflection_deg": 25.0,
        "negative_deflection_deg": 25.0,
        "deflection_deg": 0.0,
        "symmetric": symmetric,
    }


_AILERON = _ted("Aileron", "aileron")
_ELEVATOR = _ted("Elevator", "elevator", symmetric=True)
_RUDDER = _ted("Rudder", "rudder", symmetric=True)


def _smoke_aeroplane(session: Session, name: str) -> AeroplaneModel:
    """Create base AeroplaneModel for smoke tests (Peter's Glider parameters)."""
    aeroplane = AeroplaneModel(
        name=name,
        uuid=uuid.uuid4(),
        total_mass_kg=1.5,
        xyz_ref=[0.15, 0.0, 0.0],
    )
    session.add(aeroplane)
    session.flush()
    return aeroplane


def _smoke_main_wing(
    session: Session,
    aeroplane_id: int,
    sec0_ted: dict | None = None,
    sec1_ted: dict | None = None,
) -> WingModel:
    """3-section symmetric main wing (sd7037). sec2 never has a TED."""
    wing = WingModel(name="main_wing", symmetric=True, aeroplane_id=aeroplane_id)
    session.add(wing)
    session.flush()

    _add_xsec(
        session,
        wing,
        xyz_le=[0, 0, 0],
        chord=0.18,
        twist=2.0,
        airfoil="sd7037",
        sort_index=0,
        **({"x_sec_type": "segment", "ted_kwargs": sec0_ted} if sec0_ted else {}),
    )
    _add_xsec(
        session,
        wing,
        xyz_le=[0.01, 0.5, 0],
        chord=0.16,
        twist=0.0,
        airfoil="sd7037",
        sort_index=1,
        **({"x_sec_type": "segment", "ted_kwargs": sec1_ted} if sec1_ted else {}),
    )
    _add_xsec(
        session,
        wing,
        xyz_le=[0.08, 1.0, 0.1],
        chord=0.08,
        twist=-2.0,
        airfoil="sd7037",
        sort_index=2,
    )
    return wing


def _smoke_htail(
    session: Session,
    aeroplane_id: int,
    z_offset: float = 0.06,
    ted_kwargs: dict | None = None,
) -> WingModel:
    """Symmetric horizontal tail (naca0010). TED on root section if provided."""
    htail = WingModel(name="horizontal_tail", symmetric=True, aeroplane_id=aeroplane_id)
    session.add(htail)
    session.flush()

    _add_xsec(
        session,
        htail,
        xyz_le=[0.6, 0, z_offset],
        chord=0.10,
        twist=-10.0,
        airfoil="naca0010",
        sort_index=0,
        **({"x_sec_type": "segment", "ted_kwargs": ted_kwargs} if ted_kwargs else {}),
    )
    _add_xsec(
        session,
        htail,
        xyz_le=[0.62, 0.17, z_offset],
        chord=0.08,
        twist=-10.0,
        airfoil="naca0010",
        sort_index=1,
    )
    return htail


def _smoke_vtail(
    session: Session,
    aeroplane_id: int,
    ted_kwargs: dict | None = None,
) -> WingModel:
    """Non-symmetric vertical tail (naca0010). TED on root section if provided."""
    vtail = WingModel(name="vertical_tail", symmetric=False, aeroplane_id=aeroplane_id)
    session.add(vtail)
    session.flush()

    _add_xsec(
        session,
        vtail,
        xyz_le=[0.6, 0, 0.07],
        chord=0.10,
        twist=0.0,
        airfoil="naca0010",
        sort_index=0,
        **({"x_sec_type": "segment", "ted_kwargs": ted_kwargs} if ted_kwargs else {}),
    )
    _add_xsec(
        session,
        vtail,
        xyz_le=[0.64, 0, 0.22],
        chord=0.06,
        twist=0.0,
        airfoil="naca0010",
        sort_index=1,
    )
    return vtail


# --------------------------------------------------------------------------- #
# Smoke-plane factory functions
# --------------------------------------------------------------------------- #


def seed_smoke_conventional_ttail(session: Session) -> AeroplaneModel:
    """Conventional T-tail: aileron on wing sec 1, elevator + rudder on tail."""
    aeroplane = _smoke_aeroplane(session, "smoke-conventional-ttail")
    _smoke_main_wing(session, aeroplane.id, sec1_ted=_AILERON)
    _smoke_htail(session, aeroplane.id, z_offset=0.06, ted_kwargs=_ELEVATOR)
    _smoke_vtail(session, aeroplane.id, ted_kwargs=_RUDDER)
    session.commit()
    session.refresh(aeroplane)
    return aeroplane


def seed_smoke_vtail_ruddervator(session: Session) -> AeroplaneModel:
    """V-tail with ruddervator: aileron on wing sec 1, ruddervator on V-tail."""
    aeroplane = _smoke_aeroplane(session, "smoke-vtail-ruddervator")
    _smoke_main_wing(session, aeroplane.id, sec1_ted=_AILERON)

    # V-tail: symmetric wing with dihedral simulated via z at tip
    vtail = WingModel(name="v_tail", symmetric=True, aeroplane_id=aeroplane.id)
    session.add(vtail)
    session.flush()

    _add_xsec(
        session,
        vtail,
        xyz_le=[0.6, 0, 0.06],
        chord=0.12,
        twist=-10.0,
        airfoil="naca0010",
        sort_index=0,
        x_sec_type="segment",
        ted_kwargs=_ted("Ruddervator", "ruddervator", symmetric=True),
    )
    _add_xsec(
        session,
        vtail,
        xyz_le=[0.62, 0.17, 0.12],
        chord=0.08,
        twist=-10.0,
        airfoil="naca0010",
        sort_index=1,
    )

    session.commit()
    session.refresh(aeroplane)
    return aeroplane


def seed_smoke_conventional_cross(session: Session) -> AeroplaneModel:
    """Conventional cross-tail: aileron on wing sec 1, elevator + rudder, htail at z=0."""
    aeroplane = _smoke_aeroplane(session, "smoke-conventional-cross")
    _smoke_main_wing(session, aeroplane.id, sec1_ted=_AILERON)
    _smoke_htail(session, aeroplane.id, z_offset=0.0, ted_kwargs=_ELEVATOR)
    _smoke_vtail(session, aeroplane.id, ted_kwargs=_RUDDER)
    session.commit()
    session.refresh(aeroplane)
    return aeroplane


def seed_smoke_flying_wing(session: Session) -> AeroplaneModel:
    """Flying wing: elevon on sec 0, elevon on sec 1, no tail."""
    aeroplane = _smoke_aeroplane(session, "smoke-flying-wing")

    _smoke_main_wing(
        session, aeroplane.id,
        sec0_ted=_ted("Elevon_0", "elevon"),
        sec1_ted=_ted("Elevon_1", "elevon"),
    )

    session.commit()
    session.refresh(aeroplane)
    return aeroplane


def seed_smoke_flaperon_ttail(session: Session) -> AeroplaneModel:
    """Flaperon T-tail: flaperon on sec 0 + sec 1, elevator + rudder on tail."""
    aeroplane = _smoke_aeroplane(session, "smoke-flaperon-ttail")

    _smoke_main_wing(
        session, aeroplane.id,
        sec0_ted=_ted("Flaperon_0", "flaperon"),
        sec1_ted=_ted("Flaperon_1", "flaperon"),
    )
    _smoke_htail(session, aeroplane.id, z_offset=0.06, ted_kwargs=_ELEVATOR)
    _smoke_vtail(session, aeroplane.id, ted_kwargs=_RUDDER)

    session.commit()
    session.refresh(aeroplane)
    return aeroplane


def seed_smoke_flap_aileron_ttail(session: Session) -> AeroplaneModel:
    """Flap+aileron T-tail: flap on sec 0, aileron on sec 1, elevator + rudder on tail."""
    aeroplane = _smoke_aeroplane(session, "smoke-flap-aileron-ttail")

    _smoke_main_wing(
        session, aeroplane.id,
        sec0_ted=_ted("Flap", "flap", symmetric=True),
        sec1_ted=_AILERON,
    )
    _smoke_htail(session, aeroplane.id, z_offset=0.06, ted_kwargs=_ELEVATOR)
    _smoke_vtail(session, aeroplane.id, ted_kwargs=_RUDDER)

    session.commit()
    session.refresh(aeroplane)
    return aeroplane


def seed_smoke_stabilator_ttail(session: Session) -> AeroplaneModel:
    """Stabilator T-tail: aileron on wing sec 1, htail has NO TED (all-moving), rudder only."""
    aeroplane = _smoke_aeroplane(session, "smoke-stabilator-ttail")
    _smoke_main_wing(session, aeroplane.id, sec1_ted=_AILERON)
    _smoke_htail(session, aeroplane.id, z_offset=0.06, ted_kwargs=None)
    _smoke_vtail(session, aeroplane.id, ted_kwargs=_RUDDER)

    session.commit()
    session.refresh(aeroplane)
    return aeroplane
