"""The thrust at full throttle, the one function of the powered-performance formulas (gh-1414).

``full_throttle_thrust`` is the composition of the four embedded relations (torque balance, advance
ratio, table lookup, thrust from the coefficient) that ``static-thrust-to-weight``,
``motor-propeller-part-load`` and the six powered-performance formulas share. The reference is the
independent plain-Python balance of ``powertrain_reference`` (T-Motor AT2814 KV900, 14.8 V,
rho = 1.225 kg/m^3, APC 13x8E): 32.9713 N static (hand value of ``test_powertrain_chain``).
"""

import pytest
from aero_kernel.errors import FormulaError
from aero_kernel.formulas.propulsion import full_throttle_thrust
from aero_kernel.tests import powertrain_reference as reference
from aero_kernel.tests.components_builders import complete_components_with_table
from aero_kernel.tests.formula_builders import close
from aero_kernel.tests.test_powertrain_chain import context_for

KV, I0, RM = 900.0, 1.2, 0.082


def thrust_at(v: float, *, r_m: float | None = RM, i_0: float | None = I0) -> float:
    ctx = context_for("static-thrust-to-weight")
    return full_throttle_thrust(
        ctx,
        complete_components_with_table(),
        v,
        reference.RHO,
        KV,
        i_0,
        r_m,
        reference.U_BAT,
        reference.D_PROP,
    )


@pytest.mark.parametrize("v", [0.0, 5.0, 10.0, 20.0])
def test_the_thrust_equals_the_independent_balance(v: float) -> None:
    assert close(thrust_at(v), reference.full_throttle(v).thrust, 1e-6)


def test_the_static_value_is_the_hand_value() -> None:
    assert close(thrust_at(0.0), 32.9713, 1e-5)


def test_the_thrust_falls_with_the_airspeed() -> None:
    assert thrust_at(0.0) > thrust_at(10.0) > thrust_at(20.0) > 0.0


def test_an_absent_winding_resistance_is_missing_input() -> None:
    with pytest.raises(FormulaError) as caught:
        thrust_at(10.0, r_m=None)
    assert caught.value.code == "missing_input"


def test_a_speed_beyond_the_table_is_the_declared_failure() -> None:
    with pytest.raises(FormulaError) as caught:
        thrust_at(80.0)
    assert caught.value.code == "outside_propeller_table"
