"""Tests for the assumption compute service (Task 5 of gh-465).

All AeroSandbox-bound helpers are stubbed so tests run without ASB installed.
"""

from __future__ import annotations

import contextlib
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

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
        return (cl_max_sequence[idx], cl_array, cd_array, v_array, np.zeros_like(cl_array))

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
            return_value=(5.7, -2.3),  # gh-871: now returns (cl_alpha_per_rad, alpha_0_deg)
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
                np.zeros(6),
            ),
        ) as fine_sweep_mock,
        _enter_patches_no_fine_sweep(flap_ted_max=None),
    ):
        with SessionLocal() as db:
            recompute_assumptions(db, aeroplane_uuid)
            db.commit()

    # No flap geometry → only the CLEAN config is computed (takeoff/landing are
    # cloned, not separately swept). gh-672: this fixture's sweep yields only 5
    # in-window points (cl_max=1.35 → window [0.135, 1.1475]), so the clean fit
    # is rejected for `insufficient_points` and the α-resolution auto-recovery
    # re-runs the (still-degenerate) clean sweep twice → 1 initial + 2 retries.
    # That no takeoff/landing AeroBuildup passes run is carried by the
    # provenance assertions below.
    assert fine_sweep_mock.call_count == 3, (
        f"Expected 1 clean pass + 2 gh-672 refinement retries, got {fine_sweep_mock.call_count}"
    )

    ctx = _load_ctx(SessionLocal, aeroplane_id)
    pbc = ctx["polar_by_config"]
    assert pbc["clean"]["provenance"] == "aerobuildup"
    # refinement was attempted but the degenerate sweep still didn't fit → no banner
    assert pbc["clean"]["auto_refined"] is False
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


def test_flap_geometry_mismatch_falls_back_with_warning(client_and_db, caplog):
    """gh-537: when the schema reports a flap TED but the ASB airplane has
    no flap-role control surface, the per-config polar must fall back to
    `no_flap_geometry` provenance with a clear log warning — not raise.

    Repro: `_extract_flap_ted_max` returns 25.0 (model says flap exists),
    but `_make_fake_airplane(with_flap=False)` produces an airplane with
    no flap-role control surface (ASB sees nothing).
    """
    import logging

    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)
        aeroplane_id = aeroplane.id

    asb_no_flap = _make_fake_airplane(with_flap=False)
    caplog.set_level(logging.WARNING, logger="app.services.assumption_compute_service")
    with (
        patch(
            "app.services.assumption_compute_service._build_asb_airplane",
            return_value=asb_no_flap,
        ),
        patch(
            "app.services.assumption_compute_service._stability_run_at_cruise",
            return_value=(0.085, 0.20, 0.025, 0.30),
        ),
        patch(
            "app.services.assumption_compute_service._coarse_alpha_sweep",
            return_value=15.0,
        ),
        patch(
            "app.services.assumption_compute_service._fine_sweep_cl_max",
            return_value=(
                1.35,
                np.array([0.2, 0.4, 0.6, 0.8, 1.0, 1.2]),
                np.array([0.026, 0.028, 0.032, 0.039, 0.049, 0.062]),
                np.linspace(9.0, 28.0, 6),
                np.zeros(6),
            ),
        ),
        patch(
            "app.services.assumption_compute_service._extract_cl_alpha_from_linear_sweep",
            return_value=(5.7, -2.3),  # gh-871: now returns (cl_alpha_per_rad, alpha_0_deg)
        ),
        patch(
            "app.services.assumption_compute_service._load_flight_profile_speeds",
            return_value=(18.0, 28.0, True),
        ),
        patch(
            "app.services.assumption_compute_service._extract_flap_ted_max",
            return_value=25.0,  # schema disagrees with ASB
        ),
    ):
        with SessionLocal() as db:
            # Must not raise — the parity guard catches the mismatch.
            recompute_assumptions(db, aeroplane_uuid)
            db.commit()

    ctx = _load_ctx(SessionLocal, aeroplane_id)
    pbc = ctx["polar_by_config"]
    assert pbc["takeoff"]["provenance"] == "no_flap_geometry"
    assert pbc["landing"]["provenance"] == "no_flap_geometry"
    parity_warning = any(
        "parity" in rec.message.lower() or "mismatch" in rec.message.lower()
        for rec in caplog.records
        if rec.levelno >= logging.WARNING
    )
    assert parity_warning, (
        f"Expected a parity/mismatch warning; got: {[r.message for r in caplog.records]}"
    )


# gh-685: cold-start ValueError("x_np=None or mac=None") in
# compute_forward_cg_limit is expected on the first recompute of a fresh
# aeroplane — must NOT log WARNING + traceback. Only genuine errors do.


def _run_recompute_with_forward_cg_exception(SessionLocal, exception, caplog):
    """Helper: trigger recompute with a stubbed compute_forward_cg_limit
    that raises ``exception``. Returns the captured log records."""
    import contextlib
    import logging

    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)

    caplog.set_level(logging.INFO, logger="app.services.assumption_compute_service")
    with contextlib.ExitStack() as stack:
        for patcher in _patches(flap_ted_max=None):
            stack.enter_context(patcher)
        stack.enter_context(
            patch(
                "app.services.elevator_authority_service.compute_forward_cg_limit",
                side_effect=exception,
            )
        )
        with SessionLocal() as db:
            recompute_assumptions(db, aeroplane_uuid)
            db.commit()
    return list(caplog.records)


def test_forward_cg_cold_start_value_error_logs_info_no_traceback(client_and_db, caplog):
    """gh-685: first-recompute cold-start uses INFO + no exc_info."""
    import logging

    _, SessionLocal = client_and_db
    records = _run_recompute_with_forward_cg_exception(
        SessionLocal,
        ValueError("x_np=None or mac=None not available — run assumptions first."),
        caplog,
    )
    matching = [
        r
        for r in records
        if "Forward-CG limit deferred" in r.message
        and r.name == "app.services.assumption_compute_service"
    ]
    assert matching, (
        f"Expected an INFO 'Forward-CG limit deferred' message; got: "
        f"{[(r.levelname, r.message[:80]) for r in records]}"
    )
    rec = matching[0]
    assert rec.levelno == logging.INFO, f"Cold-start case must be INFO, got {rec.levelname}"
    assert rec.exc_info is None, "Cold-start case must not attach traceback (exc_info)"


def test_forward_cg_real_value_error_still_logs_warning_with_traceback(client_and_db, caplog):
    """gh-685: a non-cold-start ValueError still produces WARNING + traceback."""
    import logging

    _, SessionLocal = client_and_db
    records = _run_recompute_with_forward_cg_exception(
        SessionLocal,
        ValueError("something else went wrong in elevator authority"),
        caplog,
    )
    matching = [
        r
        for r in records
        if "Elevator authority forward CG failed" in r.message
        and r.name == "app.services.assumption_compute_service"
    ]
    assert matching, (
        f"Expected WARNING 'Elevator authority forward CG failed'; got: "
        f"{[(r.levelname, r.message[:80]) for r in records]}"
    )
    rec = matching[0]
    assert rec.levelno == logging.WARNING
    assert rec.exc_info is not None, "Non-cold-start case must still attach traceback (exc_info)"


def test_forward_cg_runtime_error_logs_warning_with_traceback(client_and_db, caplog):
    """gh-685: non-ValueError exceptions still hit the broad Exception handler."""
    import logging

    _, SessionLocal = client_and_db
    records = _run_recompute_with_forward_cg_exception(
        SessionLocal,
        RuntimeError("synthetic genuine bug"),
        caplog,
    )
    matching = [
        r
        for r in records
        if "Elevator authority forward CG failed" in r.message
        and r.name == "app.services.assumption_compute_service"
    ]
    assert matching, "Expected WARNING for RuntimeError too"
    rec = matching[0]
    assert rec.levelno == logging.WARNING
    assert rec.exc_info is not None


def test_landing_polar_uses_full_ted_limit_above_30deg(client_and_db):
    """gh-534: with a 40°-rated Fowler flap, the landing polar must run
    at the FULL TED max (40°), not the historical 30° cap.

    The old 30° cap (assumption_compute_service:168) under-deflected
    real Fowler flaps → CL_max_LDG too low → V_s0 too high → V_APP
    overshot the POH by ~23 % on a Cessna-172 cross-check.
    """
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)
        aeroplane_id = aeroplane.id

    with _enter_patches(flap_ted_max=40.0):
        with SessionLocal() as db:
            recompute_assumptions(db, aeroplane_uuid)
            db.commit()

    ctx = _load_ctx(SessionLocal, aeroplane_id)
    pbc = ctx["polar_by_config"]
    # Takeoff stays at the 15° seed (high-deflection at takeoff would
    # hurt climb performance — keep the moderate seed).
    assert pbc["takeoff"]["flap_deflection_deg"] == 15.0
    # Landing uses the FULL TED limit (no 30° cap).
    assert pbc["landing"]["flap_deflection_deg"] == 40.0


# ============================================================================
# gh-476 — extended V-speed set (v_a, v_dive, v_x, v_y) in ComputationContext
# ============================================================================


def test_context_includes_v_a_mps_from_stall_and_g_limit(client_and_db):
    """gh-476: V_a = V_s · √g_limit, capped at V_C (Scholz / CS-25.335(c))."""
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
    assert "v_a_mps" in ctx
    # The default g_limit is 3.0 (PARAMETER_DEFAULTS). v_a = v_s1 · √3
    # capped at v_cruise.
    expected_uncapped = ctx["v_s1_mps"] * (3.0**0.5)
    expected = min(expected_uncapped, ctx["v_cruise_mps"])
    assert abs(ctx["v_a_mps"] - expected) < 0.2


def test_context_v_a_is_capped_at_v_cruise(client_and_db):
    """gh-476 + Scholz M4: V_a must not exceed V_C even when V_s·√n+ does."""
    from app.models.aeroplanemodel import DesignAssumptionModel

    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        # Force a high g_limit so V_s · √n_max exceeds V_cruise.
        g_row = (
            db.query(DesignAssumptionModel)
            .filter_by(aeroplane_id=aeroplane.id, parameter_name="g_limit")
            .first()
        )
        g_row.calculated_value = 12.0
        g_row.calculated_source = "test"
        g_row.active_source = "CALCULATED"
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)
        aeroplane_id = aeroplane.id

    with _enter_patches(flap_ted_max=30.0):
        with SessionLocal() as db:
            recompute_assumptions(db, aeroplane_uuid)
            db.commit()

    ctx = _load_ctx(SessionLocal, aeroplane_id)
    assert ctx["v_a_mps"] == ctx["v_cruise_mps"], (
        f"V_a must be capped at V_C; got V_a={ctx['v_a_mps']}, V_C={ctx['v_cruise_mps']}"
    )


def test_context_includes_v_dive_mps_as_heuristic(client_and_db):
    """gh-476: V_dive = 1.4·V_max (heuristic placeholder until flutter analysis)."""
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
    assert "v_dive_mps" in ctx
    assert abs(ctx["v_dive_mps"] - 1.4 * ctx["v_max_mps"]) < 0.2


def test_context_v_x_and_v_y_are_none_when_no_ops_exist(client_and_db):
    """gh-476: V_x / V_y come from operating-point output. When no OPs
    have been generated yet, both must be None (chip row shows '–')."""
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
    assert "v_x_mps" in ctx
    assert "v_y_mps" in ctx
    assert ctx["v_x_mps"] is None
    assert ctx["v_y_mps"] is None


def test_context_v_x_and_v_y_read_from_existing_ops(client_and_db):
    """gh-476: when operating points named `best_angle_climb_vx` /
    `best_rate_climb_vy` exist, their `velocity` fields populate v_x_mps
    and v_y_mps in the assumption context."""
    from app.models.analysismodels import OperatingPointModel

    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        # Seed two OPs that gh-476 should pick up.
        db.add(
            OperatingPointModel(
                name="best_angle_climb_vx",
                description="seed",
                aircraft_id=aeroplane.id,
                config="clean",
                status="TRIMMED",
                warnings=[],
                controls={},
                velocity=12.5,
                alpha=0.08,
                beta=0.0,
                p=0.0,
                q=0.0,
                r=0.0,
                xyz_ref=[0, 0, 0],
                altitude=0.0,
            )
        )
        db.add(
            OperatingPointModel(
                name="best_rate_climb_vy",
                description="seed",
                aircraft_id=aeroplane.id,
                config="clean",
                status="TRIMMED",
                warnings=[],
                controls={},
                velocity=15.3,
                alpha=0.04,
                beta=0.0,
                p=0.0,
                q=0.0,
                r=0.0,
                xyz_ref=[0, 0, 0],
                altitude=0.0,
            )
        )
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)
        aeroplane_id = aeroplane.id

    with _enter_patches(flap_ted_max=30.0):
        with SessionLocal() as db:
            recompute_assumptions(db, aeroplane_uuid)
            db.commit()

    ctx = _load_ctx(SessionLocal, aeroplane_id)
    assert ctx["v_x_mps"] == 12.5
    assert ctx["v_y_mps"] == 15.3


# ---------------------------------------------------------------------------
# gh-692: min sink rate (w_min) — vertical speed at V_min_sink
# ---------------------------------------------------------------------------


def test_context_includes_min_sink_rate_mps(client_and_db):
    """gh-692: w_min is the vertical speed at V_min_sink — the value pilots
    read off the speed polar. Derived in closed form from the polar (no
    AeroBuildup call), so it must populate alongside v_min_sink_mps."""
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
    assert "min_sink_rate_mps" in ctx
    w_min = ctx["min_sink_rate_mps"]
    assert w_min is not None
    # Plausible band for the default fixture (RC-scale clean trainer).
    assert 0.3 <= w_min <= 2.0, f"w_min={w_min} m/s outside plausible [0.3, 2.0]"


def test_min_sink_rate_helper_matches_closed_form_formula():
    """gh-692: pin the formula directly on the helper, decoupled from the
    recompute pipeline's effective-value resolution / Picard / clamp.

        w_min = V_min_sink · (C_D/C_L)_mp
        (C_D/C_L)_mp = 4 · sqrt(C_D0 / (3·π·e·AR))   (Anderson §6.7.2)
    """
    from app.services.assumption_compute_service import _min_sink_rate, _min_sink_speed

    # Representative RC-scale trainer scalars.
    mass = 1.5  # kg
    s_ref = 0.30  # m²
    cd0 = 0.025
    ar = 8.0
    e = 0.85
    rho = 1.225
    g = 9.81

    v_ms = _min_sink_speed(mass, s_ref, cd0, ar, rho=rho, g=g, oswald_e=e)
    w_min = _min_sink_rate(mass, s_ref, cd0, ar, rho=rho, g=g, oswald_e=e)

    expected_ratio = 4.0 * np.sqrt(cd0 / (3.0 * np.pi * e * ar))
    expected_w = v_ms * expected_ratio

    # Both come from closed-form math → expect machine precision agreement.
    assert abs(w_min - expected_w) < 1e-12, (
        f"w_min={w_min}, expected={expected_w} from V_min_sink={v_ms}, "
        f"CD0={cd0}, e={e}, AR={ar}, ratio={expected_ratio}"
    )


def test_min_sink_rate_null_when_degenerate_inputs(client_and_db):
    """gh-692: when V_min_sink would be None (zero CD0 / no wing / etc.),
    w_min must also be None — same degenerate-input contract."""
    from app.services.assumption_compute_service import _min_sink_rate

    # Direct unit test of the helper to cover degenerate paths the
    # full-pipeline tests can't easily reach.
    assert _min_sink_rate(mass_kg=1.0, s_ref_m2=0.0, cd0=0.02, aspect_ratio=8.0) is None
    assert _min_sink_rate(mass_kg=1.0, s_ref_m2=0.3, cd0=0.0, aspect_ratio=8.0) is None
    assert _min_sink_rate(mass_kg=1.0, s_ref_m2=0.3, cd0=0.02, aspect_ratio=None) is None
    assert _min_sink_rate(mass_kg=1.0, s_ref_m2=0.3, cd0=0.02, aspect_ratio=0.0) is None


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


# ---------------------------------------------------------------------------
# gh-924: parasite CD0 = total CD − induced CD (single source of truth)
# ---------------------------------------------------------------------------


class TestParasiteCd0:
    """The published CD0 must be the zero-lift (parasite) intercept, not the
    total drag at a lifting α. Anderson §6.7.2: at (L/D)max induced = parasite.
    """

    def test_subtracts_induced_drag(self):
        import math

        from app.services.assumption_compute_service import _parasite_cd0

        # eHawk cruise point: CD_total=0.02364 at CL=0.552, e=0.827, AR=11.3
        cd0 = _parasite_cd0(0.02364, cl=0.552, ar=11.3, e=0.827)
        expected = 0.02364 - 0.552**2 / (math.pi * 11.3 * 0.827)
        assert cd0 == pytest.approx(expected, abs=1e-6)
        assert cd0 == pytest.approx(0.0133, abs=5e-4)
        # crucially: NOT the total drag (the old bug)
        assert cd0 < 0.02364

    def test_symmetric_wing_at_zero_lift_unchanged(self):
        # CL=0 (symmetric airfoil at α=0) → no induced drag → CD0 == total
        from app.services.assumption_compute_service import _parasite_cd0

        assert _parasite_cd0(0.018, cl=0.0, ar=8.0, e=0.85) == pytest.approx(0.018)

    def test_guards_return_total_on_bad_inputs(self):
        from app.services.assumption_compute_service import _parasite_cd0

        assert _parasite_cd0(0.02, cl=None, ar=8.0, e=0.8) == 0.02
        assert _parasite_cd0(0.02, cl=0.5, ar=0.0, e=0.8) == 0.02
        assert _parasite_cd0(0.02, cl=0.5, ar=8.0, e=0.0) == 0.02

    def test_never_returns_negative(self):
        # Pathological: huge CL would over-subtract → guard keeps total CD
        from app.services.assumption_compute_service import _parasite_cd0

        out = _parasite_cd0(0.02, cl=3.0, ar=4.0, e=0.6)
        assert out == 0.02  # fell back to total, not negative

    def test_emax_self_consistent_with_parasite_cd0(self):
        """(L/D)max = ½√(πAe/CD0) must land in the physical band with parasite CD0."""
        import math

        from app.services.assumption_compute_service import _parasite_cd0

        cd0 = _parasite_cd0(0.02364, cl=0.552, ar=11.3, e=0.7916)
        e_max = 0.5 * math.sqrt(math.pi * 11.3 * 0.7916 / cd0)
        assert e_max == pytest.approx(23.0, abs=1.0)  # NOT the wrong 17


# ---------------------------------------------------------------------------
# gh-935 MAJOR 2: turbulator-adjusted cd0 must NOT contaminate polar-fit gate
# ---------------------------------------------------------------------------


class TestTurbulatorCd0FitDecoupling:
    """gh-935 MAJOR 2: the parabolic fit's sanity gate (|cd0_fit - cd0_stability|
    / cd0_stability ≤ 0.20) must use the RAW (pre-turbulator) cd0, not the
    turbulator-adjusted one.

    Scenario: raw cd0 = 0.020, turbulator reduces drag by 25% → cd0_adjusted
    = 0.015.  The polar fit (natural-transition sweep) yields cd0_fit ≈ 0.020
    (consistent with the raw cd0).  With the BUG, cd0_stability = 0.015 → the
    gate flags |0.020 - 0.015| / 0.015 = 33% > 20% → spurious rejection.
    With the FIX, cd0_stability = 0.020 (raw) → gate passes.

    These tests are written to FAIL on the current code and PASS after the fix.
    """

    def _make_parabolic_polar_data(self, cd0_base: float = 0.020):
        """Create realistic CL/CD arrays that fit a parabolic polar with cd0≈cd0_base."""
        cl = np.linspace(0.10, 1.20, 30)
        # CD = cd0 + CL²/(π*e*AR),  e=0.85, AR=8
        e, ar = 0.85, 8.0
        cd = cd0_base + cl**2 / (np.pi * e * ar)
        return cl, cd

    def test_large_turbulator_delta_does_not_spuriously_reject_polar_fit(self):
        """gh-935 MAJOR 2: a large ΔCD0 (−25%) must NOT trigger cd0_stability_mismatch.

        The polar fit receives NATURAL-TRANSITION data (cd0≈0.020); the turbulator
        reduces raw_cd0=0.020 to cd0_adjusted=0.015 (25% reduction). The gate must
        compare against raw_cd0=0.020, not cd0_adjusted=0.015.

        This test was written to FAIL on the old code (gate uses adjusted cd0) and
        PASS after the fix (gate uses raw cd0).
        """
        from app.services.assumption_compute_service import _fit_parabolic_polar

        raw_cd0 = 0.020
        turbulator_delta = -0.005  # 25% reduction
        cd0_adjusted = raw_cd0 + turbulator_delta  # = 0.015

        cl, cd = self._make_parabolic_polar_data(cd0_base=raw_cd0)

        # With the FIX: pass raw_cd0 as cd0_stability → gate passes
        cd0_fit, e_oswald, r2, rejection_raw = _fit_parabolic_polar(
            cl=cl, cd=cd, ar=8.0, cl_max=1.35, cd0_stability=raw_cd0
        )
        # With the BUG (old behavior): passing adjusted cd0 → gate may reject
        _cd0_fit_bug, _e_bug, _r2_bug, rejection_adjusted = _fit_parabolic_polar(
            cl=cl, cd=cd, ar=8.0, cl_max=1.35, cd0_stability=cd0_adjusted
        )

        # Fix: passing raw_cd0 must succeed (no rejection)
        assert rejection_raw is None, (
            f"Polar fit rejected with raw_cd0={raw_cd0}: gate={getattr(rejection_raw, 'gate', '?')}"
        )
        assert cd0_fit is not None
        assert e_oswald is not None

        # Bug confirmation: passing adjusted cd0 triggers the gate
        # (deviation = |0.020 - 0.015| / 0.015 ≈ 33% > 20%)
        assert rejection_adjusted is not None, (
            "Expected cd0_stability_mismatch rejection when turbulator-adjusted cd0 "
            f"is passed (cd0_stability={cd0_adjusted}, cd0_fit≈{cd0_fit})"
        )
        assert rejection_adjusted.gate == "cd0_stability_mismatch"

    def test_stored_cd0_reflects_turbulator_delta(self, client_and_db):
        """gh-935 MAJOR 2: the DB-stored cd0 must reflect the turbulator delta,
        while the polar fit receives the raw (pre-turbulator) cd0.

        Setup: raw cd0=0.025 from stability run; apply_turbulator_delta_to_cd0
               injects a 20% reduction → adjusted cd0=0.020. The stored value
               in the DB must be 0.020, and the polar fit must NOT be called
               with the adjusted 0.020 (which would make the gate flag
               |0.025 - 0.020| / 0.020 = 25% > 20%).

        This test is written to FAIL on the old code (turbulator-adjusted cd0
        contaminating the polar fit stability gate) and PASS after the fix.
        """
        from unittest.mock import patch

        from app.models.aeroplanemodel import DesignAssumptionModel
        from app.services.assumption_compute_service import recompute_assumptions
        from app.services.design_assumptions_service import seed_defaults
        from app.tests.conftest import make_aeroplane

        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            seed_defaults(db, str(aeroplane.uuid))
            db.commit()
            aeroplane_uuid = str(aeroplane.uuid)
            aeroplane_id = aeroplane.id

        # Build CL/CD data consistent with raw_cd0=0.025 so the polar fit passes.
        raw_cd0 = 0.025
        adjusted_cd0 = 0.020  # turbulator reduces by 20%
        cl_arr = np.linspace(0.10, 1.20, 30)
        cd_arr = raw_cd0 + cl_arr**2 / (np.pi * 0.85 * 8.0)
        v_arr = np.linspace(9.0, 28.0, len(cl_arr))
        cdi_arr = cl_arr**2 / (np.pi * 0.85 * 8.0)

        # Capture what cd0_stability value _fit_parabolic_polar_with_refinement receives.
        fit_calls_cd0_stability: list[float] = []
        original_fit = __import__(
            "app.services.assumption_compute_service",
            fromlist=["_fit_parabolic_polar_with_refinement"],
        )._fit_parabolic_polar_with_refinement

        def _spy_fit(**kwargs):
            fit_calls_cd0_stability.append(kwargs.get("cd0_stability", float("nan")))
            return original_fit(**kwargs)

        with _enter_patches():
            # Bypass the turbulator section-building entirely: patch
            # apply_turbulator_delta_to_cd0 at module level AND patch the
            # entire turbulator injection block by stubbing
            # _extract_main_wing_turbulator_xtr to enable it, and providing a
            # fake ASB airplane whose xsecs have xyz_le so the block runs to
            # completion.  The key observable is what cd0_stability value the
            # polar fit receives.
            import numpy as _np_test
            from types import SimpleNamespace as _SN

            fake_xsec = _SN(
                xyz_le=_np_test.array([0.0, 0.25, 0.0]),
                airfoil=_SN(name="naca0012"),
                control_surfaces=[],
            )
            fake_wing_turb = _SN(
                area=lambda: 0.30,
                mean_aerodynamic_chord=lambda: 0.20,
                span=lambda: 1.5,
                xsecs=[fake_xsec],
                name="main_wing",
            )
            fake_plane_turb = _SN(
                wings=[fake_wing_turb],
                xyz_ref=[0.08, 0.0, 0.0],
                s_ref=0.30,
                c_ref=0.20,
                b_ref=1.5,
                _deflection_calls=[],
            )
            fake_plane_turb.with_control_deflections = lambda m: fake_plane_turb

            with (
                patch(
                    "app.services.assumption_compute_service._build_asb_airplane",
                    return_value=fake_plane_turb,
                ),
                patch(
                    "app.services.assumption_compute_service._stability_run_at_cruise",
                    return_value=(0.085, 0.20, raw_cd0, 0.30),
                ),
                patch(
                    "app.services.assumption_compute_service._coarse_alpha_sweep",
                    return_value=15.0,
                ),
                patch(
                    "app.services.assumption_compute_service._fine_sweep_cl_max",
                    return_value=(1.35, cl_arr, cd_arr, v_arr, cdi_arr),
                ),
                patch(
                    "app.services.assumption_compute_service._extract_cl_alpha_from_linear_sweep",
                    return_value=(5.7, -2.3),
                ),
                patch(
                    "app.services.assumption_compute_service._load_flight_profile_speeds",
                    return_value=(18.0, 28.0, True),
                ),
                patch(
                    "app.services.assumption_compute_service._extract_flap_ted_max",
                    return_value=None,
                ),
                patch(
                    "app.services.assumption_compute_service.apply_turbulator_delta_to_cd0",
                    return_value=adjusted_cd0,
                ),
                patch(
                    "app.services.assumption_compute_service._extract_main_wing_turbulator_xtr",
                    return_value=(0.4, 0.6, True),  # turbulator enabled
                ),
                patch(
                    "app.services.section_aoa_service.compute_section_aoa",
                    return_value=[],  # empty section list → _wing_sections=[] → apply_turbulator called with empty sections
                ),
                patch(
                    "app.services.assumption_compute_service._fit_parabolic_polar_with_refinement",
                    side_effect=_spy_fit,
                ),
                SessionLocal() as db,
            ):
                recompute_assumptions(db, aeroplane_uuid)
                db.commit()

        with SessionLocal() as db:
            rows = {
                r.parameter_name: r
                for r in db.query(DesignAssumptionModel)
                .filter(DesignAssumptionModel.aeroplane_id == aeroplane_id)
                .all()
            }
            # MAJOR 2 fix: the STORED cd0 must reflect the turbulator delta (= 0.020)
            assert rows["cd0"].calculated_value == pytest.approx(adjusted_cd0, abs=1e-5), (
                f"Expected stored cd0={adjusted_cd0} (turbulator-adjusted), "
                f"got {rows['cd0'].calculated_value}"
            )

        # MAJOR 2 fix: the polar fit must have been called with RAW cd0 (0.025),
        # NOT the turbulator-adjusted cd0 (0.020).  Passing 0.020 would cause
        # |0.025 - 0.020| / 0.020 = 25% > 20% → spurious cd0_stability_mismatch.
        assert len(fit_calls_cd0_stability) >= 1, "Expected _fit_parabolic_polar_with_refinement to be called"
        assert fit_calls_cd0_stability[0] == pytest.approx(raw_cd0, abs=1e-6), (
            f"Polar fit should receive raw_cd0={raw_cd0}, got cd0_stability={fit_calls_cd0_stability[0]:.5f}. "
            "The turbulator-adjusted cd0 must be applied AFTER the fit, not before."
        )
