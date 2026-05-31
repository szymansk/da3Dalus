"""gh-806: coordinated-turn kinematics (load factor + body rates from bank angle)."""

import math

import pytest

from app.services.turn_kinematics import TurnKinematics, turn_kinematics

G = 9.81


class TestLoadFactor:
    @pytest.mark.parametrize(
        "bank_deg, n_expected",
        [(20.0, 1.0642), (40.0, 1.3054), (60.0, 2.0)],
    )
    def test_load_factor(self, bank_deg, n_expected):
        tk = turn_kinematics(bank_deg=bank_deg, velocity=20.0)
        assert tk.n == pytest.approx(n_expected, abs=1e-3)
        assert tk.cl_factor == pytest.approx(tk.n)


class TestBodyRates:
    def test_rates_match_turn_rate(self):
        v = 25.0
        bank = 45.0
        tk = turn_kinematics(bank_deg=bank, velocity=v)
        psi_dot = G * math.tan(math.radians(bank)) / v
        assert tk.psi_dot == pytest.approx(psi_dot)
        assert tk.p == pytest.approx(0.0)
        assert tk.q == pytest.approx(psi_dot * math.sin(math.radians(bank)))
        assert tk.r == pytest.approx(psi_dot * math.cos(math.radians(bank)))
        assert math.hypot(tk.q, tk.r) == pytest.approx(psi_dot)

    def test_r_dominates_and_increases_with_bank(self):
        v = 20.0
        r20 = turn_kinematics(20.0, v).r
        r40 = turn_kinematics(40.0, v).r
        r60 = turn_kinematics(60.0, v).r
        assert 0 < r20 < r40 < r60

    def test_returns_dataclass(self):
        tk = turn_kinematics(30.0, 20.0)
        assert isinstance(tk, TurnKinematics)
