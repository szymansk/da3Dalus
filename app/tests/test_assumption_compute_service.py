"""Tests for the assumption compute service (Task 5 of gh-465).

All AeroSandbox-bound helpers are stubbed so tests run without ASB installed.
"""

from __future__ import annotations

import contextlib
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from app.models.aeroplanemodel import DesignAssumptionModel
from app.services.assumption_compute_service import recompute_assumptions
from app.services.design_assumptions_service import seed_defaults
from app.tests.conftest import make_aeroplane


@contextlib.contextmanager
def _enter_patches(flap_ted_max: float | None = None, fine_sweep_cl_max: float = 1.35):
    """Enter all stubs as a single context manager.

    Replaces the historical ``p1, p2, p3, p4, p5, p6 = _patches()`` unpack —
    the patch count grew with gh-526 (flap TED extraction). Using ExitStack
    keeps call sites stable across future stub additions.
    """
    with contextlib.ExitStack() as stack:
        for patcher in _patches(flap_ted_max=flap_ted_max, fine_sweep_cl_max=fine_sweep_cl_max):
            stack.enter_context(patcher)
        yield


def _make_fake_airplane(with_flap: bool = False):
    """Stub for asb_airplane: a wing with .area/.mean_aerodynamic_chord/.span()
    so _select_main_wing + the s_ref/c_ref/b_ref override don't blow up.

    `with_control_deflections` (gh-526) returns self, recording the call so
    tests can spy on flap-deflection invocations.

    When ``with_flap=True``, the wing carries a single xsec with a
    ``[flap]Flap`` control surface so that ``_detect_first_flap_name``
    can find it.
    """
    flap_cs = SimpleNamespace(name="[flap]Flap", deflection=0.0)
    xsec = SimpleNamespace(control_surfaces=[flap_cs] if with_flap else [])
    fake_wing = SimpleNamespace(
        area=lambda: 0.30,
        mean_aerodynamic_chord=lambda: 0.20,
        span=lambda: 1.5,
        xsecs=[xsec],
    )
    plane = SimpleNamespace(
        wings=[fake_wing],
        xyz_ref=[0.08, 0.0, 0.0],
        s_ref=0.30,
        c_ref=0.20,
        b_ref=1.5,
        _deflection_calls=[],
    )

    def with_control_deflections(mapping: dict):
        plane._deflection_calls.append(dict(mapping))
        return plane

    plane.with_control_deflections = with_control_deflections
    return plane


def _patches(flap_ted_max: float | None = None, fine_sweep_cl_max: float = 1.35):
    """Stub the ASB-bound helpers so tests don't need real ASB.

    Args:
        flap_ted_max: When None, simulates no flap geometry → fallback path.
            When float, simulates a flap with `positive_deflection_deg` =
            this value → 3 AeroBuildup passes.
        fine_sweep_cl_max: The C_L_max that the fine sweep returns. For the
            flapped configs we wrap the fine-sweep mock so that each call
            returns a different C_L_max (clean / takeoff / landing).
    """
    fake_airplane = _make_fake_airplane(with_flap=flap_ted_max is not None)

    # gh-526: the fine sweep is called once per configuration when a flap
    # exists. For the no-flap path, only the clean call happens.
    cl_array = np.array([0.2, 0.4, 0.6, 0.8, 1.0, 1.2])
    cd_array = np.array([0.026, 0.028, 0.032, 0.039, 0.049, 0.062])
    v_array = np.linspace(9.0, 28.0, 6)

    # Different C_L_max per config so v_s0 < v_s1 in tests.
    # Order of calls: clean, takeoff, landing.
    cl_max_sequence = [fine_sweep_cl_max, fine_sweep_cl_max + 0.4, fine_sweep_cl_max + 0.8]
    sweep_call = {"i": 0}

    def fine_sweep_side_effect(*_args, **_kwargs):
        i = sweep_call["i"]
        sweep_call["i"] += 1
        idx = min(i, len(cl_max_sequence) - 1)
        return (cl_max_sequence[idx], cl_array, cd_array, v_array)

    return (
        patch(
            "app.services.assumption_compute_service._build_asb_airplane",
            return_value=fake_airplane,
        ),
        patch(
            "app.services.assumption_compute_service._stability_run_at_cruise",
            return_value=(0.085, 0.20, 0.025, 0.30),  # x_np, MAC, CD0, s_ref
        ),
        patch(
            "app.services.assumption_compute_service._coarse_alpha_sweep",
            return_value=15.0,
        ),
        patch(
            "app.services.assumption_compute_service._fine_sweep_cl_max",
            side_effect=fine_sweep_side_effect,
        ),
        patch(
            "app.services.assumption_compute_service._extract_cl_alpha_from_linear_sweep",
            return_value=5.7,
        ),
        patch(
            "app.services.assumption_compute_service._load_flight_profile_speeds",
            return_value=(18.0, 28.0, True),
        ),
        patch(
            "app.services.assumption_compute_service._extract_flap_ted_max",
            return_value=flap_ted_max,
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

    with _enter_patches():
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
        cd0 = db.query(DesignAssumptionModel).filter_by(parameter_name="cd0").first()
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
        cd0_row = db.query(DesignAssumptionModel).filter_by(parameter_name="cd0").first()
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

    try:
        with _enter_patches():
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


def test_b_ref_m_is_in_context_after_recompute(client_and_db):
    """gh-491 sub-task: b_ref_m (span) must be persisted in assumption_computation_context."""
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)
        aeroplane_id = aeroplane.id

    with _enter_patches():
        with SessionLocal() as db:
            recompute_assumptions(db, aeroplane_uuid)
            db.commit()

    with SessionLocal() as db:
        from app.models.aeroplanemodel import AeroplaneModel

        a = db.query(AeroplaneModel).filter_by(id=aeroplane_id).first()
        ctx = a.assumption_computation_context
        assert "b_ref_m" in ctx, "b_ref_m must be present in assumption_computation_context"
        # The stub wing has span=1.5 m
        assert ctx["b_ref_m"] == 1.5


def test_polar_re_table_keys_in_context(client_and_db):
    """gh-493: polar_re_table and polar_re_table_degenerate must be in context.

    Backward-compat: cd0 and e_oswald scalar keys must ALSO remain.
    """
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)
        aeroplane_id = aeroplane.id

    with _enter_patches():
        with SessionLocal() as db:
            recompute_assumptions(db, aeroplane_uuid)
            db.commit()

    with SessionLocal() as db:
        from app.models.aeroplanemodel import AeroplaneModel

        a = db.query(AeroplaneModel).filter_by(id=aeroplane_id).first()
        ctx = a.assumption_computation_context

        # New gh-493 keys
        assert "polar_re_table" in ctx, "polar_re_table must be in context"
        assert "polar_re_table_degenerate" in ctx, "polar_re_table_degenerate must be in context"
        assert isinstance(ctx["polar_re_table_degenerate"], bool)
        assert isinstance(ctx["polar_re_table"], list)

        # Backward-compat: scalar cd0 and e_oswald must BOTH still be present (gh-486)
        # (they may be None if fit failed, but the keys must exist)
        assert "cd0" in ctx, "Backward-compat scalar key 'cd0' must remain in context"
        assert "e_oswald" in ctx, "Backward-compat scalar key 'e_oswald' must remain in context"


# ============================================================================
# gh-526 / epic gh-525 finding C1 — per-configuration polar
# ============================================================================


def _load_ctx(SessionLocal, aeroplane_id: int) -> dict:
    """Read assumption_computation_context for the given aeroplane."""
    from app.models.aeroplanemodel import AeroplaneModel

    with SessionLocal() as db:
        a = db.query(AeroplaneModel).filter_by(id=aeroplane_id).first()
        return a.assumption_computation_context


def test_context_has_polar_by_config_with_three_keys(client_and_db):
    """T1: ComputationContext exposes polar_by_config with clean/takeoff/landing.

    gh-526 AC: ``polar_by_config`` populated for all three keys.
    """
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)
        aeroplane_id = aeroplane.id

    with _enter_patches(flap_ted_max=30.0):
        with SessionLocal() as db:
            recompute_assumptions(db, aeroplane_uuid)
            db.commit()

    ctx = _load_ctx(SessionLocal, aeroplane_id)
    assert "polar_by_config" in ctx
    assert set(ctx["polar_by_config"].keys()) == {"clean", "takeoff", "landing"}
    for cfg in ("clean", "takeoff", "landing"):
        entry = ctx["polar_by_config"][cfg]
        assert "cl_max" in entry
        assert "cd0" in entry
        assert "e_oswald" in entry
        assert "flap_deflection_deg" in entry
        assert "provenance" in entry


def test_no_flap_aircraft_runs_one_pass_with_fallback_flag(client_and_db):
    """T2b: no flap geometry → 1 AeroBuildup pass, takeoff/landing cloned from clean."""
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)
        aeroplane_id = aeroplane.id

    # flap_ted_max=None → no flap → fallback
    with (
        patch(
            "app.services.assumption_compute_service._fine_sweep_cl_max",
            return_value=(
                1.35,
                np.array([0.2, 0.4, 0.6, 0.8, 1.0, 1.2]),
                np.array([0.026, 0.028, 0.032, 0.039, 0.049, 0.062]),
                np.linspace(9.0, 28.0, 6),
            ),
        ) as fine_sweep_mock,
        _enter_patches_no_fine_sweep(flap_ted_max=None),
    ):
        with SessionLocal() as db:
            recompute_assumptions(db, aeroplane_uuid)
            db.commit()

    assert fine_sweep_mock.call_count == 1, (
        f"Expected 1 AeroBuildup pass (no flap geometry), got {fine_sweep_mock.call_count}"
    )

    ctx = _load_ctx(SessionLocal, aeroplane_id)
    pbc = ctx["polar_by_config"]
    assert pbc["clean"]["provenance"] == "aerobuildup"
    assert pbc["takeoff"]["provenance"] == "no_flap_geometry"
    assert pbc["landing"]["provenance"] == "no_flap_geometry"
    # C_L_max identical when fallback cloned from clean
    assert pbc["clean"]["cl_max"] == pbc["takeoff"]["cl_max"] == pbc["landing"]["cl_max"]


def test_flapped_aircraft_runs_three_passes_and_v_s0_less_than_v_s1(client_and_db):
    """T2a + T3: flap present → 3 AeroBuildup passes; V_s0 (landing) < V_s1 (clean)."""
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)
        aeroplane_id = aeroplane.id

    with _enter_patches(flap_ted_max=30.0):
        with SessionLocal() as db:
            recompute_assumptions(db, aeroplane_uuid)
            db.commit()

    ctx = _load_ctx(SessionLocal, aeroplane_id)
    pbc = ctx["polar_by_config"]
    # Landing C_L_max > clean → V_s0 < V_s1
    assert pbc["landing"]["cl_max"] > pbc["clean"]["cl_max"]
    assert pbc["takeoff"]["cl_max"] > pbc["clean"]["cl_max"]
    # All three provenance = aerobuildup when flap is present
    assert pbc["clean"]["provenance"] == "aerobuildup"
    assert pbc["takeoff"]["provenance"] == "aerobuildup"
    assert pbc["landing"]["provenance"] == "aerobuildup"

    assert ctx["v_s1_mps"] is not None
    assert ctx["v_s0_mps"] is not None
    assert ctx["v_s0_mps"] < ctx["v_s1_mps"], (
        f"V_s0 must be smaller than V_s1 with flap; got v_s0={ctx['v_s0_mps']}, "
        f"v_s1={ctx['v_s1_mps']}"
    )


def test_v_s1_alias_matches_v_stall_for_backward_compat(client_and_db):
    """T4: v_stall_mps == v_s1_mps (clean stall, backward-compat alias).

    field_length_service, flight_envelope_service, matching_chart_service all
    read v_stall_mps — preserving the alias keeps them correct.
    """
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)
        aeroplane_id = aeroplane.id

    with _enter_patches(flap_ted_max=30.0):
        with SessionLocal() as db:
            recompute_assumptions(db, aeroplane_uuid)
            db.commit()

    ctx = _load_ctx(SessionLocal, aeroplane_id)
    assert ctx["v_stall_mps"] == ctx["v_s1_mps"]


def test_aerobuildup_failure_falls_back_to_clean_polar(client_and_db):
    """T6: when the flap-deflected AeroBuildup raises, the corresponding
    config falls back to the clean polar with provenance='aerobuildup_failed'.

    Audits the independent-try-block change so a takeoff failure does NOT
    prevent the landing pass from running (review feedback).
    """
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)
        aeroplane_id = aeroplane.id

    # Force the flap-deflected helper to raise — the clean polar should
    # still be produced, and both takeoff/landing get the fallback flag.
    with (
        patch(
            "app.services.assumption_compute_service._run_polar_for_deflection",
            side_effect=RuntimeError("simulated AeroBuildup crash"),
        ),
        _enter_patches(flap_ted_max=30.0),
    ):
        with SessionLocal() as db:
            recompute_assumptions(db, aeroplane_uuid)
            db.commit()

    ctx = _load_ctx(SessionLocal, aeroplane_id)
    pbc = ctx["polar_by_config"]
    assert pbc["clean"]["provenance"] == "aerobuildup"
    assert pbc["takeoff"]["provenance"] == "aerobuildup_failed"
    assert pbc["landing"]["provenance"] == "aerobuildup_failed"
    # Fallback uses clean cl_max so V_s comes out as the clean stall.
    assert pbc["takeoff"]["cl_max"] == pbc["clean"]["cl_max"]
    assert pbc["landing"]["cl_max"] == pbc["clean"]["cl_max"]


def test_flap_takeoff_deflection_clipped_to_ted_max(client_and_db):
    """T7: default δ_to=15° and δ_ldg=30° are clipped to TED.positive_deflection_deg.

    With a TED limit of 10°, both takeoff and landing polars should be
    computed at δ=10°, not 15° / 30°.
    """
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)
        aeroplane_id = aeroplane.id

    with _enter_patches(flap_ted_max=10.0):
        with SessionLocal() as db:
            recompute_assumptions(db, aeroplane_uuid)
            db.commit()

    ctx = _load_ctx(SessionLocal, aeroplane_id)
    pbc = ctx["polar_by_config"]
    assert pbc["takeoff"]["flap_deflection_deg"] == 10.0
    assert pbc["landing"]["flap_deflection_deg"] == 10.0


@contextlib.contextmanager
def _enter_patches_no_fine_sweep(flap_ted_max: float | None = None):
    """Variant: skip the fine_sweep patch so the test can supply its own
    mock with call-counting."""
    with contextlib.ExitStack() as stack:
        for patcher in _patches(flap_ted_max=flap_ted_max):
            # Skip the fine_sweep patcher so the test owns it.
            if "_fine_sweep_cl_max" in getattr(patcher, "attribute", ""):
                continue
            stack.enter_context(patcher)
        yield
