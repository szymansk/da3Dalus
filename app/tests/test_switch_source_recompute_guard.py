"""Guard test for the recompute-loop avoidance in switch_source.

The recompute service itself publishes AssumptionChanged(cg_x) when the
computed CG changes. If switch_source also scheduled a recompute for
cg_x, the loop would be:

  user toggles cg_x → switch_source → schedule_recompute → recompute
  writes cg_x.calculated_value → emits AssumptionChanged(cg_x) →
  handler schedules another recompute → …

This test pins the guard: switch_source must NOT schedule a recompute
when the parameter is "cg_x", but MUST schedule one for every other
non-design-choice parameter.
"""

from __future__ import annotations

from unittest.mock import patch

from app.schemas.design_assumption import AssumptionSourceSwitch
from app.services.design_assumptions_service import seed_defaults, switch_source, update_calculated_value
from app.tests.conftest import make_aeroplane


def test_switch_source_cg_x_does_not_schedule_recompute(client_and_db):
    """Toggling cg_x source must NOT trigger a recompute (loop guard)."""
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        # Give cg_x a calculated value so the switch is allowed.
        update_calculated_value(
            db, str(aeroplane.uuid), "cg_x", 0.085, "aerobuildup",
            auto_switch_source=False,
        )
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)

    with patch(
        "app.core.background_jobs.job_tracker.schedule_recompute_assumptions"
    ) as mock_schedule:
        with SessionLocal() as db:
            switch_source(
                db, aeroplane_uuid, "cg_x",
                AssumptionSourceSwitch(active_source="ESTIMATE"),
            )
            db.commit()

    mock_schedule.assert_not_called()


def test_switch_source_mass_schedules_recompute(client_and_db):
    """Sanity counter-test: non-cg_x params DO schedule recompute on toggle."""
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        update_calculated_value(
            db, str(aeroplane.uuid), "mass", 1.2, "weight_items",
            auto_switch_source=False,
        )
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)
        aeroplane_id = aeroplane.id

    with patch(
        "app.core.background_jobs.job_tracker.schedule_recompute_assumptions"
    ) as mock_schedule:
        with SessionLocal() as db:
            switch_source(
                db, aeroplane_uuid, "mass",
                AssumptionSourceSwitch(active_source="CALCULATED"),
            )
            db.commit()

    # switch_source schedules directly AND the AssumptionChanged(mass)
    # handler also schedules (mass is in RECOMPUTE_TRIGGERING_PARAMS).
    # We don't care about the exact count — just that it fires.
    assert mock_schedule.call_count >= 1
    for call in mock_schedule.call_args_list:
        assert call.args == (aeroplane_id,)
