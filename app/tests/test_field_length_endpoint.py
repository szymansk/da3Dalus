"""Endpoint tests for the field-length REST API (gh-489).

Covers the GET /aeroplanes/{id}/field-lengths endpoint:
- Happy path (runway/runway with seeded assumptions + context)
- 404 when aeroplane not found
- 422 when stall speed or s_ref not in context
- 422 when t_static_N is absent for runway mode
- Query parameters: landing_mode=belly_land, takeoff_mode=hand_launch
- Flap detection: wing with flap TED produces different (shorter) distances
"""

from __future__ import annotations

import uuid

import pytest

from app.models.aeroplanemodel import (
    AeroplaneModel,
    DesignAssumptionModel,
    WingModel,
    WingXSecDetailModel,
    WingXSecModel,
    WingXSecTrailingEdgeDeviceModel,
)
from app.tests.conftest import make_aeroplane


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_assumption(session, aeroplane_id: int, param_name: str, value: float):
    row = DesignAssumptionModel(
        aeroplane_id=aeroplane_id,
        parameter_name=param_name,
        estimate_value=value,
        active_source="ESTIMATE",
    )
    session.add(row)
    session.flush()


def _make_plane_with_context(session, *, t_static_N: float | None = 1900.0) -> AeroplaneModel:
    """Create an aeroplane with all required data for field-length computation.

    gh-548 (Phase 3): field-performance inputs (``t_static_N``, runway type,
    takeoff mode) now live on the MissionObjective, not design_assumptions.
    Mass and cl_max remain in the computation context.
    """
    from app.schemas.mission_objective import MissionObjective
    from app.services.mission_objective_service import upsert_mission_objective

    plane = make_aeroplane(session, name="field-len-test", total_mass_kg=1088.0)

    # Seed computation context (normally written by assumption_compute_service)
    plane.assumption_computation_context = {
        "mass_kg": 1088.0,
        "cl_max": 1.5,
        "v_stall_mps": 25.4,
        "s_ref_m2": 16.17,
        "v_cruise_mps": 55.0,
    }
    session.flush()

    # Seed MissionObjective (gh-548 source of truth for field-performance).
    upsert_mission_objective(
        session,
        plane.id,
        MissionObjective(
            mission_type="trainer",
            target_cruise_mps=18.0,
            target_stall_safety=1.8,
            target_maneuver_n=3.0,
            target_glide_ld=12.0,
            target_climb_energy=22.0,
            target_wing_loading_n_m2=412.0,
            target_field_length_m=50.0,
            available_runway_m=400.0,
            runway_type="grass",
            t_static_N=t_static_N if t_static_N is not None else 0.0,
            takeoff_mode="runway",
        ),
    )
    session.commit()
    return plane


# ===========================================================================
# Endpoint tests
# ===========================================================================


class TestFieldLengthEndpoint:
    def test_runway_returns_200_with_all_fields(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_plane_with_context(db)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(
            f"/aeroplanes/{aeroplane_uuid}/field-lengths",
            params={"takeoff_mode": "runway", "landing_mode": "runway"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        required = {
            "s_to_ground_m", "s_to_50ft_m",
            "s_ldg_ground_m", "s_ldg_50ft_m",
            "vto_obstacle_mps", "vapp_mps",
            "mode_takeoff", "mode_landing",
            "warnings",
        }
        assert not (required - data.keys())
        assert data["mode_takeoff"] == "runway"
        assert data["mode_landing"] == "runway"
        assert data["s_to_ground_m"] > 0
        assert data["s_ldg_ground_m"] > 0

    def test_404_when_aeroplane_not_found(self, client_and_db):
        client, _ = client_and_db
        missing_uuid = str(uuid.uuid4())
        resp = client.get(f"/aeroplanes/{missing_uuid}/field-lengths")
        assert resp.status_code == 404

    def test_422_when_t_static_missing_for_runway(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            # No t_static_N seeded
            plane = _make_plane_with_context(db, t_static_N=None)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(
            f"/aeroplanes/{aeroplane_uuid}/field-lengths",
            params={"takeoff_mode": "runway"},
        )
        assert resp.status_code == 422

    def test_422_when_stall_speed_missing_from_context(self, client_and_db):
        from app.schemas.mission_objective import MissionObjective
        from app.services.mission_objective_service import upsert_mission_objective

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db, name="no-context", total_mass_kg=1088.0)
            upsert_mission_objective(
                db,
                plane.id,
                MissionObjective(
                    mission_type="trainer",
                    target_cruise_mps=18.0, target_stall_safety=1.8,
                    target_maneuver_n=3.0, target_glide_ld=12.0,
                    target_climb_energy=22.0, target_wing_loading_n_m2=412.0,
                    target_field_length_m=50.0, available_runway_m=400.0,
                    runway_type="grass", t_static_N=1900.0, takeoff_mode="runway",
                ),
            )
            # No assumption_computation_context
            plane.assumption_computation_context = None
            db.flush()
            db.commit()
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/field-lengths")
        assert resp.status_code == 422

    def test_belly_land_returns_shorter_distance(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_plane_with_context(db)
            aeroplane_uuid = str(plane.uuid)

        r_runway = client.get(
            f"/aeroplanes/{aeroplane_uuid}/field-lengths",
            params={"landing_mode": "runway"},
        )
        r_belly = client.get(
            f"/aeroplanes/{aeroplane_uuid}/field-lengths",
            params={"landing_mode": "belly_land"},
        )
        assert r_runway.status_code == 200
        assert r_belly.status_code == 200
        assert r_belly.json()["s_ldg_ground_m"] < r_runway.json()["s_ldg_ground_m"]

    def test_hand_launch_returns_zero_ground_roll(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_plane_with_context(db)
            aeroplane_uuid = str(plane.uuid)

        v_stall = 25.4
        v_throw = 1.25 * v_stall  # above both 1.10 and 1.20 floors
        resp = client.get(
            f"/aeroplanes/{aeroplane_uuid}/field-lengths",
            params={"takeoff_mode": "hand_launch", "v_throw_mps": v_throw},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["s_to_ground_m"] == pytest.approx(0.0)
        assert data["s_to_50ft_m"] == pytest.approx(0.0)

    def test_default_mode_is_runway(self, client_and_db):
        """Calling without mode params defaults to runway/runway."""
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_plane_with_context(db)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/field-lengths")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode_takeoff"] == "runway"
        assert data["mode_landing"] == "runway"

    def test_flap_ted_produces_shorter_field_lengths(self, client_and_db):
        """Wing with a flap TED (role='flap') → shorter s_TO and s_LDG than no-flap.

        With a flap, CL_max_TO is boosted by 1.1× and CL_max_LDG by 1.3×,
        resulting in shorter ground rolls (higher CL_max → lower required speed
        → shorter distance).
        """
        client, SessionLocal = client_and_db

        # Aeroplane WITHOUT flap
        with SessionLocal() as db:
            plane_clean = _make_plane_with_context(db, t_static_N=1900.0)
            uuid_clean = str(plane_clean.uuid)

        # Aeroplane WITH flap TED
        with SessionLocal() as db:
            plane_flap = _make_plane_with_context(db, t_static_N=1900.0)

            # Add a main wing with a flap TED
            wing = WingModel(name="main_wing", symmetric=True, aeroplane_id=plane_flap.id)
            db.add(wing)
            db.flush()

            xsec = WingXSecModel(
                wing_id=wing.id,
                xyz_le=[0.0, 0.0, 0.0],
                chord=0.3,
                twist=0.0,
                airfoil="naca2412",
                sort_index=0,
            )
            db.add(xsec)
            db.flush()

            detail = WingXSecDetailModel(wing_xsec_id=xsec.id, x_sec_type="segment")
            db.add(detail)
            db.flush()

            ted = WingXSecTrailingEdgeDeviceModel(
                wing_xsec_detail_id=detail.id,
                name="Flap",
                role="flap",
                rel_chord_root=0.7,
                rel_chord_tip=0.7,
                symmetric=True,
            )
            db.add(ted)
            db.commit()
            uuid_flap = str(plane_flap.uuid)

        r_clean = client.get(
            f"/aeroplanes/{uuid_clean}/field-lengths",
            params={"takeoff_mode": "runway", "landing_mode": "runway"},
        )
        r_flap = client.get(
            f"/aeroplanes/{uuid_flap}/field-lengths",
            params={"takeoff_mode": "runway", "landing_mode": "runway"},
        )

        assert r_clean.status_code == 200, r_clean.text
        assert r_flap.status_code == 200, r_flap.text

        clean_data = r_clean.json()
        flap_data = r_flap.json()

        # With flap, CL_max is higher → both takeoff and landing distances shorter
        assert flap_data["s_to_ground_m"] < clean_data["s_to_ground_m"], (
            f"Expected flap TO ({flap_data['s_to_ground_m']:.1f} m) "
            f"< clean TO ({clean_data['s_to_ground_m']:.1f} m)"
        )
        assert flap_data["s_ldg_ground_m"] < clean_data["s_ldg_ground_m"], (
            f"Expected flap LDG ({flap_data['s_ldg_ground_m']:.1f} m) "
            f"< clean LDG ({clean_data['s_ldg_ground_m']:.1f} m)"
        )
