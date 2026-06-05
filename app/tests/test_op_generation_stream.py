"""gh-865: streaming OP generation emits SSE (targets → op → done) and
persists each operating point incrementally."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.aeroplanemodel import AeroplaneModel
from app.models.analysismodels import OperatingPointModel, OperatingPointSetModel
from app.schemas.aeroanalysisschema import OperatingPointStatus
from app.services import operating_point_generator_service as opg
from app.services.operating_point_generator_service import TrimmedPoint, _GenerationContext
from app.services.trim_enrichment_service import compute_enrichment


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def _aircraft(db) -> AeroplaneModel:
    ac = AeroplaneModel(name="streamer", total_mass_kg=2.0)
    db.add(ac)
    db.commit()
    db.refresh(ac)
    return ac


def _point(name: str) -> TrimmedPoint:
    return TrimmedPoint(
        name=name,
        description=f"mock {name}",
        config="clean",
        velocity=15.0,
        altitude=0.0,
        alpha_rad=0.05,
        beta_rad=0.0,
        p=0.0,
        q=0.0,
        r=0.0,
        status=OperatingPointStatus.TRIMMED,
        warnings=[],
        controls={"[elevator]Elevator": -2.0},
        trim_enrichment=compute_enrichment(
            controls={"[elevator]Elevator": -2.0},
            limits={"[elevator]Elevator": (25.0, 25.0)},
            trim_method="opti",
            trim_score=0.01,
            trim_residuals={},
            op_name=name,
            alpha_deg=3.0,
            aero_coefficients={"CL": 0.4, "CD": 0.03},
        ).model_dump(),
    )


def _parse_sse(chunks: list[str]) -> list[tuple[str, dict]]:
    events = []
    for chunk in chunks:
        lines = chunk.strip().splitlines()
        event = next(line[len("event: ") :] for line in lines if line.startswith("event: "))
        data = next(line[len("data: ") :] for line in lines if line.startswith("data: "))
        events.append((event, json.loads(data)))
    return events


def _ctx(aircraft, targets) -> _GenerationContext:
    return _GenerationContext(
        aircraft=aircraft,
        targets=targets,
        asb_airplane=object(),
        capabilities={"available_controls": ["[elevator]Elevator"]},
        deflection_limits={},
        plane_schema=object(),
        constraints={},
        effective_mass_kg=2.0,
        design_cg_x=0.1,
        source_profile_id=None,
        refs={"vs_clean": 8.0},
    )


def test_stream_emits_targets_then_op_per_point_then_done(db_session):
    aircraft = _aircraft(db_session)
    targets = [{"name": "cruise", "config": "clean"}, {"name": "stall", "config": "clean"}]
    ctx = _ctx(aircraft, targets)

    with (
        patch.object(opg, "_prepare_generation", return_value=ctx),
        patch.object(opg, "_validate_target_capability", return_value=(True, [])),
        patch.object(opg, "_solve_and_enrich", side_effect=lambda _c, t: _point(t["name"])),
    ):
        chunks = list(
            opg.generate_default_set_stream_for_aircraft(
                db_session, aircraft.uuid, replace_existing=True
            )
        )

    events = _parse_sse(chunks)
    names = [e[0] for e in events]
    assert names == ["targets", "op", "op", "done"]

    # targets event: both placeholder rows, COMPUTING
    _, targets_payload = events[0]
    assert [t["name"] for t in targets_payload["targets"]] == ["cruise", "stall"]
    assert all(t["status"] == "COMPUTING" for t in targets_payload["targets"])

    # each op event carries a real persisted operating point with aero
    op_names = [events[1][1]["name"], events[2][1]["name"]]
    assert op_names == ["cruise", "stall"]
    assert events[1][1]["trim_enrichment"]["aero_coefficients"]["CL"] == 0.4

    # done event + incremental persistence
    assert events[3][1]["count"] == 2
    assert db_session.query(OperatingPointModel).count() == 2
    opset = db_session.query(OperatingPointSetModel).one()
    assert len(opset.operating_points) == 2


def test_stream_skips_unsolvable_targets(db_session):
    aircraft = _aircraft(db_session)
    targets = [{"name": "ok", "config": "clean"}, {"name": "bad", "config": "clean"}]
    ctx = _ctx(aircraft, targets)

    def _solve(_c, t):
        return None if t["name"] == "bad" else _point(t["name"])

    with (
        patch.object(opg, "_prepare_generation", return_value=ctx),
        patch.object(opg, "_validate_target_capability", return_value=(True, [])),
        patch.object(opg, "_solve_and_enrich", side_effect=_solve),
    ):
        events = _parse_sse(
            list(opg.generate_default_set_stream_for_aircraft(db_session, aircraft.uuid))
        )

    names = [e[0] for e in events]
    assert names == ["targets", "op", "skip", "done"]
    assert events[2][1]["name"] == "bad"
    assert events[3][1]["count"] == 1
    assert db_session.query(OperatingPointModel).count() == 1
