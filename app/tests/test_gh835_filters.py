"""Tests for gh-835: family/tag/thickness filters on GET /airfoils/db/suitability.

TDD tests for:
  - filter_families → only matching family airfoils returned
  - filter_tags → only matching-tag airfoils returned
  - filter_thickness_min/max_pct → bounds on t/c
  - AND logic across dimensions
  - no-filter behaviour identical to before
  - `include` bypass (named airfoils pass through even when filtered out)
  - `tags` field present on each SuitabilityItem
  - endpoint query param wiring (CSV parsing, validation)
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


# ── In-memory DB fixture ──────────────────────────────────────────────────────


@pytest.fixture()
def in_memory_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app.db.base import Base
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    yield SessionLocal
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def seeded_db(in_memory_db):
    """DB seeded with 4 airfoils covering the families we filter on.

    Airfoils:
      sym_12  — symmetric,     t=12 %,  c=0.0  → tags: v_stab, h_stab, acro, low_re
      ref_9   — reflexed,      t=9 %,   c=1.5  → tags: winglet, low_re
      flat_11 — flat_bottom,   t=11 %,  c=3.9  → tags: low_re
      camb_14 — cambered,      t=14 %,  c=4.0  → tags: low_re (thick enough to be out of acro)
    """
    from app.models.airfoil import AirfoilModel
    from app.models.airfoil_low_re import AirfoilGeometryModel, AirfoilLowRePolarModel

    with in_memory_db() as session:
        # Create airfoil records
        for name in ("sym_12", "ref_9", "flat_11", "camb_14"):
            session.add(AirfoilModel(name=name, coordinates=[[0, 0], [0.5, 0.05], [1, 0]]))
        session.flush()

        # Geometry rows
        geos = {
            "sym_12": ("symmetric", 12.0, 0.0, 0.0),
            "ref_9": ("reflexed", 9.0, 1.5, 0.05),
            "flat_11": ("flat_bottom", 11.0, 3.9, 0.0),
            "camb_14": ("cambered", 14.0, 4.0, 0.0),
        }
        for name, (fam, t, c, te) in geos.items():
            session.add(
                AirfoilGeometryModel(
                    airfoil_name=name,
                    family=fam,
                    max_thickness_pct=t,
                    max_camber_pct=c,
                    camber_at_te=te,
                )
            )
        session.flush()

        # Low-Re polars — one at Re=100k (confident) for all airfoils
        for name in ("sym_12", "ref_9", "flat_11", "camb_14"):
            session.add(
                AirfoilLowRePolarModel(
                    airfoil_name=name,
                    reynolds=100_000.0,
                    ld_max=30.0,
                    cl_max=1.2,
                    cd_min=0.008,
                    drag_bucket_width=0.4,
                    stall_gentleness=-0.02,
                    cd0=0.008,
                    k=0.04,
                    cl0=0.1,
                    cl_valid_lo=0.0,
                    cl_valid_hi=1.0,
                    min_analysis_confidence=0.92,
                )
            )
        session.commit()

    yield in_memory_db


# ── Service-level filter tests ────────────────────────────────────────────────


def _call(db_factory, **kwargs):
    """Helper: call search_suitability with given kwargs, return results."""
    from app.services.suitability_service import search_suitability

    with db_factory() as db:
        resp = search_suitability(db=db, chord_m=0.2, speed_ms=14.0, **kwargs)
    return resp


def test_no_filter_returns_all_four(seeded_db):
    resp = _call(seeded_db)
    names = {item.airfoil_name for item in resp.results}
    assert {"sym_12", "ref_9", "flat_11", "camb_14"} == names


def test_filter_family_reflexed_returns_only_reflexed(seeded_db):
    resp = _call(seeded_db, filter_families=["reflexed"])
    names = {item.airfoil_name for item in resp.results}
    assert names == {"ref_9"}


def test_filter_family_or_logic(seeded_db):
    """family=reflexed,flat_bottom → union of both families."""
    resp = _call(seeded_db, filter_families=["reflexed", "flat_bottom"])
    names = {item.airfoil_name for item in resp.results}
    assert names == {"ref_9", "flat_11"}


def test_filter_family_symmetric(seeded_db):
    resp = _call(seeded_db, filter_families=["symmetric"])
    names = {item.airfoil_name for item in resp.results}
    assert names == {"sym_12"}


def test_filter_tags_acro_returns_only_symmetric(seeded_db):
    """acro tag requires symmetric family with 7<=t<=12 and camber<=0.5."""
    resp = _call(seeded_db, filter_tags=["acro"])
    names = {item.airfoil_name for item in resp.results}
    assert names == {"sym_12"}


def test_filter_tags_winglet(seeded_db):
    """winglet tag: reflexed/symmetric/semi_sym, thin, low camber, confident low-Re polar."""
    resp = _call(seeded_db, filter_tags=["winglet"])
    names = {item.airfoil_name for item in resp.results}
    # ref_9 (reflexed, t=9, c=1.5) and sym_12 (symmetric, t=12 is > 10 → fails winglet)
    # sym_12 has t=12 which is > 10 → does NOT get winglet
    assert "ref_9" in names
    assert "sym_12" not in names


def test_filter_tags_or_logic(seeded_db):
    """tags=acro,winglet: union — sym_12 (acro) + ref_9 (winglet)."""
    resp = _call(seeded_db, filter_tags=["acro", "winglet"])
    names = {item.airfoil_name for item in resp.results}
    assert "sym_12" in names
    assert "ref_9" in names


def test_filter_thickness_min(seeded_db):
    """thickness_min_pct=12 → only airfoils with t >= 12."""
    resp = _call(seeded_db, filter_thickness_min_pct=12.0)
    for item in resp.results:
        geo = {"sym_12": 12.0, "ref_9": 9.0, "flat_11": 11.0, "camb_14": 14.0}
        assert geo[item.airfoil_name] >= 12.0


def test_filter_thickness_max(seeded_db):
    """thickness_max_pct=10 → only ref_9 (t=9)."""
    resp = _call(seeded_db, filter_thickness_max_pct=10.0)
    names = {item.airfoil_name for item in resp.results}
    assert names == {"ref_9"}


def test_filter_thickness_min_and_max_combined(seeded_db):
    """11 <= t <= 13 → sym_12 (t=12) and flat_11 (t=11), not camb_14 (t=14) or ref_9 (t=9)."""
    resp = _call(seeded_db, filter_thickness_min_pct=11.0, filter_thickness_max_pct=13.0)
    names = {item.airfoil_name for item in resp.results}
    assert names == {"sym_12", "flat_11"}


def test_filter_family_and_tags_combined(seeded_db):
    """family=symmetric AND tags=acro → sym_12 only."""
    resp = _call(seeded_db, filter_families=["symmetric"], filter_tags=["acro"])
    names = {item.airfoil_name for item in resp.results}
    assert names == {"sym_12"}


def test_filter_empty_result(seeded_db):
    """Filter that matches nothing → empty results list."""
    resp = _call(seeded_db, filter_families=["semi_symmetric"])
    assert resp.results == []


def test_include_bypasses_family_filter(seeded_db):
    """include=['ref_9'] passes through even when family filter excludes reflexed."""
    resp = _call(seeded_db, filter_families=["symmetric"], include=["ref_9"])
    names = {item.airfoil_name for item in resp.results}
    # ref_9 is reflexed but was forced through by `include`
    assert "ref_9" in names
    assert "sym_12" in names


def test_include_bypasses_tag_filter(seeded_db):
    """include=['flat_11'] passes through even when tags filter excludes flat_bottom."""
    resp = _call(seeded_db, filter_tags=["acro"], include=["flat_11"])
    names = {item.airfoil_name for item in resp.results}
    assert "flat_11" in names
    assert "sym_12" in names


def test_tags_field_present_on_every_item(seeded_db):
    """Every SuitabilityItem must have a `tags` field (even if empty list)."""
    resp = _call(seeded_db)
    for item in resp.results:
        assert isinstance(item.tags, list), f"{item.airfoil_name}.tags is not a list"


def test_sym_12_has_expected_tags(seeded_db):
    """sym_12 should carry v_stabilizer, h_stabilizer, acro, low_re."""
    resp = _call(seeded_db)
    item = next(i for i in resp.results if i.airfoil_name == "sym_12")
    assert "v_stabilizer" in item.tags
    assert "h_stabilizer" in item.tags
    assert "acro" in item.tags
    assert "low_re" in item.tags


def test_ref_9_has_winglet_and_low_re_tags(seeded_db):
    """ref_9 (reflexed, t=9, c=1.5) should have winglet and low_re tags."""
    resp = _call(seeded_db)
    item = next(i for i in resp.results if i.airfoil_name == "ref_9")
    assert "winglet" in item.tags
    assert "low_re" in item.tags


def test_no_filter_behaviour_identical_to_before(seeded_db):
    """Calling without any filter returns same set + same order as before gh-835."""
    from app.services.suitability_service import search_suitability

    with seeded_db() as db:
        r_baseline = search_suitability(db=db, chord_m=0.2, speed_ms=14.0)
    with seeded_db() as db:
        r_no_filter = search_suitability(
            db=db,
            chord_m=0.2,
            speed_ms=14.0,
            filter_families=None,
            filter_tags=None,
            filter_thickness_min_pct=None,
            filter_thickness_max_pct=None,
        )

    # Same names, same order
    assert [i.airfoil_name for i in r_baseline.results] == [
        i.airfoil_name for i in r_no_filter.results
    ]
    # Same scores
    for a, b in zip(r_baseline.results, r_no_filter.results, strict=True):
        assert abs(a.re_agnostic - b.re_agnostic) < 1e-9


# ── Endpoint-level tests (CSV parsing + validation) ──────────────────────────


@pytest.fixture()
def client(seeded_db):
    """TestClient against the real app with seeded in-memory DB."""
    from app.db.base import Base
    from app.db.session import get_db
    from app.main import create_app
    from app.services.component_type_service import seed_default_types
    from app.services.mission_objective_service import seed_mission_presets

    # Re-use the same seeded_db factory
    _factory = seeded_db

    app = create_app()

    def override_get_db():
        db = _factory()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c


def test_endpoint_family_csv_param(client):
    r = client.get("/airfoils/db/suitability?chord_m=0.2&speed_ms=14&family=reflexed")
    assert r.status_code == 200
    data = r.json()
    for item in data["results"]:
        assert item["family"] == "reflexed"


def test_endpoint_tags_csv_param(client):
    r = client.get("/airfoils/db/suitability?chord_m=0.2&speed_ms=14&tags=acro")
    assert r.status_code == 200
    data = r.json()
    for item in data["results"]:
        assert "acro" in item["tags"]


def test_endpoint_thickness_params(client):
    r = client.get(
        "/airfoils/db/suitability?chord_m=0.2&speed_ms=14&thickness_min_pct=11&thickness_max_pct=13"
    )
    assert r.status_code == 200


def test_endpoint_invalid_family_returns_422(client):
    r = client.get("/airfoils/db/suitability?chord_m=0.2&speed_ms=14&family=not_a_family")
    assert r.status_code == 422


def test_endpoint_invalid_tag_returns_422(client):
    r = client.get("/airfoils/db/suitability?chord_m=0.2&speed_ms=14&tags=not_a_tag")
    assert r.status_code == 422


def test_endpoint_no_filter_has_tags_field(client):
    """Every result item should have a `tags` key in the JSON even without filters."""
    r = client.get("/airfoils/db/suitability?chord_m=0.2&speed_ms=14")
    assert r.status_code == 200
    for item in r.json()["results"]:
        assert "tags" in item
        assert isinstance(item["tags"], list)


def test_endpoint_family_or_csv(client):
    """family=reflexed,symmetric returns both families."""
    r = client.get("/airfoils/db/suitability?chord_m=0.2&speed_ms=14&family=reflexed,symmetric")
    assert r.status_code == 200
    families = {item["family"] for item in r.json()["results"]}
    assert families == {"reflexed", "symmetric"}
