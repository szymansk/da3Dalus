"""TDD tests for gh-838 (target-CL scored at own Re) and gh-839-BE (speed fields in query).

RED first, then GREEN.

#838: The three target-CL lenses (cruise/best_glide/min_sink) must each be
      scored at their OWN Reynolds number (derived from their own speed + chord),
      not the shared query Re from the slider.

      Key test: when speed_ms changes but the aeroplane context stays the same,
      the re_agnostic score DOES change (it uses query Re), while the three
      target_cl scores stay IDENTICAL (they use the per-lens Re derived from
      v_cruise_mps / v_md_mps / v_min_sink_mps in the context, which are fixed).

#839-BE: query{} block must expose v_cruise_mps, v_md_mps, v_min_sink_mps
         from the aeroplane context (additive; null when absent).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


# ---------------------------------------------------------------------------
# Shared in-memory DB fixture
# ---------------------------------------------------------------------------


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
def seeded_db_838(in_memory_db):
    """DB with one airfoil (two Re polars) + aeroplane with v_cruise/v_md/v_min_sink context."""
    from app.models.airfoil import AirfoilModel
    from app.models.airfoil_low_re import AirfoilGeometryModel, AirfoilLowRePolarModel
    from app.models.aeroplanemodel import AeroplaneModel

    ap_uuid = uuid.uuid4()

    with in_memory_db() as session:
        session.add(AirfoilModel(name="e423", coordinates=[[0, 0], [0.5, 0.08], [1, 0]]))
        session.flush()
        session.add(
            AirfoilGeometryModel(
                airfoil_name="e423",
                max_thickness_pct=12.0,
                max_camber_pct=5.0,
                camber_at_te=0.001,
                family="cambered",
                computed_at=datetime.now(timezone.utc),
            )
        )
        # Two Re grid points so interpolation works
        for re_val, ld, cl_max_v, cd0, k, cl0, bucket, stall_g in [
            (100_000, 45.0, 1.3, 0.012, 0.040, 0.25, 0.60, -0.03),
            (250_000, 60.0, 1.4, 0.009, 0.033, 0.28, 0.72, -0.02),
        ]:
            session.add(
                AirfoilLowRePolarModel(
                    airfoil_name="e423",
                    reynolds=float(re_val),
                    ld_max=ld,
                    cl_max=cl_max_v,
                    alpha_attached_lo=-4.0,
                    alpha_attached_hi=14.0,
                    drag_bucket_width=bucket,
                    cd_min=cd0,
                    stall_gentleness=stall_g,
                    cd0=cd0,
                    k=k,
                    cl0=cl0,
                    cl_valid_lo=0.0,
                    cl_valid_hi=cl_max_v,
                    min_analysis_confidence=0.95,
                    neuralfoil_model_size="xxxlarge",
                    n_crit=9.0,
                    computed_at=datetime.now(timezone.utc),
                )
            )

        # Aeroplane: v_cruise=18, v_md=13, v_min_sink=10 m/s
        ap = AeroplaneModel(
            name="glider838",
            uuid=ap_uuid,
            total_mass_kg=3.0,
            assumption_computation_context={
                "mass_kg": 3.0,
                "s_ref_m2": 0.50,
                "v_cruise_mps": 18.0,
                "v_md_mps": 13.0,
                "v_min_sink_mps": 10.0,
                "v_cruise_auto": True,
            },
        )
        session.add(ap)
        session.commit()

    return in_memory_db, ap_uuid


# ---------------------------------------------------------------------------
# gh-838: target-CL scores are slider-independent (use own Re)
# ---------------------------------------------------------------------------


class TestTargetClOwnRe:
    """gh-838 — each target-CL lens uses its own speed-derived Re."""

    def test_target_cl_scores_same_at_different_slider_speeds(self, seeded_db_838):
        """target_cl_* scores must be IDENTICAL for two different speed_ms values
        (same aeroplane + chord), because they use the fixed context speeds.
        re_agnostic must DIFFER (it uses the slider Re).
        """
        from app.services.suitability_service import search_suitability

        SessionLocal, ap_uuid = seeded_db_838
        chord = 0.18  # metres

        with SessionLocal() as s1:
            r1 = search_suitability(db=s1, chord_m=chord, speed_ms=12.0, aeroplane_id=str(ap_uuid))
        with SessionLocal() as s2:
            r2 = search_suitability(db=s2, chord_m=chord, speed_ms=20.0, aeroplane_id=str(ap_uuid))

        # Must have results
        assert len(r1.results) > 0
        assert len(r2.results) > 0

        item1 = r1.results[0]
        item2 = r2.results[0]

        # re_agnostic MUST differ (uses query Re = slider × chord)
        assert item1.re_agnostic != pytest.approx(item2.re_agnostic, abs=0.001), (
            "re_agnostic should differ across different slider speeds"
        )

        # target_cl_cruise scores must be the SAME (own Re = v_cruise * chord / nu)
        if item1.target_cl_cruise is not None and item2.target_cl_cruise is not None:
            assert item1.target_cl_cruise == pytest.approx(item2.target_cl_cruise, abs=1e-6), (
                f"target_cl_cruise scores should be identical: "
                f"{item1.target_cl_cruise} vs {item2.target_cl_cruise}"
            )

        # target_cl_best_glide scores must be the SAME
        if item1.target_cl_best_glide is not None and item2.target_cl_best_glide is not None:
            assert item1.target_cl_best_glide == pytest.approx(
                item2.target_cl_best_glide, abs=1e-6
            ), (
                f"target_cl_best_glide scores should be identical: "
                f"{item1.target_cl_best_glide} vs {item2.target_cl_best_glide}"
            )

        # target_cl_min_sink scores must be the SAME
        if item1.target_cl_min_sink is not None and item2.target_cl_min_sink is not None:
            assert item1.target_cl_min_sink == pytest.approx(item2.target_cl_min_sink, abs=1e-6), (
                f"target_cl_min_sink scores should be identical: "
                f"{item1.target_cl_min_sink} vs {item2.target_cl_min_sink}"
            )

    def test_target_cl_scores_present(self, seeded_db_838):
        """All three target-CL scores must be computed (not None) when context is complete."""
        from app.services.suitability_service import search_suitability

        SessionLocal, ap_uuid = seeded_db_838
        with SessionLocal() as session:
            resp = search_suitability(
                db=session, chord_m=0.18, speed_ms=15.0, aeroplane_id=str(ap_uuid)
            )
        item = resp.results[0]
        assert item.target_cl_cruise is not None
        assert item.target_cl_best_glide is not None
        assert item.target_cl_min_sink is not None

    def test_re_agnostic_lens_uses_query_re(self, seeded_db_838):
        """Without aeroplane context, target_cl scores are None; re_agnostic differs
        between slider speeds."""
        from app.services.suitability_service import search_suitability

        SessionLocal, _ = seeded_db_838
        with SessionLocal() as s1:
            r1 = search_suitability(db=s1, chord_m=0.18, speed_ms=10.0)
        with SessionLocal() as s2:
            r2 = search_suitability(db=s2, chord_m=0.18, speed_ms=20.0)

        item1 = r1.results[0]
        item2 = r2.results[0]

        # No context → all target_cl_* are None
        assert item1.target_cl_cruise is None
        assert item1.target_cl_best_glide is None
        assert item1.target_cl_min_sink is None

        # re_agnostic differs across speeds (different Re → different polar interpolation)
        assert item1.re_agnostic != pytest.approx(item2.re_agnostic, abs=0.001)

    def test_fallback_to_query_re_when_no_aeroplane(self, seeded_db_838):
        """Explicit target_cl_* params (no aeroplane) still score at query Re (slider).
        Two calls with different speed_ms and the SAME explicit target_cl_cruise
        must produce different cruise scores — they use the slider Re for the polar.
        """
        from app.services.suitability_service import search_suitability

        SessionLocal, _ = seeded_db_838
        with SessionLocal() as s1:
            r1 = search_suitability(db=s1, chord_m=0.18, speed_ms=10.0, target_cl_cruise=0.5)
        with SessionLocal() as s2:
            r2 = search_suitability(db=s2, chord_m=0.18, speed_ms=20.0, target_cl_cruise=0.5)

        # Both have target_cl_cruise scored
        assert r1.results[0].target_cl_cruise is not None
        assert r2.results[0].target_cl_cruise is not None

        # Scores differ because they use the slider Re (polar differs at Re=10*0.18/nu vs 20*0.18/nu)
        assert r1.results[0].target_cl_cruise != pytest.approx(
            r2.results[0].target_cl_cruise, abs=0.001
        ), "Explicit target_cl with no aeroplane should use slider Re → scores differ"


# ---------------------------------------------------------------------------
# gh-839-BE: speed fields in query{}
# ---------------------------------------------------------------------------


class TestSpeedFieldsInQuery:
    """gh-839-BE: v_cruise_mps, v_md_mps, v_min_sink_mps exposed in query{}."""

    def test_schema_has_speed_fields(self):
        """SuitabilityQuery schema must accept the three speed fields."""
        from app.schemas.airfoil import SuitabilityQuery

        q = SuitabilityQuery(
            chord_m=0.15,
            speed_ms=15.0,
            reynolds=150_000.0,
            re_clamped=False,
            active_lens="re_agnostic",
            target_cl_provenance="estimated",
            v_cruise_mps=18.0,
            v_md_mps=13.0,
            v_min_sink_mps=10.0,
        )
        assert q.v_cruise_mps == pytest.approx(18.0)
        assert q.v_md_mps == pytest.approx(13.0)
        assert q.v_min_sink_mps == pytest.approx(10.0)

    def test_schema_speed_fields_default_to_none(self):
        """Speed fields must be Optional (null when absent)."""
        from app.schemas.airfoil import SuitabilityQuery

        q = SuitabilityQuery(
            chord_m=0.15,
            speed_ms=15.0,
            reynolds=150_000.0,
            re_clamped=False,
            active_lens="re_agnostic",
            target_cl_provenance="estimated",
        )
        assert q.v_cruise_mps is None
        assert q.v_md_mps is None
        assert q.v_min_sink_mps is None

    def test_service_populates_speed_fields_from_context(self, seeded_db_838):
        """search_suitability must populate v_cruise_mps/v_md_mps/v_min_sink_mps
        from the aeroplane context."""
        from app.services.suitability_service import search_suitability

        SessionLocal, ap_uuid = seeded_db_838
        with SessionLocal() as session:
            resp = search_suitability(
                db=session, chord_m=0.18, speed_ms=15.0, aeroplane_id=str(ap_uuid)
            )
        assert resp.query.v_cruise_mps == pytest.approx(18.0)
        assert resp.query.v_md_mps == pytest.approx(13.0)
        assert resp.query.v_min_sink_mps == pytest.approx(10.0)

    def test_service_speed_fields_null_without_aeroplane(self, seeded_db_838):
        """Without aeroplane context, speed fields must be null."""
        from app.services.suitability_service import search_suitability

        SessionLocal, _ = seeded_db_838
        with SessionLocal() as session:
            resp = search_suitability(db=session, chord_m=0.18, speed_ms=15.0)
        assert resp.query.v_cruise_mps is None
        assert resp.query.v_md_mps is None
        assert resp.query.v_min_sink_mps is None

    def test_service_speed_fields_partial_when_missing_context_key(self, in_memory_db):
        """If v_md_mps is absent from context, v_md_mps in query must be None."""
        from app.models.airfoil import AirfoilModel
        from app.models.airfoil_low_re import AirfoilGeometryModel
        from app.models.aeroplanemodel import AeroplaneModel
        from app.services.suitability_service import search_suitability

        ap_uuid = uuid.uuid4()
        with in_memory_db() as session:
            session.add(AirfoilModel(name="af_partial", coordinates=[[0, 0], [1, 0]]))
            session.flush()
            session.add(
                AirfoilGeometryModel(
                    airfoil_name="af_partial",
                    max_thickness_pct=10.0,
                    max_camber_pct=2.0,
                    camber_at_te=0.0,
                    family="cambered",
                    computed_at=datetime.now(timezone.utc),
                )
            )
            ap = AeroplaneModel(
                name="partial_ctx",
                uuid=ap_uuid,
                total_mass_kg=2.0,
                assumption_computation_context={
                    "mass_kg": 2.0,
                    "s_ref_m2": 0.35,
                    "v_cruise_mps": 16.0,
                    # v_md_mps and v_min_sink_mps absent
                },
            )
            session.add(ap)
            session.commit()

        with in_memory_db() as session:
            resp = search_suitability(
                db=session, chord_m=0.15, speed_ms=15.0, aeroplane_id=str(ap_uuid)
            )
        assert resp.query.v_cruise_mps == pytest.approx(16.0)
        assert resp.query.v_md_mps is None
        assert resp.query.v_min_sink_mps is None

    def test_speed_fields_in_json_serialization(self, seeded_db_838):
        """Speed fields must be present in JSON output of SuitabilityResponse."""
        from app.services.suitability_service import search_suitability

        SessionLocal, ap_uuid = seeded_db_838
        with SessionLocal() as session:
            resp = search_suitability(
                db=session, chord_m=0.18, speed_ms=15.0, aeroplane_id=str(ap_uuid)
            )
        data = resp.model_dump()
        q = data["query"]
        assert "v_cruise_mps" in q
        assert "v_md_mps" in q
        assert "v_min_sink_mps" in q
        assert q["v_cruise_mps"] == pytest.approx(18.0)
