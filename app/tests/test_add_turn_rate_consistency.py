"""gh-806: numerical consistency of the persisted turn OP rates with turn_kinematics.

This is a *fachlicher* (domain-correctness) test, not a coverage filler. It verifies
the kinematics -> stored-OperatingPointModel plumbing end to end on a real aircraft:

For a steady coordinated level right turn (phi > 0, theta ~= 0) the body-axis rates
are (Sadraey / standard flight mechanics):

    psi_dot = g * tan(phi) / V        (heading rate)
    p = 0                              (no roll rate in steady turn, theta = 0)
    q = psi_dot * sin(phi)  > 0        (nose-up pull)
    r = psi_dot * cos(phi)  > 0        (dominant yaw rate)
    n = 1 / cos(phi)                   (load factor)

The add-turn service stores the body rates as round(tk.{p,q,r}, 6). This test asserts
the PERSISTED OperatingPointModel rates are numerically identical to
turn_kinematics(bank, op.velocity) — i.e. the stored OP is exactly the kinematics the
math says it should be, evaluated at the velocity that was actually used.
"""

import math

import pytest

from app.schemas.aeroanalysisschema import AddTurnRequest

_G = 9.81


@pytest.mark.slow
@pytest.mark.requires_aerosandbox
@pytest.mark.parametrize("bank", [30.0, 50.0])
def test_persisted_turn_rates_match_kinematics(client_and_db, bank):
    """Persisted OP rates equal turn_kinematics(bank, op.velocity), exactly (6 dp)."""
    from app.models.analysismodels import OperatingPointModel
    from app.services.add_turn_service import add_turn_operating_point
    from app.services.turn_kinematics import turn_kinematics
    from app.tests.conftest import seed_smoke_conventional_ttail

    _client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        aeroplane = seed_smoke_conventional_ttail(session)
        op = add_turn_operating_point(session, aeroplane.uuid, AddTurnRequest(bank_angle_deg=bank))
        op_id = op.id
        velocity = op.velocity
        name = op.name
        p, q, r = op.p, op.q, op.r
        session.commit()
    finally:
        session.close()

    # --- Recompute the flight-mechanics ground truth at the velocity actually used. ---
    tk = turn_kinematics(bank_deg=bank, velocity=velocity)

    # 1) The persisted rates are EXACTLY the kinematics (stored as round(.,6)).
    #    This is the core plumbing assertion: kinematics -> stored OP, no drift.
    assert r == round(tk.r, 6), f"yaw rate r mismatch at bank {bank}"
    assert q == round(tk.q, 6), f"pitch rate q mismatch at bank {bank}"
    assert p == 0.0, f"roll rate p must be 0 in a steady level turn (theta=0), got {p}"

    # 2) Physical signs/dominance for a right turn (phi > 0): r and q both positive,
    #    yaw dominant over pitch (cos phi > sin phi for phi < 45 deg; at 50 deg q>r).
    assert r > 0.0, "yaw rate must be positive (pro-turn) in a right turn"
    assert q > 0.0, "pitch rate must be positive (nose-up pull) in a right turn"
    assert tk.psi_dot > 0.0

    # 3) Conservation identity: the body-rate vector magnitude equals the heading rate.
    #    sqrt(q^2 + r^2) == psi_dot (since p == 0 here).
    assert math.isclose(math.hypot(q, r), tk.psi_dot, rel_tol=1e-4, abs_tol=1e-4), (
        "sqrt(q^2 + r^2) must equal psi_dot for a coordinated turn"
    )

    # 4) The independent kinematic definitions hold at this velocity.
    phi = math.radians(bank)
    assert math.isclose(tk.r, _G * math.tan(phi) / velocity * math.cos(phi), rel_tol=1e-9)
    assert math.isclose(tk.q, _G * math.tan(phi) / velocity * math.sin(phi), rel_tol=1e-9)

    # 5) Implied load factor n = 1/cos(phi).  30 deg -> 1.1547, 50 deg -> 1.5557.
    assert math.isclose(tk.n, 1.0 / math.cos(phi), rel_tol=1e-9)
    assert math.isclose(tk.cl_factor, tk.n, rel_tol=1e-12)

    # 6) The OP is named turn_<bank> and is actually PERSISTED (queryable by id).
    assert name == f"turn_{round(bank)}"
    session2 = SessionLocal()
    try:
        reloaded = session2.query(OperatingPointModel).filter(OperatingPointModel.id == op_id).one()
        assert reloaded.name == f"turn_{round(bank)}"
        # The reloaded-from-DB rates still match the kinematics: persistence is lossless.
        assert reloaded.r == round(tk.r, 6)
        assert reloaded.q == round(tk.q, 6)
        assert reloaded.p == 0.0
    finally:
        session2.close()
