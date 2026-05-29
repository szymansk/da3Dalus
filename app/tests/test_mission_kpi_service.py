"""Unit tests for mission_kpi_service (gh-547).

Phase 2 Task 2.1: per-axis closed-form KPI calculators built on top of
the cached ``assumption_computation_context`` payload of an aeroplane.

The aggregator + endpoint tests (Task 2.2 / 2.3) live below the
per-axis tests once those calculators exist.
"""

from __future__ import annotations

import math
from unittest.mock import patch

import pytest

from app.models.aeroplanemodel import AeroplaneModel
from app.core.exceptions import ServiceException
from app.services.mission_kpi_service import (
    _compute_field_length_score,
    _kpi_climb_energy,
    _kpi_cruise,
    _kpi_field_friendliness,
    _kpi_glide,
    _kpi_maneuver,
    _kpi_stall_safety,
    _kpi_wing_loading,
    _normalise_score,
    compute_mission_kpis,
)
from app.tests.conftest import make_aeroplane


def test_normalise_clips_outside_range():
    assert _normalise_score(5.0, 0.0, 10.0) == 0.5
    assert _normalise_score(15.0, 0.0, 10.0) == 1.0
    assert _normalise_score(-3.0, 0.0, 10.0) == 0.0


def test_normalise_degenerate_range_returns_zero():
    assert _normalise_score(5.0, 10.0, 10.0) == 0.0
    assert _normalise_score(5.0, 10.0, 5.0) == 0.0


def test_kpi_stall_safety_from_context():
    ctx = {"v_cruise_mps": 18.0, "v_s1_mps": 12.0}
    kpi = _kpi_stall_safety(ctx, range_min=1.3, range_max=2.5)
    assert kpi.value == pytest.approx(1.5)
    assert kpi.score_0_1 == pytest.approx((1.5 - 1.3) / (2.5 - 1.3))
    assert kpi.provenance == "computed"
    assert kpi.unit == "-"


def test_kpi_stall_safety_missing_when_v_s1_absent():
    ctx = {"v_cruise_mps": 18.0}
    kpi = _kpi_stall_safety(ctx, range_min=1.3, range_max=2.5)
    assert kpi.value is None
    assert kpi.score_0_1 is None
    assert kpi.provenance == "missing"


def test_kpi_stall_safety_missing_when_v_cruise_absent():
    ctx = {"v_s1_mps": 12.0}
    kpi = _kpi_stall_safety(ctx, range_min=1.3, range_max=2.5)
    assert kpi.provenance == "missing"


def test_kpi_glide_from_polar_by_config():
    ctx = {
        "aspect_ratio": 8.0,
        "polar_by_config": {
            "clean": {"cd0": 0.025, "e_oswald": 0.80, "cl_max": 1.4},
        },
    }
    kpi = _kpi_glide(ctx, range_min=5.0, range_max=18.0)
    # (L/D)_max = 0.5 * sqrt(pi * e * AR / CD0)
    expected = 0.5 * math.sqrt(math.pi * 0.80 * 8.0 / 0.025)
    assert kpi.value == pytest.approx(expected, rel=1e-3)
    assert kpi.provenance == "computed"


def test_kpi_glide_missing_when_polar_absent():
    ctx = {"aspect_ratio": 8.0}
    kpi = _kpi_glide(ctx, range_min=5.0, range_max=18.0)
    assert kpi.provenance == "missing"


def test_kpi_glide_missing_when_cd0_zero():
    ctx = {
        "aspect_ratio": 8.0,
        "polar_by_config": {"clean": {"cd0": 0.0, "e_oswald": 0.8}},
    }
    kpi = _kpi_glide(ctx, range_min=5.0, range_max=18.0)
    assert kpi.provenance == "missing"


def test_kpi_climb_energy_from_polar():
    ctx = {
        "aspect_ratio": 8.0,
        "polar_by_config": {
            "clean": {"cd0": 0.025, "e_oswald": 0.80, "cl_max": 1.4},
        },
    }
    kpi = _kpi_climb_energy(ctx, range_min=10.0, range_max=60.0)
    # Closed-form: (C_L^1.5 / C_D)_max = (3·π·e·AR)^0.75 / (4 · C_D0^0.25)
    # Hand-check: e=0.80, AR=8, C_D0=0.025 -> ~13.61
    expected = (3.0 * math.pi * 0.80 * 8.0) ** 0.75 / (4.0 * 0.025**0.25)
    assert kpi.value == pytest.approx(expected, rel=1e-3)
    assert kpi.provenance == "computed"


def test_kpi_climb_energy_missing_when_no_polar():
    ctx = {"aspect_ratio": 8.0}
    kpi = _kpi_climb_energy(ctx, range_min=5.0, range_max=25.0)
    assert kpi.provenance == "missing"


# gh-681: when the parabolic-fit was rejected, polar_by_config.clean.cd0 is
# None but top-level ctx['cd0'] (stability run) and ctx['e_oswald'] (gh-636
# AB-Trefftz) are still valid. Both KPIs must fall back to those instead of
# returning missing.


def test_kpi_glide_falls_back_to_top_level_cd0_when_fit_rejected():
    """gh-681: rejected fit ⇒ polar.cd0=None; use ctx['cd0'] + ctx['e_oswald']."""
    ctx = {
        "aspect_ratio": 18.71,
        "cd0": 0.0159,
        "e_oswald": 0.808,
        "polar_by_config": {
            "clean": {
                "cd0": None,
                "e_oswald": 0.808,
                "cl_max": 1.12,
                "rejection": {
                    "gate": "non_monotonic_polar",
                    "category": "data",
                    "fitted_value": -0.15,
                    "threshold": "dCD/d(CL²) >= 0",
                    "hint": "laminar bubble",
                },
            },
        },
    }
    kpi = _kpi_glide(ctx, range_min=15.0, range_max=35.0)
    expected = 0.5 * math.sqrt(math.pi * 0.808 * 18.71 / 0.0159)
    assert kpi.provenance == "computed"
    assert kpi.value == pytest.approx(expected, rel=1e-3)


def test_kpi_glide_prefers_empirical_ld_max():
    """gh-681: when polar.ld_max is set, prefer it over the formula."""
    ctx = {
        "aspect_ratio": 18.71,
        "cd0": 0.0159,
        "e_oswald": 0.808,
        "polar_by_config": {
            "clean": {
                "cd0": None,
                "e_oswald": 0.808,
                "cl_max": 1.12,
                "ld_max": 30.52,  # empirical, gh-636
            },
        },
    }
    kpi = _kpi_glide(ctx, range_min=15.0, range_max=35.0)
    assert kpi.provenance == "computed"
    # Empirical 30.52 should win over formula (~30.7) — small difference
    # but exercised path is what matters; assert the empirical value.
    assert kpi.value == pytest.approx(30.52, rel=1e-3)


def test_kpi_climb_energy_falls_back_to_top_level_when_fit_rejected():
    """gh-681: rejected fit ⇒ polar.cd0=None; use ctx['cd0'] + ctx['e_oswald']."""
    ctx = {
        "aspect_ratio": 18.71,
        "cd0": 0.0159,
        "e_oswald": 0.808,
        "polar_by_config": {
            "clean": {
                "cd0": None,
                "e_oswald": 0.808,
                "cl_max": 1.12,
            },
        },
    }
    kpi = _kpi_climb_energy(ctx, range_min=15.0, range_max=60.0)
    expected = (3.0 * math.pi * 0.808 * 18.71) ** 0.75 / (4.0 * 0.0159**0.25)
    assert kpi.provenance == "computed"
    assert kpi.value == pytest.approx(expected, rel=1e-3)


def test_kpi_glide_missing_when_ar_none_even_with_fallback():
    """Fallback only fires when AR is present and at least one cd0 source exists."""
    ctx = {
        "aspect_ratio": None,
        "cd0": 0.0159,
        "e_oswald": 0.808,
        "polar_by_config": {"clean": {"cd0": None, "e_oswald": 0.808, "cl_max": 1.12}},
    }
    kpi = _kpi_glide(ctx, range_min=15.0, range_max=35.0)
    assert kpi.provenance == "missing"


def test_kpi_cruise_from_context():
    ctx = {"v_cruise_mps": 22.0}
    kpi = _kpi_cruise(ctx, range_min=10.0, range_max=25.0)
    assert kpi.value == pytest.approx(22.0)
    assert kpi.unit == "m/s"
    assert kpi.score_0_1 == pytest.approx((22.0 - 10.0) / (25.0 - 10.0))
    assert kpi.provenance == "computed"


def test_kpi_cruise_missing():
    kpi = _kpi_cruise({}, range_min=10.0, range_max=25.0)
    assert kpi.provenance == "missing"


def test_kpi_maneuver_from_context():
    ctx = {"flight_envelope_n_max": 4.5}
    kpi = _kpi_maneuver(ctx, range_min=2.0, range_max=5.0)
    assert kpi.value == pytest.approx(4.5)
    assert kpi.unit == "g"
    assert kpi.provenance == "computed"


def test_kpi_maneuver_missing():
    kpi = _kpi_maneuver({}, range_min=2.0, range_max=5.0)
    assert kpi.provenance == "missing"


def test_kpi_wing_loading_from_mass_and_sref():
    ctx = {"s_ref_m2": 0.30}
    kpi = _kpi_wing_loading(ctx, mass_kg=2.0, range_min=20.0, range_max=80.0)
    expected = 2.0 * 9.81 / 0.30
    assert kpi.value == pytest.approx(expected)
    assert kpi.unit == "N/m²"
    assert kpi.provenance == "computed"


def test_kpi_wing_loading_missing_when_no_mass():
    ctx = {"s_ref_m2": 0.30}
    kpi = _kpi_wing_loading(ctx, mass_kg=None, range_min=20.0, range_max=80.0)
    assert kpi.provenance == "missing"


def test_kpi_wing_loading_missing_when_no_sref():
    kpi = _kpi_wing_loading({}, mass_kg=2.0, range_min=20.0, range_max=80.0)
    assert kpi.provenance == "missing"


# ----- Aggregator -----------------------------------------------------------


_SYNTHETIC_CONTEXT: dict = {
    "v_cruise_mps": 18.0,
    "v_s1_mps": 12.0,
    "aspect_ratio": 8.0,
    "s_ref_m2": 0.30,
    "mass_kg": 2.0,
    "polar_by_config": {
        "clean": {"cd0": 0.025, "e_oswald": 0.80, "cl_max": 1.4},
        "takeoff": {"cd0": 0.040, "e_oswald": 0.75, "cl_max": 1.7},
        "landing": {"cd0": 0.060, "e_oswald": 0.70, "cl_max": 2.0},
    },
    "flight_envelope_n_max": 3.0,
}


def _seed_context(SessionLocal, aeroplane_id: int, ctx: dict | None = None) -> None:
    """Inject a synthetic ComputationContext into the aeroplane row."""
    with SessionLocal() as db:
        row = db.query(AeroplaneModel).filter_by(id=aeroplane_id).one()
        row.assumption_computation_context = ctx if ctx is not None else dict(_SYNTHETIC_CONTEXT)
        db.commit()


def test_compute_mission_kpis_full_payload(client_and_db):
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db, total_mass_kg=2.0)
        aircraft_id = aeroplane.id
        aeroplane_uuid = str(aeroplane.uuid)

    _seed_context(SessionLocal, aircraft_id)

    with patch(
        "app.services.mission_kpi_service._compute_field_length_score",
        return_value=(45.0, 1.0, None),
    ):
        with SessionLocal() as db:
            kset = compute_mission_kpis(db, aircraft_id, ["trainer"])

    # All 7 axes present in ist polygon
    assert set(kset.ist_polygon.keys()) == {
        "stall_safety",
        "glide",
        "climb",
        "cruise",
        "maneuver",
        "wing_loading",
        "field_friendliness",
    }
    # Field-friendliness wired through the patched score
    field = kset.ist_polygon["field_friendliness"]
    assert field.value == pytest.approx(45.0)
    assert field.score_0_1 == pytest.approx(1.0)
    assert field.provenance == "computed"

    # Trainer target polygon present
    assert kset.target_polygons[0].mission_id == "trainer"
    assert kset.active_mission_id == "trainer"
    assert kset.aeroplane_uuid == aeroplane_uuid
    assert len(kset.context_hash) == 64


def test_compute_mission_kpis_multi_mission_overlay(client_and_db):
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db, total_mass_kg=2.0)
        aircraft_id = aeroplane.id

    _seed_context(SessionLocal, aircraft_id)

    with patch(
        "app.services.mission_kpi_service._compute_field_length_score",
        return_value=(45.0, 1.0, None),
    ):
        with SessionLocal() as db:
            kset = compute_mission_kpis(db, aircraft_id, ["trainer", "sailplane"])

    assert {p.mission_id for p in kset.target_polygons} == {"trainer", "sailplane"}
    # First entry of active_mission_ids drives `active_mission_id`
    assert kset.active_mission_id == "trainer"


def test_compute_mission_kpis_defaults_to_objective_mission_when_empty(client_and_db):
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db, total_mass_kg=2.0)
        aircraft_id = aeroplane.id

    _seed_context(SessionLocal, aircraft_id)

    with patch(
        "app.services.mission_kpi_service._compute_field_length_score",
        return_value=(45.0, 1.0, None),
    ):
        with SessionLocal() as db:
            kset = compute_mission_kpis(db, aircraft_id, [])

    # Default MissionObjective.mission_type == "trainer"
    assert kset.active_mission_id == "trainer"
    assert {p.mission_id for p in kset.target_polygons} == {"trainer"}


def test_compute_mission_kpis_skips_unknown_mission_ids(client_and_db):
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db, total_mass_kg=2.0)
        aircraft_id = aeroplane.id

    _seed_context(SessionLocal, aircraft_id)

    with patch(
        "app.services.mission_kpi_service._compute_field_length_score",
        return_value=(45.0, 1.0, None),
    ):
        with SessionLocal() as db:
            kset = compute_mission_kpis(db, aircraft_id, ["trainer", "nonexistent_preset"])

    # Unknown id silently dropped, known one survives
    assert {p.mission_id for p in kset.target_polygons} == {"trainer"}


def test_compute_mission_kpis_missing_context_marks_axes_missing(client_and_db):
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        aircraft_id = aeroplane.id

    # No context seeded — aeroplane.assumption_computation_context is None/empty
    with patch(
        "app.services.mission_kpi_service._compute_field_length_score",
        return_value=(None, None, None),
    ):
        with SessionLocal() as db:
            kset = compute_mission_kpis(db, aircraft_id, ["trainer"])

    # Every axis comes back missing because nothing was seeded
    for axis_name, kpi in kset.ist_polygon.items():
        assert kpi.provenance == "missing", f"{axis_name} should be missing"
        assert kpi.value is None
        assert kpi.score_0_1 is None


def test_compute_mission_kpis_field_friendliness_computed_after_phase3(client_and_db):
    """gh-548 Phase 3: with a real MissionObjective + complete context,
    field_friendliness now reports provenance='computed' (instead of the
    pre-Phase-3 'missing' fallback).
    """
    from app.schemas.mission_objective import MissionObjective
    from app.services.mission_objective_service import upsert_mission_objective

    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db, total_mass_kg=2.0)
        aircraft_id = aeroplane.id

    # Seed a context that includes v_stall_mps so the real
    # compute_field_lengths can run.
    full_ctx = dict(_SYNTHETIC_CONTEXT)
    full_ctx["v_stall_mps"] = 8.0
    _seed_context(SessionLocal, aircraft_id, full_ctx)

    with SessionLocal() as db:
        upsert_mission_objective(
            db,
            aircraft_id,
            MissionObjective(
                mission_type="trainer",
                target_cruise_mps=18.0,
                target_stall_safety=1.8,
                target_maneuver_n=3.0,
                target_glide_ld=12.0,
                target_climb_energy=22.0,
                target_wing_loading_n_m2=412.0,
                target_field_length_m=50.0,
                available_runway_m=80.0,
                runway_type="grass",
                t_static_N=20.0,
                takeoff_mode="runway",
            ),
        )
        db.commit()

    with SessionLocal() as db:
        kset = compute_mission_kpis(db, aircraft_id, ["trainer"])

    field = kset.ist_polygon["field_friendliness"]
    assert field.provenance == "computed", (
        f"Expected 'computed' after Phase 3 wiring, got {field.provenance!r}"
    )
    assert field.value is not None and field.value > 0
    assert field.score_0_1 is not None


def test_compute_mission_kpis_field_friendliness_falls_back_gracefully(client_and_db):
    """When the field-length service is unavailable on the platform (e.g.
    aerosandbox can't be imported on linux/aarch64), the axis is "missing"
    with a user-facing warning instead of crashing the whole radar payload.
    """
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db, total_mass_kg=2.0)
        aircraft_id = aeroplane.id

    _seed_context(SessionLocal, aircraft_id)

    # Simulate platform-level "service unavailable" by patching the
    # module-level reference to None — same code path as the module-load
    # ImportError fallback.
    with patch(
        "app.services.mission_kpi_service.compute_field_lengths_for_aeroplane",
        None,
    ):
        with SessionLocal() as db:
            kset = compute_mission_kpis(db, aircraft_id, ["trainer"])

    field = kset.ist_polygon["field_friendliness"]
    assert field.provenance == "missing"
    assert field.value is None
    assert field.warning is not None and "unavailable" in field.warning.lower()


def test_compute_mission_kpis_raises_when_presets_table_empty(client_and_db):
    """Empty mission_presets table surfaces as a 500, not an empty radar payload."""
    from app.models.mission_preset import MissionPresetModel

    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        db.commit()
        aircraft_id = aeroplane.id
        # Wipe presets to simulate a broken deployment (missing Alembic seed).
        db.query(MissionPresetModel).delete()
        db.commit()

    with SessionLocal() as db:
        with pytest.raises(RuntimeError, match="No mission preset"):
            compute_mission_kpis(db, aircraft_id, ["trainer"])


# ---------------------------------------------------------------------------
# gh-767: the active Soll polygon must reflect the user's editable
# MissionObjective targets, not the static preset.target_polygon.
# ---------------------------------------------------------------------------


def _persist_objective(SessionLocal, aircraft_id: int, **overrides) -> None:
    """Upsert a MissionObjective with sensible defaults + per-test overrides."""
    from app.schemas.mission_objective import MissionObjective
    from app.services.mission_objective_service import upsert_mission_objective

    base = MissionObjective(
        mission_type="trainer",
        target_cruise_mps=18.0,
        target_stall_safety=1.8,
        target_maneuver_n=3.0,
        target_glide_ld=12.0,
        target_climb_energy=22.0,
        target_wing_loading_n_m2=50.0,
        target_field_length_m=50.0,
        available_runway_m=80.0,
        runway_type="grass",
        t_static_N=20.0,
        takeoff_mode="runway",
    )
    with SessionLocal() as db:
        upsert_mission_objective(db, aircraft_id, base.model_copy(update=overrides))
        db.commit()


def test_active_target_polygon_reflects_objective_targets(client_and_db):
    """gh-767: the active Soll polygon is normalised from the user's
    MissionObjective targets, not copied from preset.target_polygon."""
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db, total_mass_kg=2.0)
        aircraft_id = aeroplane.id
    _seed_context(SessionLocal, aircraft_id)

    # Trainer preset cruise target_polygon == 0.3 with axis range (10, 25).
    # A 22 m/s target normalises to (22-10)/(25-10) = 0.8 — clearly distinct.
    _persist_objective(
        SessionLocal,
        aircraft_id,
        mission_type="trainer",
        target_cruise_mps=22.0,
        target_stall_safety=1.9,  # range (1.3, 2.5) -> 0.5
        target_glide_ld=18.0,  # range (5, 18) -> 1.0
    )

    with patch(
        "app.services.mission_kpi_service._compute_field_length_score",
        return_value=(45.0, 1.0, None),
    ):
        with SessionLocal() as db:
            kset = compute_mission_kpis(db, aircraft_id, ["trainer"])

    soll = next(p for p in kset.target_polygons if p.mission_id == "trainer")
    # cruise reflects the user's target (0.8), NOT the preset's hardcoded 0.3.
    assert soll.scores_0_1["cruise"] == pytest.approx(0.8)
    assert soll.scores_0_1["stall_safety"] == pytest.approx(0.5)
    assert soll.scores_0_1["glide"] == pytest.approx(1.0)
    # field_friendliness: Ist is target/effective, so meeting the declared
    # target field length == full score.
    assert soll.scores_0_1["field_friendliness"] == pytest.approx(1.0)


def test_comparison_target_polygons_keep_preset_defaults(client_and_db):
    """gh-767: only the active mission's Soll is objective-derived; comparison
    overlays keep their static preset polygon (no per-aeroplane targets exist
    for them)."""
    from app.services.mission_objective_service import list_mission_presets

    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db, total_mass_kg=2.0)
        aircraft_id = aeroplane.id
    _seed_context(SessionLocal, aircraft_id)
    _persist_objective(SessionLocal, aircraft_id, mission_type="trainer")

    with patch(
        "app.services.mission_kpi_service._compute_field_length_score",
        return_value=(45.0, 1.0, None),
    ):
        with SessionLocal() as db:
            presets = {p.id: p for p in list_mission_presets(db)}
            kset = compute_mission_kpis(db, aircraft_id, ["trainer", "sailplane"])

    sailplane_soll = next(p for p in kset.target_polygons if p.mission_id == "sailplane")
    assert sailplane_soll.scores_0_1 == presets["sailplane"].target_polygon


# ---------------------------------------------------------------------------
# Warning propagation (#562 review fix — surface t_static_N / recompute hints
# via MissionAxisKpi.warning now that FieldLengthsPanel is gone).
# ---------------------------------------------------------------------------


def _stub_aeroplane():
    """Smallest possible AeroplaneModel-like stub for the field-length helpers.

    _compute_field_length_score only touches the model when delegating to
    field_length_service. We mock that delegation in every test below, so a
    bare object suffices.
    """
    return object()


def test_compute_field_length_score_returns_warning_on_service_exception():
    """ServiceException raised by field_length_service must be propagated
    as the third element of the tuple (was silently swallowed pre-fix)."""
    msg = "t_static_N (static thrust) is required for takeoff_mode='runway'"
    with patch(
        "app.services.mission_kpi_service.compute_field_lengths_for_aeroplane",
        side_effect=ServiceException(message=msg),
    ):
        eff, score, warning = _compute_field_length_score(
            _stub_aeroplane(), target_field_length_m=50.0
        )
    assert eff is None
    assert score is None
    assert warning == msg


def test_compute_field_length_score_returns_warning_on_import_error():
    """ImportError (field_length_service unavailable on the platform) is the
    only OTHER exception we should catch — narrowed from bare Exception."""
    with patch(
        "app.services.mission_kpi_service.compute_field_lengths_for_aeroplane",
        side_effect=ImportError("aerosandbox not available"),
    ):
        eff, score, warning = _compute_field_length_score(
            _stub_aeroplane(), target_field_length_m=50.0
        )
    assert eff is None
    assert score is None
    assert warning is not None and "unavailable" in warning.lower()


def test_compute_field_length_score_propagates_unexpected_exception():
    """Unrelated RuntimeErrors must NOT be silently swallowed — they
    indicate real bugs and should bubble up to the endpoint handler so
    they get logged and reported."""
    with patch(
        "app.services.mission_kpi_service.compute_field_lengths_for_aeroplane",
        side_effect=RuntimeError("division by zero in CL_max"),
    ):
        with pytest.raises(RuntimeError, match="division by zero"):
            _compute_field_length_score(_stub_aeroplane(), target_field_length_m=50.0)


def test_compute_field_length_score_returns_warning_when_eff_is_zero():
    """Degenerate eff=0 (no takeoff distance) must surface a warning so
    the user knows why the axis is missing, not just that it is."""
    with patch(
        "app.services.mission_kpi_service.compute_field_lengths_for_aeroplane",
        return_value={"s_to_50ft_m": 0.0, "s_ldg_50ft_m": 0.0},
    ):
        eff, score, warning = _compute_field_length_score(
            _stub_aeroplane(), target_field_length_m=50.0
        )
    assert eff is None
    assert score is None
    assert warning is not None and "zero" in warning.lower()


def test_compute_field_length_score_no_warning_on_success():
    """The happy path must return (eff, score, None) — no spurious warning."""
    with patch(
        "app.services.mission_kpi_service.compute_field_lengths_for_aeroplane",
        return_value={"s_to_50ft_m": 40.0, "s_ldg_50ft_m": 35.0},
    ):
        eff, score, warning = _compute_field_length_score(
            _stub_aeroplane(), target_field_length_m=50.0
        )
    assert eff == 40.0
    assert score == 1.0  # target/eff clipped to 1.0
    assert warning is None


def test_kpi_field_friendliness_forwards_warning_to_missing_kpi():
    """The user-facing MissionAxisKpi.warning must carry the actionable
    hint from field_length_service. This is the regression-prevention test
    for the t_static_N hint being lost after FieldLengthsPanel removal."""
    msg = "t_static_N (static thrust) is required for takeoff_mode='runway'"
    with patch(
        "app.services.mission_kpi_service.compute_field_lengths_for_aeroplane",
        side_effect=ServiceException(message=msg),
    ):
        kpi = _kpi_field_friendliness(
            _stub_aeroplane(),
            target_field_length_m=50.0,
            range_min=0.0,
            range_max=200.0,
        )
    assert kpi.provenance == "missing"
    assert kpi.warning == msg
    assert kpi.axis == "field_friendliness"
