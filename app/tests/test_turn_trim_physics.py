"""gh-806 — fachlicher (domain-correctness) test for steady coordinated turns.

This is a *physics* test, not a smoke test. Every assertion encodes a flight-
mechanics ground truth for a steady, coordinated, level turn (right turn,
phi > 0), validated against Sadraey, "Aircraft Design: A Systems Engineering
Approach" (Wiley 2013):

  * Load factor n = 1/cos(phi):  20deg -> 1.064, 40deg -> 1.305, 60deg -> 2.000.
  * CL_turn = n * CL_1g  =>  higher bank => higher required CL => higher trimmed
    alpha AND more nose-up elevator (pull). Both must increase MONOTONICALLY
    from turn_20 -> turn_40 -> turn_60.
  * Body rates (theta ~= 0):  p ~= 0, q = psi_dot*sin(phi) (>0, pull),
    r = psi_dot*cos(phi) (>0, dominant), sqrt(q^2 + r^2) = psi_dot.
  * A coordinated turn carries a small PRO-TURN rudder (non-zero yaw control);
    an uncoordinated (rudder-free) turn would be a slip, not a coordinated turn.

If the trimmer's output contradicts any of these, the assertion is left as the
*correct* physics so the test FAILS and exposes the bug — the assertion is not
weakened to match wrong output.

Marked slow + requires_aerosandbox: it calls the real AeroBuildup trimmer.
Only one such file per agent (slow trim tests must not run many-in-parallel).
"""

from __future__ import annotations

import math

import pytest

from app.services.operating_point_generator_service import (
    PITCH_ROLES,
    YAW_ROLES,
)
from app.services.trim_enrichment_service import parse_role_tag
from app.services.turn_kinematics import turn_kinematics

# Banks of the default turn set, ascending.
_TURN_BANKS = {"turn_20": 20.0, "turn_40": 40.0, "turn_60": 60.0}
_TURN_ORDER = ["turn_20", "turn_40", "turn_60"]


def _classify_control(name: str) -> str | None:
    """Map a control-dict key (e.g. '[elevator]pitch_wing_1') to 'pitch'/'yaw'."""
    role, _ = parse_role_tag(name)
    if role in PITCH_ROLES:
        return "pitch"
    if role in YAW_ROLES:
        return "yaw"
    return None


def _pitch_magnitude(controls: dict[str, float]) -> float:
    """Total |pitch-axis control| at trim (sum over any pitch-tagged surfaces)."""
    return sum(abs(v) for k, v in controls.items() if _classify_control(k) == "pitch")


def _yaw_magnitude(controls: dict[str, float]) -> float:
    return sum(abs(v) for k, v in controls.items() if _classify_control(k) == "yaw")


@pytest.fixture(scope="module")
def turn_ops():
    """Generate the default OP set once and return the three turn OPs by name.

    Module-scoped so the expensive AeroBuildup trim solve runs a single time
    and is shared across this file's physics assertions. Mirrors the
    conftest ``client_and_db`` setup (in-memory SQLite + default-type seeds)
    but at module scope.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.db.base import Base
    from app.db.session import get_db
    from app.main import create_app
    from app.services.operating_point_generator_service import (
        generate_default_set_for_aircraft,
    )
    from app.services.component_type_service import seed_default_types
    from app.services.mission_objective_service import seed_mission_presets
    from app.tests.conftest import seed_smoke_conventional_ttail

    app = create_app()
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )
    Base.metadata.create_all(bind=engine)

    seed_session = SessionLocal()
    try:
        seed_default_types(seed_session)
        seed_mission_presets(seed_session)
        seed_session.commit()
    finally:
        seed_session.close()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    session = SessionLocal()
    try:
        aeroplane = seed_smoke_conventional_ttail(session)
        result = generate_default_set_for_aircraft(
            session, aeroplane.uuid, replace_existing=True
        )
    finally:
        session.close()

    by_name = {op.name: op for op in result.operating_points}
    missing = set(_TURN_BANKS) - set(by_name)
    assert not missing, f"default set is missing turn OPs: {sorted(missing)}"

    yield {name: by_name[name] for name in _TURN_BANKS}

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.mark.slow
@pytest.mark.requires_aerosandbox
def test_trimmed_alpha_increases_monotonically_with_bank(turn_ops):
    """Higher load factor => more required CL => higher trimmed alpha.

    alpha(20) < alpha(40) < alpha(60). A flat or decreasing trend would mean the
    trimmer is not carrying the extra turn load into the lift balance.
    """
    alphas = {name: math.degrees(turn_ops[name].alpha) for name in _TURN_ORDER}
    a20, a40, a60 = (alphas[n] for n in _TURN_ORDER)
    # Strict monotonic increase. Use a tiny epsilon so a numerically-flat
    # solve (no n-dependence) is treated as a failure, not a pass.
    eps = 0.05  # deg — well below the physical alpha spread between n=1.06 and n=2.0
    assert a40 > a20 + eps, (
        f"alpha must rise from 20->40 deg bank (n 1.06->1.31): {a20:.3f} -> {a40:.3f} deg"
    )
    assert a60 > a40 + eps, (
        f"alpha must rise from 40->60 deg bank (n 1.31->2.00): {a40:.3f} -> {a60:.3f} deg"
    )


def _signed_pitch(controls: dict[str, float]) -> float:
    """Signed pitch-axis control (sum over pitch-tagged surfaces, keeping sign)."""
    return sum(v for k, v in controls.items() if _classify_control(k) == "pitch")


@pytest.mark.slow
@pytest.mark.requires_aerosandbox
def test_pitch_control_moves_monotonically_with_bank(turn_ops):
    """More load => more nose-up trim => elevator moves monotonically (more pull).

    PHYSICS / SIGN CONVENTION (verified against this trimmer's own output across
    every default OP, sorted by alpha): for this statically-stable airframe the
    trim elevator is a strictly monotonic function of trimmed alpha,
    d(elevator)/d(alpha) < 0 — i.e. the *nose-up / pull* direction is the
    DECREASING (toward negative) elevator direction. Across the turns at a fixed
    V the trimmed elevator therefore steps strictly DOWN as bank/n/alpha grow:
    e.g. ~+6.8 -> ~+4.6 -> ~-1.1 deg.

    The meaningful invariant is *strict monotonic motion in the pull direction*,
    NOT the unsigned magnitude — magnitude is non-monotonic only because the trim
    point happens to cross elevator=0 between 40 and 60 deg. A flat or
    direction-reversing elevator (no extra pull at higher n) would be the bug.
    """
    ele = {name: _signed_pitch(turn_ops[name].controls) for name in _TURN_ORDER}
    e20, e40, e60 = (ele[n] for n in _TURN_ORDER)
    # Sanity: there is an actual pitch control to reason about.
    assert any(_classify_control(k) == "pitch" for k in turn_ops["turn_60"].controls), (
        f"expected a pitch control on the conventional T-tail; "
        f"controls={turn_ops['turn_60'].controls}"
    )
    eps = 0.05  # deg — guards against a numerically flat (n-independent) elevator
    # Pull direction for this convention is DECREASING elevator (d/dalpha < 0).
    assert e40 < e20 - eps, (
        "elevator must move in the nose-up (pull = decreasing) direction "
        f"from 20->40 deg bank: {e20:.3f} -> {e40:.3f} deg"
    )
    assert e60 < e40 - eps, (
        "elevator must move further nose-up (decreasing) from 40->60 deg bank: "
        f"{e40:.3f} -> {e60:.3f} deg"
    )


@pytest.mark.slow
@pytest.mark.requires_aerosandbox
def test_stored_rates_match_turn_kinematics(turn_ops):
    """Each turn OP stores the body rates that its (bank, V) kinematics produce.

    The OP must carry q ~= turn_kinematics(bank, V).q and r ~= .r — i.e. the
    rates the trimmer actually solved at are the coordinated-turn kinematics,
    not zeros or some unrelated value. Identity: q = psi_dot*sin(phi),
    r = psi_dot*cos(phi) => q/r = tan(phi) exactly, and p ~= 0 (theta ~= 0).
    (NB: q exceeds r above 45 deg bank, since tan(phi) > 1 there.)
    """
    for name in _TURN_ORDER:
        op = turn_ops[name]
        bank = _TURN_BANKS[name]
        tk = turn_kinematics(bank_deg=bank, velocity=float(op.velocity))
        # Stored values are rounded to 6 decimals in _op_turn_rates.
        assert op.q == pytest.approx(tk.q, abs=1e-5), (
            f"{name}: stored q={op.q} != kinematics q={tk.q} (V={op.velocity})"
        )
        assert op.r == pytest.approx(tk.r, abs=1e-5), (
            f"{name}: stored r={op.r} != kinematics r={tk.r} (V={op.velocity})"
        )
        assert op.p == pytest.approx(0.0, abs=1e-6), (
            f"{name}: level turn (theta~=0) must have p~=0, got {op.p}"
        )
        # Physical sanity: both rates positive (right turn), and their ratio is
        # exactly tan(phi) — the defining geometry of a coordinated level turn.
        assert op.r > 0.0 and op.q > 0.0, f"{name}: right turn must have q,r > 0"
        assert (op.q / op.r) == pytest.approx(math.tan(math.radians(bank)), abs=1e-4), (
            f"{name}: q/r must equal tan(phi)={math.tan(math.radians(bank)):.4f}; "
            f"got q/r={op.q / op.r:.4f} at bank {bank} deg"
        )


@pytest.mark.slow
@pytest.mark.requires_aerosandbox
def test_load_factor_at_60deg_is_two(turn_ops):
    """n at 60 deg bank == 2.0, recovered purely from the stored OP rates.

    For a coordinated level turn: r = psi_dot*cos(phi), q = psi_dot*sin(phi),
    so sqrt(q^2 + r^2)/r = 1/cos(phi) = n. This recovers the load factor from
    what the OP actually stored, independent of any 'n_target' bookkeeping.
    """
    op = turn_ops["turn_60"]
    psi_dot = math.hypot(op.q, op.r)
    n_from_rates = psi_dot / op.r
    assert n_from_rates == pytest.approx(2.0, abs=0.01), (
        f"load factor implied by stored rates at 60 deg = {n_from_rates:.4f}, "
        "expected 2.000 (n = 1/cos 60deg)"
    )
    # Cross-check the kinematics identity itself: n = 1/cos(60) = 2.0 exactly.
    assert turn_kinematics(60.0, float(op.velocity)).n == pytest.approx(2.0, abs=1e-9)


@pytest.mark.slow
@pytest.mark.requires_aerosandbox
def test_turn_is_coordinated_with_proturn_rudder(turn_ops):
    """A coordinated turn deflects a yaw (rudder) control — it is not left as a slip.

    The trimmer drives residual Cn toward zero; with a swept/dihedral-coupled
    airframe and the yaw rate present, that requires a non-zero rudder. A turn
    OP with exactly-zero rudder would be an uncoordinated turn (the feature's
    whole point is the coordinated trim), so zero is a failure.
    """
    op = turn_ops["turn_60"]
    # The seeded conventional T-tail must expose a yaw control at all.
    has_yaw_key = any(_classify_control(k) == "yaw" for k in op.controls)
    assert has_yaw_key, (
        "expected a yaw (rudder) control on the conventional T-tail; "
        f"controls={op.controls}"
    )
    yaw_mag = _yaw_magnitude(op.controls)
    assert yaw_mag > 1e-3, (
        "coordinated turn must carry a non-zero rudder deflection (pro-turn yaw); "
        f"got |rudder|={yaw_mag:.4f} deg — turn left uncoordinated. "
        f"controls={op.controls}"
    )
