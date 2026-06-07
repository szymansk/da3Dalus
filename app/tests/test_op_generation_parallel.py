"""gh-867: parallel OP-generation building blocks.

Fast-tier unit tests for the ProcessPool plumbing — no aerosandbox and no real
worker processes (the solver boundary is mocked, the executor is faked). The
real spawn + pickling + solve path is covered by the slow integration tests
that drive ``generate_default_set_for_aircraft``.
"""

from __future__ import annotations

import math
import os
from concurrent.futures import Future
from unittest.mock import patch

import pytest

from app.services import operating_point_generator_service as opg
from app.services.operating_point_generator_service import (
    _AircraftMassOnly,
    _GenerationContext,
    _solve_target_in_worker,
    _solve_targets_in_parallel,
    _worker_ctx_from,
)


class _InlineExecutor:
    """Runs submits synchronously; ``as_completed`` works on the resolved futures."""

    def submit(self, fn, *args, **kwargs):
        future: Future = Future()
        try:
            future.set_result(fn(*args, **kwargs))
        except Exception as exc:  # pragma: no cover
            future.set_exception(exc)
        return future


def _ctx(total_mass_kg=2.0) -> _GenerationContext:
    return _GenerationContext(
        aircraft=_AircraftMassOnly(total_mass_kg),
        targets=[],
        asb_airplane=object(),
        capabilities={"available_controls": ["[elevator]Elevator"]},
        deflection_limits={"[elevator]Elevator": (25.0, 25.0)},
        plane_schema=object(),
        constraints={"max_alpha_deg": 14.0},
        effective_mass_kg=2.5,
        design_cg_x=0.1,
        source_profile_id=None,
        refs={"vs_clean": 8.0},
    )


def test_worker_count_is_bounded():
    n = opg._opg_worker_count()
    assert 1 <= n <= 4
    assert n <= max(1, (os.cpu_count() or 1))


def test_worker_init_pins_blas_threads():
    saved = {v: os.environ.pop(v, None) for v in opg._BLAS_THREAD_ENV}
    try:
        opg._opg_worker_init()
        assert all(os.environ.get(v) == "1" for v in opg._BLAS_THREAD_ENV)
    finally:
        for v, old in saved.items():
            if old is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = old


def test_worker_ctx_carries_picklable_subset_and_mass():
    ctx = _ctx(total_mass_kg=3.3)
    wc = _worker_ctx_from(ctx)
    assert wc.asb_airplane is ctx.asb_airplane
    assert wc.capabilities == ctx.capabilities
    assert wc.deflection_limits == ctx.deflection_limits
    assert wc.constraints == ctx.constraints
    assert wc.effective_mass_kg == ctx.effective_mass_kg
    assert wc.refs == ctx.refs
    # the SQLAlchemy aircraft model is reduced to the one scalar the solve needs
    assert wc.total_mass_kg == 3.3


def test_solve_target_in_worker_rebuilds_ctx_with_mass_stand_in():
    ctx = _ctx(total_mass_kg=4.0)
    wc = _worker_ctx_from(ctx)
    sentinel = object()
    captured = {}

    def _fake_solve(solve_ctx, target):
        captured["ctx"] = solve_ctx
        captured["target"] = target
        return sentinel

    with patch.object(opg, "_solve_and_enrich", side_effect=_fake_solve):
        result = _solve_target_in_worker(wc, {"name": "cruise"})

    assert result is sentinel
    rebuilt = captured["ctx"]
    # rebuilt context uses the lightweight aircraft stand-in + the shipped fields
    assert isinstance(rebuilt.aircraft, _AircraftMassOnly)
    assert rebuilt.aircraft.total_mass_kg == 4.0
    assert rebuilt.asb_airplane is ctx.asb_airplane
    assert rebuilt.effective_mass_kg == ctx.effective_mass_kg
    assert captured["target"] == {"name": "cruise"}


def test_solve_targets_in_parallel_yields_points_and_skips_failures():
    ctx = _ctx()
    targets = [{"name": "a"}, {"name": "b"}, {"name": "c"}]

    def _fake_solve(_solve_ctx, target):
        if target["name"] == "b":
            raise RuntimeError("boom")  # one bad target must not kill the run
        return f"point-{target['name']}"

    with (
        patch.object(opg, "_get_opg_executor", return_value=_InlineExecutor()),
        patch.object(opg, "_solve_and_enrich", side_effect=_fake_solve),
    ):
        results = dict((t["name"], p) for t, p in _solve_targets_in_parallel(ctx, targets))

    assert results == {"a": "point-a", "b": None, "c": "point-c"}


def test_solve_targets_in_parallel_empty_is_noop():
    ctx = _ctx()
    with patch.object(opg, "_get_opg_executor") as get_exec:
        out = list(_solve_targets_in_parallel(ctx, []))
    assert out == []
    get_exec.assert_not_called()  # no pool spawned when there is nothing to solve


class _FakePool:
    """Records the BLAS env seen at construction; no real processes."""

    last_env_at_construction: dict | None = None

    def __init__(self, **kwargs):
        type(self).last_env_at_construction = {v: os.environ.get(v) for v in opg._BLAS_THREAD_ENV}
        self.max_workers = kwargs.get("max_workers")
        self.shutdown_called = False

    def map(self, fn, iterable):
        return [fn(x) for x in iterable]

    def shutdown(self, **kwargs):
        self.shutdown_called = True


@pytest.fixture()
def _clean_pool_and_env():
    """Reset the module pool + remove BLAS vars so the pin/restore is observable."""
    opg.shutdown_opg_executor()
    saved = {v: os.environ.pop(v, None) for v in opg._BLAS_THREAD_ENV}
    try:
        yield
    finally:
        opg.shutdown_opg_executor()
        for v, old in saved.items():
            if old is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = old


def test_executor_pins_blas_during_creation_then_restores(_clean_pool_and_env):
    with patch.object(opg, "ProcessPoolExecutor", _FakePool):
        ex = opg._get_opg_executor()

    # BLAS threads were pinned to "1" at the moment the pool was constructed...
    assert _FakePool.last_env_at_construction is not None
    assert all(v == "1" for v in _FakePool.last_env_at_construction.values())
    # ...and the parent env is restored afterwards (vars were unset → stay unset)
    assert all(os.environ.get(v) is None for v in opg._BLAS_THREAD_ENV)
    # singleton: a second call reuses the same pool
    with patch.object(opg, "ProcessPoolExecutor", _FakePool):
        assert opg._get_opg_executor() is ex


def test_shutdown_resets_pool(_clean_pool_and_env):
    with patch.object(opg, "ProcessPoolExecutor", _FakePool):
        ex = opg._get_opg_executor()
    assert isinstance(ex, _FakePool)
    opg.shutdown_opg_executor()
    assert opg._opg_executor is None
    opg.shutdown_opg_executor()  # idempotent
    assert opg._opg_executor is None


@pytest.mark.slow
@pytest.mark.requires_aerosandbox
def test_real_processpool_solves_targets_end_to_end():
    """Real spawn + pickle + solve: proves asb.Airplane ships to workers and the
    trim solve runs there. Inline tests can't catch pickling/spawn regressions."""
    import aerosandbox as asb

    wing_af = asb.Airfoil("naca2412")
    tail_af = asb.Airfoil("naca0010")
    wing = asb.Wing(
        name="Main",
        symmetric=True,
        xsecs=[
            asb.WingXSec(xyz_le=[0, 0, 0], chord=0.18, airfoil=wing_af),
            asb.WingXSec(xyz_le=[0.02, 0.7, 0], chord=0.12, airfoil=wing_af),
        ],
    )
    htail = asb.Wing(
        name="H",
        symmetric=True,
        xsecs=[
            asb.WingXSec(
                xyz_le=[0.6, 0, 0],
                chord=0.09,
                airfoil=tail_af,
                control_surfaces=[
                    asb.ControlSurface(name="[elevator]Elevator", hinge_point=0.7, deflection=0.0)
                ],
            ),
            asb.WingXSec(xyz_le=[0.62, 0.22, 0], chord=0.07, airfoil=tail_af),
        ],
    )
    airplane = asb.Airplane(name="t", wings=[wing, htail], xyz_ref=[0.05, 0, 0])

    ctx = _GenerationContext(
        aircraft=_AircraftMassOnly(2.0),
        targets=[],
        asb_airplane=airplane,
        capabilities=opg._detect_control_capabilities(airplane),
        deflection_limits={},
        plane_schema=None,  # enrichment fails gracefully; the solve is what matters
        constraints={"max_alpha_deg": 14.0},
        effective_mass_kg=2.0,
        design_cg_x=0.05,
        source_profile_id=None,
        refs={"vs_clean": 8.0},
    )
    targets = [
        {"name": "cruise", "config": "clean", "velocity": 15.0, "altitude": 0.0, "n_target": 1.0},
        {"name": "slow", "config": "clean", "velocity": 11.0, "altitude": 0.0, "n_target": 1.0},
    ]
    try:
        results = {t["name"]: p for t, p in _solve_targets_in_parallel(ctx, targets)}
    finally:
        opg.shutdown_opg_executor()

    assert set(results) == {"cruise", "slow"}
    for name, point in results.items():
        assert point is not None, f"{name} did not solve in a worker process"
        assert math.isfinite(point.alpha_rad)
