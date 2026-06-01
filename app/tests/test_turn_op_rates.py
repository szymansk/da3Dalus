"""gh-806: a turn target's body rates are derived from its bank angle."""

import math

from app.services.operating_point_generator_service import _op_turn_rates


def test_no_bank_means_zero_rates():
    assert _op_turn_rates({"name": "cruise", "n_target": 1.0}, velocity=20.0) == (0.0, 0.0, 0.0)


def test_turn_target_has_nonzero_rates():
    p, q, r = _op_turn_rates({"name": "turn_40", "bank_deg": 40.0}, velocity=25.0)
    psi_dot = 9.81 * math.tan(math.radians(40.0)) / 25.0
    assert p == 0.0
    assert q > 0.0 and r > 0.0
    assert r == round(psi_dot * math.cos(math.radians(40.0)), 6)
    assert abs(math.hypot(q, r) - psi_dot) < 1e-6
