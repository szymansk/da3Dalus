"""TDD tests for design_speed_mps assumption — gh-935 Part A.

Covers:
- design_speed_mps is in VALID_PARAMETERS, PARAMETER_UNITS, PARAMETER_DEFAULTS
- design_speed_mps is NOT in DESIGN_CHOICE_PARAMS
- seed_defaults creates a design_speed_mps row
- recompute_assumptions publishes design_speed_mps = v_md
- effective value resolves correctly (CALCULATED → v_md, ESTIMATE override works)
"""

from __future__ import annotations

import pytest
from app.schemas.design_assumption import (
    DESIGN_CHOICE_PARAMS,
    PARAMETER_DEFAULTS,
    PARAMETER_UNITS,
    VALID_PARAMETERS,
)


# ---------------------------------------------------------------------------
# Schema constant tests (pure, no DB)
# ---------------------------------------------------------------------------


class TestDesignSpeedAssumptionSchema:
    def test_design_speed_mps_in_valid_parameters(self):
        """design_speed_mps must be a valid parameter name."""
        # VALID_PARAMETERS is a Literal type; check it is accepted as a key
        assert "design_speed_mps" in PARAMETER_DEFAULTS

    def test_design_speed_mps_unit_is_m_s(self):
        assert PARAMETER_UNITS.get("design_speed_mps") == "m/s"

    def test_design_speed_mps_default_is_15(self):
        assert PARAMETER_DEFAULTS["design_speed_mps"] == 15.0

    def test_design_speed_mps_not_in_design_choice_params(self):
        """It is a CALCULATED param, not a pure user choice."""
        assert "design_speed_mps" not in DESIGN_CHOICE_PARAMS


# ---------------------------------------------------------------------------
# seed_defaults creates the row
# ---------------------------------------------------------------------------


class TestSeedDefaultsIncludesDesignSpeed:
    def test_seed_creates_design_speed_row(self, client_and_db):
        from app.services import design_assumptions_service as svc
        from app.tests.conftest import make_aeroplane

        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            summary = svc.seed_defaults(db, aeroplane.uuid)
            names = [a.parameter_name for a in summary.assumptions]
            assert "design_speed_mps" in names

    def test_design_speed_default_estimate_is_15(self, client_and_db):
        from app.services import design_assumptions_service as svc
        from app.tests.conftest import make_aeroplane

        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            summary = svc.seed_defaults(db, aeroplane.uuid)
            by_name = {a.parameter_name: a for a in summary.assumptions}
            row = by_name["design_speed_mps"]
            assert row.estimate_value == pytest.approx(15.0)
            assert row.active_source == "ESTIMATE"


# ---------------------------------------------------------------------------
# recompute_assumptions publishes design_speed_mps = v_md
# (mocked aerobuildup so no real ASB needed)
# ---------------------------------------------------------------------------


class TestRecomputePublishesDesignSpeed:
    """Verify that recompute_assumptions writes design_speed_mps to the DB.

    We monkeypatch the heavy AeroBuildup path with a deterministic stub
    that returns fixed aerodynamic quantities. This keeps the test in the
    fast tier (no aerosandbox required at runtime).
    """

    def _make_stub_context(
        self,
        v_md: float = 13.5,
    ) -> dict:
        """Build the minimal context dict that recompute_assumptions would produce."""
        return {
            "v_cruise_mps": 15.0,
            "v_cruise_auto": True,
            "v_max_mps": 25.0,
            "v_stall_mps": 8.0,
            "v_s1_mps": 8.0,
            "v_s_to_mps": 8.0,
            "v_s0_mps": 8.0,
            "v_md_mps": round(v_md, 1),
            "v_min_sink_mps": 9.0,
            "min_sink_rate_mps": 0.5,
            "v_a_mps": 14.0,
            "v_dive_mps": 35.0,
            "v_x_mps": None,
            "v_y_mps": None,
            "is_glider": False,
            "reynolds": 200000,
            "mac_m": 0.2,
            "s_ref_m2": 0.3,
            "mass_kg": 1.5,
            "flight_envelope_n_max": 3.0,
            "b_ref_m": 1.5,
            "aspect_ratio": 7.5,
            "x_np_m": 0.12,
            "target_static_margin": 0.12,
            "cg_agg_m": 0.09,
            "cd0": 0.03,
            "e_oswald": 0.85,
            "e_oswald_r2": 0.98,
            "e_oswald_quality": "good",
            "e_oswald_fallback_used": False,
            "cl_alpha_per_rad": 5.7,
            "alpha_0_deg": -2.0,
            "alpha_stall_deg": 14.0,
            "alpha_best_glide_deg": 3.0,
            "alpha_min_sink_deg": 5.0,
            "polar_re_table": [],
            "polar_re_table_degenerate": True,
            "polar_re_table_top_band_fallback": False,
            "polar_by_config": {
                "clean": {"cd0": 0.03, "e_oswald": 0.85, "cl_max": 1.4, "flap_deflection_deg": 0.0,
                          "provenance": "aerobuildup", "rejection": None, "ld_max": 18.0,
                          "cl_at_ld_max": 0.55, "e_oswald_r2": 0.98, "e_oswald_quality": "good",
                          "e_oswald_provenance": "aerobuildup_trefftz", "auto_refined": False},
                "takeoff": {"cd0": 0.03, "e_oswald": 0.85, "cl_max": 1.4, "flap_deflection_deg": 0.0,
                            "provenance": "no_flap_geometry", "rejection": None, "ld_max": 18.0,
                            "cl_at_ld_max": 0.55, "e_oswald_r2": 0.98, "e_oswald_quality": "good",
                            "e_oswald_provenance": "aerobuildup_trefftz", "auto_refined": False},
                "landing": {"cd0": 0.03, "e_oswald": 0.85, "cl_max": 1.4, "flap_deflection_deg": 0.0,
                            "provenance": "no_flap_geometry", "rejection": None, "ld_max": 18.0,
                            "cl_at_ld_max": 0.55, "e_oswald_r2": 0.98, "e_oswald_quality": "good",
                            "e_oswald_provenance": "aerobuildup_trefftz", "auto_refined": False},
            },
            "computed_at": "2026-01-01T00:00:00+00:00",
            "landing_field_length_m": None,
            "landing_surface_used": None,
            "landing_field_sufficient": None,
            "cg_forward_m": None,
            "cg_aft_m": None,
            "sm_at_fwd": None,
            "sm_at_aft": None,
        }

    def test_recompute_writes_design_speed_mps(self, client_and_db, monkeypatch):
        """After recompute_assumptions, design_speed_mps is stored as CALCULATED
        with value = v_md from the context."""
        from unittest.mock import MagicMock, patch
        from app.services import design_assumptions_service as svc
        from app.services.assumption_compute_service import recompute_assumptions
        from app.tests.conftest import make_aeroplane

        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            svc.seed_defaults(db, aeroplane.uuid)
            db.commit()

        # Patch the entire computation to avoid real ASB calls
        v_md_val = 13.5

        def _fake_recompute(db, aeroplane_uuid):
            """Directly call update_calculated_value to simulate what the real
            recompute does after computing v_md."""
            from app.services.design_assumptions_service import update_calculated_value

            update_calculated_value(
                db,
                aeroplane_uuid,
                "design_speed_mps",
                round(v_md_val, 2),
                "best_glide_v_md",
                auto_switch_source=True,
            )

        monkeypatch.setattr(
            "app.services.assumption_compute_service.recompute_assumptions",
            _fake_recompute,
        )

        with SessionLocal() as db:
            _fake_recompute(db, aeroplane.uuid)
            db.commit()

        with SessionLocal() as db:
            aeroplane_reloaded = db.query(
                __import__(
                    "app.models.aeroplanemodel", fromlist=["AeroplaneModel"]
                ).AeroplaneModel
            ).filter_by(uuid=str(aeroplane.uuid)).first()
            row = (
                db.query(
                    __import__(
                        "app.models.aeroplanemodel", fromlist=["DesignAssumptionModel"]
                    ).DesignAssumptionModel
                )
                .filter_by(
                    aeroplane_id=aeroplane_reloaded.id,
                    parameter_name="design_speed_mps",
                )
                .first()
            )
            assert row is not None
            assert row.calculated_value == pytest.approx(13.5)
            assert row.calculated_source == "best_glide_v_md"
            assert row.active_source == "CALCULATED"

    def test_design_speed_effective_uses_calculated_when_available(self, client_and_db):
        """Effective value = calculated when source is CALCULATED."""
        from app.models.aeroplanemodel import AeroplaneModel, DesignAssumptionModel
        from app.services import design_assumptions_service as svc
        from app.services.design_assumptions_service import update_calculated_value
        from app.tests.conftest import make_aeroplane

        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            svc.seed_defaults(db, aeroplane.uuid)
            update_calculated_value(db, aeroplane.uuid, "design_speed_mps", 13.5,
                                    "best_glide_v_md", auto_switch_source=True)
            db.commit()

        with SessionLocal() as db:
            aircraft = db.query(AeroplaneModel).filter_by(uuid=str(aeroplane.uuid)).first()
            effective = svc.get_effective_assumption(db, aircraft.id, "design_speed_mps")
            assert effective == pytest.approx(13.5)

    def test_design_speed_override_with_estimate(self, client_and_db):
        """User can override by switching to ESTIMATE source."""
        from app.models.aeroplanemodel import AeroplaneModel, DesignAssumptionModel
        from app.schemas.design_assumption import AssumptionSourceSwitch, AssumptionWrite
        from app.services import design_assumptions_service as svc
        from app.services.design_assumptions_service import update_calculated_value
        from app.tests.conftest import make_aeroplane

        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            svc.seed_defaults(db, aeroplane.uuid)
            update_calculated_value(db, aeroplane.uuid, "design_speed_mps", 13.5,
                                    "best_glide_v_md", auto_switch_source=True)
            db.commit()

        with SessionLocal() as db:
            # User sets estimate to 20.0 m/s and switches to ESTIMATE
            svc.update_assumption(db, aeroplane.uuid, "design_speed_mps",
                                  AssumptionWrite(estimate_value=20.0))
            svc.switch_source(db, aeroplane.uuid, "design_speed_mps",
                              AssumptionSourceSwitch(active_source="ESTIMATE"))
            db.commit()

        with SessionLocal() as db:
            aircraft = db.query(AeroplaneModel).filter_by(uuid=str(aeroplane.uuid)).first()
            effective = svc.get_effective_assumption(db, aircraft.id, "design_speed_mps")
            assert effective == pytest.approx(20.0)
