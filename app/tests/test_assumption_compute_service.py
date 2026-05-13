"""Tests for the assumption compute service (Task 5 of gh-465).

All AeroSandbox-bound helpers are stubbed so tests run without ASB installed.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from app.models.aeroplanemodel import DesignAssumptionModel
from app.services.assumption_compute_service import recompute_assumptions
from app.services.design_assumptions_service import seed_defaults
from app.tests.conftest import make_aeroplane


def _make_fake_airplane():
    """Stub for asb_airplane: a wing with .area/.mean_aerodynamic_chord/.span()
    so _select_main_wing + the s_ref/c_ref/b_ref override don't blow up."""
    fake_wing = SimpleNamespace(
        area=lambda: 0.30,
        mean_aerodynamic_chord=lambda: 0.20,
        span=lambda: 1.5,
    )
    return SimpleNamespace(
        wings=[fake_wing],
        xyz_ref=[0.08, 0.0, 0.0],
        s_ref=0.30,
        c_ref=0.20,
        b_ref=1.5,
    )


def _patches():
    """Stub the three ASB-bound helpers so tests don't need real ASB."""
    return (
        patch(
            "app.services.assumption_compute_service._build_asb_airplane",
            return_value=_make_fake_airplane(),
        ),
        patch(
            "app.services.assumption_compute_service._stability_run_at_cruise",
            return_value=(0.085, 0.20, 0.025, 0.30),  # x_np, MAC, CD0
        ),
        patch(
            "app.services.assumption_compute_service._coarse_alpha_sweep",
            return_value=15.0,  # stall_alpha_deg
        ),
        patch(
            "app.services.assumption_compute_service._fine_sweep_cl_max",
            # Now returns (cl_max, cl_array, cd_array) — gh-486
            return_value=(1.35, np.array([0.2, 0.4, 0.6, 0.8, 1.0, 1.2]), np.array([0.026, 0.028, 0.032, 0.039, 0.049, 0.062])),
        ),
        patch(
            "app.services.assumption_compute_service._load_flight_profile_speeds",
            return_value=(18.0, 28.0, True),
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


def test_recompute_aborts_cleanly_on_asb_exception(client_and_db):
    """ASB failure must NOT corrupt existing calculated_value fields and
    must NOT publish AssumptionChanged. This guards a critical loop in
    recompute_assumptions: any exception inside the sweep helpers is
    caught and the function returns without writing anything."""
    from app.core.events import AssumptionChanged, event_bus

    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        # Pre-seed known calculated values that must survive untouched.
        cd0_row = (
            db.query(DesignAssumptionModel)
            .filter_by(aeroplane_id=aeroplane.id, parameter_name="cd0")
            .first()
        )
        cd0_row.calculated_value = 0.9999
        cd0_row.calculated_source = "previous_run"
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)

    captured: list = []
    handler = captured.append
    event_bus.subscribe(AssumptionChanged, handler)

    try:
        with (
            patch(
                "app.services.assumption_compute_service._build_asb_airplane",
                return_value=SimpleNamespace(
                    wings=[
                        SimpleNamespace(
                            area=lambda: 0.30,
                            mean_aerodynamic_chord=lambda: 0.20,
                            span=lambda: 1.5,
                        )
                    ],
                    xyz_ref=[0.0, 0.0, 0.0],
                    s_ref=0.30,
                    c_ref=0.20,
                    b_ref=1.5,
                ),
            ),
            patch(
                "app.services.assumption_compute_service._stability_run_at_cruise",
                side_effect=RuntimeError("ASB boom"),
            ),
            patch(
                "app.services.assumption_compute_service._load_flight_profile_speeds",
                return_value=(18.0, 28.0, True),
            ),
        ):
            with SessionLocal() as db:
                recompute_assumptions(db, aeroplane_uuid)
                db.commit()
    finally:
        event_bus._subscribers.get(AssumptionChanged, []).remove(handler)

    # Pre-existing value survives.
    with SessionLocal() as db:
        cd0_row = (
            db.query(DesignAssumptionModel)
            .filter_by(parameter_name="cd0")
            .first()
        )
        assert cd0_row.calculated_value == 0.9999
        assert cd0_row.calculated_source == "previous_run"

    # No spurious cg_x change event.
    assert [e.parameter_name for e in captured] == []


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
